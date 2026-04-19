import { expect, test } from "@playwright/test";

/**
 * Phase 28 — clinician Quick Comments wedge.
 *
 * Drives one focused happy-path through a real browser against the
 * Playwright-managed backend (port 8001 / web 5174, seeded SQLite).
 * Scope is deliberately narrow:
 *
 *   clinician signs in → opens a seeded encounter → ingests a
 *   tiny transcript so a draft exists → opens Quick Comments panel
 *   → clicks a preloaded pick → asserts it lands in the draft.
 *
 * Deeper coverage (cursor-position splice, favorites idempotency,
 * usage-audit event shape) lives in the Vitest + Pytest suites
 * where the HTTP + DOM seams are isolated. This spec is here to
 * prove the full cross-stack wiring actually works end-to-end.
 */

const CLINICIAN = "clin@chartnav.local";

async function useIdentity(
  page: import("@playwright/test").Page,
  email: string
) {
  await page.goto("/");
  await page.waitForSelector("[data-testid=identity-badge]");
  await page.evaluate(
    (e) => localStorage.setItem("chartnav.devIdentity", e),
    email
  );
  await page.reload();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openEncounter(
  page: import("@playwright/test").Page,
  id: number
) {
  await page.locator(`[data-testid=enc-row-${id}]`).click();
  await page.waitForSelector("[data-testid=encounter-detail]");
  await page.waitForSelector("[data-testid=note-workspace]");
}

test.describe("NoteWorkspace — quick comments", () => {
  test("clinician clicks a preloaded quick comment and the body appears in the draft", async ({ page }) => {
    await useIdentity(page, CLINICIAN);
    await openEncounter(page, 1);

    // Ingest a minimal transcript so a draft exists to insert into.
    const transcript = [
      "Chief complaint: blurry right eye.",
      "OD 20/40, OS 20/20.",
      "IOP 15/17.",
      "Diagnosis: cataract.",
      "Plan: refer for surgery.",
      "Follow-up in 4 weeks.",
    ].join("\n");
    await page.getByTestId("transcript-ingest-textarea").fill(transcript);
    await page.getByTestId("transcript-ingest-submit").click();
    await page.getByTestId("generate-draft").click({ timeout: 15_000 });

    // The draft textarea should now be editable.
    const draft = page.getByTestId("note-draft-textarea");
    await expect(draft).toBeVisible();

    // Quick Comments panel is rendered for clinicians with the
    // clinician-entered trust pill visible.
    const panel = page.getByTestId("quick-comments-panel");
    await expect(panel).toBeVisible();
    await expect(panel).toContainText(/clinician-entered/i);

    // Click the first preloaded pick.
    const pick = page.getByTestId("quick-comment-sx-01");
    await pick.click();

    await expect(draft).toContainText("Vision stable since last visit.");
  });
});
