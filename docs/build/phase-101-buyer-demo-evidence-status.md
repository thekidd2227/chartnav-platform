# Phase 101 — Buyer Demo Evidence Status

**Date:** 2026-06-15
**Branch:** `feature/phase-101-mcp-independent-buyer-demo-evidence-capture`
**Base:** `main` after Phase 100 (`398f0e9`)
**Status:** non-feature operator-tooling phase — adds a
repo-native buyer-demo evidence capture path that does not
depend on MCP Filesystem or Kapture Browser Automation.

## Purpose

The previous local environment reported that two MCP servers
could not attach:

```
Could not attach to MCP server Filesystem
Could not attach to MCP server Kapture Browser Automation
```

Buyer-demo evidence capture must remain possible without those
servers. Phase 101 ships:

1. A four-document operator package the operator can read on a
   workstation with no MCP / no Kapture.
2. One repo-native capture script that writes a dated artifact
   bundle the operator hands to the buyer.
3. A talk track and an evidence matrix that the operator can
   pair with the Phase 100 buyer demo script.

No clinical features were added. No clinical workflow behavior
was changed. No tests were weakened. No safety scanners were
silenced. No real PHI is processed by anything in this phase.

## Hard rules upheld

- No new clinical features.
- No new autonomous decision-making.
- No diagnosis / image interpretation / treatment / surgery /
  medication / IOL recommendation.
- No submission to registries, payers, CMS, IRIS, or EHRs.
- No production LLM. No live vendor scripts. No secrets touched.
- No real PHI in any environment produced by this phase.
- No HIPAA / SOC 2 / HITRUST / FDA / "certified EHR" /
  "EHR replacement" claims.
- No reliance on MCP Filesystem.
- No reliance on Kapture Browser Automation.

## Whether buyer demo is GO / CONDITIONAL GO / NO-GO

**CONDITIONAL GO for a controlled fake-data buyer demo.**

- Every Phase 100 release-side gate is GREEN on this SHA.
- The Phase 101 capture script `R1` PASS produces the operator's
  release-side evidence bundle.
- Phase 101 optional stages (O1 Phase 63C smoke, O2 Playwright
  capture, O3 existing Phase 62 media collection) skip cleanly
  on a workstation without a running local stack and do not
  block the GO recommendation.

**NO-GO for a real-PHI buyer demo.** Real PHI requires every
gate in `docs/security/phase-93-real-phi-readiness-review.md`,
`docs/security/phase-100-no-real-phi-attestation.md`, and
`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` to
close with written, dated, attributable evidence.

## What evidence was captured

When the operator runs:

```bash
bash scripts/demo/phase101_mcp_independent_demo_capture.sh
```

the script produces under
`artifacts/buyer-demo/<YYYYMMDD-HHMMSS>/`:

- `summary.txt` — per-stage table + overall PASS/FAIL +
  buyer-demo recommendation (CONDITIONAL GO / NO-GO)
- `no-real-phi-attestation.txt` — explicit non-authorization
  statement carried into the buyer-facing bundle
- `missing-evidence.txt` — every optional stage that was skipped
  or failed, plus an operator-fill area for manual screenshots
- `01-phase100-launch-gate.log` — full Phase 100 gate output
- `phase-100-controlled-pilot-launch/` — symlink/copy of the
  underlying Phase 100 bundle (which contains the Phase 93 +
  Phase 88 evidence by transitive delegation)
- `manual-screenshots/` — always-created empty directory where
  the operator drops any manually-captured screenshots before
  handing the dir to the buyer

When O1, O2, O3 stages run successfully (live stack reachable +
Playwright installed), the script additionally produces:

- `O1-phase63c-smoke.log` — Phase 63C functional smoke output
- `O2-playwright-capture.log` — Playwright capture stdout
- `O3-existing-media-collect.log` — existing-media copy log
- `screenshots/*.png` — collected from
  `artifacts/phase-62/screenshots/`
- `videos/*.webm` — collected from
  `artifacts/phase-62/video-clips/`

## What evidence is missing

The Phase 101 capture script writes `missing-evidence.txt` on
every run with the per-stage skip / fail ledger. On a clean
workstation without a running local stack, the operator should
expect the following rows to be marked SKIP:

| Row | Reason |
|---|---|
| O1 Phase 63C functional smoke | `PHASE63C_API_URL` / `PHASE63C_WEB_URL` not set or unreachable |
| O2 Playwright demo media capture | `@playwright/test` not installed (run `cd apps/web && npm ci`) OR local stack not reachable |
| O3 Existing Phase 62 media collection | source dirs empty when no prior Playwright capture has run |

These SKIPs do not block the buyer-demo CONDITIONAL GO. They are
recorded so the operator can hand the buyer an accurate evidence
ledger and so a follow-up workstation with a running stack can
fill the gap.

## Whether Phase 63C smoke ran

Conditional. The Phase 101 capture script runs the smoke **only**
when both `PHASE63C_API_URL` and `PHASE63C_WEB_URL` are set to
URLs that answer. On a sandbox / CI workstation without a local
stack, the smoke is **skipped** and logged under
`missing-evidence.txt`.

## Whether browser screenshots / videos ran

Conditional. The Phase 101 capture script runs the existing
Playwright capture (`scripts/demo/phase63a_capture_demo_media.mjs`)
**only** when all four are true:

1. `apps/web/node_modules/@playwright/test/package.json` exists
   (`npm ci` has been run in `apps/web/`).
2. The local stack is reachable (the Phase 63C reachability
   probe in the script succeeded).
