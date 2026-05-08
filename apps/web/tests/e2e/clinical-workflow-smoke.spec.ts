/**
 * Phase 12 — End-to-end clinical workflow smoke (Playwright).
 *
 * Drives the real frontend against the real backend stack booted by
 * playwright.config.ts (API on :8001, web on :5174). The goal is
 * narrow: confirm the major clinical panels mount inside the
 * workspace, surface their provider-review safety copy, and never
 * render a forbidden order/coding/referral/patient-message control.
 *
 * This file does NOT exercise full lifecycle clicks against the
 * live stack — that is the job of the dedicated panel/integration
 * specs and the backend integration test in Phase 12B. The smoke
 * stays deterministic by reading the rendered DOM against a fresh
 * seeded encounter row.
 */

import { expect, test } from "@playwright/test";

const ADMIN = "admin@chartnav.local";

async function useIdentity(
  page: import("@playwright/test").Page,
  email: string
) {
  await page.goto("/");
  await page.waitForSelector("[data-testid=identity-badge]");
  // Seed identity is stored in localStorage; set it + reload so the
  // app picks up the new caller (matches existing e2e convention).
  await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
  await page.reload();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openEncounter(
  page: import("@playwright/test").Page,
  id: number
) {
  await page.locator(`[data-testid=enc-row-${id}]`).click();
  await page.waitForSelector("[data-testid=encounter-detail]");
  // Phase 19 — encounter detail is now a tabbed workspace; the
  // NoteWorkspace lives behind the Documentation tab and the
  // EyeDiagramPanel behind the Imaging tab. The default active
  // tab is Overview, so we no longer wait for `note-workspace`
  // to be present at openEncounter time.
  await page.waitForSelector("[data-testid=clinical-tabbed-workspace]");
}

/**
 * Phase 19 helper — click a workspace tab + wait for its panel.
 */
async function openTab(
  page: import("@playwright/test").Page,
  slug:
    | "overview"
    | "clinical"
    | "documentation"
    | "imaging"
    | "orders-labs"
    | "calendar"
    | "communications"
    | "documents"
    | "chat"
    | "billing"
) {
  await page.locator(`[data-testid=ctw-tab-${slug}]`).click();
  await page.waitForSelector(`[data-testid=ctw-panel-${slug}]`);
}

test.describe("Clinical workflow smoke — Phase 12", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
  });

  test("every clinical panel section mounts on a patient encounter", async ({
    page,
  }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    // The five Phase 5B / 8 / 9 / 10 / 11 panels each gate on a
    // numeric patientId resolved from the encounter row. The seeded
    // encounter (PT-1001) has a native patient_id, so all five
    // sections should render — but they live behind Phase 19 tabs.
    // Imaging tab — the eye-diagram panel.
    await openTab(page, "imaging");
    await expect(page.getByTestId("eye-diagram-section")).toBeVisible();

    // Documentation tab — the scribe / summary / brief / action
    // items panels (all inside NoteWorkspace).
    await openTab(page, "documentation");
    await expect(page.getByTestId("scribe-session-section")).toBeVisible();
    await expect(page.getByTestId("patient-summary-section")).toBeVisible();
    await expect(page.getByTestId("pre-visit-brief-section")).toBeVisible();
    await expect(
      page.getByTestId("provider-action-items-section")
    ).toBeVisible();
  });

  test("each panel surfaces its provider-review safety copy", async ({
    page,
  }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    // Phase 19 — banner copy lives inside NoteWorkspace, which
    // mounts in the Documentation tab.
    await openTab(page, "documentation");

    await expect(
      page.getByTestId("scribe-session-banner-copy")
    ).toContainText(/provider review required/i);
    await expect(
      page.getByTestId("patient-summary-banner-copy")
    ).toContainText(/Do not send to patient/i);
    await expect(
      page.getByTestId("pre-visit-brief-banner-copy")
    ).toContainText(/may be incomplete/i);
    await expect(
      page.getByTestId("provider-action-items-banner-copy")
    ).toContainText(/take action automatically/i);
  });

  test("no forbidden action button is rendered in the workspace", async ({
    page,
  }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    // Phase 19 — open Documentation tab so the action-items panel
    // is mounted; then sweep the entire workspace (including all
    // visible chrome) for forbidden button labels. The forbidden
    // labels must not appear on ANY interactive control regardless
    // of which tab is active, so we also visit Labs/Orders Review
    // and Communications and re-check.
    await openTab(page, "documentation");
    await page.waitForSelector("[data-testid=provider-action-items-panel]");

    const forbiddenLabels = [
      /place order/i,
      /send referral/i,
      /submit referral/i,
      /send to patient/i,
      /email patient/i,
      /sms patient/i,
      /portal push/i,
      /prescribe/i,
    ];
    for (const tab of ["documentation", "orders-labs", "communications", "billing"] as const) {
      await openTab(page, tab);
      for (const label of forbiddenLabels) {
        await expect(
          page.getByRole("button", { name: label })
        ).toHaveCount(0);
      }
    }
  });

  test("workspace text contains no autonomous-diagnosis or external-LLM language", async ({
    page,
  }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    // Phase 19 — open Documentation tab so NoteWorkspace mounts,
    // then scrape its rendered text.
    await openTab(page, "documentation");
    await page.waitForSelector(
      "[data-testid=provider-action-items-panel]"
    );

    const text = (
      await page.locator("[data-testid=note-workspace]").innerText()
    ).toLowerCase();
    expect(text).not.toMatch(/autonomous/);
    expect(text).not.toMatch(/openai|anthropic/);
    expect(text).not.toMatch(/external llm/);
    // GPT alone is too permissive; require word boundary so
    // unrelated words ("gpt-2", "gpt-4") would still match but
    // "encrypt" wouldn't.
    expect(text).not.toMatch(/\bgpt[- ]?\d/);
  });
});
