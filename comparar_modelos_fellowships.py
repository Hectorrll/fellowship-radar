"""Eval de modelos para fellowships — golden-set-fellowships.json (10 casos)."""
import os
import time
import json

import requests

KEY = os.environ.get("NVIDIA_FELLOW_KEY_1") or os.environ.get("NVIDIA_FELLOW_KEY_2")
if not KEY:
    raise SystemExit("# ERROR: falta NVIDIA_FELLOW_KEY_1")

BASE = "https://integrate.api.nvidia.com/v1"

with open("criterios_fellowships.txt", encoding="utf-8") as f:
    CRITERIOS = f.read()

with open("golden-set-fellowships.json", encoding="utf-8") as f:
    GOLDEN_RAW = json.load(f)

GOLDEN = [
    {**g, "esperado": g["esperado"]}
    for g in GOLDEN_RAW
]

TARGETS = [
    "llama-4-maverick",
    "kimi-k2.6",
    "minimax-m3",
]

FALLBACK_IDS = {
    "llama-4-maverick": "meta/llama-4-maverick-17b-128e-instruct",
    "kimi-k2.6": "moonshotai/kimi-k2.6",
    "minimax-m3": "minimaxai/minimax-m3",
}


def resolver_ids():
    resolved = {}
    ids = []
    try:
        r = requests.get(f"{BASE}/models", headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("data", [])]
    except Exception as e:
        print(f"# WARN /v1/models ({e}); uso fallback IDs")
    for t in TARGETS:
        match = [i for i in ids if t in i.lower()]
        resolved[t] = match[0] if match else FALLBACK_IDS.get(t)
    return resolved


def evaluar_con(modelo, v):
    prompt = (
        f"{CRITERIOS}\n\nPROGRAMA A EVALUAR:\n"
        f"Titulo: {v['titulo']}\nOrganizacion: {v['empresa']}\nUbicacion: {v['ubicacion']}\n"
        f"Fuente: {v['fuente']}\nDescripcion: {v['descripcion']}"
    )
    payload = {"model": modelo, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.1, "max_tokens": 500}
    t0 = time.monotonic()
    try:
        r = requests.post(f"{BASE}/chat/completions",
                          headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
                          json=payload, timeout=90)
        dt = time.monotonic() - t0
        if r.status_code != 200:
            return {"ok": False, "lat": dt, "err": f"HTTP{r.status_code}", "json_ok": False, "verdict": None, "motivo": ""}
        content = r.json()["choices"][0]["message"]["content"].strip()
        ini, fin = content.find("{"), content.rfind("}")
        verdict, motivo, json_ok = None, "", False
        if ini != -1 and fin != -1:
            try:
                res = json.loads(content[ini:fin + 1])
                json_ok = True
                verdict = bool(res.get("aceptar"))
                motivo = str(res.get("motivo", ""))[:150]
            except Exception:
                pass
        return {"ok": True, "lat": dt, "err": "", "json_ok": json_ok, "verdict": verdict, "motivo": motivo}
    except Exception as e:
        return {"ok": False, "lat": time.monotonic() - t0, "err": str(e)[:45], "json_ok": False, "verdict": None, "motivo": ""}


def main():
    resolved = resolver_ids()
    print(f"# Golden set fellowships: {len(GOLDEN)} casos")
    print("# IDs:")
    for t, mid in resolved.items():
        print(f"#   {t} -> {mid}")

    mejor_modelo = None
    mejor_score = -1

    for t in TARGETS:
        modelo = resolved[t]
        if not modelo:
            continue
        print(f"\n===== {t} ({modelo}) =====")
        aciertos, jsons = 0, 0
        for i, g in enumerate(GOLDEN):
            res = evaluar_con(modelo, g)
            time.sleep(2.5)
            jsons += 1 if res["json_ok"] else 0
            correcto = res["ok"] and res["json_ok"] and (res["verdict"] == g["esperado"])
            aciertos += 1 if correcto else 0
            mark = "OK " if correcto else "XX "
            exp = "ACEPT" if g["esperado"] else "DESC "
            got = "ACEPT" if res["verdict"] else ("DESC " if res["verdict"] is False else "---- ")
            print(f"  [{i+1:2}] esp={exp} got={got} {mark} | {g['titulo'][:40]} -> {res['motivo']}")
        print(f"  --- ACIERTOS {aciertos}/{len(GOLDEN)} | json_ok {jsons}/{len(GOLDEN)} ---")
        if aciertos > mejor_score:
            mejor_score = aciertos
            mejor_modelo = t

    print(f"\n# Mejor modelo: {mejor_modelo} ({mejor_score}/{len(GOLDEN)})")
    if mejor_score >= 8:
        print("# PASS: >= 8/10 aciertos — listo para producción")
    else:
        print("# FAIL: ajustar criterios_fellowships.txt y re-ejecutar")


if __name__ == "__main__":
    main()
