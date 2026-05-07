#!/usr/bin/env bash
# scripts/validate_controlled_pilot_env.sh — Phase 18 controlled-pilot
# environment validator.
#
# Verifies the runtime environment is configured for a controlled-
# pilot deployment that *may* (after BAA + practice security review +
# practice approval) process real PHI. Run this against the
# environment shell that will boot the controlled-pilot containers,
# OR against a CI environment that mirrors production env.
#
# What this script does:
#   - inspects environment variables (NEVER prints values)
#   - reports PASS / WARN / FAIL per check
#   - exits non-zero on any FAIL so CI / deploy pipelines can gate
#
# What this script does NOT do:
#   - does not connect to the database
#   - does not connect to OIDC / JWKS
#   - does not exfiltrate, hash, or transform any secret
#   - does not write anywhere on disk
#
# This script is NOT a HIPAA / SOC 2 / certified-EHR compliance
# check. It is a thin pre-flight env-shape gate. Real compliance
# requires BAA, practice security review, and practice approval.
#
# Usage:
#   bash scripts/validate_controlled_pilot_env.sh
#
# Override (rare):
#   CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1 — practice has
#   approved external STT vendor in writing.
#
# Exit codes:
#   0  PASS (no FAIL; warns are tolerated)
#   1  FAIL (one or more required checks failed)
#   2  invocation error (this script doesn't run in PHI environments
#      via STDIN, etc.)

set -uo pipefail

fail_count=0
warn_count=0
pass_count=0

pass()  { echo "  ok    $1"; pass_count=$((pass_count + 1)); }
warn()  { echo "  warn  $1"; warn_count=$((warn_count + 1)); }
fail()  { echo "  FAIL  $1"; fail_count=$((fail_count + 1)); }

is_set() {
  # Returns 0 if the named env var is set AND non-empty.
  local name="$1"
  if [ -z "${!name+x}" ]; then return 1; fi
  if [ -z "${!name}" ]; then return 1; fi
  return 0
}

starts_with() {
  case "$1" in
    "$2"*) return 0 ;;
    *)     return 1 ;;
  esac
}

contains() {
  case "$1" in
    *"$2"*) return 0 ;;
    *)      return 1 ;;
  esac
}

echo "ChartNav controlled-pilot environment validator (Phase 18)."
echo "  This is NOT a HIPAA / SOC 2 compliance check."
echo "  Real compliance requires BAA + practice security review +"
echo "  practice approval. See docs/pilot/chartnav-controlled-pilot-go-live-checklist.md."
echo

# ---------------------------------------------------------------
# 1. Auth mode must be bearer.
# ---------------------------------------------------------------
echo "1. Authentication"
if ! is_set CHARTNAV_AUTH_MODE; then
  fail "CHARTNAV_AUTH_MODE is not set. Required: 'bearer' for controlled-pilot."
elif [ "${CHARTNAV_AUTH_MODE}" != "bearer" ]; then
  fail "CHARTNAV_AUTH_MODE is '${CHARTNAV_AUTH_MODE}'. Required: 'bearer' for controlled-pilot. 'header' is dev-only and never safe for PHI."
else
  pass "CHARTNAV_AUTH_MODE=bearer"
fi

for var in CHARTNAV_JWT_ISSUER CHARTNAV_JWT_AUDIENCE CHARTNAV_JWT_JWKS_URL; do
  if ! is_set "$var"; then
    fail "$var is not set. Required when CHARTNAV_AUTH_MODE=bearer."
  else
    pass "$var is set"
  fi
done

if is_set CHARTNAV_JWT_USER_CLAIM; then
  pass "CHARTNAV_JWT_USER_CLAIM is set"
else
  warn "CHARTNAV_JWT_USER_CLAIM is not set; defaults to 'email'. Confirm this matches the practice's IdP."
fi

# JWKS URL should be https in a real pilot.
if is_set CHARTNAV_JWT_JWKS_URL; then
  if starts_with "${CHARTNAV_JWT_JWKS_URL}" "https://"; then
    pass "CHARTNAV_JWT_JWKS_URL uses HTTPS"
  else
    fail "CHARTNAV_JWT_JWKS_URL is not HTTPS. Required for controlled-pilot."
  fi
