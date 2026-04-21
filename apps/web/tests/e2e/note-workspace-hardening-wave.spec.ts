import { expect, test, Page } from "@playwright/test";

/**
 * ChartNav hardening wave — additional Playwright coverage for the
 * currently shipped transcript → findings → draft → signoff wedge
 * and the integrated/native encounter UX.
 *
 * Scope is deliberately narrow and deterministic. Every assertion
 * keys off stable `data-testid`s that already exist in the shipped
 * UI (phase 19–37 + wave-1). Fixtures come from the Playwright
 * webServer's seeded backend (see apps/api/scripts_seed.py) and
 * default standalone platform mode — no external-EHR adapter is
 * booted, so integrated-mode expectations are exercised via the
 * vitest suite, not here.
 */

const ADMIN = "admin@chartnav.local";
const CLINICIAN = "clin@chartnav.local";

async function useIdentity(page: Page, email: string) {
  await page.goto("/");
  await page.waitForSelector("[data-testid=identity-badge]");
  await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
  await page.reload();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openEncounter(page: Page, id: number) {
  await page.locator(`[data-testid=enc-row-${id}]`).click();
  await page.waitForSelector("[data-testid=encounter-detail]");
}

test.describe("ChartNav wedge hardening", () => {
  test("native encounter shows NoteWorkspace with all three trust tiers visible", async ({ page }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    // Native (standalone) → NoteWorkspace must mount and all three
    // tiers must be distinct DOM nodes; the external-blocked
    // section must NOT render for a native row.
    await expect(page.getByTestId("note-workspace")).toBeVisible();
    await expect(page.getByTestId("workspace-tier-transcript")).toBeVisible();
    await expect(page.getByTestId("workspace-tier-findings")).toBeVisible();
    await expect(page.getByTestId("workspace-tier-draft")).toBeVisible();
    await expect(
      page.getByTestId("note-workspace-external-note")
    ).toHaveCount(0);
  });

  test("native-encounter source chip reads ChartNav (native) and no external banner appears", async ({ page }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    const chip = page.getByTestId("detail-source-chip");
    await expect(chip).toBeVisible();
    await expect(chip).toHaveAttribute("data-source", "chartnav");
    await expect(chip).toContainText(/chartnav/i);
    await expect(
      page.getByTestId("external-encounter-banner")
    ).toHaveCount(0);
  });

  test("transcript status pill renders state + human-readable tooltip after ingest", async ({ page }) => {
    // Ingest a transcript via the shipped `transcript-ingest-*`
    // testids, then assert the status pill for the new input has a
    // human-readable `title` attribute (UI hardening contract —
    // state explanation on hover).
    await useIdentity(page, CLINICIAN);
    await openEncounter(page, 1);

    const textarea = page.getByTestId("transcript-ingest-textarea");
    await expect(textarea).toBeVisible();
    await textarea.fill(
      "Patient reports floaters OD. IOP 16/15. Anterior segment quiet. Posterior segment with attached retina."
    );
    await page.getByTestId("transcript-ingest-submit").click();

    // Text-paste pipeline lands at `completed` inline, so we can
    // reliably observe at least one transcript-status pill.
    const firstStatus = page.locator('[data-testid^="transcript-status-"]').first();
    await expect(firstStatus).toBeVisible({ timeout: 10_000 });
    // UI hardening contract: the pill carries a non-empty `title`
    // attribute with a human-readable state explanation.
    const title = await firstStatus.getAttribute("title");
    expect(title).toBeTruthy();
    expect((title ?? "").length).toBeGreaterThan(4);
  });

  test("trust tiers are visibly distinct — each tier has its own data-testid container", async ({ page }) => {
    await useIdentity(page, CLINICIAN);
    await openEncounter(page, 2);

    const t1 = page.getByTestId("workspace-tier-transcript");
    const t2 = page.getByTestId("workspace-tier-findings");
    const t3 = page.getByTestId("workspace-tier-draft");
    await expect(t1).toBeVisible();
    await expect(t2).toBeVisible();
    await expect(t3).toBeVisible();
    // DOM order contract: transcript → findings → draft, top to bottom.
    const t1Box = await t1.boundingBox();
    const t2Box = await t2.boundingBox();
    const t3Box = await t3.boundingBox();
    expect(t1Box && t2Box && t3Box).toBeTruthy();
    if (t1Box && t2Box && t3Box) {
      expect(t1Box.y).toBeLessThan(t2Box.y);
      expect(t2Box.y).toBeLessThan(t3Box.y);
    }
  });

  test("export action is not offered before a note is signed (export-before-sign guard)", async ({ page }) => {
    await useIdentity(page, CLINICIAN);
    await openEncounter(page, 1);

    // Before any draft exists, the export button must not be present.
    await expect(page.getByTestId("note-export")).toHaveCount(0);
    // The hardening hint surfaces once a draft is editable AND not
    // signed; on a fresh encounter it may not render either, which
    // is also correct — the point is: no export control before sign.
  });
});
