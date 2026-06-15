#!/usr/bin/env bash
# scripts/release/phase100_controlled_pilot_launch_gate.sh — Phase 100
# final controlled-pilot launch gate.
#
# WHY THIS EXISTS
#   Phase 91 + Phase 92 + Phase 93 closed the platform's clinical
#   intelligence + release hardening + pilot launch readiness
#   programs. Phase 100 is the final operator command that produces
#   one dated artifact bundle the ops lead attaches to the launch
#   GO/NO-GO form
#   (docs/pilot/phase-100-controlled-pilot-launch-gate.md).
#
# WHAT IT DOES
#   Runs the following checks in order. Each writes its full
#   stdout+stderr to its own log file under the dated artifact
#   directory. The gate exits non-zero on the first REQUIRED failure
#   but continues through OPTIONAL checks so the operator gets the
#   most complete artifact set on a single run.
#
#   REQUIRED checks (exit non-zero on failure):
#     R1  Phase 93 pilot launch gate (delegates to the Phase 88
#         release evidence gate; covers backend tiered release gate,
#         frontend typecheck, vitest, all five claim scanners,
#         runtime safety, git diff --check, and claim policy
#         fixtures)
#     R2  Phase 100 doc inventory (verifies the Phase 100 docs exist)
#     R3  Phase 93 doc inventory (verifies the Phase 93 docs exist —
#         Phase 100 depends on them)
#
#   OPTIONAL checks (logged, not fail-blocking):
#     O1  Phase 63C functional smoke (only if local stack reachable
#         AND PHASE63C_API_URL / PHASE63C_WEB_URL answer)
#
# WHAT IT DOES NOT DO
#   - It does NOT require secrets.
#   - It does NOT process real PHI.
#   - It does NOT run any production / live LLM / live watsonx job.
#   - It does NOT publish.
#   - It does NOT deploy.
#   - It does NOT mutate any buyer or pilot environment.
#   - It does NOT approve real PHI on its own.
#   - It does NOT instantiate the launch GO/NO-GO form — that is a
#     signed paper / PDF document and is recorded out-of-repo.
#
# USAGE
#   bash scripts/release/phase100_controlled_pilot_launch_gate.sh
#   bash scripts/release/phase100_controlled_pilot_launch_gate.sh --skip-backend
#   bash scripts/release/phase100_controlled_pilot_launch_gate.sh --skip-web
#   bash scripts/release/phase100_controlled_pilot_launch_gate.sh --no-vitest
#
# OUTPUT
#   artifacts/phase-100-controlled-pilot-launch/YYYYMMDD-HHMMSS/
#     ├── summary.txt                       overall PASS/FAIL + per-check status
#     ├── go-no-go.txt                      one-line decision recommendation
#     ├── 01-phase93-pilot-launch-gate.log  full output of Phase 93 gate
#     ├── 02-doc-inventory-phase100.log     Phase 100 doc presence
#     ├── 03-doc-inventory-phase93.log      Phase 93 doc presence (dependency)
#     ├── O1-phase63c-smoke.log             (optional)
#     ├── phase-93-pilot-launch/            symlink/copy of latest Phase 93 bundle
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
    *) echo "[phase100-gate] unknown arg: $arg" >&2; exit 64 ;;
  esac
done

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="$REPO_ROOT/artifacts/phase-100-controlled-pilot-launch/$TIMESTAMP"
mkdir -p "$OUT_DIR"

SUMMARY="$OUT_DIR/summary.txt"
GO_NO_GO="$OUT_DIR/go-no-go.txt"
META="$OUT_DIR/metadata.txt"

git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
git_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

{
  echo "ChartNav Phase 100 controlled pilot launch gate"
  echo "captured_at: ${TIMESTAMP}Z"
  echo "host: $(hostname)"
  echo "operator: ${USER:-unknown}"
  echo "repo_sha: ${git_sha}"
  echo "branch: ${git_branch}"
  echo "skip_backend: ${SKIP_BACKEND}"
  echo "skip_web: ${SKIP_WEB}"
  echo "skip_vitest: ${SKIP_VITEST}"
} > "$META"

