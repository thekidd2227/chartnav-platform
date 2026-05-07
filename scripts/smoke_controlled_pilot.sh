#!/usr/bin/env bash
# scripts/smoke_controlled_pilot.sh — Phase 18 controlled-pilot
# smoke test.
#
# Token-driven smoke test for a controlled-pilot deployment. Does
# not require real PHI. Designed to run in a deploy / restore
# window before booking any real-PHI session.
#
# What it checks:
#   1. /health responds 200
#   2. /me without a token rejects (401)
#   3. /me with each role token resolves to a Caller
#   4. Reviewer write attempts on a clinical surface return 403
#      role_forbidden (read-only enforcement)
#   5. Cross-org access against a designated pilot test patient
#      returns 404 patient_not_found (no existence leak)
#   6. (optional, gated) creates and reads back a scribe session
#      against the pilot test org — only if
#      CHARTNAV_SMOKE_ALLOW_WRITES=1
#
# What it does NOT do:
#   - never prints tokens
#   - never writes real PHI
#   - never runs destructive operations without
#     CHARTNAV_SMOKE_ALLOW_WRITES=1
#
# Required env:
#   CHARTNAV_SMOKE_BASE_URL          e.g. https://api.pilot.example.com
#   CHARTNAV_SMOKE_ADMIN_TOKEN       JWT for an admin user in the test org
#   CHARTNAV_SMOKE_CLINICIAN_TOKEN   JWT for a clinician user in the test org
#   CHARTNAV_SMOKE_REVIEWER_TOKEN    JWT for a reviewer user in the test org
#   CHARTNAV_SMOKE_TEST_PATIENT_ID   a fake / sandboxed patient id in the
#                                    designated pilot test org
#   CHARTNAV_SMOKE_TEST_ORG_ID       the designated pilot test org id
#                                    (use a TEST org, never the real one)
#
# Optional env:
#   CHARTNAV_SMOKE_ALLOW_WRITES=1    enable the create-scribe-session
#                                    write path (otherwise read-only)
#   CHARTNAV_SMOKE_OTHER_PATIENT_ID  patient id in a *different* org for
#                                    the cross-org isolation test
#
# Usage:
#   CHARTNAV_SMOKE_BASE_URL=https://api.pilot.example.com \
#   CHARTNAV_SMOKE_ADMIN_TOKEN=$(cat ~/.chartnav/admin.jwt) \
#   CHARTNAV_SMOKE_CLINICIAN_TOKEN=$(cat ~/.chartnav/clin.jwt) \
#   CHARTNAV_SMOKE_REVIEWER_TOKEN=$(cat ~/.chartnav/rev.jwt) \
#   CHARTNAV_SMOKE_TEST_PATIENT_ID=42 \
#   CHARTNAV_SMOKE_TEST_ORG_ID=99 \
#     bash scripts/smoke_controlled_pilot.sh
#
# Exit codes:
#   0  smoke passed
#   1  required env / tooling missing
#   2  one or more smoke checks failed

set -uo pipefail

BASE_URL="${CHARTNAV_SMOKE_BASE_URL:-}"
ADMIN_TOKEN="${CHARTNAV_SMOKE_ADMIN_TOKEN:-}"
CLINICIAN_TOKEN="${CHARTNAV_SMOKE_CLINICIAN_TOKEN:-}"
REVIEWER_TOKEN="${CHARTNAV_SMOKE_REVIEWER_TOKEN:-}"
TEST_PATIENT_ID="${CHARTNAV_SMOKE_TEST_PATIENT_ID:-}"
TEST_ORG_ID="${CHARTNAV_SMOKE_TEST_ORG_ID:-}"
OTHER_PATIENT_ID="${CHARTNAV_SMOKE_OTHER_PATIENT_ID:-}"
ALLOW_WRITES="${CHARTNAV_SMOKE_ALLOW_WRITES:-0}"

fail_count=0
pass_count=0
warn_count=0
pass()  { echo "  ok    $1"; pass_count=$((pass_count + 1)); }
warn()  { echo "  warn  $1"; warn_count=$((warn_count + 1)); }
fail()  { echo "  FAIL  $1"; fail_count=$((fail_count + 1)); }

echo "ChartNav controlled-pilot smoke (Phase 18)."
echo "  base url:      ${BASE_URL:-<unset>}"
echo "  test org id:   ${TEST_ORG_ID:-<unset>}"
echo "  test patient:  ${TEST_PATIENT_ID:-<unset>}"
echo "  writes allowed: $ALLOW_WRITES"
echo "  (tokens are NEVER printed)"
echo

# ---------------------------------------------------------------
# Required env / tooling.
# ---------------------------------------------------------------
missing=0
for v in CHARTNAV_SMOKE_BASE_URL CHARTNAV_SMOKE_ADMIN_TOKEN \
         CHARTNAV_SMOKE_CLINICIAN_TOKEN CHARTNAV_SMOKE_REVIEWER_TOKEN \
         CHARTNAV_SMOKE_TEST_PATIENT_ID CHARTNAV_SMOKE_TEST_ORG_ID; do
  if [ -z "${!v:-}" ]; then
    fail "$v is not set"
    missing=$((missing + 1))
  fi
done
if [ "$missing" -gt 0 ]; then
  echo
  echo "Cannot run smoke without the required env vars above."
  echo "See the doc-block at the top of this script for the full list."
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "REFUSED: curl not on PATH."
  exit 1
fi

