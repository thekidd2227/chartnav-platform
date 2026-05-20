#!/usr/bin/env bash
# Phase 63C functional buyer-demo smoke.
#
# Replaces the Phase 63A media-presence gate with a live HTTP smoke
# that exercises the actual buyer-demo workflows end-to-end:
#   - DB at Alembic head
#   - required demo tables exist
#   - API + frontend health
#   - Vitals create/review/sign happy path (clinician)
#   - VisitDraft create/draft/review/finalize happy path (clinician)
#   - Fundus generate/review/sign happy path (clinician)
#   - feature paths land on the real API, not the Vite origin
#
# Read-only against the running stack except for the artefacts it
# creates against Morgan Lee / PT-1001 / Encounter #1. Honours the
# usual safety env (CHARTNAV_ENV != production/staging/controlled-
# pilot, no production LLM, no real PHI gates).
#
# Exit codes:
#   0  buyer-demo functional GO
#   1  one or more gates failed (details on stderr)
#   2  invocation error (env / path / dependency)

set -uo pipefail

BUNDLE_DIR_DEFAULT="$HOME/Desktop/ChartNav-Buyer-Demo-Build"
REPO="${CHARTNAV_REPO_PATH:-$HOME/Desktop/ARCG/chartnav-platform}"
API="${PHASE63C_API_URL:-http://127.0.0.1:8000}"
WEB="${PHASE63C_WEB_URL:-http://127.0.0.1:5173}"
CLINICIAN="${PHASE63C_CLINICIAN:-clin@chartnav.local}"

if [[ ! -d "$REPO" ]]; then
  echo "ERROR: CHARTNAV_REPO_PATH=$REPO does not look like a checkout." >&2
  exit 2
fi
cd "$REPO"

env_name="${CHARTNAV_ENV:-local}"
case "$env_name" in
  production|staging|controlled-pilot)
    echo "ERROR: refusing to run smoke on CHARTNAV_ENV=$env_name." >&2
    exit 2
    ;;
esac
if [[ "${CHARTNAV_LLM_ENABLED:-0}" == "1" ]] \
   || [[ "${CHARTNAV_LLM_REAL_PHI_APPROVED:-0}" == "1" ]] \
   || [[ "${CHARTNAV_REAL_PHI_ENABLED:-0}" == "1" ]]; then
  echo "ERROR: production LLM / real-PHI gates are on; refusing to run smoke." >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required." >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required." >&2
  exit 2
fi

PY="$REPO/apps/api/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

PASS=0
FAIL=0
FAILURES=()

gate() {
  local name="$1"
  local ok="$2"
  local detail="${3:-}"
  if [[ "$ok" == "1" ]]; then
    echo "  PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $name${detail:+  - $detail}" >&2
    FAIL=$((FAIL + 1))
    FAILURES+=("$name")
  fi
}

echo "Phase 63C functional buyer-demo smoke"
echo "  repo=$REPO"
echo "  api=$API  web=$WEB  identity=$CLINICIAN"
echo

# ── 1. DB at Alembic head + required tables present ───────────────────
echo "[1/6] DB migration state"
HEAD_REV="$(cd apps/api && "$PY" -m alembic heads 2>/dev/null | head -1 | awk '{print $1}')" || HEAD_REV=""
CUR_REV="$(cd apps/api && "$PY" -m alembic current 2>/dev/null | head -1 | awk '{print $1}')" || CUR_REV=""
if [[ -n "$HEAD_REV" ]] && [[ "$CUR_REV" == "$HEAD_REV" ]]; then
  gate "db at Alembic head ($HEAD_REV)" 1
else
  gate "db at Alembic head" 0 "current=$CUR_REV head=$HEAD_REV — run 'make migrate' or 'bash scripts/reset_demo_state.sh'"
fi
TABLES_OK=1
TABLES_DETAIL=""
for tbl in work_queue_items visit_vitals_workups fundus_charts imaging_studies scribe_sessions; do
  if "$PY" -c "
import sqlite3, sys
con = sqlite3.connect('apps/api/chartnav.db')
cur = con.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='$tbl'\")
sys.exit(0 if cur.fetchone() else 1)
" 2>/dev/null; then
    :
  else
    TABLES_OK=0
    TABLES_DETAIL="${TABLES_DETAIL:+$TABLES_DETAIL, }$tbl missing"
  fi
done
gate "required demo tables exist" "$TABLES_OK" "$TABLES_DETAIL"

# ── 2. API + frontend health ──────────────────────────────────────────
echo "[2/6] api + frontend health"
HEALTH="$(curl -sf -m 5 -o /tmp/phase63c.health.json -w '%{http_code}' "$API/health" || echo "000")"
if [[ "$HEALTH" == "200" ]]; then
  gate "api $API/health 200" 1
else
  gate "api $API/health 200" 0 "got $HEALTH (is start-api.sh running?)"
