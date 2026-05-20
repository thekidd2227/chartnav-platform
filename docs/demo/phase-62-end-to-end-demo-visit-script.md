# Phase 62 — End-to-End Demo Visit Script

> **Fake-data demo only.** Patient is **Morgan Lee** (synthetic, no
> DOB, no MRN, no address, no phone, no real clinic identifiers).
> Scenario: retina follow-up / comprehensive ophthalmology visit
> with structured technician workup, **Provider-Reviewed VisitDraft
> Assist**, **Provider-Reviewed Fundus Drawing Assist**, provider
> review/sign, and evidence posture. ChartNav is **not** a certified
> EHR and does **not** replace one. ChartNav does **not** diagnose,
> recommend treatment, place orders, send referrals or patient
> messages, bill, code, interpret images, integrate with vital-signs
> devices, or do remote patient monitoring.

This is the canonical scenario the operator follows in the dry run
and the live buyer demo. It is a **scripted scenario**, not a
real visit. Use the built-in fake-data sample buttons; never type
real clinical content.

---

## 0. Glossary (internal name → buyer-facing name)

| Code / API / internal docs | Demo-facing label |
|---|---|
| Ambient Documentation Assist | **Provider-Reviewed VisitDraft Assist** |
| Fundus Charting V1 | **Provider-Reviewed Fundus Drawing Assist** |
| Technician Workup & Vitals | (unchanged) **Technician Workup & Vitals** |

The buyer-facing labels are **the only ones the operator says aloud**.

---

## 1. Workspace orientation (≈ 60 seconds)

**Module:** Clinical Tabbed Workspace shell.

**Operator action:**
1. Open the demo encounter URL.
2. The patient header reads: `Morgan Lee · PT-1001 · Encounter #1 · Dr. Carter · Location: Demo Clinic`.
3. Point at the demographic strip's explicit empty-state copy:
   "Not available in demo / Not recorded / No allergies recorded /
   No active meds recorded / Not scheduled."
4. Click through the nine tabs (Overview, Clinical / Ophthalmology,
   Documentation / EMR-EHR, Imaging, Labs / Orders Review, Calendar,
   Communications, Documents, Chat) without entering any. Return to
   Overview.

**Safe narration:**
> "ChartNav opens to a provider-reviewed workspace. Morgan Lee is a
> fake demo patient — the 'Not recorded' strip is intentional empty
> state. Nine tabs along the top; ChartNav is a workflow layer the
> clinic uses alongside their EHR, not the EHR itself."

**Risk to avoid:** never say "this is your EHR" / "this replaces
your EHR" / "this is HIPAA-compliant out of the box".

---

## 2. Technician workup & vitals (≈ 3 minutes)

**Module:** Clinical / Ophthalmology tab → **Technician Workup &
Vitals** wide card (top of the tab).

**Operator action:**
1. Click the **Clinical / Ophthalmology** tab.
2. The **Technician Workup & Vitals** card is the first card.
3. Click **Load fake demo vitals**. The form populates with synthetic
   values (BP 122/78 sitting left arm, temp 98.6 °F, pulse 72,
   RR 16, SpO2 98 %, height 70 in, weight 165 lb, pain 0, VA OD 20/20,
   VA OS 20/25, IOP 14 / 13 applanation, not dilated, allergies +
   medications reviewed, demo notes).
4. Point at the **BMI (calculated)** display. The number updates as
   you type height / weight.
5. Click **Save draft**.
6. Click **Save & mark entered**. Status timeline pill flips Entered.
7. **Demonstrate a warning:** clear the systolic field, click **Save**;
   the warnings panel surfaces "Blood pressure systolic captured but
   diastolic missing; please add systolic before signing." Narrate:
   *"Out-of-range or partial values surface as review prompts —
   never as a diagnosis."*
