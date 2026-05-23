#!/usr/bin/env bash
# scripts/demo/demo_preflight.sh — read-only demo readiness check.
#
# Verifies that the local environment is ready for a buyer demo
# without creating, modifying, or deleting any data. Run this
# before a buyer call to confirm the demo will work.
#
# Checks:
#   1. Environment safety (not production/staging/controlled-pilot)
#   2. Dev DB exists + at Alembic head
#   3. Seed invariants (Morgan Lee / PT-1001 / clinician / encounter 1)
#   4. API reachable at the expected URL
#   5. Frontend reachable at the expected URL
#   6. Artifact accumulation warning (stale demo runs)
#
# Exit codes:
#   0  DEMO READY
#   1  NOT READY (details printed)
#   2  invocation error

set -uo pipefail

REPO="${CHARTNAV_REPO_PATH:-$HOME/Desktop/ARCG/chartnav-platform}"
API="${PHASE63C_API_URL:-http://127.0.0.1:8000}"
WEB="${PHASE63C_WEB_URL:-http://127.0.0.1:5173}"

if [[ ! -d "$REPO" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH=$REPO does not exist." >&2
  exit 2
fi
cd "$REPO"

PY="$REPO/apps/api/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

PASS=0
FAIL=0
WARN=0
FAILURES=()

gate() {
  local name="$1"; local ok="$2"; local detail="${3:-}"
  if [[ "$ok" == "1" ]]; then
    echo "  ok   $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $name${detail:+  — $detail}" >&2
    FAIL=$((FAIL + 1))
    FAILURES+=("$name")
  fi
}

warn() {
  local name="$1"; local detail="$2"
  echo "  WARN $name  — $detail"
  WARN=$((WARN + 1))
}

echo "ChartNav demo preflight (read-only)"
echo "  repo=$REPO"
echo "  api=$API  web=$WEB"
echo

# ── 1. Environment safety ──────────────────────────────────────────
echo "[1/6] environment safety"
env_name="${CHARTNAV_ENV:-local}"
case "$env_name" in
  production|staging|controlled-pilot)
    gate "not production/staging/controlled-pilot" 0 "CHARTNAV_ENV=$env_name"
    ;;
  *)
    gate "not production/staging/controlled-pilot" 1
    ;;
esac
if [[ "${CHARTNAV_LLM_ENABLED:-0}" == "1" ]] || [[ "${CHARTNAV_REAL_PHI_ENABLED:-0}" == "1" ]]; then
  gate "production LLM / real-PHI gates are OFF" 0
else
  gate "production LLM / real-PHI gates are OFF" 1
fi

# ── 2. Dev DB exists + at Alembic head ─────────────────────────────
echo "[2/6] database state"
DB_PATH="apps/api/chartnav.db"
if [[ -f "$DB_PATH" ]]; then
  gate "dev DB exists ($DB_PATH)" 1
else
  gate "dev DB exists ($DB_PATH)" 0 "run: make reset-db"
fi
HEAD_REV="$(cd apps/api && "$PY" -m alembic heads 2>/dev/null | head -1 | awk '{print $1}')" || HEAD_REV=""
CUR_REV="$(cd apps/api && "$PY" -m alembic current 2>/dev/null | head -1 | awk '{print $1}')" || CUR_REV=""
if [[ -n "$HEAD_REV" ]] && [[ "$CUR_REV" == "$HEAD_REV" ]]; then
  gate "DB at Alembic head ($HEAD_REV)" 1
else
  gate "DB at Alembic head" 0 "current=$CUR_REV head=$HEAD_REV — run: make reset-db"
fi

# ── 3. Seed invariants ─────────────────────────────────────────────
echo "[3/6] seed invariants"
if [[ -f "$DB_PATH" ]]; then
  SEED_OK=0
  "$PY" scripts/verify_seed_invariants.py --db "$DB_PATH" 2>/dev/null && SEED_OK=1
  if [[ "$SEED_OK" == "1" ]]; then
    gate "seed invariants (Morgan Lee / PT-1001 / encounter 1 / clinician)" 1
  else
    gate "seed invariants" 0 "run: bash scripts/reset_demo_state.sh"
  fi
