"""Telegram Apply Engine — prefijos [APPLY] y [CAREER-LATAM]."""
import os
import time
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PREFIX = os.getenv("APPLY_PREFIX", "[APPLY]")
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

MAX_LEN = 4000


def enviar(texto, prefix=None):
    p = prefix or PREFIX
    if not texto.strip().startswith("["):
        texto = f"{p} {texto}"
    chunks = _split(texto, MAX_LEN)
    for chunk in chunks:
        _post(chunk)


def _split(texto, limit):
    if len(texto) <= limit:
        return [texto]
    parts, rest = [], texto
    while rest:
        if len(rest) <= limit:
            parts.append(rest)
            break
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut])
        rest = rest[cut:].lstrip()
    return parts


def _post(texto):
    for intento in range(4):
        try:
            r = requests.post(
                API,
                json={
                    "chat_id": CHAT_ID,
                    "text": texto,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if r.status_code == 429:
                espera = r.json().get("parameters", {}).get("retry_after", 3)
                time.sleep(espera + 1)
                continue
            r.raise_for_status()
            time.sleep(1.2)
            return
        except Exception as e:
            if intento < 3:
                time.sleep(3)
                continue
            print(f"# WARN telegram: {e}")
            return
