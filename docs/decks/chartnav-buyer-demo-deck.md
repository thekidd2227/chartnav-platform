# ChartNav Buyer Demo Deck

> Slides used **during** a live ChartNav demo with a buyer
> (practice, advisor, partner). 9 slides — all describing what the
> buyer sees on screen.
>
> **No terminal commands. No repo paths. No internal scripts.**
> The operator-facing setup deck lives at
> `chartnav-operator-demo-deck.md` and is for internal rehearsal
> only.

**Audience:** ophthalmology practice owner / clinical champion
watching the live fake-patient demo.
**Purpose:** narrate the demo with the buyer's eyes, anchor
provider-control safety on every panel, close on a controlled
pilot conversation.
**CTA / next step:** discuss a controlled ophthalmology pilot.

**Safe-claims contract.** Negative-assertion safety copy renders
on every panel during the live demo. Every slide obeys the
approved-language list at
`docs/commercial/chartnav-approved-claims-language.md`. ChartNav
is provider-reviewed workflow support and does not promise
certifications or capabilities it doesn't ship.

---

## Slide 1 — Cover

- **Title:** ChartNav — live ophthalmology workflow demo.
- **Content:**
  - "We'll walk through ChartNav for one fake patient, from
    pre-visit context to a finalized retinal artifact."
  - "Every step is provider-reviewed."
  - "This demo runs against fake data only. No real patient
    information is used."
- **Speaker notes:** Open with the safety line aloud — "fake data
  only."
- **Visual:** logo + DEMO MODE badge.

## Slide 2 — Fake patient story

- **Title:** Today's fake patient.
- **Content:**
  - Patient: Morgan Lee, PT-1001 (fake).
  - Fake date of birth, fake provider on record.
  - Reason for visit: blurry vision OD, two weeks.
  - Plan in chart: refraction next visit; monitor OS.
- **Speaker notes:** Repeat that this is fake data; this is the
  same fake patient every demo uses.
- **Visual:** patient chart card.

## Slide 3 — What you'll see (the eight steps)

- **Title:** What the demo walks through.
- **Content:**
  1. Pre-visit context for the patient.
  2. Doctor speaks or pastes notes.
  3. Clinical Signal Filtering separates chatter, findings, and
     uncertainty.
  4. Proposed retinal annotations appear on the OD/OS canvas.
  5. Provider applies, edits, or rejects each proposal.
  6. The retinal diagram updates as the provider acts.
  7. Provider saves and signs the artifact (immutable; edits
     fork).
  8. Pilot — what happens next.
- **Speaker notes:** Each step is a single click. Nothing
  finalizes without a provider.
- **Visual:** 8-step list.

## Slide 4 — Clinical Signal Filtering (the prime feature)

- **Title:** Filters conversation. Captures findings. Builds the diagram.
- **Content:**
  - Doctors do not dictate in perfect templates.
  - ChartNav separates casual speech from clinical findings,
    flags uncertainty, and proposes retinal diagram annotations.
  - Doctor says: *"Okay hold on… OD drusen in the macula… maybe
    OS flame hemorrhage inferior."*
  - ChartNav separates:
    - **Ignored chatter** — "Okay hold on"
    - **Clinical finding** — "OD drusen in the macula"
    - **Uncertain phrase** — "maybe OS flame hemorrhage inferior"
    - **Proposed diagram annotation** — provider review required
  - The provider applies, edits, or rejects every proposal
    before anything is saved or finalized.
- **Speaker notes:** Pause on the "maybe" — surfacing
  uncertainty is the safety win.
- **Visual:** four-row card showing the four classifications.

## Slide 5 — What to watch on every panel

- **Title:** The provider-control safety contract.
- **Content:**
  - Every panel has a provider-review banner.
  - Finalize is an explicit click — never automatic.
  - Signed retinal artifacts are immutable in place; edits
    create an explicit fork.
  - The action queue surfaces **review** tasks only — never
    orders, codes, referrals, or patient messages.
- **Speaker notes:** Pause on each banner during the run; let the
  buyer read it.
- **Visual:** four annotation callouts on a workflow image.

## Slide 6 — Retinal workflow on screen

- **Title:** OD/OS retinal diagram, end to end.
- **Content:**
  - Findings text → AI proposals → provider applies → save → sign.
  - Proposals are drafts until the provider applies them.
  - Accepted annotations preserve an "AI-proposed,
    provider-accepted" trail for audit.
  - Once signed, edits create a forked artifact — nothing is
    silently overwritten.
- **Speaker notes:** "You'd never get this from a generic
  SOAP-note generator." Highlight the OD/OS placement.
- **Visual:** OD/OS canvas mock.

## Slide 7 — What ChartNav does not do

- **Title:** Buyer-safe non-goals.
- **Content:**
  - Does not diagnose autonomously.
  - Does not create orders.
  - Does not submit referrals.
  - Does not bill or code automatically.
  - Does not message patients automatically.
  - Not a certified EHR replacement.
  - Not real-PHI production without legal / security review.
- **Speaker notes:** Read each bullet aloud — don't paraphrase.
- **Visual:** plain bullets.

## Slide 8 — Common questions (during the demo)

- **Title:** What practices typically ask.
- **Content:**
  - **HIPAA?** *"We follow HIPAA-aware data-handling practices.
    A BAA is required before any real PHI moves through
    ChartNav."*
  - **Does it diagnose?** *"No. ChartNav surfaces structured
    chart context; the provider decides."*
  - **External AI dependency?** *"Today's draft generators are
    deterministic. No external LLM is enabled."*
  - **Replacing my EHR?** *"No. ChartNav sits alongside your
    chart system."*
- **Speaker notes:** Full set lives in the buyer-objection-
  handling doc. Don't extemporize.
- **Visual:** Q&A cards.

## Slide 9 — Close / next steps

- **Title:** Where this goes from here.
- **Content:**
  - "Want to take this to a controlled pilot on fake data first?"
  - "We'll send the pilot readiness packet for your IT /
    compliance lead today."
  - Pricing on request: $299–$499/provider/month,
    $5,000/practice/month flat, or $10,000 flat for a 4–6 week
    controlled pilot.
- **Speaker notes:** Single CTA: discuss a controlled pilot. Hand
  pricing only when asked.
- **Visual:** plain card.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
