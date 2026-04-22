#!/usr/bin/env bash
# ChartNav — first-install / rebootstrap helper.
#
# Idempotent: safe to re-run. Performs the one-time steps required
# before a fresh deployment can serve its first request.
#
# Usage:
#   scripts/bootstrap.sh infra/docker/.env.prod
#
# Steps:
#   1. run deploy_preflight against the given env file
#   2. bring the stack up (`docker compose up -d`)
#   3. wait for the API to report /health:200
#   4. run enterprise_validate against the live stack
#   5. print the admin next-steps
#
# Exit codes:
#   0 — stack came up green
#   1 — preflight, up, or post-deploy validate failed

set -euo pipefail

ENV_FILE="${1:-infra/docker/.env.prod}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$REPO_ROOT/$ENV_FILE" ]]; then
  echo "bootstrap: env file not found: $REPO_ROOT/$ENV_FILE" >&2
  echo "bootstrap: copy infra/docker/.env.prod.example to $ENV_FILE and fill it in" >&2
  exit 1
fi

cd "$REPO_ROOT"

echo "== (1/4) preflight =="
bash scripts/deploy_preflight.sh "$ENV_FILE"

echo
echo "== (2/4) docker compose up -d =="
(
  cd "$REPO_ROOT/infra/docker"
  docker compose --env-file "$REPO_ROOT/$ENV_FILE" -f docker-compose.prod.yml up -d
)

# Derive the base URL from the env file (best-effort; defaults to
# localhost:8000).
API_URL="http://localhost:8000"

echo
echo "== (3/4) waiting for /health =="
DEADLINE=$(( $(date +%s) + 90 ))
while true; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$API_URL/health" || true)
  if [[ "$code" = "200" ]]; then
    echo "bootstrap: API healthy"
    break
  fi
  if (( $(date +%s) > DEADLINE )); then
    echo "bootstrap: TIMEOUT waiting for $API_URL/health" >&2
    exit 1
  fi
  sleep 3
done

echo
echo "== (4/4) enterprise validate =="
bash scripts/enterprise_validate.sh "$API_URL"

echo
cat <<'DONE'
== bootstrap done ==
Next steps:
  - Open the frontend and sign in as your configured admin.
  - Visit Admin → Operations to confirm:
      * evidence chain integrity (Infrastructure bucket)
      * signing posture (if signing is enabled)
      * sink delivery (if the sink is configured)
  - Visit Admin → Backup to create your first practice backup.
  - Save the backup file somewhere OUTSIDE this server's disk.
DONE
