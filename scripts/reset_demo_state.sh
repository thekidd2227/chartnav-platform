#!/usr/bin/env bash
# scripts/reset_demo_state.sh — restore the local demo environment.
#
# What it does:
#   1. drops + re-creates the local SQLite dev DB via `make reset-db`
#      (alembic migrate + idempotent seed against the fake demo
#      data already in scripts_seed.py);
#   2. clears the recommended browser-side demo state by printing
#      a short DevTools snippet the presenter can paste once
#      (localStorage keys: chartnav.demoStep, chartnav.demoMode,
#      chartnav.devIdentity);
#   3. prints the obvious "fake demo data only" reminder so a
#      presenter never confuses the demo with a real-PHI run.
#
# Non-destructive against any environment that is not the local dev
# SQLite DB — refuses to run if DATABASE_URL points at anything
# other than the default sqlite path.
#
# Usage:
#   bash scripts/reset_demo_state.sh
# Exit codes:
#   0  reset completed
#   1  refused to run because DATABASE_URL was not the local
#      SQLite default
#   2  reset-db / seed failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

EXPECTED_PREFIX="sqlite:///"
ACTIVE_URL="${DATABASE_URL:-}"

echo "ChartNav demo reset — fake demo data only."
echo

# Refuse to run against anything that looks like staging/production.
# An empty DATABASE_URL means the app falls back to the default
# local SQLite path (apps/api/chartnav.db) — that's safe.
if [ -n "$ACTIVE_URL" ] && [[ "$ACTIVE_URL" != "$EXPECTED_PREFIX"* ]]; then
  echo "REFUSED: DATABASE_URL is set to '$ACTIVE_URL'."
  echo "         This script only resets the local SQLite dev DB."
  echo "         Unset DATABASE_URL or point it at sqlite:///<path> to continue."
  exit 1
fi

echo "1. Resetting the local dev DB (alembic migrate + seed)…"
if ! make reset-db; then
  echo "FAILED — make reset-db returned non-zero."
  exit 2
fi
echo "   ok — dev DB is at apps/api/chartnav.db with the seeded fake demo data."
echo

echo "2. Verifying seed invariants…"
PY="$REPO_ROOT/apps/api/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
if "$PY" scripts/verify_seed_invariants.py --db apps/api/chartnav.db; then
  echo "   ok — Morgan Lee / PT-1001 / encounter 1 / clinician verified."
else
  echo "   WARN — seed verification reported failures. The DB was reset"
  echo "   but the seeded state may not match demo expectations."
  echo "   Check apps/api/scripts_seed.py for the expected seed shape."
fi
echo

echo "3. Cleaning up stale smoke temp files…"
rm -f /tmp/phase63c.*.json /tmp/phase63c.*.log /tmp/phase63c.*.txt 2>/dev/null
echo "   ok — /tmp/phase63c.* removed."
echo

echo "4. Clearing browser-side demo state."
echo "   Paste the following into the browser DevTools console once:"
echo
cat <<'BROWSER'
   try {
     localStorage.removeItem("chartnav.demoStep");
     localStorage.removeItem("chartnav.demoMode");
     console.info("ChartNav demo state cleared.");
   } catch (e) { console.warn("localStorage cleanup skipped", e); }
BROWSER
echo
echo "   If you also want to drop the dev identity selector to its"
echo "   default (admin@chartnav.local), additionally clear:"
echo "   localStorage.removeItem(\"chartnav.devIdentity\");"
echo

echo "5. Reminders for the presenter:"
echo "   - The seeded data is fake by construction (org slug:"
echo "     demo-eye-clinic, patient PT-1001 'Morgan Lee')."
echo "   - Do NOT use this script against staging or"
echo "     controlled-pilot environments."
echo "   - Do NOT load any real PHI into a 'local' or 'staging'"
echo "     environment — those modes are fake-data only."
echo "   - To enable Phase 15 Guided Demo Mode in the workspace,"
echo "     append '?demo=1' to the URL or set localStorage"
echo "     'chartnav.demoMode' to '1'."
echo
echo "6. Next steps:"
echo "   Start the API:   cd apps/api && .venv/bin/uvicorn app.main:app --port 8765"
echo "   Start the web:   cd apps/web && npm run dev -- --port 5173"
echo "   Run preflight:   PHASE63C_API_URL=http://127.0.0.1:8765 \\"
echo "                    PHASE63C_WEB_URL=http://127.0.0.1:5173 \\"
echo "                    bash scripts/demo/demo_preflight.sh"
echo "   Run smoke:       PHASE63C_API_URL=http://127.0.0.1:8765 \\"
echo "                    PHASE63C_WEB_URL=http://127.0.0.1:5173 \\"
echo "                    bash scripts/demo/phase63c_functional_smoke.sh"
echo
echo "Demo reset complete."
