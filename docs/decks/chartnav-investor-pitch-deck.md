# ChartNav Investor Pitch Deck

> Source deck for an investor / advisor pitch. 14 slides. Markdown
> source — exported to the Desktop review folder by
> `scripts/export_chartnav_decks_to_desktop.sh`.

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
  - Free-form notes drift.
  - Retinal findings live in narrative text.
  - OD/OS diagrams are paper or one-off.
  - Patient-friendly summaries are written from scratch.
  - No structured pre-visit chart prep.
- **Speaker notes:** Don't villainize incumbent EHRs.
- **Visual:** 5-bullet panel.

## Slide 3 — Market pain (qualitative)

- **Title:** What ophthalmology offices keep saying.
- **Content:**
  - High volume per provider.
  - Specialty-specific findings (retinal tear, drusen, hemorrhage).
  - Pre-visit chart prep is manual.
  - Documentation friction.
- **Speaker notes:** No numeric throughput claim unless sourced.
- **Visual:** quote cards.

## Slide 4 — Why ophthalmology first

- **Title:** Ophthalmology-specific by construction.
- **Content:**
  - OD/OS retinal canvas is first-class.
  - Findings vocabulary matches the chart (drusen, dot/blot,
    flame hemorrhage, microaneurysm, neovascularization).
  - S/I/N/T placement preserved.
  - Signed retinal artifacts are immutable in place; edits create
    an explicit fork.
  - Closed structured-note vocabulary tuned to ophthalmology.
- **Speaker notes:** This slide is the moat.
- **Visual:** OD/OS schematic.

## Slide 5 — Product

- **Title:** Eight provider-reviewed modules.
- **Content:**
  - AI scribe session lifecycle.
  - Findings-to-retinal-diagram proposal review.
  - OD/OS retinal drawing canvas.
  - Patient-friendly summary draft.
  - Pre-visit clinical brief.
  - Provider action review queue.
  - Guided demo mode.
  - Pilot-readiness package.
- **Speaker notes:** Each module is in production code on `main`.
- **Visual:** 8-card grid.

## Slide 6 — Workflow

- **Title:** Seven explicit steps. Provider drives every transition.
- **Content:** scribe → proposals → diagram → summary → brief →
  action queue → guided demo.
- **Speaker notes:** Reference Phase 12's end-to-end smoke as
  integration proof.
- **Visual:** Phase 16 workflow SVG.

## Slide 7 — Build proof

- **Title:** Phases 6–16 already on `main`.
- **Content:**
  - Phase 6 — findings-to-retinal-diagram proposal review.
  - Phase 8 — AI scribe session lifecycle.
  - Phase 9 — provider-reviewed patient-friendly summaries.
  - Phase 10 — provider-facing pre-visit brief.
  - Phase 11 — provider action review queue.
  - Phase 12 — end-to-end clinical workflow smoke review.
  - Phase 13 — demo-ready clinical workflow package.
  - Phase 14 — pilot readiness / deployment hardening.
  - Phase 15 — commercial demo delivery system.
  - Phase 16 — website proof upgrade + conversion layer.
- **Speaker notes:** Each phase has a contract doc in the repo.
- **Visual:** phase timeline.

## Slide 8 — Provider-in-control safety

- **Title:** The provider controls every step.
- **Content:**
  - Draft / review / finalize state model.
  - Signed artifacts immutable in place; edits fork.
  - Audit metadata-only by code-and-test contract.
  - Org isolation, RBAC, sentinel-token regression tests.
  - **What ChartNav is not.** Not a certified EHR. Not autonomous
    diagnosis. Not orders, coding, referrals, patient messaging.
    Not real-PHI production without legal / security review.
- **Speaker notes:** This is the slide that gets us to pilot.
- **Visual:** state diagram.

## Slide 9 — Business model

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
- **Speaker notes:** This is the pricing structure, not realized
  revenue. Reference
  `docs/commercial/pricing/chartnav-pricing-packaging-notes.md`.
- **Visual:** small pricing-tier table.

## Slide 10 — Go-to-market

- **Title:** Demo-first, then pilot.
- **Content:**
  - In-product Guided Demo Mode (Phase 15) for live sessions.
  - Public landing page (Phase 16) for buyer self-discovery.
  - Pilot readiness packet (Phase 14) for security review.
  - Outbound to ophthalmology offices via direct + advisor
    channels.
- **Speaker notes:** Refer to Phase 16 hero CTAs as the
  conversion path.
- **Visual:** 3-step funnel.

## Slide 11 — Moat + credibility

- **Title:** Why this is hard to copy.
- **Content:**
  - Ophthalmology-specific retinal diagram workflow.
  - Audit / org-isolation / RBAC contract baked into every module.
  - Closed action-type vocabulary so no "order" sneaks in.
  - Eight-doc pilot packet ready for security review.
  - **Past performance:** federal healthcare contracting at
    Mann-Grandstaff VA Medical Center, Spokane WA (operating
    entity Ariel's River Contracting Group, LLC).
  - **SDVOSB-certified** operating entity (Service-Disabled
    Veteran-Owned Small Business).
- **Speaker notes:** The moat is contract + specialty fit + real
  federal-healthcare past performance.
- **Visual:** 6-bullet card.

## Slide 12 — Roadmap

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

## Slide 13 — Team

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

## Slide 14 — Ask

- **Title:** Fundraising.
- **Content:**
  - **Stage:** to be confirmed before issuing this deck —
    operator's note.
  - **Amount:** to be confirmed before issuing this deck —
    operator's note.
  - **Investors so far:** No outside investors to date.
  - **Valuation / terms:** not disclosing in deck.
  - **Use of funds:** team build-out, pilot conversion
    infrastructure, security review formalization, out-of-repo
    media production, legal / regulatory review.
- **Speaker notes:** Fundraising stage and amount are
  conversation topics, not printed numbers in this version of the
  deck. Discuss live.
- **Visual:** plain card.
