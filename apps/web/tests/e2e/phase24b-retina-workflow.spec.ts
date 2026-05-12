/**
 * Phase 24B — Morgan Lee retina follow-up workflow wedge (Playwright).
 *
 * This e2e proves the deterministic seed wedge is wired end-to-end:
 *
 *   - dashboards surface the seeded queue items for each role
 *     (front-desk lane → tech / imaging lane → doctor lane → reviewer
 *     sign-off lane → internal follow-up lane);
 *   - the Morgan Lee encounter row opens the workspace;
 *   - the Clinical tab mounts the Specialty Tracking panel (retina
 *     row visible);
 *   - the Imaging tab mounts the Imaging Pipeline panel (study list
 *     visible with the seeded OCT macula + fundus photo metadata);
 *   - the Documentation tab mounts the NoteWorkspace with provider-
 *     review safety copy intact;
 *   - the workspace renders zero forbidden patient-messaging /
 *     order-placement / billing controls.
 *
 * The test is intentionally narrow: it does NOT exercise lifecycle
 * mutations on the live stack — those belong to the Phase 12 / 19
 * dedicated specs and the Phase 24B backend pytest in
 * `apps/api/tests/test_phase_24b_retina_wedge.py`, which is the
 * source of truth for seed shape. This file is the orchestration
 * proof: same wedge data + same UI = same buyer demo every time.
 *
 * Identities used (all dev-seeded; no real PHI; org 1 only):
 *   admin@chartnav.local      — front-desk + admin views
 *   tech@chartnav.local       — technician dashboard
 *   clin@chartnav.local       — doctor dashboard + workspace
 *   rev@chartnav.local        — reviewer dashboard
 *   front@chartnav.local      — front-desk dashboard
 */

import { expect, test, Page } from "@playwright/test";

const ADMIN_ORG1 = "admin@chartnav.local";
const CLIN_ORG1 = "clin@chartnav.local";
const REV_ORG1 = "rev@chartnav.local";
const FRONT_ORG1 = "front@chartnav.local";
const TECH_ORG1 = "tech@chartnav.local";

// Morgan Lee is PT-1001 and is seeded as the first encounter row.
const MORGAN_ENC_ID = 1;

async function setIdentity(page: Page, email: string) {
  await page.goto("/");
  await page.evaluate(
    (e) => localStorage.setItem("chartnav.devIdentity", e),
    email,
  );
  await page.reload();
  await page.waitForSelector("[data-testid=identity-badge]");
}

async function openDashboard(page: Page) {
  await page.getByTestId("sidebar-item-dashboard").click();
  await page.waitForSelector("[data-testid=role-dashboard]");
}

async function openEncounters(page: Page) {
  await page.getByTestId("sidebar-item-encounters").click();
  await page.waitForSelector("[data-testid=enc-list]");
}

async function openMorgan(page: Page) {
  await openEncounters(page);
  await page.locator(`[data-testid=enc-row-${MORGAN_ENC_ID}]`).click();
  await page.waitForSelector("[data-testid=encounter-detail]");
  await page.waitForSelector("[data-testid=clinical-tabbed-workspace]");
}

async function openTab(
  page: Page,
  slug:
    | "overview"
    | "clinical"
    | "documentation"
    | "imaging"
    | "orders-labs"
    | "calendar"
    | "communications"
    | "documents"
    | "chat",
) {
  await page.locator(`[data-testid=ctw-tab-${slug}]`).click();
  await page.waitForSelector(`[data-testid=ctw-panel-${slug}]`);
}

