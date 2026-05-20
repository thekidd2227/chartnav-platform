# Phase 62A — Buyer-Demo Go / No-Go Status

> **One-page snapshot, last updated 2026-05-20.** This is the
> single document a teammate joining mid-phase reads to learn the
> buyer-demo state at a glance. The detail lives in the audit:
> `docs/build/phase-62a-demo-evidence-repair-audit.md`.

## TL;DR

**Status: NO-GO for live buyer demo.**

Source-safety is green. All six safety scripts pass. All claim
scanners pass. Every backend + frontend test continues to pass.

What is still missing is the **operator evidence**: no actual
screenshots, no actual video clips, and no completed dry-run
report. Phase 62A delivers the docs + scaffolding that make those
captures possible; the operator still has to execute the dry run
on the iMac to flip Go / No-Go to **GO**.

## What changed in Phase 62A

| Change | File | Purpose |
|---|---|---|
| Docs-only repair audit | `docs/build/phase-62a-demo-evidence-repair-audit.md` | Records the six Codex blockers + repair decision. |
| Offline docs folder added under bundle | `artifacts/phase-62/desktop-bundle/docs/` (12 read-only copies + index `README.md`) | The bundle is now self-contained for offline dry-run reading. |
| Venv-aware safety wrapper | `artifacts/phase-62/desktop-bundle/run-safety-checks.sh` | Exports `PYTHON` from the API venv so Alembic and runtime checks see project deps. Warns and falls back to system `python3` if the venv is missing. |
| Narration-vs-UI label clarified | `docs/demo/phase-62-end-to-end-demo-visit-script.md`, `docs/demo/phase-62-screenshot-shot-list.md`, `docs/demo/phase-62-video-clip-shot-list.md`, `docs/demo/phase-62-demo-dry-run-report.md`, `artifacts/phase-62/desktop-bundle/TEST_VISIT_SCRIPT.md` | Everywhere the docs talk about VisitDraft, they now make it explicit that the operator narrates "Provider-Reviewed VisitDraft Assist" while the on-screen card title still reads "Provider-Reviewed Ambient Documentation Assist". The UI card rename is a separate follow-up phase. |
| Tab-name corrected | All Phase 62 demo + bundle docs | `Documentation / EMR-EHR` → `Documentation / EMR/EHR`. |
| Dated dry-run scaffold | `artifacts/phase-62/dry-runs/2026-05-20/report.md` | Operator-fillable dated report with PENDING markers + Go/No-Go gates. |

## What did NOT change in Phase 62A

- **No product UI rename.** The card title in
  `apps/web/src/features/ambient/AmbientDocumentationPanel.tsx` and
  `apps/web/src/ClinicalTabbedWorkspace.tsx` still reads
  "Provider-Reviewed Ambient Documentation Assist". This is by design.
- **No backend change. No migration. No new API. No new service.**
- **No real PHI processing.** Deterministic stub remains the default.
- **No production LLM activation. No deploy. No public website edit.**
- **No claim policy change.** All three claim scanners continue to
  pass on the same canonical phrase set.

## Six blockers from the Codex Phase 62 audit — status

| # | Blocker | Phase 62A repair | Operator action remaining |
|---|---|---|---|
| 1 | `~/Desktop/ChartNav-Buyer-Demo-Build/` doesn't exist locally | Bundle staged in repo at `artifacts/phase-62/desktop-bundle/`; START_HERE has the `cp -R` command. | Run the `cp -R` on the iMac. |
| 2 | `screenshots/` and `video-clips/` have only `.gitkeep` | Shot lists tell the operator exactly what each frame must show / must not show. | Capture 30 PNGs + 12 MOVs. |
| 3 | No completed dated dry-run report | `artifacts/phase-62/dry-runs/2026-05-20/report.md` scaffold created with PENDING markers. | Tick boxes and replace PENDING with PASS/FAIL after the dry run. |
| 4 | Bundle README references `docs/` that doesn't exist | `artifacts/phase-62/desktop-bundle/docs/` now holds 12 read-only copies + index README. | None — fixed in the repo. |
| 5 | "Provider-Reviewed VisitDraft Assist" treated as live UI label | Every doc now distinguishes narration vs on-screen UI title; the operator says VisitDraft, the screen says Ambient Documentation. | None — fixed in the repo. |
| 6 | `run-safety-checks.sh` fails Alembic with system python3 | Wrapper now exports `PYTHON` from the API venv when available; warns + falls back otherwise. | Ensure the API venv exists at `apps/api/.venv/`. |

## Source-safety status (re-verified at Phase 62A merge)

| Check | Status |
|---|---|
| `scripts/check_runtime_safety.py` | PASS |
| `scripts/check_commercial_claims.sh` | PASS |
| `scripts/check_website_claims.sh` | PASS |
| `scripts/check_demo_claims.sh` | PASS |
| `scripts/test_claim_policy_fixtures.sh` | PASS |
| `scripts/check_alembic_safety.sh` | PASS (run via API venv) |
| `git diff --check` | clean |

## What flips the signal to GO

1. The operator runs `bash run-safety-checks.sh` from
   `~/Desktop/ChartNav-Buyer-Demo-Build/` on the iMac — all six
   sections PASS.
2. The operator captures all 30 PNGs into
   `artifacts/phase-62/screenshots/` per the shot list.
3. The operator captures all 12 MOVs into
   `artifacts/phase-62/video-clips/` per the shot list.
4. The operator completes `artifacts/phase-62/dry-runs/2026-05-20/report.md`
   with PASS lines and no triggered stop-demo conditions.
5. A teammate spot-checks the captures for forbidden text /
   real-PHI exposure / vendor-key leakage and signs off in the
   report's § 6.

Until all five hold simultaneously, status is **NO-GO**.

## Related documents

- `docs/build/phase-62a-demo-evidence-repair-audit.md`
- `docs/build/phase-62-demo-dry-run-preflight-audit.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
- `docs/demo/phase-62-local-build-delivery.md`
- `docs/build/current-product-truth.md`
- `docs/release/release-evidence-checklist.md`
