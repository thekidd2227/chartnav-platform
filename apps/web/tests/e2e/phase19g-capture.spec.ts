/**
 * Phase 19G — media-review screenshot capture spec.
 *
 * This spec is intentionally NOT a CI test. It writes PNG files
 * to a directory the operator owns on their local machine so
 * Jean-Max can do a visual review of the post-Phase-19F demo
 * UI before final delivery.
 *
 * Skip-guard: the spec is gated on the CAPTURE_OUT_DIR env var.
 * Without that var set the suite is empty (test.skip) so a
 * normal `npx playwright test` run never tries to write to
 * the operator's Desktop and never fails because the target
 * directory doesn't exist.
 *
 * Usage (from the repo root, on the operator's Mac):
 *
 *   bash tools/media-review/capture_phase19g_media.sh \
 *     "$HOME/Desktop/Chartnav/ChartNav_Media_Review_Final_UI"
 *
 * The bash wrapper sets CAPTURE_OUT_DIR + E2E_BASE_URL and
 * invokes Playwright through the existing webServer config
 * (which boots the api + frontend stack against an ephemeral
 * SQLite seed). All 12 screenshots land in
 * "${CAPTURE_OUT_DIR}/01_Screenshots/".
 *
 * Safety contract: every screenshot is taken against a fresh
 * seeded SQLite DB containing fake demo data only. No real
 * PHI ever reaches this spec.
 */

import { test, expect, type Page } from "@playwright/test";
import { existsSync, mkdirSync } from "fs";
import path from "path";

const OUT_DIR = process.env.CAPTURE_OUT_DIR;
const SCREENSHOT_DIR = OUT_DIR
  ? path.join(OUT_DIR, "01_Screenshots")
  : null;

// Skip-guard: an empty CAPTURE_OUT_DIR means "this is normal CI,
// don't capture." We use test.skip rather than describe.skip so
// the suite still parses cleanly under playwright list.
test.describe("Phase 19G — media review screenshot capture", () => {
  test.skip(!OUT_DIR, "CAPTURE_OUT_DIR not set; capture spec disabled");

  // Single-shot setup: pre-create the screenshot dir so individual
  // screenshot() calls don't fail with ENOENT.
  test.beforeAll(() => {
    if (SCREENSHOT_DIR && !existsSync(SCREENSHOT_DIR)) {
      mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  // Default desktop viewport for shots 01..11. Shot 12 (narrow
  // mobile layout) overrides via page.setViewportSize().
  test.use({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });

  test("captures all 12 Phase 19G review screenshots", async ({ page }) => {
    if (!SCREENSHOT_DIR) {
      test.skip();
      return;
    }

    // Navigate with ?demo=1 — Guided Demo Mode hides the dev API
    // URL chip per Phase 17 / 19 contract.
    await page.goto("/?demo=1");

    // Wait for the encounter list to populate. The seed creates
    // an admin-visible encounter list; pick the first row.
    const firstEncounter = page
      .getByTestId(/^enc-row-/)
      .first();
    await expect(firstEncounter).toBeVisible({ timeout: 15_000 });
    await firstEncounter.click();

    // Tabbed workspace mounts.
    await expect(
      page.getByTestId("clinical-tabbed-workspace")
    ).toBeVisible({ timeout: 10_000 });

    // Helper: click tab, wait for its panel, full-page screenshot.
    async function shotTab(slug: string, file: string) {
      await page.getByTestId(`ctw-tab-${slug}`).click();
      await expect(
        page.getByTestId(`ctw-panel-${slug}`)
      ).toBeVisible();
      // Tiny settle for any tab-switch transition.
      await page.waitForTimeout(250);
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR!, file),
        fullPage: true,
      });
    }

    // Per the Phase 19F final tab list — exactly 9 tabs, no
    // Billing.
    await shotTab("overview", "01_overview.png");
    await shotTab("clinical", "02_clinical_ophthalmology.png");
    await shotTab("documentation", "03_documentation_emr_ehr.png");
    await shotTab("imaging", "04_imaging.png");
    await shotTab("orders-labs", "05_labs_orders_review.png");
    await shotTab("calendar", "06_calendar.png");
    await shotTab("communications", "07_communications.png");
    await shotTab("documents", "08_documents.png");
    await shotTab("chat", "09_chat.png");

    // 10 — sidebar + topbar closeup. Crops the left-hand grouped
    // sidebar nav (Phase 19E burgundy + teal active stripe).
    await shotPanelSidebar(page, "10_sidebar_header_closeup.png");

    // 11 — patient header + demographic strip closeup. Captures
    // the Phase 19F intentional empty-state copy ("Not available
    // in demo" / "No allergies recorded" / etc.) plus the Phase
    // 19E red-accent stripe.
    await shotPatientHeader(page, "11_patient_header_demographics.png");

    // 12 — narrow viewport (mobile). Set viewport to a typical
    // phone-portrait size and screenshot the same Overview tab
    // so the responsive collapse is visible.
    await shotMobile(page, "12_mobile_or_narrow_layout.png");
  });
});

async function shotPanelSidebar(page: Page, file: string) {
  if (!SCREENSHOT_DIR) return;
  // Re-show Overview before the closeup so the active item is
  // the wired Encounters entry (the teal active stripe lives
  // there).
  await page.getByTestId("ctw-tab-overview").click();
  await expect(page.getByTestId("ctw-panel-overview")).toBeVisible();
  // Capture the entire viewport — the sidebar nav + topbar
  // lives flush-left so a viewport screenshot frames it
  // naturally without needing an element-clip.
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, file),
    fullPage: false,
    clip: { x: 0, y: 0, width: 320, height: 900 },
  });
}

async function shotPatientHeader(page: Page, file: string) {
  if (!SCREENSHOT_DIR) return;
  await page.getByTestId("ctw-tab-overview").click();
  const header = page.getByTestId("ctw-patient-header");
  await expect(header).toBeVisible();
  await header.screenshot({
    path: path.join(SCREENSHOT_DIR, file),
  });
}

async function shotMobile(page: Page, file: string) {
  if (!SCREENSHOT_DIR) return;
  await page.setViewportSize({ width: 414, height: 896 });
  await page.getByTestId("ctw-tab-overview").click();
  await expect(page.getByTestId("ctw-panel-overview")).toBeVisible();
  await page.waitForTimeout(250);
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, file),
    fullPage: true,
  });
}
