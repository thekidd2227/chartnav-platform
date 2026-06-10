#!/usr/bin/env bash
# scripts/release/chartnav_release_evidence_gate.sh — Phase 88 single
# operator command that produces dated release evidence.
#
# WHY THIS EXISTS
#   The independent Manus audit observed that ChartNav's release
#   evidence is scattered across many ad-hoc commands and that no
#   single command writes a dated log directory the operator can
#   attach to a pilot ticket. This script is that command.
#
# WHAT IT DOES
#   Runs the following checks in order. Each check writes its full
#   stdout+stderr to its own file under the dated artifact directory.
#   The gate exits non-zero on the first REQUIRED failure but
#   continues through OPTIONAL checks so the operator gets the most
#   complete possible artifact set on a single run.
#
#   REQUIRED checks (exit non-zero on failure):
#     R1  backend release gate (tiered pytest)
#     R2  frontend typecheck (tsc --noEmit)
#     R3  frontend vitest (full suite)
#     R4  commercial claims scanner
#     R5  website claims scanner
#     R6  demo claims scanner
#     R7  pilot readiness scanner
#     R8  runtime safety scanner
#     R9  git diff --check
#     R10 claim policy fixture scan
#
#   OPTIONAL checks (logged, not fail-blocking):
#     O1  Phase 63C functional smoke (only if local stack reachable)
#     O2  alembic safety scan
#
# WHAT IT DOES NOT DO
#   - It does NOT require secrets.
#   - It does NOT process real PHI.
#   - It does NOT run any production / live LLM / live watsonx job.
#   - It does NOT publish.
#   - It does NOT deploy.
#   - It does NOT mutate the live site, the live FHIR endpoint, or any
#     buyer/pilot environment.
#
# USAGE
#   bash scripts/release/chartnav_release_evidence_gate.sh
#   bash scripts/release/chartnav_release_evidence_gate.sh --skip-backend
#   bash scripts/release/chartnav_release_evidence_gate.sh --skip-web
#   bash scripts/release/chartnav_release_evidence_gate.sh --no-vitest
#
# OUTPUT
#   artifacts/release-evidence/YYYYMMDD-HHMMSS/
#     ├── summary.txt           overall PASS/FAIL + per-check status
#     ├── 01-backend.log
#     ├── 02-tsc.log
#     ├── 03-vitest.log
#     ├── 04-commercial-claims.log
#     ├── 05-website-claims.log
#     ├── 06-demo-claims.log
#     ├── 07-pilot-readiness.log
#     ├── 08-runtime-safety.log
#     ├── 09-git-diff-check.log
#     ├── 10-claim-policy-fixtures.log
#     ├── O1-phase63c-smoke.log    (optional)
#     ├── O2-alembic-safety.log    (optional)
#     └── metadata.txt

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SKIP_BACKEND=0
SKIP_WEB=0
SKIP_VITEST=0
for arg in "$@"; do
  case "$arg" in
    --skip-backend) SKIP_BACKEND=1 ;;
    --skip-web)     SKIP_WEB=1 ;;
    --no-vitest)    SKIP_VITEST=1 ;;
    *) echo "[release-gate] unknown arg: $arg" >&2; exit 64 ;;
  esac
done

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="$REPO_ROOT/artifacts/release-evidence/$TIMESTAMP"
mkdir -p "$OUT_DIR"

SUMMARY="$OUT_DIR/summary.txt"
META="$OUT_DIR/metadata.txt"

git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
git_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

{
  echo "ChartNav release evidence gate"
  echo "captured_at: ${TIMESTAMP}Z"
  echo "host: $(hostname)"
  echo "operator: ${USER:-unknown}"
  echo "repo_sha: ${git_sha}"
  echo "branch: ${git_branch}"
  echo "skip_backend: ${SKIP_BACKEND}"
  echo "skip_web: ${SKIP_WEB}"
  echo "skip_vitest: ${SKIP_VITEST}"
} > "$META"

