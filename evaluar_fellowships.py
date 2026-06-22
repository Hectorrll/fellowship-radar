"""Evalúa fellowships/becas con NVIDIA NIM — keys AISLADAS de Job Radar.

NIVEL 1: Llama 4 Maverick (pool NVIDIA_FELLOW_KEY_1/_2).
NIVEL 2 (opcional): Kimi K2.6 → MiniMax M3 (pool NVIDIA_FELLOW_KEY_3).
"""
import os
import json
import time
import threading

import requests


def _keys(*names):
    return [k for k in (os.getenv(n) for n in names) if k]


KEYS_FAST = _keys("NVIDIA_FELLOW_KEY_1", "NVIDIA_FELLOW_KEY_2")
KEYS_THINK = _keys("NVIDIA_FELLOW_KEY_3")
if not KEYS_FAST:
    raise SystemExit("# ERROR: falta NVIDIA_FELLOW_KEY_1")

URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MODEL = os.getenv("FELLOW_MODEL", "meta/llama-4-maverick-17b-128e-instruct")
FALLBACK_MODEL = "meta/llama-3.3-70b-instruct"
THINK_MODEL = os.getenv("FELLOW_THINK_MODEL", "moonshotai/kimi-k2.6")
THINK_FALLBACK = os.getenv("FELLOW_THINK_FALLBACK", "minimaxai/minimax-m3")

REQ_TIMEOUT = int(os.getenv("FELLOW_REQ_TIMEOUT", "60"))
MAX_TOKENS = 350
THINK_MAX_TOKENS = 500
MIN_INTERVAL = float(os.getenv("FELLOW_MIN_INTERVAL", "1.6"))
THINK_INTERVAL = float(os.getenv("FELLOW_THINK_INTERVAL", "3.0"))

with open("criterios_fellowships.txt", encoding="utf-8") as f:
    CRITERIOS = f.read()

_session = requests.Session()


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
        payload = {"model": modelo, "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.1, "max_tokens": max_tokens}
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
_pool_think = _Pool(KEYS_THINK, THINK_INTERVAL) if KEYS_THINK else None


def tiene_think():
    return _pool_think is not None


def _prompt(v):
    return (
        f"{CRITERIOS}\n\nPROGRAMA A EVALUAR:\n"
        f"Titulo: {v['titulo']}\nOrganizacion: {v['empresa']}\nUbicacion: {v['ubicacion']}\n"
        f"Fuente: {v['fuente']}\nDescripcion: {v['descripcion']}"
    )


def _evaluar(v, pool, modelos, max_tokens, etiqueta):
    prompt = _prompt(v)
    ultimo_error = ""
    for idx, modelo in enumerate(modelos):
        if idx > 0:
            print(f"# INFO fallback ({etiqueta}) -> {modelo}: '{v['titulo'][:30]}' ({ultimo_error[:40]})")
        backoff = 2.0
        for intento in range(2):
            try:
                content = pool.pedir(prompt, modelo, max_tokens)
                ini, fin = content.find("{"), content.rfind("}")
                if ini == -1 or fin == -1:
                    ultimo_error = "respuesta sin JSON"
                    continue
                res = json.loads(content[ini:fin + 1])
                return {"aceptar": bool(res.get("aceptar")), "motivo": str(res.get("motivo", ""))[:300]}
            except _Retryable as e:
                ultimo_error = str(e)
                time.sleep(e.wait if e.wait else backoff)
                backoff = min(backoff * 2, 30)
            except Exception as e:
                ultimo_error = str(e)
                time.sleep(1)
    print(f"# WARN {etiqueta} '{v['titulo'][:40]}': {ultimo_error}")
    return None


def evaluar_programa(v):
    modelos = [MODEL] if MODEL == FALLBACK_MODEL else [MODEL, FALLBACK_MODEL]
    res = _evaluar(v, _pool_fast, modelos, MAX_TOKENS, "screening")
    return res if res else {"aceptar": False, "motivo": "error de evaluacion"}


def evaluar_profundo(v):
    if not _pool_think:
        return None
    return _evaluar(v, _pool_think, [THINK_MODEL, THINK_FALLBACK], THINK_MAX_TOKENS, "profundo")
