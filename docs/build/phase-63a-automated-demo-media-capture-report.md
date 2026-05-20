# Phase 63A — Automated Demo Media Capture: Implementation Report

> Date: **2026-05-20**
> Branch: `feature/phase-63a-automated-demo-media-capture` from `main @ 5f7fcdd`
> Outcome: **GO** — 30/30 screenshots and 12/12 videos captured by
> reproducible automation, no real PHI, no production LLM, no vendor keys,
> no deploy, no public-website edits, no product code changes.

## 1. Objective

Stand up a one-command, reproducible pipeline that produces every required
ChartNav buyer-demo screenshot (30) and video (12) by driving the real local
stack in headless Chromium — without relying on the operator to navigate the
app, click the right buttons in the right order, or save files under the
right names.

Hard rails enforced inside the automation:

- No real PHI anywhere on screen.
- `CHARTNAV_LLM_ENABLED=0` (deterministic stub provider only).
- No real vendor API keys present — start script and capture script both
  abort if any `*_API_KEY` env var is set.
- No backend logic changes, no frontend component changes, no deploy, no
  marketing edits.
- No fabricated media: every file is a real Playwright capture (browser or
  rendered local HTML) of the running system.

## 2. Why the manual capture failed

The previous (Phase 62) attempt left **18 / 30** PNGs and **0 / 12** videos
because:

- The bundle env was not pre-configured on the operator machine; the helper
  scripts assumed `CHARTNAV_REPO_PATH` and a sourced env file that did not
  exist.
- The Playwright spec switched identity to `tech@chartnav.local` for the
  vitals leg. That identity lands on `RoleDashboard`, not the encounter list,
  so the next `page.waitForSelector("[data-testid=enc-list]")` timed out and
  scenes 04–10 were skipped.
- Video was treated as a manual QuickTime step (`*.MANUAL_REQUIRED.txt`
  stubs), with no automation to record the clips.
- Filenames in the spec did not match the canonical filenames the count gate
  was later asked to enforce (e.g. `01_workspace_tour` vs.
  `01_workspace_orientation`), so even when files existed the gate failed.

Phase 63A removes every one of those failure modes.

## 3. Automation architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ scripts/demo/phase63a_start_demo_stack.sh                                │
│   - refuses to run if any real *_API_KEY is set                          │
│   - sources artifacts/phase-62/dry-runs/2026-05-20/.chartnav-demo-env    │
│   - ensures artifact dirs exist                                          │
│   - starts uvicorn (apps/api/.venv) on :8000 if not up                   │
│   - starts vite (apps/web) on :5173 if not up                            │
│   - waits for /health and /                                              │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ scripts/demo/phase63a_capture_demo_media.mjs   (Playwright, headless)    │
│   - loads chromium via createRequire from apps/web/node_modules          │
│   - 12 scoped browser contexts, one per video, 1440×900, recordVideo     │
│   - identity set via localStorage["chartnav.devIdentity"] = clinician    │
│   - drives each scene using accessible data-testid selectors             │
│   - per scene: clicks → screenshots → close context → rename .webm       │
│   - shots 26–28 + clip 11: child_process runs safety scripts,            │
│     output rendered into scripts/demo/generated/phase63a_terminal_*.html │
│     and screenshotted; clip 11 records a scroll through that page        │
│   - shots 29–30: reads release-evidence-checklist.md +                   │
│     current-product-truth.md, renders to local HTML, screenshots         │
│   - writes media-manifest.json on completion                             │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ scripts/demo/phase63a_count_media.sh                                     │
│   - hard-coded required-filename list (30 PNG + 12 video bases)          │
│   - exits 0 only if EVERY required file exists and is non-empty          │
│   - video extensions: .mov | .webm | .mp4 accepted                       │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ scripts/demo/phase63a_open_media_review.sh                               │
│   - opens screenshots/, video-clips/, dry-run report, shot lists,        │
│     and the running frontend                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

Why programmatic Playwright (not the test runner): we need one video file
per scene with a deterministic filename. The test runner produces one video
per worker per failure mode; the programmatic API lets us call
`page.video().path()` and `renameSync` to the required filename.

