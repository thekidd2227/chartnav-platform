#!/usr/bin/env bash
# scripts/demo/phase101_mcp_independent_demo_capture.sh — Phase 101
# MCP-independent buyer-demo evidence capture.
#
# WHY THIS EXISTS
#   The previous local environment reported that MCP Filesystem and
#   Kapture Browser Automation could not attach. Buyer-demo evidence
#   capture must remain possible without those servers. This script
#   uses only repo-native shell + the Playwright runtime that already
#   ships in apps/web/node_modules, falling back cleanly when no
#   local stack is reachable.
#
# WHAT IT DOES
#   Runs the following stages in order. Each writes its log under
#   the dated artifact directory.
#
#   REQUIRED stages (exit non-zero on failure):
#     R1  Phase 100 controlled-pilot launch gate (delegates Phase 93
#         → Phase 88; covers backend tiered release gate, frontend
#         typecheck, vitest, all five claim scanners, runtime
#         safety, git diff --check, and claim policy fixtures)
#
#   OPTIONAL stages (logged; skipped cleanly when prerequisites
#   aren't met):
#     O1  Phase 63C functional smoke (only if PHASE63C_API_URL +
#         PHASE63C_WEB_URL are set AND the URLs answer)
#     O2  Playwright Phase 63A demo media capture (only if
#         apps/web/node_modules ships @playwright/test AND the local
#         stack is reachable AND the existing capture script exists)
#     O3  Existing screenshot / video artifact collection from
#         artifacts/phase-62/ into the buyer-demo dir (only if the
#         source dirs exist and contain captured media)
#
# WHAT IT DOES NOT DO
#   - It does NOT require secrets.
#   - It does NOT process real PHI.
#   - It does NOT run any production / live LLM / live watsonx job.
#   - It does NOT publish.
#   - It does NOT deploy.
#   - It does NOT mutate any buyer or pilot environment.
#   - It does NOT rely on MCP Filesystem.
#   - It does NOT rely on Kapture Browser Automation.
#
# USAGE
#   bash scripts/demo/phase101_mcp_independent_demo_capture.sh
#   bash scripts/demo/phase101_mcp_independent_demo_capture.sh --skip-backend
#   bash scripts/demo/phase101_mcp_independent_demo_capture.sh --skip-web
#   bash scripts/demo/phase101_mcp_independent_demo_capture.sh --no-vitest
#
# OUTPUT
#   artifacts/buyer-demo/YYYYMMDD-HHMMSS/
#     ├── summary.txt
#     ├── no-real-phi-attestation.txt
#     ├── missing-evidence.txt
#     ├── 01-phase100-launch-gate.log
#     ├── O1-phase63c-smoke.log         (optional)
#     ├── O2-playwright-capture.log     (optional)
#     ├── O3-existing-media-collect.log (optional)
#     ├── phase-100-controlled-pilot-launch/ (symlink/copy)
#     ├── screenshots/                  (optional, populated from O2/O3)
#     ├── videos/                       (optional, populated from O2/O3)
#     ├── manual-screenshots/           (always; for operator to drop into)
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
    *) echo "[phase101-capture] unknown arg: $arg" >&2; exit 64 ;;
  esac
done

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="$REPO_ROOT/artifacts/buyer-demo/$TIMESTAMP"
mkdir -p "$OUT_DIR" "$OUT_DIR/manual-screenshots"

SUMMARY="$OUT_DIR/summary.txt"
META="$OUT_DIR/metadata.txt"
ATTESTATION="$OUT_DIR/no-real-phi-attestation.txt"
MISSING="$OUT_DIR/missing-evidence.txt"

git_sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
git_branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

{
  echo "ChartNav Phase 101 buyer-demo evidence capture"
  echo "captured_at: ${TIMESTAMP}Z"
  echo "host: $(hostname)"
  echo "operator: ${USER:-unknown}"
  echo "repo_sha: ${git_sha}"
  echo "branch: ${git_branch}"
  echo "skip_backend: ${SKIP_BACKEND}"
  echo "skip_web: ${SKIP_WEB}"
  echo "skip_vitest: ${SKIP_VITEST}"
  echo "phase63c_api_url: ${PHASE63C_API_URL:-<unset>}"
  echo "phase63c_web_url: ${PHASE63C_WEB_URL:-<unset>}"
} > "$META"

echo "ChartNav Phase 101 buyer-demo evidence capture — ${TIMESTAMP}Z" > "$SUMMARY"
echo "branch=${git_branch}  sha=${git_sha}" >> "$SUMMARY"
echo >> "$SUMMARY"

# Initialize missing-evidence + attestation files immediately so the
# operator always has them even on early failure.
{
  echo "Missing-evidence ledger — ${TIMESTAMP}Z"
  echo "branch=${git_branch}  sha=${git_sha}"
  echo
  echo "This file lists evidence rows the capture script could NOT"
  echo "machine-collect on this run. The operator may capture them"
  echo "manually and drop the files under manual-screenshots/ before"
  echo "handing the dated artifact dir to a buyer."
  echo
} > "$MISSING"

