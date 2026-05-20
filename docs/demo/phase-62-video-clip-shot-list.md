# Phase 62 — Buyer Demo Video Clip Shot List

> 12 short video clips required for the buyer-demo evidence packet.
> All captures are **`[MANUAL CAPTURE REQUIRED]`** by the operator
> on their local iMac; the sandbox cannot capture display output.
> Save every clip under `artifacts/phase-62/video-clips/` with the
> exact filename listed. Each clip is **15–45 seconds** unless noted.
> Use the seeded fake demo patient (**Morgan Lee · PT-1001 ·
> Encounter #1 · Dr. Carter**); never record real PHI.

## Capture conventions

- **Tooling:** macOS QuickTime screen recording (default), or
  Loom / Cleanshot if preferred. No browser-side recording extension
  that exfiltrates content.
- **Resolution:** at least 1280×720 (1080p preferred). Browser at
  100% zoom.
- **Audio:** capture **without** voice narration. The shot list's
  "narration" field is what the operator says **live** during the
  buyer demo, not embedded in the file. Recording audio in the file
  risks baking forbidden phrasings into the artifact.
- **Format:** `.mov` (QuickTime native) or `.mp4`. Keep file sizes
  reasonable (each clip should be < 50 MB; trim aggressively).
- **Length cap:** 45 seconds per clip except clip 12 (the highlight
  reel) which targets 3 minutes.
- **Redaction:** N/A — all data is fake. Confirm no real env-var
  value, real API key, or vendor organisation id is visible in any
  terminal segment.
- **Filename:** lowercase, snake_case, prefixed with the 2-digit ID,
  saved under `artifacts/phase-62/video-clips/`.

If actual video capture is **not** feasible at the time of the dry
run, the operator may produce **GIF stills** (export from QuickTime
to .gif at 10–15 fps) covering the same start/end points. Note in
the dry-run report that GIFs were substituted.

---

## 1. Workspace orientation

- **File:** `artifacts/phase-62/video-clips/01_workspace_orientation.mov`
- **Duration target:** 20–25 seconds.
- **Capture start:** the demo encounter URL is open with the Overview
  tab selected; the patient header (Morgan Lee · PT-1001 ·
  Encounter #1 · Dr. Carter) is visible.
- **Capture end:** after slowly hovering across the 9 tabs (Overview
  → Clinical / Ophthalmology → Documentation / EMR-EHR → Imaging →
  Labs / Orders Review → Calendar → Communications → Documents →
  Chat), return to Overview. Stop recording.
- **Narration (operator says live, not in file):** "ChartNav opens
  to a provider-reviewed workspace. Morgan Lee is a fake demo
  patient — the 'Not recorded' fields are intentional empty state.
  Nine tabs; ChartNav is a workflow layer the clinic uses alongside
  their EHR, not the EHR itself."
- **Avoid saying:** "this is your EHR", "replaces your EHR", "HIPAA
  compliant".
- **Feature value:** Tabbed workspace overview + fake-data
  discipline.
- **Marketable takeaway:** ChartNav fits an ophthalmology visit
  end-to-end without claiming to replace the EHR.

## 2. Technician Workup & Vitals intake

- **File:** `02_vitals_intake.mov`
- **Duration target:** 30–35 seconds.
- **Capture start:** Clinical / Ophthalmology tab is open and the
  Technician Workup & Vitals empty form is visible.
- **Capture end:** after clicking **Load fake demo vitals** and
  showing the populated General Vitals + Ophthalmology Workup +
  Review Checks sections, stop recording.
- **Narration (operator says live):** "Structured intake captured by
  the technician for clinician review. Vitals — BP, temperature,
  pulse, RR, SpO2 — plus ophthalmology workup with visual acuity,
  IOP, dilation status. Manually entered — no device integration.
  No real PHI."
- **Avoid saying:** "device integration", "BP cuff sync", "smart
  scale", "remote patient monitoring".
- **Feature value:** Technician-friendly structured intake.
- **Marketable takeaway:** A clear technician-driven start to the
  visit with provider-review built in.

## 3. BMI calculation + warning prompt

- **File:** `03_vitals_bmi_warning.mov`
- **Duration target:** 25–30 seconds.
- **Capture start:** Vitals form is loaded with the fake demo
  sample; height 70 in and weight 165 lb are visible. The BMI tile
  shows ~23.7.
- **Action during capture:**
  1. Briefly type a different weight (e.g. clear and re-type 200) —
     BMI tile updates live.
  2. Restore weight to 165 — BMI returns to ~23.7.
  3. Clear the systolic field (or diastolic field).
  4. Click **Save**.
  5. Warnings panel surfaces the "partial BP" review prompt.
- **Capture end:** the warnings panel is visible with the
  partial-BP review prompt text.
- **Narration (operator says live):** "BMI is server-calculated
  from height and weight. Out-of-range or partial values surface as
  review prompts, never as a diagnosis."
- **Avoid saying:** "hypertension", "hypotension", "high BP", "low
  BP", "the patient has X", "ChartNav detected X".
- **Feature value:** Server-side correctness + review-prompt
  language.
- **Marketable takeaway:** ChartNav doesn't invent clinical
  conclusions — it surfaces what's missing.

## 4. Vitals review / sign / lock

- **File:** `04_vitals_review_sign_lock.mov`
- **Duration target:** 30–40 seconds.
- **Capture start:** Vitals workup with status `Entered`, "What
  ChartNav did NOT do" card visible.
- **Action during capture:**
  1. Click **Mark Reviewed** — status flips to `Reviewed`; purple
     attestation block appears.
  2. Click **Sign & Lock Workup** without ticking the checkbox —
     button stays disabled.
  3. Tick the attestation checkbox.
  4. Click **Sign & Lock Workup**.
- **Capture end:** the green "Workup signed · locked" banner is
  visible with timestamp + signer id; all edit controls are absent
  from the DOM.
- **Narration (operator says live):** "Sign requires explicit
  attestation. Signed workups are immutable — the backend returns
  409 on any further mutation. There is no auto-sign."
- **Avoid saying:** "ChartNav signs the chart", "automatic sign".
- **Feature value:** Provider-in-the-loop signing.
- **Marketable takeaway:** Every artefact is locked by an explicit
  clinician attestation.

## 5. Provider-Reviewed VisitDraft Assist — transcript to draft

- **File:** `05_visitdraft_transcript_to_draft.mov`
- **Duration target:** 30–35 seconds.
- **Capture start:** Documentation / EMR-EHR tab is open; the
  Provider-Reviewed VisitDraft Assist wide card is visible with the
  empty textarea + safety banner.
- **Action during capture:**
  1. Click **Load demo sample (fake data)** — textarea fills with
     the synthetic transcript.
  2. Click **Generate provider-review draft**.
  3. Status timeline pills flip `Draft → READY FOR REVIEW`.
  4. Scroll briefly to reveal the structured-facts card.
- **Capture end:** the structured-facts card is visible with chief
  complaint, HPI, VA, IOP, imaging metadata, assessment context,
  plan-as-stated populated from the demo transcript.
- **Narration (operator says live):** "Provider-Reviewed VisitDraft
  Assist. The clinician's transcript drives the draft. ChartNav
  does not record audio — this is a fake demo transcript the
  operator pastes in. Structured facts come from the transcript;
  the clinician reviews and signs."
- **Avoid saying:** "ambient scribe", "hands-free scribing",
  "ChartNav listens", "OpenAI-powered clinical documentation",
  "AI writes the note".
- **Feature value:** Structured transcript-to-draft support.
- **Marketable takeaway:** Drafting comes from clinician input, not
  from autonomous AI.

## 6. VisitDraft — safety flags + "What ChartNav did NOT do"

- **File:** `06_visitdraft_safety_did_not_do.mov`
- **Duration target:** 25–35 seconds.
- **Capture start:** the VisitDraft panel is showing the post-generate
  state for the demo sample. Scroll so the **missing-information**
  card and **"What ChartNav did NOT do"** card are visible.
- **Action during capture:**
  1. Optional: clear the textarea and paste `Demo only. Patient
     seen for routine visit.`, click **Generate provider-review
     draft** to surface 3 missing-information items.
  2. Restore the clean demo sample.
  3. Scroll to the "What ChartNav did NOT do" card.
- **Capture end:** the "What ChartNav did NOT do" card is centred,
  showing 7 lines each ending in `(false)`.
- **Narration (operator says live):** "ChartNav surfaces missing
  detail as a review prompt — never as a diagnosis. The 'What
  ChartNav did NOT do' panel lists every disallowed action with
  `(false)`: diagnosis, orders, referrals, patient messages,
  billing or coding, auto-sign, image interpretation."
- **Avoid saying:** "the AI diagnosed X", "ChartNav recommends X".
- **Feature value:** Explicit closed-actions disclosure.
- **Marketable takeaway:** ChartNav's safety posture is declared on
  every response — not just narrated.

## 7. VisitDraft — review / sign / lock

- **File:** `07_visitdraft_review_sign_lock.mov`
- **Duration target:** 30–40 seconds.
- **Capture start:** the VisitDraft panel is in `Ready for Review`
  status with the demo-sample draft loaded.
- **Action during capture:**
  1. Click **Mark Reviewed** — status flips to `Reviewed`;
     attestation block appears.
  2. Read the attestation copy briefly (on screen, not in audio).
  3. Tick the checkbox.
  4. Click **Sign & Lock Draft**.
- **Capture end:** green "Draft signed · locked" banner visible with
  timestamp; edit controls absent.
- **Narration (operator says live):** "Sign requires explicit
  attestation. Signed drafts are immutable. The clinician owns the
  signature."
- **Avoid saying:** "auto-sign", "automatic finalization".
- **Feature value:** Attestation-gated signing for VisitDraft.
- **Marketable takeaway:** Same attestation discipline across every
  workflow surface.

## 8. Provider-Reviewed Fundus Drawing Assist — clinician findings to diagram

- **File:** `08_fundus_findings_to_diagram.mov`
- **Duration target:** 25–35 seconds.
- **Capture start:** Imaging tab is open; Fundus charts wide card is
  visible with the empty findings textarea + safety banner; OD is
  the selected laterality.
- **Action during capture:**
  1. Click the **`Horseshoe tear 10:30 OD`** chip — textarea fills.
  2. Click **Generate Chart**.
  3. The SVG preview renders with concentric rings, clock-hour
     labels, and the horseshoe-tear glyph at ~11 o'clock.
  4. Briefly hover the legend strip.
- **Capture end:** the SVG + legend are centred; status pill at
  Draft.
- **Narration (operator says live):** "Provider-Reviewed Fundus
  Drawing Assist. The clinician types findings — ChartNav drafts a
  structured retinal diagram. No fundus photo. No image
  interpretation. No AI diagnosis."
- **Avoid saying:** "AI interprets fundus", "fundus image
  interpretation", "AI-generated fundus diagnosis", "OCT
  interpretation".
- **Feature value:** Structured diagram from clinician text.
- **Marketable takeaway:** Diagram drafting without image input.

## 9. Fundus warning prompt

- **File:** `09_fundus_warning.mov`
- **Duration target:** 15–25 seconds.
- **Capture start:** the Fundus panel shows the post-generate state
  for the horseshoe-tear sample.
- **Action during capture:**
  1. Clear the textarea.
  2. Click the **`lattice degeneration at 6`** chip (or type that
     literal text) — laterality field empties or stays OD.
  3. Click **Generate Chart**.
  4. The warnings panel surfaces the "Laterality not stated" review
     prompt.
- **Capture end:** the warnings panel is visible with the
  missing-laterality prompt; SVG renders with the lattice glyph at
  a default position.
- **Narration (operator says live):** "Missing detail surfaces as a
  review prompt asking the clinician to confirm OD or OS — never
  as a clinical finding."
- **Avoid saying:** "lattice degeneration detected", "ChartNav
  identified lattice".
- **Feature value:** Review-prompt language consistent with Vitals
  and VisitDraft.
- **Marketable takeaway:** Same "never invent" posture for fundus.

## 10. Fundus review / sign / lock

- **File:** `10_fundus_review_sign_lock.mov`
- **Duration target:** 30–35 seconds.
- **Capture start:** the Fundus panel is showing a clean
  horseshoe-tear chart in Draft status. Restore the chart via the
  saved-charts list if the previous clip changed it.
- **Action during capture:**
  1. Click **Mark Reviewed**.
  2. Tick the attestation checkbox.
  3. Click **Sign & Lock Chart**.
- **Capture end:** green "Chart signed · locked" banner visible with
  timestamp; edit controls absent.
- **Narration (operator says live):** "Same attestation pattern.
  Same signed-lock state. Fundus Charting V1 enforces the safety
  posture through the safety banner, the warnings panel, provider
  review/sign, the signed-lock state, and the claim scanners —
  without a per-response `forbidden_actions` object today. The
  Vitals and VisitDraft surfaces additionally declare the posture
  per response; fundus declares it through these surrounding
  controls."
- **Avoid saying:** "the fundus chart has a forbidden-actions
  panel" (it doesn't — Phase 61A pinned this).
- **Feature value:** Provider-attested signing for fundus.
- **Marketable takeaway:** Three different surfaces, one consistent
  signing discipline.

## 11. Runtime safety validator + claim scanners

- **File:** `11_safety_terminal.mov`
- **Duration target:** 20–30 seconds.
- **Capture start:** a clean side terminal at the repo root.
- **Action during capture:**
  1. Type and run `python3 scripts/check_runtime_safety.py` — show
     the `PASS` line.
  2. Type and run `bash scripts/check_commercial_claims.sh 2>&1 |
     tail -3` — show the `PASSED — 0 fail / 0 warn.` line.
  3. Type and run `bash scripts/check_demo_claims.sh 2>&1 |
     tail -3` — show the `PASSED — 0 positive-claim hits across N
     demo file(s).` line.
  4. Optional: `bash scripts/check_alembic_safety.sh 2>&1 | tail -3`
     showing the `PASSED - Alembic safety checks completed.` line.
- **Capture end:** all green PASS lines visible in the terminal
  buffer.
- **Narration (operator says live):** "Every release is gated by a
  runtime safety validator that refuses unsafe combinations —
  production LLM, real-PHI with a demo adapter, OpenAI assist
  outside fake / demo mode. Claim scanners block every forbidden
  marketing phrase in source files. Alembic safety enforces
  Postgres-portable migrations and a single head."
- **Avoid saying:** quoting any specific env-var value; do **not**
  `env | grep CHARTNAV` on camera. Do **not** show any real API
  key.
- **Feature value:** Safety enforcement as infrastructure, not
  narration.
- **Marketable takeaway:** Safety claims are code-enforced.

## 12. Full 3-minute buyer-demo highlight reel

- **File:** `12_highlight_reel_3min.mov`
- **Duration target:** 2 min 45 sec to 3 min 15 sec.
- **Capture start:** workspace landing (clip 1's start state).
- **Action during capture:** the operator runs the full Phase 62
  visit script (`docs/demo/phase-62-end-to-end-demo-visit-script.md`)
  in one continuous take, compressed:
  - 15 sec workspace orientation;
  - 30 sec vitals (Load fake demo vitals → BMI → warning → review →
    sign);
  - 35 sec VisitDraft (Load demo sample → Generate → structured
    facts → "What ChartNav did NOT do" → review → sign);
  - 30 sec Fundus (sample chip → Generate → warning → review →
    sign);
  - 25 sec terminal (runtime safety validator PASS, claim scanners
    PASS, Alembic safety PASS);
  - 15 sec closing on the signed-lock banners across the three
    surfaces.
- **Capture end:** the third signed-lock banner is visible.
- **Narration (operator says live):** the script's closing narration
  from § 10 of the visit script. **Do not** bake this narration into
  the file's audio — read it live over the silent reel.
- **Avoid saying:** any forbidden phrase from
  `docs/demo/phase-61-buyer-qa-safe-answers.md` § 9.
- **Feature value:** End-to-end ChartNav workflow in one defensible
  three-minute video.
- **Marketable takeaway:** Provider-reviewed workflow layer with
  signed-and-locked artefacts and code-enforced safety posture.

---

## Capture order recommendation

To minimise app restarts, capture clips in groups:

1. **Group A** (workspace + Vitals) — clips 1, 2, 3, 4 in order.
2. **Group B** (VisitDraft) — clips 5, 6, 7.
3. **Group C** (Fundus) — clips 8, 9, 10.
4. **Group D** (terminal) — clip 11.
5. **Group E** (highlight reel) — clip 12, captured last after
   rehearsal.

If a clip reveals a forbidden phrase, real-PHI shape, or visible
secret, **delete the file** and re-capture after fixing the source.

## Related documents

- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-screenshot-shot-list.md`
- `docs/demo/phase-62-demo-dry-run-report.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
