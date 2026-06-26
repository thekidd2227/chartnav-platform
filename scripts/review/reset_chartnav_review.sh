#!/usr/bin/env bash
# Reset the ChartNav review environment to a clean slate: stop containers AND
# remove the Postgres + MinIO volumes. The next start re-migrates and re-seeds
# deterministic synthetic data. Use this if the review DB gets into a weird
# state. Safe — it only touches the disposable review volumes.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "$HERE/docker-compose.yml")

command -v docker >/dev/null 2>&1 || { echo "Docker not installed; nothing to reset."; exit 0; }
echo "==> Resetting ChartNav review env (containers + data volumes removed)…"
"${COMPOSE[@]}" down -v --remove-orphans
echo " ✓ Reset complete. Fresh synthetic data will be seeded on next start:"
echo "   ./scripts/review/start_chartnav_review.sh"
