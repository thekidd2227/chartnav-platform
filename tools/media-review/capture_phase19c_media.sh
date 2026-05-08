#!/usr/bin/env bash
# Phase 19C — bootstrap the ChartNav media-review package on the
# operator's Desktop and (optionally) capture fresh Phase-19B
# screenshots.
#
# What this script does:
#   1. Creates the canonical media-review folder structure under
#      $CHARTNAV_MEDIA_REVIEW_DIR (default:
#      $HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/).
#   2. Archives any existing pre-Phase-19B media folders into
#      05_Archive_Pre_Phase19B/ via rsync (timestamps preserved,
#      originals NOT deleted).
#   3. Drops three review templates into 00_START_HERE/ and
#      08_Capture_Manifest/.
#   4. If the local stack is running on http://127.0.0.1:5173,
#      kicks off Playwright headless and writes 10 PNGs into
#      01_New_Screenshots/. If the stack isn't reachable, the
#      script skips the capture and prints clear instructions.
#
# What this script does NOT do:
#   - It does not delete original Desktop folders.
#   - It does not overwrite the final-delivery package.
#   - It does not commit any binaries to the repo.
#   - It does not capture video clips. A capture-instructions
#     template is dropped so you can record manually with
#     QuickTime / OBS.
#
# Usage:
#   bash tools/media-review/capture_phase19c_media.sh
#
# Override the destination via:
#   CHARTNAV_MEDIA_REVIEW_DIR="$HOME/path/to/review" \
#     bash tools/media-review/capture_phase19c_media.sh
#
# Exit codes:
#   0  bootstrap done; capture either succeeded or was skipped
#   1  filesystem error (mkdir / rsync failed)
#   2  Node.js missing on PATH (capture skipped)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DEFAULT_REVIEW_DIR="$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B"
REVIEW_DIR="${CHARTNAV_MEDIA_REVIEW_DIR:-$DEFAULT_REVIEW_DIR}"
BASE_URL="${CHARTNAV_DEMO_URL:-http://127.0.0.1:5173}"

# Pre-Phase-19B Desktop source folders to archive (per Jean-Max's
# inventory). Missing folders are skipped silently.
ARCHIVE_SOURCES=(
  "$HOME/Desktop/Chartnav/chartnav imags"
  "$HOME/Desktop/Chartnav/ChartNav_Media_Central"
  "$HOME/Desktop/Chartnav/clips_final"
  "$HOME/Desktop/Chartnav/clips_generated"
  "$HOME/Desktop/Chartnav/raw_clips"
  "$HOME/Desktop/Chartnav/Screenshots"
  "$HOME/Desktop/Chartnav/Video_Clips"
)

echo "ChartNav Phase 19C — media review bootstrap."
echo "  review dir: $REVIEW_DIR"
echo "  base url:   $BASE_URL"
echo

# ---------------------------------------------------------------
# 1. Folder structure.
# ---------------------------------------------------------------

SUBDIRS=(
  "00_START_HERE"
  "01_New_Screenshots"
  "02_New_Website_Images"
  "03_New_Demo_Clips"
  "04_New_Raw_Captures"
  "05_Archive_Pre_Phase19B"
  "06_Selected_For_Website"
  "07_Selected_For_Decks"
  "08_Capture_Manifest"
)

for sub in "${SUBDIRS[@]}"; do
  mkdir -p "$REVIEW_DIR/$sub"
done
echo "1. ok — folder structure created at $REVIEW_DIR"

# ---------------------------------------------------------------
# 2. Archive pre-Phase-19B Desktop folders (rsync, originals kept).
# ---------------------------------------------------------------

echo
echo "2. Archiving pre-Phase-19B Desktop folders into 05_Archive_Pre_Phase19B/"
archived=0
skipped=0
for src in "${ARCHIVE_SOURCES[@]}"; do
  if [ -d "$src" ]; then
    base="$(basename "$src")"
    dst="$REVIEW_DIR/05_Archive_Pre_Phase19B/$base"
    mkdir -p "$dst"
    # -a preserves timestamps + perms; --quiet keeps log noise
    # down. We do NOT delete the source — operator decides when
    # to retire the originals.
    rsync -a "$src/" "$dst/"
    n="$(find "$dst" -type f | wc -l | tr -d ' ')"
    echo "   archived: $base ($n files)"
    archived=$((archived + 1))
  else
    skipped=$((skipped + 1))
  fi
done
echo "   summary: $archived archived, $skipped missing (skipped)"

# ---------------------------------------------------------------
# 3. Review templates (00_START_HERE/, 08_Capture_Manifest/).
# ---------------------------------------------------------------

echo
echo "3. Writing review templates"

cat > "$REVIEW_DIR/00_START_HERE/README_MEDIA_REVIEW.md" <<'README_EOF'
# ChartNav Media Review — Phase 19B

