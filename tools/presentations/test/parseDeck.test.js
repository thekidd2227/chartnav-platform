/**
 * Node-based smoke test for tools/presentations/parseDeck.js.
 *
 * This file lives outside vitest's Vite scope so it can exercise
 * the parser directly against the live markdown decks. Run with:
 *
 *   node tools/presentations/test/parseDeck.test.js
 *
 * Or via the package script:
 *
 *   npm --prefix tools/presentations run test
 *
 * Exits non-zero on any assertion failure.
 */

import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseDeckMarkdown } from "../parseDeck.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

let failed = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`  ok    ${name}`);
  } catch (err) {
    failed += 1;
    console.error(`  FAIL  ${name}`);
    console.error(`        ${err.message}`);
  }
}

// 1. Investor deck — canonical slide-style markdown.
check("investor deck parses with audience/purpose/CTA + ≥14 slides", () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-investor-pitch-deck.md")
  );
  if (!/Investor Pitch/i.test(deck.deckTitle)) throw new Error(`title: ${deck.deckTitle}`);
  if (!/investor/i.test(deck.audience || "")) throw new Error(`audience: ${deck.audience}`);
  if (!/demo|fundraising/i.test(deck.cta || "")) throw new Error(`cta: ${deck.cta}`);
  if (deck.slides.length < 14) throw new Error(`slide count: ${deck.slides.length}`);
});

check("investor deck has a Clinical Signal Filtering slide", () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-investor-pitch-deck.md")
  );
  const csf = deck.slides.find((s) =>
    /clinical signal filtering|filters conversation/i.test(s.title || "")
  );
  if (!csf) throw new Error("no CSF slide found");
});

// 2. One-pager — H3 fallback.
check("one-page sales deck parses ≥5 sections via H3 fallback", () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-one-page-sales-deck.md")
  );
  if (deck.slides.length < 5) {
    throw new Error(`one-pager slide count: ${deck.slides.length}`);
  }
  const titles = deck.slides.map((s) => s.title).join("\n");
  if (!/headline|problem|solution|pricing/i.test(titles)) {
    throw new Error(`one-pager titles: ${titles}`);
  }
});

// 3. Demo-deck index — H2 routing.
check("demo-deck index parses with routing slides", () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-demo-deck.md")
  );
  if (deck.slides.length < 2) {
    throw new Error(`demo-deck slide count: ${deck.slides.length}`);
  }
});

// 4. Speaker notes capture.
check("speaker notes capture on at least one investor-deck slide", () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-investor-pitch-deck.md")
  );
  const withNotes = deck.slides.filter((s) => s.speakerNotes && s.speakerNotes.length > 0);
  if (withNotes.length === 0) throw new Error("no slides have speakerNotes");
});

if (failed > 0) {
  console.error(`\n${failed} parser test(s) failed.`);
  process.exit(1);
}
console.log("\nparseDeck tests passed.");
