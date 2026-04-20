import { chromium } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(__dirname, "../../../qa/screenshots/clinical-shortcuts");
const BASE = "http://localhost:5173";

async function main() {
  const browser = await chromium.launch({ headless: true });
  async function setIdentity(page, email) {
    await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
    await page.reload({ waitUntil: "networkidle" });
    await page.waitForTimeout(2500);
  }
  async function openEncounterWithDraft(page) {
    // Encounter 2 (Jordan Rivera, review_needed) has note_draft_completed
    const row = page.locator('[data-testid="enc-row-2"]');
    const vis = await row.isVisible({ timeout: 5000 }).catch(() => false);
    if (vis) { await row.click(); await page.waitForTimeout(2000); }
    else {
      // Fallback: click the first row
      const any = page.locator('[data-testid^="enc-row-"]').first();
      if (await any.isVisible({ timeout: 3000 }).catch(() => false)) {
        await any.click(); await page.waitForTimeout(2000);
      }
    }
  }

  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1400 } });
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);

  // 1: Doctor view — Quick Comments + Clinical Shortcuts
  console.log("1. Doctor view…");
  await setIdentity(page, "clin@chartnav.local");
  await openEncounterWithDraft(page);
  // Verify both panels are visible
  const qcVis = await page.locator('[data-testid="quick-comments-panel"]').isVisible({ timeout: 3000 }).catch(() => false);
  const csVis1 = await page.locator('[data-testid="clinical-shortcuts-panel"]').isVisible({ timeout: 3000 }).catch(() => false);
  console.log("  Quick Comments visible: " + qcVis + "  Clinical Shortcuts visible: " + csVis1);
  await page.screenshot({ path: path.join(OUT, "01-doctor-view-quick-comments-and-clinical-shortcuts.png"), fullPage: true });
  console.log("  done");

  // 2: Search RD
  console.log("2. Search RD…");
  const si = page.locator('[data-testid="clinical-shortcuts-search"]');
  const hasSI = await si.isVisible({ timeout: 3000 }).catch(() => false);
  if (hasSI) { await si.fill("RD"); await page.waitForTimeout(800); }
  else { console.log("  ⚠ clinical-shortcuts-search not visible"); }
  await page.screenshot({ path: path.join(OUT, "02-clinical-shortcuts-search-rd.png"), fullPage: true });
  console.log("  done");

  // 3: Search AMD
  console.log("3. Search AMD…");
  if (hasSI) { await si.fill("AMD"); await page.waitForTimeout(800); }
  await page.screenshot({ path: path.join(OUT, "03-clinical-shortcuts-search-amd.png"), fullPage: true });
  console.log("  done");

  // 4: Insert shortcut — clear search, click enabled shortcut button
  console.log("4. Insert shortcut…");
  if (hasSI) await si.fill("");
  await page.waitForTimeout(500);
  // Check if draft textarea exists (buttons are enabled when draft is present)
  const hasDraft = await page.locator('[data-testid="note-draft-textarea"]').isVisible({ timeout: 2000 }).catch(() => false);
  console.log("  draft textarea visible: " + hasDraft);
  const btns = page.locator('[data-testid="clinical-shortcuts-panel"] button:not([disabled])');
  const cnt = await btns.count();
  console.log("  enabled shortcut buttons: " + cnt);
  let inserted = false;
  for (let i = 0; i < cnt; i++) {
    const t = await btns.nth(i).textContent();
    const disabled = await btns.nth(i).isDisabled();
    if (!disabled && t && t.length > 3 && !t.includes("☆") && !t.includes("★")) {
      await btns.nth(i).click({ timeout: 5000 });
      await page.waitForTimeout(800);
      console.log("  clicked: " + t.trim().substring(0, 50));
      inserted = true;
      break;
    }
  }
  if (!inserted) console.log("  ⚠ no insertable shortcut button found (buttons may still be disabled)");
  await page.screenshot({ path: path.join(OUT, "04-shortcut-inserted-into-draft-area.png"), fullPage: true });
  console.log("  done");

  // 5: Reviewer view — shortcuts hidden
  console.log("5. Reviewer view…");
  await setIdentity(page, "rev@chartnav.local");
  await openEncounterWithDraft(page);
  const csVis5 = await page.locator('[data-testid="clinical-shortcuts-panel"]').isVisible({ timeout: 2000 }).catch(() => false);
  await page.screenshot({ path: path.join(OUT, "05-reviewer-view-clinical-shortcuts-hidden.png"), fullPage: true });
  console.log("  done");

  await browser.close();
  console.log("\nAll 5 screenshots captured.");
  console.log("Output: " + OUT);
  console.log("Shortcuts hidden for reviewer: " + (!csVis5 ? "YES ✓" : "NO — ISSUE"));
}
main().catch(e => { console.error(e); process.exit(1); });
