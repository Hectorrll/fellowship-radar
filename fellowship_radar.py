"""Fellowship Radar 24/7 — becas y fellowships tech gratuitas.
Flujo: buscar -> prefiltrar -> dedup -> evaluar IA -> Telegram [FELLOW] -> guardar vistos.
Aislado de Job Radar (keys, seen, cron, prefijo Telegram).
"""
import os
import json
import html
import pathlib
from concurrent.futures import ThreadPoolExecutor

import portales_fellowships as portales
import evaluar_fellowships as evaluar
import notificar_fellowships as notificar

SEEN_FILE = pathlib.Path("seen-fellowships.json")
MAX_EVALUAR = int(os.getenv("FELLOW_MAX_EVALUAR", "30"))
EVAL_WORKERS = int(os.getenv("FELLOW_EVAL_WORKERS", "4"))
RESCATE_MAX = int(os.getenv("FELLOW_RESCATE_MAX", "10"))

KEYWORDS = portales.FELLOWSHIP_KEYWORDS

NICHO = [
    "fellowship", "scholarship", "bootcamp", "grant", "apprenticeship", "open source",
    "automation", "n8n", "python", "ai ", "llm", "data", "fully funded", "beca",
]

STUDY_SIGNALS = [
    "bootcamp", "scholarship", "fellowship", "apprenticeship", "cohort", "curriculum",
    "training program", "learn", "study", "certification program", "grant", "beca",
    "internship program", "tuition-free", "fully funded",
]

PLACEMENT_SIGNALS = [
    "placement", "job guarantee", "we hire", "hiring partner", "career service",
    "career support", "employability", "graduate hire", "hire graduates", "job after",
    "post-program", "talent pipeline", "job ready", "job offer", "placed in",
    "intern-to-hire", "intern to hire", "demo day", "recruiter", "colocación",
    "empleo al", "contratación", "job prep",
]

VOZ_SIGNALS = [
    "phone call", "video call", "fluent english", "verbal english", "spoken english",
    "standup", "zoom interview", "native english", "phone screen", "voice interview",
]
SPANISH_SIGNALS = ["español", "espanol", "spanish", "latam", "latin america", "guatemala"]
STIPEND_SIGNALS = ["stipend", "paid fellowship", "fully funded", "scholarship", "financial aid"]
FREE_SIGNALS = ["free", "no cost", "tuition-free", "100%", "fully funded", "gratis", "beca"]


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
    texto = (v["titulo"] + " " + v["descripcion"]).lower()
    if not any(k in texto for k in KEYWORDS):
        return False
    # Priorizar pipeline estudio → empleo (al menos señal de formación)
    tiene_estudio = any(s in texto for s in STUDY_SIGNALS)
    tiene_empleo = any(s in texto for s in PLACEMENT_SIGNALS)
    return tiene_estudio and (tiene_empleo or "fellowship" in texto or "bootcamp" in texto
                              or "scholarship" in texto or "apprenticeship" in texto)


def es_nicho(v):
    t = (v["titulo"] + " " + v["descripcion"]).lower()
    return any(k in t for k in NICHO)


def score_programa(v):
    texto = (v["titulo"] + " " + v["descripcion"] + " " + v.get("ubicacion", "")).lower()
    score = 0
    if es_nicho(v):
        score += 2
    if any(s in texto for s in STUDY_SIGNALS):
        score += 2
    if any(s in texto for s in PLACEMENT_SIGNALS):
        score += 4  # empleo al terminar = prioridad máxima
    if any(s in texto for s in SPANISH_SIGNALS):
        score += 1
    if any(s in texto for s in STIPEND_SIGNALS):
        score += 1
    if any(s in texto for s in FREE_SIGNALS):
        score += 2
    if any(s in texto for s in VOZ_SIGNALS):
        score -= 3
    if any(s in texto for s in portales.PENALTY_KEYWORDS):
        score -= 4
    return score


def tiene_ruta_empleo(v):
    texto = (v["titulo"] + " " + v["descripcion"]).lower()
    return any(s in texto for s in PLACEMENT_SIGNALS)


def _detectar_flags(v):
    texto = (v["titulo"] + " " + v["descripcion"]).lower()
    gratis = "sí" if any(s in texto for s in FREE_SIGNALS) else "verificar"
    estudio = "sí" if any(s in texto for s in STUDY_SIGNALS) else "verificar"
    empleo = "sí" if tiene_ruta_empleo(v) else "verificar"
    stipend = "sí" if any(s in texto for s in STIPEND_SIGNALS) else "no mencionado"
    return gratis, estudio, empleo, stipend


