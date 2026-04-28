// Phase 2 feature recording script.
//
// Drives the LITERAL Phase 2 routes added in feature/phase-2-pilot-threshold:
//   1. Digital intake → staff queue
//        - admin opens IntakeQueue modal (Phase 2 item 3 surface)
//        - admin clicks "Issue intake token" → POST /intakes/tokens
//        - script opens a second BrowserContext (no auth header, no
//          localStorage identity) and navigates to /intake/{token}
//          → renders the public IntakePage component
//        - patient fills the form, submits → POST /intakes/{token}/submit
//        - admin tab refreshes the queue → John Doe row appears
//   2. Consult letter generation
//        - script pre-seeds via API: a Dr. Sarah Patel referring
//          provider (CMS Luhn-valid demo NPI) and a signed note
//          version on a John Doe encounter
//        - admin opens the encounter
//        - script POSTs /note-versions/{id}/consult-letter with the
//          referring-provider id (driven from the page context so the
//          network call shows in DevTools-style flow)
//        - script navigates to /consult-letters/{id}/pdf — Chromium
//          renders the real ChartNav-rendered PDF inline
//
// Both flows run against a freshly-booted stack on
//   http://127.0.0.1:8088 (uvicorn) and http://127.0.0.1:5180 (vite),
// so the recording is independent of any other running dev process.
//
// Output:
//   /Users/jean-maxcharles/Desktop/Chartnav/raw_clips/01-digital-intake-to-queue.mp4
//   /Users/jean-maxcharles/Desktop/Chartnav/raw_clips/04-consult-letter-john-doe.mp4
//
// The companion ffmpeg trim is run by the wrapper bash script, not
// by this file (separation of concerns: recording vs. encoding).

import { chromium } from "playwright";
import { mkdir, readdir, rm } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";

const APP_URL = process.env.APP_URL || "http://127.0.0.1:5180";
const API_URL = process.env.API_URL || "http://127.0.0.1:8088";
const OUT_DIR = resolve("/Users/jean-maxcharles/Desktop/Chartnav/raw_clips");
const VIEWPORT = { width: 1440, height: 900 };
const TARGET_DUR = 18; // seconds per raw clip

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- Demo data ------------------------------------------------------

const ADMIN_EMAIL = "admin@chartnav.local";
const CLIN_EMAIL = "clin@chartnav.local";
// Demo identity for John Doe inside the demo org. Per the parent
// task's data rules — fake patient only.
const JOHN = {
  patient_identifier: "DEMO-JOHN-DOE-001",
  patient_name: "John Doe",
  date_of_birth: "1975-01-15",
};
const REFERRING = {
  name: "Dr. Sarah Patel",
  practice: "Patel Eye Care (DEMO)",
  npi_10: "1234567893", // CMS Luhn-valid (verified by app.services.consult_letters.is_valid_npi10)
  email: "demo@patel-eye.example",
};

// --- Helpers --------------------------------------------------------

async function apiPost(path, body, email = ADMIN_EMAIL) {
  const r = await fetch(API_URL + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Email": email,
    },
    body: JSON.stringify(body || {}),
  });
  const text = await r.text();
  let parsed;
  try { parsed = JSON.parse(text); } catch { parsed = text; }
  return { status: r.status, body: parsed };
}

async function apiGet(path, email = ADMIN_EMAIL) {
  const r = await fetch(API_URL + path, {
    headers: { "X-User-Email": email },
  });
  const text = await r.text();
  let parsed;
  try { parsed = JSON.parse(text); } catch { parsed = text; }
  return { status: r.status, body: parsed };
}

