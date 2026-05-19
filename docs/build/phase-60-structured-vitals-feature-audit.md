# Phase 60 Structured Vitals Feature Audit

Date: 2026-05-19
Branch: `feature/phase-60-structured-vitals-workup`

## 1. Existing Vitals / Workup Status

No complete structured vitals/workup feature existed before Phase 60.
The repo had technician roles, dashboard queues, specialty measurement
events, imaging measurement metadata, and note/ambient text references
to VA/IOP, but no encounter-scoped `visit_vitals_workups` record with
vitals, ophthalmology workup, review/sign lifecycle, signed immutability,
and metadata-only audit behavior.

## 2. Files Inspected

- `apps/api/app/`
- `apps/api/app/api/`
- `apps/api/app/services/`
- `apps/api/alembic/versions/`
- `apps/api/tests/`
- `apps/web/src/`
- `docs/workflow/`
- `docs/build/current-product-truth.md`
- `docs/commercial/claims-policy.json`
- `scripts/check_runtime_safety.py`
- `scripts/check_commercial_claims.sh`
- `scripts/check_website_claims.sh`
- `scripts/check_demo_claims.sh`

## 3. Related Encounter / Patient Structures Found

- Native patients and encounter linkage already exist.
- `ClinicalTabbedWorkspace` already provides the Documentation and
  Clinical/Ophthalmology workspace surfaces.
- Role identities include `technician`, `front_desk`, `reviewer`,
  `clinician`, and `admin`.
- Existing audit infrastructure writes to `security_audit_events`.

## 4. Related Ophthalmology Workup Structures Found

- Phase 20B structured workflow templates include technician-owned
  stages such as VA, IOP, and dilation.
- Specialty tracking supports IOP and ophthalmology measurements, but
  those are specialty longitudinal events, not full encounter intake.
- Imaging pipeline supports device-derived metadata and measurements,
  but not structured technician vitals intake.
- Fundus charting and ambient documentation both already enforce
  provider-review and signed/locked safety patterns.

## 5. Exact Gaps

- No vitals table.
- No BMI calculation.
- No partial BP / partial VA / partial IOP warning generation.
- No unified route set for encounter-scoped vitals/workup list, create,
  get, patch, review, and sign.
- No role matrix where technicians can enter but cannot sign.
- No vitals-specific audit minimization tests.
- No frontend panel for structured intake and signed/locked workup state.
- No docs or demo runbook for the workup workflow.
- Claim scanners did not explicitly block vitals diagnosis, treatment
  recommendation, device integration, or remote patient monitoring
  overclaims.

## 6. Implementation Decision

Add a new `visit_vitals_workups` table and a narrow backend/frontend
surface. Do not reuse specialty tracking or imaging measurements because
those tables do not carry the required review/sign lifecycle, signed
immutability, workup notes, BMI, or audit minimization contract.

The feature is structured intake only:

- technician-entered or clinician-entered
- provider-visible
- provider-reviewed
- signed/locked when finalized
- no diagnosis
- no treatment recommendation
- no orders, referrals, patient messages, billing, or coding
- no device integration
- no production LLM
- no real PHI in demos
