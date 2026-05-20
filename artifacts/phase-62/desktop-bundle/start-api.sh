#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: boot the ChartNav API for a local
# dry run. Refuses to run on production / staging / controlled-pilot
# CHARTNAV_ENV, and refuses to enable production LLM. This is a
# fake-data wrapper; do not adapt it for real PHI.

set -euo pipefail

if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set. See START_HERE.md." >&2
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

echo "starting API via 'make boot' in $CHARTNAV_REPO_PATH"
echo "CHARTNAV_ENV=$env_name"
exec make -C "$CHARTNAV_REPO_PATH" boot
