#!/usr/bin/env bash
# ChartNav — post-deploy enterprise validation.
#
# Runs AFTER `docker compose up -d` to confirm the live stack is
# healthy. Exits 0 on full green; non-zero on any failure with a
# readable summary. Does NOT mutate state.
#
# Usage:
#   scripts/enterprise_validate.sh https://chart.example.com
#   scripts/enterprise_validate.sh                         # defaults to http://localhost:8000
#
# Checks performed, in order:
#   1. /health returns 200.
#   2. /capability/manifest returns 200 and has schema_version.
#   3. /deployment/manifest returns 200 and has alembic_head.
#   4. Alembic head in response matches the repo's newest revision.
#   5. /admin/operations/evidence-chain-verify returns 200 with
#      `ok: true` when called with a seeded admin identity (only
#      when CHARTNAV_VALIDATE_ADMIN_EMAIL is set).

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
TIMEOUT="${CHARTNAV_VALIDATE_TIMEOUT:-5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
red() { printf '\033[0;31m%s\033[0m\n' "$*"; }

fail=0

check() {
  local label="$1"; shift
  if "$@" >/tmp/chartnav_validate.out 2>/tmp/chartnav_validate.err; then
    green "ok  $label"
  else
    red "FAIL $label"
    sed 's/^/      /' /tmp/chartnav_validate.err >&2 || true
    fail=1
  fi
}

echo "enterprise_validate: base_url=$BASE_URL"

# 1. /health
check "/health returns 200" bash -c "
  code=\$(curl -s -o /dev/null -w '%{http_code}' --max-time $TIMEOUT '$BASE_URL/health')
  test \"\$code\" = '200'
"

# 2. /capability/manifest
check "/capability/manifest returns 200" bash -c "
  body=\$(curl -s --max-time $TIMEOUT '$BASE_URL/capability/manifest')
  echo \"\$body\" | grep -q schema_version
"

# 3. /deployment/manifest
check "/deployment/manifest returns 200" bash -c "
  body=\$(curl -s --max-time $TIMEOUT '$BASE_URL/deployment/manifest')
  echo \"\$body\" | grep -q alembic_head
"

# 4. Alembic head on live service matches repo.
REPO_HEAD=$(ls "$REPO_ROOT/apps/api/alembic/versions/"*.py \
  | xargs -n1 basename \
  | sed 's/_.*//' \
  | sort -r \
  | head -1)
check "alembic head matches repo (${REPO_HEAD})" bash -c "
  live=\$(curl -s --max-time $TIMEOUT '$BASE_URL/deployment/manifest' \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get(\"alembic_head\", \"\"))')
  test \"\$live\" = '$REPO_HEAD'
"

# 5. Evidence chain verify (optional — only when admin identity given)
if [[ -n "${CHARTNAV_VALIDATE_ADMIN_EMAIL:-}" ]]; then
  check "evidence chain verify returns ok=true" bash -c "
    code=\$(curl -s -o /tmp/chartnav_validate.body -w '%{http_code}' \
      --max-time $TIMEOUT \
      -H 'X-User-Email: $CHARTNAV_VALIDATE_ADMIN_EMAIL' \
      '$BASE_URL/admin/operations/evidence-chain-verify')
    test \"\$code\" = '200' && python3 -c 'import json; assert json.load(open(\"/tmp/chartnav_validate.body\"))[\"ok\"] is True'
  "
else
  yellow "skip evidence chain verify (set CHARTNAV_VALIDATE_ADMIN_EMAIL to enable)"
fi

echo
if [[ $fail -eq 0 ]]; then
  green "enterprise_validate: OK"
else
  red "enterprise_validate: FAIL"
fi
exit $fail
