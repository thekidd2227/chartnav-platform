# Phase 21A — Retina + Glaucoma Specialty Tracking Foundation

> **Status:** Implemented (this PR).
> **Type:** New backend migration (5 tables) + new router (11 endpoints) +
> new frontend panel mounted in Clinical / Ophthalmology tab + 31 backend
> tests + 8 frontend tests.
> **Builds on:** Phase 20B (Structured Data Layer), Phase 20C (Role-Based
> Dashboards), existing EyeDiagramPanel / RetinalDrawingCanvas /
> RetinalProposalReview / NoteWorkspace / ScribeSessionPanel.
> **Branch:** `feature/phase-21a-retina-glaucoma-specialty-tracking`.

This phase persists longitudinal, provider-reviewed retina and glaucoma
findings. The provider records the structured fields; ChartNav does not
diagnose, dose, place orders, send referrals, message patients, bill, or
grade severity automatically. Imaging file uploads and device
integrations remain Phase 21B scope.

## How this extends the existing clinical workflow

Phase 21A is purely additive. None of the existing components are
modified:

- `EyeDiagramPanel.tsx`, `RetinalDrawingCanvas.tsx`,
  `retinalAnnotations.ts`, `RetinalProposalReview.tsx` — untouched.
  The retinal-drawing surface keeps owning the OD/OS annotation
  artifact lifecycle (Phase 6A/19 contract).
- `services/chart_artifacts.py`, `services/retinal_proposals.py` —
  untouched. The deterministic proposal engine still owns
  rule-based finding extraction.
- `NoteWorkspace.tsx`, `ScribeSessionPanel.tsx`,
  `clinicalShortcuts.ts`, `quickComments.ts` — untouched. The note
  pipeline and shortcut/quick-comment libraries keep their existing
  contracts.
- `RoleDashboard.tsx` (Phase 20C) and the Phase 20B work-queue —
  untouched. Phase 21A does not yet feed counts into the role
  dashboards; that is deferred so Phase 20C stays stable.

What changes:

- A new `SpecialtyTrackingPanel.tsx` renders at the top of the
  Clinical tab inside `ClinicalTabbedWorkspace.tsx`, above the
  existing clinical-shortcut grid. The shortcut grid is unchanged.
- A new backend router exposes the 11 specialty endpoints under
  `/patients/{patient_id}/{retina,glaucoma}/...`.
- An Alembic migration adds 5 specialty tables.

## Data model — 5 tables

| Table | Purpose |
|---|---|
| `retina_tracking` | One row per (patient, eye, condition) capturing review state + provider assessment + follow-up cadence + last OCT / fundus dates. |
| `retina_injection_events` | Discrete anti-VEGF / steroid injection events. Created by clinician/admin/technician. |
| `glaucoma_tracking` | One row per (patient, eye) capturing glaucoma type, target IOP, latest IOP, cup/disc ratio, RNFL & VF status, medication plan, progression risk. |
| `glaucoma_iop_measurements` | Discrete IOP readings (OD or OS). Pydantic + DB CHECK enforce `0..80 mmHg`. |
| `glaucoma_visual_field_tests` | VF test history with reliability + progression flag + result summary. |

All five tables are `organization_id`-scoped, include
`created_by_user_id`, and use CHECK constraints for eye / review status
values (portable SQLite + Postgres). Migration:
`e6f7a8b9c0d1_phase_21a_specialty_tracking` (chains off the Phase 20C
`d5e6f7a8b9c0`).

`review_status` enum (where applicable): `draft`, `needs_review`,
`reviewed`, `archived`.

## API surface — 11 endpoints

All endpoints are mounted at the FastAPI app root via
`app.api.specialty_tracking.router` and follow the standard
`Depends(require_caller)` + `_resolve_patient_in_org` pattern.

| Method | Path | Role policy |
|---|---|---|
| GET | `/patients/{id}/retina` | admin / clinician / reviewer / technician |
| POST | `/patients/{id}/retina` | admin / clinician |
| PATCH | `/patients/{id}/retina/{record_id}` | admin / clinician |
| GET | `/patients/{id}/retina/injections` | admin / clinician / reviewer / technician |
| POST | `/patients/{id}/retina/injections` | admin / clinician / **technician** |
| GET | `/patients/{id}/glaucoma` | admin / clinician / reviewer / technician |
| POST | `/patients/{id}/glaucoma` | admin / clinician |
| PATCH | `/patients/{id}/glaucoma/{record_id}` | admin / clinician |
| GET | `/patients/{id}/glaucoma/iop` | admin / clinician / reviewer / technician |
| POST | `/patients/{id}/glaucoma/iop` | admin / clinician / **technician** |
| GET | `/patients/{id}/glaucoma/visual-fields` | admin / clinician / reviewer / technician |
| POST | `/patients/{id}/glaucoma/visual-fields` | admin / clinician / **technician** |