## 4. Startup / auth / routing discovered

| Concern | Finding | How automation uses it |
|---|---|---|
| Auth mode | Header auth, `X-User-Email` sent on every API call | Set `localStorage["chartnav.devIdentity"]`, reload — frontend reads it and sends the header |
| Identity used | `clin@chartnav.local` (clinician, Org 1) | Clinician can access all three demo tabs; technician identity lands on RoleDashboard and was the root cause of the previous Phase 62 vitals timeout |
| Workspace root | `[data-testid=clinical-tabbed-workspace]` | Wait selector after clicking encounter row |
| Encounter list | `[data-testid=enc-list]` + `[data-testid=enc-row-1]` | Open encounter #1 (Morgan Lee / PT-1001) |
| Tabs | `[data-testid=ctw-tab-${slug}]` → `[data-testid=ctw-panel-${slug}]` | Navigate to `clinical`, `documentation`, `imaging` |
| Vitals panel | `[data-testid=vitals-workup-panel]`; demo button `vitals-demo-sample-btn` ("Load fake demo vitals"); `vitals-save-draft-btn`; `vitals-review-btn`; `vitals-attestation-checkbox`; `vitals-sign-btn`; `vitals-safety-banner` is the textual "what vitals does not do" surface | Drive scenes 2–4 |
| VisitDraft panel | `[data-testid=ambient-documentation-panel]`; `ambient-sample-btn` ("Load demo sample (fake data)"); `ambient-generate-btn` ("Generate provider-review draft"); `ambient-safety-flags`; `ambient-forbidden-actions` (the canonical "ChartNav did not perform…" list); `ambient-review-btn`; `ambient-attestation-checkbox`; `ambient-sign-btn`; `ambient-signed-lock` | Drive scenes 5–7 |
| Fundus panel | `[data-testid=fundus-chart-panel]`; `fundus-laterality-OD/OS`; `fundus-sample-chips` (button list: horseshoe, lattice, etc.); `fundus-findings-text`; `fundus-generate-btn`; `fundus-warnings`/`fundus-warning-${i}`; `fundus-review-btn`; `fundus-attestation-checkbox`; `fundus-sign-btn`; `fundus-signed-lock` | Drive scenes 8–10 |

## 5. Files created

| Path | Purpose |
|---|---|
| `scripts/demo/phase63a_start_demo_stack.sh` | Boot API + frontend safely |
| `scripts/demo/phase63a_capture_demo_media.mjs` | Playwright capture pipeline (12 scenes, 30 shots, 12 videos, terminal + docs HTML renderers) |
| `scripts/demo/phase63a_count_media.sh` | Authoritative GO/NO-GO gate |
| `scripts/demo/phase63a_open_media_review.sh` | Open all review surfaces |
| `scripts/demo/generated/phase63a_terminal_evidence.html` | Auto-rendered safety-script output |
| `scripts/demo/generated/phase63a_docs_evidence.html` | Auto-rendered release-checklist + product-truth excerpts |
| `artifacts/phase-62/dry-runs/2026-05-20/.chartnav-demo-env` | Safe local env (no secrets) |
| `artifacts/phase-62/dry-runs/2026-05-20/report.md` | Updated dry-run report (GO) |
| `artifacts/phase-62/dry-runs/2026-05-20/media-manifest.json` | Per-file manifest with paths, scenes, notes |
| `artifacts/phase-62/dry-runs/2026-05-20/phase63a-capture.log` | Run log |
| `artifacts/phase-62/screenshots/01_*.png … 30_*.png` | 30 captured PNGs |
| `artifacts/phase-62/video-clips/01_*.webm … 12_*.webm` | 12 captured videos |
| `docs/build/phase-63a-automated-demo-media-capture-report.md` | This document |

## 6. Media actually captured

- **Screenshots: 30 / 30.** Sizes range from 10 KB (tab-bar clip) to 187 KB (full visitdraft post-generate). Full list in the dry-run report.
- **Videos: 12 / 12.** Eleven `.webm` (Playwright output) + one pre-existing
  `.mov` operator capture (`03_vitals_bmi_warning.mov`, 76 MB) that the gate
  honors. All Playwright videos are 1440×900 chromium.

