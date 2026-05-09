#!/usr/bin/env bash
#
# Phase 19G — media-review folder + screenshot capture runner.
#
# WHAT THIS DOES (operator's Mac):
#   1. Recreates the review folder at the supplied path (default
#      ~/Desktop/Chartnav/ChartNav_Media_Review_Final_UI). ONLY
#      this one folder is touched — the legacy Desktop folders
#      (chartnav imags / ChartNav_Media_Central / clips_final /
#      clips_generated / raw_clips / Screenshots / Video_Clips)
#      are NOT modified.
#   2. Copies the Phase 19G markdown deliverables (README,
#      manifest, demo + website clip instructions, chartnavmd
#      replacement plan) from this repo's
#      tools/media-review/templates/ into the right subfolders.
#   3. Boots the local app (api + frontend, via the existing
#      Playwright webServer config) and captures the 12 Phase
#      19F review screenshots into 01_Screenshots/. The capture
#      spec is gated on CAPTURE_OUT_DIR so a normal CI run never
#      triggers it.
#
# WHAT THIS DOES NOT DO:
#   - It does NOT capture the 6 website video clips. Video clip
#     capture needs a screen recorder + a real visible cursor —
#     that's the operator's job, with the manual instructions
#     written into 03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS.
#   - It does NOT push to chartnavmd.com.
#   - It does NOT modify any final-delivery folder.
#   - It does NOT commit screenshots/videos to the repo.
#
# Usage:
#   bash tools/media-review/capture_phase19g_media.sh
#   bash tools/media-review/capture_phase19g_media.sh /path/to/folder
#
# Env knobs:
#   PLAYWRIGHT_PORT  override the frontend port the spec hits
#                    (default 5174, matches playwright.config.ts).

set -euo pipefail

# ----- arg + path resolution ------------------------------------------------

DEFAULT_OUT="$HOME/Desktop/Chartnav/ChartNav_Media_Review_Final_UI"
OUT_DIR="${1:-$DEFAULT_OUT}"

# Resolve the repo root from this script's location so the
# operator can call it from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATES_DIR="$REPO_ROOT/tools/media-review/templates"

echo "Phase 19G capture"
echo "================="
echo "  repo root : $REPO_ROOT"
echo "  out dir   : $OUT_DIR"
echo "  templates : $TEMPLATES_DIR"
echo

# ----- safety: refuse to wipe paths that aren't ours ------------------------

case "$OUT_DIR" in
  *ChartNav_Media_Review_Final_UI*) ;;
  *)
    echo "ABORT: refusing to wipe '$OUT_DIR' — not a Phase 19G review folder"
    echo "       (expected '...ChartNav_Media_Review_Final_UI' in the path)"
    exit 2
    ;;
esac

# Sister legacy folders the brief says NOT to touch. We don't
# wipe them; we just check they aren't accidentally inside the
# review folder we're about to recreate.
LEGACY=(
  "chartnav imags"
  "ChartNav_Media_Central"
  "clips_final"
  "clips_generated"
  "raw_clips"
  "Screenshots"
  "Video_Clips"
)
for L in "${LEGACY[@]}"; do
  case "$OUT_DIR" in
    *"$L"*)
      echo "ABORT: $OUT_DIR overlaps a legacy folder ($L) — refusing to recreate"
      exit 2
      ;;
  esac
done

# ----- (re)create folder tree ----------------------------------------------

if [ -e "$OUT_DIR" ]; then
  echo "Removing existing review folder: $OUT_DIR"
  rm -rf "$OUT_DIR"
fi

echo "Creating folder tree…"
mkdir -p "$OUT_DIR/00_START_HERE"
mkdir -p "$OUT_DIR/01_Screenshots"
mkdir -p "$OUT_DIR/02_Website_Selected"
mkdir -p "$OUT_DIR/03_Website_Video_Clips/MP4"
mkdir -p "$OUT_DIR/03_Website_Video_Clips/WEBM"
mkdir -p "$OUT_DIR/03_Website_Video_Clips/GIF_or_Preview_Frames"
mkdir -p "$OUT_DIR/03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS"
mkdir -p "$OUT_DIR/04_Demo_Clip_Instructions"
mkdir -p "$OUT_DIR/05_Archive_Reference"
mkdir -p "$OUT_DIR/06_Manifest"
mkdir -p "$OUT_DIR/07_Ready_For_ChartNavMD_After_Approval/images"
mkdir -p "$OUT_DIR/07_Ready_For_ChartNavMD_After_Approval/videos"
mkdir -p "$OUT_DIR/07_Ready_For_ChartNavMD_After_Approval/instructions"

# ----- copy markdown deliverables in --------------------------------------

echo "Copying markdown templates…"
cp "$TEMPLATES_DIR/README_REVIEW_FIRST.md" \
   "$OUT_DIR/00_START_HERE/README_REVIEW_FIRST.md"
cp "$TEMPLATES_DIR/media_manifest.md" \
   "$OUT_DIR/06_Manifest/media_manifest.md"
cp "$TEMPLATES_DIR/CLIP_CAPTURE_INSTRUCTIONS.md" \
   "$OUT_DIR/04_Demo_Clip_Instructions/CLIP_CAPTURE_INSTRUCTIONS.md"
cp "$TEMPLATES_DIR/WEBSITE_CLIP_CAPTURE_INSTRUCTIONS.md" \
   "$OUT_DIR/03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS/WEBSITE_CLIP_CAPTURE_INSTRUCTIONS.md"
cp "$TEMPLATES_DIR/CHARTNAVMD_WEBSITE_MEDIA_REPLACEMENT_PLAN.md" \
   "$OUT_DIR/07_Ready_For_ChartNavMD_After_Approval/instructions/CHARTNAVMD_WEBSITE_MEDIA_REPLACEMENT_PLAN.md"

# ----- run Playwright capture spec -----------------------------------------

echo
echo "Booting api + frontend + capturing screenshots…"
echo "(Playwright will reuse already-running servers if you have"
echo " them up; otherwise it boots its own ephemeral stack.)"
echo

cd "$REPO_ROOT/apps/web"
CAPTURE_OUT_DIR="$OUT_DIR" \
  npx playwright test tests/e2e/phase19g-capture.spec.ts \
    --reporter=list

# ----- final summary --------------------------------------------------------

echo
echo "Done."
echo
echo "Open this first:"
echo "  $OUT_DIR/00_START_HERE/README_REVIEW_FIRST.md"
echo
echo "Then check:"
echo "  $OUT_DIR/01_Screenshots/      (12 PNGs — Phase 19F UI)"
echo "  $OUT_DIR/06_Manifest/media_manifest.md"
echo "  $OUT_DIR/04_Demo_Clip_Instructions/CLIP_CAPTURE_INSTRUCTIONS.md"
echo "  $OUT_DIR/03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS/WEBSITE_CLIP_CAPTURE_INSTRUCTIONS.md"
echo "  $OUT_DIR/07_Ready_For_ChartNavMD_After_Approval/instructions/CHARTNAVMD_WEBSITE_MEDIA_REPLACEMENT_PLAN.md"
echo
