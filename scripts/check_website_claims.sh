#!/usr/bin/env bash
# scripts/check_website_claims.sh — public website / landing page
# claims verifier.
#
# What it does:
#   1. confirms apps/web/src/LandingPage.tsx exists and contains
#      the required negative-assertion safety phrasing;
#   2. confirms main.tsx wires the /landing and ?intro=1 gate;
#   3. greps the LandingPage source for forbidden positive claims
#      (the vitest suite at apps/web/src/test/WebsiteProofUpgrade
#      is authoritative — this script is a lightweight pre-deploy
#      sanity check);
#   4. confirms no binary media is checked in under apps/web/public
#      beyond the small SVG brand assets that already shipped;
#   5. prints the current git SHA + a short reminder.
#
# Usage:
#   bash scripts/check_website_claims.sh
# Exit codes:
#   0  passed (zero fail; warns are tolerated)
#   1  failed (a required file is missing or a forbidden positive
#      claim was detected)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

LANDING="apps/web/src/LandingPage.tsx"
ROUTER="apps/web/src/main.tsx"

fail_count=0
warn_count=0

echo "ChartNav website claims check — fake-data demo path only."
echo

# 1. Required files exist.
echo "1. Required files"
for f in "$LANDING" "$ROUTER" "apps/web/src/test/WebsiteProofUpgrade.test.tsx"; do
  if [ ! -f "$f" ]; then
    echo "   MISSING: $f"
    fail_count=$((fail_count + 1))
  else
    echo "   ok       $f"
  fi
done
echo

# 2. main.tsx routes /landing + ?intro=1 to LandingPage.
echo "2. Router gate"
if [ -f "$ROUTER" ]; then
  if grep -Eq '\.endsWith\("/landing"\)' "$ROUTER" \
     && grep -Eq 'params\.get\("intro"\)' "$ROUTER" \
     && grep -Eq 'LandingPage' "$ROUTER"; then
    echo "   ok — /landing + ?intro=1 → LandingPage"
  else
    echo "   FAIL — main.tsx does not gate /landing or ?intro=1 to LandingPage"
    fail_count=$((fail_count + 1))
  fi
fi
echo

# 3. Required negative-assertion phrasing.
#
# Phase 24A — required-phrase list updated to match the
# ophthalmology-specific non-goals block. The landing page must
# include explicit negative assertions across: EHR replacement,
# HIPAA-certified, autonomous diagnosis, OCT interpretation,
# IOL power selection, real-PHI gate, patient messaging.
echo "3. Negative-assertion phrasing on LandingPage"
if [ -f "$LANDING" ]; then
  for phrase in \
    "Provider-reviewed workflow support" \
    "does not diagnose" \
    "does not.*diagnose, create orders, send referrals, bill, or message patients" \
    "Not a certified EHR" \
    "Not HIPAA-certified" \
    "Not autonomous diagnosis" \
    "Does not autofill IOP" \
    "Does not interpret OCT" \
    "Real-PHI pilot requires BAA"; do
    if grep -Eq "$phrase" "$LANDING"; then
      echo "   ok       $phrase"
    else
      echo "   FAIL — missing phrase: $phrase"
      fail_count=$((fail_count + 1))
    fi
  done
fi
echo

# 4. Forbidden positive claims.
echo "4. Forbidden positive claims (vitest is authoritative)"
# Only flag a match if the line is not clearly negative-context
# (does not / not / never / "Not a/an" prefix).
forbidden_positive=(
  "HIPAA[- ]compliant"
  "HIPAA[- ]certified"
  "SOC[- ]?2[- ]?certified"
  "production[- ]ready for PHI"
  "real patient data ready"
)
forbidden_capability_positive=(
  "certified EHR"
  "autonomous diagnosis"
  "automatic diagnosis"
  "guaranteed accuracy"
  "automatic orders"
  "order OCT"
  "submit referral"
  "send patient message"
  "replaces a doctor"
)
if [ -f "$LANDING" ]; then
  # Phase 24A — compliance claims now use the same negative-context
  # guard as capability claims. The landing page intentionally
  # includes "Not HIPAA-certified" + "Not a certified EHR" as
  # negative assertions; the guard exempts those.
  for pattern in "${forbidden_positive[@]}"; do
    while IFS= read -r line; do
      lower="$(printf '%s' "$line" | tr 'A-Z' 'a-z')"
      if printf '%s' "$lower" | grep -Eq "(does not|never|\\bnot\\s|not approved)"; then
        continue
      fi
      echo "   FAIL — forbidden compliance claim: $pattern"
      echo "          $line"
      fail_count=$((fail_count + 1))
    done < <(grep -i "$pattern" "$LANDING" || true)
  done
  for pattern in "${forbidden_capability_positive[@]}"; do
    while IFS= read -r line; do
      lower="$(printf '%s' "$line" | tr 'A-Z' 'a-z')"
      if printf '%s' "$lower" | grep -Eq "(does not|never|\\bnot\\s)"; then
        continue
      fi
      echo "   warn — '$pattern' found outside obvious negative context: $line"
      warn_count=$((warn_count + 1))
    done < <(grep -i "$pattern" "$LANDING" || true)
  done
fi
if [ "$fail_count" -eq 0 ] && [ "$warn_count" -eq 0 ]; then
  echo "   ok — no forbidden positive claims detected."
fi
echo

# 5. Binary media under apps/web/public.
echo "5. Binary media scan under apps/web/public"
binaries=$(find apps/web/public -type f \
  \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
     -o -iname '*.gif' -o -iname '*.webp' -o -iname '*.mp4' \
     -o -iname '*.mov' -o -iname '*.webm' -o -iname '*.pdf' \) \
  2>/dev/null || true)
if [ -n "$binaries" ]; then
  echo "   FAIL — binary media checked in under apps/web/public:"
  printf '   %s\n' $binaries
  fail_count=$((fail_count + 1))
else
  echo "   ok — only SVG/text assets under apps/web/public."
fi
echo

# 6. Git SHA.
echo "6. Repo state"
echo "   sha:    $(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "   branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo

# 7. Reminders.
echo "7. Reminders"
echo "   - Phase 16 ships only public landing / proof page + tests + docs."
echo "   - vitest at apps/web/src/test/WebsiteProofUpgrade.test.tsx is"
echo "     authoritative for the safe-claims contract."
echo "   - To preview the page locally, append ?intro=1 to the dev URL."
echo

if [ "$fail_count" -gt 0 ]; then
  echo "FAILED — $fail_count fail(s), $warn_count warn(s)."
  exit 1
fi
if [ "$warn_count" -gt 0 ]; then
  echo "PASSED with $warn_count heuristic warn(s); run vitest to confirm."
  exit 0
fi
echo "PASSED — 0 fail / 0 warn."
exit 0
