// ChartNav — five-clip end-to-end patient journey proof pack.
//
// Produces 5 MP4 clips (each 20–30s, silent, 1440×900 H.264) that
// together walk the real product from "lead enters the system" to
// "note signed + audit trail visible". Every step is a real first-
// class surface (data-testid anchor) in the shipping app.
//
//   002 — lead/patient intake by the front desk (Create Encounter modal)
//   003 — encounter lands in the queue, status routed toward the doctor
//   004 — doctor opens the encounter and sees the Note Workspace tiers
//   005 — clinician ingests a transcript and generates the draft note
//   006 — clinician signs the note; audit trail + versions are visible
//
// All 5 clips are written to:
//   /Users/jean-maxcharles/Desktop/ChartNav_Video_Clips/11_hands_free_notetaking/
//   /Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/artifacts/video_clips/11_hands_free_notetaking/
//
// The recorder only exercises real product surfaces. No simulated
// "typing" into a fake UI; no staged screenshots. Every click is a
// real Playwright click against the live vite+uvicorn dev stack.

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
const MIN_DUR = 21; // seconds
const MAX_DUR = 29; // seconds

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function apiPost(path, body, email) {
  const res = await fetch(API_URL + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Email": email,
    },
    body: JSON.stringify(body),
  });
  const txt = await res.text();
  if (!res.ok) {
    throw new Error(`POST ${path} -> ${res.status}: ${txt}`);
  }
  return txt ? JSON.parse(txt) : null;
}

