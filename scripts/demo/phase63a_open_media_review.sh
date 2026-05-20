#!/usr/bin/env bash
# scripts/demo/phase63a_open_media_review.sh
# ──────────────────────────────────────────
# Opens the screenshot folder, video folder, dry-run report, shot lists,
# evidence packet, and the running frontend (if reachable). Macos-only;
# uses `open` for files and URLs.

set -uo pipefail

REPO_ROOT="${CHARTNAV_REPO_PATH:-$HOME/Desktop/ARCG/chartnav-platform}"
SHOT_DIR="${REPO_ROOT}/artifacts/phase-62/screenshots"
VID_DIR="${REPO_ROOT}/artifacts/phase-62/video-clips"
DRY_RUN_DIR="${REPO_ROOT}/artifacts/phase-62/dry-runs/2026-05-20"
REPORT="${DRY_RUN_DIR}/report.md"
PHASE63A_REPORT="${REPO_ROOT}/docs/build/phase-63a-automated-demo-media-capture-report.md"
RELEASE_CHK="${REPO_ROOT}/docs/release/release-evidence-checklist.md"
PRODUCT_TRUTH="${REPO_ROOT}/docs/build/current-product-truth.md"
WEB_URL="${E2E_BASE_URL:-http://127.0.0.1:5173}"

open_if() {
  local p="$1"
  if [[ -e "${p}" ]]; then
    echo "[open] ${p}"
    open "${p}" 2>/dev/null || true
  else
    echo "[skip] missing: ${p}"
  fi
}

echo "=== Phase 63A — open media review ==="

open_if "${SHOT_DIR}"
open_if "${VID_DIR}"
open_if "${REPORT}"
open_if "${PHASE63A_REPORT}"
open_if "${RELEASE_CHK}"
open_if "${PRODUCT_TRUTH}"

# Frontend — only open if reachable
if curl -fs --max-time 2 "${WEB_URL}/" >/dev/null 2>&1; then
  echo "[open] ${WEB_URL}/"
  open "${WEB_URL}/" 2>/dev/null || true
else
  echo "[skip] frontend not reachable at ${WEB_URL}/"
fi

echo "Done."
