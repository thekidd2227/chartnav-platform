#!/usr/bin/env bash
# Postgres parity proof: start a throwaway Postgres, run migrations +
# seed against it, boot the API, hit the live smoke subset. Tear down
# on exit (including failure).
#
# Reproducible locally AND in CI (see .github/workflows/ci.yml job
# `postgres-parity`).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"
PG_CONTAINER=chartnav-pg-verify
PG_PORT="${PG_PORT:-55432}"
PG_DB=chartnav
PG_USER=chartnav
PG_PASSWORD=chartnav
API_PORT="${API_PORT:-8766}"

DATABASE_URL="postgresql+psycopg://${PG_USER}:${PG_PASSWORD}@127.0.0.1:${PG_PORT}/${PG_DB}"
export DATABASE_URL
export CHARTNAV_AUTH_MODE=header

BOOT_LOG=/tmp/chartnav_pg_verify_api.log

cleanup() {
    echo "==> cleanup"
    if [ -f /tmp/chartnav_pg_verify_api.pid ]; then
        kill -9 "$(cat /tmp/chartnav_pg_verify_api.pid)" 2>/dev/null || true
        rm -f /tmp/chartnav_pg_verify_api.pid
    fi
    docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> start Postgres (container=$PG_CONTAINER port=$PG_PORT)"
docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
docker run -d --rm \
    --name "$PG_CONTAINER" \
    -e POSTGRES_DB="$PG_DB" \
    -e POSTGRES_USER="$PG_USER" \
    -e POSTGRES_PASSWORD="$PG_PASSWORD" \
    -p "${PG_PORT}:5432" \
    postgres:16-alpine >/dev/null

echo "==> wait for Postgres to accept connections"
for _ in $(seq 1 60); do
    if docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB"

cd "$API_DIR"

# Prefer local venv python if present, else system.
if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
    UVICORN=.venv/bin/uvicorn
    ALEMBIC=.venv/bin/alembic
else
    PY=python
    UVICORN=uvicorn
    ALEMBIC=alembic
fi

echo "==> alembic upgrade head on Postgres"
"$ALEMBIC" upgrade head

echo "==> seed (idempotent, run twice)"
"$PY" scripts_seed.py
"$PY" scripts_seed.py

echo "==> boot uvicorn against Postgres"
rm -f "$BOOT_LOG"
"$UVICORN" app.main:app --host 127.0.0.1 --port "$API_PORT" --log-level warning \
    >"$BOOT_LOG" 2>&1 </dev/null &
echo $! > /tmp/chartnav_pg_verify_api.pid

for _ in $(seq 1 40); do
    if curl -sfo /dev/null "http://127.0.0.1:${API_PORT}/health"; then
        break
    fi
    sleep 0.5
done

# Reuse the canonical smoke script.
bash scripts/smoke.sh "http://127.0.0.1:${API_PORT}"

# Additional Postgres-specific check: exercise a real write that needs
# RETURNING id — a status transition on PT-1001 (in_progress → draft_ready).
echo "==> extra: status transition on Postgres"
code=$(curl -s -o /tmp/chartnav_pg_verify_status.json -w "%{http_code}" \
    -X POST "http://127.0.0.1:${API_PORT}/encounters/1/status" \
    -H "Content-Type: application/json" \
    -H "X-User-Email: clin@chartnav.local" \
    -d '{"status":"draft_ready"}')
if [ "$code" != "200" ]; then
    echo "FAIL: status transition returned $code"
    cat /tmp/chartnav_pg_verify_status.json
    exit 1
fi
python3 -c "
import json
d = json.load(open('/tmp/chartnav_pg_verify_status.json'))
assert d['status'] == 'draft_ready', d
print('  ok  PT-1001 in_progress -> draft_ready (clinician)')
"

# And verify the status_changed workflow_event was written with changed_by
ev_code=$(curl -s -o /tmp/chartnav_pg_verify_events.json -w "%{http_code}" \
    -H "X-User-Email: clin@chartnav.local" \
    "http://127.0.0.1:${API_PORT}/encounters/1/events")
[ "$ev_code" = "200" ] || { echo "FAIL events GET $ev_code"; exit 1; }
python3 -c "
import json
events = json.load(open('/tmp/chartnav_pg_verify_events.json'))
last = events[-1]
assert last['event_type'] == 'status_changed', last
assert last['event_data']['new_status'] == 'draft_ready', last
assert last['event_data']['changed_by'] == 'clin@chartnav.local', last
print('  ok  workflow_events row recorded on Postgres')
"

echo "==> Postgres parity: PASS"
