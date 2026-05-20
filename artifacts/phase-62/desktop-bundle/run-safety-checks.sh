#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: run every safety check the operator
# must pass before opening a buyer-demo screen-share.
#
# Phase 62A repair: prefer the API venv interpreter so the runtime
# safety validator and the Alembic safety check see the project
# dependencies (alembic, sqlalchemy, etc.). System python3 on a
# fresh iMac will not have those installed.

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

env_name="${CHARTNAV_ENV:-local}"
case "$env_name" in
  production|staging|controlled-pilot)
    echo "ERROR: refusing to run safety checks on CHARTNAV_ENV=$env_name." >&2
    echo "This wrapper is fake-data only. Unset CHARTNAV_ENV or set it to local/dev/demo/test." >&2
    exit 3
    ;;
esac
if [[ "${CHARTNAV_LLM_ENABLED:-0}" == "1" ]]; then
  echo "ERROR: CHARTNAV_LLM_ENABLED=1 is not allowed by this wrapper." >&2
  exit 4
fi
if [[ "${CHARTNAV_LLM_REAL_PHI_APPROVED:-0}" == "1" ]] || [[ "${CHARTNAV_REAL_PHI_ENABLED:-0}" == "1" ]]; then
  echo "ERROR: real-PHI gates are on; refusing to run buyer-demo safety wrapper." >&2
  exit 4
fi

cd "$CHARTNAV_REPO_PATH"

# Prefer the API venv when it exists. scripts/check_alembic_safety.sh
# honours $PYTHON; export it so the venv's python is used.
API_VENV_PYTHON="$CHARTNAV_REPO_PATH/apps/api/.venv/bin/python"
if [[ -x "$API_VENV_PYTHON" ]]; then
  export PYTHON="$API_VENV_PYTHON"
  echo "Using API venv interpreter: $PYTHON"
else
  export PYTHON="python3"
  echo "WARNING: apps/api/.venv/bin/python not found. Falling back to system python3." >&2
  echo "         Alembic safety may fail with 'No module named alembic' if the API venv has not been created." >&2
  echo "         To create the venv, see START_HERE.md → API setup." >&2
fi
echo

echo "==== runtime safety validator ===="
"$PYTHON" scripts/check_runtime_safety.py
echo
echo "==== commercial claims scanner ===="
bash scripts/check_commercial_claims.sh
echo
echo "==== website claims scanner ===="
bash scripts/check_website_claims.sh
echo
echo "==== demo claims scanner ===="
bash scripts/check_demo_claims.sh
echo
echo "==== claim policy fixtures ===="
bash scripts/test_claim_policy_fixtures.sh
echo
echo "==== Alembic safety ===="
bash scripts/check_alembic_safety.sh
echo
echo "==== git diff --check ===="
git diff --check
echo "(no output above this line means clean)"
echo
echo "All safety checks completed. Review each section's PASS line"
echo "before opening the buyer-demo screen-share."
