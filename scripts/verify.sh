#!/usr/bin/env bash
# Canonical local gate: boot a fresh API, run smoke, tear it down.
# Called by `make verify` after `make reset-db` and `make test`.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/apps/api"

PORT=8765
BOOT_LOG=/tmp/chartnav_verify_boot.log

# Start uvicorn fully detached: new session, stdio to file, so nothing holds
# our stdout/stderr hostage.
rm -f "$BOOT_LOG"
# Prefer the project venv when present (local dev); otherwise fall back
# to whatever `uvicorn` is on PATH (CI's system install).
if [ -x .venv/bin/uvicorn ]; then
    UVICORN=.venv/bin/uvicorn
else
    UVICORN="$(command -v uvicorn)"
fi
"$UVICORN" app.main:app --port "$PORT" --log-level warning \
    >"$BOOT_LOG" 2>&1 </dev/null &
BOOT_PID=$!
# shellcheck disable=SC2064
trap "kill -9 $BOOT_PID 2>/dev/null || true" EXIT

# Wait up to ~10s for /health.
for _ in $(seq 1 20); do
    if curl -sfo /dev/null "http://127.0.0.1:$PORT/health"; then
        break
    fi
    sleep 0.5
done

bash scripts/smoke.sh "http://127.0.0.1:$PORT"

echo "==> verify complete"