`front_desk` has no access (clinical surface). All cross-org reads /
writes return `404` (not `403`) preserving the no-existence-leak
invariant.

### Role rationale

- **admin / clinician** — full lifecycle (create + patch the
  longitudinal review row, create discrete events).
- **technician** — can create *measurement events* (IOP readings,
  visual-field tests, injection events) since they are the operator
  capturing those readings. Cannot create or patch the longitudinal
  review row, since that records the clinician's assessment.
- **reviewer** — read-only across all five resources.
- **front_desk** — no access. The panel renders a blocked-state
  placeholder for front desk; the API returns `403
  specialty_role_forbidden`.

## Audit guarantee

Every create / patch records a metadata-only audit row via
`audit_record(...)`. The `detail` string contains **only** record IDs,
patient ID, eye, review status, and field-change list. The following
clinical body fields are **NEVER** included in audit detail:

- `provider_assessment` (retina + glaucoma)
- `injection_history_summary` (retina)
- `notes` (retina injection events)
- `medication_plan` (glaucoma)
- `result_summary` (visual field tests)
- `rnfl_status`, `visual_field_status` text

`TestRetinaTracking.test_audit_excludes_clinical_body`,
`TestGlaucomaTracking.test_audit_excludes_clinical_body`, and
`TestVisualFields.test_audit_excludes_result_summary` enforce this
contract.

## Validation contract

- `eye` must be `OD`, `OS`, or `OU` (IOP measurements only allow
  `OD` / `OS` — DB CHECK + Pydantic enforce). Invalid values return
  `400 invalid_eye`.
- `review_status` must be in the enum set. Invalid returns
  `400 invalid_review_status`.
- `iop_value` is range-checked at both the Pydantic schema layer
  (`ge=0, le=80`) and the DB layer (CHECK `iop_value >= 0 AND
  iop_value <= 80`).
- `cup_to_disc_ratio` is Pydantic-bounded `0..1`.
- `target_iop` / `latest_iop` Pydantic-bounded `0..80`.

## Frontend

### `apps/web/src/api.ts`

Adds:

- 9 types: `SpecialtyEye`, `SpecialtyEyeOdOs`,
  `SpecialtyReviewStatus`, `RetinaTrackingRecord`,
  `RetinaInjectionEvent`, `GlaucomaTrackingRecord`,
  `GlaucomaIopMeasurement`, `GlaucomaVisualFieldTest`,
  `SpecialtyListResponse<T>`.
- 5 input types: `RetinaTrackingCreateInput`,
  `RetinaTrackingUpdateInput`, `RetinaInjectionCreateInput`,
  `GlaucomaTrackingCreateInput`, `GlaucomaTrackingUpdateInput`,
  `GlaucomaIopCreateInput`, `GlaucomaVisualFieldCreateInput`.
- 12 typed functions:
  `listPatientRetinaTracking`,
  `createPatientRetinaTracking`,
  `updatePatientRetinaTracking`,
  `listPatientRetinaInjections`,
  `createPatientRetinaInjection`,
  `listPatientGlaucomaTracking`,
  `createPatientGlaucomaTracking`,
  `updatePatientGlaucomaTracking`,
  `listPatientGlaucomaIopMeasurements`,
  `createPatientGlaucomaIopMeasurement`,
  `listPatientGlaucomaVisualFields`,
  `createPatientGlaucomaVisualField`.

### `apps/web/src/SpecialtyTrackingPanel.tsx`

Single self-contained component:

- Retina section: list of retina cards (eye / condition / severity /
  OCT / fundus / follow-up / injection history summary / provider
  assessment + status select + Mark reviewed button); a retina
  create form; a retina injection table + create form.
- Glaucoma section: list of glaucoma cards (eye / type / target IOP /
  latest IOP / cup-to-disc / RNFL / VF status / med plan /
  progression risk + status select + Mark reviewed button); a
  glaucoma create form; IOP measurements table + create form;
  Visual field tests table + create form.
- Role gating: clinician/admin see Add buttons. Technician sees
  measurement Add buttons only. Reviewer sees no Add buttons; each
  card renders explicit "Read-only — your role cannot update this
  record." Front desk renders a single blocked-state placeholder
  and never calls the API.
