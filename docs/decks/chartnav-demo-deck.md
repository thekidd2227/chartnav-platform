# ChartNav Demo Deck

> Used while walking through the live product against the seeded
> fake-patient demo. 8 slides. Pair with
> `docs/demo/chartnav-clinical-workflow-demo-script.md` (what to
> say) and `docs/demo/chartnav-demo-click-path.md` (what to click).

**Safe-claims contract.** Negative-assertion safety copy renders on
every panel during the demo. Same forbidden-claims list as every
other deck.

---

## Slide 1 — Cover

- **Title:** ChartNav live demo — fake patient data only.
- **Content:**
  - "We'll walk through the existing ChartNav ophthalmology
    workflow for the demo patient."
  - "Every step is provider-reviewed."
- **Speaker notes:** Confirm the URL has `?demo=1`.
- **Visual:** logo + DEMO MODE badge.

## Slide 2 — Demo setup

- **Title:** Pre-flight.
- **Content:**
  - Local stack already booted (`make dev` or
    `START_CHARTNAV.command`).
  - Identity = `admin@chartnav.local`.
  - URL = `http://localhost:5173/?demo=1`.
  - DB reset done via `bash scripts/reset_demo_state.sh`.
- **Speaker notes:** Reset between demos.
- **Visual:** terminal mock.

## Slide 3 — Fake patient story

- **Title:** Demo patient — Morgan Lee, PT-1001.
- **Content:**
  - Fake patient. Fake DOB. Fake provider (Dr. Carter).
  - Reason for visit: blurry vision OD, two weeks.
  - Plan: refraction next visit; monitor OS.
- **Speaker notes:** Repeat: this is fake data.
- **Visual:** chart card.

## Slide 4 — Click path

- **Title:** What we'll click.
- **Content:** intake → pre-visit brief → scribe → retinal proposal
  → diagram → summary → action queue.
- **Speaker notes:** Mirror Phase 15 stepper.
- **Visual:** 7-step list.

## Slide 5 — What to watch for

- **Title:** Watch the safety contract.
- **Content:**
  - Every panel has provider-review banner copy.
  - Finalize is an explicit click — never automatic.
  - Signed artifacts are immutable in place.
  - Action queue surfaces *review* tasks only.
- **Speaker notes:** Pause on each banner during the run.
- **Visual:** four annotation callouts.

## Slide 6 — Safety boundaries (read aloud)

- **Title:** What ChartNav does not do.
- **Content:**
  - Does not diagnose autonomously.
  - Does not create orders.
  - Does not submit referrals.
  - Does not bill / code automatically.
  - Does not send anything to a patient automatically.
- **Speaker notes:** Read each bullet — don't paraphrase.
- **Visual:** plain bullets.

## Slide 7 — Q&A guardrails

- **Title:** Common questions.
- **Content:**
  - "HIPAA?" → "We follow HIPAA-aware data-handling practices.
    Compliance is implemented by covered entities. We require a
    BAA before any real PHI."
  - "Diagnose?" → "No — provider reviews and decides."
  - "External LLM?" → "Today's generators are deterministic."
- **Speaker notes:** Refer to
  `docs/commercial/objections/chartnav-buyer-objection-handling.md`.
- **Visual:** Q&A cards.

## Slide 8 — Close / CTA

- **Title:** Next step.
- **Content:**
  - "Want to take this to a controlled pilot?"
  - "We'll send the pilot readiness packet today."
  - Pricing: $299–$499/provider/month, $5,000/practice/month flat,
    or $10,000 flat for a 4–6 week pilot.
- **Speaker notes:** Single CTA. Hand the pricing only when asked.
- **Visual:** plain card.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
