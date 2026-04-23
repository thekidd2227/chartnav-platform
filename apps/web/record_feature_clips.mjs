// ChartNav — five-clip feature inventory pack (clips 007–011).
//
//   007 — Calendar / Day View (date scrubber + today/prev/next +
//         status lanes). Real surface: DayView.tsx. ChartNav does
//         not ship a standalone calendar product; this is the
//         doctor's calendar-equivalent day board.
//   008 — NextBestAction reminders + workflow Timeline. Real surface:
//         NextBestAction.tsx + Timeline.tsx in NoteWorkspace. The
//         app does not ship a standalone reminder engine; NBA is
//         the honest "what to do next" nudge.
//   009 — Patient clinical record (ExamSummary + NoteLifecyclePanel
//         + note-version-list). The app does not ship a dedicated
//         "patient records" browser; the encounter detail + workspace
//         IS the patient's clinical record surface.
//   010 — Doctor sign-off with audit attribution. Real surfaces:
//         lifecycle-signed, lifecycle-attestation, lifecycle-
//         attribution. The signed-note audit trail, post-sign.
//   011 — Post-sign close-out: note-export (downloads the note
//         text file through the real browser download path),
//         note-copy (clipboard), and note-transmit if rendered.
//
// Both copies land in:
//   /Users/jean-maxcharles/Desktop/ChartNav_Video_Clips/11_hands_free_notetaking/
//   /Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/artifacts/video_clips/11_hands_free_notetaking/
//
// All scenes run against the real live stack (vite :5174 + uvicorn
// :8765). No simulated UIs. Each clip lands inside the 20–30 s window.

import { chromium } from "playwright";
import { mkdir, rm, readdir } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const APP_URL = process.env.APP_URL || "http://127.0.0.1:5174";
const API_URL = process.env.API_URL || "http://127.0.0.1:8765";
const REPO_DIR = resolve(
  "/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/artifacts/video_clips/11_hands_free_notetaking",
);
const DESK_DIR = resolve(
  "/Users/jean-maxcharles/Desktop/ChartNav_Video_Clips/11_hands_free_notetaking",
);
const VIEWPORT = { width: 1440, height: 900 };
const TARGET_DUR = 25;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function apiGet(path, email) {
  const r = await fetch(API_URL + path, { headers: { "X-User-Email": email } });
  if (!r.ok) throw new Error(`GET ${path} -> ${r.status}`);
  return r.json();
}

async function recordClip(name, identity, scenario) {
  const rawDir = join(tmpdir(), `chartnav-feat-${name}-${Date.now()}`);
  await mkdir(rawDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: rawDir, size: VIEWPORT },
    // Allow downloads for clip 011.
    acceptDownloads: true,
  });
  const page = await ctx.newPage();
  const startedAt = Date.now();
  const elapsed = () => (Date.now() - startedAt) / 1000;

  await page.goto(APP_URL + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate((id) => {
    try { localStorage.setItem("chartnav.devIdentity", id); } catch {}
  }, identity);
  await page.goto(APP_URL + "/", { waitUntil: "domcontentloaded" });

  try {
    await scenario(page, { elapsed, sleep, ctx });
  } catch (e) {
    console.error(`scenario ${name} threw:`, e?.message || e);
  }

  while (elapsed() < TARGET_DUR) await sleep(500);

  await page.close();
  await ctx.close();
  await browser.close();

  const files = (await readdir(rawDir)).filter((f) => f.endsWith(".webm"));
  if (!files.length) throw new Error(`no webm for ${name}`);
  const rawPath = join(rawDir, files[0]);

  await mkdir(REPO_DIR, { recursive: true });
  await mkdir(DESK_DIR, { recursive: true });

  for (const base of [REPO_DIR, DESK_DIR]) {
    const outPath = join(base, `${name}.mp4`);
    execFileSync(
      "ffmpeg",
      [
        "-y", "-loglevel", "error", "-nostdin",
        "-i", rawPath,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        outPath,
      ],
      { stdio: "inherit" },
    );
    if (!existsSync(outPath)) throw new Error(`mp4 missing: ${outPath}`);
  }

  await rm(rawDir, { recursive: true, force: true });

  const duration = parseFloat(
    execFileSync(
      "ffprobe",
      [
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        join(REPO_DIR, `${name}.mp4`),
      ],
      { encoding: "utf8" },
    ).trim(),
  );
  const inWindow = duration >= 20 && duration <= 30;
  console.log(JSON.stringify({ clip: name, duration, inWindow }, null, 2));
  return { clip: name, duration, inWindow };
}

