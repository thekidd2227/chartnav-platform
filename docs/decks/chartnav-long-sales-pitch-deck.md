# ChartNav Long Sales Pitch Deck

> Comprehensive sales deck for complex buyers (multi-provider
> practices, multi-location groups, practices with internal
> security or compliance review). 14 slides. Use when the
> standard 10-slide sales deck is too compressed.

**Safe-claims contract.** Private-practice variant — federal
SDVOSB / VA past-performance references intentionally **not**
included. See the company / agency-partner / investor decks for
federal-credibility framing.

---

## Slide 1 — Cover

- **Title:** ChartNav — provider-reviewed clinical workflow for
  your ophthalmology practice.
- **Content:** practice name placeholder, primary contact
  placeholder, date placeholder.
- **Visual:** logo + practice name.

## Slide 2 — Why we're here

- **Title:** What we'll cover today.
- **Content:**
  - Workflow pain we've heard.
  - The ChartNav workflow.
  - Provider-in-control safety model.
  - Retinal workflow + OD/OS canvas demonstration.
  - Pre-visit context + action review queue.
  - Pilot offer + pricing.
  - Implementation checklist.
  - Q&A.
- **Speaker notes:** Set the agenda before pitching.
- **Visual:** 8-bullet card.

## Slide 3 — Workflow pain

- **Title:** What we usually hear from ophthalmology offices.
- **Content:**
  - Documentation drifts across the chart.
  - Retinal findings live in narrative text only.
  - OD/OS diagrams are paper or one-off.
  - Pre-visit chart prep is manual.
  - Patient-friendly summaries are written from scratch.
- **Speaker notes:** Ask which resonates.
- **Visual:** 5-bullet card.

## Slide 4 — ChartNav workflow (deep)

- **Title:** Seven explicit steps. Provider drives every transition.
- **Content:**
  1. **Scribe session** — paste source/transcript text →
     deterministic structured note → review → finalize.
  2. **Findings proposals** — generate OD/OS proposals from
     finalized findings text. Read-only suggestions.
  3. **OD/OS retinal diagram** — provider applies proposals; tags
     `source=ai_approved`; saves; signs. Signed = immutable;
     edits fork.
  4. **Patient-friendly summary** — composed from finalized
     scribe text. Reviewed and finalized by provider.
  5. **Pre-visit brief** — derived view of available chart
     records. Source counts + explicit data gaps.
  6. **Action review queue** — review tasks only. Suggested →
     accepted → completed. Dismissed and completed are immutable.
  7. **Guided demo mode** — opt-in presenter overlay for
     onboarding new providers.
- **Speaker notes:** Walk slowly. Each step is a click.
- **Visual:** Phase 16 workflow SVG with each stage expanded.

## Slide 5 — Provider-in-control safety model

- **Title:** Draft / review / finalize.
- **Content:**
  - **Draft** — every artifact starts here.
  - **Reviewed** — explicit click. Required before finalize.
  - **Finalized** — explicit click. Stamps the artifact and
    renders it immutable. Re-edits to a signed retinal artifact
    create an explicit fork.
  - **Audit metadata-only.** Section bodies, summary text, scribe
    text, and brief sections never reach the audit log.
  - **Org isolation.** Cross-organization access returns
    `404 patient_not_found`. Per-source SELECT re-asserts the org
    filter for defense in depth.
  - **RBAC.** Reviewer is read-only across all clinical surfaces.
- **Speaker notes:** This is the slide that gets us to pilot.
- **Visual:** state diagram + 6-bullet panel.

## Slide 6 — Retinal workflow proof

- **Title:** OD/OS retinal diagram, end to end.
- **Content:**
  - Findings text → AI proposals → provider applies → save → sign.
  - Proposals are read-only until applied.
  - Source `ai_approved` tag preserved on accepted annotations.
  - Versioning + parent fork on signed-edit.
  - Closed symbol vocabulary tuned to ophthalmology.
- **Speaker notes:** "You'd never get this from a generic
  SOAP-note generator."
- **Visual:** OD/OS canvas mock.

## Slide 7 — Pre-visit brief + action queue

