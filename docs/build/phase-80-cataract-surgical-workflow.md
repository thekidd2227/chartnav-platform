# Phase 80 — Cataract Surgical Workflow

**Date:** 2026-06-09
**Branch:** `feature/phase-80-cataract-surgical-workflow`
**Base:** `main` at `c989c37` (after Phase 79)
**Status:** Third Phase 2 Clinical Intelligence surface

## Purpose

Provider-entered structured workflow support for cataract surgery:
pre-op readiness signals (planned surgery date, biometry-reviewed,
topography-reviewed, consent status), post-op cadence checkpoints
(day 1 / week 1 / month 1 statuses), provider-entered complication
flag + free-text fields (target refraction, lens plan label,
complication note, internal notes).

**This is provider-entered workflow support — not clinical decision
support.** ChartNav does **not**:

- select an IOL power, model, or material
- recommend a surgical technique (phaco / ECCE / FLACS)
- recommend a surgery date or sequencing across eyes
- infer complications from biometry / topography / imaging
- autonomously order tests, refer, message patients, or bill / code
- autonomously sign anything

Every value is what the provider entered. Free-text fields are stored
verbatim and shown only on the per-record view; the cockpit summary
deliberately omits them so deterministic projections never aggregate
clinical free text.

## Schema

**New table** `cataract_workflow_records` (one row per provider-entered
workflow snapshot, per `(patient_id, surgery_eye)`):

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | FK organizations | scoping |
| `patient_id` | FK patients | |
| `encounter_id` | FK encounters (nullable) | |
| `surgery_eye` | string CHECK (`OD`, `OS`) | |
| `planned_surgery_date` | date (nullable) | provider-entered |
| `biometry_study_id` | FK imaging_studies (nullable) | must reference `modality='biometry_packet'` for this patient |
| `biometry_reviewed` | bool, default false | provider attestation |
| `topography_reviewed` | bool, default false | provider attestation |
| `consent_status` | string CHECK (5-value allowlist) | `not_obtained` / `in_progress` / `signed` / `declined` / `unknown` |
| `target_refraction` | string ≤64 (nullable) | provider-entered text |
| `lens_plan_label` | string ≤160 (nullable) | provider-entered text |
| `postop_day_1_status` | string CHECK (5-value allowlist) | `not_scheduled` / `scheduled` / `completed` / `missed` / `unknown` |
| `postop_week_1_status` | same | |
| `postop_month_1_status` | same | |
| `complications_flag` | bool, default false | provider-entered |
| `complication_note` | text (nullable) | provider-entered |
| `notes` | text (nullable) | provider-entered |
| `created_by_user_id` | FK users | |
| `created_at` / `updated_at` | timestamptz | |

Three indexes: `(org, patient)`, `(patient, surgery_eye)`, `(org, planned_surgery_date)`.

Five CHECK constraints (`eye`, `consent_status`, three post-op statuses).

Migration `a9c0d1e2f3a4` descends from `f8b9c0d1e2f3` (Phase 78 head).

## Endpoints