- Disclaimer subtitle: "ChartNav does not diagnose, dose, place
  orders, send referrals, message patients, or grade severity
  automatically."

### `apps/web/src/ClinicalTabbedWorkspace.tsx`

`ClinicalTab` now accepts `identity`, `me`, `encounter` props and
renders `SpecialtyTrackingPanel` at the top of the Clinical tab when
the encounter is linked to a native patient. The existing shortcut
grid is unchanged.

### `apps/web/src/styles.css`

Appends `~230` lines of `.specialty-tracking__*` styles using the
existing `--cn-*` palette. No new design tokens.

## Tests

### Backend — 31 tests (`tests/test_phase_21a_specialty_tracking.py`)

| Class | Coverage |
|---|---|
| `TestRetinaTracking` | clinician/admin CRUD, reviewer read-only, technician cannot create tracking row, front_desk fully blocked, invalid eye / review_status rejected, cross-org patient/record 404, audit excludes clinical body. |
| `TestRetinaInjections` | clinician + technician create, reviewer/front_desk blocked. |
| `TestGlaucomaTracking` | clinician CRUD, reviewer read-only, front_desk blocked, invalid eye / status rejected, cross-org 404, audit excludes clinical body. |
| `TestIopMeasurements` | clinician + technician create, OU rejected (OD/OS only), IOP value range, reviewer blocked. |
| `TestVisualFields` | clinician + technician create, audit excludes result summary. |
| `TestAuthRequired` | unauthenticated list returns 401. |

### Frontend — 8 tests (`test/SpecialtyTrackingPanel.test.tsx`)

- Empty states render with the right copy.
- Populated cards render values correctly.
- Clinician sees Add buttons.
- Reviewer sees read-only state with no Add buttons.
- Technician can add measurement events but not tracking rows.
- Front desk renders blocked placeholder (no API calls).
- Retina create form submits and refreshes.
- Forbidden-vocab scan: no diagnosis/order/referral/billing/messaging
  controls or copy outside the negative-assertion disclaimer.

## What is intentionally **NOT** in Phase 21A

- Imaging file uploads or DICOM ingest (Phase 21B).
- Device integrations (Humphrey, Topcon OCT, etc.).
- Autonomous diagnosis or severity grading.
- Auto-dosing / treatment recommendation.
- Automatic order placement.
- Automatic referral submission.
- Patient messaging.
- Billing / coding / claims / insurance.
- HIPAA compliance claims (Phase 23).
- Updates to chartnavmd.com.
- Updates to commercial decks or media.
- Real PHI.

## Why imaging file pipeline is Phase 21B

Imaging files require: DICOM/JPEG store, file-size + content-type
gating, vendor-side ingest webhooks, vendor identity mapping, image
viewers, and an annotation layer. That is a separate phase. Phase 21A
deliberately persists only the *structured* findings the provider
records, so the foundation can ship without that infrastructure. The
existing `EyeDiagramPanel` annotation surface (Phase 19I) continues to
own retinal-canvas review.

## Files touched

- `apps/api/alembic/versions/e6f7a8b9c0d1_phase_21a_specialty_tracking.py` (new)
- `apps/api/app/api/specialty_tracking.py` (new, ~720 lines)
- `apps/api/app/main.py` (router include)
- `apps/api/tests/test_phase_21a_specialty_tracking.py` (new, 31 tests)
- `apps/web/src/api.ts` (Phase 21A types/functions appended)
- `apps/web/src/SpecialtyTrackingPanel.tsx` (new, ~1000 lines)
- `apps/web/src/ClinicalTabbedWorkspace.tsx` (Clinical tab signature
  + SpecialtyTrackingPanel mount; shortcut grid unchanged)
- `apps/web/src/styles.css` (specialty-tracking CSS appended)
- `apps/web/src/test/SpecialtyTrackingPanel.test.tsx` (new, 8 tests)
- `docs/product/phase-21a-retina-glaucoma-specialty-tracking.md` (this file)

## Migration roundtrip

`e6f7a8b9c0d1` ran cleanly upgrade-head on a fresh SQLite DB locally.
Postgres parity is exercised by the CI `backend-postgres` job.

## Remaining limitations

- Specialty tracking is patient-scoped, not encounter-scoped beyond
  the optional `encounter_id` foreign key. Phase 22 will fold these
  rows into the work-queue and surface "review-needed" specialty
  counts into the doctor + reviewer dashboards.
- No specialty-specific quick-comment template is auto-applied yet.
- No CSV / FHIR export of specialty tracking yet.
- No imaging file references — the `last_oct_at` / `last_fundus_at`
  fields are dates only.
