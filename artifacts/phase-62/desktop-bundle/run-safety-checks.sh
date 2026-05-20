#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: run every safety check the operator
# must pass before opening a buyer-demo screen-share.
#
# Phase 62A repair: prefer the API venv interpreter so the runtime
# safety validator and the Alembic safety check see the project
# dependencies (alembic, sqlalchemy, etc.). System python3 on a
# fresh iMac will not have those installed.

set -euo pipefail

if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set. See START_HERE.md." >&2
  exit 2
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