// --- Scenarios ------------------------------------------------------

// 007 — DayView (the real calendar surface).
const scenarioCalendar = async (page, { sleep }) => {
  await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
  await sleep(1000);
  // Switch to Day View.
  await page.click('[data-testid="view-day"]');
  await page.waitForSelector('[data-testid="dayview"]', { timeout: 8000 });
  await sleep(2000);
  // Scroll through a few days using prev/next to demonstrate the
  // scrubber, then snap back with Today.
  for (let i = 0; i < 3; i++) {
    try {
      await page.click('[data-testid="dayview-prev"]');
      await sleep(1000);
    } catch {}
  }
  await sleep(1200);
  for (let i = 0; i < 3; i++) {
    try {
      await page.click('[data-testid="dayview-next"]');
      await sleep(900);
    } catch {}
  }
  await sleep(1500);
  try {
    await page.click('[data-testid="dayview-today"]');
  } catch {}
  await sleep(2500);
  // Scroll to a status lane for legibility.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="dayview"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(2500);
};

// 008 — NextBestAction + workflow Timeline reminders.
const scenarioReminders = (targetName) => async (page, { sleep }) => {
  await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
  await sleep(1000);
  // Open the target encounter's workspace.
  const clicked = await page.evaluate((pn) => {
    const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
      .find((el) => el.textContent && el.textContent.includes(pn));
    if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" }); row.click(); return true; }
    return false;
  }, targetName);
  if (!clicked) throw new Error("target row not found");
  await sleep(2000);
  // NBA CTA.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="nba"]') ||
               document.querySelector('[data-testid="nba-cta"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(3000);
  // Workflow timeline — scroll to it.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="timeline"]') ||
               document.querySelector('[data-testid="event-form"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(3500);
  // Back up to the NBA card for a closing dwell.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="nba"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(2500);
};

// 009 — Patient clinical record: ExamSummary + NoteLifecyclePanel.
const scenarioPatientRecord = (targetName) => async (page, { sleep }) => {
  await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
  await sleep(1000);
  const clicked = await page.evaluate((pn) => {
    const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
      .find((el) => el.textContent && el.textContent.includes(pn));
    if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" }); row.click(); return true; }
    return false;
  }, targetName);
  if (!clicked) throw new Error("target row not found");
  await sleep(2000);
  // ExamSummary.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="exam-summary"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(3500);
  // NoteLifecyclePanel.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="lifecycle-panel"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(3500);
  // Note version list + transmissions.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="note-version-list"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(3000);
};

// 010 — Doctor sign-off with full audit attribution.
const scenarioSignAudit = (targetName) => async (page, { sleep }) => {
  await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
  await sleep(1000);
  const clicked = await page.evaluate((pn) => {
    const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
      .find((el) => el.textContent && el.textContent.includes(pn));
    if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" }); row.click(); return true; }
    return false;
  }, targetName);
  if (!clicked) throw new Error("target row not found");
  await sleep(2000);
  // Walk the audit path: lifecycle-status -> lifecycle-signed ->
  // lifecycle-attribution -> lifecycle-attestation.
  for (const id of [
    "lifecycle-panel",
    "lifecycle-status",
    "lifecycle-attribution",
    "lifecycle-signed",
    "lifecycle-attestation",
  ]) {
    await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }, `[data-testid="${id}"]`);
    await sleep(2200);
  }
  // Final dwell on the version list.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="note-version-list"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(2000);
};

