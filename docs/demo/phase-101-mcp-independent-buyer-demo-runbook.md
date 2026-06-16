# Phase 101 — MCP-Independent Buyer Demo Runbook

**Status:** operator runbook
**Date:** 2026-06-15
**Audience:** ChartNav operator capturing buyer-demo evidence on a
local workstation **without** MCP Filesystem or Kapture Browser
Automation
**Branch:** `feature/phase-101-mcp-independent-buyer-demo-evidence-capture`

## Purpose

The previous local environment showed:

```
Could not attach to MCP server Filesystem
Could not attach to MCP server Kapture Browser Automation
```

Buyer-demo evidence capture must still be possible when those
servers are unavailable. This runbook walks the operator through
the repo-native path: existing shell scripts, Playwright (which
ships in `apps/web/node_modules`), and manual fallbacks when no
local stack is reachable.

## Hard rules

- **No real PHI.** Fake-data demo only. The reset script refuses
  non-loopback `DATABASE_URL`.
- **No production LLM.** Every LLM-shaped surface is
  deterministic / fake adapter / disabled.
- **No live vendor scripts.** Do not source `.env.prod`. Do not
  enable a live STT vendor. Do not point at a real practice EHR or
  FHIR endpoint.
- **No MCP Filesystem.** Capture must work without it.
- **No Kapture Browser Automation.** Capture must work without it.
- **No autonomous-decision narration.** See Phase 93 dry-run
  forbidden-narration list.

## 0. Local setup assumptions

Before running anything below, confirm:

| # | Item | Expected |
|---|---|---|
| 0.1 | Repo cloned to `$CHARTNAV_REPO_PATH` (defaults to `$HOME/Desktop/ARCG/chartnav-platform`) | yes |
| 0.2 | `bash`, `git`, `python3`, `curl` on PATH | yes |
| 0.3 | `apps/api/.venv` exists OR `python3` on PATH satisfies the backend tier 1 release gate | yes |
| 0.4 | `apps/web/node_modules` is installed (`npm ci` if not) | yes |
| 0.5 | Working tree clean (`git status --short` empty) | yes |

If row 0.4 is false, run `cd apps/web && npm ci` once. This pulls
Playwright as a dev dependency; **no new dependencies are
introduced by Phase 101**.

## 1. Repo sync

```bash
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull --ff-only origin main
git log --oneline -5
git status --short
```

If the working tree is dirty or `git pull` reports conflicts,
**stop**. Capture evidence only against a clean SHA so the launch
gate artifact is reproducible.

## 2. Demo reset

```bash
bash scripts/reset_demo_state.sh
```

Expected: exit 0; refuses any non-loopback `DATABASE_URL`. If the
reset refuses to run, confirm `DATABASE_URL` is
`sqlite:///./chartnav.db` or `postgres://…@127.0.0.1`. **Do not**
override.

## 3. Backend + frontend startup

The repo ships two paths. Use whichever fits the workstation.

### 3.a Playwright-driven (preferred — Playwright boots both)

Playwright's `webServer` block in `apps/web/playwright.config.ts`
boots both servers against an ephemeral SQLite DB on
`127.0.0.1:8001` (API) + `127.0.0.1:5174` (web). The operator's
dev DB is **not** touched.

```bash
cd "$CHARTNAV_REPO_PATH/apps/web"
npx playwright install --with-deps chromium     # one-time
npm run test:e2e -- --reporter=list             # runs e2e suite end-to-end
```

This produces:

- `apps/web/test-results/` — Playwright trace / video / screenshot
  artifacts on failure (no-failure runs ship clean).
- `apps/web/playwright-report/` — HTML report (open with
  `npx playwright show-report` after the run).

### 3.b Manual two-shell startup

If the operator wants to drive a buyer demo by hand rather than
through Playwright:

```bash
# shell 1 — backend
cd "$CHARTNAV_REPO_PATH/apps/api"
DATABASE_URL="sqlite:///./chartnav.db" \
PATH="$PWD/.venv/bin:$PATH" \
uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level warning

# shell 2 — frontend
cd "$CHARTNAV_REPO_PATH/apps/web"
VITE_API_URL="http://127.0.0.1:8765" npm run dev -- --host 127.0.0.1 --port 5173
```

Then point a browser at `http://127.0.0.1:5173`.

## 4. Phase 100 launch gate

```bash
cd "$CHARTNAV_REPO_PATH"
bash scripts/release/phase100_controlled_pilot_launch_gate.sh
```

Output lands under
`artifacts/phase-100-controlled-pilot-launch/<YYYYMMDD-HHMMSS>/`
with `summary.txt` + `go-no-go.txt`. **Required** for buyer-demo
GO.

## 5. Phase 63C functional smoke (optional if a live stack runs)

If the manual two-shell startup is up at the documented ports,
run the smoke:

```bash
cd "$CHARTNAV_REPO_PATH"
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh --reset
```

The smoke creates vitals / visit-draft / fundus artifacts against
the seeded fake Morgan Lee encounter. Output goes to stdout +
stderr; capture both into the buyer-demo artifact dir using
`scripts/demo/phase101_mcp_independent_demo_capture.sh` (Section 7).

If no live stack is reachable, the smoke is **skipped** — not a
GO blocker (Phase 100 gate is the authoritative release-side
signal).

