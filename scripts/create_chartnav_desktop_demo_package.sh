#!/usr/bin/env bash
# scripts/create_chartnav_desktop_demo_package.sh — Phase 17
# desktop demo delivery package orchestrator.
#
# Thin wrapper around scripts/export_chartnav_decks_to_desktop.sh
# plus a post-export verification pass that confirms every
# expected file landed in the Desktop folder.
#
# Use this when you want a single command that creates the package
# and tells you whether the result is presenter-ready.
#
# Usage:
#   bash scripts/create_chartnav_desktop_demo_package.sh
#
# Override the destination (e.g., for non-default Mac users):
#   CHARTNAV_DESKTOP_DIR="$HOME/Desktop/chartnav decks" \
#     bash scripts/create_chartnav_desktop_demo_package.sh
#
# Exit codes:
#   0  package created and verified
#   1  required source missing (export refused)
#   2  filesystem error during export
#   3  post-export verification failed (file expected on the
#      Desktop is missing or not executable)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

DEFAULT_DESKTOP="/Users/jean-maxcharles/Desktop/chartnav decks"
DEST_DIR="${CHARTNAV_DESKTOP_DIR:-$DEFAULT_DESKTOP}"

echo "ChartNav desktop demo package — create + verify."
echo "  destination: $DEST_DIR"
echo

# ---------------------------------------------------------------
# 1. Run the underlying export.
# ---------------------------------------------------------------
echo "==> Running export…"
echo
bash "$SCRIPT_DIR/export_chartnav_decks_to_desktop.sh"
status=$?
echo

if [ "$status" -ne 0 ]; then
  echo "Export exited with status $status. Aborting verification."
  exit "$status"
fi

# ---------------------------------------------------------------
# 2. Post-export verification.
# ---------------------------------------------------------------
echo "==> Verifying Desktop folder…"
echo

