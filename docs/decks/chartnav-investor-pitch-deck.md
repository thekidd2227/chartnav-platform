# ChartNav Investor Pitch Deck

> Source deck for an investor / advisor pitch. 15 slides.

**Audience:** investors, advisors, commercial advisors evaluating
the ChartNav opportunity.
**Purpose:** explain the business clearly — market, product moat,
build proof, GTM, milestones, ask.
**CTA / next step:** schedule the live fake-patient demo;
fundraising details discussed live.

**Safe-claims contract.** Every slide obeys the approved-language
list at `docs/commercial/chartnav-approved-claims-language.md`.
The deck does not claim HIPAA-compliant, certified-EHR, or
autonomous-diagnosis behavior — none of those apply to ChartNav.

---

## Slide 1 — Cover

- **Title:** ChartNav — provider-reviewed clinical workflow for
  ophthalmology.
- **Purpose:** Set the room.
- **Content:**
  - ChartNav.
  - Provider-reviewed ophthalmology workflow.
  - Demo-ready, pilot-ready.
  - Operated by Ariel's River Contracting Group, LLC,
    dba ARCG Systems · Maryland-based.
- **Speaker notes:** Open with the one-line positioning. Don't
  claim certifications.
- **Visual:** logo + tagline; no other clutter.

## Slide 2 — Problem

- **Title:** Ophthalmology charting is fragmented.
- **Content:**
  - Doctors move fast. Findings get buried in narrative notes.
  - Retinal findings live in free text, disconnected from the
    OD/OS diagram.
  - Pre-visit chart prep is manual and inconsistent.
  - Patient-friendly summaries are written from scratch.
  - No structured pre-visit chart prep across encounters.
- **Speaker notes:** Don't villainize incumbent EHRs — they aren't
  the enemy; the gap is ophthalmology-specific workflow on top of
  whatever EHR a practice already runs.
- **Visual:** 5-bullet panel.

## Slide 3 — Market pain (qualitative)

- **Title:** What ophthalmology offices keep saying.
- **Content:**
  - High volume per provider; tight per-encounter time.
  - Specialty-specific findings (drusen, dot/blot,
    flame hemorrhage, microaneurysm, neovascularization).
  - Pre-visit chart prep is manual.
  - Documentation friction sits on the provider, not the system.
- **Speaker notes:** No numeric throughput claim unless the
  practice supplies it. We do not quote made-up time-saved
  metrics.
- **Visual:** quote cards.

## Slide 4 — Why ophthalmology first

- **Title:** Ophthalmology-specific by construction.
- **Content:**
  - OD/OS retinal canvas is first-class — not bolted on.
  - Findings vocabulary matches the chart (drusen, dot/blot,
    flame hemorrhage, microaneurysm, neovascularization).
  - S/I/N/T placement is preserved.
  - Signed retinal artifacts are immutable in place; edits create
    an explicit fork.
  - Closed structured-note vocabulary tuned to ophthalmology.
- **Speaker notes:** This slide is the moat. Any general-purpose
  AI scribe can take notes; only an ophthalmology-specific
  workflow gets retinal annotation right.
- **Visual:** OD/OS schematic.

## Slide 5 — Clinical Signal Filtering (prime differentiation)

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
- **Speaker notes:** This is the prime feature — the part that
  makes ophthalmology-specific real. Use the three-line cadence
  ("filters / captures / builds") and walk the example aloud.
- **Visual:** four-row card showing the four classifications.

## Slide 6 — Product

- **Title:** Eight provider-reviewed modules.
- **Content:**
  - Clinical Signal Filtering (prime differentiator).
  - AI scribe session lifecycle.
  - Findings-to-retinal-diagram proposal review.
  - OD/OS retinal drawing canvas.
  - Patient-friendly summary draft.
  - Pre-visit clinical brief.
  - Provider action review queue.
  - Guided demo mode.
- **Speaker notes:** Each module is a built and tested workflow
  surface. The pilot-readiness package wraps deployment; the demo
  delivery package wraps live walkthrough.
- **Visual:** 8-card grid.

## Slide 7 — Workflow

- **Title:** Seven explicit steps. Provider drives every transition.
- **Content:** scribe → proposals → diagram → summary → brief →
  action queue → guided demo.
- **Speaker notes:** End-to-end smoke coverage exists across all
  seven steps.
- **Visual:** workflow diagram.

## Slide 8 — Build proof: what is already working

- **Title:** What's already built and tested.
- **Content:**
  - Provider-reviewed AI scribe lifecycle (draft → review →
    finalize).
  - Findings-to-retinal-diagram proposal review.
  - OD/OS retinal drawing canvas with immutable signed artifacts.
  - Patient-friendly summary draft (provider-reviewed).
  - Pre-visit clinical brief.
  - Provider action review queue (review tasks only — no orders).
  - End-to-end clinical workflow smoke coverage.
  - Guided demo mode for live walkthroughs.
  - Public proof page for buyer self-discovery.
  - Pilot-readiness package (8-doc security review packet, BAA
    template, deployment guide, transition plan).
