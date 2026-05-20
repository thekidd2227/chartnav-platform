# Phase 63 — Safe Website Video Plan

> **Status: PLAN ONLY.** This document defines the eight safe demo
> videos for the website. No video files exist yet. Capture
> happens on the operator's iMac (the build sandbox has no display).
> Until the videos are captured, the website MUST NOT be updated
> with broken video elements.
>
> This plan is the contract: every clip below has a safe title, a
> safe message, and a hard list of phrases the operator must
> **never** say in narration or on-screen text.

## Safety frame (apply to every clip)

ChartNav is a **provider-reviewed workflow layer**. Every artefact
is generated from clinician-provided input (transcript text typed
or pasted by the clinician; technician-entered vitals; clinician-
entered fundus findings). Every artefact requires a **clinician
sign-off** before it is locked.

ChartNav does **not** listen to the exam room, does **not** capture
live ambient audio, does **not** diagnose, does **not** interpret
fundus images, does **not** place orders, send referrals, message
patients, bill, or code. ChartNav is **not** a certified EHR and
does **not** replace a certified EHR. ChartNav is **not** HIPAA
certified.

All capture is fake-data only. `CHARTNAV_ENV=local`,
`CHARTNAV_LLM_PROVIDER=deterministic_stub`,
`CHARTNAV_LLM_ENABLED=0`. No real PHI on camera.

## The eight safe website videos

For each clip:
- **Filename** is the literal name the capture script must produce.
- **Safe title** is what the website card displays.
- **Safe message** is the narration intent (operator may rephrase
  but must stay within the safe message; must not use any phrase
  from "Must NOT say").
- **Must NOT say** is the hard exclusion list — these phrases trip
  the demo + website + commercial claim scanners.

### 1. Workflow Workspace

- **Filename:** `01_workspace_orientation.webm` (+ `.mp4` if ffmpeg
  is available).
- **Safe title:** ChartNav Workflow Workspace
- **Safe message:** ChartNav is a provider-reviewed workflow layer
  that sits alongside the EHR. The workspace shows the demo
  encounter and surface tabs (Clinical / Documentation / EMR/EHR
  / Imaging).
- **Capture path:** open the demo encounter; pan across the patient
  header + tab bar.
- **Duration target:** 20-25 sec.
- **Must NOT say:** "EHR replacement", "replaces the EHR",
  "HIPAA compliant", "certified EHR".

### 2. Technician Workup & Vitals

- **Filename:** `02_vitals_capture.webm`
- **Safe title:** Technician Workup & Vitals
- **Safe message:** A technician (acting as the clinician's
  delegate) enters structured vitals manually. ChartNav shows
  live BMI computation, partial-BP review prompts, and a "What
  ChartNav did NOT do" panel. The technician submits; the
  clinician reviews and signs.
- **Capture path:** Clinical / Ophthalmology → vitals form → load
  fake demo vitals → BMI updates → partial-BP warning → did-not-do
  panel.
- **Duration target:** 30-35 sec.
- **Must NOT say:** "device integration", "BP cuff integration",
  "remote patient monitoring", "RPM", "diagnosis", "auto-grades
  vitals".

### 3. Provider-Reviewed VisitDraft Assist

- **Filename:** `03_visitdraft_transcript_to_draft.webm`
- **Safe title:** Provider-Reviewed VisitDraft Assist
- **Safe message:** A clinician pastes a **fake demo transcript**
  into ChartNav. ChartNav extracts structured facts (chief
  complaint, HPI, VA, IOP, imaging metadata, assessment context,
  plan-as-stated) and produces a draft note labelled "DRAFT —
  provider review required." The clinician reviews and signs.
- **Capture path:** Documentation / EMR/EHR tab → wide card titled
  on screen **"Provider-Reviewed Ambient Documentation Assist"**
  (narrated as VisitDraft Assist) → Load demo sample → Generate
  provider-review draft → structured-facts card visible.
- **Duration target:** 30-35 sec.
- **Must NOT say:** "hands-free scribing", "listens to the exam
  room", "ambient capture", "captures live room audio",
  "autonomous documentation", "AI writes the note", "automated
  hands-free scribing".

