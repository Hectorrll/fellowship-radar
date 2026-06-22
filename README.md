# Apply Engine (ex Fellowship Radar)

> **Repo repurposed 2026-06-22:** de buscador de becas → **máquina de aplicar** que complementa Job Radar.
> Bot Telegram: `@hector_fellowship_radar_bot` · Prefijos: `[APPLY]` · `[CAREER-LATAM]`

**Job Radar** descubre (~1200 vacantes/h) · **Apply Engine** convierte TOP matches en paquetes accionables.

---

## Componentes

| Componente | Qué hace | Trigger |
|----------|----------|---------|
| **Apply Engine** | Cola manual → fit + cover EN draft + checklist → Telegram `[APPLY]` | `workflow_dispatch` |
| **LATAM Career Watcher** | 120+ empresas ATS → alertas fit ≥6 → Telegram `[CAREER-LATAM]` | cron `:15` 06:15 y 18:15 UTC |
| **export_to_queue.py** | Importa matches Job Radar → `apply_queue.json` | Manual local |

**Becas:** pausadas. Manual 1×/mes con `INVENTARIO-programas.md` + Antigravity.

---

## Aislamiento vs Job Radar

| | Job Radar | Apply Engine (este repo) |
|---|-----------|--------------------------|
| Repo | `Hectorrll/job-radar` | `Hectorrll/fellowship-radar` |
| Keys NVIDIA | `NVIDIA_API_KEY_*` ×6 | `NVIDIA_FELLOW_KEY_*` ×3 |
| Telegram | `@radiojobrad_bot` | `@hector_fellowship_radar_bot` |
| Cron principal | `:37` hourly | LATAM `:15` 2×/día |

**Cero imports cruzados** entre repos.

---

## Arquitectura

```
apply_queue.json (manual o export) → apply_engine.py → Telegram [APPLY]
latam_targets.json → latam_career_watcher.py → Telegram [CAREER-LATAM]
```

Workflows becas (`fellowship-radar.yml`) **pausados** — conservar solo `workflow_dispatch` histórico.

---

## Setup

1. Secrets GitHub: `NVIDIA_FELLOW_KEY_1/2/3`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
2. Actions → **Apply Engine** → Run workflow (después de encolar en `apply_queue.json`)
3. Aplicar HOY: ver [`APPLY-NOW.md`](APPLY-NOW.md)

### Encolar vacante manual

Editar `apply_queue.json`:

```json
[
  {
    "id": "paired-4423140829",
    "url": "https://www.linkedin.com/jobs/view/4423140829",
    "titulo": "AI Automation Specialist LATAM",
    "empresa": "Paired",
    "prioridad": "TOP",
    "estado": "pendiente",
    "descripcion": "... pegar JD ..."
  }
]
```

### Export desde Job Radar

```powershell
python export_to_queue.py --file top_matches_export.json --min-score 7
```

Ver formato en [`top_matches_export.example.json`](top_matches_export.example.json).

### Prueba local

```powershell
cd C:\Users\hecto\fellowship-radar
pip install -r requirements.txt
$env:NVIDIA_FELLOW_KEY_1 = "nvapi-..."
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
python apply_engine.py
```

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `apply_engine.py` | Orquestador paquetes `[APPLY]` |
| `apply_queue.json` | Cola de vacantes a procesar |
| `evaluar_apply.py` | Fit + generación paquete (keys FELLOW) |
| `criterios_apply.txt` | Perfil empleo ES/async, dealbreakers voz EN |
| `notificar_apply.py` | Telegram `[APPLY]` / `[CAREER-LATAM]` |
| `seen-apply.json` | Dedup cola (no resetear) |
| `latam_career_watcher.py` | Watcher ATS LATAM |
| `latam_targets.json` | ~120 empresas objetivo |
| `seen-latam.json` | Dedup LATAM (no resetear) |
| `export_to_queue.py` | Bridge Job Radar → cola |

### Histórico becas (referencia manual)

| Archivo | Rol |
|---------|-----|
| `fellowship_radar.py` | Orquestador becas (legacy, cron pausado) |
| `INVENTARIO-programas.md` | 40 programas becas |
| `seen-fellowships.json` | Dedup becas (conservar) |

---

## Workflows GitHub Actions

| Workflow | Estado |
|----------|--------|
| `apply-engine.yml` | **Activo** — manual dispatch |
| `latam-career-watcher.yml` | **Activo** — cron 2×/día |
| `fellowship-radar.yml` | **Pausado** — schedule comentado |

---

## Reglas

- Covers NVIDIA = **DRAFT** — pulir en Antigravity Sonnet antes de enviar
- **NO** mezclar keys con job-radar
- **NO** resetear `seen-apply.json` / `seen-latam.json`
- Money-first: aplicar Paired/RemoteVA no espera al bot

---

*Apply Engine · Guatemala · complemento de Job Radar para ingreso rápido.*
