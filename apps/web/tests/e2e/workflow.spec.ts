import { expect, test, Page } from "@playwright/test";

const ADMIN1 = "admin@chartnav.local";
const CLIN1 = "clin@chartnav.local";
const REV1 = "rev@chartnav.local";
const ADMIN2 = "admin@northside.local";

async function switchIdentity(page: Page, email: string) {
  // If we're in seeded-select mode, just pick it.
  const select = page.getByTestId("identity-select");
  if (await select.isVisible().catch(() => false)) {
    const options = await select.locator("option").allInnerTexts();
    const match = options.find((t) => t.includes(email));
    if (match) {
      await select.selectOption({ label: match });
      return;
    }
    // Fall through to custom-email mode.
    await select.selectOption("__custom__");
  }
  // Custom-email path.
  const input = page.getByPlaceholder("user@example.com");
  await input.fill(email);
  await page.getByRole("button", { name: /^use$/ }).click();
}

async function waitForIdentity(page: Page, token: string) {
  await expect(page.getByTestId("identity-badge")).toContainText(token);
}

test.describe("ChartNav end-to-end", () => {
  test.beforeEach(async ({ page }) => {
    // Each test gets a clean identity (no localStorage carryover).
    await page.context().clearCookies();
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("boots and resolves the default seeded identity", async ({ page }) => {
    // Default identity is the first seeded entry (admin@chartnav.local).
    await waitForIdentity(page, "admin@chartnav.local");
    await expect(page.getByTestId("identity-badge")).toContainText("admin");
    await expect(page.getByTestId("identity-badge")).toContainText("org 1");
    await expect(page.getByTestId("enc-list")).toBeVisible();
  });

  test("switching identity changes caller scope (org1 → org2)", async ({ page }) => {
    await waitForIdentity(page, "admin@chartnav.local");
    await expect(page.getByText("Morgan Lee")).toBeVisible();

    await switchIdentity(page, ADMIN2);
    await waitForIdentity(page, "org 2");

    await expect(page.getByText("Priya Shah")).toBeVisible();
    await expect(page.getByText("Morgan Lee")).toHaveCount(0);
  });

  test("admin can open detail, create encounter, and see it appear", async ({ page }) => {
    await waitForIdentity(page, "admin");

    // Open an existing encounter.
    await page.getByTestId("enc-row-1").click();
    await expect(page.getByTestId("encounter-detail")).toBeVisible();
    await expect(page.getByTestId("detail-status")).toContainText("in progress");

    // Create a new one.
    await page.getByTestId("open-create-encounter").click();
    await expect(page.getByTestId("create-modal")).toBeVisible();

    const pid = `E2E-${Date.now()}`;
    await page.getByTestId("create-patient-id").fill(pid);
    await page.getByTestId("create-patient-name").fill("E2E Patient");
    await page.getByTestId("create-provider").fill("Dr. E2E");
    // Location dropdown auto-selects the only option.
    await page.getByTestId("create-submit").click();

    await expect(page.getByTestId("create-modal")).toBeHidden();
    await expect(page.getByTestId("banner-ok")).toContainText(pid);
    // The new encounter auto-selects, so its row lives in the list AND its
    // pid appears in the detail sub-heading. Assert against the list row
    // (the detail sub-text doesn't carry its own testid).
    await expect(page.getByTestId("enc-list")).toContainText(pid);
  });

  test("admin can append a workflow event", async ({ page }) => {
    await waitForIdentity(page, "admin");
    await page.getByTestId("enc-row-1").click();
    await expect(page.getByTestId("encounter-detail")).toBeVisible();

    const marker = `note-${Date.now()}`;
    await page.getByTestId("event-type").fill(`e2e_${marker}`);
    await page.getByTestId("event-submit").click();
    await expect(page.getByTestId("banner-ok")).toContainText(`e2e_${marker}`);
    // Event appears in timeline.
    await expect(page.locator(`.event-item__type >> text=e2e_${marker}`)).toBeVisible();
  });

  test("clinician performs operational transition; review edge is not offered", async ({ page }) => {
    await waitForIdentity(page, "admin");
    await switchIdentity(page, CLIN1);
    await waitForIdentity(page, "clinician");

    // Create a fresh scheduled encounter so transition tests are deterministic
    // regardless of earlier runs.
    await page.getByTestId("open-create-encounter").click();
    const pid = `CLIN-${Date.now()}`;
    await page.getByTestId("create-patient-id").fill(pid);
    await page.getByTestId("create-provider").fill("Dr. Clin");
    await page.getByTestId("create-submit").click();
    await expect(page.getByTestId("create-modal")).toBeHidden();
    await expect(page.getByTestId("detail-status")).toContainText("scheduled");

    // scheduled -> in_progress is operational
    await page.getByTestId("transition-in_progress").click();
    await expect(page.getByTestId("detail-status")).toContainText("in progress");

    // in_progress -> draft_ready is operational
    await page.getByTestId("transition-draft_ready").click();
    await expect(page.getByTestId("detail-status")).toContainText("draft ready");

    // draft_ready -> review_needed is a reviewer edge — must NOT appear.
    await expect(page.getByTestId("transition-review_needed")).toHaveCount(0);
  });

  test("reviewer sees review controls, no create button, no event composer", async ({ page }) => {
    await waitForIdentity(page, "admin");
    await switchIdentity(page, REV1);
    await waitForIdentity(page, "reviewer");

    // No create button in header.
    await expect(page.getByTestId("open-create-encounter")).toHaveCount(0);

    // Open PT-1002 (seeded at review_needed).
    await page.getByTestId("enc-row-2").click();
    await expect(page.getByTestId("encounter-detail")).toBeVisible();

    // Reviewer sees completion + kick-back transitions.
    await expect(page.getByTestId("transition-completed")).toBeVisible();
    await expect(page.getByTestId("transition-draft_ready")).toBeVisible();

    // No event composer.
    await expect(page.getByTestId("event-denied")).toBeVisible();
    await expect(page.getByTestId("event-form")).toHaveCount(0);
  });

  test("unknown email surfaces auth error chip", async ({ page }) => {
    await waitForIdentity(page, "admin");
    await switchIdentity(page, "ghost@nowhere.test");
    await expect(page.getByTestId("identity-error")).toBeVisible();
    await expect(page.getByTestId("identity-error")).toContainText("unknown_user");
  });

  test("status filter narrows the list", async ({ page }) => {
    await waitForIdentity(page, "admin");
    await expect(page.getByText("Morgan Lee")).toBeVisible();
    await expect(page.getByText("Jordan Rivera")).toBeVisible();

    await page.getByTestId("filter-status").selectOption("in_progress");
    // Only Morgan Lee has the in_progress seed. (Jordan starts at review_needed.)
    await expect(page.getByText("Morgan Lee")).toBeVisible();
    await expect(page.getByText("Jordan Rivera")).toHaveCount(0);
  });
});
