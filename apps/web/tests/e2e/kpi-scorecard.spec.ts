import { expect, test, Page } from "@playwright/test";

/**
 * Phase 47 — pilot KPI scorecard smoke spec.
 *
 * The seeded backend does not drive a full transcript→draft→sign
 * pipeline, so the KPI numbers in the UI are mostly zeros/—. That
 * is the honest state and matches what a day-one pilot will see.
 * This spec verifies the scorecard surface loads, the admin tab is
 * reachable, the pilot summary renders, the window selector works,
 * the compare toggle flips, and the CSV export succeeds.
 */

const ADMIN = "admin@chartnav.local";

async function login(page: Page, email: string) {
  await page.goto("/");
  await page.waitForSelector("[data-testid=identity-badge]");
  await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
  await page.reload();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openAdminKpi(page: Page) {
  await page.getByTestId("open-admin-panel").click();
  await page.getByTestId("admin-tab-kpi").click();
  await page.waitForSelector("[data-testid=kpi-pane]");
}

test.describe("KPI scorecard", () => {
  test("admin tab opens the pilot scorecard with pilot summary + KPI cards", async ({ page }) => {
    await login(page, ADMIN);
    await openAdminKpi(page);
    await expect(page.getByTestId("kpi-pilot-summary")).toBeVisible();
    await expect(page.getByTestId("kpi-card-encounters")).toBeVisible();
    await expect(page.getByTestId("kpi-card-total")).toBeVisible();
    await expect(page.getByTestId("kpi-card-missing")).toBeVisible();
    await expect(page.getByTestId("kpi-card-export-ready")).toBeVisible();
  });

  test("window selector swaps the request window", async ({ page }) => {
    await login(page, ADMIN);
    await openAdminKpi(page);
    // Click 24h and observe at least one network request to ?hours=24
    const reqs: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/admin/kpi/")) reqs.push(r.url());
    });
    await page.getByTestId("kpi-window-24").click();
    await expect(page.getByTestId("kpi-pane")).toBeVisible();
    // Wait a beat for the fetch to start.
    await page.waitForTimeout(300);
    expect(reqs.some((u) => u.includes("hours=24"))).toBeTruthy();
  });

  test("compare toggle surfaces delta chips on latency cards", async ({ page }) => {
    await login(page, ADMIN);
    await openAdminKpi(page);
    await page.getByTestId("kpi-compare-toggle").check();
    // Any of the three latency cards may render a chip; assert at
    // least one is present once compare mode is on.
    await page.waitForTimeout(500);
    const deltaChips = page.locator(".kpi-card__delta");
    expect(await deltaChips.count()).toBeGreaterThan(0);
  });

  test("export button downloads a CSV", async ({ page }) => {
    await login(page, ADMIN);
    await openAdminKpi(page);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByTestId("kpi-export").click(),
    ]);
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/chartnav-kpi.*\.csv$/i);
  });
});
