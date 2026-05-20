# Phase 62 — Demo Dry-Run Report (Template)

> Operators fill in this template per dry run. Save the completed
> copy under `artifacts/phase-62/dry-runs/YYYY-MM-DD/report.md`
> (gitignored by default; keep locally or attach to an internal
> issue). **Never paste real PHI or any secret value into a
> completed copy.**

## 0. Header

| Field | Value |
|---|---|
| Dry-run date | YYYY-MM-DD |
| Operator (name, role) |  |
| Narrator (if separate) |  |
| Repo SHA (`git log --oneline -1`) |  |
| Branch (should be `main`) |  |
| Environment (`CHARTNAV_ENV`) | `local` / `dev` / `demo` / `test` |
| Browser + version |  |
| Display resolution |  |
| Audience (internal only / dress rehearsal / customer) |  |

## 1. Commands run (pre-flight)

| # | Command | Result | Notes |
|---|---|---|---|
| 1 | `git checkout main && git pull --ff-only origin main` | pass / fail |  |
| 2 | `git status --short` | clean / dirty |  |
| 3 | `python3 scripts/check_runtime_safety.py` | PASS / FAIL |  |
| 4 | `bash scripts/check_commercial_claims.sh` | PASSED / FAIL |  |
| 5 | `bash scripts/check_website_claims.sh` | PASSED / FAIL |  |
| 6 | `bash scripts/check_demo_claims.sh` | PASSED / FAIL |  |
| 7 | `bash scripts/test_claim_policy_fixtures.sh` | PASS / FAIL |  |
| 8 | `bash scripts/check_alembic_safety.sh` | PASSED / FAIL |  |

If **any** pre-flight returns FAIL, **halt the dry run** and resolve
before continuing.

## 2. App / API / frontend startup

| Step | Command (example) | Result | Notes |
|---|---|---|---|
| API up | `make boot` or `docker compose up -d api` | started / failed |  |
| Frontend up | `cd apps/web && npm run dev` | started / failed |  |
| API smoke | `curl -s http://localhost:8000/health` | 200 / failed |  |
| Frontend smoke | open `http://localhost:5173` | renders / failed |  |
| Demo reset | `bash scripts/reset_demo_state.sh` | ran / failed |  |

## 3. Feature-by-feature walkthrough

### 3.1 Workspace orientation

- [ ] Demo encounter URL opens.
- [ ] Patient header shows `Morgan Lee · PT-1001 · Encounter #1 · Dr. Carter`.
- [ ] Demographic strip shows the explicit empty-state copy.
- [ ] All 9 tabs visible in the tab bar.

Result: **pass / fail**. Notes:

### 3.2 Technician Workup & Structured Vitals

- [ ] Clinical / Ophthalmology tab opens.
- [ ] "Technician Workup & Vitals" wide card is the first card.
- [ ] **Load fake demo vitals** populates the form with synthetic values.
- [ ] Live BMI display updates from height + weight.
- [ ] Save draft → status `Draft`.
- [ ] Save & mark entered → status `Entered`.
- [ ] Cleared systolic + Save → warnings panel surfaces the
      "diastolic missing" prompt.
- [ ] Restored values or new workup → warning clears.
- [ ] "What ChartNav did NOT do" card lists 9 forbidden actions
      each as `(false)`.
- [ ] Mark Reviewed → status `Reviewed`; attestation block appears.
- [ ] Sign disabled until attestation checkbox ticked.
- [ ] Sign & Lock Workup → green "Workup signed · locked" banner
      with timestamp + signer.

Result: **pass / fail**. Notes:

### 3.3 Provider-Reviewed VisitDraft Assist (internal: Ambient Documentation Assist)

> **Narration vs on-screen label.** Operator narrates "Provider-
> Reviewed VisitDraft Assist". The card's **on-screen title today
> still reads "Provider-Reviewed Ambient Documentation Assist"** —
> the UI rename is a separate follow-up phase. The checklist below
> verifies the card by its current on-screen title; the operator
> uses the buyer narration label out loud.

- [ ] Documentation / EMR/EHR tab opens.
- [ ] Wide card titled **"Provider-Reviewed Ambient Documentation
      Assist"** on screen (narrated as the Provider-Reviewed
      VisitDraft Assist) is visible below the stepper + existing
      NoteWorkspace.
- [ ] Safety banner contains: "Draft from fake/demo encounter
      transcript", "Provider review required", "Does not diagnose",
      "Does not place orders", "Does not send referrals or patient
      messages", "Does not bill or code", "Not for real PHI".
