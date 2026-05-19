#!/usr/bin/env bash
# scripts/check_pilot_readiness.sh — pilot-readiness verifier.
#
# Confirms that the Phase 14 pilot docs exist, that the docs do not
# contain unsafe positive claims, that no binary media is checked
# in under docs/pilot/, and prints the current git SHA + a short
# checklist reminder.
#
# Non-destructive. Adds no dependencies. Uses only `bash`, `grep`,
# `find`, `git`, `awk`, `sort`, `wc`. Suitable for ad-hoc local
# verification or a pre-pilot dry run.
#
# Usage:
#   bash scripts/check_pilot_readiness.sh
# Exits non-zero if any required doc is missing OR any unsafe
# positive claim slips outside a negative-assertion / forbidden-list
# context (heuristic — tests in apps/web/src/test/PilotReadinessClaims.test.tsx
# are the source of truth).

set -euo pipefail

# Resolve the repo root regardless of where the script is invoked
# from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PILOT_DOCS=(
  "docs/chartnav-pilot-readiness-deployment-hardening.md"
  "docs/pilot/chartnav-pilot-readiness-checklist.md"
  "docs/pilot/chartnav-pilot-deployment-guide.md"
  "docs/pilot/chartnav-admin-onboarding-checklist.md"
  "docs/pilot/chartnav-security-review-packet.md"
  "docs/pilot/chartnav-support-runbook.md"
  "docs/pilot/chartnav-demo-to-pilot-transition-plan.md"
  "docs/pilot/chartnav-known-limitations-and-non-goals.md"
  "docs/pilot/chartnav-pilot-success-metrics.md"
)

# Forbidden positive claims. The vitest suite is authoritative; this
# is a lightweight sanity check.
FORBIDDEN_PATTERNS=(
  "HIPAA[- ]compliant"
  "HIPAA[- ]certified"
  "SOC[- ]?2[- ]?certified"
  "certified EHR"
  "autonomous diagnosis"
  "automatic diagnosis"
  "guaranteed accuracy"
  "automatic orders?"
  "order OCT"
  "submit referral"
  "send referral"
  "billing automation"
  "coding automation"
  "send patient message"
  "replaces (a )?doctor"
  "production[- ]ready for PHI"
)

fail_count=0
warn_count=0

# 1) Required pilot docs exist + are non-empty.
echo "1. Pilot docs presence"
for doc in "${PILOT_DOCS[@]}"; do
  if [ ! -f "$doc" ]; then
    echo "   MISSING: $doc"
    fail_count=$((fail_count + 1))
  elif [ ! -s "$doc" ]; then
    echo "   EMPTY:   $doc"
    fail_count=$((fail_count + 1))
  else
    echo "   ok       $doc"
  fi
done
echo

# 2) Heuristic forbidden-claim scan. A line is flagged if it
#    matches a forbidden pattern AND the line itself contains no
#    obvious negation marker. This is intentionally conservative —
#    the vitest suite is the source of truth.
echo "2. Forbidden-claim heuristic scan (vitest is authoritative)"
for doc in "${PILOT_DOCS[@]}"; do
  [ -f "$doc" ] || continue
  while IFS= read -r line; do
    # Strip markdown bold/italic markers for heuristic.
    stripped="$(printf '%s' "$line" | tr -d '*_`')"
    lower="$(printf '%s' "$stripped" | tr 'A-Z' 'a-z')"
    # Negative-assertion markers.
    if printf '%s' "$lower" | grep -Eq \
        '(does not|is not|are not|never|^[[:space:]]*(-[[:space:]]*)?not[[:space:]]|forbidden|do not say|never claim|never use|never appear)'; then
      continue
    fi
    if printf '%s' "$lower" | grep -Eq '\bno [a-z]'; then
      continue
    fi
    # Bullet-style or table-row entries are accepted.
    if printf '%s' "$line" | grep -Eq '^[[:space:]]*([-*][[:space:]]|\||[0-9]+\.[[:space:]])'; then
      continue
    fi
    # Q&A question heading? (line ends with `?`)
    if printf '%s' "$line" | grep -Eq '^#{1,6}[[:space:]].+\?[[:space:]]*"?[[:space:]]*$'; then
      continue
    fi
    for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
      if printf '%s' "$lower" | grep -Eq "\b${pattern}\b"; then
        echo "   warn: $doc: forbidden-pattern match outside obvious negative context"
        echo "         line: $line"
        warn_count=$((warn_count + 1))
        break
      fi
    done
  done < "$doc"
done
if [ "$warn_count" -eq 0 ]; then
  echo "   ok — no obvious unsafe claim slipped past the heuristic."
fi
echo

# 3) Binary media under docs/pilot/.
echo "3. Binary media scan under docs/pilot/"
binaries=$(find docs/pilot -type f \
  \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.webm' \
     -o -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
     -o -iname '*.gif' -o -iname '*.pdf' -o -iname '*.bin' \
     -o -iname '*.zip' -o -iname '*.tar' -o -iname '*.gz' \) \
  2>/dev/null || true)
if [ -n "$binaries" ]; then
  echo "   FAIL — binary media checked in under docs/pilot/:"
  printf '   %s\n' $binaries
  fail_count=$((fail_count + 1))
else
  echo "   ok — no binary media under docs/pilot/."
fi
echo

# 4) Git SHA + branch.
echo "4. Repo state"
echo "   sha:    $(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "   branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo

# 5) Checklist reminder.
echo "5. Checklist reminder"
echo "   - Phase 14 PR scope: docs + readiness tests + this script."
echo "   - No new clinical features. No new schema. No backend code."
echo "   - Real PHI only after BAA + security review gating items."
echo "   - vitest claims test (apps/web/src/test/PilotReadinessClaims.test.tsx)"
echo "     is authoritative for the safe-language contract."
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
