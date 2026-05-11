# Phase 21B — Ophthalmology Imaging Pipeline Foundation

> **Status:** Implemented (this PR).
> **Type:** New backend migration (3 tables) + new router (9 endpoints) +
> new frontend panel mounted in the Imaging tab + 28 backend tests +
> 8 frontend tests.
> **Builds on:** Phase 20B (Structured Data Layer), Phase 20C (Role-Based
> Dashboards), Phase 21A (Retina + Glaucoma Tracking), existing
> EyeDiagramPanel / RetinalDrawingCanvas / RetinalProposalReview /
> NoteWorkspace / ScribeSessionPanel.
> **Branch:** `feature/phase-21b-imaging-pipeline-foundation`.

This phase persists **metadata** for the device-derived imaging
studies that the practice captures upstream of ChartNav. It is a
metadata + review workflow layer — not an imaging system, not a
DICOM PACS, and not an integration with any specific device or
vendor. ChartNav stores study existence, modality, eye, status, file
references (URI only — no binaries), and structured measurement rows
that a clinician or technician types in. ChartNav does not interpret
images, diagnose, dose, place orders, send referrals, message
patients, or bill.

## How this extends the existing clinical workflow

Phase 21B is purely additive. None of the existing components are
modified:

- `EyeDiagramPanel.tsx`, `RetinalDrawingCanvas.tsx`,
  `retinalAnnotations.ts`, `RetinalProposalReview.tsx`,
  `services/chart_artifacts.py`, `services/retinal_proposals.py` —
  untouched. The OD/OS retinal canvas keeps owning annotated
  review. The Imaging tab continues to render the canvas below
  the new pipeline panel.
- `SpecialtyTrackingPanel.tsx` (Phase 21A) — untouched. The
  retina-tracking `last_oct_at` / `last_fundus_at` columns will
  in a later phase reference `imaging_studies.id`, but Phase 21B
  does not change Phase 21A's schema or surface.
- `NoteWorkspace.tsx`, `ScribeSessionPanel.tsx`,
  `clinicalShortcuts.ts`, `quickComments.ts` — untouched.
- `RoleDashboard.tsx` (Phase 20C) and the Phase 20B work-queue —
  untouched. Phase 21B does not feed counts into the dashboards
  yet (deferred to Phase 22 so 20C stays stable).

What changes:

- A new `ImagingPipelinePanel.tsx` renders at the **top** of the
  Imaging tab inside `ClinicalTabbedWorkspace.tsx`. The existing
  placeholder cards and the OD/OS retinal workbench remain
  unchanged below it.
- A new backend router exposes 9 endpoints for imaging studies,
  files, and measurements.
- An Alembic migration adds 3 imaging tables.

## Modality coverage (generic labels)

The migration's CHECK constraint and the Pydantic / TypeScript
enums use **generic** modality identifiers. No vendor-specific
device adapter ships in this phase. Supported labels:

| Identifier | Label |
|---|---|
| `oct_macula` | OCT macula |
| `oct_rnfl` | OCT RNFL |
| `fundus_photo` | Fundus photo |
| `widefield_fundus` | Widefield fundus |
| `visual_field_24_2` | Visual field 24-2 |
| `visual_field_10_2` | Visual field 10-2 |
| `biometry_packet` | Biometry packet |
| `external_pdf` | External PDF report |
| `other` | Other |

Vendor-specific identifiers (Cirrus / Spectralis / Triton / Optos /
IOLMaster / Topcon / Humphrey / etc.) are **not** used and are
forbidden anywhere in the shipped UI/API surface; the frontend tests
include an explicit forbidden-vocabulary scan.

## Data model — 3 tables

### `imaging_studies`

One row per device-derived imaging study attached to a patient
(optionally an encounter). Captures lifecycle status and review
provenance.

| Column | Notes |
|---|---|
| `id`, `organization_id`, `patient_id` | required |
| `encounter_id` | nullable — pre-visit imports / outside-image attachments |
| `modality` | CHECK-constrained to the generic enum above |
| `eye` | CHECK `OD` / `OS` / `OU` / `NA` |
| `status` | CHECK `pending_upload` / `uploaded` / `ready_for_review` / `reviewed` / `archived` |
| `captured_at` | datetime, nullable |
| `reviewed_by_user_id`, `reviewed_at` | provenance for the review act |
| `notes` | provider's review note, never serialized to audit |
| `created_by_user_id`, `created_at`, `updated_at` | |

### `imaging_files`

Per-study file **metadata only**. ChartNav stores no binaries; the
`storage_uri` is an opaque reference owned by the practice's storage
backend.

| Column | Notes |
|---|---|
| `study_id` | FK to `imaging_studies` |
| `file_kind` | CHECK `image` / `report_pdf` / `raw_export` |
| `storage_uri` | nullable opaque URI; data: URIs rejected by Pydantic |
| `file_name`, `content_type`, `size_bytes`, `checksum_sha256` | descriptive metadata |

