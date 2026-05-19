# Phase 61 — Controlled Buyer Demo Storyboard

> Internal operator storyboard. Companion to
> `docs/demo/phase-61-controlled-buyer-demo-runbook.md`. Use this to
> rehearse the live demo end-to-end. **Not public marketing copy.**
> Not a customer takeaway. Demo is fake-data only; no real PHI; no
> production LLM; provider review + sign-off mandatory at every
> step.

## Opening narrative (15 sec)

> "I'm going to walk you through ChartNav as a **provider-reviewed
> workflow layer**. Everything you'll see today is fake demo data —
> no real patient information is in this environment. ChartNav
> doesn't replace your EHR; it sits alongside it and drafts
> artefacts a clinician reviews and signs. By the end, you'll have
> seen structured intake, transcript-to-draft, structured fundus
> charting, and provider review/sign — plus the safety posture
> that backs every step."

---

## Scene 1 — Technician intake + vitals

| | |
|---|---|
| **Objective** | Show that ChartNav captures structured vitals + ophthalmology workup as a technician-entered intake row, with provider-review warnings and a server-calculated BMI. |
| **Screen / module** | Clinical / Ophthalmology tab → **Technician Workup & Vitals** wide card. |
| **Operator action** | (1) Click the tab. (2) Click **Load fake demo vitals**. (3) Point at the live BMI display. (4) Click **Save draft**, then **Save & mark entered**. (5) Demonstrate a partial-BP warning by clearing systolic and saving; restore. (6) Click **Mark Reviewed** with a clinician identity. (7) Read the attestation aloud, tick the box, click **Sign & Lock Workup**. |
| **Safe narration** | "Vitals are captured by the technician for clinician review. BMI is server-calculated from height and weight — no manual BMI entry. Warnings are provider-review prompts, never diagnoses. The clinician reviews, attests, and signs. Signed workups are immutable; corrections start a new workup." |
| **Risk to avoid** | Never say "ChartNav detected hypertension / fever / hypoxia / tachycardia." Never imply device sync. Never demonstrate sign without ticking the attestation checkbox. |
| **Expected result** | Status timeline pills flip Draft → Entered → Reviewed → Signed. Green "Workup signed · locked" banner with timestamp. "What ChartNav did NOT do" card shows 9 forbidden actions each as `(false)`. |

Reference for the deep click path: `docs/demo/phase-60-vitals-workup-demo-runbook.md`.

---

## Scene 2 — Ambient transcript → provider-review draft

| | |
|---|---|
| **Objective** | Show that ChartNav drafts a structured provider-review note from a fake encounter transcript pasted by the operator, with safety flags and missing-information prompts but no autonomous documentation or diagnosis. |
| **Screen / module** | Documentation / EMR/EHR tab → **Provider-Reviewed Ambient Documentation Assist** wide card. |
| **Operator action** | (1) Click the tab; scroll past the existing stepper / NoteWorkspace. (2) Click **Load demo sample (fake data)**. (3) Click **Generate provider-review draft**. (4) Point at the structured-facts card (CC, HPI, VA, IOP, imaging metadata, assessment context, plan-as-stated). (5) Point at the **"What ChartNav did NOT do"** card. (6) Open the **Draft note text** details — read the "DRAFT — provider review required" banner aloud. (7) Click **Mark Reviewed**, then the attestation checkbox, then **Sign & Lock Draft**. |
| **Safe narration** | "The clinician's transcript is the source of truth. ChartNav extracts structured facts and drafts a provider-review note. It does not record audio, it does not autonomously document, it does not diagnose, and it does not place orders or send patient messages. Every draft starts with the literal phrase 'DRAFT — provider review required.'" |
| **Risk to avoid** | Never say "hands-free scribing", "ambient scribe parity", or "OpenAI-powered documentation". Never claim ChartNav listens to the exam room. |
| **Expected result** | Status timeline pills flip Draft → Ready for Review → Reviewed → Signed. Green "Draft signed · locked" banner. Signed drafts are immutable. |

Reference for the deep click path: `docs/demo/phase-57-ambient-documentation-demo-runbook.md`.

---

## Scene 3 — Fundus charting

| | |
|---|---|
| **Objective** | Show that ChartNav drafts a structured retinal diagram **from clinician-entered findings text** — not from any image — and that missing details surface as review prompts. |
| **Screen / module** | Imaging tab → **Fundus charts** wide card. |
| **Operator action** | (1) Click the tab; scroll past the imaging-pipeline / OD-OS workbench cards to the Fundus charts card. (2) Confirm OD is the default laterality. (3) Click the **`Horseshoe tear 10:30 OD`** chip; the textarea fills, laterality stays on OD. (4) Click **Generate Chart**. Point at the SVG preview, the legend, and the empty warnings panel. (5) Optional: load **`lattice degeneration at 6`** to show the missing-laterality warning; restore. (6) Click **Mark Reviewed**, tick the attestation checkbox, click **Sign & Lock Chart**. |
| **Safe narration** | "Fundus charting drafts a structured retinal diagram from the **clinician's typed findings**. ChartNav does not interpret fundus photos, does not auto-grade diabetic retinopathy, does not interpret OCT. Warnings ask the clinician to confirm missing detail — they're not findings." |
| **Risk to avoid** | Never say "AI interprets fundus" / "AI-generated fundus diagnosis" / "automatic OCT interpretation". Never imply the SVG is a clinical conclusion. |
| **Expected result** | Status timeline pills flip Draft → Reviewed → Signed. Green "Chart signed · locked" banner. Signed charts are immutable. |

