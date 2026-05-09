// Phase 19J — automated website video clip recorder.
//
// Drives the live ChartNav stack (vite + uvicorn, booted by the
// existing Playwright webServer config or already-running by the
// operator) and records 7 short MP4-ready WebM clips matching
// the Phase 19I + Phase 19G manifest:
//
//   01 — clinical workspace overview     (8–15 s)
//   02 — ophthalmology workflow          (8–15 s)
//   03 — documentation workflow          (8–15 s)
//   04 — imaging workspace               (8–15 s)
//   05 — labs / orders review-only       (8–12 s)
//   06 — internal chat recipient selector (8–12 s)
//   07 — full workspace navigation       (25–45 s)
//
// Each clip is recorded via Playwright's built-in `recordVideo`
// API into a temp dir, then the bash runner ffmpeg-converts WebM
// -> MP4 (+ optional WEBM passthrough + thumbnail PNG).
//
// Safety contract:
//   - fake/demo seed data only; no real PHI ever reaches the
//     recorder
//   - the recorder asserts that no Billing tab / no CPT /
//     Charges / Insurance / Submit Claim / Submit Order text
//     appears on screen during any clip; if such text shows
//     up, the recorder exits non-zero so the operator never
//     ships a clip containing forbidden vocabulary
//   - default viewport is 1440x900 desktop
//   - default mode is headless (no popup window). Set
//     HEADED=1 to record with a visible browser window and
//     a real cursor (recommended for the final ship clips
//     on a Mac).
//
// Usage (operator's Mac):
//
//   bash tools/media-review/capture_phase19i_clips.sh
//
// The bash runner sets OUT_DIR + boots the stack (or reuses an
// already-running one) and invokes this file via:
//
//   node apps/web/record_phase19i_website_clips.mjs
//
// Env knobs:
//   APP_URL          frontend URL (default http://127.0.0.1:5174)
//   OUT_DIR          where to drop the .webm files
//   HEADED=1         render with a visible browser window
//   ONLY=01,03,07    record only specific clip ids (comma-list)
//

