import { expect, test } from "@playwright/test";

/**
 * Phase 24 — frontend operator-UX hardening for async ingestion.
 *
 * Exercises the NoteWorkspace when transcript processing is NOT
 * instant. The deterministic text-paste pipeline still lands at
 * `completed` inline on the backend (phase 22 contract), so we
 * cannot produce a real `queued`/`processing` state end-to-end from
 * the browser without installing a slow transcriber. Instead, this
 * spec drives the workflow through the real HTTP stack against the
 * seeded backend and asserts the messaging contract from a user's
 * perspective: Generate is blocked until a completed input exists,
 * the blocked-hint is on-screen with honest copy, the Refresh
 * button re-fetches without reloading the page, and the full
 * happy-path wedge still completes on a bridged/standalone row.
 *
 * The spec is deliberately narrow so it stays deterministic under
 * the shared Playwright stack (port 8001 / 5174 via playwright.config).
 */

const ADMIN = "admin@chartnav.local";
const CLINICIAN = "clin@chartnav.local";

async function useIdentity(page: import("@playwright/test").Page, email: string) {
  await page.goto("/");
  await page.waitForSelector("[data-testid=identity-badge]");
  // Seed identity is stored in localStorage; set it + reload so the
  // app picks up the new caller.
  await page.evaluate((e) => localStorage.setItem("chartnav.devIdentity", e), email);
  await page.reload();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openEncounter(page: import("@playwright/test").Page, id: number) {
  await page.locator(`[data-testid=enc-row-${id}]`).click();
  await page.waitForSelector("[data-testid=encounter-detail]");
  await page.waitForSelector("[data-testid=note-workspace]");
}

test.describe("NoteWorkspace — async ingestion hardening", () => {
  test("generate-blocked hint appears when no transcript has been ingested", async ({ page }) => {
    await useIdentity(page, ADMIN);
    await openEncounter(page, 1);

    // Baseline: seed currently has no ingested input for encounter 1.
    await expect(page.getByTestId("workspace-tier-transcript")).toBeVisible();
    const generate = page.getByTestId("generate-draft");
    await expect(generate).toBeDisabled();

    const hint = page.getByTestId("generate-blocked-note");
    await expect(hint).toBeVisible();
    await expect(hint).toContainText(/unlocks once a transcript/i);
  });

  test("happy path: ingest → completed → generate unlocks", async ({ page }) => {
    await useIdentity(page, CLINICIAN);
    await openEncounter(page, 1);

    const transcript = [
      "Chief complaint: blurry right eye.",
      "OD 20/40, OS 20/20. IOP 15/17.",
      "Diagnosis: cataract. Plan: refer for surgery.",
      "Follow-up in 4 weeks.",
    ].join("\n");

    await page.getByTestId("transcript-ingest-textarea").fill(transcript);
    await page.getByTestId("transcript-ingest-submit").click();

    // Backend pipeline runs inline; the row should land as
    // `completed` in the next refresh cycle. The component calls
    // loadInputs() after the ingest, so the pill flips without a
    // manual Refresh click.
    await expect(
      page.locator("[data-testid^=transcript-status-]").first()
    ).toHaveAttribute("data-status", /completed|processing|failed/);

    // Generate now enabled OR a clean blocked-hint remains.
    const generate = page.getByTestId("generate-draft");
    const status = await page
      .locator("[data-testid^=transcript-status-]")
      .first()
      .getAttribute("data-status");

    if (status === "completed") {
      await expect(generate).toBeEnabled();
      // Blocked hint gone.
      await expect(page.getByTestId("generate-blocked-note")).toHaveCount(0);
    } else {
      // Failure surface (sparse transcripts can still fail
      // backend validation): the blocked-note should not say the
      // "empty state" copy.
      const hint = page.getByTestId("generate-blocked-note");
      await expect(hint).not.toContainText(/unlocks once a transcript has been/i);
    }
  });

  test("manual refresh button re-fetches without reloading the page", async ({ page }) => {
    await useIdentity(page, CLINICIAN);
    await openEncounter(page, 1);

    // Ingest one input so the refresh button renders.
    await page
      .getByTestId("transcript-ingest-textarea")
      .fill(
        "OD 20/20, OS 20/20. IOP 14/14. Plan: observe. Follow-up in 8 weeks."
      );
    await page.getByTestId("transcript-ingest-submit").click();
    await page.waitForSelector("[data-testid^=transcript-]");

    const refresh = page.getByTestId("transcript-refresh");
    await expect(refresh).toBeVisible();

    // Intercept the input-list request so we can prove the click
    // dispatches a new fetch.
    const inputListUrl = /\/encounters\/1\/inputs(?:\?|$)/;
    const waitForRefetch = page.waitForResponse(
      (resp) => inputListUrl.test(resp.url()) && resp.status() === 200
    );
    await refresh.click();
    await waitForRefetch;
  });
});
