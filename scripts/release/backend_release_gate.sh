#!/usr/bin/env bash
# scripts/release/backend_release_gate.sh — Phase 88 backend release
# evidence gate.
#
# WHY THIS EXISTS
#   The independent Manus audit observed that running the full
#   `pytest` suite on a release candidate hangs intermittently and
#   tangles migration-heavy paths with fast deterministic paths.
#   This script provides a deterministic, tiered, fail-fast view of
#   the backend test surface so release evidence is a single command
#   that does not hang and prints PASS/FAIL plus runtime.
#
# WHAT IT DOES
#   Runs three deterministic backend tiers in order, stopping at the
#   first failure:
#
#     Tier 1: deterministic security + RBAC + org isolation tests
#             (fast; uses isolated SQLite; matches the CI backend job
#             surface).
#     Tier 2: clinical surface unit + integration tests
#             (Phase 76 - Phase 87 + Phase 21B imaging pipeline +
#             Phase 84-86 cross-phase integrations).
#     Tier 3: clinical-spine + workflow regression tests
#             (Phase 1 spine: vitals workup, scribe sessions, fundus,
#             retina visit summary / packet).
#
#   Each tier has a real timeout enforced by pytest's `--timeout` if
#   `pytest-timeout` is available; otherwise the GNU `timeout` binary
#   is used. No tier may exceed 25 minutes. The script exits non-zero
#   on the first failure; later tiers are skipped.
#
# WHAT IT DOES NOT DO
#   - It does NOT run evals/, end-to-end LLM tests, or live STT.
#   - It does NOT require secrets.
#   - It does NOT process real PHI.
#   - It does NOT deploy.
#   - It does NOT skip safety scanners (those are in the parent
#     release-evidence gate).
#   - It does NOT mark any failing test as xfail.
#
# USAGE
#   bash scripts/release/backend_release_gate.sh
#   bash scripts/release/backend_release_gate.sh --tier=1
#   bash scripts/release/backend_release_gate.sh --pytest-args="-x"
#
# OUTPUT
#   Section headers, total runtime, exit 0 on full pass.
#
# Non-zero exit on:
#   - any tier failure
#   - any tier exceeding its timeout

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

REQUESTED_TIER="all"
EXTRA_PYTEST_ARGS=""
for arg in "$@"; do
  case "$arg" in
    --tier=*) REQUESTED_TIER="${arg#--tier=}" ;;
    --pytest-args=*) EXTRA_PYTEST_ARGS="${arg#--pytest-args=}" ;;
    *) echo "[backend_release_gate] unknown arg: $arg" >&2; exit 64 ;;
  esac
done

# Tier definitions. Each tier is a list of test files (relative to
# apps/api/). The lists are intentionally explicit — globbing would
# accidentally pull in slow eval / LLM / live-stack tests.
TIER1=(
  "tests/test_auth.py"
  "tests/test_auth_modes.py"
  "tests/test_rbac.py"
  "tests/test_scoping.py"
  "tests/test_admin.py"
  "tests/test_ai_security.py"
  "tests/test_runtime_safety.py"
  "tests/test_observability.py"
  "tests/test_operational.py"
)

TIER2=(
  "tests/test_phase_21b_imaging_pipeline.py"
  "tests/test_anti_vegf_injections.py"
  "tests/test_glaucoma_summary.py"
  "tests/test_cataract_workflow.py"
  "tests/test_disease_staging.py"
  "tests/test_disease_staging_integrations.py"
  "tests/test_medications.py"
  "tests/test_medications_integrations.py"
  "tests/test_workspace_profiles.py"
  "tests/test_workspace_profiles_integrations.py"
  "tests/test_provider_action_queue.py"
  "tests/test_note_validation.py"
  "tests/test_note_validation_acknowledgements.py"
  "tests/test_fhir_export.py"
)

TIER3=(
  "tests/test_vitals_workup.py"
  "tests/test_scribe_sessions.py"
  "tests/test_fundus_charts.py"
  "tests/test_fundus_charts_phase56.py"
  "tests/test_fundus_llm_guardrails.py"
  "tests/test_retina_visit_summary.py"
  "tests/test_retina_visit_packet.py"
  "tests/test_end_to_end_clinical_workflow.py"
)

cd "$REPO_ROOT/apps/api"

# Pick the pytest binary. Prefer the .venv if present so the operator
# does not accidentally pick up a system python missing test deps.
if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

# Detect pytest-timeout. Fall back to GNU `timeout` if not present.
HAS_PYTEST_TIMEOUT=0
if "$PYTHON" -c "import pytest_timeout" 2>/dev/null; then
  HAS_PYTEST_TIMEOUT=1
fi

# Per-tier wall-clock budget (seconds). Generous enough for migration
# bootstrapping on a cold CI runner but small enough to fail loudly
# if something is hung.
TIER_BUDGET_SECONDS="${PHASE88_TIER_BUDGET_SECONDS:-1500}"

run_tier() {
  local label="$1"
  shift
  local files=("$@")
  if [[ "${#files[@]}" -eq 0 ]]; then
    echo "[backend_release_gate] tier $label is empty (skipped)" >&2
    return 0
  fi

  echo
  echo "================================================================"
  echo "Tier $label  ·  ${#files[@]} test file(s)  ·  budget ${TIER_BUDGET_SECONDS}s"
  echo "================================================================"

  local tier_start
  tier_start="$(date +%s)"

  local pytest_cmd
  if [[ "$HAS_PYTEST_TIMEOUT" -eq 1 ]]; then
    pytest_cmd=(
      "$PYTHON" -m pytest -q
      "--timeout=${TIER_BUDGET_SECONDS}"
      "--timeout-method=thread"
    )
  else
    pytest_cmd=(
      timeout "${TIER_BUDGET_SECONDS}" "$PYTHON" -m pytest -q
    )
  fi
  if [[ -n "$EXTRA_PYTEST_ARGS" ]]; then
    # shellcheck disable=SC2206
    pytest_cmd+=( $EXTRA_PYTEST_ARGS )
  fi
  pytest_cmd+=( "${files[@]}" )

  if ! "${pytest_cmd[@]}"; then
    local tier_end
    tier_end="$(date +%s)"
    echo
    echo "[backend_release_gate] FAIL  Tier $label  ·  $((tier_end - tier_start))s elapsed" >&2
    echo "[backend_release_gate] Recovery: re-run with --tier=$label --pytest-args='-x -v' to localize the failing test." >&2
    return 1
  fi

  local tier_end
  tier_end="$(date +%s)"
  echo
  echo "[backend_release_gate] PASS  Tier $label  ·  $((tier_end - tier_start))s elapsed"
}

started_at="$(date +%s)"

case "$REQUESTED_TIER" in
  1)
    run_tier 1 "${TIER1[@]}"
    ;;
  2)
    run_tier 2 "${TIER2[@]}"
    ;;
  3)
    run_tier 3 "${TIER3[@]}"
    ;;
  all)
    run_tier 1 "${TIER1[@]}"
    run_tier 2 "${TIER2[@]}"
    run_tier 3 "${TIER3[@]}"
    ;;
  *)
    echo "[backend_release_gate] unknown tier: $REQUESTED_TIER" >&2
    exit 64
    ;;
esac

ended_at="$(date +%s)"
total=$((ended_at - started_at))

echo
echo "================================================================"
echo "backend_release_gate  ·  PASS  ·  total runtime ${total}s"
echo "================================================================"
