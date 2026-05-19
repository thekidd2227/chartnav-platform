#!/usr/bin/env bash
# scripts/backup_controlled_pilot_postgres.sh — Phase 18 controlled-
# pilot Postgres backup script.
#
# Takes a `pg_dump` of the controlled-pilot Postgres database and
# writes it to a configurable backup directory.
#
# What this script does:
#   - refuses to run against SQLite (DATABASE_URL must be Postgres)
#   - refuses to run if DATABASE_URL is unset
#   - writes a compressed timestamped dump file
#   - never echoes credentials
#   - verifies the dump is non-empty after writing
#
# What this script does NOT do:
#   - does not implement off-host replication
#   - does not implement encryption-at-rest beyond what the
#     destination filesystem provides — encrypt the destination
#     volume per practice security review
#   - does not push to S3 / GCS / Azure — operator wires that
#     downstream
#
# Usage:
#   bash scripts/backup_controlled_pilot_postgres.sh
#
# Override the destination:
#   CHARTNAV_BACKUP_DIR=/path/to/practice-approved/storage \
#     bash scripts/backup_controlled_pilot_postgres.sh
#
# Dry run (print what would happen without writing):
#   CHARTNAV_BACKUP_DRY_RUN=1 \
#     bash scripts/backup_controlled_pilot_postgres.sh
#
# Exit codes:
#   0  backup written and verified non-empty
#   1  refused (DATABASE_URL unsafe / not Postgres)
#   2  pg_dump failed
#   3  filesystem error (mkdir / write)

set -uo pipefail

DEFAULT_BACKUP_DIR="$(pwd)/backups"
BACKUP_DIR="${CHARTNAV_BACKUP_DIR:-$DEFAULT_BACKUP_DIR}"
DRY_RUN="${CHARTNAV_BACKUP_DRY_RUN:-0}"

echo "ChartNav controlled-pilot Postgres backup."
echo "  destination: $BACKUP_DIR"
echo "  dry-run:     $DRY_RUN"
echo

# ---------------------------------------------------------------
# Safety guards.
# ---------------------------------------------------------------
if [ -z "${DATABASE_URL:-}" ]; then
  echo "REFUSED: DATABASE_URL is not set."
  echo "         This script only runs against a controlled-pilot Postgres URL."
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

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "REFUSED: pg_dump not on PATH. Install postgresql-client."
  exit 1
fi

# Reminder of what this is NOT.
echo "Reminders:"
echo "  - Backup files MUST live on practice-approved storage, encrypted at rest."
echo "  - Backup files MUST NOT be committed to the repo."
echo "  - Backup retention period must be set per practice agreement."
echo

# ---------------------------------------------------------------
# Filename.
# ---------------------------------------------------------------
ts="$(date -u +%Y%m%dT%H%M%SZ)"
out_file="$BACKUP_DIR/chartnav-${ts}.sql.gz"

if [ "$DRY_RUN" = "1" ]; then
  echo "(dry-run) would mkdir -p $BACKUP_DIR"
  echo "(dry-run) would pg_dump … | gzip > $out_file"
  echo "(dry-run) would verify $out_file is non-empty"
  echo
  echo "DRY-RUN complete. No filesystem changes."
  exit 0
fi

# ---------------------------------------------------------------
# Run.
# ---------------------------------------------------------------
if ! mkdir -p "$BACKUP_DIR"; then
  echo "FAILED: could not create $BACKUP_DIR"
  exit 3
fi

echo "Running pg_dump…"
# Use a custom-format dump piped through gzip.
# pg_dump reads DATABASE_URL natively when supplied as the connstr.
if ! pg_dump --no-owner --no-privileges --format=plain "$DATABASE_URL" 2>/tmp/chartnav_pgdump_err.$$ \
     | gzip -c > "$out_file"; then
  pg_dump_status=$?
  echo "FAILED: pg_dump exited $pg_dump_status"
  if [ -s /tmp/chartnav_pgdump_err.$$ ]; then
    # Print only the last 5 stderr lines and scrub URLs / passwords
    # from any leaked output.
    tail -5 /tmp/chartnav_pgdump_err.$$ | sed -E 's/postgres(ql)?:\/\/[^[:space:]]+/postgres:\/\/[REDACTED]/g'
  fi
  rm -f /tmp/chartnav_pgdump_err.$$
  rm -f "$out_file"
  exit 2
fi
rm -f /tmp/chartnav_pgdump_err.$$

if [ ! -s "$out_file" ]; then
  echo "FAILED: backup file is empty after pg_dump."
  rm -f "$out_file"
  exit 2
fi

bytes="$(stat -f%z "$out_file" 2>/dev/null || stat -c%s "$out_file" 2>/dev/null || echo unknown)"
echo "  ok — wrote $out_file ($bytes bytes)"
echo
echo "Backup complete."
echo "Next steps:"
echo "  - Verify with: bash scripts/verify_controlled_pilot_backup.sh \"$out_file\""
echo "  - Move to practice-approved off-host storage (NOT this filesystem)."
echo "  - Confirm retention against the practice's data-retention agreement."
exit 0
