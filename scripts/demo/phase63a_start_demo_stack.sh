#!/usr/bin/env bash
# scripts/demo/phase63a_start_demo_stack.sh
# ─────────────────────────────────────────
# Boot the local demo stack for Phase 63A automated media capture.
#
# - Sources the safe-local env file
# - Refuses to run if any real-vendor *_API_KEY env var is set
# - Ensures artifact directories exist
# - Seeds the local SQLite (idempotent) via scripts/reset_demo_state.sh if present
# - Starts API on :8000 and frontend on :5173 if either is not already up
# - Waits for both health endpoints
# - Logs to artifacts/phase-62/dry-runs/2026-05-20/{api.log,web.log}
#
# Constraints honored:
#   - CHARTNAV_LLM_ENABLED stays 0 (no production LLM)
#   - No real PHI, no real vendor keys, no deploy
#   - Backend logic unchanged, frontend components unchanged

set -euo pipefail

REPO_ROOT="${CHARTNAV_REPO_PATH:-$HOME/Desktop/ARCG/chartnav-platform}"
DRY_RUN_DIR="${REPO_ROOT}/artifacts/phase-62/dry-runs/2026-05-20"
ENV_FILE="${DRY_RUN_DIR}/.chartnav-demo-env"
SCREENSHOT_DIR="${REPO_ROOT}/artifacts/phase-62/screenshots"
VIDEO_DIR="${REPO_ROOT}/artifacts/phase-62/video-clips"

API_HOST="127.0.0.1"
API_PORT="${CHARTNAV_API_PORT:-8000}"
WEB_HOST="127.0.0.1"
WEB_PORT="${CHARTNAV_WEB_PORT:-5173}"

# ── 1. Verify repo and env file ───────────────────────────────────────────
if [[ ! -d "${REPO_ROOT}" ]]; then
  echo "ERROR: repo not found at ${REPO_ROOT}" >&2
  exit 1
fi
cd "${REPO_ROOT}"

mkdir -p "${DRY_RUN_DIR}" "${SCREENSHOT_DIR}" "${VIDEO_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: env file not found at ${ENV_FILE}" >&2
  exit 1
fi

# ── 2. Refuse real vendor keys BEFORE anything starts ─────────────────────
for var in CHARTNAV_OPENAI_API_KEY CHARTNAV_ANTHROPIC_API_KEY CHARTNAV_WATSONX_API_KEY \
           OPENAI_API_KEY ANTHROPIC_API_KEY WATSONX_API_KEY; do
  if [[ -n "${!var:-}" ]]; then
    echo "ABORT: ${var} is set in this shell. Unset it before running media capture." >&2
    exit 2
  fi
done

# ── 3. Load safe-local env ────────────────────────────────────────────────
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ "${CHARTNAV_LLM_ENABLED}" != "0" ]]; then
  echo "ABORT: CHARTNAV_LLM_ENABLED must be 0; got '${CHARTNAV_LLM_ENABLED}'." >&2
  exit 3
fi

echo "[phase63a] env loaded — CHARTNAV_ENV=${CHARTNAV_ENV} LLM=${CHARTNAV_LLM_ENABLED} provider=${CHARTNAV_LLM_PROVIDER}"

# ── 4. Helper: is a port up? ──────────────────────────────────────────────
port_up() {
  local host="$1" port="$2" path="${3:-/}"
  curl -fs --max-time 2 "http://${host}:${port}${path}" >/dev/null 2>&1
}

wait_for() {
  local host="$1" port="$2" path="$3" label="$4" max="${5:-30}"
  local i=0
  until port_up "${host}" "${port}" "${path}"; do
    i=$((i+1))
    if (( i >= max )); then
      echo "ERROR: ${label} did not come up at http://${host}:${port}${path} within ${max}s" >&2
      return 1
    fi
    sleep 1
  done
  echo "[phase63a] ${label} ready at http://${host}:${port}${path}"
}

# ── 5. Seed demo state (idempotent, optional) ─────────────────────────────
if [[ -x scripts/reset_demo_state.sh ]]; then
  echo "[phase63a] running scripts/reset_demo_state.sh ..."
  bash scripts/reset_demo_state.sh > "${DRY_RUN_DIR}/seed.log" 2>&1 || {
    echo "WARN: reset_demo_state.sh exited non-zero — see ${DRY_RUN_DIR}/seed.log"
  }
fi

# ── 6. Start API if not already up ────────────────────────────────────────
if port_up "${API_HOST}" "${API_PORT}" "/health"; then
  echo "[phase63a] API already running on :${API_PORT}"
else
  if [[ ! -x apps/api/.venv/bin/uvicorn ]]; then
    echo "ERROR: apps/api/.venv/bin/uvicorn not found. Activate or build the venv first." >&2
    exit 4
  fi
  echo "[phase63a] starting API on :${API_PORT} ..."
  (
    cd apps/api
    nohup ./.venv/bin/uvicorn app.main:app \
      --host "${API_HOST}" --port "${API_PORT}" --log-level warning \
      > "${DRY_RUN_DIR}/api.log" 2>&1 &
    echo $! > "${DRY_RUN_DIR}/api.pid"
  )
  wait_for "${API_HOST}" "${API_PORT}" "/health" "API" 40
fi

# ── 7. Start frontend if not already up ───────────────────────────────────
if port_up "${WEB_HOST}" "${WEB_PORT}" "/"; then
  echo "[phase63a] frontend already running on :${WEB_PORT}"
else
  if [[ ! -d apps/web/node_modules ]]; then
    echo "ERROR: apps/web/node_modules missing. Run 'npm install' in apps/web first." >&2
    exit 5
  fi
  echo "[phase63a] starting frontend on :${WEB_PORT} ..."
  (
    cd apps/web
    VITE_API_URL="http://${API_HOST}:${API_PORT}" \
    nohup npx vite --host "${WEB_HOST}" --port "${WEB_PORT}" \
      > "${DRY_RUN_DIR}/web.log" 2>&1 &
    echo $! > "${DRY_RUN_DIR}/web.pid"
  )
  wait_for "${WEB_HOST}" "${WEB_PORT}" "/" "frontend" 40
fi

# ── 8. Final summary ──────────────────────────────────────────────────────
echo ""
echo "[phase63a] stack ready"
echo "  API:      http://${API_HOST}:${API_PORT}/health"
echo "  Frontend: http://${WEB_HOST}:${WEB_PORT}/"
echo "  Logs:     ${DRY_RUN_DIR}/api.log  ${DRY_RUN_DIR}/web.log"
echo ""
echo "Next:"
echo "  node ${REPO_ROOT}/scripts/demo/phase63a_capture_demo_media.mjs"
