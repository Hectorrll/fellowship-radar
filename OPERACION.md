# Operación — Fellowship Radar

> Flujo humano cuando cae un match `[FELLOW]` en Telegram.

## Cuando llega un match

1. **Verificar URL oficial** (5 min) — confirmar $0 upfront, sin ISA, sin tarjeta.
2. **Check geo + idioma** — ¿GT/LATAM remoto? ¿Exige voz EN? Si falla → descartar.
3. **Aplicar manual** — CV + portafolio (Job Radar, Conserje, AI Content QA). Cover EN con Antigravity.
4. **Registrar** en tracker del workspace: `bitacoras/dia-28/tracker-fellowships.md`
5. **Follow-up** — 7–14 días sin respuesta.

## Estados del tracker

`⬜ investigar` · `✅ encaja` · `📨 aplicado` · `🎓 en programa` · `💼 colocado` · `❌ descartado` · `🚩 scam`

## Revisión Tier B (cada 14 días, manual)

| Fuente | Qué revisar |
|--------|-------------|
| NVIDIA DLI | Workshops gratuitos nuevos |
| Google Grow | Financial aid certificates |
| Microsoft Learn | Scholarships / challenges |
| Platzi / 4Geeks / SoyHenry | Convocatorias beca |
| CONCYT Guatemala | Becas estado |

**Próxima revisión sugerida:** 2026-07-06

## Calibración periódica

```powershell
python comparar_modelos_fellowships.py
```

Meta: ≥8/10 en `golden-set-fellowships.json`. Si baja de 8, ajustar `criterios_fellowships.txt`.

## Paralelo Job Radar

Fellowship Radar = pipeline **mediano plazo** (upskilling gratis).  
Job Radar = ingreso **inmediato** — no pausar aplicaciones.
