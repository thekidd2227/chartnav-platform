# ChartNav Pricing & Packaging Notes

> Authoritative pricing contract. Every customer-facing deck
> pulls pricing from this file. Pricing is a hypothesis — labeled
> as such — until validated by signed pilot agreements and paid
> customers.

---

## Pricing tiers

### Per-provider monthly subscription

- **Range:** $299–$499 per provider per month.
- **Use when:** practice has a stable provider count and prefers
  a per-seat model.
- **Notes:**
  - Range allows price negotiation per practice profile.
  - Bottom of range ($299) for smaller / earlier pilot
    conversions.
  - Top of range ($499) for multi-location or higher-throughput
    practices.

### Per-practice flat tier (alternative)

- **Price:** $5,000 per practice per month.
- **Use when:** practice prefers a flat predictable monthly cost
  regardless of provider count, or practice has high provider
  rotation.
- **Notes:**
  - Practice picks **per-provider** OR **per-practice** — not
    both.
  - Flat tier becomes more attractive at ~10+ providers in the
    practice.

### Pilot tier

- **Price:** $10,000 flat for a 4–6 week controlled pilot.
- **What it covers:**
  - Pilot deployment (controlled-pilot mode: Postgres,
    `bearer` auth, backups, monitoring).
  - Pilot kickoff, weekly health check, mid-pilot review,
    post-pilot decision meeting.
  - Pilot readiness packet hand-off + security review support.
- **What it doesn't cover:**
  - Real-PHI use without BAA + security review (gating items).
  - EHR-specific integration work.
  - Custom feature work outside the standard product surface.
- **Notes:**
  - Pilot fees are **not discounted** unless approved
    case-by-case.

### Multi-practice annual discounts

Apply only to **annual agreements** (not month-to-month, not
pilots):

| Practices on annual agreement | Discount |
|---|---|
| 2 – 4 | 10% off |
| 5 – 9 | 15% off |
| 10 + | Custom enterprise pricing |

Pilot fees are **not** discounted by these brackets.

---

## What's not in the pricing structure (yet)

- **No usage-based pricing.** No per-encounter / per-note / per-
  patient pricing in v1.
- **No tiered feature gating.** All eight modules are included at
  every price tier; we do not lock features behind higher-priced
  tiers.
- **No public price page.** Pricing is in commercial decks, the
  pricing-notes doc (this file), and customer pitch templates —
  not on the public website. The Phase 16 landing page directs
  buyers to schedule a demo, where pricing is shared in
  conversation.
- **No publicly-published per-provider price.** The $299–$499
  range is in commercial decks; the public landing page does not
  print it.

---

## What's still hypothesis-stage

- **Whether $299–$499 is the right range.** No paid customer has
  validated this yet. Pilot conversion data will inform whether
  to tighten the range, lift the floor, or extend the ceiling.
- **Whether pilot fee should be reduced for early-stage
  practices.** Currently firm at $10,000; case-by-case approval
  for exceptions.
- **Whether the per-practice flat tier breakeven is at
  10 providers.** Hypothesis-only; will be tuned with operating
  data.
- **Whether multi-practice discounts hit the right tipping
  points.** Hypothesis-only; will be tuned with operating data.

---

## What needs validation before publishing

Before any of the following go on the website or into a
publicly-circulated deck:

- [ ] Conversion rate from pilot → paid customer.
- [ ] Average per-encounter time saved (or not saved) — measured
      against per-practice baseline, not against an industry
      average.
- [ ] Average pilot satisfaction Likert score.
- [ ] S1 / S2 ticket rate during pilots.

Until these numbers exist, the website and decks **must not**
publish a numeric ROI claim. We use placeholders in the customer
pitch template (`{{METRIC_*}}`) so each practice fills in their
own baseline / target.

---

## Approved pricing block (use exactly across decks)

> **Per-provider:** $299–$499 / provider / month.
>
> **Per-practice flat (alternative):** $5,000 / practice / month.
>
> **Pilot tier:** $10,000 flat for a 4–6 week pilot.
>
> **Multi-practice annual discounts:** 2–4 = 10%; 5–9 = 15%; 10+
> = enterprise pricing.
>
> **Pilot fees are not discounted unless approved case-by-case.**

This block appears in:

- `docs/decks/chartnav-investor-pitch-deck.md` (slide 9)
- `docs/decks/chartnav-sales-deck.md` (slide 9)
- `docs/decks/chartnav-customer-pitch-deck-template.md` (slide 7)
- `docs/decks/chartnav-financial-fundraising-deck.md` (slide 3)
- `docs/decks/chartnav-marketing-plan-deck.md` (slide 5)
- `docs/decks/chartnav-project-proposal-deck.md` (slide 5)
- `docs/decks/chartnav-long-sales-pitch-deck.md` (slide 9)
- `docs/decks/chartnav-one-page-sales-deck.md` (Pricing block)
- `docs/decks/chartnav-elevator-pitch-deck.md` (slide 5,
  shortened)
- `docs/decks/chartnav-demo-deck.md` (slide 8, shortened)

If pricing changes, update this file first; then propagate to
every deck above.

---

## What is **not** part of pricing

- ChartNav does not sell HIPAA / SOC 2 certification (we don't
  have either).
- ChartNav does not sell EHR replacement (we are not an EHR).
- ChartNav does not sell orders / coding / referrals / patient
  messaging (those surfaces don't exist in the product).
- ChartNav does not bill per encounter or per note (no usage
  metering).
- ChartNav does not charge for the demo (demos are free).

---

## Practice-side cost ceiling guidance

We have **not heard** specific cost-ceiling guidance from
prospective practices yet. Pricing above is a hypothesis; pilot
conversations will tell us where the practice's price elasticity
lands.
