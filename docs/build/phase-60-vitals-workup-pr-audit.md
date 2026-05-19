# Phase 60 Vitals Workup PR Audit

Date: 2026-05-19
Branch: `feature/phase-60-structured-vitals-workup`

## 1. Existing Feature Status

A complete structured vitals/workup feature did not already exist.
Related pieces existed (technician role, work queues, imaging metadata,
specialty IOP events, ambient/fundus provider-review patterns), but none
provided a unified encounter-scoped vitals/workup record with BMI,
warnings, review/sign lifecycle, signed immutability, and audit
minimization.

## 2. Database Schema

The migration adds `visit_vitals_workups` with portable Alembic
`op.create_table` and CHECK constraints for enum-like fields. It uses an
integer primary key consistent with the repo, foreign keys to
organizations/patients/encounters/users, and indexes for organization,
patient, encounter, status, signed_at, and created_at.

No raw SQLite-only SQL, `AUTOINCREMENT`, `datetime('now')`, or raw
`CREATE TABLE` is introduced.

## 3. BMI Calculation

BMI is calculated in `apps/api/app/services/vitals_workup.py` when
height and weight are present. Backend tests cover the calculation, and
the frontend displays a live calculated value before save.

## 4. Warning Language

Warnings are non-diagnostic review prompts. They flag partial BP,
missing BP site/position, height/weight mismatch, partial VA/IOP, and
out-of-range review prompts for oxygen saturation and temperature. They
do not use emergency, diagnosis, treatment, order, referral, billing, or
patient-message language.

## 5. Review / Sign Workflow

The workflow is:

- `draft` or `entered` on create
- review sets `reviewed`
- sign requires `attested=true`
- signed records become immutable

Review does not sign. Sign is separate and restricted to clinician/admin.

## 6. Signed Immutability

Signed workups cannot be patched, reviewed again, or signed again. The
frontend hides edit controls after sign and shows a locked banner.

## 7. Cross-Org and Role Behavior

Backend tests cover:

- cross-org read returning 404
- front desk mutation denied
- technician create allowed
- technician sign denied
- clinician/admin review/sign path

Reviewer read-only access is implemented by role matrix; a direct
reviewer read test should be added if Phase 60 is extended.

## 8. Audit Minimization

Create, update, review, and sign emit metadata-only audit detail:
workup id, patient id, encounter id, status, warning count. Tests assert
that BP values, temperature, pulse, VA, IOP, and technician notes do not
appear in audit detail.

## 9. Frontend Demo Flow

The frontend adds `apps/web/src/features/vitals/` and mounts the panel in
the Documentation workspace. It includes general vitals, ophthalmology
workup, review checks, technician notes, warnings, status timeline,
review/sign controls, and a fake demo values button. Signed workups show
a locked state.

## 10. Claim Policy

The claim policy and scanners now explicitly block:

- vitals diagnosis overclaims
- treatment recommendation overclaims
- device integration overclaims
- remote patient monitoring overclaims
- billing code / automatic coding language
- automatic orders and patient-message language

Fixture tests cover positive failures, negative assertions, Spanish
overclaims, and forbidden-catalog contexts.

## 11. Docs

Added:

- `docs/workflow/structured-vitals-workup.md`
- `docs/demo/phase-60-vitals-workup-demo-runbook.md`
- `docs/build/phase-60-structured-vitals-feature-audit.md`

Updated:

- `docs/build/current-product-truth.md`
- `docs/release/release-evidence-checklist.md`
- LLM vendor docs for Watsonx posture

Docs clearly state no diagnosis, no treatment recommendation, no
orders/referrals/messages/billing/coding, no device integration, no
production LLM, and no real PHI in demos.

## 12. Public / Vendor Overclaims

No public marketing site copy was changed. Watsonx docs were updated
only in internal security/product-truth contexts to record manual
fake-data smoke PASS while preserving real-PHI, pilot, and production
blocks.

## 13. Merge-Safety Assessment

Merge-safe. Validation passed for:

- `tests/test_vitals_workups.py`
- `tests/test_llm_provider.py`
- affected backend suite including runtime, scribe, fundus, and ambient tests
- `src/test/VitalsWorkupPanel.test.tsx`
- full frontend Vitest suite with `--maxWorkers=1`
- frontend typecheck and production build
- claim policy fixtures
- commercial, website, and demo claim scanners
- runtime safety validator
- Alembic safety check
- `git diff --check`

Known residual risk: local backend validation uses SQLite. CI should
provide Postgres parity. The default parallel frontend Vitest run hit
suite-load timeouts in unrelated files; the failing files passed when
rerun directly, and the full suite passed with `--maxWorkers=1`.
