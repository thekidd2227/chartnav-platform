/**
 * Clinical Shortcuts — screenshot capture script.
 *
 * Requires:
 *   - API running on :8000 with CHARTNAV_AUTH_MODE=header + CHARTNAV_RUN_SEED=1
 *   - Web dev server running on :5173
 *   - Playwright chromium installed (npx playwright install chromium)
 *
 * Run:  node qa/screenshots/clinical-shortcuts/capture.mjs
 */

import { chromium } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = __dirname; // save PNGs next to this script
const BASE = "http://localhost:5173";

async function main() {
  const browser = await chromium.launch({ headless: true });

  // ── Helper: set identity via localStorage, then reload ─────────
  async function setIdentity(page, email) {
    await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
    await page.reload({ waitUntil: "networkidle" });
    // wait for the workspace to mount
    await page.waitForTimeout(1500);
  }

  // ── Helper: click first encounter to open the workspace ────────
  async function openFirstEncounter(page) {
    // The encounter list has rows; click the first one.
    const row = page.locator('[data-testid="encounter-row"]').first();
    if (await row.isVisible()) {
      await row.click();
      await page.waitForTimeout(1200);
    }
  }

  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // Load the app
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // ── SCREENSHOT 1: Doctor view — Quick Comments + Clinical Shortcuts visible ──
  console.log("1. Setting identity to clinician (doctor)…");
  await setIdentity(page, "clin@chartnav.local");
  await openFirstEncounter(page);
  // Scroll the right panel to make both panels visible
  const qcPanel = page.locator('[data-testid="quick-comments-panel"]');
  const csPanel = page.locator('[data-testid="clinical-shortcuts-panel"]');
  // Try to scroll both into view
  if (await csPanel.isVisible()) {
    await csPanel.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
  }
  await page.screenshot({
    path: path.join(OUT, "01-doctor-view-quick-comments-and-clinical-shortcuts.png"),
    fullPage: false,
  });
  console.log("  ✓ Screenshot 1 saved");

  // ── SCREENSHOT 2: Clinical Shortcuts searched with "RD" ────────
  console.log("2. Searching shortcuts for 'RD'…");
  const searchInput = page.locator('[data-testid="clinical-shortcuts-search"]');
  if (await searchInput.isVisible()) {
    await searchInput.fill("RD");
    await page.waitForTimeout(600);
  }
  await csPanel.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(OUT, "02-clinical-shortcuts-search-rd.png"),
    fullPage: false,
  });
  console.log("  ✓ Screenshot 2 saved");

  // ── SCREENSHOT 3: Clinical Shortcuts searched with "AMD" ───────
  console.log("3. Searching shortcuts for 'AMD'…");
  if (await searchInput.isVisible()) {
    await searchInput.fill("AMD");
    await page.waitForTimeout(600);
  }
  await csPanel.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(OUT, "03-clinical-shortcuts-search-amd.png"),
    fullPage: false,
  });
  console.log("  ✓ Screenshot 3 saved");

  // ── SCREENSHOT 4: Shortcut inserted into draft area ────────────
  console.log("4. Inserting a shortcut into the draft…");
  // Clear search first to see all shortcuts
  if (await searchInput.isVisible()) await searchInput.fill("");
  await page.waitForTimeout(400);
  // Click the first shortcut button to insert it
  const firstShortcut = page.locator('[data-testid="clinical-shortcuts-panel"] button').first();
  if (await firstShortcut.isVisible()) {
    await firstShortcut.click();
    await page.waitForTimeout(600);
  }
  // Scroll back to the draft/editor area to show the insertion
  const draftArea = page.locator('[data-testid="draft-textarea"], [data-testid="note-draft"], textarea').first();
  if (await draftArea.isVisible()) {
    await draftArea.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
  }
  await page.screenshot({
    path: path.join(OUT, "04-shortcut-inserted-into-draft-area.png"),
    fullPage: false,
  });
  console.log("  ✓ Screenshot 4 saved");

  // ── SCREENSHOT 5: Reviewer view — Clinical Shortcuts hidden ────
  console.log("5. Switching to reviewer identity…");
  await setIdentity(page, "rev@chartnav.local");
  await openFirstEncounter(page);
  // Verify clinical shortcuts panel is NOT visible
  const csHidden = !(await csPanel.isVisible());
  console.log(`   Clinical Shortcuts visible to reviewer: ${!csHidden}`);
  await page.screenshot({
    path: path.join(OUT, "05-reviewer-view-clinical-shortcuts-hidden.png"),
    fullPage: false,
  });
  console.log("  ✓ Screenshot 5 saved");

  await browser.close();

  console.log("\n=== All 5 screenshots captured ===");
  console.log(`Output directory: ${OUT}`);
  console.log(`Clinical Shortcuts hidden for reviewer: ${csHidden ? "YES ✓" : "NO — ISSUE"}`);
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