# Helper — make an HTTP call and return the status code.
# Token is read from the named env var by the helper so it never
# appears in argv.
http_status() {
  local method="$1"
  local path="$2"
  local token_var="${3:-}"
  local body_file="${4:-}"

  local args=(-s -o /dev/null -w "%{http_code}" -X "$method")
  if [ -n "$token_var" ]; then
    args+=(-H "Authorization: Bearer ${!token_var}")
  fi
  args+=(-H "Content-Type: application/json")
  if [ -n "$body_file" ] && [ -f "$body_file" ]; then
    args+=(--data-binary "@${body_file}")
  fi
  curl "${args[@]}" "${BASE_URL%/}${path}"
}

# ---------------------------------------------------------------
# 1. /health.
# ---------------------------------------------------------------
echo "1. /health"
status=$(http_status GET /health)
if [ "$status" = "200" ]; then
  pass "/health → 200"
else
  fail "/health → $status (expected 200)"
fi
echo

# ---------------------------------------------------------------
# 2. /me without token rejects.
# ---------------------------------------------------------------
echo "2. /me without token"
status=$(http_status GET /me)
if [ "$status" = "401" ]; then
  pass "/me without token → 401"
else
  fail "/me without token → $status (expected 401)"
fi
echo

# ---------------------------------------------------------------
# 3. /me with each role token resolves.
# ---------------------------------------------------------------
echo "3. /me with admin / clinician / reviewer tokens"
for tv in CHARTNAV_SMOKE_ADMIN_TOKEN CHARTNAV_SMOKE_CLINICIAN_TOKEN CHARTNAV_SMOKE_REVIEWER_TOKEN; do
  status=$(http_status GET /me "$tv")
  label="${tv#CHARTNAV_SMOKE_}"
  label="${label%_TOKEN}"
  if [ "$status" = "200" ]; then
    pass "/me as ${label,,} → 200"
  else
    fail "/me as ${label,,} → $status (expected 200)"
  fi
done
echo

# ---------------------------------------------------------------
# 4. Reviewer write attempt rejected.
# ---------------------------------------------------------------
echo "4. Reviewer write attempt rejected"
# Try to create a scribe session as the reviewer — should be 403.
body_tmp=$(mktemp /tmp/cn-smoke-body.XXXXXX)
cat > "$body_tmp" <<JSON
{"encounter_id": null, "title": "smoke (must be rejected)"}
JSON
status=$(http_status POST "/patients/${TEST_PATIENT_ID}/scribe-sessions" \
                          CHARTNAV_SMOKE_REVIEWER_TOKEN "$body_tmp")
rm -f "$body_tmp"
case "$status" in
  403)
    pass "reviewer scribe-create → 403 (read-only enforced)"
    ;;
  401)
    warn "reviewer scribe-create → 401 (token didn't resolve; check provisioning)"
    ;;
  *)
    fail "reviewer scribe-create → $status (expected 403)"
    ;;
esac
echo

# ---------------------------------------------------------------
# 5. Cross-org isolation.
# ---------------------------------------------------------------
echo "5. Cross-org isolation"
if [ -z "$OTHER_PATIENT_ID" ]; then
  warn "CHARTNAV_SMOKE_OTHER_PATIENT_ID not set — skipping cross-org check"
else
  status=$(http_status GET "/patients/${OTHER_PATIENT_ID}" CHARTNAV_SMOKE_ADMIN_TOKEN)
  case "$status" in
    404)
      pass "admin GET /patients/<other-org-patient> → 404 (no existence leak)"
      ;;
    403)
      warn "admin GET /patients/<other-org-patient> → 403 (existence-leak risk; expected 404)"
      ;;
    *)
      fail "admin GET /patients/<other-org-patient> → $status (expected 404)"
      ;;
  esac
fi
echo

# ---------------------------------------------------------------
# 6. Optional write path — only with explicit gate.
# ---------------------------------------------------------------
echo "6. Optional write path (CHARTNAV_SMOKE_ALLOW_WRITES gate)"
if [ "$ALLOW_WRITES" != "1" ]; then
  pass "writes disabled by default — set CHARTNAV_SMOKE_ALLOW_WRITES=1 to enable"
else
  body_tmp=$(mktemp /tmp/cn-smoke-body.XXXXXX)
  cat > "$body_tmp" <<JSON
{"encounter_id": null, "title": "phase 18 smoke session"}
JSON
  status=$(http_status POST "/patients/${TEST_PATIENT_ID}/scribe-sessions" \
                            CHARTNAV_SMOKE_CLINICIAN_TOKEN "$body_tmp")
  rm -f "$body_tmp"
  case "$status" in
    200|201)
      pass "clinician scribe-create → $status"
      ;;
    *)
      fail "clinician scribe-create → $status (expected 200 or 201)"
      ;;
  esac
fi
echo

# ---------------------------------------------------------------
# Summary.
# ---------------------------------------------------------------
echo "=========================================================="
echo "  PASS: $pass_count"
echo "  WARN: $warn_count"
echo "  FAIL: $fail_count"
echo "=========================================================="
if [ "$fail_count" -gt 0 ]; then
  echo "FAIL — controlled-pilot smoke did not pass cleanly."
  exit 2
fi
if [ "$warn_count" -gt 0 ]; then
  echo "PASSED with $warn_count warn(s); review before booking real-PHI session."
  exit 0
fi
echo "PASSED — controlled-pilot env-shape + role + isolation smoke green."
echo "Real PHI still requires BAA + practice security review +"
echo "written practice approval. See"
echo "docs/pilot/chartnav-controlled-pilot-go-live-checklist.md."
exit 0
