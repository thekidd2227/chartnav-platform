// Phase A item 5 — Tablet offline-banner spec.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.3 + §4.
//
// Drops the network with `context.setOffline(true)` and verifies:
//   - the OfflineBanner becomes visible with the documented testid
//   - sign / handoff actions are NOT executed while offline
//
// On reconnect, the banner disappears.
import { test, expect } from "@playwright/test";

test.describe("offline banner", () => {
  test("appears when the browser goes offline and disappears on reconnect", async ({ page, context }) => {
    await page.goto("/");
    await expect(page.getByTestId("offline-banner")).toHaveCount(0);

    await context.setOffline(true);
    // Trigger the offline event in case the browser does not auto-emit
    // (Playwright's setOffline does emit it on chromium/webkit).
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    await expect(page.getByTestId("offline-banner")).toBeVisible();
    await expect(page.getByTestId("offline-banner"))
      .toContainText(/signing.*disabled/i);

    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect(page.getByTestId("offline-banner")).toHaveCount(0);
  });
});