| Method | Path | RBAC |
|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/cataract-workflow` | any authenticated role |
| `GET` | `/api/v1/patients/{patient_id}/cataract-workflow/records` | any authenticated role |
| `POST` | `/api/v1/patients/{patient_id}/cataract-workflow/records` | admin / clinician |

Technician / reviewer / front-desk **denied write** — cataract workflow
is provider-level, unlike Phase 78 anti-VEGF where technician can
write intake-style records.

Cross-org access returns 404 (no existence leak) on all three paths.

## Response — summary shape

```jsonc
{
  "patient_id": 1,
  "patient_identifier": "PT-1001",
  "patient_name": "Morgan Lee",
  "organization_id": 1,
  "generated_at": "2026-06-09T...",
  "demo_mode": true,
  "od": {
    "eye": "OD",
    "record_count": 1,
    "latest_record": {
      "id": 5, "encounter_id": 1, "surgery_eye": "OD",
      "planned_surgery_date": "2026-07-01",
      "biometry_study_id": 7, "biometry_reviewed": true, "topography_reviewed": true,
      "consent_status": "signed",
      "postop_day_1_status": "completed",
      "postop_week_1_status": "scheduled",
      "postop_month_1_status": "unknown",
      "complications_flag": false,
      "created_at": "...", "updated_at": "..."
    },
    "preop_readiness": {
      "has_planned_date": true, "biometry_reviewed": true,
      "topography_reviewed": true, "consent_signed": true,
      "score_numerator": 4, "score_denominator": 4
    },
    "postop_cadence": {
      "postop_day_1_status": "completed",
      "postop_week_1_status": "scheduled",
      "postop_month_1_status": "unknown",
      "score_numerator": 2, "score_denominator": 3
    },
    "complications_flag": false,
    "insufficient_data": false
  },
  "os": { ... same shape ... },
  "bilateral_planned": true,
  "disclosure": "Provider-entered cataract surgical workflow support. ChartNav does not select an IOL power, does not recommend a surgical technique, does not recommend a surgery date, does not infer complications, and does not order tests. Free-text fields (target refraction, lens plan, complication note, notes) are provider-entered and stored verbatim."
}
```

**The summary projection deliberately omits** `target_refraction`,
`lens_plan_label`, `complication_note`, and `notes`. The per-record
GET preserves them verbatim because the provider authored them.

## Frontend

| File | Description |
|---|---|
| `apps/web/src/features/cataract/cataractTypes.ts` | Typed shape mirroring backend response. |
| `apps/web/src/features/cataract/cataractApi.ts` | Fetch wrapper following identity-resolution pattern. |
| `apps/web/src/features/cataract/CataractSurgicalWorkflowPanel.tsx` | Two per-eye lanes with long-form labels (`OD · Right Eye`, `OS · Left Eye`). Each lane renders: pre-op readiness card (planned date / biometry / topography / consent status pill with tone) with `N/4` signals score, post-op cadence card with three checkpoint rows (Day 1 / Week 1 / Month 1) and `N/3` checkpoints score, complications-flag amber callout when set. Empty lanes render an explicit `Insufficient data` red callout. |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Wires the panel into the Overview tab right after the Glaucoma cockpit. |
| `apps/web/src/test/CataractSurgicalWorkflowPanel.test.tsx` | 12 vitest cases. |

WCAG 2.1 AA contrast carried forward from Phases 76/77/78/79.

## Metadata-only invariant

The summary projection omits four free-text columns; the test
`test_summary_projection_omits_provider_entered_free_text` writes
canary tokens into `target_refraction` / `lens_plan_label` /
`complication_note` / `notes` and asserts none of them appear in the
serialized summary JSON. The same test confirms the per-record GET
*does* preserve them verbatim (provider authored).

A second canary test sweeps for forbidden phrasings (`iol power 22`,
`phaco recommended`, `flacs recommended`, `surgery scheduled by
chartnav`, `automatic billing`, etc.) and asserts none appear in the
summary response.

The frontend mirrors both invariants with its own DOM-sweep test.

## Phase 2 progression

| Phase | Surface | Pattern |
|---|---|---|
| 78 | Anti-VEGF Retina Operating Rail | Bilateral injection cadence + readiness queue + auth |
| 79 | Glaucoma Progression Cockpit | Per-eye IOP + VF + OCT aggregator |
| 80 | **Cataract Surgical Workflow** | **Per-eye pre-op + post-op cadence + provider-entered plan** |

All three surfaces follow identical discipline:

- Aggregate structured data the provider entered
- Classify into deterministic operational signals (`N/M` scoring)
- Flag missing data honestly (`insufficient_data`)
- Never interpret, never recommend, never autonomously act
- Free-text provider-entered fields are surfaced verbatim on per-record
  views but omitted from aggregator projections

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_cataract_workflow.py -v` | **17 / 17 PASS** |
| Targeted regression (7 suites: cataract + glaucoma + anti_vegf + retina_visit_summary + retina_visit_packet + vitals + clinical) | **111 / 111 PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 830 / 830 tests across 47 files** (was 818; +12 Phase 80) |
| `bash scripts/check_commercial_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/check_demo_claims.sh` | **PASS** — 0 hits |
| `bash scripts/check_website_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/test_claim_policy_fixtures.sh` | **PASS** |
| `python3 scripts/check_runtime_safety.py` | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox).

## Caveats

- New schema (`cataract_workflow_records`) extends the alembic chain
  from `f8b9c0d1e2f3` (Phase 78 head) → `a9c0d1e2f3a4` (Phase 80 head).
- `biometry_study_id` is validated against `imaging_studies` rows with
  `modality='biometry_packet'` and matching patient+org; mis-targeted
  refs return `biometry_study_not_found` 404.
- POST requires admin or clinician — cataract workflow is
  provider-level. This is stricter than Phase 78 anti-VEGF (which
  allows technician for intake-style records).
- `WorkflowError` is non-frozen dataclass (same reason as Phase 78
  `InjectionError`: `engine.begin()` rollback sets `__traceback__`,
  which `frozen=True` blocks).

## Next phase recommendation

**Phase 81 — Provider Action Item Queue (Cross-Specialty).** Aggregate
the operational signals from Phases 78–80 (anti-VEGF readiness, glaucoma
modality completeness, cataract pre-op + post-op cadence) into a single
provider-facing action queue with deterministic per-eye prioritization.
Same boundary as 78/79/80: ChartNav surfaces what needs attention from
provider-entered data; it does not autonomously decide priority order
beyond the deterministic buckets it already exposes.
