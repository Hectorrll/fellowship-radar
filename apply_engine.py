"""Apply Engine — convierte cola manual en paquetes de aplicación Telegram [APPLY].
No busca vacantes; complementa Job Radar (descubrimiento vs acción).
"""
import html
import json
import pathlib

import evaluar_apply as evaluar
import notificar_apply as notificar

QUEUE_FILE = pathlib.Path("apply_queue.json")
SEEN_FILE = pathlib.Path("seen-apply.json")
MAX_POR_CORRIDA = int(__import__("os").getenv("APPLY_MAX_POR_CORRIDA", "5"))


def cargar_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def guardar_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_seen():
    data = cargar_json(SEEN_FILE, [])
    return set(data) if isinstance(data, list) else set()


def guardar_seen(seen):
    guardar_json(SEEN_FILE, sorted(seen))


def _vacante_desde_item(item):
    return {
        "id": item["id"],
        "titulo": item.get("titulo", ""),
        "empresa": item.get("empresa", ""),
        "url": item.get("url") or item.get("link", ""),
        "link": item.get("url") or item.get("link", ""),
        "descripcion": item.get("descripcion", ""),
        "prioridad": item.get("prioridad", "normal"),
        "fuente": item.get("fuente", "cola manual"),
    }


def _mensaje_telegram(v, fit, paq):
    url = v.get("url") or v.get("link", "")
    flags = paq.get("red_flags") or fit.get("red_flags") or []
    flags_txt = ", ".join(flags) if flags else "ninguno detectado"
    resumen = paq.get("resumen_es") or []
    bullets = "\n".join(f"  • {html.escape(str(b))}" for b in resumen[:5])
    checklist = paq.get("checklist") or []
    check_txt = "\n".join(f"  ☐ {html.escape(str(c))}" for c in checklist[:8])
    cover = paq.get("cover_en", "")
    pregunta = paq.get("pregunta_obligatoria", "")
    fit_score = paq.get("fit_score", fit.get("fit_score", "?"))
    veredicto = fit.get("veredicto", "?")
    reco = fit.get("recommendation", "?")
    voz = fit.get("voz_en", "?")
    remoto = fit.get("remoto", "?")
    skills = fit.get("skills", "?")
    exp = fit.get("experiencia", "?")
    carrera = fit.get("carrera", "?")

    strengths = paq.get("strengths") or []
    gaps = paq.get("gaps") or []
    kw = paq.get("keywords_coverage") or []
    str_txt = "\n".join(f"  ✓ {html.escape(str(s))}" for s in strengths[:4])
    gap_txt = "\n".join(f"  △ {html.escape(str(g))}" for g in gaps[:4])
    kw_lines = []
    for row in kw[:8]:
        if isinstance(row, dict):
            kw_lines.append(
                f"  · {html.escape(str(row.get('keyword', '')))}: "
                f"{html.escape(str(row.get('status', '')))}"
            )
        else:
            kw_lines.append(f"  · {html.escape(str(row))}")
    kw_txt = "\n".join(kw_lines)

    msg = (
        f"⚡ <b>DRAFT — revisar en Antigravity antes de enviar</b>\n\n"
        f"📋 <b>{html.escape(v['titulo'][:100])}</b>\n"
        f"🏢 {html.escape(v.get('empresa') or '—')}\n"
        f"📊 Fit: {fit_score}/10 · {html.escape(str(veredicto))} · "
        f"<b>{html.escape(str(reco))}</b>\n"
        f"📐 skills {skills} · exp {exp} · carrera {carrera}\n"
        f"🛂 voz_en: {html.escape(str(voz))} · remoto: {html.escape(str(remoto))}\n"
        f"🚩 Red flags: {html.escape(flags_txt)}\n"
        f"💡 {html.escape(str(fit.get('motivo', ''))[:200])}\n\n"
    )
    if str_txt:
        msg += f"<b>Strengths:</b>\n{str_txt}\n\n"
    if gap_txt:
        msg += f"<b>Gaps (honestos):</b>\n{gap_txt}\n\n"
    if kw_txt:
        msg += f"<b>Keywords:</b>\n{kw_txt}\n\n"
    msg += f"<b>Resumen (ES):</b>\n{bullets}\n\n"
    if pregunta:
        msg += f"<b>Pregunta sugerida:</b>\n{html.escape(pregunta)}\n\n"
    msg += f"<b>Checklist:</b>\n{check_txt}\n\n"
    msg += f"<b>Cover EN (draft):</b>\n<pre>{html.escape(cover[:2400])}</pre>\n\n"
    msg += f"📅 Follow-up: {html.escape(str(paq.get('follow_up_fecha', '')))}\n"
    msg += f"🔗 {html.escape(url)}"
    return msg


def main():
    seen = cargar_seen()
    queue = cargar_json(QUEUE_FILE, [])
    if not isinstance(queue, list):
        print("# ERROR: apply_queue.json debe ser array")
        return

    pendientes = [q for q in queue if q.get("estado", "pendiente") == "pendiente"]
    pendientes.sort(key=lambda x: (0 if x.get("prioridad") == "TOP" else 1))
    procesar = pendientes[:MAX_POR_CORRIDA]

    print(f"# APPLY ENGINE | pendientes={len(pendientes)} | procesando={len(procesar)}")
    print(f"# keys fast={len(evaluar.KEYS_FAST)} think={'si' if evaluar.tiene_think() else 'no'}")

    if not procesar:
        print("# cola vacia — agregar entradas en apply_queue.json")
        return

    enviados = 0
    for item in procesar:
        vid = item.get("id")
        if not vid:
            print("# WARN item sin id, skip")
            continue
        if vid in seen:
            item["estado"] = "hecho"
            print(f"# skip ya visto: {vid}")
            continue

        v = _vacante_desde_item(item)
        print(f"# procesando: {v['titulo'][:50]}")

        fit = evaluar.evaluar_fit(v)
        aceptar = fit.get("aceptar", True)
        print(f"# fit={fit.get('fit_score', '?')}/10 aceptar={aceptar} | {fit.get('motivo', '')[:60]}")

        paq = evaluar.generar_paquete(v, fit)
        notificar.enviar(_mensaje_telegram(v, fit, paq))

        seen.add(vid)
        item["estado"] = "hecho"
        item["fit_score"] = fit.get("fit_score")
        item["procesado_at"] = __import__("datetime").date.today().isoformat()
        enviados += 1

    guardar_seen(seen)
    guardar_json(QUEUE_FILE, queue)
    print(f"# {enviados} paquetes [APPLY] enviados a Telegram")
    print("# listo")


if __name__ == "__main__":
    main()