else
  gate "seed invariants" 0 "DB missing"
fi

# ── 4. API reachable ───────────────────────────────────────────────
echo "[4/6] API reachable"
API_STATUS="$(curl -sf -m 5 -o /dev/null -w '%{http_code}' "$API/health" 2>/dev/null || echo "000")"
if [[ "$API_STATUS" == "200" ]]; then
  gate "API $API/health responds 200" 1
else
  gate "API $API/health responds 200" 0 \
    "got $API_STATUS — start the API, or set PHASE63C_API_URL if on a different port, e.g.:\n       PHASE63C_API_URL=http://127.0.0.1:8765 bash scripts/demo/demo_preflight.sh"
fi

# ── 5. Frontend reachable ──────────────────────────────────────────
echo "[5/6] frontend reachable"
WEB_STATUS="$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$WEB/" 2>/dev/null || echo "000")"
if [[ "$WEB_STATUS" == "200" ]] || [[ "$WEB_STATUS" == "304" ]]; then
  gate "frontend $WEB/ responds $WEB_STATUS" 1
else
  gate "frontend $WEB/ responds" 0 \
    "got $WEB_STATUS — start the frontend, or set PHASE63C_WEB_URL if on a different port, e.g.:\n       PHASE63C_WEB_URL=http://127.0.0.1:5173 bash scripts/demo/demo_preflight.sh"
fi

# ── 6. Artifact accumulation ───────────────────────────────────────
echo "[6/6] artifact accumulation"
if [[ -f "$DB_PATH" ]]; then
  COUNTS="$("$PY" -c "
import sqlite3, sys
con = sqlite3.connect('$DB_PATH')
def safe_count(tbl, where='1=1'):
    try:
        return con.execute(f'SELECT COUNT(*) FROM {tbl} WHERE {where}').fetchone()[0]
    except Exception:
        return 0
v = safe_count('visit_vitals_workups', 'encounter_id=1')
s = safe_count('scribe_sessions')
f = safe_count('fundus_charts', 'encounter_id=1')
print(f'{v} {s} {f}')
" 2>/dev/null || echo "? ? ?")"
  read -r V_CT S_CT F_CT <<< "$COUNTS"
  if [[ "$V_CT" != "?" ]] && [[ "$V_CT" -gt 5 ]]; then
    warn "vitals workups on encounter 1" "$V_CT found — prior smoke runs accumulated data. Consider: bash scripts/reset_demo_state.sh"
  fi
  if [[ "$S_CT" != "?" ]] && [[ "$S_CT" -gt 5 ]]; then
    warn "scribe sessions" "$S_CT found — prior runs accumulated data. Consider: bash scripts/reset_demo_state.sh"
  fi
  if [[ "$F_CT" != "?" ]] && [[ "$F_CT" -gt 5 ]]; then
    warn "fundus charts on encounter 1" "$F_CT found — prior runs accumulated data. Consider: bash scripts/reset_demo_state.sh"
  fi
  if [[ "$WARN" -eq 0 ]]; then
    echo "  ok   no significant artifact accumulation"
  fi
fi

# ── Summary ────────────────────────────────────────────────────────
echo
echo "Demo preflight: $PASS pass / $FAIL fail / $WARN warn"
if [[ "$FAIL" -gt 0 ]]; then
  echo
  echo "NOT READY — fix the items above before demoing." >&2
  echo "Common recovery:" >&2
  echo "  1. Reset DB:    bash scripts/reset_demo_state.sh" >&2
  echo "  2. Start API:   cd apps/api && .venv/bin/uvicorn app.main:app --port 8765" >&2
  echo "  3. Start web:   cd apps/web && npm run dev -- --port 5173" >&2
  echo "  4. Re-check:    PHASE63C_API_URL=http://127.0.0.1:8765 \\" >&2
  echo "                  PHASE63C_WEB_URL=http://127.0.0.1:5173 \\" >&2
  echo "                  bash scripts/demo/demo_preflight.sh" >&2
  exit 1
fi
echo "DEMO READY."
exit 0
