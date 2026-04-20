import { chromium } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(__dirname, "../../../qa/screenshots/full-app");
const BASE = "http://localhost:5173";
let seq = 0;

async function main() {
  const browser = await chromium.launch({ headless: true });

  async function setId(page, email) {
    await page.evaluate(e => localStorage.setItem("chartnav.devIdentity", e), email);
    await page.reload({ waitUntil: "networkidle" });
    await page.waitForTimeout(2500);
  }

  async function snap(page, name) {
    seq++;
    const fn = String(seq).padStart(2,"0") + "-" + name + ".png";
    await page.screenshot({ path: path.join(OUT, fn), fullPage: true });
    console.log("  ✓ " + fn);
  }

  async function tryClick(page, sel, wait) {
    const el = page.locator(sel).first();
    const v = await el.isVisible({ timeout: 3000 }).catch(() => false);
    if (v) { await el.click({ timeout: 5000 }).catch(()=>{}); await page.waitForTimeout(wait || 1500); }
    return v;
  }

  async function closeModal(page) {
    // Try clicking the modal backdrop edge, or pressing Escape multiple times
    for (let i = 0; i < 3; i++) {
      const modal = page.locator('[data-testid="create-modal"]');
      if (await modal.isVisible({ timeout: 500 }).catch(() => false)) {
        await page.mouse.click(10, 10);
        await page.waitForTimeout(500);
      } else break;
    }
    // Also try the admin panel close
    for (let i = 0; i < 3; i++) {
      const ap = page.locator('[data-testid="admin-panel"]');
      if (await ap.isVisible({ timeout: 500 }).catch(() => false)) {
        await page.mouse.click(10, 10);
        await page.waitForTimeout(500);
      } else break;
    }
  }

  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // ─── CLINICIAN ─────────────────────────────────────────────
  console.log("\n=== CLINICIAN ===");
  await setId(page, "clin@chartnav.local");

  await snap(page, "clinician-encounter-list");

  if (await tryClick(page, '[data-testid="open-create-encounter"]')) {
    await snap(page, "clinician-create-encounter-dialog");
    await closeModal(page);
  }

  await tryClick(page, '[data-testid="enc-row-2"]');
  await snap(page, "clinician-encounter-detail-review-needed");

  // Scroll down through workspace tiers
  for (const tier of ["workspace-tier-transcript", "workspace-tier-findings", "workspace-tier-draft"]) {
    const el = page.locator(`[data-testid="${tier}"]`);
    if (await el.isVisible({ timeout: 1500 }).catch(() => false)) {
      await el.scrollIntoViewIfNeeded().catch(()=>{});
      await page.waitForTimeout(300);
      await snap(page, "clinician-" + tier.replace("workspace-tier-",""));
    }
  }

  // Audio recording section
  const audioEl = page.locator('text=Record dictation');
  if (await audioEl.isVisible({ timeout: 1500 }).catch(() => false)) {
    await audioEl.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "clinician-audio-recording");
  }

  // Quick Comments full panel
  const qc = page.locator('[data-testid="quick-comments-panel"]');
  if (await qc.isVisible({ timeout: 1500 }).catch(() => false)) {
    await qc.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "clinician-quick-comments-panel");

    // QC search
    const qcS = page.locator('[data-testid="quick-comments-search"]');
    if (await qcS.isVisible({ timeout: 1000 }).catch(() => false)) {
      await qcS.fill("IOP");
      await page.waitForTimeout(500);
      await snap(page, "clinician-quick-comments-search-iop");
      await qcS.fill("");
    }
  }

  // Clinical Shortcuts full panel
  const cs = page.locator('[data-testid="clinical-shortcuts-panel"]');
  if (await cs.isVisible({ timeout: 1500 }).catch(() => false)) {
    await cs.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "clinician-clinical-shortcuts-full");

    const csS = page.locator('[data-testid="clinical-shortcuts-search"]');
    if (await csS.isVisible({ timeout: 1000 }).catch(() => false)) {
      for (const q of ["RD", "AMD", "SRF", "PVD", "IOL"]) {
        await csS.fill(q);
        await page.waitForTimeout(500);
        await snap(page, "clinician-shortcuts-search-" + q.toLowerCase());
      }
      await csS.fill("");
    }
  }

  // Timeline
  const tl = page.locator('text=TIMELINE');
  if (await tl.isVisible({ timeout: 1500 }).catch(() => false)) {
    await tl.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "clinician-timeline");
  }

  // Encounter #1 in_progress
  await tryClick(page, '[data-testid="enc-row-1"]');
  await snap(page, "clinician-encounter-in-progress");

  // ─── REVIEWER ──────────────────────────────────────────────
  console.log("\n=== REVIEWER ===");
  await setId(page, "rev@chartnav.local");
  await snap(page, "reviewer-encounter-list");

  await tryClick(page, '[data-testid="enc-row-2"]');
  await snap(page, "reviewer-encounter-detail");

  const csR = await page.locator('[data-testid="clinical-shortcuts-panel"]').isVisible({ timeout: 1000 }).catch(() => false);
  const qcR = await page.locator('[data-testid="quick-comments-panel"]').isVisible({ timeout: 1000 }).catch(() => false);
  console.log("  reviewer: shortcuts=" + csR + " quickcomments=" + qcR);
  await snap(page, "reviewer-workspace-panels-hidden");

  // Reviewer transitions
  const trans = page.locator('text=ALLOWED TRANSITIONS');
  if (await trans.isVisible({ timeout: 1500 }).catch(() => false)) {
    await trans.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "reviewer-transitions");
  }

  // Reviewer timeline
  const tlR = page.locator('text=TIMELINE');
  if (await tlR.isVisible({ timeout: 1500 }).catch(() => false)) {
    await tlR.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "reviewer-timeline");
  }

  // ─── ADMIN ─────────────────────────────────────────────────
  console.log("\n=== ADMIN ===");
  await setId(page, "admin@chartnav.local");
  await snap(page, "admin-encounter-list");

  if (await tryClick(page, '[data-testid="open-admin-panel"]')) {
    await page.waitForTimeout(1000);
    await snap(page, "admin-panel-organization");

    for (const tab of ["users", "providers", "patients", "locations", "audit"]) {
      await tryClick(page, `[data-testid="admin-tab-${tab}"]`, 1000);
      await snap(page, "admin-panel-" + tab);
    }
    await closeModal(page);
  }

  await tryClick(page, '[data-testid="enc-row-2"]');
  await snap(page, "admin-encounter-workspace");

  if (await tryClick(page, '[data-testid="open-create-encounter"]')) {
    await snap(page, "admin-create-encounter-dialog");
    await closeModal(page);
  }

  // ─── ORG 2 ─────────────────────────────────────────────────
  console.log("\n=== ORG 2 ===");
  await setId(page, "clin@northside.local");
  await snap(page, "org2-clinician-list");
  const org2Row = page.locator('[data-testid^="enc-row-"]').first();
  if (await org2Row.isVisible({ timeout: 2000 }).catch(() => false)) {
    await org2Row.click().catch(()=>{});
    await page.waitForTimeout(1500);
    await snap(page, "org2-clinician-encounter");
  }

  await setId(page, "admin@northside.local");
  await snap(page, "org2-admin-list");
  if (await tryClick(page, '[data-testid="open-admin-panel"]')) {
    await page.waitForTimeout(1000);
    await snap(page, "org2-admin-panel");
    await closeModal(page);
  }

  // ─── FILTERS ───────────────────────────────────────────────
  console.log("\n=== FILTERS ===");
  await setId(page, "clin@chartnav.local");
  const statusSel = page.locator('[data-testid="status-filter"], select').first();
  if (await statusSel.isVisible({ timeout: 1500 }).catch(() => false)) {
    for (const val of ["review_needed", "in_progress", "completed", "signed"]) {
      await statusSel.selectOption(val).catch(()=>{});
      await page.waitForTimeout(800);
      await snap(page, "filter-" + val);
    }
    await statusSel.selectOption("").catch(()=>{});
  }

  // ─── FOOTER ────────────────────────────────────────────────
  const ft = page.locator('[data-testid="app-footer"]');
  if (await ft.isVisible({ timeout: 1000 }).catch(() => false)) {
    await ft.scrollIntoViewIfNeeded().catch(()=>{});
    await snap(page, "app-footer");
  }

  await browser.close();
  console.log("\n=== TOTAL: " + seq + " screenshots ===");
  console.log("Output: " + OUT);
}
main().catch(e => { console.error(e); process.exit(1); });
