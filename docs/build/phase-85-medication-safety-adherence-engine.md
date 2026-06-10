# Phase 85 — Ophthalmic Medication Safety & Adherence Engine

**Date:** 2026-06-10
**Branch:** `feature/phase-85-medication-safety-adherence`
**Base:** `main` after Phase 84 (`865c500`)
**Status:** Eighth Phase 2 Clinical Intelligence surface — provider-entered medication list + deterministic informational signals

## Purpose

Phase 85 introduces a provider-entered medication list (eye drops,
oral systemic agents, intravitreal anti-VEGF) plus refill events
and an allergy list, and surfaces four deterministic informational
signals at read time:

- **polypharmacy_count** — number of currently active medications.
- **preservative_burden** — sum of `dose_per_day` across active
  preservative-flagged drop medications.
- **refill_gap** — `today - (last_refill + expected_days_supply)`
  per active medication, when both refill history and expected
  days supply are on file.
- **allergy_matches** — literal substring matches between
  provider-entered allergy substances and provider-entered
  medication names / class codes / class labels.

**ChartNav does not prescribe.** Every row was entered by a
provider. ChartNav does not refill, does not auto-dose, does not
recommend medication changes, does not contact the pharmacy, does
not perform autonomous drug-interaction checking beyond a literal
substring match against the provider-entered allergy list, and
does not generate prescriptions. The refill-gap signal is
informational only — never blocks signing, never escalates, never
triggers a Tier 1 queue item.

## Schema

Three new tables (Alembic revision `c1e2f3a4b5c6`):

### `medications`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | auto |
| `organization_id` | int FK | scope |
| `patient_id` | int FK | required |
| `encounter_id` | int FK | nullable (admin-entered medications allowed) |
| `medication_name` | text | non-empty (CHECK) |
| `medication_class` | text | closed allowlist (CHECK) |
| `route` | text | drops / oral / intravitreal (CHECK) |
| `laterality` | text | OD / OS / OU / NA (CHECK) |
| `dose_per_day` | int | 0..24 (CHECK) |
| `preservative_flag` | bool | provider-entered yes/no |
| `started_on` / `discontinued_on` | date | nullable |
| `prescriber_user_id` / `prescriber_display_name` | int / text | nullable; supports external prescribers |
| `recorded_by_user_id` | int FK users | actor metadata |
| `recorded_at` / `created_at` / `updated_at` | datetime | server-set |

Closed allowlist for `medication_class`:

- `pgf2_analog`
- `beta_blocker`
- `alpha_agonist`
- `carbonic_anhydrase_inhibitor`
- `rho_kinase_inhibitor`
- `combination_drop`
- `steroid_drop`
- `nsaid_drop`
- `antibiotic_drop`
- `anti_vegf_intravitreal`
- `lubricant`
- `oral_systemic_other`

### `medication_refills`

| Column | Type | Notes |
|---|---|---|
| `id` / `organization_id` / `patient_id` / `medication_id` | int | scope + FKs |
| `encounter_id` | int FK | nullable |
| `refill_date` | date | required |
| `expected_days_supply` | int | 1..365 (CHECK) |
| `recorded_by_user_id` | int FK users | actor metadata |
| `recorded_at` / `created_at` / `updated_at` | datetime | server-set |

### `medication_allergies`

| Column | Type | Notes |
|---|---|---|
| `id` / `organization_id` / `patient_id` | int | scope + FKs |
| `substance` | text | non-empty (CHECK) |
| `reaction_type` | text | closed allowlist (CHECK) |
| `severity` | text | mild / moderate / severe (CHECK) |
| `recorded_by_user_id` | int FK users | actor metadata |
| `recorded_at` / `created_at` / `updated_at` | datetime | server-set |

