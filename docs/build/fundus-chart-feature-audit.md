# Fundus Chart Feature Audit

**Date:** 2026-05-19
**Branch:** `claude/ai-fundus-charting-RDUN5`
**Scope:** Ophthalmology V1 — encounter-scoped AI fundus charting

## Existing retinal / fundus features found (pre-implementation)

| File | Description | Action |
|------|-------------|--------|
| `apps/api/app/api/eye_diagrams.py` | Patient-scoped eye diagram routes | Unchanged |
| `apps/api/app/services/retinal_proposals.py` | Rule-based finding proposals | Unchanged |
| `apps/api/app/services/chart_artifacts.py` | Generic chart artifact CRUD | Unchanged |
| `apps/web/src/RetinalDrawingCanvas.tsx` | SVG drawing canvas component | Unchanged |
| `apps/web/src/RetinalProposalReview.tsx` | Proposal review panel | Unchanged |

## New implementation (this branch)

| File | Purpose |
|------|---------|
| `apps/api/alembic/versions/e1f2a3041508_fundus_charts.py` | DB migration: `fundus_charts` table |
| `apps/api/app/services/fundus_chart_ai.py` | Deterministic findings parser → drawing JSON |
| `apps/api/app/services/fundus_chart_renderer.py` | SVG renderer (clock-hour math) |
| `apps/api/app/api/fundus_charts.py` | REST API (8 endpoints) |
| `apps/api/tests/test_fundus_charts.py` | Backend tests (unit + integration) |
| `apps/web/src/features/fundus/fundusTypes.ts` | TypeScript type definitions |
| `apps/web/src/features/fundus/fundusApi.ts` | API client |
| `apps/web/src/features/fundus/FundusChartRenderer.tsx` | SVG React component |
| `apps/web/src/features/fundus/FundusChartLegend.tsx` | Finding legend component |
| `apps/web/src/features/fundus/FundusChartEditor.tsx` | Editor with review/sign workflow |
| `apps/web/src/features/fundus/FundusChartPanel.tsx` | Top-level panel |

## Design decisions

- **Encounter-scoped** (not patient-scoped) — aligns with clinical workflow; separate from existing patient-scoped `eye_diagrams`.
- **No LLM required** — `rule_based_v1` is a deterministic regex parser; swap-friendly via `ai_model_name` field.
- **Audit events log no PHI** — only `chart_id`, `laterality`, `warning_count`.
- **AI never auto-signs** — doctor attestation (`attested: true`) is mandatory; `signed_at` is set only by the sign endpoint.
- **SQLite-compatible schema** — `VARCHAR` laterality/status columns, `INTEGER` PK with `AUTOINCREMENT`.
- **Org isolation** — every query filters by `organization_id`; cross-org returns 404.