# Per-check status table accumulated into summary.txt.
echo "ChartNav release evidence gate — ${TIMESTAMP}Z" > "$SUMMARY"
echo "branch=${git_branch}  sha=${git_sha}" >> "$SUMMARY"
echo >> "$SUMMARY"

declare -i overall_status=0
declare -i required_failed=0

run_check() {
  # run_check <id> <label> <required:0|1> <log_file> <recovery_hint> -- <cmd...>
  local id="$1"; shift
  local label="$1"; shift
  local required="$1"; shift
  local log_file="$1"; shift
  local recovery="$1"; shift
  [[ "$1" == "--" ]] || { echo "[release-gate] bad run_check args" >&2; return 2; }
  shift

  echo
  echo "----------------------------------------------------------------"
  echo "[${id}] ${label}"
  echo "----------------------------------------------------------------"
  local start_ts
  start_ts="$(date +%s)"

  set +e
  ( "$@" ) > "$OUT_DIR/$log_file" 2>&1
  local rc=$?
  set -e

  local end_ts
  end_ts="$(date +%s)"
  local elapsed=$((end_ts - start_ts))

  if [[ $rc -eq 0 ]]; then
    echo "[${id}] PASS  ${elapsed}s"
    printf '%-4s %-7s %-50s %5ds  log=%s\n' \
      "$id" "PASS" "$label" "$elapsed" "$log_file" >> "$SUMMARY"
  else
    echo "[${id}] FAIL rc=${rc}  ${elapsed}s  log=$OUT_DIR/$log_file"
    printf '%-4s %-7s %-50s %5ds  log=%s  rc=%d\n' \
      "$id" "FAIL" "$label" "$elapsed" "$log_file" "$rc" >> "$SUMMARY"
    if [[ -n "$recovery" ]]; then
      echo "      recovery: $recovery"
      echo "        recovery: $recovery" >> "$SUMMARY"
    fi
    if [[ "$required" -eq 1 ]]; then
      overall_status=1
      required_failed=$((required_failed + 1))
    fi
  fi
}

# -----------------------------------------------------------------
# REQUIRED checks
# -----------------------------------------------------------------

if [[ "$SKIP_BACKEND" -eq 0 ]]; then
  run_check "R1" "backend release gate (tiered pytest)" 1 \
    "01-backend.log" \
    "bash scripts/release/backend_release_gate.sh --tier=1 --pytest-args='-x -v'" \
    -- bash "$REPO_ROOT/scripts/release/backend_release_gate.sh"
else
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "R1" "SKIP" "backend release gate" "-" "skipped by --skip-backend" >> "$SUMMARY"
fi

if [[ "$SKIP_WEB" -eq 0 ]]; then
  run_check "R2" "frontend typecheck (tsc --noEmit)" 1 \
    "02-tsc.log" \
    "cd apps/web && npx tsc --noEmit" \
    -- bash -c "cd '$REPO_ROOT/apps/web' && npx tsc --noEmit"
  if [[ "$SKIP_VITEST" -eq 0 ]]; then
    run_check "R3" "frontend vitest (full suite)" 1 \
      "03-vitest.log" \
      "cd apps/web && npx vitest run" \
      -- bash -c "cd '$REPO_ROOT/apps/web' && npx vitest run"
  else
    printf '%-4s %-7s %-50s %5s  reason=%s\n' \
      "R3" "SKIP" "frontend vitest" "-" "skipped by --no-vitest" >> "$SUMMARY"
  fi
else
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "R2" "SKIP" "frontend typecheck" "-" "skipped by --skip-web" >> "$SUMMARY"
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "R3" "SKIP" "frontend vitest" "-" "skipped by --skip-web" >> "$SUMMARY"
fi

run_check "R4" "commercial claims scanner" 1 \
  "04-commercial-claims.log" \
  "open the flagged doc, fix the phrase, re-run; see docs/website/chartnav-public-claims-drift-policy.md" \
  -- bash "$REPO_ROOT/scripts/check_commercial_claims.sh"

run_check "R5" "website claims scanner" 1 \
  "05-website-claims.log" \
  "open the flagged file, fix the phrase, re-run; see docs/website/chartnav-public-claims-drift-policy.md" \
  -- bash "$REPO_ROOT/scripts/check_website_claims.sh"