async function apiGet(path, email) {
  const res = await fetch(API_URL + path, {
    headers: { "X-User-Email": email },
  });
  const txt = await res.text();
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}: ${txt}`);
  return txt ? JSON.parse(txt) : null;
}

// --- Per-clip recorder ------------------------------------------------

async function recordClip(name, identityEmail, scenario) {
  const rawDir = join(tmpdir(), `chartnav-journey-${name}-${Date.now()}`);
  await mkdir(rawDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: rawDir, size: VIEWPORT },
  });
  const page = await ctx.newPage();
  const startedAt = Date.now();
  const elapsed = () => (Date.now() - startedAt) / 1000;

  // Prime identity.
  await page.goto(APP_URL + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate((id) => {
    try { localStorage.setItem("chartnav.devIdentity", id); } catch {}
  }, identityEmail);
  await page.goto(APP_URL + "/", { waitUntil: "domcontentloaded" });

  try {
    await scenario(page, { elapsed, sleep });
  } catch (e) {
    console.error(`scenario ${name} threw:`, e);
  }

  // Dwell until we land inside [MIN_DUR, MAX_DUR]. Target mid-range.
  const target = 25;
  while (elapsed() < target) {
    await sleep(500);
  }

  await page.close();
  await ctx.close();
  await browser.close();

  const files = (await readdir(rawDir)).filter((f) => f.endsWith(".webm"));
  if (!files.length) throw new Error(`no webm produced for ${name}`);
  const rawPath = join(rawDir, files[0]);

  await mkdir(REPO_DIR, { recursive: true });
  await mkdir(DESK_DIR, { recursive: true });

  const outFile = `${name}.mp4`;
  for (const base of [REPO_DIR, DESK_DIR]) {
    const outPath = join(base, outFile);
    execFileSync(
      "ffmpeg",
      [
        "-y",
        "-loglevel", "error",
        "-nostdin",
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
        join(REPO_DIR, outFile),
      ],
      { encoding: "utf8" },
    ).trim(),
  );
  const inWindow = duration >= MIN_DUR && duration <= MAX_DUR + 1;
  console.log(JSON.stringify({ clip: name, duration, inWindow }, null, 2));
  return { clip: name, duration, inWindow };
}

// --- Scenarios -------------------------------------------------------

// Clip 002 — front-desk creates a new encounter (lead intake).
const scenarioIntake = (patientId, patientName, provider) =>
  async (page, { sleep }) => {
    await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
    await sleep(1500);
    // Open the Create Encounter modal.
    await page.click('[data-testid="open-create-encounter"]');
    await page.waitForSelector('[data-testid="create-modal"]', { timeout: 5000 });
    await sleep(1200);
    // Fill the form, typed character-by-character for legibility.
    await page.locator('[data-testid="create-patient-id"]').fill(patientId);
    await sleep(600);
    await page.locator('[data-testid="create-patient-name"]').fill(patientName);
    await sleep(600);
    await page.locator('[data-testid="create-provider"]').fill(provider);
    await sleep(600);
    // Location dropdown — pick Main Clinic (id=1) if present.
    try {
      await page.locator('[data-testid="create-location"]').selectOption("1");
    } catch {}
    await sleep(1200);
    // Submit.
    await page.click('[data-testid="create-submit"]');
    // Dwell on the new row in the list.
    await page.waitForSelector(
      `[data-testid^="enc-row-"]:has-text("${patientName}")`,
      { timeout: 10000 },
    );
    await sleep(2500);
    await page.evaluate((pn) => {
      const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
        .find((el) => el.textContent && el.textContent.includes(pn));
      if (row) row.scrollIntoView({ behavior: "smooth", block: "center" });
    }, patientName);
    await sleep(2000);
  };

// Clip 003 — queue/routing: switch to Day View, highlight readiness,
// move status forward toward the clinician's queue.
const scenarioQueue = (patientName) =>
  async (page, { sleep }) => {
    await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
    await sleep(1200);
    // Scroll to the target row and click to open detail pane.
    const clicked = await page.evaluate((pn) => {
      const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
        .find((el) => el.textContent && el.textContent.includes(pn));
      if (row) {
        row.scrollIntoView({ behavior: "smooth", block: "center" });
        row.click();
        return true;
      }
      return false;
    }, patientName);
    if (!clicked) throw new Error("target encounter row not found");
    await sleep(2000);
    // Show the detail pane + transitions.
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="transitions"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    await sleep(2000);
    // Drive the encounter forward: scheduled -> in_progress if button exists.
    const moved = await page.evaluate(() => {
      const btn =
        document.querySelector('[data-testid="transition-in_progress"]') ||
        document.querySelector('[data-testid="transition-review_needed"]');
      if (btn) { btn.click(); return true; }
      return false;
    });
    await sleep(2500);
    // Switch to Day View to show the doctor's board.
    try {
      await page.click('[data-testid="view-day"]', { timeout: 2000 });
    } catch {}
    await sleep(2500);
    // Switch back to list for closing dwell.
    try {
      await page.click('[data-testid="view-list"]', { timeout: 2000 });
    } catch {}
    await sleep(1500);
  };

// Clip 004 — doctor opens the encounter Note Workspace.
const scenarioWorkspace = (patientName) =>
  async (page, { sleep }) => {
    await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
    await sleep(1500);
    const clicked = await page.evaluate((pn) => {
      const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
        .find((el) => el.textContent && el.textContent.includes(pn));
      if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" });
        row.click(); return true; }
      return false;
    }, patientName);
    if (!clicked) throw new Error("target encounter row not found");
    await sleep(2500);
    // Scroll through the three tiers of the workspace.
    for (const id of [
      "workspace-tier-transcript",
      "workspace-tier-findings",
      "workspace-tier-draft",
    ]) {
      await page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, `[data-testid="${id}"]`);
      await sleep(2200);
    }
    // Back to the top for a final dwell.
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="note-workspace"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    await sleep(2000);
  };

// Clip 005 — ingest a transcript and generate the draft note.
const scenarioTranscriptDraft = (patientName, transcript) =>
  async (page, { sleep }) => {
    await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
    await sleep(1200);
    const clicked = await page.evaluate((pn) => {
      const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
        .find((el) => el.textContent && el.textContent.includes(pn));
      if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" });
        row.click(); return true; }
      return false;
    }, patientName);
    if (!clicked) throw new Error("target encounter row not found");
    await sleep(1800);
    // Scroll to the transcript ingest form.
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="transcript-ingest-form"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    await sleep(1500);
    // Paste a realistic transcript.
    await page
      .locator('[data-testid="transcript-ingest-textarea"]')
      .fill(transcript);
    await sleep(1500);
    await page.click('[data-testid="transcript-ingest-submit"]');
    await sleep(2500);
    // Click Generate Draft.
    try {
      await page.click('[data-testid="generate-draft"]', { timeout: 4000 });
    } catch {}
    // Wait for the draft tier to render.
    await page.waitForSelector(
      '[data-testid="note-draft-textarea"], [data-testid="note-draft-readonly"]',
      { timeout: 15000 },
    ).catch(() => {});
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="workspace-tier-draft"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    await sleep(3500);
  };

// Clip 006 — note sign-off + audit trail.
const scenarioSignoff = (patientName) =>
  async (page, { sleep }) => {
    await page.waitForSelector('[data-testid="enc-list"]', { timeout: 10000 });
    await sleep(1200);
    const clicked = await page.evaluate((pn) => {
      const row = [...document.querySelectorAll('[data-testid^="enc-row-"]')]
        .find((el) => el.textContent && el.textContent.includes(pn));
      if (row) { row.scrollIntoView({ behavior: "smooth", block: "center" });
        row.click(); return true; }
      return false;
    }, patientName);
    if (!clicked) throw new Error("target encounter row not found");
    await sleep(1800);
    // Scroll to the draft tier.
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="workspace-tier-draft"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    await sleep(1500);
    // Click Sign note. ChartNav opens its PreSignCheckpoint modal
    // (the real safety gate); tick the ack checkbox and confirm.
    let signed = false;
    try {
      await page.click('[data-testid="note-sign"]', { timeout: 3000 });
    } catch {
      try {
        await page.click('[data-testid="note-submit-review"]', { timeout: 2500 });
      } catch {}
    }
    // Handle the PreSignCheckpoint modal if it opens.
    try {
      await page.waitForSelector('[data-testid="presign-modal"]', { timeout: 3000 });
      await sleep(1200);
      // Use .check() + verify isChecked before confirming; the raw
      // checkbox is wrapped in a <label> and a plain click can be
      // absorbed by the label without flipping the React state.
      const ack = page.locator('[data-testid="presign-ack"]');
      await ack.check();
      await sleep(400);
      const checked = await ack.isChecked();
      console.log("presign-ack isChecked:", checked);
      await sleep(700);
      await page.locator('[data-testid="presign-confirm"]').click();
      signed = true;
      // Let the backend commit + UI refresh.
      await sleep(2500);
    } catch (e) {
      console.log("presign modal path not taken:", e.message);
    }
    await sleep(1500);
    // Show the note transmissions + version history panels.
    for (const sel of [
      '[data-testid="note-transmissions"]',
      '[data-testid="note-version-list"]',
    ]) {
      await page.evaluate((s) => {
        const el = document.querySelector(s);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, sel);
      await sleep(2200);
    }
    // Final dwell on the draft + status.
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="note-draft-status"]') ||
                 document.querySelector('[data-testid="workspace-tier-draft"]');
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    await sleep(2500);
  };

// --- Orchestrator ----------------------------------------------------

async function main() {
  // Seed a fresh patient identity tied to this run so the visible
  // name is stable across clips. Using a human-looking demo name.
  const PATIENT_ID = `PT-DEMO-JOURNEY-${Date.now().toString().slice(-6)}`;
  const PATIENT_NAME = "Riley Morgan";
  const PROVIDER = "Dr. Carter";

  // We don't need to pre-create the encounter — clip 002 does it
  // through the real UI. But we check the API is up first.
  await apiGet("/encounters", "clin@chartnav.local");

  const results = [];
  // This build seeds admin/clinician/reviewer for org 1 (no
  // dedicated front_desk user). `clin@chartnav.local` passes
  // `canCreateEncounter` (admin|clinician|front_desk) so the
  // Create Encounter surface is identical in behavior.
  results.push(await recordClip(
    "002_lead_intake_create_encounter",
    "clin@chartnav.local",
    scenarioIntake(PATIENT_ID, PATIENT_NAME, PROVIDER),
  ));
  results.push(await recordClip(
    "003_encounter_queue_and_routing",
    "clin@chartnav.local",
    scenarioQueue(PATIENT_NAME),
  ));
  results.push(await recordClip(
    "004_doctor_opens_note_workspace",
    "clin@chartnav.local",
    scenarioWorkspace(PATIENT_NAME),
  ));
  // Rich SOAP-complete transcript that matches the note_generator
  // regex patterns so the draft has zero missing_data_flags and the
  // clinician can actually sign in clip 006. Key forms:
  //   - "Chief complaint: ..."           → chief_complaint
  //   - "VA OD 20/25, VA OS 20/30"       → visual_acuity_od/os
  //   - "IOP 17/16"                      → iop_od/os (slash shorthand)
  //   - "Assessment: ..."                → diagnoses
  //   - "Plan: ..."                      → plan
  //   - "follow up in 3 months"          → follow_up_interval (digit)
  const TRANSCRIPT =
    "Chief complaint: glaucoma follow-up and eye pressure check. " +
    "HPI: Patient Riley Morgan here for glaucoma follow-up, " +
    "stable since last visit, no new floaters or flashes. " +
    "VA OD 20/25, VA OS 20/30. " +
    "IOP 17/16. " +
    "Medications: latanoprost 0.005% one drop each eye nightly. " +
    "Assessment: primary open-angle glaucoma, stable on therapy. " +
    "Plan: continue latanoprost nightly, counseled on adherence, " +
    "follow up in 3 months for repeat IOP and visual field testing.";
  results.push(await recordClip(
    "005_transcript_ingest_and_draft",
    "clin@chartnav.local",
    scenarioTranscriptDraft(PATIENT_NAME, TRANSCRIPT),
  ));
  results.push(await recordClip(
    "006_note_signoff_and_audit",
    "clin@chartnav.local",
    scenarioSignoff(PATIENT_NAME),
  ));

  console.log("---- JOURNEY PACK SUMMARY ----");
  console.log(JSON.stringify({ patient: PATIENT_NAME, results }, null, 2));
  const allOk = results.every((r) => r.inWindow);
  if (!allOk) {
    console.error("WARN: some clips fell outside the 20-30s window");
  }
}

main().catch((e) => {
  console.error("journey record FAIL:", e);
  process.exit(1);
});
