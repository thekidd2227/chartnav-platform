# ChartNav Educational / Onboarding Deck

> Train pilot users and practice staff before they touch the
> product. 10 slides. Pair with
> `docs/pilot/chartnav-admin-onboarding-checklist.md`.

**Audience:** practice staff onboarding to ChartNav during a
controlled pilot — providers, scribes, admin / IT / compliance
contacts.
**Purpose:** teach the provider-control workflow with concrete
examples before the practice runs against real PHI.
**CTA / next step:** complete the admin onboarding checklist
before any real-PHI session.

**Safe-claims contract.** Every slide obeys the approved-language
list at `docs/commercial/chartnav-approved-claims-language.md`.
ChartNav is provider-reviewed workflow support — no autonomous
diagnosis, no automatic orders / coding / referrals / patient
messaging.

---

## Slide 1 — Cover

- **Title:** ChartNav onboarding — fake-patient walkthrough.
- **Visual:** logo + DEMO MODE banner.

## Slide 2 — Roles

- **Title:** Who can do what in ChartNav.
- **Content:**
  - **admin** — generate / accept / dismiss / complete every
    artifact; manage users.
  - **clinician** — generate / accept / dismiss / complete every
    artifact for their organization.
  - **reviewer** — read-only across every clinical surface; write
    attempts are blocked.
- **Visual:** 3-row table.

## Slide 3 — Clinical Signal Filtering — what doctors say vs. what ChartNav captures

- **Title:** Filters conversation. Captures findings. Builds the diagram.
- **Subtitle:** How Clinical Signal Filtering classifies what you say.
- **Content:**
  - Doctors do not dictate in perfect templates. ChartNav
    separates casual speech from clinical findings.
  - **What the doctor says:** *"Okay hold on… OD drusen in the
    macula… maybe OS flame hemorrhage inferior."*
  - **What ChartNav ignores (chatter):** "Okay hold on"
  - **What ChartNav extracts (clinical finding):** "OD drusen in
    the macula"
  - **What ChartNav flags as uncertain:** "maybe OS flame
    hemorrhage inferior"
  - **What ChartNav proposes (diagram annotation):** flagged for
    provider review on the OD/OS canvas.
  - **What you do:** apply, edit, or reject each proposal before
    anything is saved or finalized.
- **Speaker notes:** Read the doctor's line aloud, then walk
  each classification. This is the moment trainees understand
  why they are still in control.
- **Visual:** four-row card showing the four classifications.

## Slide 4 — The fake demo patient

- **Title:** Morgan Lee, PT-1001 — your training patient.
- **Content:**
  - Fake patient, fake date of birth, fake provider on record.
  - Lives in the `demo-eye-clinic` organization (also fake).
  - Reset between training sessions with the demo reset script
    or the **Reset demo** button in Guided Demo Mode.
  - The reset script refuses to run if your environment points
    at anything other than the local SQLite default — that's by
    design.
- **Visual:** chart card.

## Slide 5 — Provider review is mandatory

- **Title:** Draft / review / finalize.
- **Content:**
  - Every clinical artifact starts as a draft.
  - You explicitly mark it reviewed.
  - You explicitly finalize it.
  - Finalized artifacts are immutable; signed retinal artifacts
    create an explicit forked artifact on edit.
- **Speaker notes:** "Explicitly" matters — every transition is
  a click.
- **Visual:** state diagram.

## Slide 6 — Scribe session walkthrough

- **Title:** Scribe session lifecycle.
- **Content:**
  - Paste source text or transcript.
  - Click *Process*.
  - Review the structured note draft on screen.
  - Click *Mark reviewed*.
  - Click *Finalize*.
- **Speaker notes:** Pause on the on-screen banner copy each
  trainee sees during the walkthrough.
- **Visual:** 5-step list.

## Slide 7 — Retinal diagram workflow

- **Title:** OD/OS canvas workflow.
- **Content:**
  - Click *Generate proposals from findings*.
  - Apply only the proposals you agree with.
  - Edit the placement if you want to.
  - Reject anything that looks wrong.
  - Save the artifact.
  - Sign when the drawing is right.
  - Edits to a signed artifact create an explicit forked
    artifact — nothing is silently overwritten.
- **Speaker notes:** Apply / edit / reject is the central
  trainee skill.
- **Visual:** OD/OS schematic.

## Slide 8 — Patient summary

- **Title:** Patient-friendly summary draft.
- **Content:**
  - Create from a finalized scribe session.
  - Edit the draft if the language needs to be adjusted.
  - Mark reviewed; then finalize.
  - **ChartNav never sends to a patient.** Distribution to a
    patient happens through your existing chart system, not
    through ChartNav.
- **Visual:** state diagram.

## Slide 9 — Pre-visit brief + action queue

- **Title:** Pre-visit context + provider review queue.
- **Content:**
  - Generate the pre-visit brief; the brief shows source counts
    + explicit data gaps.
  - Generate the action queue; accept / dismiss / complete each
    review task.
  - Both are review surfaces — never orders, codes, referrals,
    or patient messages.
- **Visual:** 2-card panel.

## Slide 10 — What not to do

- **Title:** Common mistakes to avoid.
- **Content:**
  - Don't treat ChartNav as a clinical decision-maker.
  - Don't rely on the action queue's clinical-language scan as
    a safety net.
  - Don't try to send the patient summary to a patient.
  - Don't put real PHI into a local or staging environment —
    those modes are fake-data only by construction.
  - Don't edit a signed retinal artifact in place — fork it.
  - Don't paraphrase the safety contract — read it aloud.
- **Visual:** plain bullets.