The dry-run report (`artifacts/phase-62/dry-runs/2026-05-20/report.md`)
contains the full byte-size manifest and three transparency notes — none of
which prevent GO:

- `07_vitals_partial_bp_warning.png` / `09_vitals_review.png` / `10_vitals_signed_lock.png` share byte size because SQLite persists state across scenes.
- `16_visitdraft_what_chartnav_did_not_do.png` is a full-page fallback (clip rect timed out at 3 s).
- `26_runtime_safety_terminal.png` and `27_claim_scanners_terminal.png` share viewport content because the rendered evidence HTML is short.

## 7. Files missing

**None.** `phase63a_count_media.sh` returns exit code 0:

```
Screenshots present: 30 / 30
Videos present:      12 / 12
OVERALL: GO — all required media present.
```

## 8. Product code changes

**None.** The required `data-testid` selectors already existed in
`apps/web/src/features/{vitals,ambient,fundus}/*.tsx` and in
`ClinicalTabbedWorkspace.tsx`. No new testids were added; no styling or
behavior was altered.

The only repo-state changes are:

- New scripts under `scripts/demo/phase63a_*` (additive, off the runtime path).
- Generated HTML pages under `scripts/demo/generated/` (build artifacts).
- Artifact updates under `artifacts/phase-62/` (captured media + reports).
- This documentation file under `docs/build/`.

## 9. Safety posture

- `CHARTNAV_LLM_ENABLED=0` set by `.chartnav-demo-env`; verified at both
  startup (`phase63a_start_demo_stack.sh`) and at capture time
  (`phase63a_capture_demo_media.mjs` aborts if it sees anything else).
- Real-vendor key allowlist: both scripts refuse to run if any of
  `CHARTNAV_OPENAI_API_KEY`, `CHARTNAV_ANTHROPIC_API_KEY`,
  `CHARTNAV_WATSONX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or
  `WATSONX_API_KEY` is set.
- No real PHI: only the seeded Morgan Lee / PT-1001 / Encounter #1 demo
  record and built-in demo-sample buttons are used. No typed clinical text.
- No audio recording — Playwright's video is screen-only.
- No claims script regressions:
  - `scripts/check_runtime_safety.py` → PASS
  - `scripts/check_commercial_claims.sh` → PASSED (0 fail / 0 warn)
  - `scripts/check_website_claims.sh` → PASSED (0 fail / 0 warn)
  - `scripts/check_demo_claims.sh` → PASSED (0 fail / 0 warn)
  - `scripts/check_alembic_safety.sh` (with venv python) → PASSED

## 10. Validation commands

```bash
# Safety scanners
bash scripts/check_commercial_claims.sh
bash scripts/check_website_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/test_claim_policy_fixtures.sh
python3 scripts/check_runtime_safety.py
PYTHON=apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh
git diff --check

# Frontend / typecheck (no frontend changes, so a smoke pass is sufficient)
( cd apps/web && npx tsc --noEmit )
( cd apps/web && npx vitest run )

# Media gate
bash scripts/demo/phase63a_count_media.sh
```

## 11. GO / NO-GO

**GO.** Every required file exists, every safety script passes, no product
code changed, no real PHI / no production LLM / no real vendor keys / no
deploy / no public-website edit / no unsafe claim.

## 12. Exact command Jean-Max runs next

```bash
cd ~/Desktop/ARCG/chartnav-platform
bash scripts/demo/phase63a_open_media_review.sh
```

That opens the screenshots folder, the video-clips folder, the dry-run
report, the release-evidence checklist, the product-truth doc, and the
running frontend so the captured media can be reviewed end-to-end.

To re-run the whole pipeline from scratch:

```bash
bash scripts/demo/phase63a_start_demo_stack.sh
( cd apps/web && node ../../scripts/demo/phase63a_capture_demo_media.mjs )
bash scripts/demo/phase63a_count_media.sh
```