EXPECTED_FILES=(
  "README.md"
  "00_START_HERE/chartnav-deck-master-kit.md"
  "00_START_HERE/chartnav-approved-claims-language.md"
  "00_START_HERE/chartnav-commercial-readiness-map.md"
  "01_Decks/Markdown_Source/chartnav-investor-pitch-deck.md"
  "01_Decks/Markdown_Source/chartnav-sales-deck.md"
  "01_Decks/Markdown_Source/chartnav-demo-deck.md"
  "01_Decks/Markdown_Source/chartnav-buyer-demo-deck.md"
  "01_Decks/Markdown_Source/chartnav-operator-demo-deck.md"
  "01_Decks/Markdown_Source/chartnav-customer-pitch-deck-template.md"
  "01_Decks/Markdown_Source/chartnav-company-deck.md"
  "01_Decks/Markdown_Source/chartnav-product-roadmap-deck.md"
  "01_Decks/Markdown_Source/chartnav-brand-guidelines-deck.md"
  "01_Decks/Markdown_Source/chartnav-educational-onboarding-deck.md"
  "01_Decks/Markdown_Source/chartnav-financial-fundraising-deck.md"
  "01_Decks/Markdown_Source/chartnav-marketing-plan-deck.md"
  "01_Decks/Markdown_Source/chartnav-project-proposal-deck.md"
  "01_Decks/Markdown_Source/chartnav-agency-partner-pitch-deck.md"
  "01_Decks/Markdown_Source/chartnav-elevator-pitch-deck.md"
  "01_Decks/Markdown_Source/chartnav-long-sales-pitch-deck.md"
  "02_One_Pagers/Markdown_Source/chartnav-one-page-sales-deck.md"
  "03_Demo_Package/chartnav-clinical-workflow-demo-script.md"
  "03_Demo_Package/chartnav-demo-click-path.md"
  "03_Demo_Package/chartnav-video-clip-shot-list.md"
  "03_Demo_Package/chartnav-demo-operator-guide.md"
  "03_Demo_Package/chartnav-demo-environment.md"
  "04_Pilot_Sales/chartnav-pilot-readiness-checklist.md"
  "04_Pilot_Sales/chartnav-pilot-deployment-guide.md"
  "04_Pilot_Sales/chartnav-admin-onboarding-checklist.md"
  "04_Pilot_Sales/chartnav-security-review-packet.md"
  "04_Pilot_Sales/chartnav-support-runbook.md"
  "04_Pilot_Sales/chartnav-demo-to-pilot-transition-plan.md"
  "04_Pilot_Sales/chartnav-known-limitations-and-non-goals.md"
  "04_Pilot_Sales/chartnav-pilot-success-metrics.md"
  "04_Pilot_Sales/chartnav-pilot-handoff-checklist.md"
  "05_Objection_Handling/chartnav-buyer-objection-handling.md"
  "06_Pricing_Packaging/chartnav-pricing-packaging-notes.md"
  "07_Website_Proof/chartnav-website-proof-upgrade-conversion-layer.md"
  "07_Website_Proof/chartnav-website-shot-list.md"
  "08_Local_Demo_Launcher/chartnav-local-demo-startup-guide.md"
  "08_Local_Demo_Launcher/chartnav-local-demo-troubleshooting.md"
  "08_Local_Demo_Launcher/START_CHARTNAV.command"
  "08_Local_Demo_Launcher/STOP_CHARTNAV.command"
  "08_Local_Demo_Launcher/RESET_DEMO_DATA.command"
  "09_Review_Checklists/chartnav-demo-review-checklist.md"

  # Phase 17D — branded PPTX outputs (one .pptx per deck).
  "01_Decks/PPTX/chartnav-investor-pitch-deck.pptx"
  "01_Decks/PPTX/chartnav-sales-deck.pptx"
  "01_Decks/PPTX/chartnav-demo-deck.pptx"
  "01_Decks/PPTX/chartnav-buyer-demo-deck.pptx"
  "01_Decks/PPTX/chartnav-operator-demo-deck.pptx"
  "01_Decks/PPTX/chartnav-customer-pitch-deck-template.pptx"
  "01_Decks/PPTX/chartnav-company-deck.pptx"
  "01_Decks/PPTX/chartnav-product-roadmap-deck.pptx"
  "01_Decks/PPTX/chartnav-brand-guidelines-deck.pptx"
  "01_Decks/PPTX/chartnav-educational-onboarding-deck.pptx"
  "01_Decks/PPTX/chartnav-financial-fundraising-deck.pptx"
  "01_Decks/PPTX/chartnav-marketing-plan-deck.pptx"
  "01_Decks/PPTX/chartnav-project-proposal-deck.pptx"
  "01_Decks/PPTX/chartnav-agency-partner-pitch-deck.pptx"
  "01_Decks/PPTX/chartnav-elevator-pitch-deck.pptx"
  "01_Decks/PPTX/chartnav-long-sales-pitch-deck.pptx"
  "02_One_Pagers/PPTX/chartnav-one-page-sales-deck.pptx"

  # Phase 17D — presentation-assets docs.
  "10_Presentation_Assets/palette.md"
  "10_Presentation_Assets/typography.md"
  "10_Presentation_Assets/brand-usage.md"
  "10_Presentation_Assets/chartnav-presentation-system.md"
)

EXECUTABLE_FILES=(
  "08_Local_Demo_Launcher/START_CHARTNAV.command"
  "08_Local_Demo_Launcher/STOP_CHARTNAV.command"
  "08_Local_Demo_Launcher/RESET_DEMO_DATA.command"
)

fail_count=0

for rel in "${EXPECTED_FILES[@]}"; do
  full="$DEST_DIR/$rel"
  if [ ! -f "$full" ]; then
    echo "  MISSING: $rel"
    fail_count=$((fail_count + 1))
  fi
done

for rel in "${EXECUTABLE_FILES[@]}"; do
  full="$DEST_DIR/$rel"
  if [ -f "$full" ] && [ ! -x "$full" ]; then
    echo "  NOT EXECUTABLE: $rel"
    fail_count=$((fail_count + 1))
  fi
done

if [ "$fail_count" -gt 0 ]; then
  echo
  echo "FAILED — $fail_count post-export issue(s)."
  exit 3
fi

echo "  ok — all ${#EXPECTED_FILES[@]} expected file(s) present."
echo "  ok — all ${#EXECUTABLE_FILES[@]} .command file(s) executable."
echo

# ---------------------------------------------------------------
# 3. Reminders.
# ---------------------------------------------------------------
echo "==> Reminders"
echo "  - The Desktop folder is a regenerated review package."
echo "    Re-run this script whenever any source doc updates in the repo."
echo "  - The Desktop folder is in .gitignore — never commit it."
echo "  - The local demo environment is fake-data only by"
echo "    construction. RESET_DEMO_DATA.command refuses non-local"
echo "    DATABASE_URL values."
echo

echo "Package ready at:"
echo "  $DEST_DIR"
exit 0