8. Manually re-enter the missing systolic value (or click "New
   workup" and **Load fake demo vitals** to start a clean workup),
   then click **Save** again to clear the warning.
9. Read the **"What ChartNav did NOT do"** card aloud: at least three
   entries with `(false)` markers. Example: *"ChartNav did not
   perform diagnosis (false). ChartNav did not perform orders
   (false). ChartNav did not perform billing or coding (false)."*

**Expected end state:** Status `Entered`, warnings panel empty, BMI
visible, "What ChartNav did NOT do" card lists 9 forbidden actions
each as `(false)`.

**Risk to avoid:** never narrate "ChartNav detected hypertension /
fever / hypoxia / tachycardia"; never claim device integration.

---

## 3. Ophthalmology intake (≈ 30 seconds, folded into vitals)

The ophthalmology section of the Vitals form (VA OD/OS/OU, IOP
OD/OS, IOP method, dilation status) is already populated by the
**Load fake demo vitals** button. The operator points at the
section and says:

> "Visual acuity OD / OS / OU is preserved as the clinician
> entered it — 20/20 OD and 20/25 OS, IOP 14 / 13 by applanation,
> not dilated today. ChartNav doesn't compute or interpret these —
> it captures what the clinician dictated."

**Risk to avoid:** never claim "ChartNav interprets VA / IOP" or
"ChartNav grades the eye exam".

---

## 4. Provider-Reviewed VisitDraft Assist — transcript to draft (≈ 3 minutes)

**Module:** Documentation / EMR-EHR tab → **Provider-Reviewed
VisitDraft Assist** wide card (below the existing Transcript →
Extracted Facts → AI Draft → Final Note stepper and the
NoteWorkspace).

**Internal name:** "Ambient Documentation Assist" (Phase 57). Same
code path; demo-facing label is **VisitDraft Assist**.

**Operator action:**
1. Click the **Documentation / EMR-EHR** tab.
2. Scroll past the stepper and existing NoteWorkspace to the
   **Provider-Reviewed VisitDraft Assist** wide card.
3. Click **Load demo sample (fake data)**. The textarea fills with
   the standard fake transcript ("Demo transcript only. Patient
   reports blurry vision in the right eye for two weeks…").
4. Click **Generate provider-review draft**. Status timeline pills
   flip `Draft → READY FOR REVIEW`.
5. Point at the **structured-facts card** (chief complaint, HPI
   summary, VA, IOP, imaging metadata, assessment context,
   plan-as-stated).
6. Point at the **"What ChartNav did NOT do"** card. Read three
   entries with `(false)` aloud (diagnosis, orders, billing-or-coding).
7. Open the **Draft note text** details. Read the opening line
   aloud: *"DRAFT — provider review required. ChartNav drafted this
   from a fake / demo encounter transcript…"*
8. **Demonstrate a missing-information warning:** clear the textarea
   and paste the literal phrase `Demo only. Patient seen for routine
   visit.`, click **Generate provider-review draft** again. The
   missing-information card now lists three items (chief complaint,
   visual acuity, intraocular pressure).
9. Return to the clean draft. Click **Mark Reviewed**. Status flips
   to `Reviewed` and the purple **attestation block** appears.
10. Read the attestation aloud: *"I attest that I have reviewed this
    draft note and it accurately reflects my clinical findings from
    the fake / demo transcript. Signing will lock the draft —
    signed drafts are immutable."*
11. Try **Sign & Lock Draft** without ticking the checkbox; it stays
    disabled. Tick the checkbox. Click **Sign & Lock Draft**.

**Expected end state:** Green **"Draft signed · locked"** banner
with timestamp + signer id; all edit controls gone from the DOM.

**Risk to avoid:** never say "ambient scribe" / "hands-free
scribing" / "ChartNav listens to the exam room" / "OpenAI-powered
clinical documentation". The optional OpenAI fake-data assist is
**not enabled** in this dry run.

---

## 5. Provider-Reviewed Fundus Drawing Assist — clinician findings to diagram (≈ 2.5 minutes)

**Module:** Imaging tab → **Fundus charts** wide card (below the
imaging-pipeline cards and the OD/OS retinal workbench).

**Internal name:** "Fundus Charting V1" (Phase 55/56). Same code
path; demo-facing label is **Provider-Reviewed Fundus Drawing
Assist**.

**Operator action:**
1. Click the **Imaging** tab.
2. Scroll to the **Fundus charts** card.
3. Confirm `OD · Right` is the default laterality.
4. Click the **`Horseshoe tear 10:30 OD`** sample chip. The textarea
   fills with `horseshoe tear at 10:30 OD`.
5. Click **Generate Chart**.
6. Point at the **SVG preview** (concentric rings + clock-hour
   labels + the horseshoe-tear glyph at 11 o'clock).
7. Point at the **legend** strip below the SVG.
8. Optional: load **`lattice degeneration at 6`** to demonstrate the
   missing-laterality warning; restore the horseshoe-tear chart by
   selecting it from the saved-charts list.
9. Read the safety banner aloud: *"Draft from clinician-entered
   findings. Provider review required. Not image interpretation.
   Does not diagnose."*
10. Click **Mark Reviewed**, then tick the attestation checkbox,
    then click **Sign & Lock Chart**.

**Expected end state:** Green **"Chart signed · locked"** banner;
all edit controls gone.

**Important note for the operator:** the Fundus Drawing Assist card
**does not** render a "What ChartNav did NOT do" panel and the
API does **not** return a `forbidden_actions` field today. Do
**not** claim it does. The Fundus V1 safety posture is enforced via
the safety banner above the panel, the warnings panel, the
provider review / sign attestation flow, the signed-lock state,
and the three claim scanners. (Phase 61A locked this distinction.)

**Risk to avoid:** never say "AI interprets fundus" / "fundus image
interpretation" / "AI-generated fundus diagnosis" / "auto-grades
DR".

---

## 6. Warnings / review prompts — recap (≈ 30 seconds)

Show one warning per surface back-to-back (Vitals, VisitDraft Assist,
Fundus). For each:

- Point at the warning text.
- Narrate: *"This is a review prompt for the clinician — not a
  finding, not a diagnosis. ChartNav asks for confirmation; the
  clinician decides clinical meaning."*

---

## 7. Provider review (≈ 30 seconds)

For each of the three signed surfaces (Vitals, VisitDraft, Fundus):

- Show the status timeline pill row with the Reviewed pill highlighted
  (pre-sign), or the Signed pill highlighted (post-sign).
- Narrate the **Review vs Sign** distinction: *"Reviewed is a
  workflow checkpoint. Sign is the permanent attestation. Two
  different actions because they mean two different things."*

---

## 8. Sign / lock (≈ 30 seconds)

For each of the three signed surfaces, show the green signed-lock
banner with timestamp + signer id. Narrate:

> "Signed artefacts are immutable. The backend returns 409 on any
> further mutation attempt. There is no auto-sign — sign always
> requires the attestation checkbox."

---

## 9. Audit / safety posture (≈ 60 seconds)

**Module:** Side terminal + editor (release-evidence checklist +
product-truth doc).

**Operator action:**
1. Switch to the side terminal.
2. Run `python3 scripts/check_runtime_safety.py` live. Point at
   `PASS - no unsafe runtime combinations detected.`
3. Open `docs/release/release-evidence-checklist.md`. Point at the
   Required Results table.
4. Open `docs/build/current-product-truth.md`. Point at the row for
   one of the three demonstrated features.

**Safe narration:**
> "Every release is gated by a runtime safety validator that refuses
> unsafe combinations — production LLM, real-PHI with a demo
> adapter, OpenAI assist outside fake / demo mode, the Phase 52B
> pilot-allow flag set to 1, etc. Audit rows on every workflow
> surface are metadata-only — raw vitals values, raw transcript
> text, raw fundus drawings never appear in the audit log. Canary
> regression tests per surface prove this."

**Risk to avoid:** never reveal real env values / API keys / vendor
organisation ids in the terminal.

---

## 10. What ChartNav did NOT do (≈ 60 seconds)

Return to either the Vitals or VisitDraft Assist signed artefact
(these are the surfaces that render the "What ChartNav did NOT do"
card). Read every entry aloud:

> "ChartNav did not perform diagnosis (false). ChartNav did not
> recommend treatment (false). ChartNav did not place orders
> (false). ChartNav did not send referrals (false). ChartNav did
> not send patient messages (false). ChartNav did not bill or code
> (false). ChartNav did not integrate with any device (false).
> ChartNav did not perform remote patient monitoring (false).
> ChartNav did not auto-sign (false)."

Add the Fundus V1 caveat aloud:

> "The Fundus Drawing Assist enforces the same posture through the
> safety banner, the warnings panel, provider review/sign, the
> signed-lock state, and the claim scanners — without a
> per-response forbidden-actions object today."

**Closing narration:**
> "ChartNav is a provider-reviewed workflow layer. Not a certified
> EHR. Not HIPAA-certified out of the box. Not an autonomous agent.
> Provider review and sign-off are mandatory at every step. Happy
> to take questions."

Pivot to Q&A using `docs/demo/phase-61-buyer-qa-safe-answers.md`.

---

## Total runtime

| Section | Estimated duration |
|---|---|
| 1. Workspace orientation | 1 min |
| 2. Technician workup & vitals | 3 min |
| 3. Ophthalmology intake | 30 sec (folded into § 2) |
| 4. VisitDraft Assist | 3 min |
| 5. Fundus Drawing Assist | 2.5 min |
| 6. Warnings recap | 30 sec |
| 7. Provider review | 30 sec |
| 8. Sign / lock | 30 sec |
| 9. Audit / safety posture | 1 min |
| 10. What ChartNav did NOT do + closing | 1 min |
| **Total** | **≈ 13 min 30 sec** |

The Phase 61 runbook targets 12 minutes — Phase 62's script is a
little longer because it captures the warning-demo explicitly per
surface. Operators may compress § 6 if running short.

---

## Related documents

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` — master runbook.
- `docs/demo/phase-61-buyer-qa-safe-answers.md` — 20-question Q&A.
- `docs/demo/phase-62-demo-dry-run-report.md` — dry-run report template.
- `docs/demo/phase-62-screenshot-shot-list.md` — 30 screenshots.
- `docs/demo/phase-62-video-clip-shot-list.md` — 12 video clips.
- `docs/build/current-product-truth.md` — single source of truth.