- [ ] **Load demo sample (fake data)** populates the textarea with
      the synthetic transcript.
- [ ] **Generate provider-review draft** → status `Ready for Review`.
- [ ] Structured-facts card renders (chief complaint, HPI summary,
      visual acuity, IOP, imaging metadata, assessment context,
      plan-as-stated).
- [ ] "What ChartNav did NOT do" card lists 7 forbidden actions
      each as `(false)`.
- [ ] Draft note text begins "DRAFT — provider review required."
- [ ] Missing-information demo: `Demo only. Patient seen for routine
      visit.` → 3 missing items.
- [ ] Mark Reviewed → status `Reviewed`; attestation appears.
- [ ] Sign disabled until checkbox ticked.
- [ ] Sign & Lock Draft → green "Draft signed · locked" banner.

Result: **pass / fail**. Notes:

### 3.4 Provider-Reviewed Fundus Drawing Assist (internal: Fundus Charting V1)

- [ ] Imaging tab opens.
- [ ] **Fundus charts** wide card visible.
- [ ] Default laterality is `OD · Right`.
- [ ] Safety banner contains: "Draft from clinician-entered
      findings", "Provider review required", "Not image
      interpretation", "Does not diagnose".
- [ ] `Horseshoe tear 10:30 OD` chip populates the textarea.
- [ ] **Generate Chart** → SVG preview renders with clock-hour
      labels + glyph at 11 o'clock + legend strip.
- [ ] Missing-laterality demo with `lattice degeneration at 6` →
      warnings panel surfaces the missing-laterality warning.
- [ ] Mark Reviewed → status `Reviewed`.
- [ ] Sign attestation gates the Sign button.
- [ ] Sign & Lock Chart → green "Chart signed · locked" banner.
- [ ] **Important:** the Fundus card does **not** render a
      "What ChartNav did NOT do" panel and the API does **not**
      return a `forbidden_actions` field. The operator must not
      claim it does.

Result: **pass / fail**. Notes:

### 3.5 Provider review across all three surfaces

- [ ] Each of Vitals / VisitDraft / Fundus shows status timeline
      pills lighting the Reviewed pill at the review step.

Result: **pass / fail**. Notes:

### 3.6 Sign / lock across all three surfaces

- [ ] Each shows the consistent signed-lock posture: green banner,
      timestamp, signer id, edit controls absent from DOM.
- [ ] Optional: try `curl -X PATCH` (or browser dev-tools fetch) on
      one signed row — backend returns 409.

Result: **pass / fail**. Notes:

### 3.7 Safety / audit posture

- [ ] Side-terminal run of `python3 scripts/check_runtime_safety.py`
      prints `PASS - no unsafe runtime combinations detected.`
- [ ] `docs/release/release-evidence-checklist.md` open in editor.
- [ ] `docs/build/current-product-truth.md` open in editor.

Result: **pass / fail**. Notes:

## 4. Screenshot capture status

Use `docs/demo/phase-62-screenshot-shot-list.md` as the source.

