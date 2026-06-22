"""Fetchers ATS LATAM — Greenhouse, Lever, Ashby (APIs publicas JSON). Sin imports de job-radar."""
import json
import pathlib
import re

import requests

_session = requests.Session()
HEADERS = {"User-Agent": "ApplyEngine-LATAM/1.0 (personal job search; hectorrodase04@gmail.com)"}
TIMEOUT = 25
MAX_DESC = 6000
TARGETS_FILE = pathlib.Path("latam_targets.json")


def _limpiar(html_text):
    if not html_text:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(html_text))
    return re.sub(r"\s+", " ", t).strip()


def _get_json(url):
    try:
        r = _session.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"# WARN latam fetch {url}: {e}")
        return None


def load_targets():
    if not TARGETS_FILE.exists():
        return []
    return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))


def fetch_greenhouse(board, label):
    data = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
    if not isinstance(data, dict):
        return []
    jobs = []
    for j in data.get("jobs") or []:
        locs = j.get("location") or {}
        loc_name = locs.get("name", "") if isinstance(locs, dict) else str(locs)
        jobs.append({
            "id": f"latam-gh-{board}-{j.get('id')}",
            "titulo": j.get("title", ""),
            "empresa": label,
            "ubicacion": loc_name or "ver descripcion",
            "descripcion": _limpiar(j.get("content", ""))[:MAX_DESC],
            "link": j.get("absolute_url") or "",
            "url": j.get("absolute_url") or "",
            "fuente": f"Greenhouse LATAM ({label})",
        })
    return jobs


def fetch_lever(company, label):
    data = _get_json(f"https://api.lever.co/v0/postings/{company}?mode=json")
    if not isinstance(data, list):
        return []
    jobs = []
    for j in data:
        loc = j.get("categories", {}).get("location", "")
        desc = _limpiar(j.get("descriptionPlain", "") or j.get("description", ""))
        lists = j.get("lists") or []
        if lists:
            desc = " ".join(
                _limpiar(item.get("content", ""))
                for lst in lists for item in (lst.get("content") or [])
            ) or desc
        jobs.append({
            "id": f"latam-lever-{company}-{j.get('id', '')}",
            "titulo": j.get("text", ""),
            "empresa": label,
            "ubicacion": loc or "ver descripcion",
            "descripcion": desc[:MAX_DESC],
            "link": j.get("hostedUrl") or j.get("applyUrl", ""),
            "url": j.get("hostedUrl") or j.get("applyUrl", ""),
            "fuente": f"Lever LATAM ({label})",
        })
    return jobs


def fetch_ashby(board, label):
    data = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
    if not isinstance(data, dict):
        return []
    jobs = []
    for j in data.get("jobs") or []:
        loc = j.get("location", "")
        if isinstance(loc, dict):
            loc = loc.get("name", "")
        desc = _limpiar(j.get("descriptionPlain", "") or j.get("descriptionHtml", ""))
        jobs.append({
            "id": f"latam-ashby-{board}-{j.get('id', '')}",
            "titulo": j.get("title", ""),
            "empresa": label,
            "ubicacion": str(loc) or "ver descripcion",
            "descripcion": desc[:MAX_DESC],
            "link": j.get("jobUrl") or j.get("applyUrl", ""),
            "url": j.get("jobUrl") or j.get("applyUrl", ""),
            "fuente": f"Ashby LATAM ({label})",
        })
    return jobs


def fetch_all_targets():
    todas = []
    for t in load_targets():
        ats = t.get("ats", "")
        board = t.get("board", "")
        label = t.get("label", board)
        if not board:
            continue
        if ats == "greenhouse":
            lista = fetch_greenhouse(board, label)
        elif ats == "lever":
            lista = fetch_lever(board, label)
        elif ats == "ashby":
            lista = fetch_ashby(board, label)
        else:
            print(f"# WARN latam: ATS desconocido {ats}")
            continue
        print(f"#   - {label} ({ats}): {len(lista)}")
        todas.extend(lista)
    return todas
