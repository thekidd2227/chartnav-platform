# Phase 62 — Buyer Demo Screenshot Shot List

> 30 screenshots required for the buyer-demo evidence packet. All
> captures are **`[MANUAL CAPTURE REQUIRED]`** by the operator on
> their local iMac; the sandbox cannot capture display output.
> Save every PNG under `artifacts/phase-62/screenshots/` with the
> exact filename listed. Use the seeded fake demo patient
> (**Morgan Lee · PT-1001 · Encounter #1 · Dr. Carter**); never
> capture real PHI.

## Capture conventions

- **Browser:** Chrome / Edge / Firefox at 100% zoom; viewport at
  least 1440×900.
- **Identity:** logged in as `clin@chartnav.local` (clinician) by
  default. Use `tech@chartnav.local` only where the shot lists below
  call for the technician identity.
- **Format:** PNG, full-window capture (no OS chrome / dock if
  avoidable).
- **Redaction:** N/A — all data is fake. Confirm no real env-var
  value, no real API key, no real vendor org id is visible in any
  terminal screenshot.
- **Filename:** lowercase, snake_case, prefixed with the 2-digit ID,
  saved under `artifacts/phase-62/screenshots/`.

---

## A. Platform / workspace

### 01 — Clinical workspace landing view

- **File:** `artifacts/phase-62/screenshots/01_workspace_landing.png`
- **Screen / module:** SPA root at the demo encounter URL.
- **Purpose:** First impression. Shows the workspace shell.
- **Must be visible:** Patient header (`Morgan Lee · PT-1001 ·
  Encounter #1 · Dr. Carter`); 9 tabs in the tab bar; Overview tab
  selected.
- **Must NOT be visible:** No real name / DOB / phone / address;
  no production env banner; no real API key in any extension/console
  overlay.
- **Approved narration:** "ChartNav opens to a provider-reviewed
  workspace."

### 02 — Patient header / fake demo patient context

- **File:** `02_patient_header.png`
- **Screen / module:** Patient header strip, zoomed in.
- **Purpose:** Document the fake-data discipline.
- **Must be visible:** "Morgan Lee", "PT-1001", "Encounter #1",
  "Dr. Carter", "Location: Demo Clinic"; the demographic strip's
  empty-state copy ("Not available in demo / Not recorded / No
  allergies recorded / No active meds recorded / Not scheduled").
- **Must NOT be visible:** Real demographic data.
- **Approved narration:** "Morgan Lee is a fake demo patient. The
  'Not recorded' fields are intentional empty state."

### 03 — Tab navigation (Clinical / Documentation / Imaging)

- **File:** `03_tab_navigation.png`
- **Screen / module:** Tab bar.
- **Purpose:** Show the buyer the three tabs the demo will visit.
- **Must be visible:** All 9 tabs, with Clinical / Documentation /
  Imaging visually grouped if possible.
- **Must NOT be visible:** Any "Billing" tab (Phase 19F removed it).
- **Approved narration:** "We'll visit three tabs: Clinical for
  vitals, Documentation for the VisitDraft Assist, Imaging for the
  Fundus Drawing Assist."

---

## B. Technician Workup & Structured Vitals

### 04 — Empty vitals/workup form

- **File:** `04_vitals_empty_form.png`
- **Screen / module:** Clinical / Ophthalmology tab → Technician
  Workup & Vitals card.
- **Purpose:** Show the panel shell before any data is entered.
- **Must be visible:** Safety banner ("Structured intake for
  provider review… Does not diagnose… Not for real PHI… No device
  integration"); "Load fake demo vitals" button; "Save draft"
  button; status timeline pills at Draft.
- **Must NOT be visible:** Any populated form value.
- **Approved narration:** "Structured intake for provider review.
  Manually entered — no device integration."

### 05 — Fake demo vitals loaded

- **File:** `05_vitals_loaded.png`
- **Screen / module:** Same panel after clicking **Load fake demo
  vitals**.
- **Purpose:** Show the synthetic values that drive the demo.
- **Must be visible:** Populated General vitals + Ophthalmology
  workup sections; BP 122/78 sitting left arm; pulse 72; SpO2 98 %;
  VA OD 20/20, VA OS 20/25; IOP 14 / 13.
- **Must NOT be visible:** Any real value.
- **Approved narration:** "Fake demo values loaded by the sample
  button."

### 06 — BMI calculated display

- **File:** `06_vitals_bmi.png`
- **Screen / module:** Same panel, with BMI tile visible.
- **Purpose:** Demonstrate server-calculated BMI.
- **Must be visible:** Height 70 in + Weight 165 lb + **BMI
  (calculated)** showing ~23.7 (server result). The "BMI
  (calculated)" tile label.
- **Must NOT be visible:** No manual BMI input field.
- **Approved narration:** "BMI is server-calculated from height and
  weight. No manual BMI entry."

### 07 — Partial BP warning

- **File:** `07_vitals_partial_bp_warning.png`
- **Screen / module:** Same panel with systolic cleared.
- **Purpose:** Show the review-prompt language.
- **Must be visible:** Warnings panel surfacing "Blood pressure
  diastolic captured but systolic missing; please add systolic
  before signing." (or the symmetric variant); empty systolic
  field.
- **Must NOT be visible:** Any diagnostic language. Never narrate
  "hypertension" / "hypotension" / "low BP" / "high BP".
- **Approved narration:** "Out-of-range or partial values surface
  as review prompts, never as a diagnosis."

### 08 — "What ChartNav did NOT do" panel (Vitals)

- **File:** `08_vitals_what_chartnav_did_not_do.png`
- **Screen / module:** Same panel, scrolled to the actions-summary
  card.
- **Purpose:** Show the closed-actions list.
- **Must be visible:** 9 lines each ending in `(false)`: diagnosis,
  treatment recommendation, orders, referrals, patient messages,
  billing or coding, device integration, remote patient monitoring,
  auto-sign.
- **Must NOT be visible:** Any `(true)` entry.
- **Approved narration:** "Nine forbidden actions, each `(false)`
  on every Vitals response."

### 09 — Vitals review state

- **File:** `09_vitals_review.png`
- **Screen / module:** Same panel after **Mark Reviewed**.
- **Purpose:** Show the Reviewed pill + attestation block surfaced.
- **Must be visible:** Status timeline with Reviewed highlighted;
  purple attestation block visible with "I attest that I have
  reviewed this technician workup and the vitals values are
  accurate. Signing will lock the workup — signed workups are
  immutable."; "Sign & Lock Workup" button disabled.
- **Must NOT be visible:** Sign button enabled prior to attestation.
- **Approved narration:** "Reviewed is a workflow checkpoint, not
  the final signature."

### 10 — Vitals signed/locked

- **File:** `10_vitals_signed_lock.png`
- **Screen / module:** Same panel after Sign & Lock.
- **Purpose:** Show the locked posture.
- **Must be visible:** Green "Workup signed · locked" banner with
  timestamp + signer id; "Signed workups are immutable."; no edit
  buttons in the DOM.
- **Must NOT be visible:** Any edit/save/review/sign control.
- **Approved narration:** "Signed workups are immutable; backend
  returns 409 on any further mutation."

---

## C. Provider-Reviewed VisitDraft Assist

### 11 — Empty VisitDraft Assist panel

- **File:** `11_visitdraft_empty.png`
- **Screen / module:** Documentation / EMR-EHR tab →
  Provider-Reviewed VisitDraft Assist wide card (below stepper).
- **Purpose:** Show the panel shell + safety banner.
- **Must be visible:** Safety banner with all six required clauses
  ("Draft from fake/demo encounter transcript", "Provider review
  required", "Does not diagnose", "Does not place orders", "Does
  not send referrals or patient messages", "Does not bill or
  code", "Not for real PHI"); empty transcript textarea; "Load
  demo sample (fake data)" button.
- **Must NOT be visible:** Any populated transcript.
- **Approved narration:** "Provider-Reviewed VisitDraft Assist —
  the clinician's transcript drives the draft."

### 12 — Fake VisitDraft transcript loaded

- **File:** `12_visitdraft_transcript.png`
- **Screen / module:** Same panel after **Load demo sample**.
- **Purpose:** Show the synthetic transcript.
- **Must be visible:** Textarea filled with "Demo transcript
  only. Patient reports blurry vision in the right eye for two
  weeks…"; "Generate provider-review draft" button.
- **Must NOT be visible:** Any real transcript content.

### 13 — Generated structured facts

- **File:** `13_visitdraft_structured_facts.png`
- **Screen / module:** Same panel after generation.
- **Purpose:** Show the closed-schema structured-facts card.
- **Must be visible:** Chief complaint, HPI summary, visual acuity,
  IOP, imaging metadata, assessment context, plan-as-stated —
  populated from the demo transcript.
- **Must NOT be visible:** Any diagnostic conclusion / treatment
  recommendation field.

### 14 — Draft note text with provider-review language

- **File:** `14_visitdraft_draft_note.png`
- **Screen / module:** Same panel, "Draft note text" details
  expanded.
- **Purpose:** Show the literal DRAFT prefix.
- **Must be visible:** First line beginning "DRAFT — provider
  review required. ChartNav drafted this from a fake / demo
  encounter transcript…"
- **Must NOT be visible:** Any "FINAL" / "SIGNED" marker pre-sign.

### 15 — Safety flags / missing information

- **File:** `15_visitdraft_safety_flags.png`
- **Screen / module:** Same panel with the missing-information demo
  payload (`Demo only. Patient seen for routine visit.`).
- **Purpose:** Show the closed-schema "missing information" list.
- **Must be visible:** Missing-information card listing 3 items
  (chief complaint, visual acuity, intraocular pressure each as
  "Please supply or confirm.").
- **Must NOT be visible:** Any inferred-diagnosis text.

### 16 — "What ChartNav did NOT do" panel (VisitDraft)

- **File:** `16_visitdraft_what_chartnav_did_not_do.png`
- **Screen / module:** Same panel, scrolled to the actions-summary
  card.
- **Purpose:** Show the closed-actions list for VisitDraft Assist.
- **Must be visible:** 7 lines each ending in `(false)`:
  diagnosis, orders, referrals, patient_message, billing_or_coding,
  auto_sign, image_interpretation.
- **Must NOT be visible:** Any `(true)`.

### 17 — VisitDraft Reviewed state

- **File:** `17_visitdraft_reviewed.png`
- **Screen / module:** Same panel after **Mark Reviewed**.
- **Purpose:** Show the attestation block.
- **Must be visible:** Reviewed pill highlighted; purple
  attestation block reading "I attest that I have reviewed this
  draft note and it accurately reflects my clinical findings
  from the fake / demo transcript. Signing will lock the draft —
  signed drafts are immutable."; Sign disabled pre-tick.

### 18 — VisitDraft signed/locked

- **File:** `18_visitdraft_signed_lock.png`
- **Screen / module:** Same panel after Sign & Lock.
- **Purpose:** Locked posture.
- **Must be visible:** Green "Draft signed · locked" banner with
  timestamp; "Signed drafts are immutable."
- **Must NOT be visible:** Edit / Review / Sign controls.

---

## D. Provider-Reviewed Fundus Drawing Assist

### 19 — Empty fundus charting panel

- **File:** `19_fundus_empty.png`
- **Screen / module:** Imaging tab → Fundus charts wide card.
- **Purpose:** Show the panel shell + safety banner.
- **Must be visible:** Safety banner ("Draft from clinician-entered
  findings", "Provider review required", "Not image
  interpretation", "Does not diagnose"); empty findings textarea;
  4 demo-safe sample chips; OD / OS / OU laterality radio group
  with OD selected.
- **Must NOT be visible:** Any fundus photo / OCT image.
  **Important:** the Fundus card does **not** render a "What
  ChartNav did NOT do" panel — do **not** capture a screenshot of
  such a panel.

### 20 — Clinician-entered findings text

- **File:** `20_fundus_findings.png`
- **Screen / module:** Same panel after the `Horseshoe tear 10:30
  OD` chip is clicked.
- **Purpose:** Show the textarea filled.
- **Must be visible:** "horseshoe tear at 10:30 OD" in the
  textarea; OD still selected.

### 21 — Generated fundus SVG preview

- **File:** `21_fundus_svg.png`
- **Screen / module:** Same panel after **Generate Chart**.
- **Purpose:** Show the deterministic structured drawing.
- **Must be visible:** SVG with concentric rings, 12 clock-hour
  labels, horseshoe-tear glyph at approximately the 11 o'clock
  position; status timeline pill at Draft.
- **Must NOT be visible:** Any photo / OCT / camera image.

### 22 — Fundus legend

- **File:** `22_fundus_legend.png`
- **Screen / module:** Same panel, legend strip below the SVG.
- **Purpose:** Document the finding-type colour key.
- **Must be visible:** Legend strip with at least the "Horseshoe
  Tear" entry and its colour swatch.

### 23 — Fundus missing-laterality warning

- **File:** `23_fundus_warning.png`
- **Screen / module:** Same panel after loading the `lattice
  degeneration at 6` sample.
- **Purpose:** Show review-prompt language for fundus.
- **Must be visible:** Warnings panel surfacing the missing-
  laterality warning.
- **Must NOT be visible:** Any diagnostic language about lattice
  degeneration.

### 24 — Fundus review / sign attestation

- **File:** `24_fundus_attestation.png`
- **Screen / module:** Same panel after **Mark Reviewed**.
- **Purpose:** Show the attestation block.
- **Must be visible:** Purple attestation block "I attest that I
  have reviewed this fundus chart and it accurately reflects my
  clinical findings. Signing will lock the chart — signed charts
  are immutable."; Sign disabled pre-tick.

### 25 — Fundus signed/locked

- **File:** `25_fundus_signed_lock.png`
- **Screen / module:** Same panel after Sign & Lock.
- **Purpose:** Locked posture.
- **Must be visible:** Green "Chart signed · locked" banner;
  "Signed charts are immutable."
- **Must NOT be visible:** Edit / Review / Sign controls; any
  `forbidden_actions` panel.

---

## E. Evidence / safety

### 26 — Runtime safety validator passing in terminal

- **File:** `26_runtime_safety_terminal.png`
- **Screen / module:** Side terminal.
- **Purpose:** Show the live runtime gate.
- **Must be visible:** Command line `python3
  scripts/check_runtime_safety.py` followed by
  `ChartNav runtime safety validator` and `PASS - no unsafe
  runtime combinations detected.`
- **Must NOT be visible:** Any real env-var value, any API key,
  any vendor organisation id. **Do not** `env | grep CHARTNAV`
  before this screenshot if any real secret is set.

### 27 — Claim scanners passing in terminal

- **File:** `27_claim_scanners_terminal.png`
- **Screen / module:** Side terminal.
- **Purpose:** Document the claim-policy posture.
- **Must be visible:** All three `bash scripts/check_*claims.sh`
  invocations and the `PASSED — 0 fail / 0 warn.` lines (and the
  `PASSED — 0 positive-claim hits across N demo file(s).` line
  from the demo scanner).
- **Must NOT be visible:** Any forbidden-phrase example text
  (e.g., do not pipe the scanner output through `grep -i hipaa`).

### 28 — Alembic safety passing in terminal

- **File:** `28_alembic_safety_terminal.png`
- **Screen / module:** Side terminal.
- **Purpose:** Document the migration-safety posture.
- **Must be visible:** `bash scripts/check_alembic_safety.sh`
  printing `ok - exactly one Alembic head`, `ok - alembic upgrade
  head succeeds against local test DB`, `ok - no obvious
  SQLite-only/raw CREATE TABLE migration patterns found`,
  `PASSED - Alembic safety checks completed.`

### 29 — Release-evidence checklist

- **File:** `29_release_evidence_checklist.png`
- **Screen / module:** Text editor with
  `docs/release/release-evidence-checklist.md` open.
- **Purpose:** Document the release-gate template.
- **Must be visible:** Required Results table header + a few rows.

### 30 — Product-truth safety statements

- **File:** `30_product_truth_safety_statements.png`
- **Screen / module:** Text editor with
  `docs/build/current-product-truth.md` open, scrolled to the
  "Hard Safety Statements" section.
- **Purpose:** Document the single source of truth.
- **Must be visible:** The Hard Safety Statements list (the bullet
  list at the top of the doc).

---

## Capture order recommendation

To minimise app restarts, capture screenshots in groups:

1. **Group A** (workspace shell) — 01, 02, 03 first.
2. **Group B** (Vitals) — 04 → 10 in order.
3. **Group C** (VisitDraft) — 11 → 18 in order.
4. **Group D** (Fundus) — 19 → 25 in order.
5. **Group E** (terminal + editor) — 26 → 30 last.

If a screenshot reveals a forbidden phrase or real-PHI shape,
**discard the file** and re-capture after fixing the source.

## Related documents

- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-video-clip-shot-list.md`
- `docs/demo/phase-62-demo-dry-run-report.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-demo-checklist.md`
