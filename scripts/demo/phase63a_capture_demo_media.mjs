#!/usr/bin/env node
/*
 * scripts/demo/phase63a_capture_demo_media.mjs
 * ────────────────────────────────────────────
 * Phase 63A — fully-automated capture of every required ChartNav buyer-demo
 * screenshot AND video.
 *
 * What it does:
 *   - Loads @playwright/test from apps/web/node_modules (no new deps).
 *   - Opens 12 scoped Playwright contexts (one per video) at 1440x900 chromium.
 *   - Sets demo identity via localStorage["chartnav.devIdentity"] = clin@chartnav.local.
 *     Backend uses header auth (X-User-Email) — the React app reads localStorage
 *     and sends the header automatically.
 *   - Drives each scene through the actual demo workspace (no fake media).
 *   - Saves PNGs under artifacts/phase-62/screenshots/ with required filenames.
 *   - Saves one .webm per scene under artifacts/phase-62/video-clips/ with the
 *     required filenames (Playwright outputs webm; required spec accepts
 *     mov|webm|mp4 so we leave as .webm).
 *   - For shots 26–28 + clip 11: runs safety scripts via child_process, renders
 *     output to a local HTML page, then screenshots it.
 *   - For shots 29–30: renders existing markdown docs to a local HTML page,
 *     then screenshots it.
 *   - Records a final 12th video — a continuous "highlight reel" walk-through.
 *   - Writes a JSON manifest summary at the end.
 *
 * What it does NOT do:
 *   - Does not change any product code.
 *   - Does not enable production LLM or use any real vendor API key.
 *   - Does not process real PHI — only the seeded demo encounter (Morgan Lee,
 *     PT-1001, Encounter #1) and built-in demo-sample buttons.
 *   - Does not record audio (browser context only).
 *   - Does not deploy.
 *
 * Run:
 *   cd $HOME/Desktop/ARCG/chartnav-platform/apps/web
 *   node ../../scripts/demo/phase63a_capture_demo_media.mjs
 *
 * Env it respects:
 *   E2E_BASE_URL  default http://127.0.0.1:5173
 *   E2E_API_URL   default http://127.0.0.1:8000
 */

import { createRequire } from "node:module";
import { execFileSync, spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// ── Paths & constants ──────────────────────────────────────────────────────
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const REPO_ROOT = resolve(__dirname, "..", "..");

const SHOT_DIR = join(REPO_ROOT, "artifacts", "phase-62", "screenshots");
const VIDEO_DIR = join(REPO_ROOT, "artifacts", "phase-62", "video-clips");
const DRY_RUN_DIR = join(
  REPO_ROOT,
  "artifacts",
  "phase-62",
  "dry-runs",
  "2026-05-20",
);
const RUN_LOG = join(DRY_RUN_DIR, "phase63a-capture.log");
const MANIFEST_PATH = join(DRY_RUN_DIR, "media-manifest.json");
const GENERATED_DIR = join(REPO_ROOT, "scripts", "demo", "generated");
const TERMINAL_HTML = join(GENERATED_DIR, "phase63a_terminal_evidence.html");
const DOCS_HTML = join(GENERATED_DIR, "phase63a_docs_evidence.html");

const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:5173";
const API_URL = process.env.E2E_API_URL || "http://127.0.0.1:8000";
const CLINICIAN = "clin@chartnav.local";

// Make sure the dirs exist before anything else.
for (const d of [SHOT_DIR, VIDEO_DIR, DRY_RUN_DIR, GENERATED_DIR]) {
  mkdirSync(d, { recursive: true });
}

// Truncate run log.
writeFileSync(RUN_LOG, `# phase63a capture run — ${new Date().toISOString()}\n`);
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  try {
    writeFileSync(RUN_LOG, line + "\n", { flag: "a" });
  } catch {
    /* noop */
  }
}

// ── Load Playwright from apps/web/node_modules ─────────────────────────────
const require_ = createRequire(import.meta.url);
let chromium;
try {
  const pw = require_(
    join(REPO_ROOT, "apps/web/node_modules/@playwright/test"),
  );
  chromium = pw.chromium;
} catch (err) {
  console.error(
    "FATAL: could not load @playwright/test from apps/web/node_modules. " +
      "Run 'npm install' in apps/web first.",
  );
  console.error(err.message);
  process.exit(2);
}