run_check "R6" "demo claims scanner" 1 \
  "06-demo-claims.log" \
  "open the flagged demo doc, fix the phrase, re-run" \
  -- bash "$REPO_ROOT/scripts/check_demo_claims.sh"

run_check "R7" "pilot readiness scanner" 1 \
  "07-pilot-readiness.log" \
  "open the flagged pilot doc, fix the phrase, re-run" \
  -- bash "$REPO_ROOT/scripts/check_pilot_readiness.sh"

run_check "R8" "runtime safety scanner" 1 \
  "08-runtime-safety.log" \
  "review the runtime safety combination flagged; see apps/api/app/services/" \
  -- python3 "$REPO_ROOT/scripts/check_runtime_safety.py"

run_check "R9" "git diff --check (whitespace/trailing)" 1 \
  "09-git-diff-check.log" \
  "fix whitespace in the flagged hunk(s)" \
  -- git -C "$REPO_ROOT" diff --check

run_check "R10" "claim policy fixture scan" 1 \
  "10-claim-policy-fixtures.log" \
  "review tests/claim_fixtures/ against scripts/check_*_claims.sh" \
  -- bash "$REPO_ROOT/scripts/test_claim_policy_fixtures.sh"

# -----------------------------------------------------------------
# OPTIONAL checks (logged, not fail-blocking)
# -----------------------------------------------------------------

# Phase 63C functional smoke — only runs if the operator has set the
# expected env vars OR if the local default ports answer.
phase63c_api="${PHASE63C_API_URL:-http://127.0.0.1:8765}"
phase63c_web="${PHASE63C_WEB_URL:-http://127.0.0.1:5173}"
phase63c_reachable=0
if command -v curl >/dev/null 2>&1; then
  if curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "${phase63c_api%/}/healthz" 2>/dev/null | grep -q '^[23]'; then
    if curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "$phase63c_web" 2>/dev/null | grep -q '^[2345]'; then
      phase63c_reachable=1
    fi
  fi
fi

if [[ "$phase63c_reachable" -eq 1 ]]; then
  run_check "O1" "Phase 63C functional smoke (local stack reachable)" 0 \
    "O1-phase63c-smoke.log" \
    "see scripts/demo/phase63c_functional_smoke.sh" \
    -- env PHASE63C_API_URL="$phase63c_api" PHASE63C_WEB_URL="$phase63c_web" \
       bash "$REPO_ROOT/scripts/demo/phase63c_functional_smoke.sh" --reset
else
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "O1" "SKIP" "Phase 63C functional smoke" "-" "no local stack reachable" >> "$SUMMARY"
fi

if [[ -x "$REPO_ROOT/scripts/check_alembic_safety.sh" ]]; then
  run_check "O2" "alembic migration safety scan" 0 \
    "O2-alembic-safety.log" \
    "see scripts/check_alembic_safety.sh output" \
    -- bash "$REPO_ROOT/scripts/check_alembic_safety.sh"
else
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "O2" "SKIP" "alembic safety scan" "-" "scripts/check_alembic_safety.sh missing" >> "$SUMMARY"
fi

# -----------------------------------------------------------------
# Summary
# -----------------------------------------------------------------

end_ts="$(date +%s)"
start_meta="$(grep -m1 captured_at "$META" | awk '{print $2}')"

echo >> "$SUMMARY"
if [[ "$overall_status" -eq 0 ]]; then
  echo "OVERALL: PASS  (every required check passed)" >> "$SUMMARY"
else
  echo "OVERALL: FAIL  (${required_failed} required check(s) failed)" >> "$SUMMARY"
fi
echo "artifact_dir: $OUT_DIR" >> "$SUMMARY"

echo
echo "================================================================"
cat "$SUMMARY"
echo "================================================================"
echo

if [[ "$overall_status" -ne 0 ]]; then
  echo "[release-gate] FAIL  see $SUMMARY" >&2
  exit 1
fi

echo "[release-gate] PASS  artifact: $OUT_DIR"
