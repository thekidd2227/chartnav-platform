#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: run every safety check the operator
# must pass before opening a buyer-demo screen-share.

set -euo pipefail

if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set. See START_HERE.md." >&2
  exit 2
fi

cd "$CHARTNAV_REPO_PATH"

echo "==== runtime safety validator ===="
python3 scripts/check_runtime_safety.py
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