The Pydantic input model rejects `data:image/...;base64,...`
URIs to ensure no one smuggles a binary into the metadata field.

### `imaging_measurements`

Structured measurement metadata. Values are stored as strings for
unit flexibility (`"240"` microns, `"0.6"` ratio, `"-3.4"` dB).

| Column | Notes |
|---|---|
| `study_id` | FK |
| `measurement_type` | free-text identifier (e.g. `central_macular_thickness`, `rnfl_thickness_avg`, `cup_to_disc_ratio`) |
| `eye` | CHECK `OD` / `OS` / `OU` / `NA` |
| `value`, `unit` | value as string + unit identifier |
| `source` | CHECK `manual` / `demo` / `imported_metadata` — **no** `auto_inferred` |

Migration revision: `f7a8b9c0d1e2_phase_21b_imaging_pipeline`
(chains off Phase 21A `e6f7a8b9c0d1`).

## API surface — 9 endpoints

| Method | Path | Role policy |
|---|---|---|
| GET | `/patients/{id}/imaging-studies` | admin / clinician / reviewer / technician |
| POST | `/patients/{id}/imaging-studies` | admin / clinician / **technician** |
| GET | `/imaging-studies/{id}` | admin / clinician / reviewer / technician |
| PATCH | `/imaging-studies/{id}` | admin / clinician / **technician** |
| PATCH | `/imaging-studies/{id}/review` | **admin / clinician only** |
| GET | `/imaging-studies/{id}/files` | admin / clinician / reviewer / technician |
| POST | `/imaging-studies/{id}/files` | admin / clinician / **technician** |
| GET | `/imaging-studies/{id}/measurements` | admin / clinician / reviewer / technician |
| POST | `/imaging-studies/{id}/measurements` | admin / clinician / **technician** |

`front_desk` has **no** access (clinical imaging surface). All
cross-org reads/writes return `404` (not `403`) preserving the
no-existence-leak invariant.

### Role rationale

- **admin / clinician** — full lifecycle: create, patch, mark
  reviewed.
- **technician** — creates the study metadata, the file metadata,
  and measurement rows (they're the operator capturing the
  upstream studies). Can patch a study but **cannot** mark it
  reviewed — review is the provider's act.
- **reviewer** — read-only across all three resources.
- **front_desk** — no access. The panel renders a blocked-state
  placeholder.

## Audit guarantee

Every create / patch / review records a metadata-only audit row.
`detail` contains only IDs, modality, eye, status, file kind, size
(bytes), measurement type, and source. The following clinical body
fields are **NEVER** included in audit detail:

- `notes` (imaging study)
- `storage_uri`, `file_name` (imaging file)
- `value` (imaging measurement)

Enforced by 3 dedicated tests
(`test_audit_excludes_clinical_body`,
`test_audit_excludes_storage_uri_and_file_name`,
`test_audit_excludes_measurement_value`).

## Frontend

### `apps/web/src/api.ts`

Adds 8 types (`ImagingModality`, `ImagingEye`, `ImagingStudyStatus`,
`ImagingFileKind`, `ImagingMeasurementSource`, `ImagingStudy`,
`ImagingFileMetadata`, `ImagingMeasurement`,
`ImagingListResponse<T>`) and 9 typed functions:

- `listPatientImagingStudies`
- `createPatientImagingStudy`
- `getImagingStudy`
- `updateImagingStudy`
- `markImagingStudyReviewed`
- `listImagingStudyFiles`
- `createImagingStudyFile`
- `listImagingStudyMeasurements`
- `createImagingStudyMeasurement`

### `apps/web/src/ImagingPipelinePanel.tsx`

