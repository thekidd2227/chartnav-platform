# Phase 84 — Disease Staging Protocol Engine

**Date:** 2026-06-10
**Branch:** `feature/phase-84-disease-staging-protocol-engine`
**Base:** `main` after Phase 83
**Status:** Seventh Phase 2 Clinical Intelligence surface — deterministic provider-entered disease staging

## Purpose

Phase 84 introduces a closed-allowlist disease staging surface so
that providers can **record** the stage they assigned during the
visit, and so that downstream surfaces (Phase 76 retina visit
summary, Phase 77 packet export, Phase 81 provider action queue,
Phase 82 note validation rail) can show whether staging
documentation is present without inferring anything clinical.

**ChartNav does not stage disease.** Every value stored in the
`disease_stages` table was entered by a provider via the POST
endpoint. ChartNav does not interpret imaging, does not infer
progression, does not recommend treatment, does not recommend
surgery, does not recommend injections, does not recommend
medications, does not auto-generate a stage, and does not
escalate. The "progression_detected" flag is a pure equality
check on `current_stage != prior_stage` and changes nothing in
the persisted record.

## Schema

New table `disease_stages` (Alembic revision `b0d1e2f3a4b5`):

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | auto |
| `organization_id` | int FK | scope |
| `patient_id` | int FK | required |
| `encounter_id` | int FK | nullable (admin-entered staging allowed) |
| `diagnosis_code` | text | non-empty (CHECK) |
| `staging_system` | text | closed allowlist (CHECK) |
| `stage_value` | text | non-empty (CHECK) |
| `prior_stage` | text | nullable |
| `staged_at` | datetime | server-set on insert |
| `staged_by_user_id` | int FK | caller user id |
| `created_at` / `updated_at` | datetime | server-set |

Closed allowlist for `staging_system`:

- `amd_areds`
- `diabetic_etdrs`
- `glaucoma_poag`
- `keratoconus_amsler_krumeich`
- `dry_eye_dews`

Per-system stage values are enforced service-side (e.g. AMD AREDS
allows Category 1 through Category 4 only). The CHECK constraints
catch the system enum; the service catches stage-vs-system
mismatches with a `422 stage_value_invalid` body.

