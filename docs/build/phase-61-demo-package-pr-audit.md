# Phase 61 Controlled Buyer Demo Package PR Audit

Date: 2026-05-19
Reviewed PR: `#70` (`feature/phase-61-controlled-buyer-demo-package`)
Audit branch: `feature/phase-61-demo-package-pr-audit`
Base reviewed: `d6f02ec docs(demo): add controlled buyer demo package`

## Executive Conclusion

The Phase 61 PR is directionally strong and claim-safe: it is docs/script-only, adds a coherent buyer-demo package, keeps fake-data and real-PHI boundaries explicit, adds the four new demo docs to `scripts/check_demo_claims.sh`, and passes the claim/runtime/Alembic validation set.

It is not quite merge-safe as written. The docs repeatedly assert that every signed artifact or every demonstrated surface has a "What ChartNav did NOT do" / `forbidden_actions` panel. That is true for Structured Vitals and Ambient Documentation Assist, but it is not true for Fundus Charting in the current shipped UI/API. The fundus surface has a safety banner, warnings, review/sign attestation, and signed-lock state, but no `forbidden_actions` response shape and no "What ChartNav did NOT do" card. This should be corrected before merging because it is a buyer-demo script accuracy issue, not just wording polish.

## Files Inspected

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-demo-checklist.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-61-demo-storyboard.md`
- `docs/build/phase-61-demo-package-audit.md`
- `docs/build/current-product-truth.md`
- `docs/commercial/claims-policy.json`
- `docs/workflow/ambient-documentation-assist.md`
- `docs/workflow/fundus-charting.md`
- `docs/workflow/structured-vitals-workup.md`
- `docs/demo/phase-56-fundus-demo-runbook.md`
- `docs/demo/phase-57-ambient-documentation-demo-runbook.md`
- `docs/demo/phase-60-vitals-workup-demo-runbook.md`
- `scripts/check_commercial_claims.sh`
- `scripts/check_website_claims.sh`
- `scripts/check_demo_claims.sh`
- `scripts/test_claim_policy_fixtures.sh`
- `scripts/check_runtime_safety.py`
- `apps/web/src/features/fundus/*`
- `apps/web/src/features/ambient/*`
- `apps/web/src/features/vitals/*`
- `apps/web/src/ClinicalTabbedWorkspace.tsx`
- `apps/api/app/api/fundus_charts.py`
- `apps/api/app/api/scribe_sessions.py`
- `apps/api/app/api/vitals_workup.py`

## Findings

### P1 - Fundus is documented as having a forbidden-actions panel/API that it does not ship

Evidence:
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` says every signed artifact has a "What ChartNav did NOT do" card and instructs the operator to point at it during closing.
- `docs/demo/phase-61-demo-storyboard.md` closes with the same "What ChartNav did NOT do" panel across signed artifacts.
- `docs/demo/phase-61-buyer-qa-safe-answers.md` says `forbidden_actions.diagnosis=false` exists on every fundus, ambient, and vitals response.
- The actual fundus API/types do not expose `forbidden_actions`; `apps/web/src/features/fundus/FundusChartEditor.tsx` renders warnings, SVG, legend, review/sign controls, attestation, and signed-lock banner, but no "What ChartNav did NOT do" card.

Risk:
The buyer-demo script can send the operator hunting for a UI element that does not exist, or worse, verbally claim a server response contract fundus does not currently provide.

Recommended edit:
Change Phase 61 docs to say:
- Vitals and Ambient have explicit "What ChartNav did NOT do" / `forbidden_actions` panels.
- Fundus has explicit safety banner + warnings + provider review/sign attestation + signed-lock state, but no forbidden-actions card in V1.
- Do not claim `forbidden_actions` exists on fundus until the product actually ships it.

### P2 - Vitals "restore sample" step is ambiguous after editing an existing saved workup

Evidence:
- The runbook tells the operator to clear systolic, save, then "Restore the sample."
- In the shipped UI, `Load fake demo vitals` resets selection to a new unsaved form rather than restoring the currently selected saved workup.

Risk:
During a live buyer demo, clicking the sample button after editing an entered workup can move the operator to a new unsaved form, hiding the selected workup and making the subsequent review/sign steps confusing.

Recommended edit:
Make the step concrete: after demonstrating the partial-BP warning, manually re-enter the missing systolic value and click Save on the same selected workup, or explicitly create a fresh demo-sample workup and advance it before review/sign.

### P2 - Fallback table has a copy/paste endpoint error

Evidence:
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` fallback table says the Vitals symptom is "API 500 / 404 / 403 on draft-ambient or similar".
- `draft-ambient` is the ambient documentation endpoint, not the vitals endpoint.

Risk:
Low product risk, but high operator-confusion risk during a live failure.

Recommended edit:
Change Vitals symptom to "API 500 / 404 / 403 on vitals-workups create/update/review/sign" or similar.

### P3 - "Three new docs" wording is inconsistent

Evidence:
- The runbook says "Phase 61's three new docs" and then lists four docs: runbook, checklist, Q&A, storyboard.
- `scripts/check_demo_claims.sh` correctly scans all four new Phase 61 demo docs.

Risk:
Minor, but it weakens the audit trail.

Recommended edit:
Change "three" to "four" anywhere it appears for Phase 61 docs.

## Audit Results

### 1. Demo flow matches actual shipped product

Partial pass. The overall sequence maps to shipped surfaces: Clinical / Ophthalmology -> Technician Workup & Vitals; Documentation / EMR/EHR -> Ambient Documentation Assist; Imaging -> Fundus charts; then review/sign and safety posture.

Mismatch: Phase 61 overstates the fundus safety UI/API by describing a forbidden-actions card/response that does not exist on fundus.

### 2. Demo order is coherent

Pass. Intake -> ambient draft -> fundus charting -> review/sign -> audit/release posture is a coherent buyer narrative and matches the clinical workflow shape better than showing specialty artifacts first.

### 3. Click paths are realistic

Mostly pass. Tab names, panel names, core buttons, attestation blocks, and signed-lock states match the shipped UI. The main realism issue is the Vitals "restore sample" ambiguity after a saved row is edited.

### 4. Fake-data boundaries are explicit

Pass. The runbook, checklist, storyboard, and Q&A repeatedly state fake-data only and instruct operators not to type real names, MRNs, DOBs, phone numbers, addresses, insurance, images, or clinical content.

### 5. Real-PHI boundaries are explicit

Pass. Real PHI is consistently described as gated behind controlled-pilot/security review. Demo instructions explicitly prohibit real PHI and require runtime safety validation.

### 6. LLM/vendor boundaries are explicit

Pass. Docs say no production LLM, deterministic/default paths, OpenAI fake-data adapter only behind separate gates, no OpenAI-powered clinical documentation claim, and IBM watsonx fake-data evaluation only with production/real-PHI/pilot still unapproved.

### 7. EHR/HIPAA language is safe

Pass. The docs use negative assertions: not a certified EHR, does not replace a certified EHR, not HIPAA compliant/certified by default, no out-of-box HIPAA claim.

### 8. Fundus language avoids image interpretation/diagnosis

Mostly pass. The language correctly says clinician-entered findings to structured retinal diagram, not fundus-photo interpretation, not OCT interpretation, not diagnosis. Correct the nonexistent fundus `forbidden_actions` / "What ChartNav did NOT do" claims before merge.

### 9. Vitals language avoids diagnosis/treatment/device/RPM claims

Pass. Vitals are framed as technician-entered structured intake for provider review. The docs explicitly avoid diagnosis, treatment recommendation, device integration, and remote patient monitoring claims.

### 10. Ambient language avoids hands-free/autonomous scribe claims

Pass. Ambient is framed as fake transcript-to-draft, provider-reviewed, no real-time audio recording, no hands-free scribing, no autonomous documentation, no OpenAI-powered production claim.

### 11. Buyer Q&A answers are safe and useful

Mostly pass. The Q&A is practical and conservative. Correct the answer that says every fundus response has `forbidden_actions`; otherwise the sheet is safe and operator-useful.

### 12. Nonexistent scripts are referenced

Pass. Referenced scripts exist:
- `scripts/reset_demo_state.sh`
- `scripts/reset_phase24b_retina_demo.sh`
- `scripts/check_runtime_safety.py`
- `scripts/check_commercial_claims.sh`
- `scripts/check_website_claims.sh`
- `scripts/check_demo_claims.sh`
- `scripts/test_claim_policy_fixtures.sh`
- `scripts/check_alembic_safety.sh`

### 13. Public marketing copy accidentally created

Pass. PR #70 adds docs under `docs/demo/` and `docs/build/`, plus a demo claim scanner update. It does not modify the public website, landing copy, i18n files, or app marketing surfaces.

### 14. Claim scanners pass

Pass. All requested claim checks passed. The scanner expansion to include the four Phase 61 docs works; `check_demo_claims.sh` scanned 22 demo files and reported zero positive-claim hits.

### 15. PR merge safety

Not merge-safe until the P1 demo-accuracy issue is corrected. After the fundus forbidden-actions/what-did-not-do claims and smaller copy issues are fixed, this PR should be merge-safe as a docs-only demo package.

## Validation

- `bash scripts/check_commercial_claims.sh` - PASS
- `bash scripts/check_website_claims.sh` - PASS
- `bash scripts/check_demo_claims.sh` - PASS, scanned 22 demo files
- `bash scripts/test_claim_policy_fixtures.sh` - PASS
- `python3 scripts/check_runtime_safety.py` - PASS
- `bash scripts/check_alembic_safety.sh` - initial FAIL in the clean worktree because system Python lacks the repo Alembic dependency
- `PYTHON=/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh` - PASS
- `git diff --check` - PASS

Environment note: the clean audit worktree does not contain its own API virtualenv, so Alembic validation used the existing repo virtualenv from `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python`.

## Recommended Edits Before PR #70 Merge

1. Remove or narrow all claims that every signed artifact has a "What ChartNav did NOT do" panel. State that Vitals/Ambient have the explicit card and Fundus has safety banner/warnings/attestation/signed-lock.
2. Remove the Q&A claim that `forbidden_actions.diagnosis=false` exists on fundus responses.
3. Make the Vitals warning-demo recovery step exact: manually restore the edited field on the same selected workup, or create a fresh demo-sample workup and advance it before review/sign.
4. Fix the Vitals fallback symptom from `draft-ambient` to a vitals-workup endpoint/action.
5. Change "three new docs" to "four new docs" for the Phase 61 doc set.

## Blockers

Blocker for PR #70: fundus forbidden-actions / "What ChartNav did NOT do" mismatch.

No blocker for this audit PR; it is an audit-only document.

## Overlap With Claude's PR

This audit intentionally reviews Claude's Phase 61 PR #70. This audit branch is stacked on `feature/phase-61-controlled-buyer-demo-package` and should be reviewed as audit feedback. It does not modify product code, backend services, frontend components, API routes, migrations, public marketing copy, or deployment settings.

## Merge Recommendation

For PR #70: request changes before merge.

For this audit PR: merge-safe as audit-only documentation if the team wants the findings attached in-repo.
