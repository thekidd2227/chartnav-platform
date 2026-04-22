#!/usr/bin/env bash
# ChartNav — deploy preflight.
#
# Runs BEFORE `docker compose up -d` against a production-intent
# env file. Fails non-zero with a readable findings block when any
# REQUIRED configuration is missing or insecure. Safe to run as
# many times as you want; it never modifies state.
#
# Usage:
#   scripts/deploy_preflight.sh infra/docker/.env.prod
#   scripts/deploy_preflight.sh                       # uses CHARTNAV_PREFLIGHT_ENV_FILE
#
# Exit codes:
#   0 — config OK, safe to deploy
#   1 — config validation produced error-level findings
#   2 — usage error (missing env file, etc.)
#
# The heavy lifting is in `app.config.validate_production_config`;
# this script just loads the env file and calls it.

set -euo pipefail

ENV_FILE="${1:-${CHARTNAV_PREFLIGHT_ENV_FILE:-}}"

if [[ -z "$ENV_FILE" ]]; then
  echo "usage: $0 <path-to-.env.prod>" >&2
  exit 2
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "preflight: env file not found: $ENV_FILE" >&2
  exit 2
fi

# Resolve repo root from this script's directory so operator can
# invoke from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"

if [[ ! -x "$API_DIR/.venv/bin/python" ]]; then
  echo "preflight: backend venv not found at $API_DIR/.venv" >&2
  echo "          run: make install" >&2
  exit 2
fi

echo "preflight: loading env from $ENV_FILE"
# Source the env file in a subshell so we don't pollute the
# operator's shell. `set -a` auto-exports every var declared after.
(
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a

  cd "$API_DIR"
  .venv/bin/python - <<'PYEOF'
import json
import sys

try:
    from app.config import settings, validate_production_config, ProductionConfigError
except Exception as e:
    print(f"preflight: FAILED to import config: {e}", file=sys.stderr)
    sys.exit(1)

print(f"preflight: env={settings.env!r} auth_mode={settings.auth_mode!r}")
print(f"preflight: database_url={settings.database_url[:40] + '...' if len(settings.database_url) > 40 else settings.database_url!r}")

try:
    findings = validate_production_config(settings, strict=False)
except Exception as e:
    print(f"preflight: validator crashed: {e}", file=sys.stderr)
    sys.exit(1)

# Group by severity and render.
by_sev = {"error": [], "warning": [], "info": []}
for f in findings:
    by_sev.setdefault(f["severity"], []).append(f)

for sev in ("error", "warning", "info"):
    for f in by_sev.get(sev, []):
        print(f"  [{sev.upper():<7}] {f['key']}: {f['reason']}")

errors = by_sev.get("error", [])
warnings = by_sev.get("warning", [])
info = by_sev.get("info", [])
print(
    f"preflight: {len(errors)} error(s), {len(warnings)} warning(s), "
    f"{len(info)} info"
)

if errors:
    print("preflight: FAIL — resolve every ERROR above before deploying")
    sys.exit(1)

print("preflight: OK")
sys.exit(0)
PYEOF
)