## 6. Playwright screenshot + video capture fallback

The repo ships two existing capture scripts:

- `scripts/demo/phase63a_capture_demo_media.mjs` — automated
  Playwright capture of the documented Phase 62 shot list.
- `apps/web/tests/screenshot-capture.mjs` — clinical-shortcuts
  screenshot harness.

Both require a reachable local stack (Section 3.b) and Playwright
installed (Section 3.a one-time install). They write artifacts
under:

- `artifacts/phase-62/screenshots/` — PNG shots
- `artifacts/phase-62/video-clips/` — webm clips
- `qa/screenshots/` — clinical-shortcuts shots

To run the existing Phase 63A capture against a manual stack:

```bash
cd "$CHARTNAV_REPO_PATH"
node scripts/demo/phase63a_capture_demo_media.mjs
```

If the stack is **not** reachable, skip this step and fall back
to Section 7.

## 7. Manual screenshot fallback (no Playwright / no MCP)

When Playwright or the local stack is unavailable, the operator
still has a path: capture screenshots manually using the OS's
native screenshot tool against the prior recorded media under
`artifacts/phase-62/`, **OR** rely entirely on the Phase 100 gate
artifact bundle as the release-side evidence.

The repo never blocks a buyer-demo GO on browser screenshots
alone — the screenshots are accompaniment to the gate output.

Steps:

1. Open one or more reference shots from `artifacts/phase-62/`
   or the existing buyer evidence packet
   (`docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`).
2. Note any updated panel positions or labels the operator wants
   to re-capture for the current SHA.
3. Drop the new manual screenshots into
   `artifacts/buyer-demo/<YYYYMMDD-HHMMSS>/manual-screenshots/`
   (created by the Phase 101 capture script when missing).
4. Record the manual screenshot list in
   `missing-evidence.txt` under that dated dir so the operator can
   document what is **not** machine-captured this run.

## 8. Run the Phase 101 capture script

```bash
cd "$CHARTNAV_REPO_PATH"
bash scripts/demo/phase101_mcp_independent_demo_capture.sh
```

This script:

- Creates `artifacts/buyer-demo/<YYYYMMDD-HHMMSS>/`.
- Runs the Phase 100 launch gate; saves the per-check breakdown.
- Runs Phase 63C smoke **only** if `PHASE63C_API_URL` +
  `PHASE63C_WEB_URL` are set and the URLs answer.
- Runs Playwright capture **only** if `apps/web/node_modules`
  ships `@playwright/test` and the local stack is reachable.
- Collects existing screenshots / videos from
  `artifacts/phase-62/` into the buyer-demo dir.
- Writes `summary.txt`, `no-real-phi-attestation.txt`, and
  `missing-evidence.txt`.
- Exits non-zero **only** when a required gate (Phase 100) fails.

## 9. No-real-PHI warning

Every artifact this runbook produces is labelled `demo mode — no
real PHI`. Read aloud Section 1 of
`docs/security/phase-100-no-real-phi-attestation.md` before any
buyer conversation that uses captured evidence. Do not present
captured screenshots as "real-PHI ready evidence" — captured
output is fake-data evidence only.

## 10. Recovery steps

| Symptom | Recovery |
|---|---|
| `git pull` reports conflict | Stop. Resolve out of band. Capture cannot run against a dirty tree. |
| `bash scripts/reset_demo_state.sh` refuses | Confirm `DATABASE_URL` is loopback. Do not override. |
| Phase 100 gate FAIL on R1/R2/R3 | Open the per-check log under the gate's artifact dir; follow the recovery hint at the top of `scripts/release/phase100_controlled_pilot_launch_gate.sh`. Do not run the demo. |
| Phase 63C smoke fails on a single step | Re-run with `--reset` (already on by default in the Phase 101 capture). Do not skip the failing step. |
| Playwright capture errors with "executable not found" | `cd apps/web && npx playwright install --with-deps chromium`. |
| Local stack unreachable | Capture script auto-skips Playwright + Phase 63C smoke. Phase 100 gate still runs and is authoritative. |
| MCP Filesystem error in operator terminal | Ignore. Phase 101 does not depend on MCP. |
| Kapture Browser Automation error | Ignore. Phase 101 does not depend on Kapture. |
| Claim scanner flags a doc | Open the flagged file, fix the language, re-run. Do not allowlist around the scanner. |

## 11. What the operator hands the buyer

After a clean run of the Phase 101 capture script:

1. The dated artifact dir
   `artifacts/buyer-demo/<YYYYMMDD-HHMMSS>/` (PII-clean — fake data
   only).
2. The Phase 100 launch gate `summary.txt` + `go-no-go.txt`.
3. The Phase 93 pilot launch gate `summary.txt`.
4. The Phase 100 controlled-pilot launch GO/NO-GO form
   (`docs/pilot/phase-100-controlled-pilot-launch-gate.md`) for
   the practice's signature page.
5. The Phase 100 no-real-PHI attestation
   (`docs/security/phase-100-no-real-phi-attestation.md`) for the
   practice's countersignature.
6. The Phase 101 evidence matrix
   (`docs/demo/phase-101-buyer-demo-evidence-matrix.md`) showing
   what was machine-captured vs manual-captured vs skipped on
   this SHA.