### 4. VisitDraft Signal Filter

- **Filename:** `04_visitdraft_signal_filter.webm`
- **Safe title:** VisitDraft Signal Filter
- **Safe message:** Given a clinician-pasted fake transcript that
  mixes everyday small-talk with stated clinical facts, ChartNav
  **extracts only the stated clinical facts the clinician typed**
  and surfaces missing-information prompts for items the clinician
  did not state. The clinician decides what to keep.
- **Capture path:** Same VisitDraft card → paste a fake transcript
  that includes both casual lines ("How's the dog?") and stated
  clinical facts ("VA OD 20/40") → Generate → structured facts
  panel shows only the clinical fields → missing-information card
  flags blanks.
- **Duration target:** 25-30 sec.
- **Must NOT say:** "listens to chatter", "ignores chatter from
  live audio", "captures live room audio", "ambient capture",
  "hands-free", "AI listens".

### 5. Provider-Reviewed Fundus Drawing Assist

- **Filename:** `05_fundus_drawing_assist.webm`
- **Safe title:** Provider-Reviewed Fundus Drawing Assist
- **Safe message:** The clinician types findings (e.g., "horseshoe
  tear at 10:30 OD") into a structured findings textarea, picks
  laterality, and clicks Generate. ChartNav produces a
  **structured retinal diagram** (concentric rings + clock-hour
  labels + finding glyphs) deterministically from the clinician's
  text. ChartNav does not interpret fundus photos or OCT images.
- **Capture path:** Imaging tab → Fundus charts card → click
  Horseshoe tear 10:30 OD chip → Generate Chart → SVG renders →
  legend strip visible.
- **Duration target:** 25-35 sec.
- **Must NOT say:** "AI interprets fundus", "image
  interpretation", "OCT interpretation", "AI detects retinal
  disease", "fundus diagnosis", "autonomous fundus
  interpretation", "auto-grades DR".

### 6. Doctor Review & Signed Lock

- **Filename:** `06_doctor_review_signoff.webm`
- **Safe title:** Doctor Review, Attestation, and Signed Lock
- **Safe message:** On each surface (Vitals, VisitDraft, Fundus),
  the clinician marks Reviewed, ticks the attestation checkbox,
  and clicks Sign & Lock. The artefact becomes immutable; further
  mutation returns 409. There is no auto-sign.
- **Capture path:** Repeat Reviewed → attestation → Sign & Lock on
  Vitals, VisitDraft, and Fundus surfaces. Show the green
  "signed · locked" banner each time.
- **Duration target:** 30-40 sec.
- **Must NOT say:** "auto-sign", "ChartNav signs the chart",
  "autonomous finalize", "automatic chart finalization".

### 7. Safety Boundaries

- **Filename:** `07_safety_posture.webm`
- **Safe title:** What ChartNav Did Not Do
- **Safe message:** ChartNav's safety posture is declared on every
  response (the closed-actions list returns each disallowed action
  with `(false)`), and a side terminal shows the runtime safety
  validator + claim scanners all PASS.
- **Capture path:** Show the "What ChartNav did NOT do" card on
  Vitals + VisitDraft. Side terminal: `python3
  scripts/check_runtime_safety.py` → PASS. Optional:
  `bash scripts/check_commercial_claims.sh` → PASSED.
- **Duration target:** 20-30 sec.
- **Must NOT say:** "compliance certification", "HIPAA
  compliant", "SOC 2 certified", "FDA cleared", "HITRUST
  certified".

### 8. Three-Minute Controlled Demo Highlight Reel

- **Filename:** `08_three_minute_highlight_reel.webm`
- **Safe title:** ChartNav Controlled Demo Highlight Reel
- **Safe message:** Workspace → Vitals → VisitDraft → Fundus
  Drawing → Doctor Sign-Off → Safety Posture, end to end, in
  about three minutes. Narrated with the safe message from each
  preceding clip.
- **Capture path:** Re-run the full visit script
  (`docs/demo/phase-62-end-to-end-demo-visit-script.md`) in one
  unbroken capture, compress to ~3 min.
- **Duration target:** ~3 min.
- **Must NOT say:** any forbidden claim from clips 1-7.

## Capture method

Two-stage, in priority order:

1. **Playwright headed capture** via
   `scripts/demo/capture_phase63_safe_demo_media.mjs`. Drives the
   local web app at `http://localhost:5173` with a header-auth
   clinician identity (`X-User-Email: clin@chartnav.local`), uses
   only fake demo data, and produces `.webm` recordings into
   `artifacts/phase-63/video-clips/`.
2. **Manual fallback** via QuickTime Player + Screenshot.app, with
   the same filename targets, driven by the operator following
   this plan. The helper script
   `~/Desktop/ChartNav-Buyer-Demo-Build/prepare-phase63-video-capture.sh`
   opens the relevant URLs / docs / folders so the operator can
   capture by hand.

If neither path yields a real file, the manifest stays
`exists: false` and the website integration stays blocked.

## Website integration

When (and only when) the eight `.webm` files exist:

1. Copy web-optimized versions into
   `apps/web/public/demo-media/` (a sibling step, **not** part of
   Phase 63's sandbox commit because the videos don't exist yet).
2. Add a "Controlled Demo Videos" section to the landing page
   using the approved copy block + safe titles below.
3. Add poster thumbnails from
   `artifacts/phase-63/screenshots/` if those exist.
4. Use muted controls or click-to-play. No autoplay with sound.
5. Add the fake-data disclaimer above the video grid.

### Approved website copy block

> Controlled fake-data demo videos. ChartNav is a provider-reviewed
> workflow layer. These clips show structured intake, provider-
> reviewed VisitDraft Assist, Fundus Drawing Assist, doctor sign-
> off, and safety boundaries. ChartNav does not diagnose, does not
> interpret fundus images, does not place orders, does not bill or
> code, and does not replace a certified EHR.

### Card titles (one per video, in display order)

1. Workflow Workspace
2. Technician Workup & Vitals
3. Provider-Reviewed VisitDraft Assist
4. VisitDraft Signal Filter
5. Provider-Reviewed Fundus Drawing Assist
6. Doctor Review & Signed Lock
7. Safety Boundaries
8. Three-Minute Controlled Demo

## Unsafe phrasing the user originally asked for, and the safe
## replacement

| Originally requested (unsafe) | Why rejected | Safe replacement (use this) |
|---|---|---|
| "automated hands-free scribing" | implies autonomous live capture | "Provider-Reviewed VisitDraft Assist — fake transcript to provider-review draft" |
| "ambient capture with regular chatter ignored and medical findings listened to" | implies live audio capture + filtering | "VisitDraft Signal Filter — from a clinician-pasted fake transcript, ChartNav extracts stated clinical facts only and flags missing items for provider review" |
| "ChartNav listens to the exam room" | implies live audio capture | (do not narrate; ChartNav does not listen) |
| "AI writes the note" | implies autonomous documentation | "ChartNav drafts; provider reviews and signs" |
| "ChartNav diagnoses X" | implies diagnosis | "ChartNav surfaces missing-information prompts; provider diagnoses" |
| "AI interprets the fundus" | implies image interpretation | "Clinician-entered findings to structured retinal diagram" |
| "HIPAA compliant" / "certified EHR" | unapproved compliance claim | (do not narrate; not a claim ChartNav holds) |

These pairs are also encoded in the existing claim scanners
(`scripts/check_demo_claims.sh`, `scripts/check_website_claims.sh`,
`scripts/check_commercial_claims.sh`). Any narration that strays
into the left column will be caught either by the scanner or by a
human reviewer before publication.

## Out of scope

- No product UI rename. The on-screen card title still reads
  "Provider-Reviewed Ambient Documentation Assist"; narration says
  "Provider-Reviewed VisitDraft Assist". Phase 62A pinned this.
- No backend / migration / API change.
- No new claim approval.
- No production LLM activation. No real PHI. No deploy.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-screenshot-shot-list.md`
- `docs/demo/phase-62-video-clip-shot-list.md`
- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
- `docs/build/phase-63-safe-demo-media-website-report.md` (the
  Phase 63 evidence report, written after capture)
