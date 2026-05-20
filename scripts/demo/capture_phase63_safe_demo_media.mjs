#!/usr/bin/env node
// Phase 63 — safe demo media capture (Playwright headed).
//
// Drives the local ChartNav dev stack on the iMac and records the
// eight safe demo clips defined in
// docs/demo/phase-63-safe-website-video-plan.md. Captures real .webm
// files into artifacts/phase-63/video-clips/ and screenshot posters
// into artifacts/phase-63/screenshots/.
//
// SAFETY:
//   - fake demo data only (Morgan Lee, PT-1001, seeded by
//     apps/api/scripts_seed.py).
//   - CHARTNAV_ENV=local; deterministic stub provider.
//   - no real PHI on camera, no real vendor keys, no production LLM.
//   - the script refuses to run if CHARTNAV_ENV is production /
//     staging / controlled-pilot, or if real-PHI gates are on.
//
// USAGE (operator, on the iMac, in a separate terminal from the
// running api + web):
//   cd "$CHARTNAV_REPO_PATH"
//   node scripts/demo/capture_phase63_safe_demo_media.mjs
//
// The script targets http://localhost:5173 by default. Override
// with PHASE63_BASE_URL=http://localhost:5174 if you're using the
// Playwright-managed stack.
//
// If a clip's capture path errors out, the script keeps going and
// reports the failure at the end. Each clip is independent.

import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const ARTIFACTS = path.join(REPO_ROOT, "artifacts/phase-63");
const VIDEO_DIR = path.join(ARTIFACTS, "video-clips");
const SHOT_DIR = path.join(ARTIFACTS, "screenshots");
const DRY_RUN_DIR = path.join(ARTIFACTS, "dry-run");

const BASE = process.env.PHASE63_BASE_URL || "http://localhost:5173";
const CLINICIAN = "clin@chartnav.local";
const TECHNICIAN = "tech@chartnav.local";
const VIEWPORT = { width: 1440, height: 900 };

function refuseUnsafeEnv() {
  const envName = process.env.CHARTNAV_ENV || "local";
  if (["production", "staging", "controlled-pilot"].includes(envName)) {
    console.error(`ERROR: refusing to run capture on CHARTNAV_ENV=${envName}`);
    process.exit(3);
  }
  if (process.env.CHARTNAV_LLM_ENABLED === "1") {
    console.error("ERROR: CHARTNAV_LLM_ENABLED=1 is not allowed for capture.");
    process.exit(4);
  }
  if (
    process.env.CHARTNAV_LLM_REAL_PHI_APPROVED === "1" ||
    process.env.CHARTNAV_REAL_PHI_ENABLED === "1"
  ) {
    console.error("ERROR: real-PHI gates are on; refusing to capture.");
    process.exit(4);
  }
}

function ensureDirs() {
  for (const d of [VIDEO_DIR, SHOT_DIR, DRY_RUN_DIR]) {
    fs.mkdirSync(d, { recursive: true });
  }
}

async function newRecordingContext(browser, clipBaseName) {
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: VIDEO_DIR, size: VIEWPORT },
  });
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  return { ctx, page };
}

async function setIdentity(page, email) {
  await page.evaluate((e) => {
    try { localStorage.setItem("chartnav.devIdentity", e); } catch {}
  }, email);
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
}

