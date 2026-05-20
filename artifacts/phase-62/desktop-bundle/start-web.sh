#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: start the ChartNav frontend for a
# local dry run. Fake-data only; refuses production-shaped CHARTNAV_ENV.

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

if [[ ! -d "$CHARTNAV_REPO_PATH/apps/web" ]]; then
  echo "ERROR: $CHARTNAV_REPO_PATH/apps/web not found." >&2
  exit 2
fi

env_name="${CHARTNAV_ENV:-local}"
case "$env_name" in
  production|staging|controlled-pilot)
    echo "ERROR: refusing to start the frontend on CHARTNAV_ENV=$env_name." >&2
    exit 3
    ;;
esac

cd "$CHARTNAV_REPO_PATH/apps/web"

if [[ ! -d node_modules ]]; then
  echo "node_modules not found; running 'npm ci' first."
  npm ci
fi

echo "starting frontend via 'npm run dev' in $CHARTNAV_REPO_PATH/apps/web"
echo "CHARTNAV_ENV=$env_name"
exec npm run dev
