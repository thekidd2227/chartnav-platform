# Phase 60 Post-Merge Audit - Technician Workup & Structured Vitals Intake

Date: 2026-05-19
Branch: `feature/phase-60-post-merge-audit`
Base: `origin/main` at `7d6a8d3ac8b7a5f912c304728696e28402e0bfbd`

## Executive Conclusion

Phase 60 is merge-present on main and is broadly safe for continued demo-hardening: the database migration is portable, Alembic has one head, routes are org-scoped, technician entry and clinician sign separation are tested, signed rows are immutable, audit details avoid vitals values and notes, warnings are non-diagnostic, and public/demo claim scanners cover the Phase 60 overclaim set.

The highest-value follow-up is not new feature work. It is tightening the reviewed-state policy. Today a `reviewed` workup can still be patched by any write role, including `technician`, without clearing `reviewed_by_user_id` / `reviewed_at` or reverting status to `entered`. Signed rows are locked, but review metadata can become stale before sign. That should be resolved before controlled-pilot use.

## Files Inspected

- `apps/api/alembic/versions/b1c2d3e4f5a6_phase_60_visit_vitals_workups.py`
- `apps/api/app/services/vitals_workup.py`
- `apps/api/app/api/vitals_workup.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_vitals_workup.py`
- `apps/web/src/features/vitals/VitalsWorkupPanel.tsx`
- `apps/web/src/features/vitals/VitalsWorkupForm.tsx`
- `apps/web/src/features/vitals/VitalsWorkupSummary.tsx`
- `apps/web/src/features/vitals/vitalsApi.ts`
- `apps/web/src/features/vitals/vitalsTypes.ts`
- `apps/web/src/ClinicalTabbedWorkspace.tsx`
- `apps/web/src/test/VitalsWorkupPanel.test.tsx`
- `apps/web/src/test/ClinicalTabbedWorkspace.test.tsx`
- `docs/workflow/structured-vitals-workup.md`
- `docs/demo/phase-60-vitals-workup-demo-runbook.md`
- `docs/build/current-product-truth.md`
- `docs/commercial/claims-policy.json`
- `scripts/check_commercial_claims.sh`
- `scripts/check_website_claims.sh`
- `scripts/check_demo_claims.sh`
- `scripts/test_claim_policy_fixtures.sh`
- `docs/release/release-evidence-checklist.md`

Notes on expected filenames:
- The merged implementation uses singular `vitals_workup.py` and `test_vitals_workup.py`; prompt-expected plural files `apps/api/app/api/vitals_workups.py` and `apps/api/tests/test_vitals_workups.py` do not exist.
- `docs/build/phase-60-vitals-workup-pr-audit.md` is not present on main. The pre-implementation audit `docs/build/phase-60-structured-vitals-feature-audit.md` is present.

## Findings

### P1 - Reviewed workups can be edited without invalidating review

Evidence:
- `apps/api/app/api/vitals_workup.py` defines write roles as `admin`, `clinician`, and `technician`.
- `PATCH /api/v1/vitals-workups/{workup_id}` only blocks terminal statuses via `assert_can_modify`; `reviewed` is not terminal.
- The patch path recomputes BMI and warnings, but does not clear review metadata, revert status to `entered`, or require clinician-only edits after review.
- Tests cover signed immutability, review-before-sign ordering, and technician cannot sign, but do not cover "technician edits reviewed workup" or "post-review edit invalidates review".

Risk:
If a technician edits a reviewed-but-not-signed workup, the clinician review timestamp and reviewer identity can appear to cover a data snapshot the clinician did not review. Sign still requires clinician action, but the review step loses evidentiary clarity.

Recommendation:
Pick one policy and test it:
- Block all edits to `reviewed` rows except clinician/admin correction flows, or
- Allow edits but automatically reset status to `entered` and clear `reviewed_by_user_id` / `reviewed_at`, or
- Allow clinician/admin edits to reviewed rows but block technician edits after review.

### P2 - Read RBAC is broader than one route comment implies

Evidence:
- Route header states: "front_desk has no clinical access."
- GET/list routes use `require_caller` plus org scoping only; they do not call a read-role guard.
- Workflow docs describe GET/list as `any in-org`, so documentation and code behavior are partly aligned, but the route comment is stricter than implementation.
- Tests cover `front_desk` cannot create, but do not test whether `front_desk` can read/list same-org vitals workups.

Risk:
Vitals workups can contain PHI and clinical notes. Same-org read access may be intentional, but the policy is not pinned. Ambiguous access policy is a release-safety risk.

