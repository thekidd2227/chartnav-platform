# Phase 19C — media-review tooling

Helper that bootstraps a clean **media-review folder** on the
operator's Desktop, archives pre-Phase-19B media into it, and
captures fresh Phase-19B screenshots using Playwright.

**This tooling never commits image binaries to the repo.**
Output writes to the operator's Desktop, outside the working
tree.

## Prerequisites

1. Node 18+ on `PATH`.
2. `apps/web/node_modules/` populated:
   ```bash
   cd apps/web && npm install
   ```
3. Chromium for Playwright:
   ```bash
   cd apps/web && npx playwright install chromium
   ```
4. Python venv at `apps/api/.venv` with backend deps installed
   (the spec's `webServer:` boots a real backend). `make install`
   from the repo root sets this up if missing.

You do **NOT** need `make dev` running — the Playwright spec
boots its own isolated stack on ports 8001 / 5174 (the same
ports CI uses) and tears it down on exit.

## Run it

```bash
bash tools/media-review/capture_phase19c_media.sh
```

What happens, in order:

1. Creates the canonical 9-folder structure under
   `$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/`.
2. `rsync` archives any existing pre-Phase-19B Desktop media
   folders into `05_Archive_Pre_Phase19B/`. **Originals are
   not deleted.**
3. Drops README + REVIEW_ORDER + CLIP_CAPTURE_INSTRUCTIONS +
   media manifest into the review folder.
4. Delegates to `npx playwright test --project=chromium tests/media-review/capture-phase19b.spec.ts`,
   which boots a clean stack on ports 8001 / 5174, walks the
   10 Phase-19B tabs, and writes 10 PNGs into
   `01_New_Screenshots/`. If this step fails, the script prints
   targeted next-step instructions and still leaves the folder
   structure + archive in place.

## Override the destination

```bash
CHARTNAV_MEDIA_REVIEW_DIR="$HOME/path/to/review" \
  bash tools/media-review/capture_phase19c_media.sh
```

## Files

| File | Purpose |
|---|---|
| `capture_phase19c_media.sh` | Bash entry point — folder bootstrap, archive, template generation, delegation to Playwright |
| `../../apps/web/tests/e2e/capture-phase19c-media-review.spec.ts` | Playwright spec that drives the 10-tab capture using the existing CI-tested harness. Lives in `tests/e2e/` so `playwright.config.ts` discovers it; auto-skips unless `CAPTURE_OUT_DIR` is set so it never runs on a normal e2e dev pass. |
| `README.md` | This file |

## Why this delegates to `npx playwright test` instead of running
Playwright directly from a Node script

Earlier iteration of this tooling imported Playwright from a
standalone `.mjs` script. On at least one Mac that produced:

```
Cannot find module './mcp/test/browserBackend'
Require stack:
- apps/web/node_modules/playwright/lib/index.js
```

This is a known symptom of a partially-upgraded Playwright
install (the `playwright` package's MCP modules go missing if
`@playwright/test` was upgraded mid-session). Switching to
`npx playwright test` uses the *same* code path that CI's
`E2E — Playwright against live stack` job runs every day —
which means if CI is green, capture works. The trade-off is a
~15s extra boot for the spec's `webServer:`; in exchange we
get a known-good harness.

## What this tooling does NOT do

- It does not delete any original Desktop folder.
- It does not overwrite `~/Desktop/ChartNav Final Delivery/`
  (which doesn't actually exist as a script output anyway —
  `create_chartnav_desktop_demo_package.sh` writes to
  `~/Desktop/chartnav decks/`).
- It does not commit any image / video binary to the repo.
- It does not capture video clips. A capture-instructions
  template is dropped instead — record manually with QuickTime
  or OBS using the seeded fake-data demo.
- It does not push captured assets to the live website. That's
  a separate phase, gated on the operator's visual approval.