This folder is a **visual-review staging area** for screenshots,
website images, and demo clips that reflect the Phase 19B
clinical UI correction (10-tab clinical workspace, dark
grouped sidebar, sticky patient header with demographic strip,
review-only Billing tab, scoped #0f766e teal).

## What lives here

| Folder | Contents |
|---|---|
| `00_START_HERE/` | This README + `REVIEW_ORDER.md` |
| `01_New_Screenshots/` | Fresh PNG captures of the new UI |
| `02_New_Website_Images/` | Curated subset for the website |
| `03_New_Demo_Clips/` | Re-recorded demo clips (or instructions) |
| `04_New_Raw_Captures/` | Raw screen recordings before editing |
| `05_Archive_Pre_Phase19B/` | Old media folders, copied — **DO NOT** mix with the new captures |
| `06_Selected_For_Website/` | Operator-approved final website assets |
| `07_Selected_For_Decks/` | Operator-approved final deck assets |
| `08_Capture_Manifest/` | Spreadsheet-style index of every media file |

## Workflow

1. Review every PNG in `01_New_Screenshots/` against the
   reference design.
2. Pick website-ready images and copy them to
   `02_New_Website_Images/` (or use the suggested filenames in
   the manifest).
3. Capture (or re-record) the 8 demo clips per
   `03_New_Demo_Clips/CLIP_CAPTURE_INSTRUCTIONS.md`. Save raw
   captures into `04_New_Raw_Captures/` and edited clips into
   `03_New_Demo_Clips/`.
4. After visual approval: copy approved assets into
   `06_Selected_For_Website/` and `07_Selected_For_Decks/`.
5. Only **after** visual approval, run the website-asset
   replacement and final-delivery rebuild phases (Phase 19D+).

## Safety contract

- **Fake/demo data only.** Capture against
  `http://127.0.0.1:5173/?demo=1` with the seeded
  `admin@chartnav.local` identity. Never capture real PHI.
- **No image binaries in the repo.** This folder lives on the
  Desktop, outside the git working tree.
- **Old media is archived, not deleted.** If you decide to
  retire the originals, do it manually after visual approval.
- **Final delivery is untouched** until you say so.
README_EOF

cat > "$REVIEW_DIR/00_START_HERE/REVIEW_ORDER.md" <<'ORDER_EOF'
# Review order

Walk these in this order. Each one is annotated with the
Phase-19B contract it has to honor.

1. **`01_New_Screenshots/01_overview_tab.png`** — sticky patient
   header + demographic strip + 3-column card grid + dark
   sidebar with 5 grouped sections. API URL chip must be
   absent (demo mode hides it).
2. **`01_New_Screenshots/02_clinical_ophthalmology_tab.png`** —
   collapsible groups (Cornea / Retina / Glaucoma /
   Oculoplastics) + clinical-shortcut search + Phase 17B
   filtering banner.
3. **`01_New_Screenshots/03_documentation_emr_ehr_tab.png`** —
   `NoteWorkspace` mounts: transcript, extracted findings,
   AI draft, finalized note tiers visible.
4. **`01_New_Screenshots/04_imaging_tab.png`** — OD/OS retinal
   diagram via `EyeDiagramPanel` + imaging-notes empty state
   (no upload backend yet — controlled-pilot work).
5. **`01_New_Screenshots/10_billing_review_tab.png`** — loud
   disclaimer banner ("ChartNav does not auto-code, auto-bill,
   or submit claims") + 4 read-only cards (CPT Codes / Charges
   / Insurance Status / Billing Review Notes) + only View /
   Mark reviewed / Add note buttons (all disabled).
6. **`02_New_Website_Images/`** — your curated website subset.
7. **`03_New_Demo_Clips/`** — clips or capture instructions.

## Stop signs

If any screenshot shows:

- A "Submit Claim" / "Auto-code" / "Auto-bill" / "Send Claim" /
  "Charge Patient" / "Bill Insurance" button on **Billing**;
- A "Submit Order" / "Place Order" / "Send Referral" button on
  **Orders & Labs**;
- A "Send to Patient" / "Patient Portal" / "Automated Patient
  Message" surface on **Communications**;
- The dev API URL chip (`API http://localhost:8000`) anywhere;
- Real patient data;

…stop the review and file an issue. The Phase 19B safe-claims
contract is non-negotiable.
ORDER_EOF

cat > "$REVIEW_DIR/03_New_Demo_Clips/CLIP_CAPTURE_INSTRUCTIONS.md" <<'CLIPS_EOF'
# Phase 19B demo-clip capture instructions

Capture against `http://127.0.0.1:5173/?demo=1` with the seeded
`admin@chartnav.local` identity. Use QuickTime, OBS, or a
similar tool. Never capture real PHI. Save edited clips here
(`03_New_Demo_Clips/`); save unedited screen recordings into
`04_New_Raw_Captures/`.

## Pre-capture checklist

- [ ] Local stack running: `make dev` from the repo root.
- [ ] Browser at `http://127.0.0.1:5173/?demo=1`.
- [ ] Identity chip reads **Identity Admin · Org 1**.
- [ ] API URL chip is **NOT** visible.
- [ ] Encounter `enc-row-1` (Morgan Lee) selected.

## Required clips (8)

| File | Length | Tab(s) | Scene |
|---|---|---|---|
| `clip_01_overview_tab_reveal.mp4` | 10–15 s | Overview | Slow pan over the sticky patient header + demographic strip + 3-column card grid + dark sidebar |
| `clip_02_clinical_ophthalmology_navigation.mp4` | 15–20 s | Clinical / Ophthalmology | Click each collapsible group (Cornea → Retina → Glaucoma → Oculoplastics); pause briefly on each |
| `clip_03_documentation_workflow.mp4` | 20–30 s | Documentation / EMR/EHR | Paste sample transcript → ingest → generate draft → mark reviewed → finalize. End on the read-only finalized state |
| `clip_04_imaging_workspace.mp4` | 15–20 s | Imaging | OD/OS retinal diagram. Pan over the eye-diagram canvas + imaging-notes empty state |
| `clip_05_orders_labs_review_only.mp4` | 10–15 s | Orders & Labs | Pan over the 4 cards. Verbally call out: "review-only — no Submit / Place / Send buttons" |
| `clip_06_communications_and_documents.mp4` | 10–15 s | Communications + Documents | Click Communications, type a staff-handoff note, switch to Documents, show the local document index |
| `clip_07_billing_review_only.mp4` | 10–15 s | Billing | Pan over the disclaimer banner. Then over the 4 cards (CPT Codes / Charges / Insurance Status / Billing Review Notes). All buttons are visibly disabled |
| `clip_08_full_demo_navigation_flow.mp4` | 30–45 s | All 10 | Left-to-right hover across the 10 tabs; click into each briefly. Reads as "this is a real product, not a single screen" |

## Recording rules

- **Resolution**: 1440×900 (matches the Playwright capture).
- **Format**: `.mp4` or `.webm`.
- **No voice-over with unsafe phrasing.** Do not say "HIPAA",
  "certified", "autonomous", "automatic orders", or "billing
  automation". Use the safe phrasing from
  `docs/demo/chartnav-clinical-workflow-demo-script.md`.
- **No real patient data.** If you accidentally have real data
  loaded, run `make reset-db` and re-record.
- **Re-record, don't edit.** If a take captures forbidden
  language or wrong UI, throw it away and re-record.

## After capture

1. Drop each `.mp4` into `03_New_Demo_Clips/`.
2. Update `08_Capture_Manifest/media_manifest.md` with the
   filename + length + status.
3. Wait for visual approval before replacing the live website
   clips.
CLIPS_EOF

cat > "$REVIEW_DIR/08_Capture_Manifest/media_manifest.md" <<'MANIFEST_EOF'
# ChartNav media manifest — Phase 19B review

Every media file in this review folder, indexed for
walkthrough. Update the **Approved?** column as you review.

## Screenshots

| File | Folder | Type | Source route | Tab | Status | Approved? | Notes |
|---|---|---|---|---|---|---|---|
| `01_overview_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Overview | New | No | Sticky patient header + demographic strip + 3-col card grid |
| `02_clinical_ophthalmology_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Clinical / Ophthalmology | New | No | Collapsible groups + search |
| `03_documentation_emr_ehr_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Documentation / EMR/EHR | New | No | NoteWorkspace mounted |
| `04_imaging_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Imaging | New | No | OD/OS retinal diagram |
| `05_orders_labs_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Orders & Labs | New | No | Review-only |
| `06_calendar_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Calendar | New | No | Read-only schedule context |
| `07_communications_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Communications | New | No | Internal notes only |
| `08_documents_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Documents | New | No | Local file index |
| `09_chat_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Chat | New | No | Demo-local thread |
| `10_billing_review_tab.png` | `01_New_Screenshots/` | screenshot | `/?demo=1` | Billing | New | No | Disclaimer + 4 review cards |

## Website images (after curation)

| File | Folder | Type | Source screenshot | Status | Approved? | Notes |
|---|---|---|---|---|---|---|
| `website_hero_overview.png` | `02_New_Website_Images/` | website image | `01_overview_tab.png` | Pending | No | Hero |
| `website_clinical_tab.png` | `02_New_Website_Images/` | website image | `02_clinical_ophthalmology_tab.png` | Pending | No |  |
| `website_documentation_workflow.png` | `02_New_Website_Images/` | website image | `03_documentation_emr_ehr_tab.png` | Pending | No |  |
| `website_imaging_tab.png` | `02_New_Website_Images/` | website image | `04_imaging_tab.png` | Pending | No |  |
| `website_orders_labs_review.png` | `02_New_Website_Images/` | website image | `05_orders_labs_tab.png` | Pending | No |  |

## Demo clips (after capture)

| File | Folder | Type | Length | Tab(s) | Status | Approved? | Notes |
|---|---|---|---|---|---|---|---|
| `clip_01_overview_tab_reveal.mp4` | `03_New_Demo_Clips/` | clip | 10–15 s | Overview | Pending | No |  |
| `clip_02_clinical_ophthalmology_navigation.mp4` | `03_New_Demo_Clips/` | clip | 15–20 s | Clinical | Pending | No |  |
| `clip_03_documentation_workflow.mp4` | `03_New_Demo_Clips/` | clip | 20–30 s | Documentation | Pending | No |  |
| `clip_04_imaging_workspace.mp4` | `03_New_Demo_Clips/` | clip | 15–20 s | Imaging | Pending | No |  |
| `clip_05_orders_labs_review_only.mp4` | `03_New_Demo_Clips/` | clip | 10–15 s | Orders & Labs | Pending | No |  |
| `clip_06_communications_and_documents.mp4` | `03_New_Demo_Clips/` | clip | 10–15 s | Communications + Documents | Pending | No |  |
| `clip_07_billing_review_only.mp4` | `03_New_Demo_Clips/` | clip | 10–15 s | Billing | Pending | No |  |
| `clip_08_full_demo_navigation_flow.mp4` | `03_New_Demo_Clips/` | clip | 30–45 s | All 10 | Pending | No |  |

## Pre-Phase-19B archive

The folders under `05_Archive_Pre_Phase19B/` are read-only
copies of the operator's original Desktop folders. Do **not**
re-use them for the website, decks, or final delivery —
they predate the Phase 19B UI.
MANIFEST_EOF

echo "   ok — README, REVIEW_ORDER, CLIP_CAPTURE_INSTRUCTIONS, manifest written"

# ---------------------------------------------------------------
# 4. Optional Playwright capture.
#
# Phase 19C correction: we drive capture via the existing
# `npx playwright test` harness instead of a standalone Node
# script. The harness's `webServer:` already boots a clean
# isolated stack on ports 8001 / 5174 against an ephemeral
# SQLite seed — same setup CI uses every day, so it sidesteps
# corrupted-node_modules / mcp-module load failures.
#
# This means the operator does NOT need `make dev` running.
# Playwright will spin its own stack up and tear it down.
# ---------------------------------------------------------------

echo
echo "4. Screenshot capture (Playwright test runner)"

if ! command -v node >/dev/null 2>&1; then
  echo "   skip — node not on PATH; install Node 18+ to enable capture"
  echo "   You can still review the templates + archive copies."
  exit 0
fi

if [ ! -d "$REPO_ROOT/apps/web/node_modules/@playwright/test" ]; then
  echo "   skip — apps/web/node_modules is missing or incomplete."
  echo "   Run this first to populate it:"
  echo "     ( cd $REPO_ROOT/apps/web && npm install )"
  echo "     ( cd $REPO_ROOT/apps/web && npx playwright install chromium )"
  echo "   Then re-run this script."
  exit 0
fi

# Sanity: the spec we delegate to.
SPEC="apps/web/tests/media-review/capture-phase19b.spec.ts"
if [ ! -f "$REPO_ROOT/$SPEC" ]; then
  echo "   skip — capture spec missing at $SPEC"
  echo "   Make sure your branch is up to date: git pull"
  exit 0
fi

# Run from the apps/web workspace so playwright.config.ts is
# picked up. CAPTURE_OUT_DIR is honored by the spec.
(
  cd "$REPO_ROOT/apps/web"
  CAPTURE_OUT_DIR="$REVIEW_DIR/01_New_Screenshots" \
    npx playwright test \
      --project=chromium \
      --reporter=list \
      tests/media-review/capture-phase19b.spec.ts
) || {
  echo
  echo "   Capture failed. Common fixes:"
  echo "     1. ( cd $REPO_ROOT/apps/web && npx playwright install chromium )"
  echo "     2. The spec drives a self-managed stack — make sure"
  echo "        ports 8001 and 5174 are FREE before re-running."
  echo "        \`lsof -ti tcp:8001 tcp:5174 | xargs -r kill -9\`"
  echo "     3. The Python venv at apps/api/.venv must exist;"
  echo "        run \`make install\` from the repo root if missing."
  echo
  echo "   Templates + archive copies are already in place at:"
  echo "     $REVIEW_DIR"
  exit 0
}

echo
echo "Done. Review folder: $REVIEW_DIR"
echo "Start with: $REVIEW_DIR/00_START_HERE/REVIEW_ORDER.md"
