import { expect, test, Page } from "@playwright/test";

/**
 * Phase 48 — enterprise control-plane wave 2 Playwright smoke.
 *
 * Verifies the admin Security tab renders the policy, audit sink,
 * and sessions blocks against the seeded backend. Walks the
 * policy-save path end-to-end so we catch serialization / route
 * wiring / audit-row regressions the moment they land.
 */

const ADMIN = "admin@chartnav.local";

async function login(page: Page, email: string) {
  await page.goto("/");
  await page.waitForSelector("[data-testid=identity-badge]");
  await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
  await page.reload();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openSecurityTab(page: Page) {
  await page.getByTestId("open-admin-panel").click();
  await page.getByTestId("admin-tab-security").click();
  await page.waitForSelector("[data-testid=security-pane]");
}

test.describe("Security control plane", () => {
  test("renders policy, audit sink, and sessions blocks", async ({ page }) => {
    await login(page, ADMIN);
    await openSecurityTab(page);
    await expect(page.getByTestId("sec-require-mfa")).toBeVisible();
    await expect(page.getByTestId("sec-sink-mode")).toBeVisible();
    await expect(page.getByTestId("sec-refresh-sessions")).toBeVisible();
  });

  test("admin saves a policy change end-to-end", async ({ page }) => {
    await login(page, ADMIN);
    await openSecurityTab(page);
    await page.getByTestId("sec-require-mfa").check();
    await page.getByTestId("sec-idle-timeout").fill("30");
    await page.getByTestId("sec-save-policy").click();
    await expect(page.getByTestId("sec-banner")).toContainText(/updated/i);
  });

  test("sink probe runs against the live backend", async ({ page }) => {
    await login(page, ADMIN);
    await openSecurityTab(page);
    await page.getByTestId("sec-probe-sink").click();
    // Default sink is disabled → detail confirms nothing dispatched.
    await expect(page.getByTestId("sec-sink-probe-value")).toContainText(/ok/i);
  });
});
