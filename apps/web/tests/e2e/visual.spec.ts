import { expect, test, Page } from "@playwright/test";

/**
 * Visual regression baseline.
 *
 * We snapshot a small set of high-signal views at a fixed viewport,
 * with animations + transitions disabled, after seeding a known
 * identity and waiting for the first data paint. Snapshots land under
 * apps/web/tests/e2e/visual.spec.ts-snapshots/.
 *
 * Re-baseline with:
 *     npx playwright test tests/e2e/visual.spec.ts --update-snapshots
 *
 * Pixel tolerance is intentionally modest (`maxDiffPixelRatio: 0.02`):
 * small renderer drift between chromium builds shouldn't turn the
 * suite into a minefield, but a real layout regression will still
 * crack the threshold.
 */

test.use({ viewport: { width: 1280, height: 820 } });

async function freezeUI(page: Page) {
  await page.addStyleTag({
    content: `
      *,
      *::before,
      *::after {
        transition: none !important;
        animation: none !important;
        caret-color: transparent !important;
      }
    `,
  });
}

async function seedAdmin(page: Page) {
  await page.goto("/");
  await page.evaluate(() =>
    localStorage.setItem("chartnav.devIdentity", "admin@chartnav.local")
  );
  await page.reload();
  await expect(page.getByTestId("identity-badge")).toContainText("admin");
  // Wait for the list's first response
  await expect(page.getByTestId("enc-list")).toBeVisible();
  await freezeUI(page);
}

const MATCH = {
  maxDiffPixelRatio: 0.02,
  animations: "disabled" as const,
};

test.describe("visual regression baseline", () => {
  test("encounter list — default admin view", async ({ page }) => {
    await seedAdmin(page);
    await expect(page.getByTestId("enc-list")).toHaveScreenshot(
      "encounter-list.png",
      MATCH
    );
  });

  test("admin panel — users tab", async ({ page }) => {
    await seedAdmin(page);
    await page.getByTestId("open-admin-panel").click();
    await expect(page.getByTestId("admin-users-table")).toBeVisible();
    await freezeUI(page);
    await expect(page.getByTestId("admin-panel")).toHaveScreenshot(
      "admin-users.png",
      MATCH
    );
  });

  test("admin panel — audit tab", async ({ page }) => {
    await seedAdmin(page);
    await page.getByTestId("open-admin-panel").click();
    await page.getByTestId("admin-tab-audit").click();
    await expect(page.getByTestId("admin-audit-table")).toBeVisible();
    await freezeUI(page);
    await expect(page.getByTestId("admin-panel")).toHaveScreenshot(
      "admin-audit.png",
      MATCH
    );
  });

  test("invite accept screen", async ({ page }) => {
    await page.goto("/invite?invite=placeholder-token-for-visual-baseline");
    await expect(page.getByTestId("invite-token-input")).toBeVisible();
    await freezeUI(page);
    await expect(page).toHaveScreenshot("invite-accept.png", MATCH);
  });
});