| ID | Description | Captured? | File path |
|---|---|---|---|
| 01 | Clinical workspace landing |  | `artifacts/phase-62/screenshots/01_workspace_landing.png` |
| 02 | Patient header / fake demo patient |  | `02_patient_header.png` |
| 03 | Tab navigation (Clinical / Documentation / Imaging) |  | `03_tab_navigation.png` |
| 04 | Empty vitals workup form |  | `04_vitals_empty_form.png` |
| 05 | Fake demo vitals loaded |  | `05_vitals_loaded.png` |
| 06 | BMI calculated display |  | `06_vitals_bmi.png` |
| 07 | Partial BP warning |  | `07_vitals_partial_bp_warning.png` |
| 08 | Vitals "What ChartNav did NOT do" |  | `08_vitals_what_chartnav_did_not_do.png` |
| 09 | Vitals review state |  | `09_vitals_review.png` |
| 10 | Vitals signed/locked |  | `10_vitals_signed_lock.png` |
| 11 | Empty VisitDraft Assist panel |  | `11_visitdraft_empty.png` |
| 12 | Fake VisitDraft transcript loaded |  | `12_visitdraft_transcript.png` |
| 13 | Generated structured facts |  | `13_visitdraft_structured_facts.png` |
| 14 | Draft note text with DRAFT prefix |  | `14_visitdraft_draft_note.png` |
| 15 | Safety flags / missing info |  | `15_visitdraft_safety_flags.png` |
| 16 | VisitDraft "What ChartNav did NOT do" |  | `16_visitdraft_what_chartnav_did_not_do.png` |
| 17 | VisitDraft Reviewed state |  | `17_visitdraft_reviewed.png` |
| 18 | VisitDraft signed/locked |  | `18_visitdraft_signed_lock.png` |
| 19 | Empty fundus charting panel |  | `19_fundus_empty.png` |
| 20 | Clinician-entered findings text |  | `20_fundus_findings.png` |
| 21 | Generated fundus SVG preview |  | `21_fundus_svg.png` |
| 22 | Fundus legend |  | `22_fundus_legend.png` |
| 23 | Fundus missing-laterality warning |  | `23_fundus_warning.png` |
| 24 | Fundus review / sign attestation |  | `24_fundus_attestation.png` |
| 25 | Fundus signed/locked |  | `25_fundus_signed_lock.png` |
| 26 | Runtime safety validator PASS in terminal |  | `26_runtime_safety_terminal.png` |
| 27 | Claim scanners PASS in terminal |  | `27_claim_scanners_terminal.png` |
| 28 | Alembic safety PASS in terminal |  | `28_alembic_safety_terminal.png` |
| 29 | Release-evidence checklist |  | `29_release_evidence_checklist.png` |
| 30 | Product-truth safety statements |  | `30_product_truth_safety_statements.png` |

Total captured: ___ / 30.

## 5. Video clip capture status

Use `docs/demo/phase-62-video-clip-shot-list.md` as the source.

| ID | Description | Captured? | File path |
|---|---|---|---|
| 01 | Workspace orientation |  | `artifacts/phase-62/video-clips/01_workspace_orientation.mov` |
| 02 | Technician Workup & Vitals intake |  | `02_vitals_intake.mov` |
| 03 | BMI calculation + warning prompt |  | `03_vitals_bmi_warning.mov` |
| 04 | Vitals review / sign / lock |  | `04_vitals_review_sign_lock.mov` |
| 05 | VisitDraft Assist transcript to draft |  | `05_visitdraft_transcript_to_draft.mov` |
| 06 | VisitDraft safety flags + "What ChartNav did NOT do" |  | `06_visitdraft_safety_did_not_do.mov` |
| 07 | VisitDraft review / sign / lock |  | `07_visitdraft_review_sign_lock.mov` |
| 08 | Fundus Drawing Assist clinician findings to diagram |  | `08_fundus_findings_to_diagram.mov` |
| 09 | Fundus warning prompt |  | `09_fundus_warning.mov` |
| 10 | Fundus review / sign / lock |  | `10_fundus_review_sign_lock.mov` |
| 11 | Runtime safety validator + claim scanners |  | `11_safety_terminal.mov` |
| 12 | Full 3-minute buyer-demo highlight reel |  | `12_highlight_reel_3min.mov` |

Total captured: ___ / 12.

## 6. Known issues encountered during the dry run

| # | Severity (P1 / P2 / P3) | Module | Description | Action |
|---|---|---|---|---|

Severity guide:
- **P1** — buyer-demo blocker (any forbidden phrasing, any UI bug
  that allows sign without attestation, any safety-gate FAIL,
  visible secret, real-PHI exposure).
- **P2** — confusing operator experience but not a buyer-safety
  issue. Fix before next dry run.
- **P3** — nit / wording polish. Track in the next docs PR.

## 7. Go / no-go for buyer demo

- **Pre-flight gates** (all 8 commands in § 1 PASSED): yes / no
- **Feature walkthrough** (all 7 sections in § 3 pass): yes / no
- **Screenshots captured** (≥ 25 of 30): yes / no
- **Video clips captured** (≥ 8 of 12): yes / no
- **No P1 issue open**: yes / no

Overall decision: **GO** / **NO-GO**

Approver: _______________________

Date: _______________________

## 8. Follow-up repairs

| # | Owner | Action | Target |
|---|---|---|---|

---

## Related documents

- `docs/demo/phase-62-end-to-end-demo-visit-script.md` — visit scenario.
- `docs/demo/phase-62-screenshot-shot-list.md` — capture spec per screenshot.
- `docs/demo/phase-62-video-clip-shot-list.md` — capture spec per clip.
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` — packet index.
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` — master runbook.
- `docs/demo/phase-61-buyer-demo-checklist.md` — pre/during/post checklist.
