#!/usr/bin/env bash
# scripts/restore_controlled_pilot_postgres.sh — Phase 18
# controlled-pilot Postgres restore.
#
# Restores a `pg_dump` SQL backup (gzipped) into the controlled-
# pilot Postgres database.
#
# *** DESTRUCTIVE ***
#
# Restore overwrites the live database. This script refuses to run
# unless an explicit confirmation flag is set:
#
#   CHARTNAV_RESTORE_CONFIRM=I_UNDERSTAND
#
# Usage:
#   CHARTNAV_RESTORE_CONFIRM=I_UNDERSTAND \
#     bash scripts/restore_controlled_pilot_postgres.sh /path/to/backup.sql.gz
#
# Dry-run (parse + report; touches nothing):
#   CHARTNAV_RESTORE_DRY_RUN=1 \
#     bash scripts/restore_controlled_pilot_postgres.sh /path/to/backup.sql.gz
#
# Exit codes:
#   0  restore complete (or dry-run completed)
#   1  refused (no confirmation, no DATABASE_URL, SQLite, etc.)
#   2  backup file missing / empty
#   3  psql failed
#   4  invocation error (missing argument)

set -uo pipefail

CONFIRM="${CHARTNAV_RESTORE_CONFIRM:-}"
DRY_RUN="${CHARTNAV_RESTORE_DRY_RUN:-0}"

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <backup.sql.gz>"
  echo "       (set CHARTNAV_RESTORE_CONFIRM=I_UNDERSTAND to actually run)"
  exit 4
fi
backup_file="$1"

echo "ChartNav controlled-pilot Postgres restore."
echo "  backup_file: $backup_file"
echo "  dry-run:     $DRY_RUN"
echo
echo "*** DESTRUCTIVE ***"
echo "  This will OVERWRITE the live controlled-pilot database."
echo "  Use only on a pre-approved restore window. Coordinate with"
echo "  the practice's IT and clinical owners before running."
echo

# ---------------------------------------------------------------
# Confirmation flag.
# ---------------------------------------------------------------
if [ "$DRY_RUN" != "1" ] && [ "$CONFIRM" != "I_UNDERSTAND" ]; then
  echo "REFUSED: CHARTNAV_RESTORE_CONFIRM is not set to I_UNDERSTAND."
  echo "         Set it explicitly to run this destructive operation."
  echo "         Or run with CHARTNAV_RESTORE_DRY_RUN=1 to preview."
  exit 1
fi

# ---------------------------------------------------------------
# Backup file checks.
# ---------------------------------------------------------------
if [ ! -f "$backup_file" ]; then
  echo "REFUSED: backup file does not exist: $backup_file"
  exit 2
fi
if [ ! -s "$backup_file" ]; then
  echo "REFUSED: backup file is empty: $backup_file"
  exit 2
fi

# ---------------------------------------------------------------
# DATABASE_URL safety.
# ---------------------------------------------------------------
if [ -z "${DATABASE_URL:-}" ]; then
  echo "REFUSED: DATABASE_URL is not set."
  exit 1
fi

case "${DATABASE_URL}" in
  sqlite:*)
    echo "REFUSED: DATABASE_URL is SQLite. This script is Postgres-only."
    exit 1
    ;;
  postgresql*|postgres*)
    : # ok
    ;;
  *)
    echo "REFUSED: DATABASE_URL scheme is not recognized as Postgres."
    exit 1
    ;;
esac

if ! command -v psql >/dev/null 2>&1; then
  echo "REFUSED: psql not on PATH. Install postgresql-client."
  exit 1
fi
if ! command -v gunzip >/dev/null 2>&1; then
  echo "REFUSED: gunzip not on PATH."
  exit 1
fi

# ---------------------------------------------------------------
# Dry run.
# ---------------------------------------------------------------
if [ "$DRY_RUN" = "1" ]; then
  bytes="$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo unknown)"
  echo "(dry-run) backup file:    $backup_file ($bytes bytes)"
  echo "(dry-run) DATABASE scheme: postgres (specific URL not echoed)"
  echo "(dry-run) would: gunzip -c \$backup_file | psql \$DATABASE_URL"
  echo "(dry-run) would: stop on first error (psql -v ON_ERROR_STOP=1)"
  echo
  echo "DRY-RUN complete. No database changes."
  exit 0
fi

# ---------------------------------------------------------------
# Execute restore.
# ---------------------------------------------------------------
echo "Running restore. Press Ctrl-C within 10 seconds to abort."
for i in 10 9 8 7 6 5 4 3 2 1; do
  printf "  %s … " "$i"
  sleep 1
done
echo
echo

# `ON_ERROR_STOP=1` ensures the restore halts on the first SQL
# error rather than silently leaving the DB half-restored.
if ! gunzip -c "$backup_file" | psql -v ON_ERROR_STOP=1 "$DATABASE_URL" \
     > /tmp/chartnav_restore_log.$$ 2>&1; then
  status=$?
  echo "FAILED: psql exited $status"
  echo "  Last 10 lines of log (URLs / passwords scrubbed):"
  tail -10 /tmp/chartnav_restore_log.$$ \
    | sed -E 's/postgres(ql)?:\/\/[^[:space:]]+/postgres:\/\/[REDACTED]/g'
  rm -f /tmp/chartnav_restore_log.$$
  exit 3
fi
rm -f /tmp/chartnav_restore_log.$$

echo "Restore complete."
echo
echo "Next steps:"
echo "  - Smoke-test the live API: bash scripts/smoke_controlled_pilot.sh"
echo "  - Notify practice clinical / IT owners that restore window is closed."
echo "  - File an incident note per docs/security/chartnav-incident-response-plan.md"
echo "    if this restore was triggered by a data-safety event."
exit 0
