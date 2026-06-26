#!/usr/bin/env bash
# Start the ChartNav local REVIEW environment with one command.
# Synthetic data only. Dev identity selection. No real PHI / no live services.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
COMPOSE_FILE="$HERE/docker-compose.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")
LOG_DIR="$HERE/.logs"
mkdir -p "$LOG_DIR"
WEB="http://localhost:5173"
API="http://localhost:8000"
HEALTH_TIMEOUT=90

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ✓\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m ✗ %s\033[0m\n' "$*" >&2; exit 1; }

# 1. Docker exists
command -v docker >/dev/null 2>&1 || die "Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
docker compose version >/dev/null 2>&1 || die "'docker compose' (v2) is not available."

# 2. Docker running
docker info >/dev/null 2>&1 || die "Docker is installed but the daemon is not running. Start Docker Desktop, then re-run."
ok "Docker is running ($(docker version --format '{{.Server.Version}}' 2>/dev/null))"

# 3. Required host ports free — UNLESS our own review stack already holds them
#    (re-running the launcher should reconcile the existing stack, not abort).
if [ -n "$("${COMPOSE[@]}" ps -q 2>/dev/null)" ]; then
  ok "review stack already running — reusing it (up -d will reconcile)"
else
  for p in 5173 8000 9000 9001; do
    if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
      die "port $p is in use by another process. Free it (lsof -iTCP:$p) or stop the conflicting app, then re-run."
    fi
  done
  ok "required ports 5173 / 8000 / 9000 / 9001 are available"
fi

# 4-8. Build + start (migrate → seed → api → web are ordered via depends_on).
say "Building images + starting containers (first run can take a few minutes)…"
"${COMPOSE[@]}" up -d --build 2>&1 | tee "$LOG_DIR/up.log" | tail -8
ok "containers started"

# 9. Poll health (loop, not a fixed sleep) up to ${HEALTH_TIMEOUT}s.
poll() { # url label
  local url="$1" label="$2" waited=0
  while (( waited < HEALTH_TIMEOUT )); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "$url")" = "200" ]; then
      ok "$label ready (${waited}s)"; return 0
    fi
    sleep 2; waited=$((waited+2))
  done
  echo "   recent api logs:" >&2; "${COMPOSE[@]}" logs --tail 30 api >&2 2>/dev/null
  die "$label did not become ready within ${HEALTH_TIMEOUT}s."
}
say "Waiting for services to become healthy…"
poll "$API/healthz" "API (/healthz)"
poll "$API/readyz"  "API database (/readyz)"
poll "$WEB" "Frontend"

# 10. Verify the running system.
say "Verifying the running platform…"
if bash "$HERE/verify_chartnav_review.sh"; then
  ok "verification passed"
else
  echo "   ⚠️ verification reported failures — the app is up but review docs/feature script note known gaps." >&2
fi

# 11. Open the app (macOS).
[ "$(uname -s)" = "Darwin" ] && { open "$WEB" 2>/dev/null && ok "opened $WEB"; } || true

# 12. Summary.
cat <<EOF

────────────────────────────────────────────────────────────
  ChartNav review environment is UP.

  Frontend : $WEB
  API      : $API
  API health: $API/healthz   (readiness: $API/readyz)
  MinIO    : http://localhost:9000  (console http://localhost:9001)

  Demo identities (pick one in the UI's dev identity selector):
    admin@chartnav.local   (admin)
    clin@chartnav.local    (clinician)
    tech@chartnav.local    (technician)
    front@chartnav.local   (front desk)
    rev@chartnav.local     (reviewer / read-only)
  Second org for cross-tenant tests: admin@northside.local

  Walkthrough : docs/review/FEATURE_TEST_SCRIPT.md
  Identities  : docs/review/DEMO_IDENTITIES.md
  Limitations : docs/review/KNOWN_LIMITATIONS.md

  Stop  : ./scripts/review/stop_chartnav_review.sh     (keeps data)
  Reset : ./scripts/review/reset_chartnav_review.sh    (wipes data, re-seeds next start)
  Logs  : docker compose -f scripts/review/docker-compose.yml logs -f
          startup log: $LOG_DIR/up.log
────────────────────────────────────────────────────────────
EOF
