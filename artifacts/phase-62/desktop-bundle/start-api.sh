#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: boot the ChartNav API for a local
# dry run. Refuses to run on production / staging / controlled-pilot
# CHARTNAV_ENV, and refuses to enable production LLM. This is a
# fake-data wrapper; do not adapt it for real PHI.

set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${CHARTNAV_REPO_PATH:-}" ]] && [[ -f "$BUNDLE_DIR/.chartnav-demo-env" ]]; then
  # shellcheck disable=SC1091
  source "$BUNDLE_DIR/.chartnav-demo-env"
fi
if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set and $BUNDLE_DIR/.chartnav-demo-env did not provide it." >&2
  echo "Recovery:" >&2
  echo "  1. export CHARTNAV_REPO_PATH=\"\$HOME/Desktop/ARCG/chartnav-platform\"" >&2
  echo "  2. or edit $BUNDLE_DIR/.chartnav-demo-env so CHARTNAV_REPO_PATH points at your local checkout." >&2
  echo "See START_HERE.md for the full setup walkthrough." >&2
  exit 2
fi

if [[ ! -d "$CHARTNAV_REPO_PATH/apps/api" ]] || [[ ! -f "$CHARTNAV_REPO_PATH/Makefile" ]]; then
  echo "ERROR: $CHARTNAV_REPO_PATH does not look like a chartnav-platform checkout." >&2
  exit 2
fi

env_name="${CHARTNAV_ENV:-local}"
case "$env_name" in
  production|staging|controlled-pilot)
    echo "ERROR: refusing to start a buyer-demo API on CHARTNAV_ENV=$env_name." >&2
    echo "Unset CHARTNAV_ENV or set it to local/dev/demo/test." >&2
    exit 3
    ;;
esac

# Hard-block production LLM activation from this wrapper. Operators
# who want to test the optional OpenAI fake-data adapter set the
# env explicitly in a different shell, not through this wrapper.
if [[ "${CHARTNAV_LLM_ENABLED:-0}" == "1" ]]; then
  echo "ERROR: CHARTNAV_LLM_ENABLED=1 is not allowed by this wrapper." >&2
  echo "Unset it or set to 0 before running ./start-api.sh." >&2
  exit 4
fi
if [[ "${CHARTNAV_LLM_REAL_PHI_APPROVED:-0}" == "1" ]]; then
  echo "ERROR: CHARTNAV_LLM_REAL_PHI_APPROVED=1 is not allowed by this wrapper." >&2
  exit 4
fi
if [[ "${CHARTNAV_REAL_PHI_ENABLED:-0}" == "1" ]]; then
  echo "ERROR: CHARTNAV_REAL_PHI_ENABLED=1 is not allowed by this wrapper." >&2
  exit 4
fi

echo "starting API in $CHARTNAV_REPO_PATH"
echo "CHARTNAV_ENV=$env_name"

# Phase 63C — auto-bring the demo DB to Alembic head + seed before
# booting. This is non-destructive: `make migrate` runs
# `alembic upgrade head` (no rm), and `make seed` is idempotent
# (it upserts Morgan Lee / PT-1001 / Encounter #1 + the demo org
# without disturbing existing rows). Operators who want a clean
# Morgan-only DB run `bash scripts/reset_demo_state.sh` first.
#
# Skip the auto-migrate by setting CHARTNAV_DEMO_SKIP_MIGRATE=1.
if [[ "${CHARTNAV_DEMO_SKIP_MIGRATE:-0}" != "1" ]]; then
  echo "migrating demo DB to Alembic head…"
  if ! make -C "$CHARTNAV_REPO_PATH" migrate; then
    echo "ERROR: 'make migrate' failed. Refusing to boot a buyer-demo API on a stale DB." >&2
    echo "Recovery: run 'bash $CHARTNAV_REPO_PATH/scripts/reset_demo_state.sh' for a clean reset." >&2
    exit 5
  fi
  echo "seeding demo DB (idempotent)…"
  if ! make -C "$CHARTNAV_REPO_PATH" seed; then
    echo "ERROR: 'make seed' failed. Recovery: 'bash $CHARTNAV_REPO_PATH/scripts/reset_demo_state.sh'." >&2
    exit 5
  fi
fi

exec make -C "$CHARTNAV_REPO_PATH" boot