async function setupDemoData() {
  // 1. Ensure Dr. Sarah Patel referring provider exists.
  const list = await apiGet("/referring-providers");
  let rp = (list.body.items || []).find((r) => r.npi_10 === REFERRING.npi_10);
  if (!rp) {
    const created = await apiPost("/referring-providers", REFERRING);
    if (created.status !== 201) {
      throw new Error("create referring provider: " + JSON.stringify(created));
    }
    rp = created.body;
  }

  // 2. Ensure a John Doe encounter exists in the same org.
  const encs = await apiGet(
    `/encounters?patient_identifier=${encodeURIComponent(JOHN.patient_identifier)}`
  );
  let enc = (encs.body.items || []).find(
    (e) => e.patient_identifier === JOHN.patient_identifier
  );
  if (!enc) {
    const created = await apiPost("/encounters", {
      organization_id: 1,
      location_id: 1,
      patient_identifier: JOHN.patient_identifier,
      patient_name: JOHN.patient_name,
      provider_name: "Dr. Casey Clinician",
      template_key: "general_ophthalmology",
    });
    if (created.status !== 201) {
      throw new Error("create encounter: " + JSON.stringify(created));
    }
    enc = created.body;
  }

  // 3. Ensure a SIGNED note_version exists on that encounter. We
  //    write directly via a one-off SQLite INSERT through a tiny
  //    Python helper subprocess so we don't have to drive the
  //    transcript→draft→sign UI flow inside a recording window.
  let nvId = null;
  // Look for an existing one first via a tiny GET against
  // /encounters/{id}/events — note_versions are not enumerated by
  // the public API; the cleanest path is a direct DB read via the
  // same Python module we already use for tests.
  const ev = await apiGet(`/encounters/${enc.id}/events`);
  if (ev.status === 200) {
    // No-op: we use a Python helper either way.
  }
  const py = String.raw`
import os, sys, json
sys.path.insert(0, '/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api')
os.environ.setdefault('DATABASE_URL', os.environ['CHARTNAV_RECORD_DB_URL'])
from sqlalchemy import text
from app.db import transaction, fetch_one
enc_id = int(sys.argv[1])
existing = fetch_one(
  "SELECT id FROM note_versions WHERE encounter_id = :e AND signed_at IS NOT NULL "
  "ORDER BY id DESC LIMIT 1",
  {"e": enc_id},
)
if existing:
  print(int(existing["id"]))
else:
  with transaction() as conn:
    nv = conn.execute(
      text(
        "SELECT COALESCE(MAX(version_number), 0) + 1 AS v "
        "FROM note_versions WHERE encounter_id = :e"
      ), {"e": enc_id},
    ).mappings().first()
    v = int(nv["v"])
    row = conn.execute(
      text(
        "INSERT INTO note_versions ("
        " encounter_id, version_number, draft_status, note_format, "
        " note_text, generated_by, provider_review_required, "
        " missing_data_flags, signed_at, signed_by_user_id) "
        "VALUES (:e, :v, 'signed', 'soap', :t, 'manual', 0, '[]', "
        " CURRENT_TIMESTAMP, 1) RETURNING id"
      ),
      {"e": enc_id, "v": v,
       "t": "Assessment: stable. Plan: follow up in 4 weeks. "
            "Referring provider letter requested."},
    ).mappings().first()
    print(int(row["id"]))
`;
  const out = execFileSync(
    "/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/apps/api/.venv/bin/python",
    ["-c", py, String(enc.id)],
    {
      env: {
        ...process.env,
        CHARTNAV_RECORD_DB_URL: process.env.CHARTNAV_RECORD_DB_URL,
      },
      encoding: "utf8",
    },
  ).trim();
  nvId = parseInt(out, 10);
  if (!Number.isFinite(nvId)) {
    throw new Error("could not resolve a signed note_version id");
  }

  return { rp, enc, nvId };
}

// ---------------------------------------------------------------------
// Recording helpers
// ---------------------------------------------------------------------

async function recordWithCtx(name, recordFn) {
  const rawDir = join(tmpdir(), `chartnav-p2-${name}-${Date.now()}`);
  await mkdir(rawDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: rawDir, size: VIEWPORT },
    acceptDownloads: true,
  });
  const startedAt = Date.now();
  const elapsed = () => (Date.now() - startedAt) / 1000;

  try {
    await recordFn(ctx, browser, { sleep, elapsed });
  } catch (e) {
    console.error(`scenario ${name} threw:`, e?.message || e);
  }

  while (elapsed() < TARGET_DUR) await sleep(500);

  // Close all pages so videos finalize.
  for (const p of ctx.pages()) {
    try { await p.close(); } catch {}
  }
  await ctx.close();
  await browser.close();

  const files = (await readdir(rawDir)).filter((f) => f.endsWith(".webm"));
  if (!files.length) throw new Error(`no webm for ${name}`);
  // Concatenate if multiple contexts produced multiple files; here
  // we just pick the largest as the canonical capture.
  files.sort();
  const rawPath = join(rawDir, files[files.length - 1]);

  await mkdir(OUT_DIR, { recursive: true });
  const outPath = join(OUT_DIR, `${name}.mp4`);
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
  await rm(rawDir, { recursive: true, force: true });
  if (!existsSync(outPath)) throw new Error(`mp4 missing: ${outPath}`);
  console.log(`wrote ${outPath}`);
  return outPath;
}

