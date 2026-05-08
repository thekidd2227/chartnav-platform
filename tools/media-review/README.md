# Phase 19C — media-review tooling

Helper scripts that bootstrap a clean **media-review folder**
on the operator's Desktop, archive the pre-Phase-19B media into
that folder, and capture fresh screenshots of the Phase 19B
clinical UI against the local fake-data demo route.

**This tooling never commits image binaries to the repo.**
Output writes to the operator's Desktop, outside the working
tree.

## Prerequisites

1. Node 18+ on `PATH`.
2. `apps/web/node_modules/` populated (`npm --prefix apps/web install`).
3. Local stack running on `http://127.0.0.1:5173`:
   ```bash
   make dev
   ```
4. Identity chip reading **Identity Admin · Org 1** in the
   browser (the seeded admin@chartnav.local user).

## Run it

```bash
bash tools/media-review/capture_phase19c_media.sh
```

That will:

1. Create the canonical review folder structure under
   `$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/`.
2. `rsync` archive any existing pre-Phase-19B Desktop media
   folders into `05_Archive_Pre_Phase19B/`. **Originals are
   not deleted.**
3. Drop README + REVIEW_ORDER + CLIP_CAPTURE_INSTRUCTIONS +
   media manifest into the review folder.
4. If the local stack is reachable, run Playwright headless
   and write 10 PNGs into `01_New_Screenshots/`. If the stack
   isn't reachable the script skips capture cleanly and tells
   you what to do.

## Override the destination

```bash
CHARTNAV_MEDIA_REVIEW_DIR="$HOME/path/to/review" \
  bash tools/media-review/capture_phase19c_media.sh
```

## Override the base URL

```bash
CHARTNAV_DEMO_URL="http://127.0.0.1:5173" \
  bash tools/media-review/capture_phase19c_media.sh
```

## Files

| File | Purpose |
|---|---|
| `capture_phase19c_media.sh` | Bash entry point (folders + archive + templates + delegates to capture script) |
| `capture_phase19c_screenshots.mjs` | Playwright headless capture (Node ESM) |
| `README.md` | This file |

## What this tooling does NOT do

- It does not delete the operator's original Desktop folders.
- It does not overwrite `~/Desktop/ChartNav Final Delivery/`.
- It does not commit screenshots, clips, or any binary to the
  repo.
- It does not capture video clips. A capture-instructions
  template is dropped instead — record manually with QuickTime
  or OBS.
- It does not push captured assets to the live website. That's
  a separate phase, gated on the operator's visual approval.
