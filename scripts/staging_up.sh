#!/usr/bin/env bash
# Boot the staging stack.
#
# Usage: scripts/staging_up.sh [--pull]
#   --pull  force docker compose pull before `up`
#
# Requirements:
#   - infra/docker/.env.staging exists (copy from .env.staging.example)
#   - CHARTNAV_IMAGE_OWNER and CHARTNAV_IMAGE_TAG are set in that file

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$REPO_ROOT/infra/docker"
ENV_FILE="$COMPOSE_DIR/.env.staging"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.staging.yml"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found." >&2
    echo "Copy infra/docker/.env.staging.example to .env.staging and fill it in." >&2
    exit 1
fi

pull=0
for arg in "$@"; do
    case "$arg" in
        --pull) pull=1 ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

cd "$COMPOSE_DIR"

echo "==> staging: config validation"
docker compose --env-file ./.env.staging -f "$COMPOSE_FILE" config >/dev/null

if [ "$pull" -eq 1 ]; then
    echo "==> staging: pull images"
    docker compose --env-file ./.env.staging -f "$COMPOSE_FILE" pull
fi

echo "==> staging: up -d"
docker compose --env-file ./.env.staging -f "$COMPOSE_FILE" up -d

echo "==> staging: containers"
docker compose --env-file ./.env.staging -f "$COMPOSE_FILE" ps
echo
echo "Next: bash scripts/staging_verify.sh"