// 011 — Post-sign close-out: final-approval → export → copy → transmit.
// Wave 7 gate: a signed note is export-blocked until an authorized
// final signer types their exact stored name into the Final Approval
// form on the NoteLifecyclePanel. Clinician's stored name in the
// seeded DB is "Casey Clinician".
const scenarioExport = (targetName, approverName) => async (page, { sleep }) => {
  await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
  await sleep(1000);
  const clicked = await page.evaluate((pn) => {
    const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
      .find((el) => el.textContent && el.textContent.includes(pn));
    if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" }); row.click(); return true; }
    return false;
  }, targetName);
  if (!clicked) throw new Error("target row not found");
  await sleep(1500);
  // 1) Record final physician approval.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="lifecycle-final-approval"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(1500);
  try {
    await page.locator('[data-testid="lifecycle-final-approval-input"]').fill(approverName);
    await sleep(800);
    await page.click('[data-testid="lifecycle-final-approve-submit"]');
    await sleep(2500);
  } catch (e) {
    console.log("final-approve path skipped:", e?.message || e);
  }
  // 2) Scroll back up to the artifact actions and click Export.
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="note-artifact-actions"]') ||
               document.querySelector('[data-testid="note-export"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(1200);
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 8000 }).catch(() => null),
    page.click('[data-testid="note-export"]').catch((e) => {
      console.log("note-export click:", e?.message || e);
    }),
  ]);
  if (download) {
    try { await download.saveAs(join(tmpdir(), `note-${Date.now()}.txt`)); } catch {}
  }
  await sleep(2000);
  // 3) Copy + Transmit (both optional / informational in dev).
  try { await page.click('[data-testid="note-copy"]', { timeout: 2000 }); } catch {}
  await sleep(1500);
  try { await page.click('[data-testid="note-transmit"]', { timeout: 2000 }); } catch {}
  await sleep(2000);
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="lifecycle-final-approval"]') ||
               document.querySelector('[data-testid="note-version-list"]');
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  await sleep(2000);
};

// --- Orchestrator ---------------------------------------------------

async function main() {
  await apiGet("/encounters", "clin@chartnav.local");

  // The previously-recorded journey pack left a signed note on the
  // latest Riley Morgan encounter. Use that for clips 008–011 so the
  // workspace is rich (transcript + findings + generated note + signed
  // attestation + attribution metadata).
  const enc = await apiGet("/encounters", "clin@chartnav.local");
  const items = Array.isArray(enc) ? enc : (enc.items || []);
  const riley = items
    .filter((r) => r.patient_name === "Riley Morgan")
    .sort((a, b) => b.id - a.id)[0];
  if (!riley) throw new Error("no Riley Morgan encounter; run journey pack first");
  const TARGET_NAME = riley.patient_name;
  console.log(`Target encounter: id=${riley.id} patient="${TARGET_NAME}" pid=${riley.patient_identifier}`);

  const results = [];
  results.push(await recordClip(
    "007_calendar_day_view",
    "clin@chartnav.local",
    scenarioCalendar,
  ));
  results.push(await recordClip(
    "008_next_best_action_and_timeline",
    "clin@chartnav.local",
    scenarioReminders(TARGET_NAME),
  ));
  results.push(await recordClip(
    "009_patient_clinical_record",
    "clin@chartnav.local",
    scenarioPatientRecord(TARGET_NAME),
  ));
  results.push(await recordClip(
    "010_doctor_signoff_audit_attribution",
    "clin@chartnav.local",
    scenarioSignAudit(TARGET_NAME),
  ));
  // Stored name on clin@chartnav.local per the seed is "Casey Clinician".
  results.push(await recordClip(
    "011_note_export_copy_transmit",
    "clin@chartnav.local",
    scenarioExport(TARGET_NAME, "Casey Clinician"),
  ));

  console.log("---- FEATURE PACK SUMMARY ----");
  console.log(JSON.stringify({ target: TARGET_NAME, results }, null, 2));
}

main().catch((e) => {
  console.error("feature record FAIL:", e);
  process.exit(1);
});