fi
WEB_HEALTH="$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$WEB/" || echo "000")"
if [[ "$WEB_HEALTH" == "200" ]] || [[ "$WEB_HEALTH" == "304" ]]; then
  gate "frontend $WEB/ reachable" 1
else
  gate "frontend $WEB/ reachable" 0 "got $WEB_HEALTH (is start-web.sh running?)"
fi

# Quick check: no feature route should resolve on the frontend
# origin. Hitting /api/v1/encounters/1/vitals-workups on Vite should
# return the SPA HTML shell, not JSON; our smoke is that the API is
# the right destination for these paths.
VITE_404="$(curl -s -m 3 -o /tmp/phase63c.viteprobe.txt -w '%{http_code}' \
  -H "Accept: application/json" "$WEB/api/v1/encounters/1/vitals-workups" || echo "000")"
if [[ "$VITE_404" == "200" ]] && head -c 60 /tmp/phase63c.viteprobe.txt 2>/dev/null | grep -qi '<!doctype'; then
  gate "feature paths NOT proxied through Vite (or proxy unintentional)" 0 \
    "Vite served HTML for /api/v1/...; feature clients calling relative URLs would mis-route"
else
  gate "Vite does not silently serve feature paths" 1
fi

# ── 3. Vitals happy path (clinician) ──────────────────────────────────
echo "[3/6] vitals workflow"
VITALS_PAYLOAD='{
  "source_type":"technician_entry","heart_rate_bpm":72,
  "blood_pressure_systolic":120,"blood_pressure_diastolic":78,
  "temperature_value":98.6,"temperature_unit":"F",
  "spo2_pct":99,"respiratory_rate_bpm":16,"weight_lb":170,"height_in":70
}'
V_BODY="$(curl -s -m 10 -o /tmp/phase63c.vitals_create.json -w '%{http_code}' \
  -X POST "$API/api/v1/encounters/1/vitals-workups" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d "$VITALS_PAYLOAD" || echo "000")"
WORKUP_ID="$("$PY" -c "
import json, sys
try:
    with open('/tmp/phase63c.vitals_create.json') as fh:
        d = json.load(fh)
    print(d.get('id') or '')
except Exception:
    pass
" 2>/dev/null)"
if [[ "$V_BODY" =~ ^(200|201)$ ]] && [[ -n "$WORKUP_ID" ]]; then
  gate "POST /api/v1/encounters/1/vitals-workups -> $V_BODY (id=$WORKUP_ID)" 1
else
  gate "POST /api/v1/encounters/1/vitals-workups" 0 "got $V_BODY; body=/tmp/phase63c.vitals_create.json"
fi
if [[ -n "$WORKUP_ID" ]]; then
  V_REV="$(curl -s -m 10 -o /tmp/phase63c.vitals_rev.json -w '%{http_code}' \
    -X POST "$API/api/v1/vitals-workups/$WORKUP_ID/review" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{}' || echo "000")"
  V_SIGN="$(curl -s -m 10 -o /tmp/phase63c.vitals_sign.json -w '%{http_code}' \
    -X POST "$API/api/v1/vitals-workups/$WORKUP_ID/sign" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{"attested":true}' || echo "000")"
  [[ "$V_REV" =~ ^(200|201)$ ]] && gate "vitals review -> $V_REV" 1 || gate "vitals review" 0 "got $V_REV"
  [[ "$V_SIGN" =~ ^(200|201)$ ]] && gate "vitals sign -> $V_SIGN" 1 || gate "vitals sign" 0 "got $V_SIGN"
fi

# ── 4. VisitDraft happy path ──────────────────────────────────────────
echo "[4/6] visitdraft workflow"
SES_PAYLOAD='{"encounter_id":1,"fake_data_context":true,"transcript_text":"Demo transcript only. Patient reports blurry vision OD x 2 weeks."}'
S_BODY="$(curl -s -m 10 -o /tmp/phase63c.scribe_create.json -w '%{http_code}' \
  -X POST "$API/patients/1/scribe-sessions" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d "$SES_PAYLOAD" || echo "000")"
SESSION_ID="$("$PY" -c "
import json
try:
    with open('/tmp/phase63c.scribe_create.json') as fh:
        d = json.load(fh)
    print(d.get('id') or '')
except Exception:
    pass
" 2>/dev/null)"
if [[ "$S_BODY" =~ ^(200|201)$ ]] && [[ -n "$SESSION_ID" ]]; then
  gate "POST /patients/1/scribe-sessions -> $S_BODY (id=$SESSION_ID)" 1
else
  gate "POST /patients/1/scribe-sessions" 0 "got $S_BODY; body=/tmp/phase63c.scribe_create.json"
