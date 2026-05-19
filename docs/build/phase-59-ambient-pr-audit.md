# Phase 59 Ambient Documentation PR Audit

Date: 2026-05-19
Audited PR: #65 `test(demo): harden ambient documentation QA and demo checklist`
Head branch: `feature/phase-59-ambient-qa-demo-lockdown`
Head commit inspected: `ecea9b99947537116970a96fdac70eae2970c289`
Audit branch: `feature/phase-59-ambient-pr-audit`

## Executive Conclusion

Merge recommendation: merge-safe after normal review.

The Phase 59 PR is a QA/demo lockdown PR, not a product-feature PR. Its own delta adds backend tests, frontend tests, a demo QA checklist, and demo-claim scanner coverage. I found no unnecessary backend service, frontend product component, API route, migration, deployment, public marketing, or real-PHI change in the Phase 59 delta.

The coverage is materially strong for ambient lifecycle, role/cross-org behavior, audit minimization, prompt-injection-as-transcript-data, OpenAI fake-data gating, runtime safety, and demo-critical frontend states. The only non-blocking repair I found is a documentation cleanup: the Phase 59 checklist references `scripts/reset_demo.sh`, but the repo has `scripts/reset_demo_state.sh` and `scripts/reset_phase24b_retina_demo.sh`, not `scripts/reset_demo.sh`.

## Files Inspected

- `apps/api/tests/test_ambient_documentation.py`
- `apps/api/tests/test_runtime_safety.py`
- `apps/web/src/test/AmbientDocumentationPanel.test.tsx`
- `apps/web/src/test/ClinicalTabbedWorkspace.test.tsx`
- `docs/demo/phase-57-ambient-documentation-demo-runbook.md`
- `docs/demo/phase-59-ambient-demo-qa-checklist.md`
- `docs/workflow/ambient-documentation-assist.md`
- `docs/release/release-evidence-checklist.md`
- `docs/build/current-product-truth.md`
- `scripts/check_runtime_safety.py`
- `docs/commercial/claims-policy.json`
- `scripts/check_commercial_claims.sh`
- `scripts/check_website_claims.sh`
- `scripts/check_demo_claims.sh`
- `scripts/test_claim_policy_fixtures.sh`

## Audit Findings

### 1. Backend Ambient Lifecycle Coverage

Status: sufficient.

The backend test suite covers the major lifecycle edges:

- deterministic default path works without env vars;
- OpenAI assist only activates through the explicit `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai` path plus Phase 52B safe gates;
- no silent fallback when opt-in gates fail;
- `fake_data_context=false` returns 422;
- draft moves to `ready_for_review`;
- review before ambient draft is rejected;
- finalize before review is rejected;
- finalized sessions reject re-draft and double-finalize;
- discard works from `ready_for_review` and `reviewed`;
- finalized sessions are immutable;
- role matrix and cross-org behavior are covered.

Evidence: tests named `test_full_lifecycle_walkthrough_draft_to_finalized`, `test_review_before_ambient_draft_is_rejected`, `test_finalize_before_review_is_rejected`, `test_second_finalize_on_finalized_session_returns_409`, `test_discard_works_post_ambient_draft`, `test_discard_post_reviewed_works`, and `test_cross_org_returns_404`.

### 2. Frontend Demo-Critical State Coverage

Status: sufficient.

The frontend test suite covers the states a demo operator needs:

- safety banner visible with required clauses;
- empty state and no-session preview;
- generate disabled until transcript exists;
- sample button loads fake data;
- generate flow creates session and calls ambient draft with `fake_data_context: true`;
- generate failure preserves typed transcript;
- structured facts, safety flags, missing info, and forbidden-actions summary render;
- status timeline marks ready-for-review;
- review exposes attestation;
- sign is disabled until attestation;
- signed/locked state hides action controls;
- rendered UI avoids forbidden positive phrases;
- workspace Documentation tab mounts the Ambient Documentation panel.

Evidence: `AmbientDocumentationPanel.test.tsx` and `ClinicalTabbedWorkspace.test.tsx` ambient mount assertions.

### 3. Audit Minimization

Status: sufficient.

Backend tests assert audit rows do not store raw transcript text, draft body text, structured fact payloads, or canary transcript phrases. The prompt-injection API test also checks that injection text does not leak into `scribe_session_drafted_ambient` audit details.

Residual risk: the tests cover ambient audit detail, not every historical scribe-session audit event. That is acceptable for this PR because the change is ambient-specific.

### 4. Prompt-Injection / Transcript-As-Data Risk

Status: sufficient for deterministic path.

The tests include a transcript containing instruction-like text: "Ignore previous instructions", auto-sign, order, patient message, diagnosis confirmation, and CPT billing language. The service and route tests assert:

- provider review remains required;
- every `forbidden_actions` key remains `false`;
- lifecycle status remains `ready_for_review`, not finalized;
- order/billing/messaging language becomes safety flags rather than executable action;
- audit details do not include the injection text.

Residual risk: the mocked OpenAI happy path validates response-envelope handling and server-side pinning, but not adversarial model output containing instruction-injection content in every field. That is acceptable for fake-data-only evaluation, but future LLM expansion should add explicit malicious-model-output fixtures before any real-PHI or production path is considered.

### 5. OpenAI Fake-Data Assist Gates

Status: sufficient.

Ambient tests cover:

