#!/usr/bin/env bash
# ChartNav API smoke check.
#
# Usage:   scripts/smoke.sh [BASE_URL]
# Default: BASE_URL=http://127.0.0.1:8000
#
# Assumes the DB behind BASE_URL was migrated + seeded via scripts_seed.py
# so that `admin@chartnav.local` exists in org 1.
#
# Exits non-zero on any failure. Safe to use in CI and by operators.

set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
ADMIN1_HDR="X-User-Email: admin@chartnav.local"

pass() { printf "  ok  %s\n" "$1"; }
fail() { printf "  FAIL %s\n  got: %s\n" "$1" "$2" >&2; exit 1; }

echo "==> smoke: $BASE"

# 1. /health 200 + ok
code=$(curl -s -o /tmp/chartnav_smoke_health.json -w "%{http_code}" "$BASE/health")
[ "$code" = "200" ] || fail "/health 200" "HTTP $code"
pass "/health 200"
status=$(python3 -c "import sys,json; print(json.load(open('/tmp/chartnav_smoke_health.json')).get('status'))")
[ "$status" = "ok" ] || fail "/health body.status" "$status"
pass "/health body.status=ok"

# 2. /me without auth -> 401
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/me")
[ "$code" = "401" ] || fail "/me 401 without auth" "HTTP $code"
pass "/me 401 without auth"

# 3. /me with admin1 -> 200 + role=admin
body=$(curl -s -H "$ADMIN1_HDR" "$BASE/me")
echo "$body" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
assert d.get('role') == 'admin', d
assert d.get('organization_id') == 1, d
" || fail "/me 200 admin1" "$body"
pass "/me 200 role=admin org=1"

# 4. /encounters 401 without auth
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/encounters")
[ "$code" = "401" ] || fail "/encounters 401 without auth" "HTTP $code"
pass "/encounters 401 without auth"

# 5. /encounters 200 with admin1
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN1_HDR" "$BASE/encounters")
[ "$code" = "200" ] || fail "/encounters 200 admin1" "HTTP $code"
pass "/encounters 200 admin1"

# 6. cross-org lens -> 403
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN1_HDR" "$BASE/encounters?organization_id=2")
[ "$code" = "403" ] || fail "/encounters?organization_id=2 -> 403" "HTTP $code"
pass "/encounters?organization_id=2 (cross-org) -> 403"

# 7. own encounter
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN1_HDR" "$BASE/encounters/1")
[ "$code" = "200" ] || fail "GET /encounters/1 as admin1" "HTTP $code"
pass "GET /encounters/1 as admin1 -> 200"

# 8. cross-org encounter -> 404
code=$(curl -s -o /dev/null -w "%{http_code}" -H "$ADMIN1_HDR" "$BASE/encounters/3")
[ "$code" = "404" ] || fail "GET /encounters/3 cross-org as admin1" "HTTP $code"
pass "GET /encounters/3 cross-org -> 404"

echo "==> all smoke checks passed"
