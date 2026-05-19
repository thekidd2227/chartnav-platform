# Phase 61A Demo Package Accuracy Repair Audit

Date: 2026-05-19
Reviewed PR: `#72` (`feature/phase-61a-demo-package-accuracy-repair`)
Audit branch: `feature/phase-61a-demo-package-repair-audit`
Base reviewed: `969076d docs(demo): repair phase 61 demo package accuracy`

## Executive Conclusion

Phase 61A substantially fixes the Phase 61 buyer-demo accuracy issues. The false claims that Fundus Charting V1 exposes `forbidden_actions` or a "What ChartNav did NOT do" card have been removed or reframed in the buyer-facing runbook, checklist, Q&A, storyboard, and repair memo. Fundus is now accurately described as enforcing safety through clinician-entered findings, no image input, warnings, provider review/sign, signed-lock state, and claim scanners.

One requested cleanup remains incomplete: `docs/demo/phase-61-controlled-buyer-demo-runbook.md` still says "Phase 61's three new docs" while listing four docs. This is not a buyer-demo safety blocker, but it means the Phase 61A repair checklist is not fully complete.

## Files Inspected

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-demo-checklist.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-61-demo-storyboard.md`
- `docs/build/phase-61a-demo-package-accuracy-repair.md`
- `docs/build/phase-61-demo-package-audit.md`
- `docs/workflow/fundus-charting.md`
- `docs/workflow/ambient-documentation-assist.md`
- `docs/workflow/structured-vitals-workup.md`
- `apps/web/src/features/fundus/`
- `apps/api/app/api/fundus_charts.py`

## Audit Results

### 1. Fundus `forbidden_actions` false claims removed

Pass. The Q&A now scopes `forbidden_actions` to Ambient and Vitals, and explicitly says Fundus V1 does not expose a `forbidden_actions` field. The repair memo correctly lists Fundus as `✗` for the field.

### 2. Fundus "What ChartNav did NOT do" false card claims removed

Pass. The runbook closing now points operators to the Vitals or Ambient signed artifact for the "What ChartNav did NOT do" card and states Fundus V1 does not render that card. The checklist and storyboard use the same scoping.

### 3. Fundus safety posture accuracy

Pass. Fundus is described as clinician-entered findings to structured retinal diagram, with no image input, no fundus photo/OCT interpretation, no diagnosis, warnings as review prompts, explicit attestation, and signed-lock immutability.

### 4. Ambient and Vitals safety panels accuracy

Pass. Ambient and Vitals are still accurately described as having explicit "What ChartNav did NOT do" / `forbidden_actions` panels. That matches the shipped UI/API surfaces.

### 5. Vitals restore-sample wording

Pass. The runbook now instructs the operator to manually re-enter the missing systolic value on the same selected workup, or start a clean workup with "New workup" + "Load fake demo vitals" for review/sign.

### 6. Vitals fallback endpoint wording

Pass. The fallback table now references the `vitals-workups` create/update/review/sign endpoints instead of `draft-ambient`.

### 7. "Three new docs" corrected to "four new docs"

Partial. `docs/build/phase-61-demo-package-audit.md` was corrected, but `docs/demo/phase-61-controlled-buyer-demo-runbook.md` still says "Phase 61's three new docs" while listing four: runbook, checklist, Q&A, storyboard.

Recommended edit:
Change that one remaining phrase to "four new docs" or "four new demo docs."

### 8. Fake-data boundaries

Pass. Fake-data-only constraints remain explicit in the runbook, checklist, Q&A, and storyboard. The docs continue to prohibit real patient names, MRNs, DOBs, phone numbers, addresses, insurance, real images, and real clinical content.

### 9. Real-PHI boundaries

Pass. Real PHI remains explicitly gated behind controlled-pilot/security review. The demo package requires runtime safety checks and says not to demo with production/staging/controlled-pilot envs.

### 10. EHR/HIPAA/vendor language

Pass. The package continues to use negative assertions: not HIPAA compliant/certified by default, not a certified EHR, does not replace a certified EHR, not OpenAI-powered, no production LLM, IBM watsonx not approved for production/real-PHI/pilot use.

### 11. Public marketing copy modified

Pass. The PR touches only `docs/build/` and `docs/demo/` files. No public website, landing page, i18n, app marketing, deck, backend, frontend, API, migration, or deployment files were modified.

### 12. PR merge safety

Nearly merge-safe. There are no remaining buyer-demo safety blockers. I recommend one small docs correction before merge to satisfy the explicit Phase 61A acceptance criteria: change the remaining "three new docs" phrase in `docs/demo/phase-61-controlled-buyer-demo-runbook.md`.

## Checks Run

- `bash scripts/check_commercial_claims.sh` - PASS
- `bash scripts/check_website_claims.sh` - PASS
- `bash scripts/check_demo_claims.sh` - PASS, scanned 22 demo files
- `bash scripts/test_claim_policy_fixtures.sh` - PASS
- `python3 scripts/check_runtime_safety.py` - PASS
- `bash scripts/check_alembic_safety.sh` - initial FAIL in the clean worktree because system Python lacks the repo Alembic dependency
- `PYTHON=/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh` - PASS
- `git diff --check` - PASS

Environment note: the audit worktree did not have its own API virtualenv, so Alembic validation used the existing repo virtualenv at `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python`.

## Remaining Risks

- Low: one doc-count wording issue remains. It does not change demo safety posture, but it is an accuracy repair miss.
- Low: the docs correctly state Fundus V1 lacks `forbidden_actions`; if product later adds that field, the Phase 61 docs should be updated again.

## Blockers

No buyer-demo safety blocker remains.

If applying the requested Phase 61A checklist strictly, the remaining "three new docs" phrase is a merge-blocking typo until fixed.

## Overlap With Claude's PR

This audit intentionally reviews Claude's Phase 61A PR #72. It is stacked on `feature/phase-61a-demo-package-accuracy-repair` and adds only this audit artifact. It does not modify product code, backend services, frontend components, API routes, migrations, public marketing copy, deployment settings, or real PHI.

## Merge Recommendation

For PR #72: request one minor docs correction before merge; after that, merge-safe.

For this audit PR: merge-safe as audit-only documentation.
