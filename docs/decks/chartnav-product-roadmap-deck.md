# ChartNav Product Roadmap Deck

> 9 slides. Frames what's already working, what's next, and
> what's deliberately deferred. Translated into business
> outcomes — no engineering changelog.

**Audience:** investors, advisors, partners, practice owners
asking "what's next."
**Purpose:** show the build is real, the next 90 days are
focused, and what's deferred is deferred on purpose.
**CTA / next step:** schedule the live fake-patient demo;
discuss a controlled pilot.

**Safe-claims contract.** Every slide obeys the approved-language
list at `docs/commercial/chartnav-approved-claims-language.md`.
ChartNav is provider-reviewed workflow support — no certifications
claimed, no autonomous diagnosis, no automatic orders / coding /
referrals / patient messaging.

---

## Slide 1 — Cover

- **Title:** ChartNav product roadmap.
- **Visual:** logo only.

## Slide 2 — Capabilities already working

- **Title:** What ChartNav can do today.
- **Content:**
  - **Clinical Signal Filtering** — filters conversation,
    captures findings, and builds the diagram; separates chatter,
    findings, uncertainty; proposes retinal diagram annotations.
  - **Provider-reviewed AI scribe lifecycle** — draft → review
    → finalize.
  - **Findings-to-retinal-diagram proposal review** — provider
    applies, edits, or rejects each proposal.
  - **OD/OS retinal drawing canvas** — first-class diagram with
    closed symbol vocabulary; signed artifacts immutable; edits
    fork.
  - **Patient-friendly summary draft** — provider-reviewed.
  - **Pre-visit clinical brief** — derived view of available
    chart records with explicit data gaps.
  - **Provider action review queue** — review tasks only.
  - **End-to-end clinical workflow smoke coverage** — every
    module integrates.
  - **Guided demo mode** — opt-in presenter overlay for live
    walkthroughs.
  - **Public proof page** for buyer self-discovery.
  - **Pilot-readiness package** — eight-doc security review
    packet, BAA template, deployment guide, transition plan.
- **Speaker notes:** Every item above is built and tested today.
  Buyers can see it run live in the fake-patient demo.
- **Visual:** capability checklist (11 items, no engineering
  phase numbers).

## Slide 3 — Commercial launch package (now shipping)

- **Title:** What just shipped on the commercial side.
- **Content:**
  - A complete commercial deck library spanning every recurring
    sales, investor, partner, and onboarding scenario.
  - Buyer + operator demo decks split — buyer never sees
    operator-only setup.
  - One-page leave-behind for follow-up emails.
  - Clinical Signal Filtering positioned as the prime feature
    across every buyer-facing deck.
  - Local demo launcher on the operator's Mac (single double-
    click START / STOP / RESET).
  - Commercial readiness map (what's demo-ready, pilot-ready,
    not yet ready).
- **Speaker notes:** Commercial launch is delivery + operator
  UX, not a new clinical feature.
- **Visual:** 6-bullet card.

## Slide 4 — Next 90 days (execution plan)

- **Title:** What we're doing right now.
- **Content:**
  - **Days 0–30 — pipeline build.**
    - Record ophthalmology-specific scribe demo clips.
    - Refresh the one-page leave-behind.
    - Build the discovery list (private practices + advisors).
    - Confirm 5 partner intro paths.
  - **Days 30–60 — discovery + pitch refinement.**
    - 10–20 ophthalmology discovery calls.
    - Capture every objection; update the objection-handling
      doc.
    - Identify 3–5 pilot-candidate practices.
  - **Days 60–90 — first paid pilot.**
    - Sign the first pilot agreement.
    - Stand up the controlled-pilot environment for that
      practice.
    - Tighten deployment readiness based on the practice's
      compliance posture.
- **Speaker notes:** This is operations work, not new product.
  We are deliberately not pulling forward clinical features.
- **Visual:** three-column 30/60/90 timeline.

## Slide 5 — Milestones

- **Title:** Near-term milestones.
- **Content:**
  - **M1 — first paid pilot:** July 1, 2026.
  - **M2 — five paid pilots:** October 1, 2026.
  - **M3 — first paying customer (post-pilot):** Q4 2026.
  - **M4 — multi-practice deployment:** Q4 2026.
- **Speaker notes:** Targets, not committed delivery dates.
- **Visual:** 4-row milestone table.

## Slide 6 — Deferred (deliberately not promised)

- **Title:** Deferred — not on the roadmap.
- **Content:**
  - External LLM source under the same provider-review contract.
  - Specialty-specific risk scoring (glaucoma progression, AMD
    progression, post-op infection risk).
  - Patient-portal delivery of any kind.
  - Orders / coding / billing automation.
  - Automated follow-up creation (no calendar writes).
  - Longitudinal trend analytics across encounters.
  - EHR adapter integrations beyond the existing FHIR shape.
  - Team queues / task-assignment routing.
- **Speaker notes:** Saying "deferred" is a feature, not a flaw.
  Each deferred item carries safety risk we are not pulling
  forward.
- **Visual:** 8-bullet card.

## Slide 7 — Why provider control stays central

- **Title:** Provider-in-control is the moat.
- **Content:**
  - Every artifact has explicit draft → review → finalize.
  - Signed artifacts are immutable; edits create an explicit
    fork.
  - Audit-friendly design with metadata-only logging.
  - Closed action-type vocabulary so no "order" can sneak in.
  - Per-organization isolation enforced by both code and
    automated tests.
- **Speaker notes:** This is what makes the moat hard to copy.
- **Visual:** 5-bullet card.

## Slide 8 — Roadmap risks

- **Title:** What could derail the roadmap.
- **Content:**
  - Pilot conversion timing — M1 and M2 dates are targets, not
    committed delivery dates.
  - External-LLM safety contract design — when we add it, we
    will not weaken provider-review.
  - Practice security review duration varies per practice.
  - Hosting decisions per practice (single-tenant vs.
    multi-tenant) shape deployment effort.
- **Speaker notes:** Be honest. No fake risks, no hidden risks.
- **Visual:** 4-bullet card.

## Slide 9 — Single CTA

- **Title:** Want to take this further?
- **Content:**
  - Schedule the live fake-patient demo.
  - Open the controlled pilot conversation with your IT /
    compliance lead.
  - Email: jeanmax@arivergroup.com.
  - Website: chartnavmd.com.
- **Visual:** plain card.