Indexes: `(organization_id, patient_id)` everywhere;
`(medication_id, refill_date)` on refills;
`(patient_id, discontinued_on, started_on)` on medications.

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/medications` | required | any caller with patient access |
| `POST` | `/api/v1/encounters/{encounter_id}/medications` | required | admin / clinician |
| `PATCH` | `/api/v1/medications/{medication_id}/discontinue` | required | admin / clinician |
| `POST` | `/api/v1/medications/{medication_id}/refills` | required | admin / clinician |
| `POST` | `/api/v1/patients/{patient_id}/medication-allergies` | required | admin / clinician |

Cross-org returns 404 (no existence leak).

GET response includes:

- `medications[]` with `is_active`, `refill_gap` projection, and
  `refill_count`.
- `refills[]` — full refill history.
- `allergies[]`.
- `supported_medication_classes`, `supported_routes`,
  `supported_lateralities`, `supported_reaction_types`,
  `supported_severities` so the UI renders typed pickers without
  hard-coding.
- `signals` — `{polypharmacy_count, preservative_burden,
  refill_gaps[], allergy_matches[], insufficient_data}`.
- `disclosure` — verbatim boundary copy.

## Cross-phase integrations

### Phase 77 — Retina Visit Packet Export

Adds a `medication_safety_summary` block (metadata only, no
clinical narrative):

```jsonc
{
  "active_medication_count": 2,
  "preservative_burden": 3,
  "refill_gap_count": 1,
  "refill_gap_medication_ids": [42],
  "allergy_count": 1,
  "medication_classes_present": ["beta_blocker", "pgf2_analog"],
  "insufficient_data": false
}
```

### Phase 81 — Provider Action Item Queue

When a patient's active medications include at least one refill
gap, the queue surfaces a single **informational** item:

```jsonc
{
  "specialty_source": "medication",
  "category": "medication_refill_gap",
  "priority_bucket": "informational",
  "insufficient_data": false
}
```

**Never Tier 1.** The item disappears as soon as the provider
records a refresh refill that closes the gap.

### Phase 82 — Note Validation Rail

A single informational check per encounter:

| State | check_id | status |
|---|---|---|
| Active meds + no gaps | `medication:documented` | `pass` |
| Active meds + at least one refill gap | `medication:refill_gap` | `warning` |
| No active meds | `medication:missing` | `missing` |

`requires_provider_acknowledgement` is always `false`. **The
medication check never blocks signing** and never appears in
`acknowledgements_required`.

## Forbidden behaviors (verified)

- ChartNav does NOT prescribe.
- ChartNav does NOT refill.
- ChartNav does NOT dose.
- ChartNav does NOT recommend medication changes.
- ChartNav does NOT contact the pharmacy.
- ChartNav does NOT perform autonomous drug-interaction checking
  beyond a literal substring match against the
  provider-entered allergy list.
- The provider action queue item is informational only — never
  Tier 1.
- The note validation check is informational only — never blocks
  signing.
- The preservative-burden flag is **provider-entered**, not
  autonomously categorized.
- The packet export contains no clinical narrative — counts only.

## UI

New panel `apps/web/src/features/medications/MedicationSafetyPanel.tsx`
wired into the Overview tab of `ClinicalTabbedWorkspace`. The
panel shows:

- Polypharmacy / preservative-burden / refill-gap / allergy
  counters.
- Per-medication row with a refill-gap pill: **green** (On
  track), **amber** (Refill gap · Nd), **neutral** (No refill
  history / Discontinued).
- Class, route, laterality, dose/day, preservative-flag display.
- Last refill date + expected days supply when on file.
- "Mark discontinued" button (admin / clinician only via RBAC at
  the API layer).
- Allergy-match callout (red banner) when literal name/class
  substring matches an allergy.
- Three typed forms: medication, refill, allergy.
- Disclosure rendered verbatim from server.

WCAG 2.1 AA contrast preserved (palette inherited from Phases
76–84).

## Tests

Backend:

- `apps/api/tests/test_medications.py` — 30 tests covering
  POST + GET + PATCH discontinue + refills + allergies + RBAC +
  enum allowlists + signal arithmetic + cross-org 404 + safety
  canary.
- `apps/api/tests/test_medications_integrations.py` — 7 tests
  covering Phase 82 documented/missing/refill_gap, Phase 81
  queue surfaces + drops + never-Tier-1, Phase 77 packet
  embedding.

Web:

- `apps/web/src/test/MedicationSafetyPanel.test.tsx` — 14 tests
  (render, signals, empty, populated, allergy-match callout,
  POST medication + refill + allergy + discontinue PATCH, error
  banner, refresh, disclosure boundary copy, forbidden-phrase
  canary sweep).

## Smoke

- `npx tsc --noEmit` — clean.
- `npx vitest run` — 881/881 pass (up from 867).
- `pytest tests/test_medications.py
  tests/test_medications_integrations.py` — 37/37 pass.
- Cross-phase backend regression (test_disease_staging +
  integrations, test_provider_action_queue, test_note_validation,
  test_note_validation_acknowledgements, test_retina_visit_summary,
  test_retina_visit_packet, test_cataract_workflow,
  test_glaucoma_summary, test_anti_vegf_injections) — 160/160
  pass.
- All five safety scripts (`check_commercial_claims.sh`,
  `check_demo_claims.sh`, `check_website_claims.sh`,
  `test_claim_policy_fixtures.sh`, `check_runtime_safety.py`)
  pass.
- `git diff --check` — clean.

## Caveats

- `preservative_flag` is provider-entered. Phase 85 does NOT
  autonomously categorize whether a specific drop carries BAK or
  another preservative — that's a clinical knowledge call the
  provider makes when adding the row.
- `refill_gap` arithmetic clamps negative values to 0; the
  signal never reports a negative gap.
- `allergy_matches` uses literal case-insensitive substring
  matching against `medication_name`, `medication_class` code,
  and `medication_class_label`. It is NOT a full drug-drug
  interaction inference; ChartNav explicitly disclaims that
  capability in the response disclosure.
- The Phase 81 queue item for refill gaps triggers off any
  active medication with a closed gap — it does not distinguish
  between glaucoma drops and lubricants. This matches the
  Phase 81 contract that the queue surfaces operational
  signals without inferring clinical urgency.

## Recommended next phase

**Phase 86 — Subspecialty Adaptive Workspace.** A workspace
shell that adapts the Overview tab's panel ordering, default
filters, and visible cards to the encounter's
declared subspecialty context (retina vs glaucoma vs cataract
vs cornea), with operator-configurable preferences stored per
user. Safe-claims boundary: ChartNav does not auto-classify the
encounter, does not auto-route patients, does not infer
specialty from imaging, and does not change clinical content —
the adaptation reorders existing panels only.