Reference for the deep click path: `docs/demo/phase-56-fundus-demo-runbook.md`.

---

## Scene 4 — Provider review / sign across all three surfaces

| | |
|---|---|
| **Objective** | Reinforce that sign is gated by an explicit attestation checkbox on every surface and that the signed-lock posture is consistent across vitals, ambient, and fundus. |
| **Screen / module** | Loop through the three signed artefacts from Scenes 1–3. |
| **Operator action** | (1) Open each signed artefact in turn. (2) Point at the green signed-lock banner. (3) Point at the absence of action buttons (Save / Mark Reviewed / Sign all gone from the DOM). (4) Read the consistent "Signed artefacts are immutable" copy. (5) Optional: try to PATCH one via the browser dev tools / curl to show the 409 response. |
| **Safe narration** | "Three different artefacts, one consistent posture: sign requires explicit attestation, signing locks the artefact, the API returns 409 on any further mutation, and the clinician owns the signature. There is no auto-sign and no auto-amend." |
| **Risk to avoid** | Never narrate the 409 as a "rejection of the clinician" — it's a contract that signed artefacts are immutable. |
| **Expected result** | Three locked artefacts; three consistent signed-state UIs. |

---

## Scene 5 — Safety / audit posture

| | |
|---|---|
| **Objective** | Demonstrate the runtime safety validator, the audit posture, and the release-evidence checklist. Show that the safety frame is **infrastructure**, not narration. |
| **Screen / module** | Side terminal + editor (release evidence checklist + product truth doc). |
| **Operator action** | (1) Switch to the side terminal. (2) Run `python3 scripts/check_runtime_safety.py` live. (3) Point at `PASS — no unsafe runtime combinations detected.` (4) Open `docs/release/release-evidence-checklist.md`. Point at the Required Results table. (5) Optional: open `docs/build/current-product-truth.md` and point at the row for one of the three demonstrated features. (6) State the audit posture aloud. |
| **Safe narration** | "Every release is gated by a runtime safety validator that refuses unsafe combinations — production LLM, real-PHI with a demo adapter, OpenAI assist outside fake/demo mode, the Phase 52B pilot-allow flag set to 1, and so on. Audit rows on every workflow surface are metadata-only — raw vitals, raw transcript text, raw fundus drawings never appear in the audit log. We have canary regression tests on each surface that prove this." |
| **Risk to avoid** | Never reveal a real env-var value or API key in the side terminal. If the validator returns FAIL during the live run, halt the demo. |
| **Expected result** | `PASS` printed live. Buyer sees the release-evidence template. Buyer sees the product-truth row pinning the feature posture. |

---

## Closing narrative (30 sec)

> "Vitals and Ambient signed artefacts in ChartNav each carry an
> explicit 'What ChartNav did NOT do' panel listing the actions
> ChartNav did **not** perform — diagnosis, treatment
> recommendation, orders, referrals, patient messages, billing,
> coding, device integration, remote patient monitoring,
> auto-sign. Fundus Charting V1 enforces the same posture through
> warnings, the provider review/sign attestation flow, the signed-
> lock state, and the claim scanners — without a per-response
> forbidden-actions object today. Across all three surfaces, the
> posture is enforced by code, by tests, by the runtime safety
> validator, by the claim policy manifest, and by the operator
> runbook — not just by narration. ChartNav is a provider-reviewed
> workflow layer. Not a certified EHR. Not HIPAA-certified out of
> the box. Not an autonomous agent. Provider review and sign-off
> are mandatory at every step. Happy to take questions — and we
> have a safe-answers sheet for the most common ones we'd expect."

> *(Pivot to Q&A using `docs/demo/phase-61-buyer-qa-safe-answers.md`.)*

---

## Related documents

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` — master operator runbook.
- `docs/demo/phase-61-buyer-demo-checklist.md` — pre/during/post checklist.
- `docs/demo/phase-61-buyer-qa-safe-answers.md` — Q&A safe answers.
- `docs/demo/phase-60-vitals-workup-demo-runbook.md` — Vitals per-feature runbook.
- `docs/demo/phase-57-ambient-documentation-demo-runbook.md` — Ambient per-feature runbook.
- `docs/demo/phase-56-fundus-demo-runbook.md` — Fundus per-feature runbook.
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/release/release-evidence-checklist.md` — release-gate template.
- `scripts/check_runtime_safety.py` — runtime gate.