echo "ChartNav Phase 100 controlled pilot launch gate — ${TIMESTAMP}Z" > "$SUMMARY"
echo "branch=${git_branch}  sha=${git_sha}" >> "$SUMMARY"
echo >> "$SUMMARY"

declare -i overall_status=0
declare -i required_failed=0

run_check() {
  local id="$1"; shift
  local label="$1"; shift
  local required="$1"; shift
  local log_file="$1"; shift
  local recovery="$1"; shift
  [[ "$1" == "--" ]] || { echo "[phase100-gate] bad run_check args" >&2; return 2; }
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
# REQUIRED — delegate to the Phase 93 pilot launch gate
# -----------------------------------------------------------------

phase93_args=()
[[ "$SKIP_BACKEND" -eq 1 ]] && phase93_args+=( "--skip-backend" )
[[ "$SKIP_WEB"     -eq 1 ]] && phase93_args+=( "--skip-web" )
[[ "$SKIP_VITEST"  -eq 1 ]] && phase93_args+=( "--no-vitest" )

run_check "R1" "Phase 93 pilot launch gate (delegated)" 1 \
  "01-phase93-pilot-launch-gate.log" \
  "open artifacts/phase-93-pilot-launch/<latest>/summary.txt for the per-check breakdown" \
  -- bash "$REPO_ROOT/scripts/release/phase93_pilot_launch_gate.sh" "${phase93_args[@]}"

# Snapshot the Phase 93 artifact dir into the Phase 100 bundle so the
# Phase 100 deliverable is self-contained.
latest_phase93_dir=""
if [[ -d "$REPO_ROOT/artifacts/phase-93-pilot-launch" ]]; then
  latest_phase93_dir="$(ls -1dt "$REPO_ROOT"/artifacts/phase-93-pilot-launch/*/ 2>/dev/null | head -n1 | sed 's:/$::')"
fi
if [[ -n "$latest_phase93_dir" && -d "$latest_phase93_dir" ]]; then
  ln -s "$latest_phase93_dir" "$OUT_DIR/phase-93-pilot-launch" 2>/dev/null \
    || cp -r "$latest_phase93_dir" "$OUT_DIR/phase-93-pilot-launch"
  echo "phase93_pilot_launch_dir: $latest_phase93_dir" >> "$META"
fi

# -----------------------------------------------------------------
# REQUIRED — Phase 100 doc inventory
# -----------------------------------------------------------------

check_phase100_docs() {
  local repo_root="$1"
  local missing=0
  local docs=(
    "docs/pilot/phase-100-controlled-pilot-launch-gate.md"
    "docs/pilot/phase-100-final-pilot-evidence-index.md"
    "docs/security/phase-100-no-real-phi-attestation.md"
    "docs/demo/phase-100-controlled-pilot-buyer-demo-script.md"
    "docs/build/phase-100-controlled-pilot-launch-status.md"
  )
  for d in "${docs[@]}"; do
    if [[ -s "$repo_root/$d" ]]; then
      echo "OK   $d"
    else
      echo "MISS $d"
      missing=1
    fi
  done
  return $missing
}

run_check "R2" "Phase 100 doc inventory" 1 \
  "02-doc-inventory-phase100.log" \
  "create the missing Phase 100 doc before re-running the gate" \
  -- bash -c "$(declare -f check_phase100_docs); check_phase100_docs \"$REPO_ROOT\""

# -----------------------------------------------------------------
# REQUIRED — Phase 93 doc inventory (Phase 100 depends on them)
# -----------------------------------------------------------------

check_phase93_docs() {
  local repo_root="$1"
  local missing=0
  local docs=(
    "docs/pilot/phase-93-pilot-dry-run-runbook.md"
    "docs/pilot/phase-93-end-to-end-validation-checklist.md"
    "docs/pilot/phase-93-controlled-pilot-launch-go-no-go.md"
    "docs/security/phase-93-real-phi-readiness-review.md"
    "docs/build/phase-93-pilot-launch-readiness-status.md"
  )
  for d in "${docs[@]}"; do
    if [[ -s "$repo_root/$d" ]]; then
      echo "OK   $d"
    else
      echo "MISS $d"
      missing=1
    fi
  done
  return $missing
}

run_check "R3" "Phase 93 doc inventory (dependency)" 1 \
  "03-doc-inventory-phase93.log" \
  "restore the missing Phase 93 doc from main before launching" \
  -- bash -c "$(declare -f check_phase93_docs); check_phase93_docs \"$REPO_ROOT\""

# -----------------------------------------------------------------
# OPTIONAL — Phase 63C functional smoke (only if local stack up)
# -----------------------------------------------------------------

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

if [[ "$phase63c_reachable" -eq 1 && -x "$REPO_ROOT/scripts/demo/phase63c_functional_smoke.sh" ]]; then
  run_check "O1" "Phase 63C functional smoke (local stack reachable)" 0 \
    "O1-phase63c-smoke.log" \
    "rerun with --verbose to localize the failing step" \
    -- env PHASE63C_API_URL="$phase63c_api" PHASE63C_WEB_URL="$phase63c_web" \
       bash "$REPO_ROOT/scripts/demo/phase63c_functional_smoke.sh" --reset
else
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "O1" "SKIP" "Phase 63C functional smoke" "-" \
    "no local stack reachable (PHASE63C_API_URL/WEB_URL not set or unreachable)" >> "$SUMMARY"
fi

# -----------------------------------------------------------------
# Summary + go/no-go recommendation
# -----------------------------------------------------------------

echo >> "$SUMMARY"
if [[ "$overall_status" -eq 0 ]]; then
  echo "OVERALL: PASS  (every required check passed)" >> "$SUMMARY"
  cat > "$GO_NO_GO" <<EOF
ChartNav Phase 100 controlled pilot launch gate
captured_at: ${TIMESTAMP}Z
branch: ${git_branch}
sha: ${git_sha}

RECOMMENDATION: CONDITIONAL GO

Every required Phase 100 release-side gate passed on this SHA. The
operator may proceed with the controlled pilot launch GO/NO-GO
sign-off form (docs/pilot/phase-100-controlled-pilot-launch-gate.md)
once the practice's clinical, security (Scope B), administrative,
and ARCG commercial owners countersign.

This recommendation is RELEASE-SIDE ONLY. It does NOT approve real
PHI. Real PHI requires every gate in
docs/security/phase-93-real-phi-readiness-review.md,
docs/security/phase-100-no-real-phi-attestation.md,
and docs/pilot/chartnav-controlled-pilot-go-live-checklist.md to
close with written evidence.

Artifact dir: $OUT_DIR
EOF
else
  echo "OVERALL: FAIL  (${required_failed} required check(s) failed)" >> "$SUMMARY"
  cat > "$GO_NO_GO" <<EOF
ChartNav Phase 100 controlled pilot launch gate
captured_at: ${TIMESTAMP}Z
branch: ${git_branch}
sha: ${git_sha}

RECOMMENDATION: NO-GO

${required_failed} required Phase 100 release-side gate(s) failed
on this SHA. The controlled pilot launch GO/NO-GO form cannot be
signed until every failing check is remediated. Open
$SUMMARY for the per-check breakdown and the recovery hint per
failing row.

Artifact dir: $OUT_DIR
EOF
fi
echo "artifact_dir: $OUT_DIR" >> "$SUMMARY"

echo
echo "================================================================"
cat "$SUMMARY"
echo "----------------------------------------------------------------"
cat "$GO_NO_GO"
echo "================================================================"
echo

if [[ "$overall_status" -ne 0 ]]; then
  echo "[phase100-gate] FAIL  see $SUMMARY" >&2
  exit 1
fi

echo "[phase100-gate] PASS  artifact: $OUT_DIR"
