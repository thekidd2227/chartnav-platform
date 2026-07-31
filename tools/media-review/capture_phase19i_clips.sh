#!/usr/bin/env bash
#
# Phase 19J — automated website video clip runner (Mac-side).
#
# Pipeline:
#   1. Verify ffmpeg is installed (clips need WebM -> MP4
#      conversion + thumbnail extraction).
#   2. Boot the api + frontend stack (or reuse if the operator
#      already has it up — Playwright config handles both).
#   3. Run apps/web/record_phase19i_website_clips.mjs which
#      drives Playwright through 7 scripted scenarios and
#      records each as a WebM via Playwright's built-in
#      recordVideo API.
#   4. ffmpeg-convert each WebM to MP4 (H.264 / yuv420p /
#      faststart for browser playback) and to a re-encoded
#      WEBM (VP9) plus a poster PNG at t=1s.
#   5. Drop the MP4 / WEBM / PNG outputs into the Phase 19G
#      review folder structure under
#      03_Website_Video_Clips/{MP4,WEBM,GIF_or_Preview_Frames}/.
#
# Default output folder:
#   ~/Desktop/Chartnav/ChartNav_Media_Review_Final_UI
#
# Usage:
#   bash tools/media-review/capture_phase19i_clips.sh
#   bash tools/media-review/capture_phase19i_clips.sh /path/to/folder
#
# Env knobs:
#   HEADED=1   record with a visible browser window + cursor
#              (recommended for the final ship clips on a Mac;
#              defaults to headless for unattended runs)
#   ONLY=01,06 record only these clip ids (comma-separated)

set -euo pipefail

# ----- arg + path resolution ------------------------------------------------

DEFAULT_OUT="$HOME/Desktop/Chartnav/ChartNav_Media_Review_Final_UI"
OUT_DIR="${1:-$DEFAULT_OUT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CLIP_DIR="$OUT_DIR/03_Website_Video_Clips"
MP4_DIR="$CLIP_DIR/MP4"
WEBM_DIR="$CLIP_DIR/WEBM"
THUMB_DIR="$CLIP_DIR/GIF_or_Preview_Frames"
TMP_WEBM_DIR="$(mktemp -d -t phase19j-clips-XXXXXX)"

echo "Phase 19J clip capture"
echo "======================"
echo "  repo root : $REPO_ROOT"
echo "  out dir   : $OUT_DIR"
echo "  tmp WebMs : $TMP_WEBM_DIR"
echo

# ----- safety: only operate inside a Phase 19G review folder ---------------

case "$OUT_DIR" in
  *ChartNav_Media_Review_Final_UI*) ;;
  *)
    echo "ABORT: '$OUT_DIR' isn't a Phase 19G review folder"
    echo "       (expected '...ChartNav_Media_Review_Final_UI' in the path)"
    exit 2
    ;;
esac

if [ ! -d "$OUT_DIR" ]; then
  echo "ABORT: $OUT_DIR doesn't exist."
  echo "       Run the screenshot capture first:"
  echo "         bash tools/media-review/capture_phase19g_media.sh"
  exit 2
fi

# ----- verify ffmpeg is installed ------------------------------------------

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ABORT: ffmpeg not found on PATH."
  echo "       The clip pipeline needs ffmpeg to convert"
  echo "       Playwright's WebM output to MP4 (and WEBM/poster)."
  echo
  echo "       Install on macOS:"
  echo "         brew install ffmpeg"
  echo
  exit 2
fi
echo "  ffmpeg    : $(command -v ffmpeg) ($(ffmpeg -version 2>&1 | head -1))"
echo

# ----- ensure target subfolders exist --------------------------------------

mkdir -p "$MP4_DIR" "$WEBM_DIR" "$THUMB_DIR"

# ----- record raw WebMs via Playwright -------------------------------------

echo "Recording raw WebM clips…"
echo "(Boots the api + frontend stack, or reuses an already-running"
echo " stack; same webServer config as the Phase 19G screenshots.)"
echo

cd "$REPO_ROOT/apps/web"

# We piggy-back on the existing playwright.config.ts webServer so
# the Node recorder can hit a running stack on :5174. We invoke
# Playwright once with a no-op spec just to bring the servers up,
# then run the recorder against the live stack.
#
# Simpler approach: use `npx playwright test` with a tiny inline
# spec that spawns the servers, then call the recorder script
# inside that test. But that interleaves recording with test
# reporting and makes the artifacts harder to find.
#
# Cleaner approach: rely on the operator already running the dev
# stack (`npm run dev` + uvicorn) on the standard ports, OR boot
# our own stack here. We do the latter:

# Boot api + frontend in the background using the same
# commands the playwright config uses. Tear them down on exit.
#
# NOTE: this script intentionally targets port 5174 (Playwright
# webServer port), NOT the operator's default 5173 dev port. If
# you have `npm run dev` running on 5173, that's left alone.