def _mensaje(v, motivo):
    gratis, estudio, empleo, stipend = _detectar_flags(v)
    return (
        f"🎓 <b>{html.escape(v['titulo'][:120])}</b>\n"
        f"🏛 {html.escape(v['empresa'] or '—')}\n"
        f"📍 {html.escape(v['ubicacion'])}\n"
        f"💰 Gratis: {gratis} | Estudio: {estudio} | Empleo al terminar: {empleo}\n"
        f"💵 Stipend: {stipend}\n"
        f"🔎 {html.escape(v['fuente'])}\n"
        f"💡 {html.escape(motivo)}\n"
        f"🔗 {html.escape(v['link'])}"
    )


def main():
    seen = cargar_seen()
    _kf = len(evaluar.KEYS_FAST)
    print("# FOCO: becas de estudio tech GRATIS + empleo/placement al terminar")
    print(f"# FELLOWSHIP RADAR | NIVEL 1: {evaluar.MODEL} | {_kf} key(s) fast")
    if evaluar.tiene_think():
        print(f"# NIVEL 2: {evaluar.THINK_MODEL} | {len(evaluar.KEYS_THINK)} key(s) think")
    else:
        print("# NIVEL 2: OFF (agregar NVIDIA_FELLOW_KEY_3 para activarlo)")

    with ThreadPoolExecutor(max_workers=max(1, len(portales.PORTALES))) as ex:
        resultados = list(ex.map(lambda f: f(), portales.PORTALES))
    todas = [v for lista in resultados for v in lista]
    for f, lista in zip(portales.PORTALES, resultados):
        nombre = lista[0]["fuente"] if lista else f.__name__.replace("fetch_", "")
        print(f"#   - {nombre}: {len(lista)}")
    print(f"# {len(todas)} listings fellowship de {len(portales.PORTALES)} fuentes")

    nuevas = [v for v in todas if es_relevante(v) and v["id"] not in seen]
    _k, _dedup = set(), []
    for v in nuevas:
        clave = (v["titulo"].lower().strip() + "|" + v["empresa"].lower().strip())
        if clave not in _k:
            _k.add(clave)
            _dedup.append(v)
    nuevas = _dedup
    nuevas.sort(key=score_programa, reverse=True)
    if nuevas:
        top = nuevas[0]
        print(f"# prioridad top: score={score_programa(top)} | {top['fuente']}: {top['titulo'][:50]}")
    print(f"# {len(nuevas)} nuevas relevantes (evaluare hasta {MAX_EVALUAR})")
    a_evaluar = nuevas[:MAX_EVALUAR]

    aceptadas, rechazadas = [], []
    if a_evaluar:
        with ThreadPoolExecutor(max_workers=EVAL_WORKERS) as ex:
            veredictos = list(ex.map(evaluar.evaluar_programa, a_evaluar))
        for v, ver in zip(a_evaluar, veredictos):
            estado = "ACEPTA" if ver["aceptar"] else "descarta"
            print(f"# [{estado}] {v['fuente']}: {v['titulo'][:45]} -> {ver['motivo'][:70]}")
            seen.add(v["id"])
            (aceptadas if ver["aceptar"] else rechazadas).append((v, ver))

    enviar = []
    if not evaluar.tiene_think():
        enviar = [(v, ver["motivo"]) for v, ver in aceptadas]
    else:
        rescatables = [par for par in rechazadas if es_nicho(par[0])][:RESCATE_MAX]
        with ThreadPoolExecutor(max_workers=EVAL_WORKERS) as ex:
            prof_acc = list(ex.map(lambda par: evaluar.evaluar_profundo(par[0]), aceptadas))
            prof_res = list(ex.map(lambda par: evaluar.evaluar_profundo(par[0]), rescatables))
        n_filtrados = 0
        for (v, ver), prof in zip(aceptadas, prof_acc):
            if prof and prof.get("motivo"):
                if not prof["aceptar"]:
                    n_filtrados += 1
                    continue
                motivo = "🧠 " + prof["motivo"]
            else:
                motivo = ver["motivo"]
            enviar.append((v, motivo))
        n_resc = 0
        for (v, ver), prof in zip(rescatables, prof_res):
            if prof and prof.get("aceptar"):
                n_resc += 1
                enviar.append((v, "🧠🆘 RESCATADO: " + prof["motivo"]))
        print(f"# Nivel 2: {len(aceptadas)} aceptados | filtro {n_filtrados} | rescate {n_resc}")

    if enviar:
        for v, motivo in enviar:
            notificar.enviar(_mensaje(v, motivo))
        print(f"# {len(enviar)} matches enviados a Telegram [FELLOW]")
    else:
        print(f"# 0 matches esta corrida (revisé {len(a_evaluar)})")

    guardar_seen(seen)
    print("# listo")


if __name__ == "__main__":
    main()
