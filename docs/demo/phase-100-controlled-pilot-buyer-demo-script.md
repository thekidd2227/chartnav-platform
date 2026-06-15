# Phase 100 — Controlled Pilot Buyer Demo Script

**Status:** operator demo script
**Date:** 2026-06-15
**Audience:** ChartNav operator running a controlled buyer demo on
the fake-data stack prior to a controlled-pilot launch decision
**Branch:** `feature/phase-100-controlled-pilot-launch-gate`

## Purpose

A single demo script the operator can rehearse against the
fake-data demo before, during, and after a Phase 100 controlled-
pilot launch decision. Two walkthrough lengths are included so the
operator can right-size the meeting.

This script does **not** introduce new claims. Every line below
has been audited against the Phase 93 forbidden-narration list and
the Phase 24c demo runbook.

## Hard rules

- **No real PHI** — the demo uses synthetic seed data only.
  Display "demo mode — no real PHI" prominently. If a buyer asks
  to substitute their own patient, decline and reset to seed.
- **No production LLM** — every LLM-shaped surface is
  deterministic / fake adapter / disabled. Do not enable a live
  vendor on a buyer call.
- **No live vendor scripts** — do not run
  `dev_live_watsonx_eval.py`, do not enable a live STT vendor, do
  not point at a real FHIR endpoint.
- **No autonomous-decision narration** — see Phase 93 dry-run
  runbook's forbidden-narration list. Do not say it, do not write
  it, do not show it on a slide.

## Roles in the rehearsal

| Role | Identity header | Purpose |
|---|---|---|
| Operator (presenter) | `clin@chartnav.local` | drives the demo, narrates each step |
| Admin (optional shadow) | `admin@chartnav.local` | covers admin role surfaces if the buyer asks |
| Technician (optional shadow) | `tech@chartnav.local` | covers vitals workup if the buyer asks |
| Reviewer (optional shadow) | `rev@chartnav.local` | covers read-only review path if the buyer asks |

## Pre-demo (T-15 minutes)

| # | Step | Expected |
|---|---|---|
| P1 | Confirm pre-flight per Phase 93 dry-run runbook Section 0 | every row PASS |
| P2 | `bash scripts/reset_demo_state.sh` | exit 0; non-local DB refused |
| P3 | Backend boots on 8765, frontend boots on 5173 | both 200 OK |
| P4 | Browser shows the encounter list for `clin@chartnav.local`, demo banner visible | demo banner present |
| P5 | Mute notifications, close unrelated tabs | screen-share-safe |

## 15-minute walkthrough

A focused buyer demo that proves the Phase 1 spine + the most
buyer-relevant Phase 2 panels. Target audience: clinical owner +
administrator.

### 0:00 — 0:30 · Open the demo

- Show the encounter list. Identify it explicitly as a fake-data
  demo: "This is the synthetic demo environment. There is no real
  patient data anywhere on this screen."
- Open encounter #1.

### 0:30 — 2:00 · Patient + encounter header + workspace state

- Show the patient-encounter header. Read the seeded identifiers
  aloud: "Morgan Lee, MRN PT-1001, encounter #1."
- Show the Phase 91 visit-mode + active-laterality ribbon. Read
  the current visit mode aloud: "follow-up."
- Switch the active laterality to OD, then back to OU. Narrate:
  "Provider-driven, never inferred."

### 2:00 — 4:00 · Vitals workup (Phase 60)

- Open Clinical tab → Vitals Workup.
- Record OD IOP = 18. Record OS IOP = 20.
- Narrate: "Structured capture by the technician. The provider
  reviews and signs."
- Sign the vitals workup. Show the audit row.
- Narrate: "Every signing event lands in the audit trail with
  metadata only — no clinical body text, no transcript text, no
  numeric values in the detail field."

### 4:00 — 7:00 · Documentation tab (scribe → review → finalize)