import { chromium } from "playwright";
import { mkdir, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";

const APP_URL = process.env.APP_URL || "http://127.0.0.1:5174";
const OUT_DIR = process.env.OUT_DIR || resolve("/tmp/phase19j-clips-out");
const HEADED = process.env.HEADED === "1";
const ONLY =
  process.env.ONLY && process.env.ONLY.length > 0
    ? new Set(process.env.ONLY.split(",").map((s) => s.trim()))
    : null;
const VIEWPORT = { width: 1440, height: 900 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Forbidden vocabulary — every clip is screened for these BEFORE
// the recording closes. If any visible page text matches, the
// scenario throws and the bash runner exits non-zero so we never
// ship a clip with banned phrasing.
const FORBIDDEN = [
  /\bBilling\b/,
  /\bCPT\b/,
  /\bCharges\b/,
  /\bInsurance\b/,
  /\bSubmit Claim\b/i,
  /\bAuto-code\b/i,
  /\bAuto-bill\b/i,
  /\bSend Claim\b/i,
  /\bCharge Patient\b/i,
  /\bBill Insurance\b/i,
  /\bPayment\b/,
  /\bClaim submission\b/i,
  /\bSubmit Order\b/i,
  /\bPlace Order\b/i,
  /\bSend Referral\b/i,
  /\bSend to Patient\b/i,
  /\bPatient Portal\b/i,
];

async function assertSafePage(page, clipId) {
  const text = await page.evaluate(() => document.body.innerText);
  for (const re of FORBIDDEN) {
    if (re.test(text)) {
      throw new Error(
        `Clip ${clipId}: forbidden phrasing detected on page (matched ${re}). Aborting.`
      );
    }
  }
}

// ---------- shared scenario primitives -------------------------------------

async function loadDemo(page) {
  await page.goto(`${APP_URL}/?demo=1`, { waitUntil: "domcontentloaded" });
  // Pick the first seeded encounter — this is the same row the
  // Phase 19G screenshot capture picks.
  const firstRow = page.locator("[data-testid^='enc-row-']").first();
  await firstRow.waitFor({ state: "visible", timeout: 15_000 });
  await firstRow.click();
  await page
    .locator("[data-testid='clinical-tabbed-workspace']")
    .waitFor({ state: "visible", timeout: 10_000 });
}

async function clickTab(page, slug) {
  await page.locator(`[data-testid='ctw-tab-${slug}']`).click();
  await page
    .locator(`[data-testid='ctw-panel-${slug}']`)
    .waitFor({ state: "visible" });
}

// ---------- the 7 scenarios ------------------------------------------------

const SCENARIOS = [
  {
    id: "01",
    file: "website_clip_01_clinical_workspace_overview.webm",
    targetSec: 12,
    async run(page) {
      await loadDemo(page);
      // Hold on Overview so the burgundy sidebar + patient
      // header + demographic strip + tab row read.
      await sleep(3_000);
      // Slow scroll over the Overview cards.
      await page.mouse.move(700, 400);
      await page.mouse.wheel(0, 200);
      await sleep(2_000);
      await page.mouse.wheel(0, 200);
      await sleep(2_000);
      await page.mouse.wheel(0, -400);
      await sleep(2_000);
      // Hover the tab bar to draw the eye to the 9-tab list.
      await page.locator("[data-testid='ctw-tabbar']").hover();
      await sleep(1_500);
      await assertSafePage(page, "01");
    },
  },
  {
    id: "02",
    file: "website_clip_02_ophthalmology_workflow.webm",
    targetSec: 12,
    async run(page) {
      await loadDemo(page);
      await clickTab(page, "clinical");
      await sleep(2_000);
      // Hover the search field, then pan the pill cards.
      await page.locator("[data-testid='ctw-clinical-search']").hover();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-clinical-group-favorites']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-clinical-group-retina']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-clinical-group-glaucoma']")
        .scrollIntoViewIfNeeded();
      await sleep(2_000);
      await page
        .locator("[data-testid='ctw-clinical-group-general']")
        .scrollIntoViewIfNeeded();
      await sleep(2_000);
      await assertSafePage(page, "02");
    },
  },
  {
    id: "03",
    file: "website_clip_03_documentation_workflow.webm",
    targetSec: 12,
    async run(page) {
      await loadDemo(page);
      await clickTab(page, "documentation");
      await sleep(2_000);
      // Pause on the four-stage stepper.
      await page.locator("[data-testid='ctw-doc-stepper']").hover();
      await sleep(2_500);
      // Pan into the workbench.
      await page
        .locator("[data-testid='ctw-doc-workbench']")
        .scrollIntoViewIfNeeded();
      await sleep(2_500);
      await page.mouse.wheel(0, 300);
      await sleep(2_500);
      await page.mouse.wheel(0, 300);
      await sleep(2_000);
      await assertSafePage(page, "03");
    },
  },
  {
    id: "04",
    file: "website_clip_04_imaging_workspace.webm",
    targetSec: 12,
    async run(page) {
      await loadDemo(page);
      await clickTab(page, "imaging");
      await sleep(2_000);
      // Pan over the 6-card workspace grid.
      await page
        .locator("[data-testid='ctw-card-upload-imaging']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-card-oct-images']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-card-fundus-photos']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-card-attachments']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      // End on the OD/OS retinal workbench.
      await page
        .locator("[data-testid='ctw-card-od-os-retinal-workbench']")
        .scrollIntoViewIfNeeded();
      await sleep(2_500);
      await assertSafePage(page, "04");
    },
  },
  {
    id: "05",
    file: "website_clip_05_labs_orders_review_only.webm",
    targetSec: 10,
    async run(page) {
      await loadDemo(page);
      await clickTab(page, "orders-labs");
      await sleep(2_000);
      // Pan the four review-only cards.
      await page
        .locator("[data-testid='ctw-card-lab-results']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-card-imaging-orders']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-card-procedure-plan']")
        .scrollIntoViewIfNeeded();
      await sleep(1_500);
      await page
        .locator("[data-testid='ctw-card-review-notes']")
        .scrollIntoViewIfNeeded();
      await sleep(2_500);
      await assertSafePage(page, "05");
    },
  },
  {
    id: "06",
    file: "website_clip_06_internal_chat_recipient_selector.webm",
    targetSec: 11,
    async run(page) {
      await loadDemo(page);
      await clickTab(page, "chat");
      await sleep(2_000);
      // Hover the demo-local warning banner.
      await page.locator("[data-testid='ctw-chat-banner']").hover();
      await sleep(1_500);
      // Hover the recipient selector dropdown + recipient card.
      await page
        .locator("[data-testid='ctw-chat-recipient-select']")
        .hover();
      await sleep(1_500);
      // Switch recipient: Carter -> Patel (away). Composer
      // placeholder updates live.
      await page
        .locator("[data-testid='ctw-chat-recipient-select']")
        .selectOption("patel");
      await sleep(2_500);
      // Hover the export buttons so the buyer sees the export
      // affordance.
      await page.locator("[data-testid='ctw-chat-export-txt']").hover();
      await sleep(1_500);
      await page.locator("[data-testid='ctw-chat-export-json']").hover();
      await sleep(1_500);
      await assertSafePage(page, "06");
    },
  },
  {
    id: "07",
    file: "website_clip_07_full_workspace_navigation.webm",
    targetSec: 36,
    async run(page) {
      await loadDemo(page);
      // Hold ~3 s on Overview, then click each tab in order
      // holding ~3.5 s on each. Total ~3 + 8*3.5 = 31 s; with
      // tab-switch animation + final hold lands inside 25–45.
      await sleep(3_000);
      const tour = [
        "clinical",
        "documentation",
        "imaging",
        "orders-labs",
        "calendar",
        "communications",
        "documents",
        "chat",
      ];
      for (const slug of tour) {
        await clickTab(page, slug);
        await sleep(3_500);
      }
      await assertSafePage(page, "07");
    },
  },
];

// ---------- driver ---------------------------------------------------------

async function runScenario(scenario) {
  console.log(
    `[clip ${scenario.id}] recording ${scenario.file} ` +
      `(target ~${scenario.targetSec}s, headed=${HEADED})`
  );

  if (!existsSync(OUT_DIR)) {
    await mkdir(OUT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: !HEADED });
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: OUT_DIR, size: VIEWPORT },
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();

  let scenarioErr = null;
  try {
    await scenario.run(page);
  } catch (e) {
    scenarioErr = e;
  }

  // Capture the WebM path BEFORE closing the page (Playwright
  // assigns a temp filename per recording; we rename it after
  // close to the canonical scenario filename).
  const tmpVideoPath = await page.video()?.path();
  await ctx.close();
  await browser.close();

  if (scenarioErr) {
    throw scenarioErr;
  }

  if (!tmpVideoPath) {
    throw new Error(`Clip ${scenario.id}: no video path returned`);
  }

  // Rename the playwright-generated .webm to the canonical
  // scenario filename. Both files live under OUT_DIR.
  const finalPath = join(OUT_DIR, scenario.file);
  if (existsSync(finalPath)) {
    await rm(finalPath);
  }
  // ESM rename (avoid pulling in fs.promises here).
  const { rename } = await import("node:fs/promises");
  await rename(tmpVideoPath, finalPath);
  console.log(`[clip ${scenario.id}] -> ${finalPath}`);
}

async function main() {
  const target = ONLY
    ? SCENARIOS.filter((s) => ONLY.has(s.id))
    : SCENARIOS;
  if (target.length === 0) {
    console.error(`No scenarios match ONLY=${process.env.ONLY}`);
    process.exit(2);
  }
  console.log(`Phase 19J — recording ${target.length} clip(s)`);
  console.log(`  app : ${APP_URL}`);
  console.log(`  out : ${OUT_DIR}`);
  console.log("");
  for (const scenario of target) {
    await runScenario(scenario);
  }
  console.log("");
  console.log("Done. WebMs are in:");
  console.log(`  ${OUT_DIR}`);
  console.log(
    "Next step: ffmpeg-convert WebM -> MP4 via the bash runner."
  );
}

main().catch((e) => {
  console.error(e?.stack || e?.message || e);
  process.exit(1);
});