fi
if [[ -n "$SESSION_ID" ]]; then
  S_DRAFT="$(curl -s -m 15 -o /tmp/phase63c.scribe_draft.json -w '%{http_code}' \
    -X POST "$API/patients/1/scribe-sessions/$SESSION_ID/draft-ambient" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{"fake_data_context":true}' || echo "000")"
  S_REV="$(curl -s -m 10 -o /tmp/phase63c.scribe_rev.json -w '%{http_code}' \
    -X POST "$API/patients/1/scribe-sessions/$SESSION_ID/review" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{}' || echo "000")"
  S_FIN="$(curl -s -m 10 -o /tmp/phase63c.scribe_fin.json -w '%{http_code}' \
    -X POST "$API/patients/1/scribe-sessions/$SESSION_ID/finalize" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{"attested":true}' || echo "000")"
  [[ "$S_DRAFT" =~ ^(200|201)$ ]] && gate "visitdraft draft-ambient -> $S_DRAFT" 1 || gate "visitdraft draft-ambient" 0 "got $S_DRAFT"
  [[ "$S_REV" =~ ^(200|201)$ ]] && gate "visitdraft review -> $S_REV" 1 || gate "visitdraft review" 0 "got $S_REV"
  [[ "$S_FIN" =~ ^(200|201)$ ]] && gate "visitdraft finalize -> $S_FIN" 1 || gate "visitdraft finalize" 0 "got $S_FIN"
fi

# ── 5. Fundus happy path ──────────────────────────────────────────────
echo "[5/6] fundus workflow"
F_GEN_PAYLOAD='{"findings_text":"horseshoe tear at 10:30 OD","laterality":"OD","fake_data_context":true}'
F_GEN="$(curl -s -m 15 -o /tmp/phase63c.fundus_gen.json -w '%{http_code}' \
  -X POST "$API/api/v1/encounters/1/fundus-charts/generate" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d "$F_GEN_PAYLOAD" || echo "000")"
CHART_ID="$("$PY" -c "
import json
try:
    with open('/tmp/phase63c.fundus_gen.json') as fh:
        d = json.load(fh)
    print(d.get('chart_id') or d.get('id') or '')
except Exception:
    pass
" 2>/dev/null)"
if [[ "$F_GEN" =~ ^(200|201)$ ]] && [[ -n "$CHART_ID" ]]; then
  gate "POST /api/v1/encounters/1/fundus-charts/generate -> $F_GEN (chart_id=$CHART_ID)" 1
else
  gate "POST /api/v1/encounters/1/fundus-charts/generate" 0 "got $F_GEN; body=/tmp/phase63c.fundus_gen.json"
fi
if [[ -n "$CHART_ID" ]]; then
  F_REV="$(curl -s -m 10 -o /tmp/phase63c.fundus_rev.json -w '%{http_code}' \
    -X POST "$API/api/v1/fundus-charts/$CHART_ID/review" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{}' || echo "000")"
  F_SIGN="$(curl -s -m 10 -o /tmp/phase63c.fundus_sign.json -w '%{http_code}' \
    -X POST "$API/api/v1/fundus-charts/$CHART_ID/sign" \
    -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
    -d '{"attested":true}' || echo "000")"
  [[ "$F_REV" =~ ^(200|201)$ ]] && gate "fundus review -> $F_REV" 1 || gate "fundus review" 0 "got $F_REV"
  [[ "$F_SIGN" =~ ^(200|201)$ ]] && gate "fundus sign -> $F_SIGN" 1 || gate "fundus sign" 0 "got $F_SIGN"
fi

# ── 6. manual_note payload shape ──────────────────────────────────────
echo "[6/6] manual_note payload shape"
# String payload must be rejected with 400 invalid_event_data.
M_STR="$(curl -s -m 10 -o /tmp/phase63c.manual_str.json -w '%{http_code}' \
  -X POST "$API/encounters/1/events" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d '{"event_type":"manual_note","event_data":"hello"}' || echo "000")"
[[ "$M_STR" == "400" ]] && gate "manual_note string -> 400 (rejected)" 1 || gate "manual_note string -> 400" 0 "got $M_STR"
# Object payload must be accepted.
M_OBJ="$(curl -s -m 10 -o /tmp/phase63c.manual_obj.json -w '%{http_code}' \
  -X POST "$API/encounters/1/events" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d '{"event_type":"manual_note","event_data":{"note":"smoke ok"}}' || echo "000")"
[[ "$M_OBJ" =~ ^(200|201)$ ]] && gate "manual_note object -> $M_OBJ (accepted)" 1 || gate "manual_note object -> 201" 0 "got $M_OBJ"

# ── summary ──────────────────────────────────────────────────────────
echo
echo "Phase 63C functional smoke: $PASS pass / $FAIL fail"
if [[ "$FAIL" -gt 0 ]]; then
  echo "FAILURES:" >&2
  for f in "${FAILURES[@]}"; do echo "  - $f" >&2; done
  echo
  echo "BUYER-DEMO FUNCTIONAL GO: NO" >&2
  exit 1
fi
echo "BUYER-DEMO FUNCTIONAL GO: YES"
exit 0
