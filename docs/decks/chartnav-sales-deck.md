# ChartNav Sales Deck (Ophthalmology Office)

> Sales conversation deck for an ophthalmology private practice.
> 10 slides. Companion to `chartnav-demo-deck.md` (used while
> driving the live product).

**Safe-claims contract.** Private-practice sales deck — federal
SDVOSB / VA past-performance references intentionally **not**
included. See `chartnav-company-deck.md` or the agency-partner
deck for federal-credibility framing.

---

## Slide 1 — Cover

- **Title:** ChartNav — provider-reviewed clinical workflow for
  your ophthalmology practice.
- **Content:** practice name placeholder, provider name
  placeholder, date placeholder.
- **Speaker notes:** Open with their name; not yours.
- **Visual:** logo + practice name.

## Slide 2 — Current workflow pain

- **Title:** What we usually hear from ophthalmology offices.
- **Content:**
  - Documentation drifts across the chart.
  - Retinal findings live in narrative text only.
  - Pre-visit chart prep is manual.
  - Patient summaries are written from scratch.
- **Speaker notes:** Ask the practice which of these resonates.
- **Visual:** four-bullet card.

## Slide 3 — ChartNav workflow

- **Title:** Seven explicit steps. Provider drives every transition.
- **Content:** scribe → proposals → diagram → summary → brief →
  action queue → guided demo.
- **Speaker notes:** Use the workflow SVG from Phase 16.
- **Visual:** stage diagram.

## Slide 4 — Provider-in-control safety model

- **Title:** Draft / review / finalize. Provider clicks every
  transition.
- **Content:**
  - Draft → reviewed → finalized.
  - Signed retinal artifacts are immutable; edits fork explicitly.
  - Audit metadata-only.
  - Cross-org access returns 404 patient_not_found.
- **Speaker notes:** Repeat: ChartNav surfaces context, the
  provider decides.
- **Visual:** state diagram.

## Slide 5 — Retinal workflow proof

- **Title:** OD/OS retinal diagram, end to end.
- **Content:**
  - Findings text → AI proposals → provider applies → save → sign.
  - Proposals are read-only until applied.
  - Source `ai_approved` tag preserved on accepted annotations.
  - Versioning + parent fork on signed-edit.
- **Speaker notes:** "You'd never get this from a generic
  SOAP-note generator."
- **Visual:** OD/OS canvas mock.

## Slide 6 — Pre-visit brief + action queue

- **Title:** Pre-visit context + provider review queue.
- **Content:**
  - Pre-visit brief — derived view of available chart records;
    explicit data gaps.
  - Action queue — review tasks only. Suggested → accepted →
    completed. Dismissed and completed are immutable.
  - **No orders. No coding. No referrals. No patient messages.**
- **Speaker notes:** Anchor the negative-assertion safety bullets.
- **Visual:** two-card panel.

## Slide 7 — Pilot offer

- **Title:** A controlled pilot, on fake demo data.
- **Content:**
  - Fake-patient demo first.
  - Pilot agreement + security review before any real PHI.
  - 4–6 week pilot template.
  - Defined success metrics.
- **Speaker notes:** Reference
  `docs/pilot/chartnav-demo-to-pilot-transition-plan.md`.
- **Visual:** 4-step pilot timeline.

## Slide 8 — What ChartNav is not

- **Title:** Buyer-safe non-goals.
- **Content:**
  - Not a certified EHR replacement.
  - Not autonomous diagnosis.
  - Not automatic orders, coding, referrals, or patient messaging.
  - Not real-PHI production without legal / security review.
- **Speaker notes:** Read this list aloud — it builds trust.
- **Visual:** plain bullets.

## Slide 9 — Pricing

- **Title:** ChartNav pricing.
- **Content:**
  - **Per-provider monthly subscription:** $299–$499 per provider
    per month.
  - **Pilot tier:** $10,000 flat for a 4–6 week pilot.
  - **Per-practice flat tier:** $5,000 per practice per month
    (alternative to per-provider).
  - **Multi-practice annual discounts:** 2–4 practices = 10% off;
    5–9 practices = 15% off; 10+ practices = enterprise pricing.
  - Pilot fees are not discounted unless approved case-by-case.
- **Speaker notes:** Practice picks per-provider OR per-practice;
  not both. Discounts apply to annual agreements only.
- **Visual:** pricing-tier table.

## Slide 10 — Next steps

- **Title:** What we'd do next.
- **Content:**
  - Schedule the live fake-patient demo.
  - Identify pilot champion + security/compliance owner.
  - Discuss BAA + security review timeline.
  - Set pilot success metrics.
- **Speaker notes:** Single CTA: schedule the demo.
- **Visual:** 4-step list with checkboxes.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