fi
echo

# ---------------------------------------------------------------
# 2. Database must be Postgres, not SQLite, not local demo.
# ---------------------------------------------------------------
echo "2. Database"
if ! is_set DATABASE_URL; then
  fail "DATABASE_URL is not set. Required: postgres URL for controlled-pilot."
else
  if starts_with "${DATABASE_URL}" "sqlite:"; then
    fail "DATABASE_URL is SQLite. Required: postgresql+psycopg://… for controlled-pilot. SQLite is local-demo only."
  elif starts_with "${DATABASE_URL}" "postgresql"; then
    pass "DATABASE_URL is Postgres"
    if contains "${DATABASE_URL}" "127.0.0.1" || contains "${DATABASE_URL}" "localhost"; then
      warn "DATABASE_URL points at localhost. Confirm this is the practice-approved Postgres host, not a developer laptop."
    fi
    if contains "${DATABASE_URL}" "chartnav:chartnav"; then
      fail "DATABASE_URL contains the dev placeholder credentials 'chartnav:chartnav'. Rotate to practice-issued credentials."
    fi
    # The local demo DB filename is `chartnav.db` — we already
    # caught sqlite above; defensive double-check.
    if contains "${DATABASE_URL}" "chartnav.db"; then
      fail "DATABASE_URL references the local demo file 'chartnav.db'. Controlled-pilot uses Postgres only."
    fi
  else
    fail "DATABASE_URL scheme is not recognized as Postgres or SQLite. Inspect manually."
  fi
fi
echo

# ---------------------------------------------------------------
# 3. CORS must be explicit, not wildcard.
# ---------------------------------------------------------------
echo "3. CORS"
if ! is_set CHARTNAV_CORS_ALLOW_ORIGINS; then
  warn "CHARTNAV_CORS_ALLOW_ORIGINS is not set. Default rejects cross-origin; confirm this matches the practice's frontend host."
else
  if [ "${CHARTNAV_CORS_ALLOW_ORIGINS}" = "*" ]; then
    fail "CHARTNAV_CORS_ALLOW_ORIGINS='*' is forbidden in controlled-pilot. List explicit origins."
  elif contains "${CHARTNAV_CORS_ALLOW_ORIGINS}" "localhost" \
       || contains "${CHARTNAV_CORS_ALLOW_ORIGINS}" "127.0.0.1"; then
    fail "CHARTNAV_CORS_ALLOW_ORIGINS contains localhost / 127.0.0.1. Strip dev origins from controlled-pilot config."
  else
    pass "CHARTNAV_CORS_ALLOW_ORIGINS is explicit and dev-free"
  fi
fi
echo

# ---------------------------------------------------------------
# 4. Audit retention must be configured.
# ---------------------------------------------------------------
echo "4. Audit retention"
if ! is_set CHARTNAV_AUDIT_RETENTION_DAYS; then
  fail "CHARTNAV_AUDIT_RETENTION_DAYS is not set. Required: integer >= 0 (per practice agreement)."