- **Speaker notes:** Every item above is built and tested today.
  Buyers can see it run live in the fake-patient demo.
- **Visual:** capability checklist (10 items, no phase numbers).

## Slide 9 — Provider-in-control safety

- **Title:** The provider controls every step.
- **Content:**
  - Draft / review / finalize state model.
  - Signed artifacts immutable in place; edits fork.
  - Audit-friendly design with metadata-only logging.
  - Per-organization isolation; role-based access; cross-org
    requests fail closed.
  - **What ChartNav is not.** Not a certified EHR replacement.
    Not autonomous diagnosis. Not orders, coding, referrals, or
    patient messaging. Not real-PHI production without legal /
    security review.
- **Speaker notes:** This is the slide that gets us to pilot.
- **Visual:** state diagram.

## Slide 10 — Business model

- **Title:** How ChartNav charges.
- **Content:**
  - **Per-provider monthly subscription:** $299–$499 / provider /
    month.
  - **Pilot tier:** $10,000 flat for a 4–6 week controlled pilot.
  - **Per-practice flat tier:** $5,000 / practice / month
    (alternative to per-provider).
  - **Multi-practice annual discounts:** 2–4 practices = 10% off;
    5–9 practices = 15% off; 10+ practices move to custom
    enterprise pricing.
  - **Pilot fees** are not discounted unless approved
    case-by-case.
- **Speaker notes:** Pricing is structure, not realized revenue.
  No paid pilots have run yet.
- **Visual:** small pricing-tier table.

## Slide 11 — Go-to-market

- **Title:** Demo-first, then pilot.
- **Content:**
  - Live fake-patient demo for buyer meetings.
  - Public proof page for buyer self-discovery.
  - Eight-doc pilot readiness packet for security review.
  - Outbound to ophthalmology offices via direct + advisor
    channels.
- **Speaker notes:** The first conversion is fake-data demo →
  controlled pilot, not free trial → paid customer.
- **Visual:** 3-step funnel (demo → pilot → customer).

## Slide 12 — Moat + credibility

- **Title:** Why this is hard to copy.
- **Content:**
  - Ophthalmology-specific retinal diagram workflow.
  - Clinical Signal Filtering tuned to how doctors actually talk.
  - Provider-reviewed retinal diagram proposals.
  - Signed artifact protection (immutable in place; edits fork).
  - Audit-friendly design with per-org isolation and role-based
    access baked into every module.
  - Closed action-type vocabulary so no "order" sneaks in.
  - Eight-doc pilot packet ready for security review.
  - **Past performance:** federal healthcare contracting at
    Mann-Grandstaff VA Medical Center, Spokane WA (operating
    entity Ariel's River Contracting Group, LLC).
  - **SDVOSB-certified** operating entity (Service-Disabled
    Veteran-Owned Small Business).
- **Speaker notes:** The moat is contract + specialty fit + real
  federal-healthcare past performance attached to the operating
  entity.
- **Visual:** 8-bullet card.

## Slide 13 — Roadmap

- **Title:** What's next.
- **Content:**
  - **M1 — first paid pilot:** July 1, 2026.
  - **M2 — five paid pilots:** October 1, 2026.
  - **M3 — first paying customer (post-pilot):** Q4 2026.
  - **M4 — multi-practice deployment:** Q4 2026.
  - **Deferred** — external LLM source (under same provider-review
    contract), specialty-specific risk scoring, EHR adapter
    extensions, longitudinal trend analytics.
- **Speaker notes:** Be explicit about deferred work.
- **Visual:** roadmap timeline.

## Slide 14 — Team

- **Title:** Team.
- **Content:**
  - **Jean-Max Charles** — Founder, ARCG Systems · Co-founder,
    ChartNav · President & Sales Director, Ariel's River
    Contracting Group, LLC · SDVOSB operator · Maryland-based.
  - **Maria Jackson** — Vice President of Operations · Training
    leader, formerly Lead Scribe at McKesson, focused on scribe
    roles and training personnel on scribing with doctors. More
    than 10 years in healthcare operations across ophthalmology.
  - **Advisors — recruiting** (target archetypes: retina
    sub-specialist, practice administrator, healthcare-IT
    operator).
- **Speaker notes:** Two co-founders + advisor recruiting in
  progress.
- **Visual:** name cards (no photos committed to repo).

## Slide 15 — Ask

- **Title:** Fundraising.
- **Content:**
  - **Fundraising details discussed live.**
  - **Current focus:** first paid pilots and ophthalmology
    workflow validation.
  - **Investors so far:** No outside investors to date.
  - **Valuation / terms:** not disclosed in deck.
  - **Use of funds:** team build-out, pilot conversion
    infrastructure, security review formalization, out-of-repo
    media production, legal / regulatory review.
- **Speaker notes:** Stage and amount are conversation topics.
  Demo request: jeanmax@arivergroup.com · chartnavmd.com.
- **Visual:** plain card.
