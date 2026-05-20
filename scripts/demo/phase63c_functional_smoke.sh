#!/usr/bin/env bash
# Phase 63C functional buyer-demo smoke (Phase 63C-1 enhanced).
#
# Replaces the Phase 63A media-presence gate with a live HTTP smoke
# that exercises the actual buyer-demo workflows end-to-end:
#   - DB at Alembic head
#   - required demo tables exist
#   - seeded clinician + Morgan encounter look correct (Phase 63C-1)
#   - API + frontend health
#   - Vitals create/review/sign happy path (clinician)
#   - VisitDraft create/draft/review/finalize happy path (clinician)
#   - Fundus generate/review/sign happy path (clinician)
#   - feature paths land on the real API, not the Vite origin
#   - manual_note payload shape is enforced (string rejected, object
#     accepted)
#
# Phase 63C-1 enhancements:
#   - failure bodies are echoed to stderr (not just /tmp)
#   - pre-flight DB introspection surfaces seeded clinician /
#     Morgan encounter / table state before any POST
#   - --reset flag runs `scripts/reset_demo_state.sh` first to
#     recover from accumulated state contamination
#   - explicit recovery hints on every FAIL line
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

RESET_FIRST=0
for arg in "$@"; do
  case "$arg" in
    --reset|--reset-first)
      RESET_FIRST=1
      ;;
    --help|-h)
      echo "Usage: $0 [--reset]"
      echo "  --reset   Run scripts/reset_demo_state.sh first to wipe"
      echo "            the local dev DB to a clean Morgan-only seed."
      exit 0
      ;;
    *)
      echo "WARN: ignoring unknown flag: $arg" >&2
      ;;
  esac
done

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

dump_failure_body() {
  local label="$1"
  local file="$2"
  if [[ -s "$file" ]]; then
    echo "      ↳ $label body:" >&2
    head -c 1200 "$file" >&2
    echo >&2
    echo >&2
  fi
}

echo "Phase 63C functional buyer-demo smoke (63C-1)"
echo "  repo=$REPO"
echo "  api=$API  web=$WEB  identity=$CLINICIAN"
echo "  reset_first=$RESET_FIRST"
echo

# ── 0. Optional reset (Phase 63C-1) ──────────────────────────────────
if [[ "$RESET_FIRST" == "1" ]]; then
  echo "[0/7] running scripts/reset_demo_state.sh (clean slate)"
  if [[ ! -x scripts/reset_demo_state.sh ]] && [[ ! -f scripts/reset_demo_state.sh ]]; then
    gate "scripts/reset_demo_state.sh exists" 0 "missing"
  else
    if bash scripts/reset_demo_state.sh >/tmp/phase63c.reset.log 2>&1; then
      gate "demo state reset" 1
    else
      gate "demo state reset" 0 "see /tmp/phase63c.reset.log"
      head -c 600 /tmp/phase63c.reset.log >&2 || true
    fi
  fi
fi

# ── 1. DB at Alembic head + required tables present ──────────────────
echo "[1/7] DB migration state"
HEAD_REV="$(cd apps/api && "$PY" -m alembic heads 2>/dev/null | head -1 | awk '{print $1}')" || HEAD_REV=""
CUR_REV="$(cd apps/api && "$PY" -m alembic current 2>/dev/null | head -1 | awk '{print $1}')" || CUR_REV=""
if [[ -n "$HEAD_REV" ]] && [[ "$CUR_REV" == "$HEAD_REV" ]]; then
  gate "db at Alembic head ($HEAD_REV)" 1
else
  gate "db at Alembic head" 0 "current=$CUR_REV head=$HEAD_REV — run './start-api.sh' (auto-migrates) or 'bash scripts/reset_demo_state.sh'"
fi
TABLES_OK=1
TABLES_DETAIL=""
for tbl in work_queue_items visit_vitals_workups fundus_charts imaging_studies scribe_sessions security_audit_events users encounters patients organizations; do
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
gate "required tables present" "$TABLES_OK" "$TABLES_DETAIL"

# ── 2. Seeded clinician + Morgan encounter introspection (63C-1) ─────
echo "[2/7] seeded clinician + encounter introspection"
SEED_REPORT="$("$PY" - <<PY 2>/dev/null
import sqlite3, json
con = sqlite3.connect('apps/api/chartnav.db')
out = {}
try:
    row = con.execute("SELECT id, email, role, organization_id, is_active FROM users WHERE email=?", ("$CLINICIAN",)).fetchone()
    out['clinician'] = row
except Exception as e:
    out['clinician_error'] = str(e)