async function openMorganLeeEncounter(page) {
  // Encounter 1 = Morgan Lee per scripts_seed.py.
  await page.goto(`${BASE}/?encounter=1`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
}

async function clickTab(page, label) {
  // The tab bar lives at role="tablist". Tabs are role="tab".
  const tab = page.getByRole("tab", { name: label, exact: false });
  if (await tab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await tab.click();
    await page.waitForTimeout(1200);
    return true;
  }
  console.warn(`  warn: tab '${label}' not visible`);
  return false;
}

async function safeClick(page, selector, label) {
  try {
    const el = page.locator(selector).first();
    if (await el.isVisible({ timeout: 3000 })) {
      await el.click();
      await page.waitForTimeout(800);
      return true;
    }
  } catch {}
  console.warn(`  warn: ${label} (${selector}) not clickable`);
  return false;
}

async function finalizeRecording(ctx, page, targetBase) {
  const png = path.join(SHOT_DIR, `${targetBase}.png`);
  try {
    await page.screenshot({ path: png, fullPage: false });
  } catch (e) {
    console.warn(`  warn: screenshot failed: ${e.message}`);
  }
  await page.close();
  // Playwright finalizes video on context close. Grab path before close.
  const video = page.video();
  await ctx.close();
  if (video) {
    const auto = await video.path();
    const target = path.join(VIDEO_DIR, `${targetBase}.webm`);
    try {
      fs.renameSync(auto, target);
    } catch (e) {
      console.warn(`  warn: rename ${auto} → ${target} failed: ${e.message}`);
    }
  }
}

const CLIPS = [
  {
    id: "01_workspace_orientation",
    title: "Workflow Workspace",
    identity: CLINICIAN,
    durationMs: 22_000,
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await page.waitForTimeout(3000);
      await clickTab(page, "Clinical / Ophthalmology");
      await page.waitForTimeout(2500);
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(2500);
      await clickTab(page, "Imaging");
      await page.waitForTimeout(2500);
      await clickTab(page, "Clinical / Ophthalmology");
      await page.waitForTimeout(2000);
    },
  },
  {
    id: "02_vitals_capture",
    title: "Technician Workup & Vitals",
    identity: TECHNICIAN,
    durationMs: 32_000,
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await clickTab(page, "Clinical / Ophthalmology");
      await safeClick(page, '[data-testid="vitals-demo-sample-btn"]', "Load fake demo vitals");
      await page.waitForTimeout(3500);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(2500);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(2500);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(2500);
    },
  },
  {
    id: "03_visitdraft_transcript_to_draft",
    title: "Provider-Reviewed VisitDraft Assist",
    identity: CLINICIAN,
    durationMs: 33_000,
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(2000);
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(1500);
      await safeClick(page, '[data-testid="ambient-sample-btn"]', "Load demo sample");
      await page.waitForTimeout(2000);
      await safeClick(page, '[data-testid="ambient-generate-btn"]', "Generate draft");
      await page.waitForTimeout(5000);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(3000);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(3000);
    },
  },
  {
    id: "04_visitdraft_signal_filter",
    title: "VisitDraft Signal Filter",
    identity: CLINICIAN,
    durationMs: 27_000,
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(2000);
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(1500);
      // Replace transcript with a fake mixed-content sample to show
      // the filter behaviour: small-talk + stated clinical facts.
      const textarea = page.locator('textarea').first();
      if (await textarea.isVisible({ timeout: 3000 }).catch(() => false)) {
        await textarea.fill(
          "Demo transcript only. How's the dog doing? Anyway, patient reports blurry vision in the right eye for two weeks. VA OD 20/40, OS 20/25. IOP 18 OD, 16 OS. Did you watch the game last night? No fundus photo today."
        );
        await page.waitForTimeout(2000);
      }
      await safeClick(page, '[data-testid="ambient-generate-btn"]', "Generate draft");
      await page.waitForTimeout(5000);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(3000);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(3000);
    },
  },
  {
    id: "05_fundus_drawing_assist",
    title: "Provider-Reviewed Fundus Drawing Assist",
    identity: CLINICIAN,
    durationMs: 28_000,
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await clickTab(page, "Imaging");
      await page.waitForTimeout(2000);
      await safeClick(page, '[data-testid="fundus-sample-OD"]', "Horseshoe tear chip");
      await page.waitForTimeout(2000);
      await safeClick(page, '[data-testid="fundus-generate-btn"]', "Generate Chart");
      await page.waitForTimeout(5000);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(3000);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(3000);
    },
  },
  {
    id: "06_doctor_review_signoff",
    title: "Doctor Review, Attestation, and Signed Lock",
    identity: CLINICIAN,
    durationMs: 35_000,
    // This clip narrates the Reviewed → attestation → Sign & Lock
    // flow on Vitals, VisitDraft, and Fundus. The script clicks
    // through the buttons that are present; if any are disabled
    // (e.g. the artefact has not yet been generated in this fresh
    // session), the operator can re-run scripts/reset_demo_state.sh
    // and try again, or capture this clip manually.
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await clickTab(page, "Clinical / Ophthalmology");
      await page.waitForTimeout(2500);
      await safeClick(page, '[data-testid="vitals-sign-btn"]', "Sign & Lock Workup");
      await page.waitForTimeout(2500);
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(2500);
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(1500);
      await safeClick(page, '[data-testid="ambient-sign-btn"]', "Sign & Lock Draft");
      await page.waitForTimeout(2500);
      await clickTab(page, "Imaging");
      await page.waitForTimeout(2500);
      await safeClick(page, '[data-testid="fundus-sign-btn"]', "Sign & Lock Chart");
      await page.waitForTimeout(2500);
    },
  },
  {
    id: "07_safety_posture",
    title: "What ChartNav Did Not Do",
    identity: CLINICIAN,
    durationMs: 25_000,
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await clickTab(page, "Clinical / Ophthalmology");
      await page.waitForTimeout(2000);
      // Try to scroll the "What ChartNav did NOT do" card into view
      // on Vitals.
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(3500);
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(2000);
      await page.evaluate(() => window.scrollBy(0, 1200));
      await page.waitForTimeout(4000);
      // Reset scroll and pan around safety banners.
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(3000);
    },
  },
  {
    id: "08_three_minute_highlight_reel",
    title: "ChartNav Controlled Demo Highlight Reel",
    identity: CLINICIAN,
    durationMs: 180_000,
    // This is a compressed re-walk of all 7 prior clips. Plays
    // back through workspace → vitals → visitdraft → fundus →
    // sign-off → safety posture in ~3 min. Capture is best-effort;
    // if any sub-step fails the script logs a warning and continues
    // (the highlight reel is the most fragile to capture because
    // it depends on prior surfaces being in the right state).
    drive: async (page) => {
      await openMorganLeeEncounter(page);
      await page.waitForTimeout(5000);
      await clickTab(page, "Clinical / Ophthalmology");
      await page.waitForTimeout(4000);
      await safeClick(page, '[data-testid="vitals-demo-sample-btn"]', "Load fake demo vitals");
      await page.waitForTimeout(5000);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(4000);
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(3000);
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(2000);
      await safeClick(page, '[data-testid="ambient-sample-btn"]', "Load demo sample");
      await page.waitForTimeout(2000);
      await safeClick(page, '[data-testid="ambient-generate-btn"]', "Generate draft");
      await page.waitForTimeout(8000);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(5000);
      await clickTab(page, "Imaging");
      await page.waitForTimeout(3000);
      await safeClick(page, '[data-testid="fundus-sample-OD"]', "Horseshoe tear chip");
      await page.waitForTimeout(2000);
      await safeClick(page, '[data-testid="fundus-generate-btn"]', "Generate Chart");
      await page.waitForTimeout(6000);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(4000);
      // Closing panel: safety posture
      await clickTab(page, "Documentation / EMR/EHR");
      await page.waitForTimeout(3000);
      await page.evaluate(() => window.scrollBy(0, 1500));
      await page.waitForTimeout(8000);
    },
  },
];