- `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` only accepts literal `openai`;
- non-OpenAI values do not activate ambient assist;
- `CHARTNAV_LLM_ENABLED` missing refuses;
- `CHARTNAV_LLM_REAL_PHI_APPROVED=1` refuses;
- `CHARTNAV_PILOT_ALLOW_LLM_OPENAI=1` refuses;
- missing API key refuses;
- injected transport path avoids network;
- API key canary is not logged.

The source-level test also asserts Anthropic and IBM watsonx are not wired into the ambient path.

### 6. Runtime Safety Validator

Status: sufficient.

`scripts/check_runtime_safety.py` now covers ambient OpenAI gates:

- `AMBIENT_OPENAI_PRODUCTION`;
- `AMBIENT_OPENAI_NOT_DEMO`;
- `AMBIENT_OPENAI_REAL_PHI_APPROVED`;
- `REAL_PHI_WITH_AMBIENT_OPENAI`;
- `PRODUCTION_AMBIENT_OPENAI`.

Runtime tests cover production, non-demo, local/demo allowed state, real-PHI approved, real-PHI enabled, unset/default state, and non-OpenAI literal values.

### 7. Claim Policy / Scanner Coverage

Status: sufficient.

The claim policy includes an `ambient_documentation_overclaims` category for:

- hands-free scribing;
- ambient scribe parity;
- note writes itself;
- chart fills itself;
- AI writes the note;
- production LLM documentation;
- OpenAI-powered scribe.

The commercial, website, and demo scanners include ambient/scribe overclaim phrases. The Phase 59 PR also adds the Phase 57 ambient runbook and Phase 59 checklist to the demo scanner file list.

Checks passed across commercial, website, demo, fixture, and sync scripts.

### 8. Demo Runbook / Checklist Readiness

Status: mostly sufficient; one non-blocking doc nit.

The Phase 59 checklist is operator-ready in the important safety areas:

- environment gates;
- fake patient/transcript controls;
- required safety scripts;
- UI reachability;
- narration phrases;
- stop-demo triggers;
- troubleshooting for runtime safety and provider-disabled failures;
- post-demo cleanup.

Non-blocking nit: `docs/demo/phase-59-ambient-demo-qa-checklist.md` line 215 references `scripts/reset_demo.sh`, which does not exist in the repo. Existing reset-like scripts are `scripts/reset_demo_state.sh` and `scripts/reset_phase24b_retina_demo.sh`. The checklist says "or equivalent — adjust path," so this is not a merge blocker, but it should be made concrete before the next customer-facing demo.

### 9. Release Evidence Checklist

Status: adequate but generic.

`docs/release/release-evidence-checklist.md` includes claim scanners, claim fixtures, runtime safety validator, Alembic safety, no real PHI, no production LLM, no autonomous diagnosis, no image interpretation, and no orders/referrals/patient messaging/billing/coding confirmations.

Gap: it does not include an ambient-specific row such as "Ambient demo QA checklist completed" or "Ambient lifecycle target tests passed." The Phase 59 checklist functions as the ambient-specific subset, so this is not a blocker. Add an ambient row later if release checklists are intended to be feature-specific.

### 10. Product Behavior Changed Unnecessarily

Status: no.

The Phase 59 delta from `249ef2b3` to `ecea9b9` changes:

- `apps/api/tests/test_ambient_documentation.py`
- `apps/web/src/test/AmbientDocumentationPanel.test.tsx`
- `docs/demo/phase-59-ambient-demo-qa-checklist.md`
- `scripts/check_demo_claims.sh`

No backend service, frontend product component, API route, migration, deployment script, or public website file was changed by the Phase 59 lockdown commit.

### 11. Public / Vendor Overclaims

Status: none found.

Claim scanners passed. The new demo checklist includes forbidden phrases only in negative/catalog/stop-demo contexts, which the scanner handles correctly.

### 12. Merge Safety

Status: merge-safe.

No blocker found. The PR is a safety and regression coverage improvement. Merge is recommended after normal reviewer acceptance, with the non-blocking reset-script doc nit tracked.

## Checks Run

Run from the Phase 59 PR worktree at `/tmp/chartnav-phase59-review`:

- `bash scripts/check_commercial_claims.sh` — passed.
- `bash scripts/check_website_claims.sh` — passed.
- `bash scripts/check_demo_claims.sh` — passed, scanning 17 demo files.
- `bash scripts/test_claim_policy_fixtures.sh` — passed.
- `python3 scripts/check_runtime_safety.py` — passed.
- `PYTHON=/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh` — passed.
- `cd apps/api && /Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python -m pytest tests/test_ambient_documentation*.py tests/test_runtime_safety.py tests/test_llm_provider.py -q` — 98 passed.
- `cd apps/web && npx tsc --noEmit && npx vitest run` — passed after symlinking the existing repo `apps/web/node_modules` into the temporary review worktree; 38 test files / 694 tests passed.

Environment note: the isolated review worktree did not contain ignored dependency directories (`apps/api/.venv`, `apps/web/node_modules`). Initial direct commands failed for missing local dependency directories, not code failures. Reruns used the existing repo venv and node dependency tree.

## Blockers

None.

## Risks / Follow-Ups

1. Replace the non-existent `scripts/reset_demo.sh` example in the Phase 59 checklist with a concrete existing reset command before the next live demo.
2. Consider adding an ambient-specific row to `docs/release/release-evidence-checklist.md` if that checklist is meant to be feature-specific rather than generic.
3. Before any future real-PHI or production LLM path, add malicious model-output fixtures, not just malicious transcript-input fixtures.

## Overlap With Claude's Implementation PR

This audit does not modify Claude's implementation branch and does not change product behavior. It reviews PR #65 and creates this separate docs-only audit artifact.