API_PORT=8001
WEB_PORT=5174
E2E_DB="$REPO_ROOT/apps/api/.phase19j.chartnav.db"

cleanup() {
  if [ -n "${API_PID:-}" ] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
  if [ -n "${WEB_PID:-}" ] && kill -0 "$WEB_PID" 2>/dev/null; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
  if [ -f "$E2E_DB" ]; then
    rm -f "$E2E_DB"
  fi
}
trap cleanup EXIT

# Boot api.
(
  cd "$REPO_ROOT/apps/api"
  rm -f "$E2E_DB"
  DATABASE_URL="sqlite:///$E2E_DB" \
    PATH="$PWD/.venv/bin:$PATH" \
    alembic upgrade head >/dev/null 2>&1
  DATABASE_URL="sqlite:///$E2E_DB" \
    PATH="$PWD/.venv/bin:$PATH" \
    python scripts_seed.py >/dev/null 2>&1
  DATABASE_URL="sqlite:///$E2E_DB" \
    CHARTNAV_RATE_LIMIT_PER_MINUTE=0 \
    PATH="$PWD/.venv/bin:$PATH" \
    uvicorn app.main:app \
      --host 127.0.0.1 \
      --port "$API_PORT" \
      --log-level warning \
    >/tmp/phase19j-api.log 2>&1 &
  echo $! >/tmp/phase19j-api.pid
)
API_PID=$(cat /tmp/phase19j-api.pid)

# Wait for api health.
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
  echo "ABORT: api on :$API_PORT didn't come up in 60s. See /tmp/phase19j-api.log"
  exit 3
fi
echo "  api       : ready on :$API_PORT"

# Boot frontend.
VITE_API_URL="http://127.0.0.1:$API_PORT" \
  npm run dev -- --host 127.0.0.1 --port "$WEB_PORT" \
  >/tmp/phase19j-web.log 2>&1 &
WEB_PID=$!

# Wait for frontend.
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$WEB_PORT/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS "http://127.0.0.1:$WEB_PORT/" >/dev/null 2>&1; then
  echo "ABORT: frontend on :$WEB_PORT didn't come up in 60s. See /tmp/phase19j-web.log"
  exit 3
fi
echo "  frontend  : ready on :$WEB_PORT"
echo

# Run the recorder.
APP_URL="http://127.0.0.1:$WEB_PORT" \
  OUT_DIR="$TMP_WEBM_DIR" \
  HEADED="${HEADED:-}" \
  ONLY="${ONLY:-}" \
  node record_phase19i_website_clips.mjs

# ----- ffmpeg conversions --------------------------------------------------

echo
echo "Converting WebMs -> MP4 / WEBM (re-encoded) / poster PNG…"
echo

shopt -s nullglob
for raw in "$TMP_WEBM_DIR"/*.webm; do
  name="$(basename "$raw" .webm)"
  mp4="$MP4_DIR/${name}.mp4"
  webm="$WEBM_DIR/${name}.webm"
  thumb="$THUMB_DIR/${name}.png"

  echo "  $name"

  # MP4: H.264 in yuv420p w/ faststart for streamable browser play.
  ffmpeg -y -loglevel error \
    -i "$raw" \
    -c:v libx264 -pix_fmt yuv420p -preset medium -crf 22 \
    -movflags +faststart \
    "$mp4"

  # WEBM passthrough: re-encode to VP9 (Playwright's raw WebM is
  # VP8 in a Matroska-ish container — a cleaner VP9 export plays
  # nicely on every modern browser).
  ffmpeg -y -loglevel error \
    -i "$raw" \
    -c:v libvpx-vp9 -b:v 1500k \
    "$webm"

  # Poster PNG at t=5s — Phase 19J target clips all run >= 10s,
  # and the first 1–3 s is page-load time (blank background +
  # encounter list mount). t=5s reliably lands on a fully-
  # rendered workspace frame.
  ffmpeg -y -loglevel error \
    -ss 5 -i "$mp4" -frames:v 1 \
    "$thumb"
done

# ----- cleanup tmp ----------------------------------------------------------

rm -rf "$TMP_WEBM_DIR"

echo
echo "Done."
echo
echo "Outputs:"
echo "  $MP4_DIR"
ls -la "$MP4_DIR" | tail -n +2 | sed 's/^/    /'
echo
echo "  $WEBM_DIR"
ls -la "$WEBM_DIR" | tail -n +2 | sed 's/^/    /'
echo
echo "  $THUMB_DIR"
ls -la "$THUMB_DIR" | tail -n +2 | sed 's/^/    /'
echo
echo "Next: walk $OUT_DIR/06_Manifest/media_manifest.md and mark"
echo "the website-clip rows Approved? = Yes/No/Reshoot."
