"""LATAM Career Watcher — empresas objetivo ATS, prefijo Telegram [CAREER-LATAM]."""
import html
import json
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor

import evaluar_apply as evaluar
import latam_portales
import notificar_apply as notificar

SEEN_FILE = pathlib.Path("seen-latam.json")
MAX_EVALUAR = int(os.getenv("LATAM_MAX_EVALUAR", "25"))
EVAL_WORKERS = int(os.getenv("LATAM_EVAL_WORKERS", "4"))
PREFIX = "[CAREER-LATAM]"

KEYWORDS = [
    "n8n", "automation", "automatiz", "workflow", "python", "ai ", "llm",
    "virtual assistant", "customer support", "soporte", "async", "remote",
    "latam", "latin america", "español", "spanish", "bilingual", "operations",
    "integration", "api", "no-code", "make.com", "zapier", "hubspot",
]

NICHO = ["n8n", "automation", "automatiz", "ai agent", "workflow", "make.com", "zapier"]
VOZ_SIGNALS = evaluar.VOZ_SIGNALS
SPANISH_SIGNALS = ["español", "espanol", "spanish", "latam", "latin america", "guatemala", "mexico", "colombia"]


def cargar_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def guardar_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=1), encoding="utf-8")


def es_relevante(v):
    texto = (v["titulo"] + " " + v["descripcion"] + " " + v.get("ubicacion", "")).lower()
    return any(k in texto for k in KEYWORDS)


def es_nicho(v):
    t = (v["titulo"] + " " + v["descripcion"]).lower()
    return any(k in t for k in NICHO)


def score_vacante(v):
    texto = (v["titulo"] + " " + v["descripcion"] + " " + v.get("ubicacion", "")).lower()
    score = 0
    if es_nicho(v):
        score += 3
    if any(s in texto for s in SPANISH_SIGNALS):
        score += 2
    if "remote" in texto or "remoto" in texto:
        score += 1
    if any(s in texto for s in VOZ_SIGNALS):
        score -= 3
    return score


def _mensaje(v, fit):
    url = v.get("url") or v.get("link", "")
    flags = fit.get("red_flags") or []
    flags_txt = ", ".join(flags) if flags else "ninguno"
    return (
        f"🌎 <b>{html.escape(v['titulo'][:100])}</b>\n"
        f"🏢 {html.escape(v.get('empresa') or '—')}\n"
        f"📍 {html.escape(v.get('ubicacion', ''))}\n"
        f"📊 Fit: {fit.get('fit_score', '?')}/10\n"
        f"🚩 {html.escape(flags_txt)}\n"
        f"💡 {html.escape(str(fit.get('motivo', ''))[:250])}\n"
        f"🔎 {html.escape(v.get('fuente', ''))}\n"
        f"🔗 {html.escape(url)}\n\n"
        f"<i>Encolar en apply_queue.json para paquete completo [APPLY]</i>"
    )


def main():
    seen = cargar_seen()
    print(f"# LATAM CAREER WATCHER | targets={len(latam_portales.load_targets())}")
    todas = latam_portales.fetch_all_targets()
    print(f"# {len(todas)} vacantes ATS")

    nuevas = [v for v in todas if es_relevante(v) and v["id"] not in seen]
    _k, dedup = set(), []
    for v in nuevas:
        clave = (v["titulo"].lower().strip() + "|" + v["empresa"].lower().strip())
        if clave not in _k:
            _k.add(clave)
            dedup.append(v)
    nuevas = dedup
    nuevas.sort(key=score_vacante, reverse=True)
    a_evaluar = nuevas[:MAX_EVALUAR]
    print(f"# {len(nuevas)} nuevas relevantes (evaluare {len(a_evaluar)})")

    enviados = 0
    if a_evaluar:
        with ThreadPoolExecutor(max_workers=EVAL_WORKERS) as ex:
            fits = list(ex.map(evaluar.evaluar_fit, a_evaluar))
        for v, fit in zip(a_evaluar, fits):
            seen.add(v["id"])
            aceptar = fit.get("aceptar", False)
            score = fit.get("fit_score", 0)
            print(f"# fit={score} aceptar={aceptar} | {v['titulo'][:45]}")
            if aceptar and score >= 6:
                notificar.enviar(_mensaje(v, fit), prefix=PREFIX)
                enviados += 1

    guardar_seen(seen)
    print(f"# {enviados} alertas [CAREER-LATAM] enviadas")
    print("# listo")


if __name__ == "__main__":
    main()
