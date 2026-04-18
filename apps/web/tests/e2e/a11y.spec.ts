import AxeBuilder from "@axe-core/playwright";
import { expect, test, Page } from "@playwright/test";

/**
 * WCAG 2.1 AA accessibility baseline.
 *
 * Scope: main app shell, encounter list, encounter detail, admin
 * panel, invite accept screen. We scan with axe-core and fail the
 * test on any `serious` or `critical` violation. We stop short of
 * breaking on `minor` findings so the baseline is meaningful but
 * not flaky — the suite is a floor, not a ceiling.
 *
 * Impact levels come from axe itself; see
 * https://github.com/dequelabs/axe-core/blob/master/doc/rule-descriptions.md
 */

const BLOCKING_IMPACTS = new Set(["serious", "critical"]);

async function scan(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const blocking = results.violations.filter(
    (v) => v.impact && BLOCKING_IMPACTS.has(v.impact)
  );
  if (blocking.length) {
    const summary = blocking
      .map(
        (v) =>
          `  - [${v.impact}] ${v.id}: ${v.help} (nodes: ${v.nodes.length})\n    ${v.helpUrl}`
      )
      .join("\n");
    throw new Error(
      `axe found ${blocking.length} blocking violations:\n${summary}`
    );
  }
  // Still surface non-blocking for the report.
  if (results.violations.length) {
    console.log(
      `[axe] ${results.violations.length} non-blocking findings on ${page.url()}`
    );
  }
}

async function seedAdmin(page: Page) {
  await page.goto("/");
  await page.evaluate(() =>
    localStorage.setItem("chartnav.devIdentity", "admin@chartnav.local")
  );
  await page.reload();
  // Wait for identity + first list fetch to complete.
  await expect(page.getByTestId("identity-badge")).toContainText("admin");
}

test.describe("a11y — WCAG 2.1 AA blocking floor", () => {
  test("app shell + encounter list", async ({ page }) => {
    await seedAdmin(page);
    await scan(page);
  });

  test("encounter detail", async ({ page }) => {
    await seedAdmin(page);
    await page.getByTestId("enc-row-1").click();
    await expect(page.getByTestId("encounter-detail")).toBeVisible();
    await scan(page);
  });

  test("admin panel (users tab)", async ({ page }) => {
    await seedAdmin(page);
    await page.getByTestId("open-admin-panel").click();
    await expect(page.getByTestId("admin-panel")).toBeVisible();
    await scan(page);
  });

  test("admin panel (audit tab)", async ({ page }) => {
    await seedAdmin(page);
    await page.getByTestId("open-admin-panel").click();
    await page.getByTestId("admin-tab-audit").click();
    await expect(page.getByTestId("admin-audit-table")).toBeVisible();
    await scan(page);
  });

  test("invite accept screen", async ({ page }) => {
    await page.goto("/invite?invite=placeholder-token-for-a11y-scan-only");
    await expect(page.getByTestId("invite-token-input")).toBeVisible();
    await scan(page);
  });
});
