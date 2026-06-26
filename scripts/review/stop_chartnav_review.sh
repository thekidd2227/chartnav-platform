#!/usr/bin/env bash
# Stop the ChartNav review environment. Keeps Docker volumes (data persists),
# so the next start is fast and your review data is retained.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "$HERE/docker-compose.yml")

command -v docker >/dev/null 2>&1 || { echo "Docker not installed; nothing to stop."; exit 0; }
echo "==> Stopping ChartNav review containers (volumes kept)…"
"${COMPOSE[@]}" down
echo " ✓ Stopped. Data volumes preserved."
echo "   Start again : ./scripts/review/start_chartnav_review.sh"
echo "   Full reset  : ./scripts/review/reset_chartnav_review.sh"