Indexes: `(organization_id, patient_id)`,
`(patient_id, diagnosis_code, staged_at desc)`,
`(encounter_id)`.

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/disease-staging` | required | any caller with patient access |
| `POST` | `/api/v1/encounters/{encounter_id}/disease-staging` | required | admin or clinician |

Cross-org returns 404 (no existence leak).

POST payload:

```jsonc
{
  "diagnosis_code": "h35.31",
  "staging_system": "amd_areds",
  "stage_value": "Category 3",
  "prior_stage": null
}
```

GET response includes:

- `records[]` — newest-first per patient, each carrying
  `staged_by_display_name`, `staged_by_role`,
  `progression_detected`, `elapsed_days_since_prior`,
  `staging_system_label`.
- `latest_by_diagnosis` — newest record per `diagnosis_code`.
  When the persisted `prior_stage` is null but an earlier row
  exists for the same `(patient, diagnosis_code)`, the service
  derives `prior_stage` and `progression_detected` by reading the
  next-to-latest row.
- `supported_systems[]` — code, label, and allowed stage values
  so the UI can render typed pickers without hard-coding the
  matrix.
- `disclosure` — verbatim boundary copy.

`progression_detected` is `null` for the first record on a
diagnosis; for subsequent records it is a strict equality check
(`current != prior`). The service never escalates or assumes
progression; the boolean is informational only.

## Cross-phase integrations

### Phase 76 — Retina Visit Summary

Adds a `disease_staging_summary` block to the response:

```jsonc
{
  "record_count": 2,
  "latest_by_diagnosis": [
    {
      "diagnosis_code": "h35.31",
      "staging_system": "amd_areds",
      "stage_value": "Category 4",
      "prior_stage": "Category 2",
      "progression_detected": true,
      "elapsed_days_since_prior": 90,
      "staged_at": "2026-06-10T04:00:00Z"
    }
  ],
  "insufficient_data": false
}
```

`audit_disclosure` was extended to mention the staging boundary
("ChartNav does not stage disease...").

### Phase 77 — Retina Visit Packet Export

The packet projection now embeds the same
`disease_staging_summary` block — metadata only, no clinical
narrative.

### Phase 81 — Provider Action Item Queue

When a patient has anti-VEGF activity or IOP records but no row
in `disease_stages`, the queue surfaces a single **informational**
item per patient:

```jsonc
{
  "specialty_source": "staging",
  "category": "staging_missing",
  "priority_bucket": "informational",
  "insufficient_data": true
}
```

**Never Tier 1.** Always informational/Low priority. The item
disappears as soon as any staging row is recorded for the patient.

### Phase 82 — Note Validation Rail

A single informational check per encounter:

| State | check_id | status |
|---|---|---|
| Patient has at least one staging row | `staging:documented` | `pass` |
| Patient has none | `staging:missing` | `missing` |

`requires_provider_acknowledgement` is always `false`. **The
staging check never blocks signing** and never appears in
`acknowledgements_required`.

## Forbidden behaviors (verified)

- ChartNav does NOT diagnose.
- ChartNav does NOT interpret imaging.
- ChartNav does NOT infer progression.
- ChartNav does NOT recommend treatment.
- ChartNav does NOT recommend surgery.
- ChartNav does NOT recommend injections.
- ChartNav does NOT recommend medications.
- ChartNav does NOT auto-generate a stage.
- ChartNav does NOT escalate.
- The provider action queue item is informational only — never
  Tier 1.
- The note validation check is informational only — never blocks
  signing.
- The packet export contains no clinical narrative.

## UI

New panel `apps/web/src/features/disease-staging/DiseaseStagingPanel.tsx`
wired into the Overview tab of `ClinicalTabbedWorkspace`. The
panel shows:

- Current stage per diagnosis (`stage_value`).
- Prior stage (when on file or derivable from history).
- Days since prior (`elapsed_days_since_prior`).
- Staging system label.
- Provider display name and role.
- Timestamp.
- Progression pill: **green** (Stage unchanged), **amber**
  (Stage changed), **neutral** (First stage on record). The color
  reflects the deterministic equality check ONLY — it is not
  clinical interpretation.
- A typed form to record a new stage (system select → stage
  select auto-filters per system → diagnosis code input → submit).
- The disclosure copy rendered verbatim from the server.

WCAG 2.1 AA contrast is preserved (palette inherited from
Phases 76–80).

## Tests

Backend:

- `apps/api/tests/test_disease_staging.py` — 18 tests
  (POST + GET + RBAC + enum allowlist + progression equality +
  cross-org 404).
- `apps/api/tests/test_disease_staging_integrations.py` — 6 tests
  (Phase 76 baseline + populated, Phase 77 packet, Phase 82
  validation, Phase 81 queue surfaces + drops staging item).

Web:

- `apps/web/src/test/DiseaseStagingPanel.test.tsx` — 12 tests
  (render, empty, populated, system-select filters stages, POST
  flow refetches, error banner, refresh, disclosure boundary
  copy, forbidden-phrase canary sweep).

## Smoke

- `npx tsc --noEmit` — clean.
- `npx vitest run` — 867/867 pass (up from 855).
- `pytest tests/test_disease_staging.py
  tests/test_disease_staging_integrations.py` — 24/24 pass.
- Cross-phase backend regression
  (`test_provider_action_queue.py`, `test_note_validation.py`,
  `test_note_validation_acknowledgements.py`,
  `test_retina_visit_summary.py`, `test_retina_visit_packet.py`,
  `test_cataract_workflow.py`, `test_glaucoma_summary.py`,
  `test_anti_vegf_injections.py`) — 99/99 pass.
- All five safety scripts (`check_commercial_claims.sh`,
  `check_demo_claims.sh`, `check_website_claims.sh`,
  `test_claim_policy_fixtures.sh`, `check_runtime_safety.py`)
  pass.
- `git diff --check` — clean.

## Caveats

- The `elapsed_days_since_prior` field is computed on read by
  subtracting the previous row's `staged_at` from the current
  row's `staged_at`. It is **not** persisted; the GET endpoint
  is the source of truth.
- The "first stage on record" tone is intentionally neutral
  rather than green so the UI doesn't suggest "no progression"
  on a single-row history (it only means: no prior to compare
  against).
- The provider action queue item triggers off retina or
  glaucoma activity. Cataract-only and dry-eye-only patients are
  not flagged for missing staging — this matches the Phase 81
  contract that the queue surfaces specialty-relevant work and
  does not nudge providers on every patient.

## Recommended next phase

**Phase 85 — Ophthalmic Medication Safety & Adherence Engine.**
A provider-entered medication list (drops, oral systemic agents)
with a metadata-only adherence ledger, allergy interaction
warnings (informational only, never blocking), and a refill
reminder surface that integrates with the Phase 81 queue at
informational priority. Safe-claims boundary: ChartNav does not
prescribe, does not refill, does not dose, does not interact-
check beyond the provider-entered allergy list, and does not
contact the pharmacy.
