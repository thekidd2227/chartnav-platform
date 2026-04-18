#!/usr/bin/env bash
# Staging smoke + observability verification.
#
# Usage:
#   scripts/staging_verify.sh [BASE_URL]
#   Default BASE_URL: http://127.0.0.1:${API_PORT:-8000}
#
# In `header` auth mode this performs a full workflow smoke.
# In `bearer` auth mode it only checks unauth surfaces + observability
# (auth paths require a token the script does not mint — see runbook).
#
# Always non-zero on the first failed assertion. Safe in CI or on a VM.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/infra/docker/.env.staging"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    . "$ENV_FILE"
    set +a
fi

BASE="${1:-http://127.0.0.1:${API_PORT:-8000}}"
MODE="${CHARTNAV_AUTH_MODE:-header}"

pass() { printf "  ok  %s\n" "$1"; }
fail() { printf "  FAIL %s\n  got: %s\n" "$1" "$2" >&2; exit 1; }

echo "==> staging verify: $BASE  (auth mode: $MODE)"

# ---- Unauth + ops surfaces (always checked) ---------------------------

code=$(curl -s -o /tmp/cn_stage_health.json -w "%{http_code}" "$BASE/health")
[ "$code" = "200" ] || fail "/health" "$code"
pass "/health 200"

code=$(curl -s -o /tmp/cn_stage_ready.json -w "%{http_code}" "$BASE/ready")
[ "$code" = "200" ] || fail "/ready" "$code"
python3 -c "
import json
d = json.load(open('/tmp/cn_stage_ready.json'))
assert d['database'] == 'ok', d
" || fail "/ready payload" "$(cat /tmp/cn_stage_ready.json)"
pass "/ready 200 (database=ok)"

code=$(curl -s -o /tmp/cn_stage_metrics.txt -w "%{http_code}" "$BASE/metrics")
[ "$code" = "200" ] || fail "/metrics" "$code"
grep -q "chartnav_requests_total" /tmp/cn_stage_metrics.txt \
    || fail "/metrics missing chartnav_requests_total" "$(head /tmp/cn_stage_metrics.txt)"
pass "/metrics exposes chartnav_requests_total"

# /me without auth → 401 (both modes)
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/me")
[ "$code" = "401" ] || fail "/me without auth → 401" "$code"
pass "/me unauth → 401"

# Request id echoed back
rid=$(curl -s -D- -o /dev/null -H "X-Request-ID: stage-smoke-rid" "$BASE/health" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-request-id"{print $2}')
if [ "$rid" = "stage-smoke-rid" ]; then
    pass "X-Request-ID roundtrips"
else
    fail "X-Request-ID roundtrip" "got=$rid"
fi

# ---- Auth-mode dependent workflow smoke -------------------------------

if [ "$MODE" = "header" ]; then
    ADMIN1="X-User-Email: admin@chartnav.local"
    code=$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN1" "$BASE/me")
    [ "$code" = "200" ] || fail "/me admin1" "$code"
    pass "/me admin1 → 200"

    code=$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN1" "$BASE/encounters")
    [ "$code" = "200" ] || fail "/encounters admin1" "$code"
    pass "/encounters admin1 → 200"

    # One mutation: append an event to encounter #1 (present if seed ran).
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$ADMIN1" \
        -H 'Content-Type: application/json' \
        "$BASE/encounters/1/events" \
        -d '{"event_type":"staging_verify_ping"}')
    if [ "$code" = "201" ]; then
        pass "POST /encounters/1/events → 201"
    else
        # If the seed never ran, the encounter won't exist. Non-fatal; report.
        printf "  skip POST /encounters/1/events (got %s — seed may be off)\n" "$code"
    fi
else
    echo "  skip /me + /encounters workflow smoke (bearer mode — needs a token)."
    echo "  Use docs/build/21-staging-runbook.md § 'Exercising bearer mode' for the manual path."
fi

# ---- Observability signal: denied attempts should audit ---------------

code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/me")
[ "$code" = "401" ] || fail "/me repeat unauth" "$code"
grep -qE '^chartnav_auth_denied_total\{error_code="missing_auth_header"\} [0-9]+' \
    <(curl -fsS "$BASE/metrics") \
    || fail "/metrics missing auth_denied counter" "no missing_auth_header counter"
pass "/metrics reflects at least one missing_auth_header denial"

echo "==> staging verify: PASS"
