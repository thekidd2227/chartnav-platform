#!/usr/bin/env bash
# scripts/verify_controlled_pilot_backup.sh — Phase 18 backup
# verifier.
#
# Inspects a Postgres backup file produced by
# scripts/backup_controlled_pilot_postgres.sh:
#
#   - file exists and is non-empty
#   - looks like a gzipped pg_dump (gzip magic + plain SQL after
#     decompression)
#   - contains the expected ChartNav schema fingerprint (a small
#     set of CREATE TABLE statements we always emit)
#   - prints byte size and timestamp
#
# This is NOT a restore-test. A real restore-test must be performed
# periodically against an isolated Postgres instance — see
# docs/security/chartnav-monitoring-logging-readiness.md.
#
# This script never prints credentials and never connects to a
# database.
#
# Usage:
#   bash scripts/verify_controlled_pilot_backup.sh /path/to/backup.sql.gz
#
# Exit codes:
#   0  backup looks valid
#   1  invocation error
#   2  file missing / empty / not a gzip
#   3  fingerprint missing (suspicious — may be truncated)

set -uo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <backup.sql.gz>"
  exit 1
fi

backup="$1"

echo "ChartNav controlled-pilot backup verifier."
echo "  file: $backup"
echo

if [ ! -f "$backup" ]; then
  echo "FAIL: file not found."
  exit 2
fi
if [ ! -s "$backup" ]; then
  echo "FAIL: file is empty."
  exit 2
fi

bytes="$(stat -f%z "$backup" 2>/dev/null || stat -c%s "$backup" 2>/dev/null || echo unknown)"
echo "  size: $bytes bytes"

# Gzip magic check.
if ! gzip -t "$backup" 2>/dev/null; then
  echo "FAIL: file does not appear to be a valid gzip stream."
  exit 2
fi
echo "  ok: valid gzip"

# Fingerprint check — confirm the expected ChartNav schema is in
# the dump. We grep the gunzipped stream for a small handful of
# known table names. The actual PHI / clinical body content is
# not inspected.
echo
echo "Schema fingerprint:"
need=(
  "CREATE TABLE.*organizations"
  "CREATE TABLE.*users"
  "CREATE TABLE.*patients"
  "CREATE TABLE.*encounters"
  "CREATE TABLE.*security_audit_events"
)
missing=0
for pat in "${need[@]}"; do
  if gunzip -c "$backup" | grep -Eq "$pat"; then
    label="${pat#CREATE TABLE.*}"
    echo "  ok: found '$label'"
  else
    echo "  FAIL: missing '$pat'"
    missing=$((missing + 1))
  fi
done
echo

if [ "$missing" -gt 0 ]; then
  echo "FAIL: $missing expected table(s) missing from dump."
  echo "      Backup may be truncated, mis-formatted, or against the wrong DB."
  exit 3
fi

echo "PASS: backup file looks structurally valid."
echo
echo "Note: this is a *structural* check, not a restore-test."
echo "      A periodic real restore-test against an isolated Postgres"
echo "      instance is required per the controlled-pilot deployment"
echo "      contract. See docs/security/chartnav-monitoring-logging-readiness.md."
exit 0
