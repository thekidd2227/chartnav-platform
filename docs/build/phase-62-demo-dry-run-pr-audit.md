# Phase 62 Demo Dry-Run PR Audit

Date: 2026-05-20  
Auditor: Codex healthcare SaaS demo-safety audit pass  
Audited branch: `feature/phase-62-demo-dry-run-pr-audit`  
Audited source state: `origin/main` at `47820ed docs(demo): add controlled buyer demo dry-run evidence packet (#74)`  
PR status: Phase 62 PR `#74` was already merged before this audit.

## Executive conclusion

Phase 62 is source-safety clean and directionally useful: it adds a controlled visit script, evidence-packet template, manual screenshot/video shot lists, local Desktop-bundle scaffolding, and extends the demo claim scanner to cover the new Phase 62 docs. The language is consistently fake-data-only, provider-reviewed, no real PHI, no production LLM, not a certified EHR, and not autonomous diagnosis or image interpretation.

It is not yet buyer-demo-ready as a completed evidence package. The local Desktop bundle is not present at `~/Desktop/ChartNav-Buyer-Demo-Build`, no actual screenshots/videos are present, and the staged bundle references a `docs/` subfolder that is not included. These are operational readiness issues, not clinical product-code regressions.

Merge-safety assessment if this were still open: **merge-safe as a docs/scaffold PR only after acknowledging follow-up repairs; not GO for a buyer dry run until the Desktop copy, actual captures, and bundle-doc mismatch are resolved.**

## Files inspected

- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-demo-dry-run-report.md`
- `docs/demo/phase-62-screenshot-shot-list.md`
- `docs/demo/phase-62-video-clip-shot-list.md`
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
- `docs/demo/phase-62-local-build-delivery.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-demo-checklist.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/build/current-product-truth.md`
- `docs/commercial/claims-policy.json`
- `artifacts/phase-62/desktop-bundle/*`
- `artifacts/phase-62/screenshots/`
- `artifacts/phase-62/video-clips/`
- `.gitignore`
- `scripts/check_demo_claims.sh`
- `scripts/check_commercial_claims.sh`
- `scripts/check_website_claims.sh`
- `scripts/test_claim_policy_fixtures.sh`
- `scripts/check_runtime_safety.py`
- `scripts/check_alembic_safety.sh`
- `apps/web/src/ClinicalTabbedWorkspace.tsx`
- `apps/web/src/features/ambient/AmbientDocumentationPanel.tsx`

## Audit findings

### 1. Visit script coverage

The visit script exercises the major demoable clinical workflow surfaces:

- workspace shell and nine-tab navigation;
- Technician Workup & Vitals, including fake values, BMI, warnings, review, signing, and lock state;
- ophthalmology intake fields inside the vitals/workup surface;
- Provider-Reviewed VisitDraft Assist / ambient documentation path;
- Provider-Reviewed Fundus Drawing Assist / fundus charting path;
- runtime safety, claim scanner, Alembic, release checklist, and product-truth evidence.

Coverage is sufficient for a controlled buyer dry run once the operational issues below are fixed.

### 2. Provider-Reviewed VisitDraft Assist naming

The buyer-facing label **Provider-Reviewed VisitDraft Assist** is safer than "ambient scribe" language and avoids autonomous documentation claims.

However, the docs use that buyer-facing label as if it is the on-screen card title:

- `docs/demo/phase-62-end-to-end-demo-visit-script.md` describes the module as `Documentation / EMR-EHR tab -> Provider-Reviewed VisitDraft Assist wide card`.
- `docs/demo/phase-62-screenshot-shot-list.md`, `docs/demo/phase-62-video-clip-shot-list.md`, and `docs/demo/phase-62-demo-dry-run-report.md` repeat that expected screen label.

The actual UI still renders:

- tab label: `Documentation / EMR/EHR`;
- card title: `Provider-Reviewed Ambient Documentation Assist`;
- panel title: `Provider-Reviewed Ambient Documentation Assist`.

Risk: an operator following the script literally may look for a non-existent on-screen `VisitDraft Assist` card during a timed dry run.

Recommended repair: keep `VisitDraft Assist` as approved narration, but update click paths to say the on-screen UI currently reads `Provider-Reviewed Ambient Documentation Assist`. Also replace `Documentation / EMR-EHR` with the actual `Documentation / EMR/EHR` tab label.

### 3. Fundus drawing safety

Fundus language is safe and accurate:

- described as clinician-entered findings converted to a structured drawing;
- explicitly not image interpretation;
- explicitly not diagnosis;
- no fundus photo/OCT capture is requested;
- Phase 61A caveat remains: Fundus does not render a per-response `forbidden_actions` / "What ChartNav did NOT do" card today.

No fundus overclaim was found in the Phase 62 docs.

### 4. Screenshot shot list

The 30-shot list covers the marketable workflow areas: workspace shell, vitals, VisitDraft Assist, fundus drawing, runtime safety, claim scanners, Alembic safety, release checklist, and product-truth statements.

The shot list clearly states actual capture is manual and that only fake Morgan Lee demo data should be used.

Issue: no actual screenshot files are present in `artifacts/phase-62/screenshots/`; only `.gitkeep` exists. The evidence packet correctly says actual PNGs are gitignored and operator-captured, but the package is therefore a shot-list scaffold, not a completed evidence packet.

### 5. Video clip shot list

The 12-clip list covers the major marketable demo flows, including the three-minute highlight reel. The language avoids autonomous, diagnosis, treatment, device, and production-LLM claims.

Issue: no actual video files are present in `artifacts/phase-62/video-clips/`; only `.gitkeep` exists. This is acceptable for a template/scaffold PR, but it is a blocker for buyer-demo GO.

### 6. Dry-run report usefulness

The dry-run report is useful as a template. It captures environment, SHA, validation commands, feature walkthrough, screenshot/video counts, known failures, and go/no-go.

It is not a completed dry-run report. All capture-status fields are blank by design. Before a buyer demo, the operator must create a dated completed copy under `artifacts/phase-62/dry-runs/YYYY-MM-DD/report.md` or attach it to an internal issue.

### 7. Known failure modes

The Desktop bundle includes `TROUBLESHOOTING.md` with operational symptoms and stop-demo triggers. The stop-demo triggers are appropriately conservative:

- real PHI on screen;
- unsafe `CHARTNAV_ENV`;
- runtime safety failure;
- forbidden narration/UI phrase;
- visible secret;
- raw clinical values in an audit log;
- signing without attestation.

This is a strong part of the PR.

### 8. Local build delivery

The repo contains a staged bundle at `artifacts/phase-62/desktop-bundle/`, but the requested local folder does **not** exist:

`/Users/jean-maxcharles/Desktop/ChartNav-Buyer-Demo-Build` was missing at audit time.

This means the local Desktop build delivery has not been completed on this machine. The docs accurately describe the copy command, but the operator-ready Desktop folder cannot be inspected for final contents, permissions, local accidental files, secrets, or real-PHI absence.

### 9. Desktop bundle doc mismatch

The staged bundle claims it includes a `docs/` subfolder:

- `artifacts/phase-62/desktop-bundle/README.md` lists `docs/` as a read-only copy of Phase 62/61/61A docs plus product truth and release evidence checklist.
- `docs/demo/phase-62-local-build-delivery.md` says the bundle copies the docs the operator needs offline.
- `artifacts/phase-62/desktop-bundle/START_HERE.md` tells the operator the shot lists are copied in the bundle under `docs/`.

Actual staged bundle contents do **not** include `artifacts/phase-62/desktop-bundle/docs/`; only top-level markdown files and scripts are present.

Risk: a buyer-demo operator working from the Desktop bundle can follow `TEST_VISIT_SCRIPT.md`, but cannot open the referenced offline shot lists, Q&A, runbook, product truth, or evidence packet from the bundle itself.

Recommended repair: either add the intended read-only `docs/` copy to the staged bundle or narrow the bundle docs to state that canonical docs remain in `$CHARTNAV_REPO_PATH/docs/...`.

### 10. Secrets and real PHI

No real secrets or obvious real-PHI data were found in the Phase 62 docs or staged bundle. `.env.example` contains placeholder environment variable names only and repeatedly warns against real keys and real PHI.

The Desktop folder was missing, so no final copied Desktop folder could be inspected for accidental local-only secrets or PHI.

### 11. LLM/vendor boundaries

The Phase 62 docs and bundle preserve safe vendor boundaries:

- no production LLM enabled;
- OpenAI fake-data assist remains optional and not part of the default demo;
- Anthropic and IBM watsonx are not presented as shipped clinical documentation engines;
- no vendor partnership or vendor-powered clinical claim is introduced.

Runtime safety validation passed under the default environment.

### 12. Public marketing changes

No public marketing copy changes were found in this Phase 62 diff. The PR touched docs/demo, artifacts, `.gitignore`, and the demo claim scanner.

### 13. Claim scanner coverage

`scripts/check_demo_claims.sh` was extended to include the six Phase 62 demo docs. Claim scanners and fixture tests passed.

This is sufficient as a regex safety net. Human narration review is still required because the docs intentionally contain forbidden phrase examples in negative/catalog contexts.

### 14. Wrapper reliability

The local `bash scripts/check_alembic_safety.sh` invocation failed under system `python3` because Alembic was not available there. Re-running with the repo API virtualenv passed:

`PYTHON=/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh`

The Desktop bundle's `run-safety-checks.sh` currently calls `bash scripts/check_alembic_safety.sh` without setting `PYTHON`. On a clean operator machine, that can produce a false blocker even when the repo venv is installed.

Recommended repair: have `run-safety-checks.sh` set `PYTHON="$CHARTNAV_REPO_PATH/apps/api/.venv/bin/python"` when that executable exists, then fall back to `python3`.

## Validation run

Required checks:

- `bash scripts/check_commercial_claims.sh` — PASS.
- `bash scripts/check_website_claims.sh` — PASS.
- `bash scripts/check_demo_claims.sh` — PASS, 0 positive-claim hits across 28 demo files.
- `bash scripts/test_claim_policy_fixtures.sh` — PASS.
- `python3 scripts/check_runtime_safety.py` — PASS.
- `bash scripts/check_alembic_safety.sh` — FAIL under system Python due missing Alembic module.
- `PYTHON=/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh` — PASS.
- `git diff --check` — PASS.

Practical targeted tests:

- `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python -m pytest tests/test_vitals_workup.py tests/test_ambient_documentation.py tests/test_fundus_charts.py tests/test_fundus_charts_phase56.py tests/test_runtime_safety.py -q` — PASS, 142 passed.
- `cd apps/web && npx tsc --noEmit` — PASS.
- `cd apps/web && npx vitest run` — PASS, 39 test files / 709 tests.

## Actual media and Desktop build status

- Local Desktop build folder: **missing** at `/Users/jean-maxcharles/Desktop/ChartNav-Buyer-Demo-Build`.
- Screenshots in repo: **none**, only `artifacts/phase-62/screenshots/.gitkeep`.
- Video clips in repo: **none**, only `artifacts/phase-62/video-clips/.gitkeep`.
- The docs correctly identify screenshots/videos as manual capture requirements, not already captured artifacts.

## Recommended edits

1. Correct on-screen click paths:
   - `Documentation / EMR-EHR` -> `Documentation / EMR/EHR`.
   - `Provider-Reviewed VisitDraft Assist wide card` -> actual on-screen `Provider-Reviewed Ambient Documentation Assist` card, with `VisitDraft Assist` kept as approved narration.

2. Resolve the Desktop bundle doc mismatch:
   - add the promised `desktop-bundle/docs/` copy, or
   - remove the promise and point every offline reference back to `$CHARTNAV_REPO_PATH/docs/...`.

3. Make `run-safety-checks.sh` venv-aware for Alembic:
   - prefer `$CHARTNAV_REPO_PATH/apps/api/.venv/bin/python` via `PYTHON=...`;
   - fall back to system `python3`.

4. Before a buyer demo, create the actual Desktop folder and inspect it:
   - copy `artifacts/phase-62/desktop-bundle` to `~/Desktop/ChartNav-Buyer-Demo-Build`;
   - verify no `.env`, real key, local DB with real PHI, screenshot with real PHI, or untracked operator file is present.

5. Complete evidence, not just templates:
   - capture at least 25/30 screenshots;
   - capture at least 8/12 videos including the highlight reel;
   - complete a dated dry-run report;
   - re-run all safety gates after reset.

## Blockers before buyer-demo GO

- Desktop bundle missing locally.
- No actual screenshots or videos captured.
- No completed dated dry-run report.
- Staged bundle references an absent `docs/` folder.
- VisitDraft click-path docs do not match current UI labels.

## Overlap assessment

This audit did not touch product code, backend services, frontend product components, API routes, migrations, deployments, public marketing copy, or real PHI.

It overlaps the Phase 62 docs PR only as a review/audit artifact. It does not overlap implementation work.
