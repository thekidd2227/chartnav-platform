#!/usr/bin/env bash
# ChartNav — production image rollback.
#
# Pin the API image to a prior tag and restart. Uses the same
# .env.prod file and compose stack as the initial deploy.
#
# Usage:
#   scripts/deploy_rollback.sh v0.1.0                     # uses .env.prod
#   scripts/deploy_rollback.sh v0.1.0 path/to/.env.prod
#
# This script never migrates the database. If the target tag
# requires an older schema, use the practice backup/restore flow
# (docs/build/59-practice-backup-restore-reinstall.md) instead —
# rollback alone is safe only when both tags carry compatible
# schema.

set -euo pipefail

TAG="${1:-}"
ENV_FILE="${2:-infra/docker/.env.prod}"

if [[ -z "$TAG" ]]; then
  echo "usage: $0 <tag> [path-to-.env.prod]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$REPO_ROOT/$ENV_FILE" ]]; then
  echo "rollback: env file not found: $REPO_ROOT/$ENV_FILE" >&2
  exit 2
fi

echo "rollback: pinning CHARTNAV_IMAGE_TAG=$TAG"
(
  cd "$REPO_ROOT/infra/docker"
  CHARTNAV_IMAGE_TAG="$TAG" docker compose \
    --env-file "$REPO_ROOT/$ENV_FILE" \
    -f docker-compose.prod.yml up -d api
)

API_URL="${CHARTNAV_VALIDATE_URL:-http://localhost:8000}"
echo "rollback: waiting for /health at $API_URL"
DEADLINE=$(( $(date +%s) + 90 ))
while true; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$API_URL/health" || true)
  if [[ "$code" = "200" ]]; then
    echo "rollback: API healthy on $TAG"
    break
  fi
  if (( $(date +%s) > DEADLINE )); then
    echo "rollback: TIMEOUT; current API not responding" >&2
    exit 1
  fi
  sleep 3
done

echo "rollback: running enterprise_validate"
bash "$REPO_ROOT/scripts/enterprise_validate.sh" "$API_URL"
