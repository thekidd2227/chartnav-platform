#!/usr/bin/env bash
# scripts/demo/phase63a_count_media.sh
# ────────────────────────────────────
# Authoritative GO/NO-GO gate for Phase 63A automated media capture.
#
# - Verifies every required screenshot (30) and video (12) by filename.
# - Videos accept .mov / .webm / .mp4 — same scene number / base name.
# - Prints exactly which files are missing.
# - Exits 0 on GO, 1 on NO-GO.
# - No placeholders accepted: only real files in the right directory count.

set -uo pipefail

REPO_ROOT="${CHARTNAV_REPO_PATH:-$HOME/Desktop/ARCG/chartnav-platform}"
SHOT_DIR="${REPO_ROOT}/artifacts/phase-62/screenshots"
VID_DIR="${REPO_ROOT}/artifacts/phase-62/video-clips"

REQUIRED_SHOTS=(
  "01_workspace_landing.png"
  "02_patient_header.png"
  "03_tab_navigation.png"
  "04_vitals_empty_form.png"
  "05_vitals_loaded.png"
  "06_vitals_bmi.png"
  "07_vitals_partial_bp_warning.png"
  "08_vitals_what_chartnav_did_not_do.png"
  "09_vitals_review.png"
  "10_vitals_signed_lock.png"
  "11_visitdraft_empty.png"
  "12_visitdraft_transcript.png"
  "13_visitdraft_structured_facts.png"
  "14_visitdraft_draft_note.png"
  "15_visitdraft_safety_flags.png"
  "16_visitdraft_what_chartnav_did_not_do.png"
  "17_visitdraft_reviewed.png"
  "18_visitdraft_signed_lock.png"
  "19_fundus_empty.png"
  "20_fundus_findings.png"
  "21_fundus_svg.png"
  "22_fundus_legend.png"
  "23_fundus_warning.png"
  "24_fundus_attestation.png"
  "25_fundus_signed_lock.png"
  "26_runtime_safety_terminal.png"
  "27_claim_scanners_terminal.png"
  "28_alembic_safety_terminal.png"
  "29_release_evidence_checklist.png"
  "30_product_truth_safety_statements.png"
)

# Video base names (without extension). Any of .mov | .webm | .mp4 satisfies.
REQUIRED_VIDEO_BASES=(
  "01_workspace_orientation"
  "02_vitals_intake"
  "03_vitals_bmi_warning"
  "04_vitals_review_sign_lock"
  "05_visitdraft_transcript_to_draft"
  "06_visitdraft_safety_did_not_do"
  "07_visitdraft_review_sign_lock"
  "08_fundus_findings_to_diagram"
  "09_fundus_warning"
  "10_fundus_review_sign_lock"
  "11_safety_terminal"
  "12_highlight_reel_3min"
)

echo "=== Phase 63A — media count ==="
echo "Repo:   ${REPO_ROOT}"
echo "Shots:  ${SHOT_DIR}"
echo "Videos: ${VID_DIR}"
echo

# ── Screenshots ───────────────────────────────────────────────────────────
shot_ok=0
shot_missing=()
echo "--- Screenshots (30 required) ---"
for f in "${REQUIRED_SHOTS[@]}"; do
  p="${SHOT_DIR}/${f}"
  if [[ -s "${p}" ]]; then
    printf "  [OK]      %s (%s bytes)\n" "${f}" "$(stat -f%z "${p}" 2>/dev/null || stat -c%s "${p}")"
    shot_ok=$((shot_ok + 1))
  else
    printf "  [MISSING] %s\n" "${f}"
    shot_missing+=("${f}")
  fi
done
echo
echo "Screenshots present: ${shot_ok} / ${#REQUIRED_SHOTS[@]}"
echo

# ── Videos ─────────────────────────────────────────────────────────────────
vid_ok=0
vid_missing=()
echo "--- Videos (12 required, .mov/.webm/.mp4 accepted) ---"
for base in "${REQUIRED_VIDEO_BASES[@]}"; do
  found=""
  for ext in mov webm mp4; do
    p="${VID_DIR}/${base}.${ext}"
    if [[ -s "${p}" ]]; then
      found="${p}"
      break
    fi
  done
  if [[ -n "${found}" ]]; then
    printf "  [OK]      %s (%s bytes)\n" "$(basename "${found}")" "$(stat -f%z "${found}" 2>/dev/null || stat -c%s "${found}")"
    vid_ok=$((vid_ok + 1))
  else
    printf "  [MISSING] %s.{mov|webm|mp4}\n" "${base}"
    vid_missing+=("${base}")
  fi
done
echo
echo "Videos present: ${vid_ok} / ${#REQUIRED_VIDEO_BASES[@]}"
echo

# ── Verdict ────────────────────────────────────────────────────────────────
if (( shot_ok == ${#REQUIRED_SHOTS[@]} )) && (( vid_ok == ${#REQUIRED_VIDEO_BASES[@]} )); then
  echo "OVERALL: GO — all required media present."
  exit 0
fi

echo "OVERALL: NO-GO"
if (( ${#shot_missing[@]} > 0 )); then
  echo "Missing screenshots:"
  for f in "${shot_missing[@]}"; do echo "  - ${f}"; done
fi
if (( ${#vid_missing[@]} > 0 )); then
  echo "Missing videos:"
  for b in "${vid_missing[@]}"; do echo "  - ${b}.{mov|webm|mp4}"; done
fi
exit 1