- Open Documentation tab. Show the stepper.
- Run a deterministic scribe session (fake adapter only). Narrate:
  "ChartNav's scribe drafts. The clinician edits and signs.
  Provider review is required before anything is final."
- Sign the visit draft.
- Open the imaging tab → OD/OS canvas. Plot one annotation. Sign
  the fundus chart.
- Narrate: "Fundus charting is provider-entered findings — ChartNav
  does not interpret the photograph."

### 7:00 — 10:00 · Overview tab — Phase 86 + Phase 91 + Phase 92

- Switch to Overview tab.
- Walk the Phase 86 adaptive panels in their resolver order for the
  encounter's profile. Pause briefly on each:
  - Provider Action Queue, Note Validation Rail
  - Retina Visit Summary, Retina Visit Packet
  - Anti-VEGF Injection Rail
  - Glaucoma Progression Cockpit
  - Cataract Surgical Workflow
  - Disease Staging
  - Medication Safety (Phase 85 + Phase 90)
  - Quality Intelligence
  - Imaging Metadata
  - Advanced Clinical Intelligence (Phase 92)
- Narrate consistently on each panel: "Provider-reviewed metadata
  projection. ChartNav does not diagnose, does not interpret
  images, does not recommend treatment, does not submit anything."

### 10:00 — 12:00 · Advanced Clinical Intelligence (Phase 92)

- Expand the Advanced Clinical Intelligence panel.
- Show the four sections: Retina, Glaucoma, Cataract, FHIR export
  readiness.
- Point at the OD/OS chips and the insufficient_data banners where
  applicable.
- Open the FHIR section. Read aloud the chips: "Packet renderable.
  Submission: not submitted. Transport: none."
- Read one safety boundary aloud: "ChartNav does not submit,
  transmit, or post anything to any registry, payer, CMS endpoint,
  IRIS feed, or EHR."

### 12:00 — 13:30 · Retina visit packet export

- Open the Retina Visit Packet panel.
- Download the packet JSON.
- Open it in a text viewer; scroll to `schema_version`,
  `safety_boundaries`, and `advanced_clinical_intelligence_summary`.
- Narrate: "Metadata-only export. The artifact hashes prove the
  packet was issued against this exact state."

### 13:30 — 15:00 · Close + buyer questions

- Switch to Communications tab. Show the internal-staff-only note
  surface; read aloud: "Demo-local internal chat. No patient-send
  surface. Stored only on this device."
- Close on the safety boundaries banner + the
  demo-environment disclosure.
- Open buyer Q&A. Reference
  `docs/demo/phase-61-buyer-qa-safe-answers.md` for any sensitive
  question.

## 30-minute walkthrough

The 15-minute script above, plus the following four sections.
Target audience: clinical owner + administrator + security owner.

### 15:00 — 18:00 · Disease staging + medication safety deep-dive

- Open Disease Staging panel. Add an AMD AREDS Category 3 row.
- Show how it surfaces in the retina summary stage history.
- Open Phase 90 ophthalmic Medication Safety panel. Show the
  per-eye counts, the active safety event count, and the boundary
  note pinned at the bottom.
- Narrate: "Counts only. ChartNav does not write prescriptions,
  does not recommend medication changes, does not message the
  pharmacy."

### 18:00 — 22:00 · Cataract workflow + conversion funnel

- Open Cataract Surgical Workflow panel.
- Add a planned-surgery record for OD with a near-future date.
- Walk the conversion funnel chips: any record → planned date →
  biometry → consent → post-op day 1.
- Narrate: "Provider-reviewed funnel. ChartNav does not schedule
  surgery, does not recommend IOL choices, does not auto-bill."

### 22:00 — 26:00 · Security boundaries + audit

- Open a vitals row → show the metadata-only audit trail.
- Open `docs/security/chartnav-real-phi-readiness-status.md` (or
  the corresponding security packet PDF) in a second tab.
- Read the bottom-line statement aloud: "ChartNav is not
  HIPAA-certified, not a certified EHR, does not replace your EHR,
  does not process real PHI in this build."
