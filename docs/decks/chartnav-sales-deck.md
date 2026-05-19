# ChartNav Sales Deck (Ophthalmology Office)

> Sales conversation deck for an ophthalmology private practice.
> 13 slides. Companion to `chartnav-buyer-demo-deck.md` (used
> while driving the live product).
>
> **Phase 21C-follow-up.** Restructured around the ophthalmology
> clinic workflow layer narrative — eye-clinic lane cycle, role
> dashboards, retina + glaucoma tracking, imaging metadata +
> review pipeline, internal coordination — alongside the original
> Clinical Signal Filtering and OD/OS retinal workflow anchors.
> Source of truth for buyer language is
> `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`.

**Audience:** ophthalmology private-practice owner / managing
partner / clinical champion.
**Purpose:** explain ChartNav clearly, anchor provider-control
safety, walk pricing, and close on a live fake-patient demo.
**CTA / next step:** schedule the live fake-patient demo, OR
discuss a controlled ophthalmology pilot.

**Core one-line positioning:**

> "ChartNav is an ophthalmology clinic workflow layer that
> connects intake, technician workup, imaging review,
> retina/glaucoma tracking, provider-reviewed documentation,
> review queues, and internal coordination."

**Safe-claims contract.** Private-practice sales deck — federal
SDVOSB / VA past-performance references intentionally **not**
included. Every slide obeys the approved-language list at
`docs/commercial/chartnav-approved-claims-language.md` and the
ophthalmology language guide. ChartNav is provider-reviewed
workflow support and does not promise certifications or
capabilities it doesn't ship.

---

## Slide 1 — Cover

- **Title:** ChartNav — the clinical workflow layer for your
  ophthalmology practice.
- **Content:** practice name placeholder, provider name
  placeholder, date placeholder.
- **Speaker notes:** Open with their name; not yours. Read the
  positioning one-liner.
- **Visual:** logo + practice name.

## Slide 2 — Why ophthalmology needs a specialty workflow layer

- **Title:** Eye-care lanes are not generic clinic lanes.
- **Content:**
  - Front desk → technician workup (VA / IOP / refraction /
    dilation) → ancillary imaging review (OCT / fundus /
    visual field / biometry) → MD encounter → review / sign-off
    → checkout / follow-up / internal coordination.
  - Retina injection days close 30–60 charts in a single session.
  - Glaucoma follow-ups need IOP trends, target IOP, cup-to-disc
    history, RNFL status, VF progression — all in one place.
  - OD/OS thinking is built into every clinical decision.
- **Speaker notes:** A horizontal scribe app cannot model any of
  this. ChartNav is built around these lanes.
- **Visual:** horizontal lane-cycle bar with 6 steps.

## Slide 3 — Current workflow pain

- **Title:** What we usually hear from ophthalmology offices.
- **Content:**
  - Doctors move fast — findings get buried in narrative notes.
  - Retinal findings live in free text, disconnected from the
    OD/OS diagram.
  - OCT / fundus / VF studies surface in vendor viewers —
    disconnected from the encounter chart.
  - Pre-visit chart prep is manual and inconsistent.
  - Patient-friendly summaries are written from scratch every
    encounter.
- **Speaker notes:** Ask the practice which of these resonates;
  let them name their loudest pain first.
- **Visual:** five-bullet card.

## Slide 4 — Role-based clinic dashboards

- **Title:** Five role views, one work queue.
- **Content:**
  - **Front desk** — today's schedule, check-in pending, ready
    for technician, checkout, follow-up.
  - **Technician** — workup queue, imaging needed, dilation,
    testing, ready for doctor.
  - **Doctor** — ready for MD, pre-visit briefs, imaging ready
    for review, documentation status, sign-off queue,
    high-priority clinical items.
  - **Reviewer** — notes awaiting review, diagram proposal
    review, AI draft review, audit exceptions, blocked items.
  - **Admin** — open queue items, overdue items, unsigned
    notes, queue aging by status / priority / role / queue type.
- **Speaker notes:** Each role sees only what they own. Admin
  can view any role's dashboard via the *View as* selector.
- **Visual:** dashboard screenshot with the *View as* selector
  open.

## Slide 5 — Clinical Signal Filtering (the prime feature)

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
- **Speaker notes:** This is the unique differentiator. Walk the
  example aloud. Pause on "maybe" — uncertainty surfacing is
  what makes this provider-safe.
- **Visual:** four-row card showing the four classifications.

## Slide 6 — Retina + glaucoma specialty tracking

- **Title:** Provider-reviewed structured tracking.
- **Content:**
  - **Retina tracking.** Per patient, per eye — condition,
    severity, last OCT, last fundus, follow-up interval,
    provider assessment, review status. Plus retina injection
    event history.
  - **Glaucoma tracking.** Per patient, per eye — glaucoma type,
    target IOP, latest IOP, cup-to-disc ratio, RNFL status, VF
    status, medication plan, progression risk label. Plus IOP
    measurement events and visual field test events.
- **Speaker notes:** Every value is provider-entered. ChartNav
  does not autofill IOP, does not autofill cup-to-disc ratio,
  does not grade DR severity, does not select medications.
