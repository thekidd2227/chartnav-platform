#!/usr/bin/env bash
# scripts/check_live_site_claims.sh — Phase 24A live-site claims drift
# detector.
#
# Why this exists:
#   Manus's audit found ChartNav's repo passing every claims-check
#   while the live `chartnavmd.com` deployment carried overclaiming
#   language ("hands-free scribing", "replace your EHR", "chart fills
#   itself", "note writes itself", IBM/watsonx-powered, etc.). The
#   gap: existing scripts scan only repo-controlled docs/decks. They
#   cannot see what the externally-deployed live site actually says.
#
# What this script does:
#   1. Accepts a captured live-site HTML file (or directory of files)
#      as input.
#   2. Scans for the Phase 24A forbidden-positive-claim phrase list.
#   3. Negative-context guard: lines containing "does not", "do not",
#      "never", "not <forbidden>", "no <forbidden>" are exempted (we
#      WANT negative assertions; we ban positive claims).
#   4. Exits non-zero on any hit so CI / a pre-deploy hook can gate.
#
# What this script does NOT do:
#   - does not fetch the live site (the operator captures HTML
#     out-of-band with `curl > captured.html` or similar — this script
#     never touches the network and never prints secrets).
#   - does not modify the captured file.
#   - does not approve the live site for publication.
#
# Usage:
#   bash scripts/check_live_site_claims.sh path/to/captured.html
#   bash scripts/check_live_site_claims.sh path/to/captured_dir/
#
# Operator workflow (recommended cadence: pre-publish + weekly):
#   # 1. Capture the live site HTML out-of-band:
#   curl -sL https://chartnavmd.com/ -o /tmp/chartnavmd-live.html
#   # 2. Scan it:
#   bash scripts/check_live_site_claims.sh /tmp/chartnavmd-live.html
#   # 3. If any positive claim is found, the script exits non-zero;
#   #    DO NOT publish until the live copy is corrected.
#
# Exit codes:
#   0  pass — no positive-claim hits found
#   1  FAIL — at least one positive claim detected; live site is out
#      of compliance with the repo's safe-claims contract
#   2  invocation error (missing input file / no readable HTML)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INPUT="${1:-}"
if [ -z "$INPUT" ]; then
  cat <<EOF >&2
usage: bash scripts/check_live_site_claims.sh <path>
  <path> is either an HTML file or a directory containing HTML files
  that the operator captured from the live deployment.

This script never fetches the network. The operator must capture
the live HTML out-of-band first.
EOF
  exit 2
fi

if [ ! -e "$INPUT" ]; then
  echo "ERROR: input path does not exist: $INPUT" >&2
  exit 2
fi

# Build the file list.
if [ -f "$INPUT" ]; then
  FILES=("$INPUT")
elif [ -d "$INPUT" ]; then
  mapfile -t FILES < <(find "$INPUT" -type f \( -name "*.html" -o -name "*.htm" \))
  if [ "${#FILES[@]}" -eq 0 ]; then
    echo "ERROR: no .html / .htm files found under $INPUT" >&2
    exit 2
  fi
else
  echo "ERROR: input is neither a file nor a directory: $INPUT" >&2
  exit 2
fi

echo "ChartNav Phase 24A live-site claims check."
echo "Scanning ${#FILES[@]} file(s)."
echo

