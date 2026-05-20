#!/usr/bin/env bash
# Phase 63 manual capture helper. Opens everything the operator
# needs to record the 8 safe demo clips by hand if the Playwright
# script can't drive the UI on this iMac (auth headers, vendor
# popups, etc.).
#
# This wrapper does NOT capture video itself. macOS's
# screen-record APIs require user-interactive permission, so the
# operator does the actual capture via QuickTime / Cmd-Shift-5.
# The wrapper just stages the workspace.

set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${CHARTNAV_REPO_PATH:-}" ]] && [[ -f "$BUNDLE_DIR/.chartnav-demo-env" ]]; then
  # shellcheck disable=SC1091
  source "$BUNDLE_DIR/.chartnav-demo-env"
fi
if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set." >&2
  echo "Recovery: export CHARTNAV_REPO_PATH=\"\$HOME/Desktop/ARCG/chartnav-platform\"" >&2
  exit 2
fi

VIDEO_DIR="$CHARTNAV_REPO_PATH/artifacts/phase-63/video-clips"
SHOT_DIR="$CHARTNAV_REPO_PATH/artifacts/phase-63/screenshots"
PLAN="$CHARTNAV_REPO_PATH/docs/demo/phase-63-safe-website-video-plan.md"

mkdir -p "$VIDEO_DIR" "$SHOT_DIR"

cat <<'BANNER'

============================================================
ChartNav Phase 63 — manual safe-demo capture preparation
============================================================
This wrapper opens the dev app, the safe-video plan, and the
output folders. It does NOT record. You record using QuickTime
(File → New Screen Recording → Cmd-Ctrl-N) and macOS Screenshot
(Cmd-Shift-5 → Options → Save to ...).

Stop-conditions (halt + reset if any fire):
  - real PHI on screen
  - CHARTNAV_ENV is production / staging / controlled-pilot
  - any forbidden phrase on screen or in narration
  - a vendor / network error exposes a secret in a stack trace
  - sign / finalize succeeds without the attestation checkbox

BANNER

cat <<EOF
Targets (record into $VIDEO_DIR):
  01_workspace_orientation.mov           20–25 sec
  02_vitals_capture.mov                  30–35 sec
  03_visitdraft_transcript_to_draft.mov  30–35 sec
  04_visitdraft_signal_filter.mov        25–30 sec
  05_fundus_drawing_assist.mov           25–35 sec
  06_doctor_review_signoff.mov           30–40 sec
  07_safety_posture.mov                  20–30 sec
  08_three_minute_highlight_reel.mov     ~3 min

Posters (screenshot into $SHOT_DIR):
  01_workspace_orientation.png
  02_vitals_capture.png
  03_visitdraft_transcript_to_draft.png
  04_visitdraft_signal_filter.png
  05_fundus_drawing_assist.png
  06_doctor_review_signoff.png
  07_safety_posture.png
  08_highlight_reel_thumbnail.png

If you need .webm for the website, convert with ffmpeg after capture:
  ffmpeg -i 01_workspace_orientation.mov \\
         -c:v libvpx-vp9 -b:v 0 -crf 32 -an \\
         01_workspace_orientation.webm

EOF

if command -v open >/dev/null 2>&1; then
  echo "Opening the safe-video plan and the output folders…"
  open "$PLAN" >/dev/null 2>&1 || true
  open "$VIDEO_DIR" >/dev/null 2>&1 || true
  open "$SHOT_DIR" >/dev/null 2>&1 || true
  echo "Opening the local dev app at http://localhost:5173/?encounter=1 …"
  open "http://localhost:5173/?encounter=1" >/dev/null 2>&1 || true
  echo "Launching QuickTime Player and Screenshot…"
  open -a "QuickTime Player" >/dev/null 2>&1 || true
  open -a "Screenshot" >/dev/null 2>&1 || true
else
  echo "(no 'open' command on this OS; do this manually:)"
  echo "  - read $PLAN"
  echo "  - save captures into $VIDEO_DIR and $SHOT_DIR"
  echo "  - point your browser at http://localhost:5173/?encounter=1"
fi

cat <<'NEXT'

Next:
  1. Confirm api + web are running (./start-api.sh, ./start-web.sh).
  2. Set dev identity in DevTools console (one tab per role):
       localStorage.setItem('chartnav.devIdentity', 'clin@chartnav.local')
       localStorage.setItem('chartnav.devIdentity', 'tech@chartnav.local')
     then reload.
  3. Walk each clip in the order above. Use the safe message + must-not-say
     list in the plan doc as your narration guide.
  4. After all 8 clips + 8 posters exist, update the Phase 63 manifest:
       $CHARTNAV_REPO_PATH/artifacts/phase-63/manifest.json
     setting exists: true for the files you captured.
  5. When every file exists, open a PR for the website integration
     (see Phase 63 evidence report § 7).
NEXT
