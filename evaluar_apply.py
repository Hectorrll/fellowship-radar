"""Evalúa vacantes y genera paquetes de aplicación — keys NVIDIA_FELLOW_* (aisladas de Job Radar)."""
import os
import json
import time
import threading
from datetime import date, timedelta

import requests

CRITERIOS_FILE = os.getenv("APPLY_CRITERIOS", "criterios_apply.txt")


def _keys(*names):
    return [k for k in (os.getenv(n) for n in names) if k]


KEYS_FAST = _keys("NVIDIA_FELLOW_KEY_1", "NVIDIA_FELLOW_KEY_2")
KEYS_THINK = _keys("NVIDIA_FELLOW_KEY_3")
if not KEYS_FAST:
    raise SystemExit("# ERROR: falta NVIDIA_FELLOW_KEY_1")

URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = os.getenv("APPLY_MODEL", "meta/llama-4-maverick-17b-128e-instruct")
FALLBACK_MODEL = "meta/llama-3.3-70b-instruct"
THINK_MODEL = os.getenv("APPLY_THINK_MODEL", "moonshotai/kimi-k2.6")
THINK_FALLBACK = os.getenv("APPLY_THINK_FALLBACK", "minimaxai/minimax-m3")

REQ_TIMEOUT = int(os.getenv("APPLY_REQ_TIMEOUT", "90"))
MAX_TOKENS = 400
PACK_MAX_TOKENS = 1200
MIN_INTERVAL = float(os.getenv("APPLY_MIN_INTERVAL", "1.6"))
THINK_INTERVAL = float(os.getenv("APPLY_THINK_INTERVAL", "3.0"))

with open(CRITERIOS_FILE, encoding="utf-8") as f:
    CRITERIOS = f.read()

_session = requests.Session()

VOZ_SIGNALS = [
    "phone call", "video call", "fluent english", "verbal english", "spoken english",
    "native english", "phone screen", "voice interview", "standup", "zoom call",
]


class _Retryable(Exception):
    def __init__(self, msg, wait=None):
        super().__init__(msg)
        self.wait = wait


class _Pool:
    def __init__(self, keys, interval):
        self.keys = keys
        self.interval = interval
        self._locks = [threading.Lock() for _ in keys]
        self._next = [[0.0] for _ in keys]
        self._rr_lock = threading.Lock()
        self._rr = [0]

    def _acquire(self):
        with self._rr_lock:
            i = self._rr[0] % len(self.keys)
            self._rr[0] += 1
        with self._locks[i]:
            now = time.monotonic()
            start_at = max(now, self._next[i][0])
            self._next[i][0] = start_at + self.interval
            wait = start_at - now
        if wait > 0:
            time.sleep(wait)
        return self.keys[i]

    def pedir(self, prompt, modelo, max_tokens):
        key = self._acquire()
        payload = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
        r = _session.post(URL, headers=headers, json=payload, timeout=REQ_TIMEOUT)
        if r.status_code == 429:
            ra = r.headers.get("Retry-After", "")
            raise _Retryable("HTTP 429 rate limit", wait=float(ra) if ra.isdigit() else None)
        if r.status_code >= 500:
            raise _Retryable(f"HTTP {r.status_code} servidor")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


_pool_fast = _Pool(KEYS_FAST, MIN_INTERVAL)
_pool_think = _Pool(KEYS_THINK, THINK_INTERVAL) if KEYS_THINK else _Pool(KEYS_FAST, MIN_INTERVAL)


def tiene_think():
    return bool(KEYS_THINK)


def _vacante_texto(v):
    url = v.get("url") or v.get("link", "")
    return (
        f"Titulo: {v.get('titulo', '')}\n"
        f"Empresa: {v.get('empresa', '')}\n"
        f"URL: {url}\n"
        f"Prioridad: {v.get('prioridad', 'normal')}\n"
        f"Descripcion:\n{v.get('descripcion', '')[:4000]}"
    )


def _parse_json(content):
    ini, fin = content.find("{"), content.rfind("}")
    if ini == -1 or fin == -1:
        return None
    try:
        return json.loads(content[ini:fin + 1])
    except json.JSONDecodeError:
        return None


