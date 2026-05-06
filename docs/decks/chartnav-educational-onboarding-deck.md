# ChartNav Educational / Onboarding Deck

> Train pilot users and practice staff before they touch the
> product. 9 slides. Pair with
> `docs/pilot/chartnav-admin-onboarding-checklist.md`.

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
    artifact for their org.
  - **reviewer** — read-only on every clinical surface; write
    attempts return `403 role_forbidden`.
- **Visual:** 3-row table.

## Slide 3 — The fake demo patient

- **Title:** Morgan Lee, PT-1001.
- **Content:**
  - Fake patient, fake DOB, fake provider (Dr. Carter).
  - Lives in `demo-eye-clinic` org (also fake).
  - Reset with `bash scripts/reset_demo_state.sh` between sessions.
- **Visual:** chart card.

## Slide 4 — Provider review is mandatory

- **Title:** Draft / review / finalize.
- **Content:**
  - Every clinical artifact starts as a draft.
  - You explicitly mark it reviewed.
  - You explicitly finalize it.
  - Finalized artifacts are immutable; signed retinal artifacts
    fork on edit.
- **Visual:** state diagram.

## Slide 5 — Scribe session

- **Title:** Scribe session lifecycle.
- **Content:**
  - Paste source text or transcript.
  - Click *Process*.
  - Review the structured note.
  - Click *Mark reviewed*.
  - Click *Finalize*.
- **Speaker notes:** Pause on the banner copy.
- **Visual:** 5-step list.

## Slide 6 — Retinal diagram workflow

- **Title:** OD/OS canvas workflow.
- **Content:**
  - Click *Generate proposals from findings*.
  - Apply only the proposals you agree with.
  - Save the artifact.
  - Sign when the drawing is right.
  - Edits to a signed artifact create an explicit fork.
- **Visual:** OD/OS schematic.

## Slide 7 — Patient summary

- **Title:** Patient-friendly summary draft.
- **Content:**
  - Create from a finalized scribe session.
  - Edit the draft if you want to.
  - Mark reviewed; then finalize.
  - **ChartNav never sends to a patient.**
- **Visual:** state diagram.

## Slide 8 — Pre-visit brief + action queue

- **Title:** Pre-visit context + provider review queue.
- **Content:**
  - Generate the pre-visit brief; show source counts + data gaps.
  - Generate the action queue; accept / dismiss / complete.
  - Both are review surfaces — never orders or messages.
- **Visual:** 2-card panel.

## Slide 9 — What not to do

- **Title:** Common mistakes to avoid.
- **Content:**
  - Don't treat ChartNav as a clinical decision-maker.
  - Don't rely on the action queue's clinical-language scan as a
    safety net.
  - Don't try to send the patient summary to a patient.
  - Don't put real PHI into a `local` or `staging` environment.
  - Don't edit a signed retinal artifact in place — fork it.
  - Don't paraphrase the safety contract — read it aloud.
- **Visual:** plain bullets.