try:
    row = con.execute("SELECT id, organization_id, patient_identifier, patient_name, status FROM encounters WHERE id=1").fetchone()
    out['encounter_1'] = row
except Exception as e:
    out['encounter_1_error'] = str(e)
try:
    out['encounter_count'] = con.execute("SELECT COUNT(*) FROM encounters").fetchone()[0]
except Exception as e:
    out['encounter_count_error'] = str(e)
print(json.dumps(out, default=str))
PY
)"
echo "  seeded state: $SEED_REPORT"
CLIN_OK="$("$PY" -c "
import json, sys
d = json.loads('''$SEED_REPORT''') if '''$SEED_REPORT''' else {}
clin = d.get('clinician')
if not clin: sys.exit(1)
_, email, role, org_id, is_active = clin
if email != '$CLINICIAN': sys.exit(2)
if role not in ('clinician','admin','technician'): sys.exit(3)
if not is_active: sys.exit(4)
if org_id != 1: sys.exit(5)
sys.exit(0)
" 2>/dev/null; echo $?)"
case "$CLIN_OK" in
  0) gate "seeded clinician $CLINICIAN exists in org 1 with valid role" 1 ;;
  1) gate "seeded clinician exists" 0 "no row for $CLINICIAN — run 'bash scripts/reset_demo_state.sh' or rerun './start-api.sh' which seeds idempotently" ;;
  2) gate "seeded clinician email matches" 0 "row exists but email mismatch" ;;
  3) gate "seeded clinician has write role" 0 "role not clinician/admin/technician" ;;
  4) gate "seeded clinician is active" 0 "is_active=0" ;;
  5) gate "seeded clinician in org 1" 0 "organization_id != 1 — Morgan is in org 1; cross-org access would 404" ;;
  *) gate "seeded clinician introspection" 0 "introspection error" ;;
esac
ENC_OK="$("$PY" -c "
import json, sys
d = json.loads('''$SEED_REPORT''') if '''$SEED_REPORT''' else {}
enc = d.get('encounter_1')
if not enc: sys.exit(1)
_, org_id, pid_str, _, _ = enc
if org_id != 1: sys.exit(2)
if pid_str != 'PT-1001': sys.exit(3)
sys.exit(0)
" 2>/dev/null; echo $?)"
case "$ENC_OK" in
  0) gate "encounter 1 is PT-1001 (Morgan Lee) in org 1" 1 ;;
  1) gate "encounter 1 exists" 0 "no encounter 1 — runbook must name the actual seeded record or you should reset" ;;
  2) gate "encounter 1 in org 1" 0 ;;
  3) gate "encounter 1 is PT-1001" 0 "encounter 1 is not Morgan — narration in docs/demo/phase-62-end-to-end-demo-visit-script.md assumes Morgan; reset with 'bash scripts/reset_demo_state.sh'" ;;
  *) gate "encounter introspection" 0 "introspection error" ;;
esac

# ── 3. API + frontend health ──────────────────────────────────────────
echo "[3/7] api + frontend health"
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

VITE_404="$(curl -s -m 3 -o /tmp/phase63c.viteprobe.txt -w '%{http_code}' \
  -H "Accept: application/json" "$WEB/api/v1/encounters/1/vitals-workups" || echo "000")"
if [[ "$VITE_404" == "200" ]] && head -c 60 /tmp/phase63c.viteprobe.txt 2>/dev/null | grep -qi '<!doctype'; then
  gate "feature paths NOT proxied through Vite (or proxy unintentional)" 0 \
    "Vite served HTML for /api/v1/...; feature clients calling relative URLs would mis-route"
else
  gate "Vite does not silently serve feature paths" 1
fi

# ── 4. Vitals happy path (clinician) ──────────────────────────────────
echo "[4/7] vitals workflow"
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
  gate "POST /api/v1/encounters/1/vitals-workups" 0 "got $V_BODY; recovery: rerun with './phase63c_functional_smoke.sh --reset' or 'bash scripts/reset_demo_state.sh'"
  dump_failure_body "vitals_create" /tmp/phase63c.vitals_create.json
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
  if [[ "$V_REV" =~ ^(200|201)$ ]]; then gate "vitals review -> $V_REV" 1; else gate "vitals review" 0 "got $V_REV"; dump_failure_body "vitals_review" /tmp/phase63c.vitals_rev.json; fi
  if [[ "$V_SIGN" =~ ^(200|201)$ ]]; then gate "vitals sign -> $V_SIGN" 1; else gate "vitals sign" 0 "got $V_SIGN"; dump_failure_body "vitals_sign" /tmp/phase63c.vitals_sign.json; fi