- Reference the Phase 93 real-PHI readiness review and the
  Phase 100 no-real-PHI attestation by file path.

### 26:00 — 30:00 · Release + pilot readiness

- Switch to a terminal. Run
  `bash scripts/release/phase100_controlled_pilot_launch_gate.sh`
  (or show a prior dated artifact bundle).
- Show the summary table and the `go-no-go.txt` recommendation.
- Open
  `docs/pilot/phase-100-controlled-pilot-launch-gate.md` and walk
  the signature page.
- Hand the buyer the Phase 100 evidence index
  (`docs/pilot/phase-100-final-pilot-evidence-index.md`) and
  schedule the next conversation.

## Demo patient reset

If the demo gets into a strange state mid-call:

1. Apologize: "Let me reset to a clean demo state — this is
   intentional in our demo environment."
2. In a side terminal:
   ```
   bash scripts/reset_demo_state.sh
   ```
3. Refresh the browser.
4. Resume at the section before the failure.

If the reset itself fails, the call ends with a follow-up. Do not
improvise around a broken state; do not show real patient data;
do not point at a live practice integration.

## What to say

- "Provider-reviewed workflow support for ophthalmology."
- "ChartNav drafts. The clinician signs."
- "Metadata-only export. Read-only. Does not submit."
- "Fake-data demo. No real PHI in this build."
- "Lives alongside your existing EHR. Not a replacement."
- "Every action is in the audit trail with metadata only — no
  clinical body text."

## What NOT to claim

Use the Phase 93 dry-run runbook's forbidden-narration list as the
authoritative source. Key entries:

- "ChartNav diagnoses" / "interprets images" / "recommends
  treatment" / "writes back to your EHR" / "replaces your EHR" /
  "is a certified EHR" / "submits claims" / "codes / bills" /
  "HIPAA-certified" / "SOC 2-certified" / "FDA-cleared" / "auto-
  coded" / "auto-billed" / "auto-submitted" / "auto-scheduled" /
  "progression confirmed" / "IOL power recommended" / "messages
  patients automatically."

## Recovery if a section fails

| Failed section | Recovery |
|---|---|
| Demo reset | Apologize, end the live demo, schedule a follow-up after re-running the Phase 100 gate. Do not improvise. |
| Backend / frontend boot | Show the prior recorded video clip from `docs/demo/phase-62-video-clip-shot-list.md`. Do not attempt a hot-fix on a buyer call. |
| Panel renders blank | Refresh once. If it persists, skip that panel and reference the panel's build doc from `docs/build/`. Do not attempt to debug live. |
| Forbidden phrase appears in narration | Correct it on the spot — "Let me re-state — ChartNav does NOT recommend treatment; it surfaces a metadata projection of provider-entered structured data." |
| Buyer asks "can you do real PHI today?" | Read aloud from `docs/security/phase-100-no-real-phi-attestation.md` Section 1. Offer to schedule a security review. |
| Buyer asks "can you message my patients?" | "No. ChartNav has no patient-send surface and never auto-messages patients." Move on. |
| Buyer asks "can you bill / code / submit claims?" | "No. ChartNav does not bill, code, submit, or transmit any claim at any tier." Move on. |
| Buyer asks "does it integrate with my EHR?" | "Read-only FHIR export today. No writeback in this build. Production integration is a separate Phase 2x conversation." |

## Post-demo (T+15 minutes)

| # | Step | Expected |
|---|---|---|
| Q1 | Capture the rehearsal stopwatch (15 or 30 min target) | within 5% of target |
| Q2 | Capture buyer questions in the Phase 65 success metric tracker | added to log |
| Q3 | If any forbidden phrase was used, log it as a remediation item | added to log |
| Q4 | If demo state was reset mid-call, log it as a stability item | added to log |
| Q5 | Send the buyer the Phase 100 evidence index + the Phase 93 GO/NO-GO form template | sent within 24h |