async function main() {
  refuseUnsafeEnv();
  ensureDirs();

  console.log(`Phase 63 capture starting. base=${BASE} viewport=${VIEWPORT.width}x${VIEWPORT.height}`);
  console.log(`videos → ${VIDEO_DIR}`);
  console.log(`shots  → ${SHOT_DIR}`);

  const browser = await chromium.launch({ headless: false });
  const results = [];
  for (const clip of CLIPS) {
    console.log(`\n[${clip.id}] ${clip.title}`);
    const start = Date.now();
    let { ctx, page } = await newRecordingContext(browser, clip.id);
    try {
      await setIdentity(page, clip.identity);
      // Run the clip's capture path with a soft timeout so a stuck
      // selector doesn't blow up the whole run.
      const driveTimeout = clip.durationMs + 15_000;
      await Promise.race([
        clip.drive(page),
        new Promise((_, rej) =>
          setTimeout(() => rej(new Error("drive timeout")), driveTimeout)
        ),
      ]);
      // Pad to roughly the declared duration so the .webm is not
      // truncated mid-frame.
      const elapsed = Date.now() - start;
      const pad = Math.max(0, clip.durationMs - elapsed);
      if (pad > 0) await page.waitForTimeout(Math.min(pad, 15_000));
      await finalizeRecording(ctx, page, clip.id);
      const webm = path.join(VIDEO_DIR, `${clip.id}.webm`);
      const png = path.join(SHOT_DIR, `${clip.id}.png`);
      results.push({
        id: clip.id,
        title: clip.title,
        webm_exists: fs.existsSync(webm),
        png_exists: fs.existsSync(png),
        error: null,
      });
      console.log(`  ok webm=${fs.existsSync(webm)} png=${fs.existsSync(png)}`);
    } catch (e) {
      console.error(`  FAIL ${clip.id}: ${e.message}`);
      try { await finalizeRecording(ctx, page, clip.id); } catch {}
      results.push({
        id: clip.id,
        title: clip.title,
        webm_exists: fs.existsSync(path.join(VIDEO_DIR, `${clip.id}.webm`)),
        png_exists: fs.existsSync(path.join(SHOT_DIR, `${clip.id}.png`)),
        error: e.message,
      });
    }
  }

  await browser.close();

  // Append a summary the operator can paste into the dated dry-run
  // folder.
  const summary = {
    base_url: BASE,
    viewport: VIEWPORT,
    started_at: new Date().toISOString(),
    safety: {
      chartnav_env: process.env.CHARTNAV_ENV || "local",
      llm_enabled: process.env.CHARTNAV_LLM_ENABLED || "0",
      real_phi_approved: process.env.CHARTNAV_LLM_REAL_PHI_APPROVED || "0",
      provider: process.env.CHARTNAV_LLM_PROVIDER || "deterministic_stub",
    },
    clips: results,
  };
  const stamp = new Date().toISOString().slice(0, 10);
  const out = path.join(DRY_RUN_DIR, `${stamp}-capture-summary.json`);
  fs.writeFileSync(out, JSON.stringify(summary, null, 2));
  console.log(`\nsummary → ${out}`);

  const failed = results.filter((r) => !r.webm_exists);
  if (failed.length > 0) {
    console.error(`\n${failed.length} clip(s) without .webm:`);
    for (const f of failed) console.error(`  - ${f.id}${f.error ? `: ${f.error}` : ""}`);
    process.exit(1);
  }
  console.log("\nall clips recorded.");
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