Single self-contained component. Top half is a split: studies list
on the left, selected-study detail on the right. The detail pane
shows file-metadata table, measurements table, and a review
workbench with a Mark-reviewed button (admin/clinician only). Empty
states render explicit placeholder copy ("No imaging studies yet",
"No files recorded for this study", "No measurements recorded for
this study"). When the encounter has no native patient, the panel
renders an **unavailable** state and never calls the API. Front
desk renders a **blocked** state.

Disclaimer subtitle: *"Structured records of device-derived studies
the practice captures upstream. ChartNav stores metadata only — no
image binaries, no device integrations, no autonomous
interpretation, and no automatic orders, referrals, or patient
messaging."*

### `apps/web/src/ClinicalTabbedWorkspace.tsx`

`ImagingTab` now destructures `me` (previously unused) and mounts
`ImagingPipelinePanel` above the existing placeholder grid. The
placeholder cards (Upload imaging, OCT images, Fundus photos,
Attachments, Imaging notes, Selected image viewer) and the OD/OS
retinal workbench at the bottom are unchanged.

### `apps/web/src/styles.css`

Appends `~266` lines of `.imaging-pipeline__*` styles using the
existing `--cn-*` palette. No new design tokens.

## Connection to retina/glaucoma tracking (Phase 21A)

Phase 21A's retina tracking carries `last_oct_at` / `last_fundus_at`
date columns. Phase 21B persists the actual underlying imaging
studies those dates reference. The two surfaces sit side-by-side in
the Clinical tab (Phase 21A) and Imaging tab (Phase 21B). A later
phase will link `retina_tracking` to the most recent
`imaging_studies` row by patient + eye + modality; this PR does not
change the Phase 21A schema.

## Connection to EyeDiagramPanel / RetinalDrawingCanvas

The OD/OS retinal canvas already lives in the Imaging tab below the
new pipeline panel. A reviewer / clinician opens a study in the
pipeline panel, then uses the OD/OS workbench below to annotate
findings on the retinal canvas and sign them into the encounter
note. The pipeline panel renders an explicit hint pointing to that
workbench ("Open the OD/OS retinal diagram workbench below..."). No
data is mutated between the two surfaces in this phase.

## Tests

### Backend — 28 tests (`tests/test_phase_21b_imaging_pipeline.py`)

| Class | Coverage |
|---|---|
| `TestImagingStudies` | Clinician/admin CRUD; technician creates studies; admin reviews; reviewer/front_desk blocked appropriately; invalid modality / eye / status rejected; cross-org 404 on patient + study; audit excludes notes. |
| `TestImagingFiles` | Clinician + technician create file metadata; reviewer blocked; invalid `file_kind` rejected; **data: URI rejected** to prevent binary smuggling; audit excludes `storage_uri` + `file_name`; cross-org 404 on file create. |
| `TestImagingMeasurements` | Clinician + technician create; reviewer blocked; invalid `source` (`auto_inferred`) rejected; invalid eye rejected; audit excludes `value`. |
| `TestAuthRequired` | 401 on every unauthenticated entry point. |

### Frontend — 8 tests (`test/ImagingPipelinePanel.test.tsx`)

- Unavailable state when `patientId === null` (no API call).
- Front desk blocked state (no API call).
- Empty-studies placeholder for clinician.
- Populated rendering: studies list + selected-study files +
  measurements all render.
- Technician sees create buttons but **not** Mark reviewed.
- Reviewer sees no write controls.
- Mark-reviewed flow calls `markImagingStudyReviewed` and refreshes.
- Forbidden-vocabulary + button scan: no vendor names, no
  autonomous-interpretation language, no order / referral /
  patient-messaging / billing terms.

## Dashboard integration

**Deferred to Phase 22.** Phase 20C's dashboards are stable; folding
imaging counts into the doctor / technician / reviewer dashboards
would risk regression to that surface. This PR keeps the Phase 20C
dashboard contract unchanged.

## Out of scope (intentional)

- ❌ No real device integrations (Cirrus / Spectralis / Triton /
  Optos / IOLMaster / Topcon / Humphrey or any other vendor).
- ❌ No DICOM ingestion.
- ❌ No binary image storage (the route layer rejects `data:`
  URIs to enforce this).
- ❌ No autonomous image interpretation.
- ❌ No autonomous diagnosis.
- ❌ No automatic orders.
- ❌ No automatic referrals.
- ❌ No patient messaging.
- ❌ No billing / coding / claims / insurance.
- ❌ No HIPAA compliance claims.
- ❌ No `chartnavmd.com` updates.
- ❌ No commercial deck or media updates.
- ❌ No real PHI.

## Files touched

- `apps/api/alembic/versions/f7a8b9c0d1e2_phase_21b_imaging_pipeline.py` (new)
- `apps/api/app/api/imaging_pipeline.py` (new)
- `apps/api/app/main.py` (router include)
- `apps/api/tests/test_phase_21b_imaging_pipeline.py` (new, 28 tests)
- `apps/web/src/api.ts` (Phase 21B types/functions appended)
- `apps/web/src/ImagingPipelinePanel.tsx` (new)
- `apps/web/src/ClinicalTabbedWorkspace.tsx` (Imaging tab mounts new
  panel; placeholder cards + retinal workbench unchanged)
- `apps/web/src/styles.css` (`.imaging-pipeline__*` appended)
- `apps/web/src/test/ImagingPipelinePanel.test.tsx` (new, 8 tests)
- `docs/product/phase-21b-imaging-pipeline-foundation.md` (this file)

## Migration roundtrip

`f7a8b9c0d1e2` ran cleanly upgrade-head on a fresh SQLite DB locally.
Postgres parity is exercised by the CI `backend-postgres` job.

## Remaining limitations

- No work-queue integration — `imaging_studies` are not yet routed
  into Phase 20B `work_queue_items`. Phase 22 will surface
  ready-for-review counts on the doctor + reviewer dashboards.
- No retina/glaucoma → imaging linkage — Phase 21A's `last_oct_at`
  / `last_fundus_at` still float as standalone date columns.
- No imaging-study export (CSV / FHIR / DICOM SR).
- No automated detection of duplicate studies (same patient + eye +
  modality + captured_at).
- No file-checksum verification beyond storing the value.
