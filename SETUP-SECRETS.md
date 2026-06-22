# Setup seguro — Fellowship Radar (repo público)

> **Regla de oro:** las API keys **nunca** van en el código ni en commits.  
> Solo en **GitHub Secrets** (producción) o en variables de entorno **locales** (pruebas tuyas).

---

## Por qué es seguro subir el repo a GitHub (público)

| Qué se sube al repo | ¿Contiene secrets? |
|---------------------|-------------------|
| `.py`, workflows, `criterios_fellowships.txt` | **No** — solo leen `os.environ[...]` |
| `.github/workflows/*.yml` | **No** — usan `${{ secrets.NOMBRE }}` (GitHub inyecta en runtime, no se ven en el YAML) |
| `seen-fellowships.json` | **No** — solo IDs de programas ya vistos |
| `.env` | **Bloqueado** por `.gitignore` — no debe existir en el repo |

GitHub **enmascara** secrets en logs de Actions. Aun así: el código **no imprime** keys (solo nombres de modelos y títulos de programas).

**Aislamiento vs Job Radar:** usá secrets con nombre distinto (`NVIDIA_FELLOW_KEY_*`, no `NVIDIA_API_KEY`).

---

## Paso 1 — Crear repo en GitHub (público OK)

1. https://github.com/new → nombre `fellowship-radar` → **Public**
2. **No** marques "Add README" (ya tenés uno local)

```powershell
cd C:\Users\hecto\fellowship-radar
git commit -m "chore: setup inicial Fellowship Radar"
git remote add origin https://github.com/Hectorrll/fellowship-radar.git
git push -u origin main
```

Antes del push, verificá que no hay `.env`:

```powershell
git status
# No debe aparecer .env ni archivos con nvapi-
```

---

## Paso 2 — GitHub Secrets (Settings → Secrets and variables → Actions → New repository secret)

Creá **cada fila como secret separado** (nombre exacto, case-sensitive):

| Nombre del secret | Obligatorio | Valor (ejemplo de formato) | Notas |
|-------------------|-------------|----------------------------|-------|
| `NVIDIA_FELLOW_KEY_1` | **Sí** | `nvapi-...` | Key NVIDIA NIM dedicada a Fellowship |
| `NVIDIA_FELLOW_KEY_2` | No | `nvapi-...` | 2ª key = más RPM en screening |
| `NVIDIA_FELLOW_KEY_3` | No | `nvapi-...` | Activa Nivel 2 (Kimi/MiniMax) |
| `TELEGRAM_BOT_TOKEN` | **Sí** | token de **@hector_fellowship_radar_bot** | Bot **propio** de Fellowship (no el de Job Radar) |
| `TELEGRAM_CHAT_ID` | **Sí** | `8011462057` | Tu user ID de Telegram (chat privado con el bot) |

**Mínimo para producción:** `NVIDIA_FELLOW_KEY_1` + los 2 secrets de Telegram del bot **Fellowship**.

**NO reutilizar** en este repo los valores `TELEGRAM_*` del repo `job-radar` (`@radiojobrad_bot`). Job Radar y Fellowship Radar usan **bots distintos**, mismo dueño.

### Bot Fellowship (creado 2026-06-22)

| Dato | Valor |
|------|-------|
| Username | `@hector_fellowship_radar_bot` |
| Link | https://t.me/hector_fellowship_radar_bot |
| Token | Copiar del **último mensaje de @BotFather** en tu Telegram (no commitear) |
| Chat ID | `8011462057` (tu cuenta; ya enviaste `/start` al bot) |

Para pegar el token en GitHub sin dejarlo en historial de terminal:

```powershell
gh secret set TELEGRAM_BOT_TOKEN -R Hectorrll/fellowship-radar
gh secret set TELEGRAM_CHAT_ID -R Hectorrll/fellowship-radar
```

(Pega el token cuando `gh` lo pida; para chat ID: `8011462057`.)

---

## Paso 3 — Primera corrida en GitHub Actions

1. Repo → **Actions** → **Fellowship Radar** → **Run workflow**
2. Revisá el log:
   - Debe listar portales y conteos
   - Si falta un secret: error `# ERROR: falta NVIDIA_FELLOW_KEY_1`
   - Si hay match: Telegram con prefijo `[FELLOW]`

Calibración (opcional, manual):

1. Actions → **Comparar modelos Fellowships** → Run workflow  
2. Meta: ≥8/10 en golden-set

---

## Paso 4 — cron-job.org (disparo confiable, secret aparte)

El **PAT de GitHub** para cron-job.org **no va en el repo**. Solo en cron-job.org:

| Campo | Valor |
|-------|-------|
| URL | `https://api.github.com/repos/Hectorrll/fellowship-radar/actions/workflows/fellowship-radar.yml/dispatches` |
| Método | POST |
| Header | `Authorization: Bearer <TU_GITHUB_PAT>` |
| Header | `Accept: application/vnd.github+json` |
| Body | `{"ref":"main"}` |
| Schedule | Cada **12 h**, minuto **:15** UTC |

El PAT necesita scope `repo` (o fine-grained: Actions write en este repo).

**Job separado** del Job Radar (que dispara a `:37`).

---

## Prueba local (opcional, sin commitear keys)

**Opción A — variables en la sesión (recomendada, no deja archivo):**

```powershell
cd C:\Users\hecto\fellowship-radar
$env:NVIDIA_FELLOW_KEY_1 = "nvapi-pega-aqui"
$env:TELEGRAM_BOT_TOKEN = "pega-aqui"
$env:TELEGRAM_CHAT_ID = "pega-aqui"
python fellowship_radar.py
```

**Opción B — archivo `.env` local (gitignored):**

```powershell
Copy-Item .env.example .env
# Editá .env con Notepad — NUNCA git add .env
```

Si usás `.env` local, necesitás cargarlo manualmente (el radar no incluye `python-dotenv` a propósito — menos superficie de error en CI).

---

## Checklist antes de cada push

- [ ] `git status` — sin `.env`, sin `nvapi-` en archivos tracked
- [ ] No pegaste keys en `criterios_fellowships.txt`, README ni workflows
- [ ] Secrets solo en GitHub UI (o env local temporal)
- [ ] No hiciste `git push --force` sobre `main`
- [ ] No reseteaste `seen-fellowships.json` en producción

---

## Si una key se filtró por error

1. **Revocar** la key en build.nvidia.com / BotFather de inmediato
2. Generar key nueva → actualizar solo el secret en GitHub
3. **No** commitear la key vieja ni nueva

---

## Resumen

```
Código público en GitHub  →  sin secrets
GitHub Secrets            →  keys en runtime de Actions
cron-job.org              →  PAT aparte (no en repo)
Local                     →  $env:... o .env gitignored
```

Listo para que pegues las keys **solo en GitHub Secrets** y corras el workflow.