# ---------------------------------------------------------------
# Phase 24A forbidden-positive-claim phrases.
#
# Each entry is an extended regex. The negative-context guard below
# skips lines where the phrase appears in an explicit negative
# context ("does not", "do not", "never", "not <phrase>", etc.).
# ---------------------------------------------------------------
FORBIDDEN=(
  # Overclaiming positioning
  "hands[- ]free"
  "chart fills itself"
  "chart writes itself"
  "note fills itself"
  "note writes itself"
  "replace[s]? (your |an? )?(EHR|EMR|electronic health record|electronic medical record)"
  "EHR replacement"
  "EMR replacement"
  "replace[s]? (a |the )?doctor"
  "replace[s]? (a |the )?provider"
  "replace[s]? (your |a |the )?scribe"
  # Vendor claims that drift
  "powered by IBM"
  "powered by watsonx"
  "watsonx[- ]powered"
  "IBM[- ]powered"
  # Compliance overclaims
  "HIPAA[- ]compliant"
  "HIPAA[- ]certified"
  "SOC[- ]?2[- ]?certified"
  "FDA[- ]cleared"
  "HITRUST[- ]certified"
  "certified EHR"
  "production[- ]ready for PHI"
  "real patient data ready"
  # Autonomous / automation overclaims (verb-tense variants)
  "autonomous diagnosis"
  "autonomous interpretation"
  "auto[- ]interpret[s]? OCT"
  "auto[- ]grade[s]? DR"
  "auto[- ]determine[s]? cup[- ]to[- ]disc"
  "auto[- ]select[s]? IOL"
  "auto[- ]recommend[s]? anti[- ]VEGF"
  "automatic charting"
  "automatically chart[s]?"
  "automatic diagnosis"
  "automatically diagnose[s]?"
  "automatic orders"
  "automatically order[s]?"
  "automatic referrals"
  "automatically refer[s]?"
  "automatic coding"
  "automatically code[s]?"
  "automatic billing"
  "automatically bill[s]?"
  "billing[- ]aware coding"
  "coding recommendations"
  # Patient-side / external overclaims
  "patient messaging"
  "patient message[s]?"
  "patient portal"
  "send to patient"
  "submit[s]? (a )?claim[s]?"
  "submit[s]? (a |an? )?referral[s]?"
  "claim[s]? submission"
  "insurance handling"
  # Roadmap claims as-current
  "IRIS Registry submission"
  "MIPS submission"
)

fail_count=0
warn_count=0

# Per-file scan.
for f in "${FILES[@]}"; do
  [ -r "$f" ] || { echo "WARN: cannot read $f"; warn_count=$((warn_count + 1)); continue; }
  # Strip HTML tags to text-only stream for scanning. Use a portable
  # sed so the operator does not need extra tools installed. Keep the
  # original file untouched.
  text="$(sed -E 's/<[^>]+>//g' "$f" | tr -s '[:space:]' ' ')"
  for pattern in "${FORBIDDEN[@]}"; do
    if printf '%s' "$text" | grep -Eiq "$pattern"; then
      # Per-occurrence negative-context guard. We walk the original
      # file line-by-line so the operator can see which line.
      while IFS= read -r line; do
        # Strip tags from the line for the negative-context check.
        line_text="$(printf '%s' "$line" | sed -E 's/<[^>]+>//g')"
        lower="$(printf '%s' "$line_text" | tr 'A-Z' 'a-z')"
        # Negative-context regex mirrors check_commercial_claims.sh:
        # "does not", "do not", "never", "no <phrase>", sentence-
        # leading "not ", "don't say", "forbidden", "banned".
        if printf '%s' "$lower" | grep -Eq '(does not|do not|never|no autonomous|no automatic|\bnot\s|forbidden|banned|do[- ]not[- ]use|don.?t say|not approved)'; then
          continue
        fi
        echo "FAIL ($f): positive-claim pattern '$pattern'"
        echo "          $(printf '%s' "$line_text" | head -c 220)"
        fail_count=$((fail_count + 1))
      done < <(grep -Ei "$pattern" "$f" || true)
    fi
  done
done

echo
echo "Repo state"
echo "   sha:    $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')"
echo "   branch: $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
echo

if [ "$fail_count" -gt 0 ]; then
  echo "FAILED — $fail_count positive-claim hit(s) detected in captured live-site HTML."
  echo "Live site is out of compliance with the repo's safe-claims contract."
  echo "Update the live deployment before publishing or proceeding."
  exit 1
fi

echo "PASSED — 0 positive-claim hits in $((${#FILES[@]})) scanned file(s)."
echo "Note: this script is not a substitute for human review of the"
echo "live site. It is a regex-based safety net against drift."
exit 0