- **Visual:** specialty tracking panel with one retina card +
  one glaucoma card visible.

## Slide 7 — Imaging metadata + review pipeline

- **Title:** Imaging studies surface in the chart.
- **Content:**
  - **Generic modality labels.** OCT macula, OCT RNFL, fundus
    photo, widefield fundus, visual field 24-2, visual field
    10-2, biometry packet, external PDF report.
  - **Metadata only.** ChartNav stores the storage URI, file
    name, content type, size, checksum — never image binaries.
  - **Review workflow.** Pending upload → uploaded → ready for
    review → reviewed → archived. Mark reviewed is provider-only.
- **Speaker notes:** ChartNav does not interpret OCT scans,
  fundus photographs, or visual fields. ChartNav has no current
  vendor adapter — Cirrus / Spectralis / Triton / Optos /
  IOLMaster / Humphrey / Topcon adapters are roadmap, not
  shipped.
- **Visual:** imaging pipeline panel with study list + file
  metadata table.

## Slide 8 — OD/OS retinal workflow proof

- **Title:** OD/OS retinal diagram, end to end.
- **Content:**
  - Findings text → proposed annotations → provider applies →
    save → sign.
  - Proposals are draft until the provider applies them.
  - Accepted annotations preserve a "proposed, provider-
    accepted" trail for audit.
  - Once signed, the retinal artifact is **immutable in place**;
    edits create an explicit fork. Nothing is silently
    overwritten.
- **Speaker notes:** "You'd never get this from a generic
  SOAP-note generator." This is the ophthalmology-specific moat.
- **Visual:** OD/OS canvas mock with two demo annotations.

## Slide 9 — Pre-visit brief, action queue, internal Chat

- **Title:** Documentation support + internal coordination.
- **Content:**
  - **Pre-visit brief** — derived view of available chart
    records with explicit data gaps surfaced.
  - **Action queue** — review tasks only. Suggested → accepted
    → completed. Dismissed / completed items are immutable.
  - **Internal Chat** — recipient selector targeting staff
    identities; selected conversations can be exported.
    **No patient-facing messaging surface.**
  - **No orders. No coding. No referrals. No patient messages.**
- **Speaker notes:** Anchor the negative-assertion safety
  bullets aloud. Call Chat *internal coordination*, never
  *patient messaging*.
- **Visual:** three-card panel.

## Slide 10 — Provider-in-control safety model

- **Title:** Draft / review / finalize. Provider clicks every
  transition.
- **Content:**
  - Draft → reviewed → finalized.
  - Signed retinal artifacts are immutable; edits create an
    explicit fork.
  - Audit-friendly design with metadata-only logging — no
    clinical body text in audit detail.
  - Per-organization isolation; cross-organization requests
    return 404 (no existence leak), not 403.
- **Speaker notes:** Repeat: ChartNav surfaces context, the
  provider decides.
- **Visual:** state diagram.

## Slide 11 — What ChartNav does not do

- **Title:** Ophthalmology-specific non-goals.
- **Content:**
  - Does not autofill IOP, refraction, or cup-to-disc ratio.
  - Does not interpret OCTs, fundus photos, or visual fields.
  - Does not select IOL power or anti-VEGF dosing.
  - Does not grade diabetic retinopathy severity.
  - Does not finalize retinal annotations without explicit
    provider approval.
  - Does not send patient messages automatically.
  - Does not submit orders, referrals, claims, or imaging
    requests.
  - Not a certified EHR replacement.
  - Does not claim HIPAA compliance.
- **Speaker notes:** Read this list aloud — it builds trust.
- **Visual:** plain bullets.

## Slide 12 — Pilot offer + pricing

- **Title:** A controlled pilot, on fake demo data first.
- **Content (pilot):**
  - Fake-patient demo first — no PHI, no risk.
  - Pilot agreement + security review before any real PHI.
  - 4–6 week pilot template with defined success metrics.
  - Eight-doc security-review packet ready for your IT /
    compliance lead.
- **Content (pricing):**
  - **Per-provider monthly:** $299–$499 per provider per month.
  - **Pilot tier:** $10,000 flat for a 4–6 week pilot.
  - **Per-practice flat tier:** $5,000 per practice per month
    (alternative to per-provider).
  - **Multi-practice annual discounts:** 2–4 practices = 10% off;
    5–9 practices = 15% off; 10+ practices = enterprise pricing.
- **Speaker notes:** Make the BAA / security review the gate,
  not a surprise. Practice picks per-provider OR per-practice;
  not both.
- **Visual:** 4-step pilot timeline + pricing-tier table.

## Slide 13 — Next steps

- **Title:** What we'd do next.
- **Content:**
  - Schedule the live fake-patient demo.
  - Identify pilot champion + security / compliance owner.
  - Discuss BAA + security review timeline.
  - Set pilot success metrics.
- **Speaker notes:** Single CTA: schedule the demo. Hand the
  one-page sales deck and the security review packet to the
  practice's compliance owner.
- **Visual:** 4-step list with checkboxes.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
