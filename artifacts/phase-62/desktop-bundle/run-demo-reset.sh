#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: reset local fake-demo state.

set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${CHARTNAV_REPO_PATH:-}" ]] && [[ -f "$BUNDLE_DIR/.chartnav-demo-env" ]]; then
  # shellcheck disable=SC1091
  source "$BUNDLE_DIR/.chartnav-demo-env"
fi
if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set and $BUNDLE_DIR/.chartnav-demo-env did not provide it." >&2
  echo "Recovery: export CHARTNAV_REPO_PATH=\"\$HOME/Desktop/ARCG/chartnav-platform\" before running this wrapper." >&2
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
