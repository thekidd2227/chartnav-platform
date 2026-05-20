#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: reset local fake-demo state.

set -euo pipefail

if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set. See START_HERE.md." >&2
  exit 2
fi

reset_script="$CHARTNAV_REPO_PATH/scripts/reset_demo_state.sh"
if [[ ! -x "$reset_script" ]] && [[ ! -f "$reset_script" ]]; then
  echo "ERROR: $reset_script not found." >&2
  exit 2
fi

env_name="${CHARTNAV_ENV:-local}"
case "$env_name" in
  production|staging|controlled-pilot)
    echo "ERROR: refusing to reset demo state on CHARTNAV_ENV=$env_name." >&2
    echo "This wrapper is fake-data only. Reset production data through" >&2
    echo "the documented production runbook, not this wrapper." >&2
    exit 3
    ;;
esac

echo "resetting local demo state via $reset_script"
exec bash "$reset_script"
