# Phase 79 — Glaucoma Progression Cockpit

**Date:** 2026-06-09
**Branch:** `feature/phase-79-glaucoma-progression-cockpit`
**Base:** `main` at `1da7190` (after Phase 78)
**Status:** Second Phase 2 Clinical Intelligence surface

## Purpose

A per-eye aggregator surface for glaucoma workflow. Reads existing
structured data — IOP from `visit_vitals_workups`, visual-field / OCT
metadata from `imaging_studies` — and renders a single cockpit with
two lanes (OD, OS) showing IOP history, modality review state, and
data-completeness signals.

**This is workflow intelligence — not clinical interpretation.**

ChartNav does **not**:
- interpret IOP trends or classify progression (stable / slow / rapid)
- interpret visual-field studies or OCT scans
- diagnose glaucoma
- recommend medication, laser, or surgery
- autonomously order tests or escalate care
- invent measurements to fill missing-data gaps

The provider's measurements are the source of truth; the cockpit
surfaces what's there and explicitly flags `insufficient_data` where
it isn't.

## What changed

### Backend — pure aggregation, no schema change

| File | Kind | Description |
|---|---|---|
| `apps/api/app/services/glaucoma_summary.py` | New service | Joins `visit_vitals_workups` (IOP per eye, sorted DESC) + `imaging_studies` (visual_field_24_2 / 10_2 / oct_rnfl / oct_macula, eye filter accepts `eye='OU'` for bilateral studies). Returns per-eye lane with IOP history, modality summaries, data-completeness scoring, and `insufficient_data` flags. Cross-dialect ordering (no `NULLS LAST` — uses CASE for SQLite + Postgres parity). |
| `apps/api/app/api/glaucoma_summary.py` | New router | `GET /api/v1/patients/{patient_id}/glaucoma-summary`. Cross-org returns 404. |
| `apps/api/app/main.py` | Modified | Registers the new router. |
| `apps/api/tests/test_glaucoma_summary.py` | New | 10 pytest cases — baseline, IOP per-eye, eye-isolation, ordering, completeness, cross-org 404, unknown 404, unauth, disclosure language, forbidden-clinical-text canary. |

### Frontend

| File | Kind | Description |
|---|---|---|
| `apps/web/src/features/glaucoma/glaucomaTypes.ts` | New | Typed shape mirroring backend response. |
| `apps/web/src/features/glaucoma/glaucomaApi.ts` | New | Fetch wrapper using project identity-resolution pattern. |
| `apps/web/src/features/glaucoma/GlaucomaProgressionCockpit.tsx` | New | Two per-eye lanes (OD/OS) with long-form eye labels, IOP trend block, three modality rows (VF / OCT RNFL / OCT macula) with green/amber/red tone pills, completeness pill (`N / 3 signals`), insufficient-data callouts, refresh button, disclosure block. |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Modified | Wires the cockpit into the Overview tab after the Anti-VEGF panel, gated on `nativeEncounter && typeof patient_id === "number"`. |
| `apps/web/src/test/GlaucomaProgressionCockpit.test.tsx` | New | 13 vitest cases — baseline render, both lanes, insufficient data, completeness pill, IOP latest + trend, modality tones (Reviewed / Ready for review / Insufficient data), bilateral flag, disclosure copy, refresh interaction, error banner, forbidden-phrasings canary. |