def _llamar(pool, prompt, modelos, max_tokens, etiqueta):
    ultimo_error = ""
    for idx, modelo in enumerate(modelos):
        if idx > 0:
            print(f"# INFO fallback ({etiqueta}) -> {modelo}")
        backoff = 2.0
        for _ in range(2):
            try:
                content = pool.pedir(prompt, modelo, max_tokens)
                parsed = _parse_json(content)
                if parsed:
                    return parsed
                ultimo_error = "respuesta sin JSON valido"
            except _Retryable as e:
                ultimo_error = str(e)
                time.sleep(e.wait if e.wait else backoff)
                backoff = min(backoff * 2, 30)
            except Exception as e:
                ultimo_error = str(e)
                time.sleep(1)
    print(f"# WARN {etiqueta}: {ultimo_error}")
    return None


def detectar_red_flags_keyword(v):
    texto = (v.get("titulo", "") + " " + v.get("descripcion", "")).lower()
    flags = []
    if any(s in texto for s in VOZ_SIGNALS):
        flags.append("posible voz EN requerida")
    if "us citizen" in texto or "us only" in texto:
        flags.append("posible restriccion US-only")
    if "pay to apply" in texto or "application fee" in texto:
        flags.append("posible fee aplicacion")
    return flags


def evaluar_fit(v):
    prompt = (
        f"{CRITERIOS}\n\nTAREA: Evaluar FIT para aplicar.\n\n"
        f"{_vacante_texto(v)}\n\nRespondé SOLO JSON fit."
    )
    modelos = [MODEL] if MODEL == FALLBACK_MODEL else [MODEL, FALLBACK_MODEL]
    res = _llamar(_pool_fast, prompt, modelos, MAX_TOKENS, "fit")
    if not res:
        return {"aceptar": True, "fit_score": 5, "motivo": "evaluacion fallida — revisar manual", "red_flags": []}
    res.setdefault("fit_score", 5)
    res.setdefault("red_flags", [])
    kw = detectar_red_flags_keyword(v)
    for f in kw:
        if f not in res["red_flags"]:
            res["red_flags"].append(f)
    return res


def generar_paquete(v, fit=None):
    hoy = date.today().isoformat()
    follow_default = (date.today() + timedelta(days=6)).isoformat()
    fit_txt = json.dumps(fit or {}, ensure_ascii=False)
    prompt = (
        f"{CRITERIOS}\n\nTAREA: Generar PAQUETE de aplicacion completo.\n"
        f"Hoy: {hoy}\n\nEvaluacion previa:\n{fit_txt}\n\n"
        f"{_vacante_texto(v)}\n\nRespondé SOLO JSON paquete."
    )
    modelos = [THINK_MODEL, THINK_FALLBACK] if tiene_think() else [MODEL, FALLBACK_MODEL]
    pool = _pool_think if tiene_think() else _pool_fast
    res = _llamar(pool, prompt, modelos, PACK_MAX_TOKENS, "paquete")
    if not res:
        return _paquete_fallback(v, fit, follow_default)
    res.setdefault("fit_score", fit.get("fit_score", 5) if fit else 5)
    res.setdefault("red_flags", fit.get("red_flags", []) if fit else [])
    res.setdefault("resumen_es", ["Revisar JD manualmente"])
    res.setdefault("cover_en", "DRAFT unavailable — generar en Antigravity")
    res.setdefault("checklist", ["Revisar cover en Antigravity Sonnet antes de enviar", "Adjuntar CV EN"])
    res.setdefault("pregunta_obligatoria", "")
    res.setdefault("follow_up_fecha", follow_default)
    if "Revisar cover en Antigravity" not in " ".join(res["checklist"]):
        res["checklist"].append("Revisar cover en Antigravity Sonnet antes de enviar")
    return res


def _paquete_fallback(v, fit, follow_default):
    return {
        "fit_score": fit.get("fit_score", 5) if fit else 5,
        "red_flags": fit.get("red_flags", []) if fit else detectar_red_flags_keyword(v),
        "resumen_es": [
            f"Rol: {v.get('titulo', '')[:80]}",
            f"Empresa: {v.get('empresa', '')}",
            "Paquete IA fallo — completar manualmente",
            "Verificar dealbreakers voz EN",
            "Aplicar si encaja con perfil async/LATAM",
        ],
        "cover_en": "DRAFT unavailable — usar Antigravity Sonnet 4.6",
        "checklist": [
            "Revisar cover en Antigravity Sonnet antes de enviar",
            "Adjuntar CV: dia-27/CV-Hector-Automatizacion-EN.md",
            f"Aplicar en: {v.get('url') or v.get('link', '')}",
            f"Follow-up: {follow_default}",
        ],
        "pregunta_obligatoria": "Is day-to-day communication async/written only, or are spoken English calls required?",
        "follow_up_fecha": follow_default,
    }
