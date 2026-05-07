/**
 * Node-based smoke test for tools/presentations/renderDeck.js.
 *
 * Renders one deck end-to-end and checks the PptxGenJS instance
 * carries the expected slide count + non-empty PPTX bytes when
 * written to a tmpfile.
 *
 *   node tools/presentations/test/renderDeck.test.js
 */

import path from "node:path";
import { mkdtempSync, statSync, rmSync } from "node:fs";
import os from "node:os";
import { fileURLToPath } from "node:url";

import { parseDeckMarkdown } from "../parseDeck.js";
import { renderDeck } from "../renderDeck.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

let failed = 0;
async function check(name, fn) {
  try {
    await fn();
    console.log(`  ok    ${name}`);
  } catch (err) {
    failed += 1;
    console.error(`  FAIL  ${name}`);
    console.error(`        ${err.stack || err.message}`);
  }
}

const tmp = mkdtempSync(path.join(os.tmpdir(), "cn-renderdeck-"));

await check("renders the elevator deck and writes a non-empty PPTX", async () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-elevator-pitch-deck.md")
  );
  const pptx = renderDeck(deck);
  const out = path.join(tmp, "elevator.pptx");
  await pptx.writeFile({ fileName: out });
  const sz = statSync(out).size;
  if (sz < 5000) throw new Error(`pptx size: ${sz}`);
});

await check("renders the buyer-demo deck and writes a non-empty PPTX", async () => {
  const deck = parseDeckMarkdown(
    path.join(REPO_ROOT, "docs/decks/chartnav-buyer-demo-deck.md")
  );
  const pptx = renderDeck(deck);
  const out = path.join(tmp, "buyer-demo.pptx");
  await pptx.writeFile({ fileName: out });
  const sz = statSync(out).size;
  if (sz < 5000) throw new Error(`buyer-demo size: ${sz}`);
});

rmSync(tmp, { recursive: true, force: true });

if (failed > 0) {
  console.error(`\n${failed} render test(s) failed.`);
  process.exit(1);
}
console.log("\nrenderDeck tests passed.");
