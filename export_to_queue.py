#!/usr/bin/env python3
"""Exporta matches de Job Radar (o JSON manual) a apply_queue.json.

Uso (tras descargar artifact 'top-matches' del workflow Job Radar):
  python export_to_queue.py --file top_matches.json
  python export_to_queue.py --file ../job-radar/top_matches.json --min-score 7

Formato de entrada (array) — compatible con top_matches.json del radar:
[
  {
    "id": "getonbrd-123",
    "titulo": "...",
    "empresa": "...",
    "url": "https://...",
    "descripcion": "...",
    "score": 9,
    "prioridad": "TOP",
    "motivo": "razon del match (opcional)",
    "fuente": "GetOnBrd"
  }
]
"""
import argparse
import json
import pathlib
import sys


QUEUE_FILE = pathlib.Path("apply_queue.json")


def cargar_queue():
    if QUEUE_FILE.exists():
        try:
            data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def ids_existentes(queue):
    return {item.get("id") for item in queue if item.get("id")}


def normalizar(item):
    vid = item.get("id") or item.get("vacante_id")
    url = item.get("url") or item.get("link", "")
    if not vid:
        vid = f"import-{hash(url + item.get('titulo', '')) & 0xFFFFFFFF:08x}"
    desc = item.get("descripcion", item.get("description", ""))[:4000]
    motivo = (item.get("motivo") or "").strip()
    if motivo and motivo not in desc:
        desc = (desc + "\n\n[Motivo radar] " + motivo).strip()[:4000]
    try:
        score_num = float(item.get("score", item.get("fit_score", 0)) or 0)
    except (TypeError, ValueError):
        score_num = 0
    return {
        "id": str(vid),
        "url": url,
        "titulo": item.get("titulo", item.get("title", "")),
        "empresa": item.get("empresa", item.get("company", "")),
        "descripcion": desc,
        "prioridad": item.get("prioridad") or ("TOP" if score_num >= 8 else "normal"),
        "estado": "pendiente",
        "fuente": item.get("fuente", "job-radar export"),
    }


def main():
    parser = argparse.ArgumentParser(description="Exportar matches a apply_queue.json")
    parser.add_argument("--file", "-f", required=True, help="JSON con array de vacantes")
    parser.add_argument("--min-score", type=float, default=6, help="Score minimo para encolar")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no escribir")
    args = parser.parse_args()

    src = pathlib.Path(args.file)
    if not src.exists():
        print(f"# ERROR: no existe {src}")
        sys.exit(1)

    matches = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(matches, list):
        print("# ERROR: el archivo debe ser un array JSON")
        sys.exit(1)

    queue = cargar_queue()
    existentes = ids_existentes(queue)
    agregados = 0

    for raw in matches:
        score = raw.get("score", raw.get("fit_score", 10))
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 10
        if score < args.min_score:
            continue
        item = normalizar(raw)
        if item["id"] in existentes:
            print(f"# skip duplicado: {item['id']}")
            continue
        queue.append(item)
        existentes.add(item["id"])
        agregados += 1
        print(f"# + {item['id']} | {item['titulo'][:50]}")

    print(f"# agregados={agregados} | cola total={len(queue)}")
    if not args.dry_run and agregados:
        QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"# guardado en {QUEUE_FILE}")
    elif args.dry_run:
        print("# dry-run — no se escribio apply_queue.json")


if __name__ == "__main__":
    main()