- **Title:** Pre-visit context + provider review queue.
- **Content:**
  - Pre-visit brief — derived view of available chart records;
    explicit data gaps.
  - Action queue — review tasks only. Suggested → accepted →
    completed. Dismissed and completed are immutable.
  - Closed action-type vocabulary so no "order" can sneak in.
  - **No orders. No coding. No referrals. No patient messages.**
- **Speaker notes:** Anchor the negative-assertion safety bullets.
- **Visual:** two-card panel.

## Slide 8 — Pilot offer

- **Title:** A controlled pilot, on fake demo data first.
- **Content:**
  - Fake-patient demo first.
  - Pilot agreement + security review before any real PHI.
  - 4–6 week pilot template.
  - Defined success metrics (3–5 per pilot).
  - **Pilot fee:** $10,000 flat.
- **Speaker notes:** Reference
  `docs/pilot/chartnav-demo-to-pilot-transition-plan.md`.
- **Visual:** 4-step pilot timeline + pilot-fee card.

## Slide 9 — Post-pilot pricing

- **Title:** What ChartNav costs after the pilot.
- **Content:**
  - **Per-provider monthly subscription:** $299–$499 / provider
    / month.
  - **Per-practice flat tier:** $5,000 / practice / month
    (alternative).
  - **Multi-practice annual discounts:** 2–4 = 10% off; 5–9 =
    15% off; 10+ = enterprise pricing.
  - Pilot fees are not discounted unless approved case-by-case.
- **Speaker notes:** Practice picks per-provider OR per-practice.
- **Visual:** pricing-tier table.

## Slide 10 — Success metrics

- **Title:** What we measure together.
- **Content:**
  - Provider time saved (estimate).
  - Documentation completeness.
  - Retinal diagram usage.
  - Scribe session review completion.
  - Patient summary review completion.
  - Pre-visit brief usage.
  - Action queue usage.
  - Provider satisfaction.
  - Safety / issue reports.
  - Workflow fit.
- **Speaker notes:** Pick 3–5 with the practice. No fabricated
  baseline numbers.
- **Visual:** 10-row table.

## Slide 11 — Implementation checklist

- **Title:** What it takes to go live.
- **Content:**
  - BAA executed.
  - `CHARTNAV_AUTH_MODE=bearer` against a real OIDC issuer.
  - Hosting decided (API + DB + frontend).
  - Audit retention agreed.
  - Backups + tested restore.
  - Network egress confirmed.
  - Logging destination approved.
  - Incident response contacts in place.
  - Optional pen test / vuln scan.
- **Speaker notes:** Reference
  `docs/pilot/chartnav-security-review-packet.md`.
- **Visual:** 9-row checklist.

## Slide 12 — What ChartNav is not

- **Title:** Buyer-safe non-goals.
- **Content:**
  - Not a certified EHR replacement.
  - Not autonomous diagnosis.
  - Not automatic orders, coding, referrals, or patient messaging.
  - Not real-PHI production without legal / security review.
- **Speaker notes:** Read aloud.
- **Visual:** plain bullets.

## Slide 13 — Q&A guardrails

- **Title:** Common questions.
- **Content:**
  - HIPAA — *"HIPAA-aware data-handling practices; BAA required
    before real PHI."*
  - EHR — *"Not an EHR replacement. We sit alongside your chart
    system."*
  - Diagnose — *"No. ChartNav surfaces structured chart context;
    your provider decides."*
  - Orders — *"No. There is no order-creation surface in the
    product."*
  - External LLM — *"Today's generators are deterministic. No
    LLM is enabled."*
- **Speaker notes:** Reference
  `docs/commercial/objections/chartnav-buyer-objection-handling.md`
  for the full set.
- **Visual:** Q&A cards.

## Slide 14 — Next steps

- **Title:** What we'd do next.
- **Content:**
  - Schedule the live fake-patient demo.
  - Identify pilot champion + security/compliance owner.
  - Discuss BAA + security review timeline.
  - Set pilot success metrics.
  - Sign pilot agreement; kick off pilot.
- **Speaker notes:** Single CTA: schedule the demo.
- **Visual:** 5-step list.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
