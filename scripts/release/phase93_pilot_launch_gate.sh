#!/usr/bin/env bash
# scripts/release/phase93_pilot_launch_gate.sh — Phase 93 single
# operator command that produces dated pilot-launch evidence.
#
# WHY THIS EXISTS
#   Phase 91 (Unified Ophthalmology Workspace Engine) + Phase 92
#   (Advanced Clinical Intelligence Layer) closed the last clinical
#   intelligence workstreams on the Phase 2 roadmap. Phase 93
#   collapses the controlled-pilot launch readiness program into a
#   single operator command that writes one dated artifact bundle
#   the ops lead can attach to the launch GO/NO-GO form
#   (`docs/pilot/phase-93-controlled-pilot-launch-go-no-go.md`).
#
# WHAT IT DOES
#   Runs the following checks in order. Each writes its full
#   stdout+stderr to its own log file under the dated artifact
#   directory. The gate exits non-zero on the first REQUIRED failure
#   but continues through OPTIONAL checks so the operator gets the
#   most complete artifact set on a single run.
#
#   REQUIRED checks (exit non-zero on failure):
#     R1  Phase 88 release evidence gate (delegates the tiered
#         backend gate, frontend typecheck, vitest, claim scanners,
#         pilot readiness scanner, runtime safety, git diff --check,
#         and claim policy fixtures)
#
#   OPTIONAL checks (logged, not fail-blocking):
#     O1  Phase 63C functional smoke (only if local stack reachable
#         AND PHASE63C_API_URL / PHASE63C_WEB_URL are set)
#     O2  Phase 93 doc inventory (verifies the Phase 93 docs exist)
#     O3  Phase 91 + Phase 92 build doc presence (sanity sentinel)
#
# WHAT IT DOES NOT DO
#   - It does NOT require secrets.
#   - It does NOT process real PHI.
#   - It does NOT run any production / live LLM / live watsonx job.
#   - It does NOT publish.
#   - It does NOT deploy.
#   - It does NOT mutate any buyer or pilot environment.
#   - It does NOT approve real PHI on its own.
#
# USAGE
#   bash scripts/release/phase93_pilot_launch_gate.sh
#   bash scripts/release/phase93_pilot_launch_gate.sh --skip-backend
#   bash scripts/release/phase93_pilot_launch_gate.sh --skip-web
#   bash scripts/release/phase93_pilot_launch_gate.sh --no-vitest
#
# OUTPUT
#   artifacts/phase-93-pilot-launch/YYYYMMDD-HHMMSS/
#     ├── summary.txt                   overall PASS/FAIL + per-check status
#     ├── 01-release-evidence-gate.log  full output of Phase 88 gate
#     ├── O1-phase63c-smoke.log         (optional)
#     ├── O2-doc-inventory.log          (optional)
#     ├── O3-phase-91-92-doc-presence.log (optional)
#     ├── release-evidence/             symlink or copy of latest Phase 88 artifact dir
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
    *) echo "[phase93-gate] unknown arg: $arg" >&2; exit 64 ;;
  esac
done

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="$REPO_ROOT/artifacts/phase-93-pilot-launch/$TIMESTAMP"
mkdir -p "$OUT_DIR"

SUMMARY="$OUT_DIR/summary.txt"
META="$OUT_DIR/metadata.txt"

git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
git_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

{
  echo "ChartNav Phase 93 pilot launch gate"
  echo "captured_at: ${TIMESTAMP}Z"
  echo "host: $(hostname)"
  echo "operator: ${USER:-unknown}"
  echo "repo_sha: ${git_sha}"
  echo "branch: ${git_branch}"
  echo "skip_backend: ${SKIP_BACKEND}"
  echo "skip_web: ${SKIP_WEB}"
  echo "skip_vitest: ${SKIP_VITEST}"
} > "$META"

echo "ChartNav Phase 93 pilot launch gate — ${TIMESTAMP}Z" > "$SUMMARY"
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
  [[ "$1" == "--" ]] || { echo "[phase93-gate] bad run_check args" >&2; return 2; }
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
# REQUIRED — delegate to the Phase 88 release evidence gate
# -----------------------------------------------------------------

release_gate_args=()
[[ "$SKIP_BACKEND" -eq 1 ]] && release_gate_args+=( "--skip-backend" )
[[ "$SKIP_WEB"     -eq 1 ]] && release_gate_args+=( "--skip-web" )
[[ "$SKIP_VITEST"  -eq 1 ]] && release_gate_args+=( "--no-vitest" )

run_check "R1" "Phase 88 release evidence gate (delegated)" 1 \
  "01-release-evidence-gate.log" \
  "open artifacts/release-evidence/<latest>/summary.txt for the per-check breakdown" \
  -- bash "$REPO_ROOT/scripts/release/chartnav_release_evidence_gate.sh" "${release_gate_args[@]}"

# Snapshot the Phase 88 artifact dir we just produced so the
# Phase 93 bundle is self-contained.
latest_release_dir=""
if [[ -d "$REPO_ROOT/artifacts/release-evidence" ]]; then
  latest_release_dir="$(ls -1dt "$REPO_ROOT"/artifacts/release-evidence/*/ 2>/dev/null | head -n1 | sed 's:/$::')"
fi
if [[ -n "$latest_release_dir" && -d "$latest_release_dir" ]]; then
  ln -s "$latest_release_dir" "$OUT_DIR/release-evidence" 2>/dev/null \
    || cp -r "$latest_release_dir" "$OUT_DIR/release-evidence"
  echo "release_evidence_dir: $latest_release_dir" >> "$META"
fi

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
# OPTIONAL — Phase 93 doc inventory
# -----------------------------------------------------------------

check_doc_inventory() {
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

run_check "O2" "Phase 93 doc inventory" 0 \
  "O2-doc-inventory.log" \
  "create the missing Phase 93 doc before re-running the gate" \
  -- bash -c "$(declare -f check_doc_inventory); check_doc_inventory \"$REPO_ROOT\""

# -----------------------------------------------------------------
# OPTIONAL — Phase 91 + Phase 92 build doc sentinel
# -----------------------------------------------------------------

check_phase_91_92_docs() {
  local repo_root="$1"
  local missing=0
  for d in \
    "docs/build/phase-91-unified-workspace-engine.md" \
    "docs/build/phase-92-advanced-clinical-intelligence-layer.md"; do
    if [[ -s "$repo_root/$d" ]]; then
      echo "OK   $d"
    else
      echo "MISS $d"
      missing=1
    fi
  done
  return $missing
}

run_check "O3" "Phase 91 + Phase 92 build doc presence" 0 \
  "O3-phase-91-92-doc-presence.log" \
  "restore the missing build doc from main before launching" \
  -- bash -c "$(declare -f check_phase_91_92_docs); check_phase_91_92_docs \"$REPO_ROOT\""

# -----------------------------------------------------------------
# Summary
# -----------------------------------------------------------------

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
  echo "[phase93-gate] FAIL  see $SUMMARY" >&2
  exit 1
fi

echo "[phase93-gate] PASS  artifact: $OUT_DIR"
