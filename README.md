# Fellowship Radar — Becas y fellowships tech gratuitas

> Sistema **24/7 sin servidor** que monitorea becas, fellowships y bootcamps becados,
> los evalúa con **pipeline IA de dos niveles** (NVIDIA NIM) y avisa por Telegram con
> prefijo **`[FELLOW]`**. Proyecto **aislado** de [Job Radar](https://github.com/Hectorrll/job-radar).

**Stack:** Python · GitHub Actions · NVIDIA NIM (`NVIDIA_FELLOW_KEY_*`) · Telegram · cron-job.org  
**Regla de negocio:** Héctor paga **$0** para entrar. Stipend y empleo al final = opcionales.

---

## Aislamiento vs Job Radar

| | Job Radar | Fellowship Radar |
|---|-----------|------------------|
| Repo | `job-radar` | `fellowship-radar` |
| Keys NVIDIA | `NVIDIA_API_KEY_*` | `NVIDIA_FELLOW_KEY_*` |
| Dedup | `seen.json` | `seen-fellowships.json` |
| Cron | :37 hourly | :15 cada 12h |
| Telegram | normal | `[FELLOW]` |

**Cero imports cruzados** entre repos.

---

## Arquitectura

```
fuentes (5 Tier A) → keywords fellowship → dedup seen-fellowships.json
  → score → eval IA Maverick → thinking opcional → Telegram [FELLOW]
```

**Fuentes MVP:** RemoteOK, Remotive, Himalayas, HN Who is Hiring, OpportunityDesk RSS.

**Volumen:** `MAX_EVALUAR=30` por corrida.

---

## Setup (repo público — keys solo en GitHub Secrets)

**Las API keys no van en el código.** El repo puede ser público sin riesgo si seguís [`SETUP-SECRETS.md`](SETUP-SECRETS.md).

1. Push del repo a `github.com/Hectorrll/fellowship-radar`
2. GitHub → **Settings → Secrets → Actions** → crear `NVIDIA_FELLOW_KEY_1`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
3. Actions → **Fellowship Radar** → Run workflow

Mínimo: `NVIDIA_FELLOW_KEY_1` + Telegram (2 secrets).

Prueba local (keys en la sesión, no en archivos commiteados):

```powershell
cd C:\Users\hecto\fellowship-radar
pip install -r requirements.txt
$env:NVIDIA_FELLOW_KEY_1 = "nvapi-..."   # nunca git add
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
python fellowship_radar.py
```

Plantilla local: [`.env.example`](.env.example) (nombres solamente, sin valores).

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `fellowship_radar.py` | Orquestador |
| `portales_fellowships.py` | Fetchers Tier A |
| `evaluar_fellowships.py` | Pipeline IA (keys `NVIDIA_FELLOW_*`) |
| `criterios_fellowships.txt` | Perfil y dealbreakers |
| `seen-fellowships.json` | Memoria dedup |
| `golden-set-fellowships.json` | Calibración evaluador |
| `INVENTARIO-programas.md` | 40 programas verificados (Fase 1) |
| `comparar_modelos_fellowships.py` | Test ≥8/10 golden-set |

---

## Inventario y operación

- **Inventario:** [`INVENTARIO-programas.md`](INVENTARIO-programas.md) — 40 programas (2026-06-22).
- **Tracker humano:** [`bitacoras/dia-28/tracker-fellowships.md`](../Mi proyecto claude/bitacoras/dia-28/tracker-fellowships.md) en workspace principal.

---

## Calibración

```powershell
python comparar_modelos_fellowships.py
```

Meta: **≥8/10** aciertos en golden-set antes de confiar en producción.

---

*Fellowship Radar · Guatemala · pipeline mediano plazo (no reemplaza Job Radar para ingreso inmediato).*