// ── Refuse to run if any real vendor key is set ────────────────────────────
const FORBIDDEN_KEYS = [
  "CHARTNAV_OPENAI_API_KEY",
  "CHARTNAV_ANTHROPIC_API_KEY",
  "CHARTNAV_WATSONX_API_KEY",
  "OPENAI_API_KEY",
  "ANTHROPIC_API_KEY",
  "WATSONX_API_KEY",
];
for (const k of FORBIDDEN_KEYS) {
  if (process.env[k]) {
    console.error(
      `ABORT: ${k} is set in this shell. Unset it before running capture.`,
    );
    process.exit(3);
  }
}
if (process.env.CHARTNAV_LLM_ENABLED && process.env.CHARTNAV_LLM_ENABLED !== "0") {
  console.error(
    `ABORT: CHARTNAV_LLM_ENABLED must be 0 (got "${process.env.CHARTNAV_LLM_ENABLED}").`,
  );
  process.exit(3);
}

// ── Capture manifest ───────────────────────────────────────────────────────
const manifest = [];
function record(filename, type, exists, path_, generated_by, scene, notes) {
  manifest.push({
    filename,
    type,
    exists,
    path: path_,
    generated_by,
    scene,
    notes,
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────
async function newScene(browser, sceneId) {
  const sceneVideoDir = join(VIDEO_DIR, `_tmp_${sceneId}`);
  mkdirSync(sceneVideoDir, { recursive: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: sceneVideoDir, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  return { context, page, sceneVideoDir };
}

async function finalizeScene(context, page, sceneVideoDir, videoFilename) {
  // Closing the page forces the video to flush; then close the context.
  const video = page.video();
  await page.close();
  await context.close();
  const dest = join(VIDEO_DIR, videoFilename);
  try {
    const src = await video.path();
    renameSync(src, dest);
    try {
      rmSync(sceneVideoDir, { recursive: true, force: true });
    } catch {
      /* noop */
    }
    log(`VIDEO ✓ ${videoFilename}`);
    record(videoFilename, "video", true, dest, "playwright", videoFilename, "");
    return true;
  } catch (err) {
    log(`VIDEO ✗ ${videoFilename} — ${err.message}`);
    record(
      videoFilename,
      "video",
      false,
      dest,
      "playwright",
      videoFilename,
      `failed to save: ${err.message}`,
    );
    return false;
  }
}

async function setIdentityAndOpenEncounter(page, email = CLINICIAN, encounterId = 1) {
  await page.goto(BASE_URL + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate(
    (e) => localStorage.setItem("chartnav.devIdentity", e),
    email,
  );
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForSelector("[data-testid=enc-list]", { timeout: 20000 });
  await page.locator(`[data-testid=enc-row-${encounterId}]`).click({
    timeout: 8000,
  });
  await page.waitForSelector("[data-testid=clinical-tabbed-workspace]", {
    timeout: 15000,
  });
  await page.waitForTimeout(400);
}

async function openTab(page, slug) {
  await page.locator(`[data-testid=ctw-tab-${slug}]`).click({ timeout: 8000 });
  await page.waitForSelector(`[data-testid=ctw-panel-${slug}]`, {
    timeout: 10000,
  });
  await page.waitForTimeout(400);
}

async function shot(page, filename, label, opts = {}) {
  const dest = join(SHOT_DIR, filename);
  try {
    await page.screenshot({ path: dest, fullPage: !!opts.fullPage });
    log(`SHOT  ✓ ${filename} — ${label}`);
    record(
      filename,
      "screenshot",
      true,
      dest,
      "playwright",
      label,
      opts.notes || "",
    );
    return true;
  } catch (err) {
    log(`SHOT  ✗ ${filename} — ${err.message}`);
    record(
      filename,
      "screenshot",
      false,
      dest,
      "playwright",
      label,
      `failed: ${err.message}`,
    );
    return false;
  }
}

async function clipShot(page, locator, filename, label) {
  const dest = join(SHOT_DIR, filename);
  try {
    const box = await locator.boundingBox({ timeout: 3000 });
    if (!box) throw new Error("locator has no bounding box");
    await page.screenshot({
      path: dest,
      clip: {
        x: Math.max(0, box.x),
        y: Math.max(0, box.y),
        width: Math.min(box.width, 1440),
        height: Math.min(box.height, 900),
      },
    });
    log(`SHOT  ✓ ${filename} — ${label} (clipped)`);
    record(filename, "screenshot", true, dest, "playwright", label, "clipped");
    return true;
  } catch (err) {
    log(`SHOT  ⚠ ${filename} — clip failed (${err.message}); fallback to full`);
    return await shot(page, filename, label, { notes: `clip fallback: ${err.message}` });
  }
}

async function maybeClick(loc, label) {
  try {
    if (await loc.isVisible({ timeout: 1500 })) {
      await loc.click({ timeout: 5000 });
      log(`CLICK ✓ ${label}`);
      return true;
    }
  } catch (err) {
    log(`CLICK ⚠ ${label} — ${err.message}`);
  }
  return false;
}

// ── Terminal + docs HTML rendering (shots 26–30, clip 11) ──────────────────
function runCmd(cmd, args, env = {}) {
  const r = spawnSync(cmd, args, {
    cwd: REPO_ROOT,
    env: { ...process.env, ...env },
    encoding: "utf8",
    timeout: 90_000,
  });
  return {
    cmd: [cmd, ...args].join(" "),
    code: r.status,
    stdout: (r.stdout || "").slice(-4000),
    stderr: (r.stderr || "").slice(-2000),
  };
}

function renderEvidenceHtml() {
  // Run the three safety commands and capture outputs.
  const runtime = runCmd("python3", ["scripts/check_runtime_safety.py"]);
  const commercial = runCmd("bash", ["scripts/check_commercial_claims.sh"]);
  const website = runCmd("bash", ["scripts/check_website_claims.sh"]);
  const demo = runCmd("bash", ["scripts/check_demo_claims.sh"]);
  // Alembic — try venv python first if present.
  const venvPy = join(REPO_ROOT, "apps/api/.venv/bin/python");
  const alembic = existsSync(venvPy)
    ? runCmd("bash", ["scripts/check_alembic_safety.sh"], { PYTHON: venvPy })
    : runCmd("bash", ["scripts/check_alembic_safety.sh"]);

  const sec = (title, r) => `
    <section>
      <h2>${title}</h2>
      <div class="cmd">$ ${escapeHtml(r.cmd)}</div>
      <pre class="ok">${escapeHtml(r.stdout)}</pre>
      ${r.stderr ? `<pre class="err">${escapeHtml(r.stderr)}</pre>` : ""}
      <div class="exit">exit ${r.code}</div>
    </section>`;

  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Phase 63A — Safety evidence</title>
<style>
  body { font: 14px/1.5 -apple-system, ui-monospace, monospace;
         background:#0f1115; color:#e5e7eb; margin:0; padding:24px 32px; }
  h1 { color:#a3e635; margin:0 0 16px; font-size:22px; }
  h2 { color:#fde68a; margin:24px 0 4px; font-size:16px; }
  section { background:#1f2430; border:1px solid #2a3140; border-radius:8px;
            padding:12px 16px; margin:0 0 16px; }
  .cmd { color:#93c5fd; margin-bottom:6px; }
  pre { background:#0a0d12; border-radius:6px; padding:10px 12px; margin:0;
        white-space:pre-wrap; word-break:break-word;
        font: 12.5px/1.55 ui-monospace, "SF Mono", Menlo, monospace;
        max-height:340px; overflow:auto; }
  pre.ok { color:#bef264; }
  pre.err { color:#fca5a5; margin-top:6px; }
  .exit { color:#a3a3a3; font-size:12px; margin-top:6px; }
  footer { color:#737373; font-size:12px; margin-top:24px; }
</style></head><body data-testid="phase63a-evidence">
<h1>ChartNav — Phase 63A automated safety evidence</h1>
<p>Generated ${new Date().toISOString()} from real script invocations.
Demo/local only. <strong>CHARTNAV_LLM_ENABLED=${process.env.CHARTNAV_LLM_ENABLED ?? "0"}</strong>.
No real vendor keys present.</p>

<a id="runtime-safety"></a>
${sec("Runtime safety validator", runtime)}

<a id="claim-scanners"></a>
${sec("Commercial-claim scanner", commercial)}
${sec("Website-claim scanner", website)}
${sec("Demo-claim scanner", demo)}

<a id="alembic-safety"></a>
${sec("Alembic safety", alembic)}

<footer>artifacts/phase-62/dry-runs/2026-05-20 · phase63a_capture_demo_media.mjs</footer>
</body></html>`;
  writeFileSync(TERMINAL_HTML, html);
  return { runtime, commercial, website, demo, alembic };
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderDocsHtml() {
  const releaseChk = safeRead(
    join(REPO_ROOT, "docs/release/release-evidence-checklist.md"),
  );
  const truth = safeRead(join(REPO_ROOT, "docs/build/current-product-truth.md"));

  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Phase 63A — Docs evidence</title>
<style>
  body { font: 14px/1.55 -apple-system, system-ui, sans-serif;
         background:#fafafa; color:#1f2937; margin:0; padding:24px 36px; max-width:1100px; }
  h1 { color:#1f2937; margin:0 0 16px; font-size:22px; }
  section { background:#fff; border:1px solid #e5e7eb; border-radius:8px;
            padding:18px 24px; margin:0 0 18px;
            box-shadow:0 1px 2px rgba(0,0,0,0.04); }
  h2 { margin:0 0 10px; font-size:16px; color:#111827; }
  pre { background:#0a0d12; color:#e5e7eb; border-radius:6px;
        padding:12px 14px; max-height:520px; overflow:auto;
        white-space:pre-wrap; word-break:break-word;
        font: 12.5px/1.55 ui-monospace, "SF Mono", Menlo, monospace; }
  .path { color:#6b7280; font-size:12px; margin-bottom:8px; }
</style></head><body>
<h1>ChartNav — Phase 63A documentation evidence</h1>
<section id="release-evidence-checklist">
  <h2>release-evidence-checklist.md</h2>
  <div class="path">docs/release/release-evidence-checklist.md</div>
  <pre>${escapeHtml(releaseChk.slice(0, 5500))}</pre>
</section>
<section id="current-product-truth">
  <h2>current-product-truth.md — Hard Safety Statements</h2>
  <div class="path">docs/build/current-product-truth.md</div>
  <pre>${escapeHtml(extractSafetySection(truth))}</pre>
</section>
</body></html>`;
  writeFileSync(DOCS_HTML, html);
}

function safeRead(p) {
  try {
    return readFileSync(p, "utf8");
  } catch (err) {
    return `(could not read ${p}: ${err.message})`;
  }
}

function extractSafetySection(md) {
  const idx = md.search(/hard safety statements/i);
  if (idx === -1) return md.slice(0, 5500);
  return md.slice(idx, idx + 5500);
}

// ── Scene scripts ──────────────────────────────────────────────────────────
async function sceneWorkspaceOrientation(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "01");
  try {
    await setIdentityAndOpenEncounter(page);
    await page.waitForTimeout(700);
    await shot(page, "01_workspace_landing.png", "workspace landing");
    const hdr = page.locator("[data-testid=ctw-patient-header]");
    await clipShot(page, hdr, "02_patient_header.png", "patient header");
    const tabBar = page.locator("[data-testid=ctw-tab-overview]").first();
    const tabBarParent = tabBar.locator("xpath=..");
    await clipShot(page, tabBarParent, "03_tab_navigation.png", "tab bar");
    // brief tour: hover each tab so video shows them
    for (const slug of ["clinical", "documentation", "imaging"]) {
      await page.locator(`[data-testid=ctw-tab-${slug}]`).hover();
      await page.waitForTimeout(350);
    }
  } catch (err) {
    log(`SCENE ✗ 01 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "01_workspace_orientation.webm");
}

async function sceneVitalsIntake(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "02");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "clinical");
    await page.waitForSelector("[data-testid=vitals-workup-panel]", { timeout: 10000 });
    await shot(page, "04_vitals_empty_form.png", "vitals empty form");
    await maybeClick(page.locator("[data-testid=vitals-demo-sample-btn]"), "load fake demo vitals");
    await page.waitForTimeout(900);
    await shot(page, "05_vitals_loaded.png", "vitals loaded");
    await page.waitForTimeout(600);
  } catch (err) {
    log(`SCENE ✗ 02 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "02_vitals_intake.webm");
}

async function sceneVitalsBmiAndWarning(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "03");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "clinical");
    await page.waitForSelector("[data-testid=vitals-workup-panel]", { timeout: 10000 });
    // Load demo vitals then surface BMI tile.
    await maybeClick(page.locator("[data-testid=vitals-demo-sample-btn]"), "load fake demo vitals");
    await page.waitForTimeout(900);
    await shot(page, "06_vitals_bmi.png", "vitals BMI");
    // Partial BP warning — clear systolic, save draft.
    const sysInput = page.getByLabel(/systolic/i).first();
    if (await sysInput.isVisible().catch(() => false)) {
      await sysInput.fill("");
      await maybeClick(
        page.locator("[data-testid=vitals-save-draft-btn]"),
        "save draft (partial BP)",
      );
      await page.waitForTimeout(900);
      await shot(page, "07_vitals_partial_bp_warning.png", "partial BP warning");
    } else {
      await shot(page, "07_vitals_partial_bp_warning.png", "no systolic field");
    }
    // Safety banner is the textual "what vitals does not do" surface.
    const banner = page.locator("[data-testid=vitals-safety-banner]");
    await clipShot(
      page,
      banner,
      "08_vitals_what_chartnav_did_not_do.png",
      "vitals safety banner (what NOT done)",
    );
  } catch (err) {
    log(`SCENE ✗ 03 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "03_vitals_bmi_warning.webm");
}

async function sceneVitalsReviewSignLock(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "04");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "clinical");
    await page.waitForSelector("[data-testid=vitals-workup-panel]", { timeout: 10000 });
    // Reload a clean draft.
    await maybeClick(page.locator("[data-testid=vitals-demo-sample-btn]"), "load fake demo vitals");
    await page.waitForTimeout(700);
    await maybeClick(
      page.locator("[data-testid=vitals-save-draft-btn]"),
      "save draft",
    );
    await page.waitForTimeout(800);
    await maybeClick(page.locator("[data-testid=vitals-review-btn]"), "mark reviewed");
    await page.waitForTimeout(700);
    await shot(page, "09_vitals_review.png", "vitals reviewed state");
    const cb = page.locator("[data-testid=vitals-attestation-checkbox]");
    if (await cb.isVisible().catch(() => false)) {
      await cb.check({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(400);
      await maybeClick(page.locator("[data-testid=vitals-sign-btn]"), "sign and lock vitals");
      await page.waitForTimeout(1200);
    }
    await shot(page, "10_vitals_signed_lock.png", "vitals signed/locked");
  } catch (err) {
    log(`SCENE ✗ 04 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "04_vitals_review_sign_lock.webm");
}

async function sceneVisitDraftTranscriptToDraft(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "05");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "documentation");
    await page.waitForSelector("[data-testid=ambient-documentation-panel]", { timeout: 10000 });
    await shot(page, "11_visitdraft_empty.png", "visitdraft empty");
    await maybeClick(page.locator("[data-testid=ambient-sample-btn]"), "load demo sample");
    await page.waitForTimeout(700);
    await shot(page, "12_visitdraft_transcript.png", "visitdraft transcript loaded");
    await maybeClick(page.locator("[data-testid=ambient-generate-btn]"), "generate provider-review draft");
    await page.waitForTimeout(3500);
    await shot(page, "13_visitdraft_structured_facts.png", "structured facts");
    // expand details so draft note is fully visible
    const details = page.locator("[data-testid=ambient-draft-editor] details").first();
    if (await details.isVisible().catch(() => false)) {
      const open = await details.getAttribute("open").catch(() => null);
      if (open === null) await details.click().catch(() => {});
      await page.waitForTimeout(300);
    }
    await shot(page, "14_visitdraft_draft_note.png", "draft note text");
  } catch (err) {
    log(`SCENE ✗ 05 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "05_visitdraft_transcript_to_draft.webm");
}

async function sceneVisitDraftSafetyDidNotDo(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "06");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "documentation");
    await page.waitForSelector("[data-testid=ambient-documentation-panel]", { timeout: 10000 });
    await maybeClick(page.locator("[data-testid=ambient-sample-btn]"), "load demo sample");
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=ambient-generate-btn]"), "generate");
    await page.waitForTimeout(3500);
    // Safety flags / missing-info area.
    const safety = page.locator("[data-testid=ambient-safety-flags]");
    if (await safety.isVisible().catch(() => false)) {
      await safety.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
    }
    await shot(page, "15_visitdraft_safety_flags.png", "safety flags");
    // Forbidden-actions panel ("ChartNav did not perform ...").
    const forb = page.locator("[data-testid=ambient-forbidden-actions]");
    if (await forb.isVisible().catch(() => false)) {
      await forb.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
    }
    await clipShot(page, forb, "16_visitdraft_what_chartnav_did_not_do.png", "forbidden actions");
  } catch (err) {
    log(`SCENE ✗ 06 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "06_visitdraft_safety_did_not_do.webm");
}

async function sceneVisitDraftReviewSignLock(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "07");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "documentation");
    await page.waitForSelector("[data-testid=ambient-documentation-panel]", { timeout: 10000 });
    await maybeClick(page.locator("[data-testid=ambient-sample-btn]"), "load demo sample");
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=ambient-generate-btn]"), "generate");
    await page.waitForTimeout(3500);
    await maybeClick(page.locator("[data-testid=ambient-review-btn]"), "mark reviewed");
    await page.waitForTimeout(700);
    await shot(page, "17_visitdraft_reviewed.png", "visitdraft reviewed");
    const cb = page.locator("[data-testid=ambient-attestation-checkbox]");
    if (await cb.isVisible().catch(() => false)) {
      await cb.check({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(400);
      await maybeClick(page.locator("[data-testid=ambient-sign-btn]"), "sign and lock visitdraft");
      await page.waitForTimeout(1200);
    }
    await shot(page, "18_visitdraft_signed_lock.png", "visitdraft signed/locked");
  } catch (err) {
    log(`SCENE ✗ 07 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "07_visitdraft_review_sign_lock.webm");
}

async function sceneFundusFindingsToDiagram(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "08");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "imaging");
    await page.waitForSelector("[data-testid=fundus-chart-panel]", { timeout: 10000 });
    await shot(page, "19_fundus_empty.png", "fundus empty");
    // Choose laterality OD then click the horseshoe demo chip (OD).
    await maybeClick(page.locator("[data-testid=fundus-laterality-OD]"), "set laterality OD");
    const chips = page.locator("[data-testid=fundus-sample-chips] button");
    const chipCount = await chips.count().catch(() => 0);
    let chipClicked = false;
    for (let i = 0; i < chipCount; i++) {
      const c = chips.nth(i);
      const t = (await c.textContent().catch(() => ""))?.toLowerCase() ?? "";
      if (t.includes("horseshoe")) {
        await c.click({ timeout: 5000 }).catch(() => {});
        chipClicked = true;
        break;
      }
    }
    if (!chipClicked && chipCount > 0) {
      await chips.first().click({ timeout: 5000 }).catch(() => {});
    }
    await page.waitForTimeout(500);
    await shot(page, "20_fundus_findings.png", "fundus findings populated");
    await maybeClick(page.locator("[data-testid=fundus-generate-btn]"), "generate fundus chart");
    await page.waitForTimeout(2500);
    await shot(page, "21_fundus_svg.png", "fundus SVG rendered");
    const editor = page.locator("[data-testid=fundus-chart-editor]");
    if (await editor.isVisible().catch(() => false)) {
      await editor.scrollIntoViewIfNeeded();
    }
    await shot(page, "22_fundus_legend.png", "fundus legend / editor view");
  } catch (err) {
    log(`SCENE ✗ 08 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "08_fundus_findings_to_diagram.webm");
}

async function sceneFundusWarning(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "09");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "imaging");
    await page.waitForSelector("[data-testid=fundus-chart-panel]", { timeout: 10000 });
    // Lattice degeneration (OS) — should produce a non-empty warnings list.
    await maybeClick(page.locator("[data-testid=fundus-laterality-OS]"), "set laterality OS");
    const chips = page.locator("[data-testid=fundus-sample-chips] button");
    const count = await chips.count().catch(() => 0);
    for (let i = 0; i < count; i++) {
      const c = chips.nth(i);
      const t = (await c.textContent().catch(() => ""))?.toLowerCase() ?? "";
      if (t.includes("lattice")) {
        await c.click({ timeout: 5000 }).catch(() => {});
        break;
      }
    }
    await page.waitForTimeout(500);
    await maybeClick(page.locator("[data-testid=fundus-generate-btn]"), "generate fundus (lattice)");
    await page.waitForTimeout(2500);
    // Capture warnings list (or fundus-warnings-empty if none).
    const warnings = page.locator("[data-testid=fundus-warnings]");
    if (await warnings.isVisible().catch(() => false)) {
      await warnings.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
    }
    await shot(page, "23_fundus_warning.png", "fundus warning list");
  } catch (err) {
    log(`SCENE ✗ 09 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "09_fundus_warning.webm");
}

async function sceneFundusReviewSignLock(browser) {
  const { context, page, sceneVideoDir } = await newScene(browser, "10");
  try {
    await setIdentityAndOpenEncounter(page);
    await openTab(page, "imaging");
    await page.waitForSelector("[data-testid=fundus-chart-panel]", { timeout: 10000 });
    // Generate a clean OD horseshoe chart.
    await maybeClick(page.locator("[data-testid=fundus-laterality-OD]"), "set laterality OD");
    const chips = page.locator("[data-testid=fundus-sample-chips] button");
    const cnt = await chips.count().catch(() => 0);
    for (let i = 0; i < cnt; i++) {
      const c = chips.nth(i);
      const t = (await c.textContent().catch(() => ""))?.toLowerCase() ?? "";
      if (t.includes("horseshoe")) {
        await c.click({ timeout: 5000 }).catch(() => {});
        break;
      }
    }
    await page.waitForTimeout(500);
    await maybeClick(page.locator("[data-testid=fundus-generate-btn]"), "generate fundus");
    await page.waitForTimeout(2500);
    await maybeClick(page.locator("[data-testid=fundus-review-btn]"), "mark fundus reviewed");
    await page.waitForTimeout(700);
    await shot(page, "24_fundus_attestation.png", "fundus attestation block");
    const cb = page.locator("[data-testid=fundus-attestation-checkbox]");
    if (await cb.isVisible().catch(() => false)) {
      await cb.check({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(400);
      await maybeClick(page.locator("[data-testid=fundus-sign-btn]"), "sign and lock fundus");
      await page.waitForTimeout(1200);
    }
    await shot(page, "25_fundus_signed_lock.png", "fundus signed/locked");
  } catch (err) {
    log(`SCENE ✗ 10 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "10_fundus_review_sign_lock.webm");
}

async function sceneSafetyTerminal(browser) {
  // Render terminal-evidence HTML, screenshot 26/27/28 + record clip 11.
  const { context, page, sceneVideoDir } = await newScene(browser, "11");
  try {
    const fileUrl = "file://" + TERMINAL_HTML;
    await page.goto(fileUrl, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("[data-testid=phase63a-evidence]", { timeout: 8000 });
    // Shot 26 — runtime safety section.
    await page.locator("#runtime-safety").scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shot(page, "26_runtime_safety_terminal.png", "runtime safety section", { fullPage: false });
    // Shot 27 — claim scanners section.
    await page.locator("#claim-scanners").scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shot(page, "27_claim_scanners_terminal.png", "claim scanners section", { fullPage: false });
    // Shot 28 — alembic safety section.
    await page.locator("#alembic-safety").scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shot(page, "28_alembic_safety_terminal.png", "alembic safety section", { fullPage: false });
    // Clip 11: scroll back to top, then slowly scroll through.
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.waitForTimeout(700);
    const docH = await page.evaluate(() => document.body.scrollHeight);
    const winH = await page.evaluate(() => window.innerHeight);
    const steps = Math.max(6, Math.ceil((docH - winH) / 220));
    for (let i = 1; i <= steps; i++) {
      await page.evaluate((y) => window.scrollTo({ top: y, behavior: "smooth" }), Math.round((i * (docH - winH)) / steps));
      await page.waitForTimeout(550);
    }
  } catch (err) {
    log(`SCENE ✗ 11 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "11_safety_terminal.webm");
}

async function sceneDocsEvidence(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  try {
    const fileUrl = "file://" + DOCS_HTML;
    await page.goto(fileUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#release-evidence-checklist").scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shot(page, "29_release_evidence_checklist.png", "release-evidence-checklist");
    await page.locator("#current-product-truth").scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shot(page, "30_product_truth_safety_statements.png", "product truth safety statements");
  } catch (err) {
    log(`SCENE ✗ docs — ${err.message}`);
  }
  await page.close();
  await context.close();
}

async function sceneHighlightReel(browser) {
  // One long continuous video, ~2-3 minutes.
  const { context, page, sceneVideoDir } = await newScene(browser, "12");
  try {
    await setIdentityAndOpenEncounter(page);
    await page.waitForTimeout(1500);
    // Clinical / vitals
    await openTab(page, "clinical");
    await page.waitForSelector("[data-testid=vitals-workup-panel]", { timeout: 10000 });
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=vitals-demo-sample-btn]"), "load demo vitals");
    await page.waitForTimeout(900);
    await maybeClick(page.locator("[data-testid=vitals-save-draft-btn]"), "save draft");
    await page.waitForTimeout(900);
    await maybeClick(page.locator("[data-testid=vitals-review-btn]"), "mark reviewed");
    await page.waitForTimeout(700);
    const vcb = page.locator("[data-testid=vitals-attestation-checkbox]");
    if (await vcb.isVisible().catch(() => false)) {
      await vcb.check({ timeout: 4000 }).catch(() => {});
      await page.waitForTimeout(400);
      await maybeClick(page.locator("[data-testid=vitals-sign-btn]"), "sign vitals");
      await page.waitForTimeout(1200);
    }
    // Documentation / visitdraft
    await openTab(page, "documentation");
    await page.waitForSelector("[data-testid=ambient-documentation-panel]", { timeout: 10000 });
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=ambient-sample-btn]"), "load demo transcript");
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=ambient-generate-btn]"), "generate");
    await page.waitForTimeout(3500);
    const forb = page.locator("[data-testid=ambient-forbidden-actions]");
    if (await forb.isVisible().catch(() => false)) await forb.scrollIntoViewIfNeeded();
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=ambient-review-btn]"), "mark visitdraft reviewed");
    await page.waitForTimeout(700);
    const acb = page.locator("[data-testid=ambient-attestation-checkbox]");
    if (await acb.isVisible().catch(() => false)) {
      await acb.check({ timeout: 4000 }).catch(() => {});
      await page.waitForTimeout(400);
      await maybeClick(page.locator("[data-testid=ambient-sign-btn]"), "sign visitdraft");
      await page.waitForTimeout(1500);
    }
    // Imaging / fundus
    await openTab(page, "imaging");
    await page.waitForSelector("[data-testid=fundus-chart-panel]", { timeout: 10000 });
    await page.waitForTimeout(700);
    await maybeClick(page.locator("[data-testid=fundus-laterality-OD]"), "OD");
    const chips = page.locator("[data-testid=fundus-sample-chips] button");
    const cnt = await chips.count().catch(() => 0);
    for (let i = 0; i < cnt; i++) {
      const c = chips.nth(i);
      const t = (await c.textContent().catch(() => ""))?.toLowerCase() ?? "";
      if (t.includes("horseshoe")) {
        await c.click({ timeout: 4000 }).catch(() => {});
        break;
      }
    }
    await page.waitForTimeout(500);
    await maybeClick(page.locator("[data-testid=fundus-generate-btn]"), "generate fundus");
    await page.waitForTimeout(2500);
    await maybeClick(page.locator("[data-testid=fundus-review-btn]"), "mark fundus reviewed");
    await page.waitForTimeout(700);
    const fcb = page.locator("[data-testid=fundus-attestation-checkbox]");
    if (await fcb.isVisible().catch(() => false)) {
      await fcb.check({ timeout: 4000 }).catch(() => {});
      await page.waitForTimeout(400);
      await maybeClick(page.locator("[data-testid=fundus-sign-btn]"), "sign fundus");
      await page.waitForTimeout(1500);
    }
    // Closer: scroll up to show patient header, hold briefly.
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await page.waitForTimeout(2000);
  } catch (err) {
    log(`SCENE ✗ 12 — ${err.message}`);
  }
  await finalizeScene(context, page, sceneVideoDir, "12_highlight_reel_3min.webm");
}

// ── Main ───────────────────────────────────────────────────────────────────
(async () => {
  log(`base=${BASE_URL} api=${API_URL}`);
  log(`SHOT_DIR=${SHOT_DIR}`);
  log(`VIDEO_DIR=${VIDEO_DIR}`);

  // Pre-flight: check both services.
  for (const url of [API_URL + "/health", BASE_URL + "/"]) {
    try {
      const r = await fetch(url);
      log(`pre-flight ${url} → ${r.status}`);
      if (!r.ok) throw new Error(`status ${r.status}`);
    } catch (err) {
      console.error(`ABORT: ${url} not reachable (${err.message}).`);
      console.error("Run scripts/demo/phase63a_start_demo_stack.sh first.");
      process.exit(4);
    }
  }

  // Render evidence HTML pages BEFORE launching browser (cheap, deterministic).
  try {
    log("rendering terminal-evidence HTML ...");
    renderEvidenceHtml();
    log("rendering docs-evidence HTML ...");
    renderDocsHtml();
  } catch (err) {
    log(`evidence rendering failed: ${err.message}`);
  }

  const browser = await chromium.launch({ headless: true });
  log("chromium launched (headless)");

  // Scenes 1-12.
  await sceneWorkspaceOrientation(browser);
  await sceneVitalsIntake(browser);
  await sceneVitalsBmiAndWarning(browser);
  await sceneVitalsReviewSignLock(browser);
  await sceneVisitDraftTranscriptToDraft(browser);
  await sceneVisitDraftSafetyDidNotDo(browser);
  await sceneVisitDraftReviewSignLock(browser);
  await sceneFundusFindingsToDiagram(browser);
  await sceneFundusWarning(browser);
  await sceneFundusReviewSignLock(browser);
  await sceneSafetyTerminal(browser);
  await sceneDocsEvidence(browser);
  await sceneHighlightReel(browser);

  await browser.close();
  log("chromium closed");

  // Persist manifest summary now (count_media.sh will be the authoritative GO).
  writeFileSync(
    MANIFEST_PATH,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        base_url: BASE_URL,
        api_url: API_URL,
        identity: CLINICIAN,
        entries: manifest,
      },
      null,
      2,
    ),
  );
  log(`manifest written: ${MANIFEST_PATH}`);
  log("DONE");
})().catch((err) => {
  console.error("FATAL: ", err);
  process.exit(1);
});
