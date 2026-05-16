#!/usr/bin/env bash
#
# Phase 19K — public-site / platform separation guard.
#
# Fails the build if the static public-marketing source under
# apps/web/chartnavmd-site/ accidentally re-exposes any of the
# authenticated chartnav-platform clinical-SPA markers. This is the
# regression that produced the 8 May incident where chartnavmd.com
# was serving the clinical SPA with the localhost:8000 chip visible.
#
# Also requires the public-site source to retain the public markers
# that prove the marketing page is actually shipping the marketing
# content (ChartNav, ophthalmology, workflow, provider-reviewed,
# Español).
#
# Usage:
#   bash scripts/check_public_site_not_platform.sh
# Exit codes:
#   0  all checks pass
#   1  forbidden platform marker found, or required public marker missing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> public-site / platform separation guard"
echo "    site root: $SITE_ROOT"

# ---- files in scope (every .html under the static site) ---------------
TARGETS=()
while IFS= read -r f; do TARGETS+=("$f"); done < <(find "$SITE_ROOT" -type f -name "*.html" \
  -not -path "*/.vercel/*" -not -path "*/node_modules/*")

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "FAIL — no static .html pages found under $SITE_ROOT"
  exit 1
fi

# ---- forbidden platform markers ---------------------------------------
# Each entry is a fixed string that should NEVER appear in the public
# static source. These are the markers that surfaced on chartnavmd.com
# when the platform SPA hijacked the domain.
FORBIDDEN=(
  "auth failed to fetch"
  "API http://localhost:8000"
  "API http://localhost"
  "admin@chartnav.local"
  "Select an encounter"
  "ClinicalTabbedWorkspace"
  "RoleDashboard"
  "Security Readiness"
  "Production Readiness"
  "clinical workflow platform"
)

# Platform-only sidebar nav labels. These are platform-context markers,
# NOT the marketing site nav items. We allow them only if they appear
# inside an inline-script string or a negative-context safety phrase.
# To keep the guard simple, treat them as forbidden on the public site.
FORBIDDEN_NAV=(
  "Org 1"
)

fail_count=0
for f in "${TARGETS[@]}"; do
  for needle in "${FORBIDDEN[@]}"; do
    if grep -F -q -- "$needle" "$f"; then
      echo "FAIL — forbidden platform marker in $f:"
      grep -F -n -- "$needle" "$f" | head -3
      fail_count=$((fail_count+1))
    fi
  done
  for needle in "${FORBIDDEN_NAV[@]}"; do
    if grep -F -q -- "$needle" "$f"; then
      echo "FAIL — platform nav marker '$needle' in $f"
      fail_count=$((fail_count+1))
    fi
  done
done

# ---- required public markers ------------------------------------------
# At least one .html under the public site must mention each of these.
REQUIRED=(
  "ChartNav"
  "ophthalmology"
  "workflow"
  "provider-reviewed"
  "Español"
)

for needle in "${REQUIRED[@]}"; do
  if ! grep -lF -r -- "$needle" "${TARGETS[@]}" >/dev/null 2>&1; then
    echo "FAIL — required public-site marker '$needle' missing from all pages"
    fail_count=$((fail_count+1))
  fi
done

# ---- summary ----------------------------------------------------------
if [ "$fail_count" -gt 0 ]; then
  echo
  echo "FAIL — $fail_count check(s) failed."
  exit 1
fi

echo "PASS — $(echo "${TARGETS[@]}" | wc -w | tr -d ' ') pages, no platform markers, all required public markers present."
exit 0