Recommendation:
Define explicit read roles. If `front_desk` should not view clinical vitals, add `_READ_ROLES` and tests for GET/list denial. If front-desk read is intended, update the route comment and product truth so reviewers do not infer a stronger policy than exists.

### P2 - `patient_id` has an index but no foreign key

Evidence:
- Migration creates indexed nullable `patient_id`.
- Migration defines FKs for organization, encounter, reviewed_by, signed_by, and created_by.
- No FK is defined from `patient_id` to `patients.id`.

Risk:
The route currently derives `patient_id` from the encounter, so normal API writes are coherent. A direct data repair or future endpoint could still create dangling `patient_id` values.

Recommendation:
If legacy encounter rows can safely satisfy it, add a follow-up migration with `patient_id -> patients.id`. If nullable/non-FK is intentional, document the reason in the migration or workflow docs.

### P3 - Database integrity relies on route validation, not DB checks

Evidence:
- Status, source type, BP position/site, temperature unit/site, height/weight unit, IOP method, and dilation status are string columns without DB-level CHECK constraints.
- Service and route validation are strong; Alembic safety passes.

Risk:
Route validation is enough for current API traffic, but DB-level integrity would reduce drift from future scripts or direct writes.

Recommendation:
Consider portable CHECK constraints for status and core enums in a future schema hardening pass, or explicitly document why app-level validation is the chosen convention.

### P3 - Evidence doc gap

Evidence:
- `docs/build/phase-60-vitals-workup-pr-audit.md` is missing from merged main.
- The release evidence checklist does not yet include a Phase 60-specific row for structured vitals tests or audit minimization, though general backend/frontend/safety rows exist.

Risk:
The product is test-covered, but release evidence is less complete than the Phase 60 task required.

Recommendation:
Either add the missing PR audit retroactively or treat this post-merge audit as the Phase 60 evidence artifact. Add structured vitals backend/frontend/audit-minimization rows to the release checklist.

## Audit Questions

### 1. Database schema portability and indexing

Pass with follow-up. The migration uses Alembic/SQLAlchemy portable APIs, no raw `CREATE TABLE`, no `AUTOINCREMENT`, and no `datetime('now')`. Required indexes exist for organization, encounter, patient, status, signed_at, and created_at. Alembic upgrade to head succeeded against a local SQLite test DB.

Follow-up: add or document the missing `patient_id` FK, and consider DB-level CHECK constraints for lifecycle/status strings.

### 2. Alembic one-head state

Pass. `scripts/check_alembic_safety.sh` reported exactly one Alembic head and successful upgrade to head when run with the API virtualenv.

### 3. Backend org scoping

Pass. Create/list resolves encounter by `id` plus caller `organization_id`; get/update/review/sign select the workup by `id` plus `organization_id`. Cross-org tests return 404 for get and list.

### 4. RBAC against stated rules

Partial pass. Write/review/sign roles match the core stated rules:
- admin/clinician/technician can create/update.
- clinician/admin can review/sign.
- technician can enter but cannot review or sign.
- reviewer/front_desk cannot create.

Gap: read access is `any in-org`, while the route comment says front desk has no clinical access. This needs a clear product decision and tests.

### 5. Technician can enter but not sign

Pass. Backend tests cover technician create + enter, technician cannot review, and technician cannot sign. API sign role requires admin or clinician.

### 6. Review/sign workflow safety

Mostly pass. Review requires `entered`; sign requires `reviewed`; sign requires `attested=true`; audit events are emitted for create/update/review/sign. The reviewed-state edit policy is the main gap because reviewed data can change without invalidating review metadata.

### 7. Signed record immutability

Pass. Signed workups are terminal; patch and double-sign return 409; frontend hides edit/review/sign controls in signed state and shows a locked banner.

### 8. Audit detail minimization

Pass. Audit detail is built from metadata only: workup id, encounter id, patient id, status, warning count, and action. Tests use a canary note and check that BP, temperature, VA, IOP, and technician note content do not appear in vitals audit details.

### 9. Non-diagnostic warnings

Pass. Service warnings use review-required language. Tests explicitly reject diagnostic/treatment/order/referral/billing phrases for high BP, low oxygen saturation, and high temperature cases.

### 10. BMI calculation coverage

Pass. Unit tests cover in/lb, cm/kg, missing height/weight, create-time BMI, and update-time recalculation. Frontend tests cover live BMI preview.

### 11. Frontend demo flow usability

Pass for demo-readiness. The Clinical tab mounts the panel, the fake demo vitals button populates synthetic values, the form has general vitals/ophthalmology/review/notes sections, warnings render from server responses, review and sign are visually distinct, and sign requires attestation.