3. The capture script exists at the expected path.
4. Chromium is installed under `$HOME/.cache/ms-playwright`
   (run `cd apps/web && npx playwright install --with-deps chromium`
   once per workstation). Chromium absence is now a clean SKIP, not
   a FAIL — the capture log records the SKIP reason verbatim so a
   later capture on the same SHA can fill the row.

When the local stack runs at non-default ports (the user's
verified setup uses 8765/5173 — not the historical 8000/5173 the
capture script's defaults baked in), the Phase 101 capture script
plumbs `PHASE63C_API_URL` and `PHASE63C_WEB_URL` through to the
Playwright capture as `E2E_API_URL` and `E2E_BASE_URL` so the
capture targets the right host without the operator editing the
script.

Otherwise the script falls back to O3 (collect any existing
Phase 62 media) and skips O2 cleanly.

## Whether MCP / Kapture were required

**No.** Phase 101 is engineered so that:

- The capture script uses only `bash`, `git`, `curl`, `python3`,
  and the Playwright runtime that already ships in
  `apps/web/node_modules`. No MCP server, no Kapture, no new
  external dependency.
- The four documents reference repo-internal artifacts only —
  no MCP-served paths, no Kapture-driven browser invocations.
- The Phase 101 runbook explicitly notes that MCP Filesystem and
  Kapture errors in the operator's terminal can be **ignored**;
  Phase 101 does not call into either.

## Next recommended action

1. **Boot the local stack** at the documented ports (8765 / 5173):
   ```bash
   # one-time seed (venv-free; works on workstations without
   # apps/api/.venv)
   bash scripts/demo/phase101_local_seed_sqlite.sh

   # API on 8765
   cd apps/api
   DATABASE_URL="sqlite:///./chartnav.db" \
     CHARTNAV_ENV=local CHARTNAV_LLM_ENABLED=0 \
     CHARTNAV_RATE_LIMIT_PER_MINUTE=0 \
     uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level warning &

   # Web on 5173
   cd ../web
   VITE_API_URL="http://127.0.0.1:8765" \
     npx vite --host 127.0.0.1 --port 5173 &
   ```
2. **Run the Phase 101 capture script** on the launch SHA — with
   `PHASE101_SMOKE_RESET=0` when the workstation lacks
   `apps/api/.venv`:
   ```bash
   PHASE101_SMOKE_RESET=0 \
   PHASE63C_API_URL="http://127.0.0.1:8765" \
   PHASE63C_WEB_URL="http://127.0.0.1:5173" \
   bash scripts/demo/phase101_mcp_independent_demo_capture.sh
   ```
   On a workstation that does ship the venv, omit
   `PHASE101_SMOKE_RESET=0` and the smoke runs with `--reset` per
   the repo-default posture.
2. **Open the dated artifact dir** and confirm:
   - `summary.txt` shows `OVERALL: PASS` and
     `BUYER-DEMO RECOMMENDATION: CONDITIONAL GO`.
   - `no-real-phi-attestation.txt` is present and unmodified.
   - `missing-evidence.txt` lists only the expected SKIP rows.
3. **Pair the bundle with the Phase 100 GO/NO-GO form**
   (`docs/pilot/phase-100-controlled-pilot-launch-gate.md`).
   Walk the practice's clinical + administrative + ARCG ops +
   ARCG commercial owners through the signature page.
4. **Use the Phase 101 buyer demo talk track** during the
   controlled demo. The closing ask is Section 4 of
   `docs/demo/phase-101-buyer-demo-talk-track.md` — verbatim,
   not paraphrased.
5. **Hand the buyer**:
   - The dated artifact dir (PII-clean — fake data only).
   - The Phase 100 launch gate `summary.txt` + `go-no-go.txt`.
   - The Phase 100 launch GO/NO-GO form.
   - The Phase 100 no-real-PHI attestation.
   - The Phase 101 evidence matrix updated with the per-row
     status.

## Files

### New (Phase 101)

- `docs/demo/phase-101-mcp-independent-buyer-demo-runbook.md`
- `docs/demo/phase-101-buyer-demo-evidence-matrix.md`
- `docs/demo/phase-101-buyer-demo-talk-track.md`
- `docs/build/phase-101-buyer-demo-evidence-status.md`
- `scripts/demo/phase101_mcp_independent_demo_capture.sh`

### Modified

- `.gitignore` — gitignore `artifacts/buyer-demo/` (added in this
  phase's commit) to match the Phase 88 + Phase 93 + Phase 100
  pattern.

No source changes. Zero TypeScript / Python diff outside docs +
scripts.

## Risks closed

- **MCP / Kapture dependency surface.** Phase 101 is the first
  buyer-demo operator path that does not assume MCP Filesystem
  or Kapture Browser Automation are attached. If they are
  unavailable on the operator's workstation, the buyer-demo path
  still completes.
- **Single-command buyer-evidence assembly.** The Phase 101
  capture script collapses Phase 100 launch gate + optional
  Phase 63C smoke + optional Playwright capture + optional
  existing-media collection + no-real-PHI attestation + missing-
  evidence ledger into one operator command, one dated bundle.
- **Demo-narration drift.** The Phase 101 talk track ships a
  verbatim 15-minute + 30-minute script audited against the
  Phase 93 forbidden-narration list, and a verbatim closing ask
  that splits the fake-data pilot review from the real-PHI
  readiness approvals into two parallel tracks.
- **Evidence-row ambiguity.** The Phase 101 evidence matrix
  enumerates every panel + signal a buyer expects, distinguishes
  required vs optional, and routes each row to either the
  machine-capture path (Phase 100 gate / vitest / Phase 63C
  smoke / Playwright) or a manual-screenshot fallback under
  `manual-screenshots/`.