fi

# ── 5. VisitDraft happy path ──────────────────────────────────────────
echo "[5/7] visitdraft workflow"
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
  gate "POST /patients/1/scribe-sessions" 0 "got $S_BODY"
  dump_failure_body "scribe_create" /tmp/phase63c.scribe_create.json
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
  if [[ "$S_DRAFT" =~ ^(200|201)$ ]]; then gate "visitdraft draft-ambient -> $S_DRAFT" 1; else gate "visitdraft draft-ambient" 0 "got $S_DRAFT"; dump_failure_body "scribe_draft" /tmp/phase63c.scribe_draft.json; fi
  if [[ "$S_REV" =~ ^(200|201)$ ]]; then gate "visitdraft review -> $S_REV" 1; else gate "visitdraft review" 0 "got $S_REV"; dump_failure_body "scribe_review" /tmp/phase63c.scribe_rev.json; fi
  if [[ "$S_FIN" =~ ^(200|201)$ ]]; then gate "visitdraft finalize -> $S_FIN" 1; else gate "visitdraft finalize" 0 "got $S_FIN"; dump_failure_body "scribe_finalize" /tmp/phase63c.scribe_fin.json; fi
fi

# ── 6. Fundus happy path ──────────────────────────────────────────────
echo "[6/7] fundus workflow"
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
  gate "POST /api/v1/encounters/1/fundus-charts/generate" 0 "got $F_GEN"
  dump_failure_body "fundus_generate" /tmp/phase63c.fundus_gen.json
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
  if [[ "$F_REV" =~ ^(200|201)$ ]]; then gate "fundus review -> $F_REV" 1; else gate "fundus review" 0 "got $F_REV"; dump_failure_body "fundus_review" /tmp/phase63c.fundus_rev.json; fi
  if [[ "$F_SIGN" =~ ^(200|201)$ ]]; then gate "fundus sign -> $F_SIGN" 1; else gate "fundus sign" 0 "got $F_SIGN"; dump_failure_body "fundus_sign" /tmp/phase63c.fundus_sign.json; fi
fi

# ── 7. manual_note payload shape ──────────────────────────────────────
echo "[7/7] manual_note payload shape"
M_STR="$(curl -s -m 10 -o /tmp/phase63c.manual_str.json -w '%{http_code}' \
  -X POST "$API/encounters/1/events" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d '{"event_type":"manual_note","event_data":"hello"}' || echo "000")"
if [[ "$M_STR" == "400" ]]; then gate "manual_note string -> 400 (rejected)" 1; else gate "manual_note string -> 400" 0 "got $M_STR (backend should reject string)"; dump_failure_body "manual_note_string" /tmp/phase63c.manual_str.json; fi
M_OBJ="$(curl -s -m 10 -o /tmp/phase63c.manual_obj.json -w '%{http_code}' \
  -X POST "$API/encounters/1/events" \
  -H "Content-Type: application/json" -H "X-User-Email: $CLINICIAN" \
  -d '{"event_type":"manual_note","event_data":{"note":"smoke ok"}}' || echo "000")"
if [[ "$M_OBJ" =~ ^(200|201)$ ]]; then gate "manual_note object -> $M_OBJ (accepted)" 1; else gate "manual_note object -> 201" 0 "got $M_OBJ"; dump_failure_body "manual_note_object" /tmp/phase63c.manual_obj.json; fi

# ── summary ──────────────────────────────────────────────────────────
echo
echo "Phase 63C functional smoke: $PASS pass / $FAIL fail"
if [[ "$FAIL" -gt 0 ]]; then
  echo "FAILURES:" >&2
  for f in "${FAILURES[@]}"; do echo "  - $f" >&2; done
  echo >&2
  echo "Recovery suggestions:" >&2
  echo "  1. Rerun with --reset to wipe the dev DB to a clean Morgan-only seed:" >&2
  echo "       bash scripts/demo/phase63c_functional_smoke.sh --reset" >&2
  echo "  2. Ensure the API was started via the bundle wrapper so 'make migrate seed' ran:" >&2
  echo "       cd \$HOME/Desktop/ChartNav-Buyer-Demo-Build && ./start-api.sh" >&2
  echo "  3. If specific 5xx persist, paste the body lines above into the chat for diagnosis." >&2
  echo "  4. Inspect API logs (foreground terminal or artifacts/phase-62/dry-runs/*/api.log)." >&2
  echo
  echo "BUYER-DEMO FUNCTIONAL GO: NO" >&2
  exit 1
fi
echo "BUYER-DEMO FUNCTIONAL GO: YES"
exit 0