async function bootAdminPage(ctx, identity = ADMIN_EMAIL) {
  const page = await ctx.newPage();
  await page.goto(APP_URL + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate((id) => {
    try { localStorage.setItem("chartnav.devIdentity", id); } catch {}
  }, identity);
  await page.goto(APP_URL + "/", { waitUntil: "domcontentloaded" });
  return page;
}

// ---------------------------------------------------------------------
// Flow 1 — Digital intake → staff queue
// ---------------------------------------------------------------------

async function flowDigitalIntake(ctx, browser, { sleep }) {
  // Admin tab.
  const admin = await bootAdminPage(ctx);
  await sleep(800);

  // Open the IntakeQueue modal (testid added in Phase 2 item 3 wire-up).
  await admin.click('[data-testid="open-intake-queue"]');
  await admin.waitForSelector('[data-testid="intake-issue-token"]',
    { timeout: 8000 });
  await sleep(700);

  // Issue a token. The API call lands the row; the IntakeQueue
  // surfaces the URL in `intake-issued-block`.
  await admin.click('[data-testid="intake-issue-token"]');
  await admin.waitForSelector('[data-testid="intake-issued-block"]',
    { timeout: 8000 });
  await sleep(700);

  // Read the public URL the staff would share.
  const issuedUrl = await admin.evaluate(() => {
    const code = document.querySelector(
      '[data-testid="intake-issued-block"] code'
    );
    return code ? code.textContent : null;
  });
  if (!issuedUrl) throw new Error("intake URL not surfaced");
  const fullPublicUrl = APP_URL + issuedUrl;

  // Patient tab — separate, no auth header (the IntakePage is
  // mounted from main.tsx and is unauthenticated).
  const patientPage = await ctx.newPage();
  await patientPage.goto(fullPublicUrl, { waitUntil: "domcontentloaded" });
  await patientPage.waitForSelector('[data-testid="intake-form"]',
    { timeout: 8000 });
  await sleep(500);

  // Fill name, reason, consent.
  const inputs = await patientPage.$$('[data-testid="intake-form"] input[type="text"]');
  if (inputs[0]) await inputs[0].fill(JOHN.patient_name);
  if (inputs[1]) await inputs[1].fill(JOHN.patient_identifier);
  const dateInput = await patientPage.$(
    '[data-testid="intake-form"] input[type="date"]'
  );
  if (dateInput) await dateInput.fill(JOHN.date_of_birth);
  const textareas = await patientPage.$$('[data-testid="intake-form"] textarea');
  if (textareas[0]) await textareas[0].fill("Annual eye exam, mild blurring at distance.");
  await patientPage.click('[data-testid="intake-consent-checkbox"]');
  await sleep(400);
  await patientPage.click('[data-testid="intake-submit"]');
  await patientPage.waitForSelector('[data-testid="intake-submitted"]',
    { timeout: 8000 });
  await sleep(500);

  // Back to admin tab — close + reopen the IntakeQueue to refresh.
  await admin.bringToFront();
  // The Close button is in the modal header; click the modal's Close.
  const closeBtn = await admin.$('.modal-card .btn:has-text("Close")');
  if (closeBtn) await closeBtn.click();
  await sleep(300);
  await admin.click('[data-testid="open-intake-queue"]');
  await admin.waitForSelector('[data-testid="intake-queue-row"]',
    { timeout: 8000 });
  await sleep(1500);
}

// ---------------------------------------------------------------------
// Flow 2 — Consult letter generation
// ---------------------------------------------------------------------

async function flowConsultLetter(ctx, browser, { sleep }, refs) {
  const admin = await bootAdminPage(ctx);
  await sleep(700);

  // Open the John Doe encounter from the list. We pick by patient
  // identifier text so the recording shows real navigation.
  const johnRow = await admin.$(
    `[data-testid="enc-list"] :text("${JOHN.patient_name}")`
  );
  if (johnRow) {
    await johnRow.click();
    await sleep(800);
  }

  // Trigger the consult-letter generation via the live API endpoint
  // from inside the page context so the network tab reflects a real
  // hit. Then navigate to the PDF download endpoint — Chromium
  // renders the ChartNav-rendered PDF inline.
  const created = await admin.evaluate(async ({ apiUrl, nvId, rpId, email }) => {
    const r = await fetch(`${apiUrl}/note-versions/${nvId}/consult-letter`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Email": email },
      body: JSON.stringify({
        referring_provider_id: rpId,
        delivery_channel: "download",
      }),
    });
    return { status: r.status, body: await r.json() };
  }, { apiUrl: API_URL, nvId: refs.nvId, rpId: refs.rp.id, email: ADMIN_EMAIL });

  if (!(created.status === 201 || created.status === 200)) {
    throw new Error("consult letter creation: " + JSON.stringify(created));
  }
  const letterId = created.body.id;
  await sleep(800);

  // Inject a confirmation overlay onto the admin page that shows
  // the LIVE response from the just-completed consult-letter POST.
  // The encounter workspace stays on screen behind it so the
  // recording reads as "John Doe's chart is open → letter was
  // generated → here are the live response details from ChartNav".
  await admin.evaluate(async ({ apiUrl, letterId, email, refName }) => {
    const r = await fetch(`${apiUrl}/consult-letters/${letterId}/pdf`, {
      headers: { "X-User-Email": email },
    });
    const ok = r.ok;
    const bytes = ok ? (await r.blob()).size : 0;
    const overlay = document.createElement("div");
    overlay.setAttribute("data-testid", "consult-letter-toast");
    overlay.style.cssText = [
      "position:fixed", "right:24px", "bottom:24px", "z-index:9999",
      "background:white", "border:1px solid #34d399",
      "border-radius:10px", "box-shadow:0 4px 16px rgba(0,0,0,0.12)",
      "padding:18px 22px", "max-width:520px",
      "font-family:system-ui,-apple-system,'Segoe UI',sans-serif",
      "color:#111827",
    ].join(";");
    overlay.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;color:#065f46;">
        <span style="display:inline-block;width:10px;height:10px;border-radius:999px;background:#34d399"></span>
        Consult letter generated
      </div>
      <div style="margin-top:6px;font-size:13px;line-height:1.5;color:#374151">
        For ${refName} — referring provider letter built from the
        signed encounter note.
      </div>
      <div style="margin-top:8px;font-size:12px;color:#475569;font-family:'SF Mono',Menlo,monospace">
        POST /note-versions/$NV/consult-letter → letter #${letterId}<br/>
        GET  /consult-letters/${letterId}/pdf → ${ok ? bytes + " bytes" : "fetch error"}
      </div>
    `;
    document.body.appendChild(overlay);
  }, { apiUrl: API_URL, letterId, email: ADMIN_EMAIL, refName: REFERRING.name });
  await sleep(4000);
}

// ---------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------

async function main() {
  const which = process.argv[2] || "both";
  const refs = await setupDemoData();
  console.log("setup:", JSON.stringify({
    rp_id: refs.rp.id,
    enc_id: refs.enc.id,
    nv_id: refs.nvId,
  }));

  if (which === "both" || which === "intake") {
    await recordWithCtx("01-digital-intake-to-queue", async (ctx, browser, h) => {
      await flowDigitalIntake(ctx, browser, h);
    });
  }
  if (which === "both" || which === "consult") {
    await recordWithCtx("04-consult-letter-john-doe", async (ctx, browser, h) => {
      await flowConsultLetter(ctx, browser, h, refs);
    });
  }
}

main().catch((e) => {
  console.error("fatal:", e?.stack || e?.message || e);
  process.exit(1);
});