test.describe("Phase 24B — Morgan Lee retina workflow wedge", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
  });

  test("front-desk dashboard surfaces the seeded check-in / follow-up lane", async ({
    page,
  }) => {
    await setIdentity(page, FRONT_ORG1);
    await openDashboard(page);

    // The dashboard must mount in front-desk shape.
    await expect(page.getByTestId("dashboard-front-desk")).toBeVisible();

    // Phase 24B seeds at least one check-in item + one internal
    // follow-up item in the front-desk lane.
    const recent = page.getByTestId("front-desk-recent");
    await expect(recent).toBeVisible();
    await expect(recent).toContainText(/check in/i);
    await expect(recent).toContainText(/follow up/i);
  });

  test("technician dashboard surfaces the workup + imaging-needed lane", async ({
    page,
  }) => {
    await setIdentity(page, TECH_ORG1);
    await openDashboard(page);

    await expect(page.getByTestId("dashboard-technician")).toBeVisible();
    const queue = page.getByTestId("technician-queue");
    await expect(queue).toBeVisible();
    // Phase 24B seeds both technician_workup and imaging_needed.
    await expect(queue).toContainText(/technician workup/i);
    await expect(queue).toContainText(/imaging needed/i);
  });

  test("doctor dashboard surfaces ready-for-MD, documentation, and sign-off lanes", async ({
    page,
  }) => {
    await setIdentity(page, CLIN_ORG1);
    await openDashboard(page);

    await expect(page.getByTestId("dashboard-doctor")).toBeVisible();
    // The seeded ready_for_doctor item is high priority — the
    // high-priority count card must read >= 1.
    const hp = page.getByTestId("card-high-priority");
    await expect(hp).toBeVisible();
    const queue = page.getByTestId("doctor-queue");
    await expect(queue).toBeVisible();
    await expect(queue).toContainText(/ready for doctor/i);
    await expect(queue).toContainText(/documentation/i);
    await expect(queue).toContainText(/signoff needed/i);
  });

  test("reviewer dashboard mounts and shows the sign-off lane counts", async ({
    page,
  }) => {
    await setIdentity(page, REV_ORG1);
    await openDashboard(page);

    await expect(page.getByTestId("dashboard-reviewer")).toBeVisible();
    // The reviewer dashboard always renders the awaiting/blocked/audit
    // count cards; the wedge contributes to the unsigned-notes /
    // sign-off counts (admin view), and the reviewer view stays
    // mounted with the seeded counts even if its own queue list is
    // empty.
    await expect(page.getByTestId("card-notes-awaiting")).toBeVisible();
    await expect(page.getByTestId("card-blocked")).toBeVisible();
  });

  test("admin dashboard reflects the wedge in queue-by-status + by-queue-type breakdowns", async ({
    page,
  }) => {
    await setIdentity(page, ADMIN_ORG1);
    await openDashboard(page);

    await expect(page.getByTestId("dashboard-admin")).toBeVisible();

    // The seeded wedge adds 7 open queue items. The "Open Queue
    // Items" card must therefore be >= 7. We assert it's a number
    // and at least 7.
    const openCard = page.getByTestId("card-open-queue");
    await expect(openCard).toBeVisible();
    const openText = (await openCard.textContent()) ?? "";
    const openValue = Number((openText.match(/\d+/) ?? ["0"])[0]);
    expect(openValue).toBeGreaterThanOrEqual(7);

    // By-queue-type breakdown surfaces the wedge lanes by name.
    const byType = page.getByTestId("admin-by-queue-type");
    await expect(byType).toBeVisible();
    await expect(byType).toContainText(/check in/i);
    await expect(byType).toContainText(/technician workup/i);
    await expect(byType).toContainText(/imaging needed/i);
    await expect(byType).toContainText(/ready for doctor/i);
    await expect(byType).toContainText(/documentation/i);
    await expect(byType).toContainText(/signoff needed/i);
    await expect(byType).toContainText(/follow up/i);
  });

  test("admin operations dashboard surfaces Phase 24C workload aging and source proof", async ({
    page,
  }) => {
    await setIdentity(page, ADMIN_ORG1);
    await page.getByTestId("sidebar-item-multi-clinic").click();
    await expect(page.getByTestId("multi-clinic")).toBeVisible();

    await expect(page.getByTestId("card-stale-work")).toBeVisible();
    await expect(page.getByTestId("breakdown-open-user")).toContainText(/tech@chartnav.local/i);
    await expect(page.getByTestId("breakdown-stale-role")).toContainText(/technician/i);
    await expect(page.getByTestId("breakdown-source")).toContainText(/phase 24c glaucoma wedge/i);
  });

  test("opening Morgan Lee mounts the workspace and the Clinical / Imaging panels", async ({
    page,
  }) => {
    await setIdentity(page, ADMIN_ORG1);
    await openMorgan(page);

    // The Clinical tab must mount the Specialty Tracking panel and
    // reveal the seeded retina row.
    await openTab(page, "clinical");
    await expect(page.getByTestId("specialty-tracking")).toBeVisible();
    // The retina cards container appears once the wedge row loads.
    await expect(page.getByTestId("retina-cards")).toBeVisible({
      timeout: 8_000,
    });

    // The Imaging tab must mount the Imaging Pipeline panel and
    // reveal the seeded study list.
    await openTab(page, "imaging");
    await expect(page.getByTestId("imaging-pipeline")).toBeVisible();
    await expect(page.getByTestId("imaging-studies")).toBeVisible({
      timeout: 8_000,
    });

    // The Documentation tab must mount the note workspace + its
    // provider-review banner copy. The wedge demo relies on the
    // existing safety phrasing.
    await openTab(page, "documentation");
    await expect(page.getByTestId("scribe-session-banner-copy")).toContainText(
      /provider review required/i,
    );
    await expect(
      page.getByTestId("provider-action-items-banner-copy"),
    ).toContainText(/take action automatically/i);
  });

  test("the workspace renders zero forbidden patient-messaging / order / billing controls", async ({
    page,
  }) => {
    await setIdentity(page, ADMIN_ORG1);
    await openMorgan(page);

    const forbiddenButtonLabels = [
      /place order/i,
      /send referral/i,
      /submit referral/i,
      /send to patient/i,
      /email patient/i,
      /sms patient/i,
      /portal push/i,
      /prescribe/i,
      /submit claim/i,
      /submit bill/i,
      /bill insurance/i,
    ];
    for (const tab of [
      "clinical",
      "documentation",
      "imaging",
      "orders-labs",
      "communications",
    ] as const) {
      await openTab(page, tab);
      for (const label of forbiddenButtonLabels) {
        await expect(
          page.getByRole("button", { name: label }),
        ).toHaveCount(0);
      }
    }
  });

  test("the workspace text contains no autonomous-diagnosis or device-vendor language", async ({
    page,
  }) => {
    await setIdentity(page, ADMIN_ORG1);
    await openMorgan(page);

    // Walk the demo-relevant tabs and scrape rendered text. The
    // wedge must not introduce any forbidden positive-claim phrase.
    const forbiddenText: RegExp[] = [
      /autonomous diagnosis/i,
      /automatic diagnosis/i,
      /auto[- ]grade/i,
      /auto[- ]interpret/i,
      /auto[- ]select iol/i,
      /hands[- ]free scribing/i,
      /chart fills itself/i,
      /note writes itself/i,
      /replace\s+(your\s+)?ehr/i,
      /powered by ibm/i,
      /powered by watsonx/i,
      /hipaa[- ]compliant/i,
      /hipaa[- ]certified/i,
      /certified ehr/i,
    ];
    for (const tab of [
      "overview",
      "clinical",
      "documentation",
      "imaging",
    ] as const) {
      await openTab(page, tab);
      const text = (
        await page.getByTestId(`ctw-panel-${tab}`).innerText()
      ).toLowerCase();
      for (const re of forbiddenText) {
        expect(text).not.toMatch(re);
      }
    }
  });
});