cat > "$ATTESTATION" <<EOF
ChartNav Phase 101 buyer-demo evidence capture
captured_at: ${TIMESTAMP}Z
branch: ${git_branch}
sha: ${git_sha}

NO-REAL-PHI ATTESTATION

Every artifact in this dated dir was produced against synthetic
seed data only. ChartNav does not process real PHI in this build.
The Phase 100 controlled-pilot launch gate (R1 below) PASS is a
release-side technical readiness signal only; it does NOT approve
real PHI.

Real PHI requires every gate in
docs/security/phase-93-real-phi-readiness-review.md,
docs/security/phase-100-no-real-phi-attestation.md, and
docs/pilot/chartnav-controlled-pilot-go-live-checklist.md to
close with written, dated, attributable evidence.

ChartNav remains:
  - NOT HIPAA-certified, SOC 2-certified, HITRUST-certified, or
    FDA-cleared.
  - NOT a certified electronic health record.
  - NOT a replacement for the practice's existing EHR.
  - NOT a surface that diagnoses, recommends treatment, recommends
    surgery, recommends medication changes, recommends IOL choices,
    or interprets fundus / OCT / VF / any imaging modality.
  - NOT a surface that places orders, sends referrals, bills,
    codes, submits claims, or messages patients.
  - NOT enabled with a production LLM in this build.

These non-claims survive every go-live and are enforced by the
safety-scanner suite and the runtime safety scanner on every
release.
EOF

declare -i overall_status=0
declare -i required_failed=0

run_stage() {
  local id="$1"; shift
  local label="$1"; shift
  local required="$1"; shift
  local log_file="$1"; shift
  local recovery="$1"; shift
  [[ "$1" == "--" ]] || { echo "[phase101-capture] bad run_stage args" >&2; return 2; }
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
    else
      echo "  - ${id} ${label}: optional FAIL (see $log_file)" >> "$MISSING"
    fi
  fi
}

skip_stage() {
  local id="$1"
  local label="$2"
  local reason="$3"
  printf '%-4s %-7s %-50s %5s  reason=%s\n' \
    "$id" "SKIP" "$label" "-" "$reason" >> "$SUMMARY"
  echo "  - ${id} ${label}: SKIPPED — ${reason}" >> "$MISSING"
}

# -----------------------------------------------------------------
# R1 — Phase 100 controlled-pilot launch gate (REQUIRED)
# -----------------------------------------------------------------

phase100_args=()
[[ "$SKIP_BACKEND" -eq 1 ]] && phase100_args+=( "--skip-backend" )
[[ "$SKIP_WEB"     -eq 1 ]] && phase100_args+=( "--skip-web" )
[[ "$SKIP_VITEST"  -eq 1 ]] && phase100_args+=( "--no-vitest" )

run_stage "R1" "Phase 100 controlled-pilot launch gate" 1 \
  "01-phase100-launch-gate.log" \
  "open artifacts/phase-100-controlled-pilot-launch/<latest>/summary.txt for the per-check breakdown" \
  -- bash "$REPO_ROOT/scripts/release/phase100_controlled_pilot_launch_gate.sh" "${phase100_args[@]}"

# Snapshot the Phase 100 artifact dir we just produced so the
# Phase 101 buyer-demo bundle is self-contained.
latest_phase100_dir=""
if [[ -d "$REPO_ROOT/artifacts/phase-100-controlled-pilot-launch" ]]; then
  latest_phase100_dir="$(ls -1dt "$REPO_ROOT"/artifacts/phase-100-controlled-pilot-launch/*/ 2>/dev/null | head -n1 | sed 's:/$::')"
fi
if [[ -n "$latest_phase100_dir" && -d "$latest_phase100_dir" ]]; then
  ln -s "$latest_phase100_dir" "$OUT_DIR/phase-100-controlled-pilot-launch" 2>/dev/null \
    || cp -r "$latest_phase100_dir" "$OUT_DIR/phase-100-controlled-pilot-launch"
  echo "phase100_launch_dir: $latest_phase100_dir" >> "$META"
fi

# -----------------------------------------------------------------
# O1 — Phase 63C functional smoke (OPTIONAL)
# -----------------------------------------------------------------

phase63c_api="${PHASE63C_API_URL:-}"
phase63c_web="${PHASE63C_WEB_URL:-}"
phase63c_reachable=0
if [[ -n "$phase63c_api" && -n "$phase63c_web" ]] \
   && command -v curl >/dev/null 2>&1; then
  if curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "${phase63c_api%/}/healthz" 2>/dev/null | grep -q '^[23]' \
     || curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "${phase63c_api%/}/health" 2>/dev/null | grep -q '^[23]'; then
    if curl -sS --max-time 2 -o /dev/null -w '%{http_code}' "$phase63c_web" 2>/dev/null | grep -q '^[2345]'; then
      phase63c_reachable=1
    fi
  fi