else
  if [[ "${CHARTNAV_AUDIT_RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
    if [ "${CHARTNAV_AUDIT_RETENTION_DAYS}" = "0" ]; then
      warn "CHARTNAV_AUDIT_RETENTION_DAYS=0 (no automatic pruning). Confirm this matches practice retention policy."
    else
      pass "CHARTNAV_AUDIT_RETENTION_DAYS=${CHARTNAV_AUDIT_RETENTION_DAYS} (integer)"
    fi
  else
    fail "CHARTNAV_AUDIT_RETENTION_DAYS must be a non-negative integer."
  fi
fi
echo

# ---------------------------------------------------------------
# 5. Backup destination must be documented.
# ---------------------------------------------------------------
echo "5. Backup destination"
if is_set CHARTNAV_BACKUP_DIR; then
  pass "CHARTNAV_BACKUP_DIR is set"
else
  warn "CHARTNAV_BACKUP_DIR is not set. scripts/backup_controlled_pilot_postgres.sh will write to ./backups/ by default. Confirm this is practice-approved storage, NOT inside the repo."
fi
echo

# ---------------------------------------------------------------
# 6. Logging destination must be documented.
# ---------------------------------------------------------------
echo "6. Logging destination"
if is_set CHARTNAV_LOG_DESTINATION; then
  pass "CHARTNAV_LOG_DESTINATION is set"
else
  warn "CHARTNAV_LOG_DESTINATION is not set. Confirm logs are forwarded to a practice-approved sink (no PHI in logs by contract; verify the sink does not retain auth headers / clinical bodies)."
fi
echo

# ---------------------------------------------------------------
# 7. STT provider gating.
# ---------------------------------------------------------------
echo "7. STT provider"
stt="${CHARTNAV_STT_PROVIDER:-stub}"
case "$stt" in
  stub|none|"")
    pass "CHARTNAV_STT_PROVIDER=$stt (no external speech-to-text vendor)"
    ;;
  openai_whisper)
    if [ "${CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER:-0}" = "1" ]; then
      warn "CHARTNAV_STT_PROVIDER=openai_whisper allowed by CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1. Confirm a BAA chain exists with the STT vendor and the practice has approved external PHI egress in writing."
    else
      fail "CHARTNAV_STT_PROVIDER=openai_whisper requires explicit practice approval. Set CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1 only after the practice signs off in writing."
    fi
    ;;
  *)
    fail "CHARTNAV_STT_PROVIDER='$stt' is not in the approved provider list (stub | none | openai_whisper)."
    ;;
esac
echo

# ---------------------------------------------------------------
# 8. Refuse dev / demo footguns.
# ---------------------------------------------------------------
echo "8. Dev / demo footgun checks"
if [ "${CHARTNAV_RUN_SEED:-0}" = "1" ]; then
  fail "CHARTNAV_RUN_SEED=1 is forbidden in controlled-pilot. The container would seed fake demo data on boot."
else
  pass "CHARTNAV_RUN_SEED is 0 / unset"
fi

case "${CHARTNAV_ENV:-}" in
  prod|production|controlled-pilot|controlled_pilot|pilot)
    pass "CHARTNAV_ENV=${CHARTNAV_ENV} (production-shaped)"
    ;;
  ""|dev|test|ci|staging)
    warn "CHARTNAV_ENV='${CHARTNAV_ENV:-<unset>}' is dev/staging-shaped. Set to 'controlled-pilot' (or equivalent) for a real pilot environment."
    ;;
  *)
    warn "CHARTNAV_ENV='${CHARTNAV_ENV}' is non-standard. Document what this value means in the practice's runbook."
    ;;
esac
echo

# ---------------------------------------------------------------
# 9. Repo / runtime guardrails.
# ---------------------------------------------------------------
echo "9. Repo guardrails"
if [ -t 1 ] && [ -d ".git" ]; then
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "  branch:  $branch"
  if [ "$branch" != "main" ]; then
    warn "Repo is on '$branch', not 'main'. Controlled-pilot deploys from main."
  else
    pass "Repo is on main"
  fi
else
  pass "(non-tty / non-repo; skipping branch check)"
fi
echo

# ---------------------------------------------------------------
# 10. Reminder.
# ---------------------------------------------------------------
echo "10. Reminders"
echo "   - This script does NOT confirm BAA execution."
echo "   - This script does NOT confirm practice security review."
echo "   - This script does NOT confirm practice written approval."
echo "   - This script does NOT confirm backup / restore are tested."
echo "   - Use docs/pilot/chartnav-controlled-pilot-go-live-checklist.md"
echo "     before booking a real-PHI start date."
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
  echo "FAIL — controlled-pilot environment is NOT ready."
  echo "       Fix the FAIL items above before any real-PHI session."
  exit 1
fi
if [ "$warn_count" -gt 0 ]; then
  echo "PASSED with $warn_count warn(s). Review and confirm with the practice."
  exit 0
fi
echo "PASSED — env-shape gates met. Real PHI still requires BAA + practice"
echo "         security review + written practice approval."
exit 0
