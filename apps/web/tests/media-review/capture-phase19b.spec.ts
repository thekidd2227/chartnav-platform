import { test, expect, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

/**
 * Phase 19C — media-review screenshot capture spec.
 *
 * Walks the 10 tabs of the Phase 19B clinical workspace against
 * the Playwright-managed dev stack and writes one PNG per tab
 * into the directory pointed to by the `CAPTURE_OUT_DIR` env
 * var (default: `$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/01_New_Screenshots`).
 *
 * Why this exists as a Playwright TEST rather than a standalone
 * Node script: the existing `playwright.config.ts` already boots
 * both the API (port 8001) and the web (port 5174) cleanly via
 * `webServer:`, against an ephemeral SQLite file with the seeded
 * fake-data demo. CI uses this exact harness, so the Playwright
 * install is known-good. A direct `import("playwright")` from a
 * standalone script can hit the corrupted-node_modules edge
 * (e.g. `Cannot find module './mcp/test/browserBackend'`); using
 * `npx playwright test` sidesteps it.
 *
 * Usage (Mac, after `bash tools/media-review/capture_phase19c_media.sh`):
 *
 *   CAPTURE_OUT_DIR="$HOME/Desktop/Chartnav/ChartNav_Media_Review_Phase19B/01_New_Screenshots" \
 *     npx --prefix apps/web playwright test \
 *       --project=chromium \
 *       tests/media-review/capture-phase19b.spec.ts
 *
 * Safety contract:
 *   - Uses the seeded admin@chartnav.local identity + the
 *     `?demo=1` query param so the API URL chip is hidden.
 *   - Captures fake demo data only — never real PHI.
 *   - Output directory is OUTSIDE the repo working tree by
 *     default (Desktop). The repo never receives image binaries.
 */

const OUT_DIR =
  process.env.CAPTURE_OUT_DIR ||
  resolve(
    process.env.HOME || ".",
    "Desktop",
    "Chartnav",
    "ChartNav_Media_Review_Phase19B",
    "01_New_Screenshots"
  );

// Tab catalog must match ClinicalTabbedWorkspace.tsx (Phase 19B).
const TABS: { slug: string; filename: string }[] = [
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

async function pinAdminIdentity(page: Page) {
  await page.goto("/?demo=1");
  await page.evaluate(() =>
    window.localStorage.setItem(
      "chartnav.devIdentity",
      "admin@chartnav.local"
    )
  );
  await page.reload();
  await expect(page.getByTestId("identity-badge")).toContainText(/Admin/);
  await expect(page.getByTestId("enc-list")).toBeVisible();
}

test.describe("Phase 19C — capture media-review screenshots", () => {
  test.beforeAll(async () => {
    await mkdir(OUT_DIR, { recursive: true });
    // eslint-disable-next-line no-console
    console.log(`[capture] output: ${OUT_DIR}`);
  });

  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
  });

  test.use({ viewport: { width: 1440, height: 900 } });

  for (const tab of TABS) {
    test(`captures ${tab.filename} (${tab.slug})`, async ({ page }) => {
      await pinAdminIdentity(page);
      await page.locator("[data-testid=enc-row-1]").click();
      await page.waitForSelector("[data-testid=clinical-tabbed-workspace]");
      await page.locator(`[data-testid=ctw-tab-${tab.slug}]`).click();
      await page.waitForSelector(`[data-testid=ctw-panel-${tab.slug}]`);
      // Small settle so panel-mount transitions complete.
      await page.waitForTimeout(250);
      const path = resolve(OUT_DIR, tab.filename);
      await page.screenshot({ path, fullPage: true });
      // eslint-disable-next-line no-console
      console.log(`[capture] ✓ ${tab.filename}`);
    });
  }
});
