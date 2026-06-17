#!/usr/bin/env bash
# scripts/demo/phase101_local_seed_sqlite.sh — local SQLite migrate +
# seed helper for the Phase 101 buyer-demo evidence capture path.
#
# WHY THIS EXISTS
#   The repo-default `make reset-db` target expects
#   apps/api/.venv/bin/alembic, which a fresh workstation or sandbox
#   may not have. The Phase 101 capture script calls Phase 63C with
#   `--reset`, which in turn calls reset_demo_state.sh, which calls
#   `make reset-db` — so a workstation without the venv cannot drive
#   the capture's optional smoke stage to PASS.
#
#   This script gives the operator a venv-free path: it uses
#   whichever `alembic` and `python3` are on PATH, against the same
#   apps/api/chartnav.db file the repo's defaults use. It is a thin
#   wrapper around the alembic + scripts_seed.py commands the user
#   already demonstrated works in the local stack walkthrough.
#
# WHAT IT DOES
#   1. cd into apps/api
#   2. exports DATABASE_URL=sqlite:///./chartnav.db
#   3. exports CHARTNAV_ENV=local, CHARTNAV_LLM_ENABLED=0
#   4. deletes apps/api/chartnav.db (idempotent reset)
#   5. runs `alembic upgrade head`
#   6. runs `python3 scripts_seed.py`
#
# WHAT IT DOES NOT DO
#   - It does NOT require apps/api/.venv.
#   - It does NOT change any product behavior.
#   - It does NOT touch DATABASE_URLs other than the local SQLite
#     default; if the operator has a non-default DATABASE_URL
#     exported, the script refuses to run.
#   - It does NOT process real PHI.
#   - It does NOT enable a production LLM or any live vendor.
#   - It does NOT require MCP / Kapture.
#
# USAGE
#   bash scripts/demo/phase101_local_seed_sqlite.sh
#
# EXIT CODES
#   0  migrate + seed completed
#   1  refused (DATABASE_URL set to a non-default value)
#   2  alembic missing or seed missing on PATH

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"

# Refuse to run if the operator has DATABASE_URL pointed somewhere
# other than the local SQLite default. We will OVERRIDE it for our
# own subprocess invocations, but we won't proceed if the operator
# has set it to a postgres URL — that would suggest they expect this
# script to seed a non-local DB, which is out of scope.
if [[ -n "${DATABASE_URL:-}" ]]; then
  case "$DATABASE_URL" in
    sqlite:///*chartnav.db|sqlite:///./chartnav.db|"")
      ;;
    *)
      echo "REFUSED: DATABASE_URL is set to '$DATABASE_URL'." >&2
      echo "         This helper only seeds the local SQLite dev DB." >&2
      echo "         Unset DATABASE_URL or point it at" \
           "sqlite:///./chartnav.db to continue." >&2
      exit 1
      ;;
  esac
fi

# Find an alembic binary on PATH. Prefer the repo venv if present so
# the operator's environment isn't surprised, but fall back to the
# system alembic so a fresh workstation can still seed.
ALEMBIC=""
if [[ -x "$API_DIR/.venv/bin/alembic" ]]; then
  ALEMBIC="$API_DIR/.venv/bin/alembic"
elif command -v alembic >/dev/null 2>&1; then
  ALEMBIC="$(command -v alembic)"
fi
if [[ -z "$ALEMBIC" ]]; then
  echo "ERROR: alembic is not installed on PATH." >&2
  echo "       Install hint:" >&2
  echo "         cd '$API_DIR'" >&2
  echo "         python3 -m venv .venv" >&2
  echo "         .venv/bin/pip install -r requirements.txt" >&2
  echo "         .venv/bin/pip install -r requirements-dev.txt" >&2
  echo "       Then re-run: bash scripts/demo/phase101_local_seed_sqlite.sh" >&2
  exit 2
fi

PY=""
if [[ -x "$API_DIR/.venv/bin/python" ]]; then
  PY="$API_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
fi
if [[ -z "$PY" ]]; then
  echo "ERROR: python3 is not installed on PATH." >&2
  exit 2
fi

SEED_SCRIPT="$API_DIR/scripts_seed.py"
if [[ ! -f "$SEED_SCRIPT" ]]; then
  echo "ERROR: seed script not found at $SEED_SCRIPT" >&2
  exit 2
fi

cd "$API_DIR"

echo "[phase101-local-seed] using alembic: $ALEMBIC"
echo "[phase101-local-seed] using python:  $PY"
echo "[phase101-local-seed] resetting apps/api/chartnav.db"
rm -f "$API_DIR/chartnav.db"

export DATABASE_URL="sqlite:///./chartnav.db"
export CHARTNAV_ENV="local"
export CHARTNAV_LLM_ENABLED="0"

echo "[phase101-local-seed] alembic upgrade head"
if ! "$ALEMBIC" upgrade head; then
  echo "ERROR: alembic upgrade head failed." >&2
  exit 2
fi

echo "[phase101-local-seed] python3 scripts_seed.py"
if ! "$PY" "$SEED_SCRIPT"; then
  echo "ERROR: scripts_seed.py failed." >&2
  exit 2
fi

echo "[phase101-local-seed] PASS  apps/api/chartnav.db seeded"