fi

if [[ "$phase63c_reachable" -eq 1 && -x "$REPO_ROOT/scripts/demo/phase63c_functional_smoke.sh" ]]; then
  run_stage "O1" "Phase 63C functional smoke" 0 \
    "O1-phase63c-smoke.log" \
    "rerun with --verbose to localize the failing step" \
    -- env PHASE63C_API_URL="$phase63c_api" PHASE63C_WEB_URL="$phase63c_web" \
       bash "$REPO_ROOT/scripts/demo/phase63c_functional_smoke.sh" --reset
else
  skip_stage "O1" "Phase 63C functional smoke" \
    "PHASE63C_API_URL/WEB_URL not set or unreachable (local stack required)"
fi

# -----------------------------------------------------------------
# O2 — Playwright Phase 63A demo media capture (OPTIONAL)
# -----------------------------------------------------------------

playwright_ready=0
playwright_capture_script="$REPO_ROOT/scripts/demo/phase63a_capture_demo_media.mjs"
if [[ -f "$REPO_ROOT/apps/web/node_modules/@playwright/test/package.json" ]] \
   && [[ -f "$playwright_capture_script" ]] \
   && [[ "$phase63c_reachable" -eq 1 ]]; then
  playwright_ready=1
fi

if [[ "$playwright_ready" -eq 1 ]]; then
  run_stage "O2" "Playwright demo media capture" 0 \
    "O2-playwright-capture.log" \
    "rerun: npx playwright install --with-deps chromium; then re-run capture" \
    -- bash -c "cd '$REPO_ROOT' && node '$playwright_capture_script'"
else
  reason=""
  if [[ ! -f "$REPO_ROOT/apps/web/node_modules/@playwright/test/package.json" ]]; then
    reason="@playwright/test not installed (cd apps/web && npm ci)"
  elif [[ ! -f "$playwright_capture_script" ]]; then
    reason="capture script missing at $playwright_capture_script"
  else
    reason="local stack not reachable (PHASE63C_API_URL/WEB_URL must answer)"
  fi
  skip_stage "O2" "Playwright demo media capture" "$reason"
fi

# -----------------------------------------------------------------
# O3 — Collect any existing media into the buyer-demo dir
# -----------------------------------------------------------------

collect_existing_media() {
  local copied=0
  local screens_src="$REPO_ROOT/artifacts/phase-62/screenshots"
  local videos_src="$REPO_ROOT/artifacts/phase-62/video-clips"
  local screens_dst="$OUT_DIR/screenshots"
  local videos_dst="$OUT_DIR/videos"
  if [[ -d "$screens_src" ]] && ls "$screens_src"/*.png >/dev/null 2>&1; then
    mkdir -p "$screens_dst"
    cp "$screens_src"/*.png "$screens_dst"/ 2>/dev/null && copied=1
    echo "copied screenshots from $screens_src"
  fi
  if [[ -d "$videos_src" ]] && ls "$videos_src"/*.{webm,mp4,mov} >/dev/null 2>&1; then
    mkdir -p "$videos_dst"
    cp "$videos_src"/*.{webm,mp4,mov} "$videos_dst"/ 2>/dev/null && copied=1
    echo "copied videos from $videos_src"
  fi
  if [[ "$copied" -eq 0 ]]; then
    echo "no existing media found under artifacts/phase-62/"
    return 1
  fi
  return 0
}

run_stage "O3" "Collect existing Phase 62 media" 0 \
  "O3-existing-media-collect.log" \
  "run Playwright capture (O2) first to populate artifacts/phase-62/" \
  -- bash -c "$(declare -f collect_existing_media); collect_existing_media"

# -----------------------------------------------------------------
# Summary
# -----------------------------------------------------------------

echo >> "$SUMMARY"
if [[ "$overall_status" -eq 0 ]]; then
  echo "OVERALL: PASS  (every required stage passed)" >> "$SUMMARY"
  echo "BUYER-DEMO RECOMMENDATION: CONDITIONAL GO" >> "$SUMMARY"
else
  echo "OVERALL: FAIL  (${required_failed} required stage(s) failed)" >> "$SUMMARY"
  echo "BUYER-DEMO RECOMMENDATION: NO-GO" >> "$SUMMARY"
fi
echo "artifact_dir: $OUT_DIR" >> "$SUMMARY"

# Append optional-stage status footer to missing-evidence so the
# operator sees the full ledger in one file.
{
  echo
  echo "See summary.txt for the per-stage table; see"
  echo "no-real-phi-attestation.txt for the boundary statement;"
  echo "drop manual captures into manual-screenshots/ before"
  echo "handing this dir to a buyer."
} >> "$MISSING"

echo
echo "================================================================"
cat "$SUMMARY"
echo "================================================================"
echo

if [[ "$overall_status" -ne 0 ]]; then
  echo "[phase101-capture] FAIL  see $SUMMARY" >&2
  exit 1
fi

echo "[phase101-capture] PASS  artifact: $OUT_DIR"
