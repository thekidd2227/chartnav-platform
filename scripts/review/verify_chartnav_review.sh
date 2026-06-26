#!/usr/bin/env bash
# Verify the running ChartNav review environment end to end. Read-only except
# for creating one synthetic eye-diagram (in the disposable review DB).
# Exits non-zero on the first hard failure. No live external services.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "$HERE/docker-compose.yml")
WEB="http://localhost:5173"
API="http://localhost:8000"
ADMIN_A="admin@chartnav.local"      # org: demo-eye-clinic
ADMIN_B="admin@northside.local"     # org: northside-retina
REV_A="rev@chartnav.local"

pass=0 fail=0
ok()  { pass=$((pass+1)); echo "  ✅ $1"; }
bad() { fail=$((fail+1)); echo "  ❌ $1"; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
jget() { curl -s -H "X-User-Email: $1" "$API$2"; }

echo "── ChartNav review verification ──"

# 1. Frontend + API health
[ "$(code "$WEB")" = "200" ] && ok "frontend 200 ($WEB)" || bad "frontend not 200 ($(code "$WEB"))"
[ "$(code "$API/healthz")" = "200" ] && ok "API /healthz 200" || bad "API /healthz not 200"
[ "$(code "$API/readyz")" = "200" ] && ok "API /readyz 200 (db reachable)" || bad "API /readyz not 200"

# 2. DB revision == Alembic head (query the running api container; the
#    migrate container is a one-shot that has already exited).
HEAD_REV="$("${COMPOSE[@]}" exec -T api alembic heads 2>/dev/null | awk '/^[0-9a-f]/{print $1; exit}')"
CUR_REV="$("${COMPOSE[@]}" exec -T api alembic current 2>/dev/null | awk '/^[0-9a-f]/{print $1; exit}')"
[ -n "$HEAD_REV" ] && [ "$HEAD_REV" = "$CUR_REV" ] && ok "DB at Alembic head ($CUR_REV)" || bad "DB revision '$CUR_REV' != head '$HEAD_REV'"

# 3. Synthetic org + demo users + patient list
PATIENTS="$(jget "$ADMIN_A" /patients)"
echo "$PATIENTS" | grep -q "PT-1001" && ok "patient list loads (PT-1001 present)" || bad "patient list missing PT-1001"
PID="$(echo "$PATIENTS" | python3 -c "import sys,json;print(next(p['id'] for p in json.load(sys.stdin) if p['patient_identifier']=='PT-1001'))" 2>/dev/null)"
[ -n "$PID" ] && ok "resolved PT-1001 numeric id ($PID)" || bad "could not resolve PT-1001 id"

# 4. Patient chart opens + numeric patient_id (drives the Open chart link)
[ -n "$PID" ] && [ "$(code -H "X-User-Email: $ADMIN_A" "$API/patients/$PID")" = "200" ] && ok "patient chart opens (GET /patients/$PID)" || bad "patient detail not 200"
ENC="$(jget "$ADMIN_A" /encounters)"
echo "$ENC" | python3 -c "import sys,json; d=json.load(sys.stdin); assert any(isinstance(e.get('patient_id'),int) for e in d)" 2>/dev/null \
  && ok "encounter exposes numeric patient_id (Open chart link will render)" || bad "no numeric patient_id on encounters"

# 5. Eye diagram save + reload with drawing_json (object, not string)
CREATED="$(curl -s -H "X-User-Email: $ADMIN_A" -H 'Content-Type: application/json' \
  -d '{"title":"Review OD","findings_text":"synthetic","drawing_json":{"strokes":[{"path":"M0 0 L5 5"}]}}' \
  "$API/patients/$PID/eye-diagrams")"
AID="$(echo "$CREATED" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)"
echo "$CREATED" | python3 -c "import sys,json; b=json.load(sys.stdin); assert isinstance(b['drawing_json'],dict) and b['version_number']==1 and b['is_signed'] is False" 2>/dev/null \
  && ok "eye diagram saved with drawing_json object" || bad "eye diagram create/shape failed"
if [ -n "$AID" ]; then
  jget "$ADMIN_A" "/patients/$PID/eye-diagrams/$AID" | python3 -c "import sys,json; b=json.load(sys.stdin); assert isinstance(b['drawing_json'],dict)" 2>/dev/null \
    && ok "eye diagram reloads with drawing_json object" || bad "eye diagram reload failed"
fi

# 6. Fundus charts reachable (encounter-scoped: /encounters/{id}/fundus-charts)
EID="$(echo "$ENC" | python3 -c "import sys,json;d=json.load(sys.stdin);print(next((e['id'] for e in d if isinstance(e.get('patient_id'),int)),''))" 2>/dev/null)"
if [ -n "$EID" ]; then
  # Fundus router is mounted under the /api/v1 prefix (unlike the root-mounted
  # patient/eye-diagram routers).
  [ "$(code -H "X-User-Email: $ADMIN_A" "$API/api/v1/encounters/$EID/fundus-charts")" = "200" ] \
    && ok "fundus charts endpoint 200 (/api/v1/encounters/$EID/fundus-charts)" \
    || bad "fundus charts list non-200"
else
  bad "no encounter id to probe fundus charts"
fi

# 7. Cross-tenant isolation: org-B user must NOT see org-A patient → 404
XC="$(code -H "X-User-Email: $ADMIN_B" "$API/patients/$PID")"
[ "$XC" = "404" ] && ok "cross-tenant access denied with non-disclosing 404" || bad "cross-tenant returned $XC (expected 404)"

# 8. Role enforcement: reviewer cannot create an eye diagram → 403
RC="$(code -H "X-User-Email: $REV_A" -H 'Content-Type: application/json' -d '{"title":"x"}' "$API/patients/$PID/eye-diagrams")"
[ "$RC" = "403" ] && ok "reviewer write denied (403)" || bad "reviewer create returned $RC (expected 403)"

# 9. Audit events written (security_audit_events)
AUDITN="$("${COMPOSE[@]}" exec -T db psql -U chartnav -d chartnav -tAc "select count(*) from security_audit_events" 2>/dev/null | tr -d '[:space:]')"
[ -n "$AUDITN" ] && [ "$AUDITN" -gt 0 ] 2>/dev/null && ok "audit events written ($AUDITN rows)" || bad "no audit events found"

# 10. Object storage stays private (MinIO bucket not anonymously listable)
MC="$(code "http://localhost:9000/chartnav-review-objects/")"
[ "$MC" = "403" ] || [ "$MC" = "404" ] && ok "object store not public (HTTP $MC)" || echo "  ⚠️ object store returned $MC"

echo "── verify: $pass passed, $fail failed ──"
[ "$fail" -eq 0 ]
