# Fundus Charting Workflow

ChartNav's AI-assisted fundus charting feature generates standardised retinal drawings from clinician-entered findings text.

## Clinical workflow

1. **Enter findings** — Clinician types free-text in the FundusChartPanel (e.g. `horseshoe tear at 10:30 OD, lattice from 5 to 7 OS near ora`).
2. **Generate chart** — `POST /api/v1/encounters/{id}/fundus-charts/generate` parses findings, returns `drawing_json` with clock-hour mapped elements and any warnings.
3. **Review warnings** — AI emits warnings for missing laterality, missing clock hour, or unrecognised findings. No clinical detail is ever invented.
4. **Render SVG** — `POST /api/v1/fundus-charts/{id}/render` produces a 200×200-unit SVG with concentric rings, clock-hour labels, and colour-coded finding overlays.
5. **Review** — Clinician (or admin) calls `POST /api/v1/fundus-charts/{id}/review`. Status → `reviewed`.
6. **Sign** — Clinician sends `{"attested": true}` to `POST /api/v1/fundus-charts/{id}/sign`. Status → `signed`. Signed charts are immutable.

## Security and privacy

- Audit events record `chart_id`, `laterality`, and `warning_count` only — findings text and drawing JSON are never stored in the audit log.
- Every request filters by `organization_id`; cross-org access returns 404.
- Only `admin` and `clinician` roles can create, update, review, or sign.

## Clock-hour coordinate system

- 12 o'clock = superior = top of diagram
- 3 o'clock = temporal (OD) / nasal (OS)
- Angle formula: `angle_deg = (h × 30 − 90) % 360`

## Zones

| Zone | Retinal region |
|------|----------------|
| `posterior_pole` | Optic disc, macula (innermost ring) |
| `equator` | Equatorial retina (middle ring) |
| `ora_serrata` | Peripheral retina, ora serrata (outermost ring) |

## AI model

The V1 model is `rule_based_v1` — a deterministic regex parser requiring no external API. It is swappable: implement a replacement and update `ai_model_name` in the generate endpoint. A future LLM-backed model would return the same `FundusChartGenerationResult` dataclass.