## Endpoint

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/glaucoma-summary` | required | any authenticated role with patient access |

Cross-org access returns 404 (no existence leak).

## Response shape (excerpt)

```jsonc
{
  "patient_id": 1,
  "patient_identifier": "PT-1001",
  "patient_name": "Morgan Lee",
  "organization_id": 1,
  "generated_at": "2026-06-09T...",
  "demo_mode": true,
  "bilateral_data": true,
  "od": {
    "eye": "OD",
    "iop_history": [
      { "vitals_workup_id": 3, "eye": "OD", "value": 18, "method": "applanation",
        "status": "signed", "signed": true, "reviewed_at": "...", "signed_at": "...",
        "recorded_at": "..." }
    ],
    "latest_iop": { ... },
    "iop_count": 2,
    "visual_field": { "count": 2, "latest_id": 7, "latest_status": "reviewed",
                      "latest_captured_at": "...", "latest_reviewed_at": "...",
                      "latest_reviewed_by_user_id": 3, "insufficient_data": false },
    "oct_rnfl": { ... },
    "oct_macula": { ... },
    "data_completeness": { "has_iop": true, "has_visual_field": true,
                           "has_oct_rnfl": true,
                           "score_numerator": 3, "score_denominator": 3 },
    "insufficient_data": false
  },
  "os": { ... same shape ... },
  "disclosure": "ChartNav surfaces what the provider's measurements show. ChartNav does not interpret IOP trends, visual fields, or OCT scans. It does not classify glaucoma progression. It does not recommend medication, laser, or surgery. Missing data is shown as insufficient_data; values are never invented to fill gaps."
}
```

## Visual hierarchy on the cockpit

| State | Tone | When |
|---|---|---|
| `Reviewed` | Green (`#c6f6d5` / `#1c4532`) | imaging study has `latest_reviewed_at` |
| `Ready for review` / pending intermediate status | Amber (`#fed7aa` / `#7c2d12`) | study uploaded but not yet reviewed |
| `Insufficient data` | Red (`#fed7d7` / `#822727`) | no study in this modality OR no IOP recorded |
| Completeness pill `N/3` | Green when 2+, amber at 1, red at 0 | based on `score_numerator` |

WCAG 2.1 AA contrast pattern carried forward from Phases 76/77/78.

## Metadata-only invariant

The aggregator service deliberately **never selects** the `notes`
column on `imaging_studies` or `technician_notes` on
`visit_vitals_workups`. Per-modality projection includes only
metadata: `id`, `modality`, `eye`, `status`, `captured_at`,
`reviewed_at`, `reviewed_by_user_id`, `count`.

The backend test `test_response_contains_no_forbidden_clinical_phrases`
writes a canary note containing the phrase "concerned about
progression" and BP values, then asserts that none of those tokens
appear anywhere in the serialized cockpit response — plus a hard
allowlist sweep for `diagnosis confirmed`, `stage iii/iv`, `rapid
progression`, `surgery recommended`, `laser recommended`, etc.

The frontend test `does NOT render forbidden clinical/progression
phrases` does the same DOM sweep on the rendered cockpit.

## Phase 2 progression

Phase 2 Clinical Intelligence surfaces shipped so far:

| Phase | Surface | Pattern |
|---|---|---|
| 78 | Anti-VEGF Retina Operating Rail | Bilateral cadence + readiness queue + auth tracking |
| 79 | **Glaucoma Progression Cockpit** | **Per-eye IOP + VF + OCT aggregator + completeness signals** |

Both follow the same discipline: aggregate structured data the
provider entered, classify into deterministic operational buckets,
flag what's missing, never interpret, never recommend.

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_glaucoma_summary.py -v` | **10 / 10 PASS** |
| Targeted regression (6 suites: glaucoma + anti_vegf + retina_visit_summary + retina_visit_packet + vitals + clinical) | **94 / 94 PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 818 / 818 tests across 46 files** (was 805; +13 Phase 79) |
| `bash scripts/check_commercial_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/check_demo_claims.sh` | **PASS** — 0 hits |
| `bash scripts/check_website_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/test_claim_policy_fixtures.sh` | **PASS** |
| `python3 scripts/check_runtime_safety.py` | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox).

## Caveats

- No schema changes. All Phase 79 data is already structured in
  existing tables (`visit_vitals_workups` for IOP, `imaging_studies`
  for VF/OCT). The aggregator reads — it does not write.
- Initial draft used `ORDER BY captured_at DESC NULLS LAST` which is
  PostgreSQL-only. Corrected to `ORDER BY CASE WHEN captured_at IS
  NULL THEN 1 ELSE 0 END, captured_at DESC, id DESC` — works on both
  SQLite and Postgres.
- Imaging-study `eye` column includes `OU` (both eyes) per Phase 21B.
  The per-eye lane filter accepts `eye IN (:eye, 'OU')` so bilateral
  studies count toward both per-eye lanes.

## Next phase recommendation

**Phase 80 — Cataract Surgical Workflow.** Third Phase 2 surface. Pre-op
intervals tracking (last optical biometry → planned surgery date), IOL
calculation metadata aggregation (already in `imaging_studies` for
`biometry_packet`), post-op visit schedule cadence, complication
capture surface. Same boundary: ChartNav does not select an IOL power,
does not choose a surgical technique, does not autonomously order tests
or referrals. The workflow surfaces what the provider entered.
