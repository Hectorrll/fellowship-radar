"""Fetchers de becas/fellowships (APIs públicas, sin login).
Cada función devuelve: {id, titulo, empresa, ubicacion, descripcion, link, fuente}
"""
import re
import html
import time
import requests
import feedparser

HEADERS = {"User-Agent": "Mozilla/5.0 (fellowship-radar personal de Hector)"}
TIMEOUT = 30
MAX_DESC = 2500
_session = requests.Session()

FELLOWSHIP_KEYWORDS = [
    "fellowship", "apprenticeship", "bootcamp", "scholarship", "scholar",
    "grant", "stipend", "fully funded", "financial aid", "beca", "becado",
    "programa becado", "funded program", "trainee program", "internship program",
    "free cohort", "no cost", "100% scholarship", "tuition-free",
    # estudio → empleo
    "job placement", "hiring partner", "we hire", "hire graduates", "career service",
    "placement program", "intern-to-hire", "apprentice to hire", "job guarantee",
    "talent pipeline", "employability", "post-program", "career support",
]

PENALTY_KEYWORDS = [
    "income share", "isa ", "deferred tuition", "pay when you",
    "application fee", "enrollment fee", "non-refundable",
    "us citizen only", "us residents only", "must be us",
    "fluent spoken english", "native english speaker", "phone interview",
    "video interview", "daily standup", "hourly annotation", "per task",
]


def _get_json(url):
    try:
        r = _session.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"# WARN fetch {url}: {e}")
        return None


def _get_text(url):
    try:
        r = _session.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"# WARN fetch {url}: {e}")
        return None


def _limpiar(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def es_fellowship_listing(titulo, descripcion):
    texto = (titulo + " " + descripcion).lower()
    if not any(k in texto for k in FELLOWSHIP_KEYWORDS):
        return False
    if any(k in texto for k in PENALTY_KEYWORDS):
        return False
    return True


def _filtrar_fellowship(jobs):
    return [j for j in jobs if es_fellowship_listing(j["titulo"], j["descripcion"])]


def fetch_remoteok():
    data = _get_json("https://remoteok.com/api")
    if not isinstance(data, list):
        return []
    jobs = []
    for j in data:
        if not isinstance(j, dict) or "position" not in j or "id" not in j:
            continue
        jobs.append({
            "id": f"remoteok-{j.get('id')}",
            "titulo": j.get("position", "") or "",
            "empresa": j.get("company", "") or "",
            "ubicacion": j.get("location", "") or "Remoto",
            "descripcion": (j.get("description", "") or "")[:MAX_DESC],
            "link": j.get("url") or j.get("apply_url", "") or "",
            "fuente": "RemoteOK",
        })
    return _filtrar_fellowship(jobs)


def fetch_remotive():
    data = _get_json("https://remotive.com/api/remote-jobs?limit=100")
    if not isinstance(data, dict):
        return []
    jobs = []
    for j in data.get("jobs", []):
        jobs.append({
            "id": f"remotive-{j.get('id')}",
            "titulo": j.get("title", "") or "",
            "empresa": j.get("company_name", "") or "",
            "ubicacion": j.get("candidate_required_location", "") or "Remoto",
            "descripcion": _limpiar(j.get("description", ""))[:MAX_DESC],
            "link": j.get("url", "") or "",
            "fuente": "Remotive",
        })
    return _filtrar_fellowship(jobs)


def fetch_himalayas():
    data = _get_json("https://himalayas.app/jobs/api?limit=100")
    if not isinstance(data, dict):
        return []
    jobs = []
    for j in (data.get("jobs") or []):
        restr = j.get("locationRestrictions") or []
        ubic = ", ".join(restr) if restr else "Mundial"
        clave = j.get("guid") or j.get("id") or j.get("applicationLink", "")
        jobs.append({
            "id": f"himalayas-{clave}",
            "titulo": j.get("title", "") or "",
            "empresa": j.get("companyName", "") or "",
            "ubicacion": ubic,
            "descripcion": (j.get("excerpt", "") or j.get("description", "") or "")[:MAX_DESC],
            "link": j.get("applicationLink", "") or "",
            "fuente": "Himalayas",
        })
    return _filtrar_fellowship(jobs)


def fetch_hn():
    d = _get_json("https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=12")
    if not isinstance(d, dict):
        return []
    sid = None
    for h in (d.get("hits") or []):
        if "who is hiring" in (h.get("title", "") or "").lower() and h.get("objectID"):
            sid = int(h["objectID"])
            break
    if not sid:
        return []
    jobs = []
    for page in range(5):
        data = _get_json(f"https://hn.algolia.com/api/v1/search?tags=comment,story_{sid}&hitsPerPage=100&page={page}")
        if not isinstance(data, dict):
            break
        hits = data.get("hits") or []
        if not hits:
            break
        for h in hits:
            if h.get("parent_id") != sid:
                continue
            oid = h.get("objectID")
            txt = _limpiar(h.get("comment_text", ""))
            if not oid or not txt:
                continue
            primera = txt.split("\n")[0][:200]
            parts = [p.strip() for p in primera.split("|")]
            jobs.append({
                "id": f"hn-{oid}",
                "titulo": primera,
                "empresa": (parts[0][:80] if parts else ""),
                "ubicacion": (parts[2][:60] if len(parts) >= 3 else "ver descripcion"),
                "descripcion": txt[:MAX_DESC],
                "link": f"https://news.ycombinator.com/item?id={oid}",
                "fuente": "HN Who is Hiring",
            })
    return _filtrar_fellowship(jobs)


def fetch_opportunitydesk():
    """OpportunityDesk RSS — scholarships/fellowships feed."""
    jobs = []
    try:
        feed = feedparser.parse("https://opportunitydesk.org/feed/")
        for entry in (feed.entries or [])[:40]:
            titulo = entry.get("title", "") or ""
            link = entry.get("link", "") or ""
            desc = _limpiar(entry.get("summary", "") or entry.get("description", ""))[:MAX_DESC]
            eid = entry.get("id") or link
            slug = re.sub(r"[^a-z0-9]+", "-", titulo.lower())[:40]
            jobs.append({
                "id": f"oppdesk-{hash(eid) & 0xFFFFFFFF}",
                "titulo": titulo,
                "empresa": "",
                "ubicacion": "ver descripcion",
                "descripcion": desc or titulo,
                "link": link,
                "fuente": "OpportunityDesk",
            })
    except Exception as e:
        print(f"# WARN opportunitydesk: {e}")
    return _filtrar_fellowship(jobs)


PORTALES = [
    fetch_remoteok,
    fetch_remotive,
    fetch_himalayas,
    fetch_hn,
    fetch_opportunitydesk,
]