Follow-up: make the UI role-aware if identity is available, so technicians/front-desk users do not see actions that will only fail at the API.

### 12. Signed UI lock

Pass. Signed workups disable the form, remove save/review/sign controls, remove the attestation block, and show "Workup signed - locked" with immutable copy.

### 13. Docs claim safety

Pass. Workflow and demo docs explicitly state no diagnosis, no treatment recommendations, no orders/referrals/messages/billing/coding, no device integration, no remote patient monitoring, no real PHI in demo, and no production LLM use for this feature.

### 14. Claim scanner coverage

Pass. The canonical policy and all three scanners include Phase 60 overclaims such as AI vitals diagnosis, automatic vitals diagnosis, vital-sign diagnosis, treatment recommendation, device integration, vital-signs device integration, remote patient monitoring, billing/coding, HIPAA compliant, and EHR replacement. Fixture tests pass.

### 15. Product truth accuracy

Mostly pass. `docs/build/current-product-truth.md` includes a Phase 60 row with status `shipped`, correct safety claims, runtime gates, tests/checks, demo path, non-goals, and rollback path. It should be updated after the follow-up RBAC/read-policy decision if front-desk read access changes.

### 16. Duplicate PR/branch risk from PR #68

Resolved. PR #68 (`feature/phase-60-structured-vitals-workup-codex-audit-safe`) is closed and has merge state `DIRTY`. It should remain closed and must not be merged over the accepted Phase 60 implementation from PR #67.

Open PR scan:
- No active Phase 60 duplicate PR was found.
- No active Claude Phase 60 implementation PR was found.
- Open PR #1 (`Phase 64: Clinical Coding Intelligence`) is outside Phase 60 and should remain explicitly separated from vitals because Phase 60 forbids billing/coding automation.

## Recommended Phase 61 Options Ranked by Business Value

1. Phase 61A - Vitals access-control and review-integrity hardening.
   Fix reviewed-state mutation semantics, add explicit read-role policy, add tests for front_desk/reviewer read behavior, and make the frontend role-aware where feasible. This has the highest business value because it protects clinical trust and pilot-readiness.

2. Phase 61B - Release evidence and migration integrity hardening.
   Add the missing Phase 60 evidence artifact or adopt this audit as the artifact, add structured vitals rows to the release checklist, and add `patient_id` FK / DB CHECK constraints if compatible. This improves audit posture and reduces migration drift.

3. Phase 61C - Demo reliability polish.
   Add a scripted fake-data reset path for vitals workups, add an end-to-end demo smoke covering create -> enter -> review -> sign -> locked UI, and add operator notes for role switching. This helps sales/demo operations without adding clinical scope.

## What Not To Build Next

- Do not add diagnosis, triage, treatment recommendation, orders, referrals, patient messaging, billing, coding, or RPM to vitals.
- Do not add device integration until there is a separate vendor/security/data-retention design.
- Do not connect OpenAI, Anthropic, IBM watsonx, or any production LLM to vitals.
- Do not weaken claim scanners to make demo copy easier.
- Do not make signed workups editable in place.

## Validation

Required checks:
- `bash scripts/check_commercial_claims.sh` - PASS
- `bash scripts/check_website_claims.sh` - PASS
- `bash scripts/check_demo_claims.sh` - PASS
- `bash scripts/test_claim_policy_fixtures.sh` - PASS
- `python3 scripts/check_runtime_safety.py` - PASS
- `bash scripts/check_alembic_safety.sh` - initial FAIL on system Python because Alembic dependency was unavailable in the clean worktree environment
- `PYTHON=/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh` - PASS

Targeted backend tests:
- `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python -m pytest tests/test_vitals_workup.py tests/test_runtime_safety.py -q` - PASS, 57 passed

Targeted frontend tests:
- `npx tsc --noEmit` from `apps/web` - PASS using the primary checkout's installed `node_modules` via temporary symlink
- `npx vitest run src/test/VitalsWorkupPanel.test.tsx` from `apps/web` - PASS, 13 passed

Environment notes:
- The clean audit worktree did not have its own `apps/api/.venv` or `apps/web/node_modules`; existing project dependencies from `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform` were used for validation.
- The temporary frontend `node_modules` symlink was removed after validation.

## Blockers

No blocker to merging this audit document.

For Phase 60 controlled-pilot readiness, treat the reviewed-state mutation policy and explicit read-role policy as blockers until decided and tested.

## Merge Recommendation

Merge-safe as an audit-only PR. Do not merge any duplicate Phase 60 implementation branch. Use this audit to drive a small Phase 61 hardening PR before broad demo or controlled-pilot expansion.
