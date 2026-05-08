#!/usr/bin/env node
/**
 * Phase 19C — Playwright-driven screenshot capture for the
 * media-review package.
 *
 * Walks the 10 tabs of the new clinical workspace against the
 * fake-data demo route and writes one PNG per tab into a
 * caller-supplied output directory. No image binaries are
 * committed — output lives outside the repo (default:
 * `$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/01_New_Screenshots/`).
 *
 * Pre-reqs (all on the operator's machine):
 *   1. Local stack running on http://127.0.0.1:5173 with
 *      seeded demo data. Boot via `make dev` from the repo root.
 *   2. `@playwright/test` installed under apps/web (already true
 *      in this monorepo — used by the e2e suite).
 *   3. The `?demo=1` query param hides the dev API URL chip.
 *
 * Usage:
 *   node tools/media-review/capture_phase19c_screenshots.mjs \
 *     --out "$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/01_New_Screenshots" \
 *     [--base-url http://127.0.0.1:5173]
 *
 * Exit codes:
 *   0   captured successfully
 *   2   couldn't load Playwright (missing dep)
 *   3   couldn't reach the local stack
 *   4   capture failed mid-run
 *
 * Safety contract:
 *   - Uses fake demo data only (the `?demo=1` route + seeded
 *     `admin@chartnav.local` identity).
 *   - Never touches real PHI.
 *   - Never writes anything to the repo working tree.
 */

import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

// Resolve playwright from apps/web/node_modules — this script lives
// outside that workspace, so a plain `import` would miss it.
const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..", "..");
const PLAYWRIGHT_ENTRY = resolve(
  REPO_ROOT,
  "apps",
  "web",
  "node_modules",
  "@playwright",
  "test",
  "index.mjs"
);

let chromium;
try {
  ({ chromium } = await import(PLAYWRIGHT_ENTRY));
} catch (err) {
  console.error(
    `[capture] Failed to import Playwright from ${PLAYWRIGHT_ENTRY}.`
  );
  console.error(
    `[capture] Run \`npm --prefix apps/web install\` first.`
  );
  console.error(`[capture] Underlying error: ${err.message}`);
  process.exit(2);
}

// ---------------------------------------------------------------
// CLI parsing.
// ---------------------------------------------------------------

const argv = process.argv.slice(2);
function flag(name, def) {
  const idx = argv.indexOf(`--${name}`);
  if (idx === -1) return def;
  return argv[idx + 1];
}

const OUT_DIR = flag(
  "out",
  resolve(
    process.env.HOME || ".",
    "Desktop",
    "Chartnav",
    "ChartNav_Media_Review_Phase19B",
    "01_New_Screenshots"
  )
);
const BASE_URL = flag("base-url", "http://127.0.0.1:5173");

// ---------------------------------------------------------------
// Tab catalog — must match ClinicalTabbedWorkspace.tsx (Phase 19B).
// ---------------------------------------------------------------

const TABS = [
  { slug: "overview", filename: "01_overview_tab.png" },
  { slug: "clinical", filename: "02_clinical_ophthalmology_tab.png" },
  { slug: "documentation", filename: "03_documentation_emr_ehr_tab.png" },
  { slug: "imaging", filename: "04_imaging_tab.png" },
  { slug: "orders-labs", filename: "05_orders_labs_tab.png" },
  { slug: "calendar", filename: "06_calendar_tab.png" },
  { slug: "communications", filename: "07_communications_tab.png" },
  { slug: "documents", filename: "08_documents_tab.png" },
  { slug: "chat", filename: "09_chat_tab.png" },
  { slug: "billing", filename: "10_billing_review_tab.png" },
];

// ---------------------------------------------------------------
// Capture.
// ---------------------------------------------------------------

async function main() {
  console.log(`[capture] base-url:   ${BASE_URL}`);
  console.log(`[capture] output dir: ${OUT_DIR}`);
  await mkdir(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  // 1. Land on the demo route. ?demo=1 hides the dev API chip.
  try {
    await page.goto(`${BASE_URL}/?demo=1`, {
      waitUntil: "networkidle",
      timeout: 15_000,
    });
  } catch (err) {
    console.error(
      `[capture] Couldn't reach ${BASE_URL}/?demo=1. Boot the local stack with \`make dev\` first.`
    );
    console.error(`[capture] Underlying error: ${err.message}`);
    await browser.close();
    process.exit(3);
  }

  // 2. Pin the seeded admin identity so the demo always renders
  //    as "Identity Admin · Org 1".
  await page.evaluate(() =>
    window.localStorage.setItem(
      "chartnav.devIdentity",
      "admin@chartnav.local"
    )
  );
  await page.reload({ waitUntil: "networkidle" });

  // 3. Wait for the encounter list, then click the seeded encounter.
  await page.waitForSelector("[data-testid=enc-list]", { timeout: 10_000 });
  await page.locator("[data-testid=enc-row-1]").click();
  await page.waitForSelector("[data-testid=clinical-tabbed-workspace]", {
    timeout: 10_000,
  });

  // 4. Walk each tab, screenshot the full page (so the dark sidebar
  //    + top header + patient header + tab content all land in the
  //    PNG).
  let captured = 0;
  for (const tab of TABS) {
    try {
      await page.locator(`[data-testid=ctw-tab-${tab.slug}]`).click();
      await page.waitForSelector(`[data-testid=ctw-panel-${tab.slug}]`, {
        timeout: 5_000,
      });
      // Small settle so any panel-mount transitions complete before
      // we shoot.
      await page.waitForTimeout(250);
      const path = resolve(OUT_DIR, tab.filename);
      await page.screenshot({ path, fullPage: true });
      console.log(`[capture] ✓ ${tab.filename}`);
      captured++;
    } catch (err) {
      console.error(
        `[capture] ✗ ${tab.filename} — ${err.message}`
      );
    }
  }

  await browser.close();

  if (captured !== TABS.length) {
    console.error(
      `[capture] Only ${captured}/${TABS.length} screenshots captured. Re-run after fixing the failures above.`
    );
    process.exit(4);
  }
  console.log(
    `[capture] Done. ${captured}/${TABS.length} screenshots written to ${OUT_DIR}`
  );
}

await main();
