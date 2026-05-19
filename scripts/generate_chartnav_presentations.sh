#!/usr/bin/env bash
# scripts/generate_chartnav_presentations.sh — Phase 17D
# branded-PPTX generator entry point.
#
# Wraps `node tools/presentations/generateAll.js` so the operator
# can regenerate every ChartNav presentation with one command.
#
# What it does:
#   1. Ensures node_modules in tools/presentations/ are installed.
#   2. Runs the JS driver which parses every markdown deck under
#      docs/decks/ and writes a branded .pptx into the operator's
#      Desktop folder under 01_Decks/PPTX/ (and 02_One_Pagers/PPTX/
#      for the one-page sales deck).
#
# Override the destination via:
#   CHARTNAV_DESKTOP_DIR="$HOME/Desktop/chartnav decks"
#
# PDF export is deferred — pure-JS PPTX-to-PDF requires a heavy
# LibreOffice headless dependency. Open the generated PPTX in
# PowerPoint or Keynote and "Export as PDF" if you need PDFs.
#
# Usage:
#   bash scripts/generate_chartnav_presentations.sh
#
# Exit codes:
#   0  presentations generated
#   1  generator failed (missing source / parse error)
#   2  Node.js or npm not available

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_DIR="$REPO_ROOT/tools/presentations"

DEFAULT_DESKTOP="/Users/jean-maxcharles/Desktop/chartnav decks"
DEST_DIR="${CHARTNAV_DESKTOP_DIR:-$DEFAULT_DESKTOP}"

echo "ChartNav presentation generation (Phase 17D)."
echo "  destination: $DEST_DIR"
echo

# 1. Verify Node.js + npm.
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node is not on the PATH. Install Node 18+ first."
  exit 2
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is not on the PATH. Install Node 18+ first."
  exit 2
fi
node_version="$(node --version 2>&1)"
echo "  node:    $node_version"

# 2. Install presentation tooling deps if missing.
if [ ! -d "$TOOLS_DIR/node_modules" ]; then
  echo "  installing tools/presentations dependencies…"
  ( cd "$TOOLS_DIR" && npm install --no-audit --no-fund )
  echo
fi

# 3. Run the JS driver.
cd "$REPO_ROOT"
CHARTNAV_DESKTOP_DIR="$DEST_DIR" node "$TOOLS_DIR/generateAll.js"

echo
echo "Done. Open the Desktop folder and review the generated PPTX:"
echo "  $DEST_DIR/01_Decks/PPTX/"
echo "  $DEST_DIR/02_One_Pagers/PPTX/"
