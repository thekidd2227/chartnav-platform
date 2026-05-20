#!/usr/bin/env bash
# Phase 62 buyer-demo wrapper: start the ChartNav frontend for a
# local dry run. Fake-data only; refuses production-shaped CHARTNAV_ENV.

set -euo pipefail

if [[ -z "${CHARTNAV_REPO_PATH:-}" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH not set. See START_HERE.md." >&2
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
