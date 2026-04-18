#!/usr/bin/env bash
# Roll the staging API back to a previously-published image tag.
#
# Usage: scripts/staging_rollback.sh <previous_tag>
#
# Strategy (honest):
#   1. Rewrite CHARTNAV_IMAGE_TAG in infra/docker/.env.staging.
#   2. docker compose pull + up -d (api service only).
#   3. Poll /ready until green (or fail).
#
# This is all rollback can be when the deployment unit is "image tag in
# a compose file". For anything more (blue/green, in-place DB
# rewinds, etc.) you need a bigger deployment substrate than compose.
# That's documented in docs/build/21-staging-runbook.md.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$REPO_ROOT/infra/docker"
ENV_FILE="$COMPOSE_DIR/.env.staging"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.staging.yml"

if [ $# -ne 1 ]; then
    echo "usage: $0 <previous_tag>" >&2
    exit 2
fi
PREV_TAG="$1"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found." >&2
    exit 1
fi

CURRENT_TAG=$(awk -F= '/^CHARTNAV_IMAGE_TAG=/{print $2}' "$ENV_FILE" | tr -d '"')
echo "==> rollback: $CURRENT_TAG -> $PREV_TAG"

# Atomic rewrite via temp file (works on macOS + Linux sed variants).
python3 - "$ENV_FILE" "$PREV_TAG" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
tag = sys.argv[2]
lines = p.read_text().splitlines()
out = []
found = False
for line in lines:
    if line.startswith("CHARTNAV_IMAGE_TAG="):
        out.append(f"CHARTNAV_IMAGE_TAG={tag}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"CHARTNAV_IMAGE_TAG={tag}")
p.write_text("\n".join(out) + "\n")
PY

cd "$COMPOSE_DIR"

echo "==> pull image $PREV_TAG"
docker compose --env-file ./.env.staging -f "$COMPOSE_FILE" pull api

echo "==> restart api"
docker compose --env-file ./.env.staging -f "$COMPOSE_FILE" up -d api

echo "==> wait for /ready"
set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a
BASE="http://127.0.0.1:${API_PORT:-8000}"
for _ in $(seq 1 40); do
    if curl -sfo /dev/null "$BASE/ready"; then
        echo "==> rollback complete: $PREV_TAG is live."
        exit 0
    fi
    sleep 1
done
echo "ERROR: /ready did not become green after rollback. Inspect:"
echo "  docker compose -f $COMPOSE_FILE logs --tail=200 api"
exit 1
