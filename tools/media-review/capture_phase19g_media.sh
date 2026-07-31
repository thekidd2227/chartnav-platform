#!/usr/bin/env bash
#
# Phase 19G — media-review folder + screenshot capture runner.
# Phase 19J extension — optional `--with-clips` flag chains into
# the website-clip recorder after screenshots finish.
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
#   4. (Optional, with --with-clips) After screenshots finish,
#      hands off to capture_phase19i_clips.sh to record the 7
#      Phase 19I website video clips into
#      03_Website_Video_Clips/{MP4,WEBM,GIF_or_Preview_Frames}/.
#      Requires ffmpeg (brew install ffmpeg).
#
# WHAT THIS DOES NOT DO:
#   - Without --with-clips, video clips are NOT captured. Use
#     the manual instructions or pass --with-clips.
#   - It does NOT push to chartnavmd.com.
#   - It does NOT modify any final-delivery folder.
#   - It does NOT commit screenshots/videos to the repo.
#
# Usage:
#   bash tools/media-review/capture_phase19g_media.sh
#   bash tools/media-review/capture_phase19g_media.sh /path/to/folder
#   bash tools/media-review/capture_phase19g_media.sh --with-clips
#   bash tools/media-review/capture_phase19g_media.sh /path/to/folder --with-clips
#
# Env knobs:
#   PLAYWRIGHT_PORT  override the frontend port the spec hits
#                    (default 5174, matches playwright.config.ts).
#   HEADED=1         (passed through to the clip recorder when
#                    --with-clips is set) record clips with a
#                    visible browser window + cursor.

set -euo pipefail

# ----- arg parsing ----------------------------------------------------------

WITH_CLIPS=0
POSITIONAL_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --with-clips) WITH_CLIPS=1 ;;
    *)            POSITIONAL_ARGS+=("$arg") ;;
  esac
done
set -- "${POSITIONAL_ARGS[@]}"

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

# ----- optional Phase 19J chain: website clip capture ----------------------

if [ "$WITH_CLIPS" = "1" ]; then
  echo
  echo "Phase 19J chain — recording website clips…"
  echo
  bash "$SCRIPT_DIR/capture_phase19i_clips.sh" "$OUT_DIR"
fi

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
if [ "$WITH_CLIPS" = "1" ]; then
  echo "  $OUT_DIR/03_Website_Video_Clips/MP4/     (7 MP4 website clips)"
  echo "  $OUT_DIR/03_Website_Video_Clips/WEBM/    (7 VP9 WEBM mirrors)"
  echo "  $OUT_DIR/03_Website_Video_Clips/GIF_or_Preview_Frames/   (7 PNG posters)"
else
  echo
  echo "Tip: re-run with --with-clips to also capture the 7 website"
  echo "video clips automatically. Requires ffmpeg (brew install ffmpeg)."
fi
echo
