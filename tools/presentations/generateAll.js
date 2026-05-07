/**
 * Phase 17D — generate the full ChartNav presentation set.
 *
 * Walks the deck library at `docs/decks/`, parses each markdown
 * deck, renders it through the branded slide-layout system, and
 * writes the PPTX file into the appropriate Desktop sub-folder.
 *
 * Defaults:
 *   - Source root      : <repo>/docs/decks/
 *   - Desktop dest     : /Users/jean-maxcharles/Desktop/chartnav decks
 *   - PPTX output dirs :
 *       01_Decks/PPTX/                    (every deck except the one-pager)
 *       02_One_Pagers/PPTX/               (the one-page sales deck)
 *
 * Override the destination via CHARTNAV_DESKTOP_DIR.
 *
 * The driver does **not** write Markdown source copies into the
 * Desktop folder — that is the job of
 * `scripts/export_chartnav_decks_to_desktop.sh`. This driver only
 * generates PPTX outputs.
 *
 * Usage:
 *   node tools/presentations/generateAll.js
 *   CHARTNAV_DESKTOP_DIR=/tmp/desk node tools/presentations/generateAll.js
 *
 * Exit codes:
 *   0  all decks generated
 *   1  one or more decks failed to parse / render
 *   2  filesystem error (mkdir / write)
 */

import { readdirSync, mkdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { parseDeckMarkdown } from "./parseDeck.js";
import { renderDeck } from "./renderDeck.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const DECKS_DIR = path.join(REPO_ROOT, "docs", "decks");

const DEFAULT_DESKTOP = "/Users/jean-maxcharles/Desktop/chartnav decks";
const DESKTOP_DIR = process.env.CHARTNAV_DESKTOP_DIR || DEFAULT_DESKTOP;

const ONE_PAGER_DECKS = new Set(["chartnav-one-page-sales-deck"]);

// Decks the operator asked us to convert. The demo index is
// included so the routing index has a printable copy too.
const REQUIRED_DECKS = [
  "chartnav-investor-pitch-deck",
  "chartnav-sales-deck",
  "chartnav-long-sales-pitch-deck",
  "chartnav-one-page-sales-deck",
  "chartnav-buyer-demo-deck",
  "chartnav-operator-demo-deck",
  "chartnav-company-deck",
  "chartnav-customer-pitch-deck-template",
  "chartnav-project-proposal-deck",
  "chartnav-financial-fundraising-deck",
  "chartnav-product-roadmap-deck",
  "chartnav-marketing-plan-deck",
  "chartnav-brand-guidelines-deck",
  "chartnav-educational-onboarding-deck",
  "chartnav-agency-partner-pitch-deck",
  "chartnav-elevator-pitch-deck",
  "chartnav-demo-deck",
];

function deckOutputDir(deckId) {
  if (ONE_PAGER_DECKS.has(deckId)) {
    return path.join(DESKTOP_DIR, "02_One_Pagers", "PPTX");
  }
  return path.join(DESKTOP_DIR, "01_Decks", "PPTX");
}

async function main() {
  console.log("ChartNav presentation generator (Phase 17D).");
  console.log(`  source decks: ${DECKS_DIR}`);
  console.log(`  destination : ${DESKTOP_DIR}`);
  console.log("");

  // 1. Validate every required deck is on disk.
  const missing = [];
  for (const deckId of REQUIRED_DECKS) {
    const p = path.join(DECKS_DIR, `${deckId}.md`);
    try {
      const s = statSync(p);
      if (!s.isFile()) missing.push(deckId);
    } catch {
      missing.push(deckId);
    }
  }
  if (missing.length > 0) {
    console.error(`FAILED — missing deck source(s): ${missing.join(", ")}`);
    process.exit(1);
  }
  console.log(`  ok — all ${REQUIRED_DECKS.length} deck source(s) present.`);
  console.log("");

  // 2. Ensure destination folders exist.
  const outputDirs = new Set();
  for (const deckId of REQUIRED_DECKS) outputDirs.add(deckOutputDir(deckId));
  outputDirs.add(path.join(DESKTOP_DIR, "10_Presentation_Assets"));
  for (const d of outputDirs) {
    try {
      mkdirSync(d, { recursive: true });
    } catch (err) {
      console.error(`FAILED — mkdir ${d}: ${err.message}`);
      process.exit(2);
    }
  }

  // 3. Render + write each deck.
  let generated = 0;
  let failed = 0;
  const summary = [];
  for (const deckId of REQUIRED_DECKS) {
    const src = path.join(DECKS_DIR, `${deckId}.md`);
    try {
      const deck = parseDeckMarkdown(src);
      const pptx = renderDeck(deck);
      const outDir = deckOutputDir(deckId);
      const outPath = path.join(outDir, `${deckId}.pptx`);
      await pptx.writeFile({ fileName: outPath });
      generated += 1;
      summary.push({
        deckId,
        slides: deck.slides.length,
        outPath,
      });
      console.log(
        `  ok   ${deckId.padEnd(40)} ${deck.slides.length.toString().padStart(2)} slides → ${path.relative(DESKTOP_DIR, outPath)}`
      );
    } catch (err) {
      failed += 1;
      console.error(`  FAIL ${deckId}: ${err.stack || err.message}`);
    }
  }
  console.log("");

  // 4. Summary.
  console.log(`Generated ${generated} of ${REQUIRED_DECKS.length} presentations.`);
  if (failed > 0) {
    console.error(`${failed} deck(s) failed.`);
    process.exit(1);
  }
  console.log("PDF export is deferred — pure-JS PPTX-to-PDF requires a heavy");
  console.log("LibreOffice headless dependency. Open the PPTX files in");
  console.log("PowerPoint or Keynote and export PDFs manually if needed.");
  console.log("");
  console.log("Done. Open the Desktop folder and review:");
  console.log(`  ${DESKTOP_DIR}/01_Decks/PPTX/`);
  console.log(`  ${DESKTOP_DIR}/02_One_Pagers/PPTX/`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
