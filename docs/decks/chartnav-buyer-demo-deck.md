# ChartNav Buyer Demo Deck

> Slides used **during** a live ChartNav demo with a buyer
> (practice, advisor, partner). 13 slides — every slide describes
> what the buyer sees on screen or names a specific
> ophthalmology-clinic workflow concept.
>
> **No terminal commands. No repo paths. No internal scripts.**
> The operator-facing setup deck lives at
> `chartnav-operator-demo-deck.md` and is for internal rehearsal
> only.
>
> **Phase 21C-follow-up.** Buyer-facing positioning re-anchored
> around the ophthalmology clinic workflow layer narrative —
> role dashboards, structured retina + glaucoma tracking, imaging
> metadata + review pipeline, OD/OS retinal diagram, internal
> Chat coordination — alongside the original Clinical Signal
> Filtering anchor. Source of truth for buyer language is
> `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`.

**Audience:** ophthalmology practice owner / clinical champion
watching the live fake-patient demo.
**Purpose:** narrate the demo with the buyer's eyes, anchor
provider-control safety on every panel, close on a controlled
pilot conversation.
**CTA / next step:** discuss a controlled ophthalmology pilot.

**Core one-line positioning** *(say verbatim on Slide 2)*:

> "ChartNav is an ophthalmology clinic workflow layer that
> connects intake, technician workup, imaging review,
> retina/glaucoma tracking, provider-reviewed documentation,
> review queues, and internal coordination."

**Safe-claims contract.** Negative-assertion safety copy renders
on every panel during the live demo. Every slide obeys the
approved-language list at
`docs/commercial/chartnav-approved-claims-language.md` and the
ophthalmology language guide at
`docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`.
ChartNav is provider-reviewed workflow support and does not
promise certifications or capabilities it doesn't ship.

---

## Slide 1 — Cover

- **Title:** ChartNav — live ophthalmology workflow demo.
- **Content:**
  - "ChartNav is the clinical workflow layer for ophthalmology
    practices. Front desk to provider sign-off, built for
    eye-care lanes."
  - "Every step is provider-reviewed."
  - "This demo runs against fake data only. No real patient
    information is used."
- **Speaker notes:** Open with the safety line aloud — "fake data
  only." Then read the positioning one-liner.
- **Visual:** logo + DEMO MODE badge.

## Slide 2 — The eye-clinic lane cycle

- **Title:** What ChartNav connects.
- **Content (the lane cycle):**
  - Front desk →
  - Technician workup (VA / IOP / refraction / dilation) →
  - Ancillary imaging review (OCT / fundus / visual field /
    biometry / external PDF metadata) →
  - MD encounter →
  - Review / sign-off →
  - Checkout / follow-up / internal coordination.
- **Speaker notes:** This is the spine of the demo. We'll touch
  each lane in the next 8 slides. ChartNav is not just a scribe —
  it sits across every lane the practice already runs.
- **Visual:** horizontal lane-cycle bar with 6 steps.

## Slide 3 — Today's fake patient

- **Title:** Today's fake patient.
- **Content:**
  - Patient: Morgan Lee, PT-1001 (fake).
  - Fake date of birth, fake provider on record.
  - Reason for visit: blurry vision OD, two weeks.
  - Plan in chart: refraction next visit; monitor OS.
- **Speaker notes:** Repeat that this is fake data; same fake
  patient every demo uses.
- **Visual:** patient chart card.

## Slide 4 — Role-based clinic dashboards

- **Title:** Five role dashboards, one work queue.
- **Content:**
  - **Front desk.** Today's schedule, check-in pending, ready
    for technician, checkout, follow-up.
  - **Technician.** Workup queue, imaging needed, dilation,
    testing, ready for doctor.
  - **Doctor.** Ready for MD, pre-visit briefs, imaging ready
    for review, documentation status, sign-off queue,
    high-priority clinical items.
  - **Reviewer.** Notes awaiting review, diagram proposal
    review, AI draft review, audit exceptions, blocked items.
  - **Admin.** Open queue items, overdue items, unsigned notes,
    queue aging by status / priority / role / queue type.
- **Speaker notes:** Each role sees only the queues they own.
  Org-scoped, role-scoped. Admin can view any role's dashboard.
- **Visual:** dashboard screenshot with the *View as* selector
  visible.

## Slide 5 — Clinical / Ophthalmology shortcut bank

- **Title:** Specialty review prompts the provider applies.
- **Content:**
  - Retina / AMD / DME — Drusen, Dot/blot hemorrhage, Flame
    hemorrhage, Microaneurysm, Macular edema, Subretinal fluid.
  - Cornea / Anterior Segment — Dry eye, Keratitis, Pterygium,
    Corneal abrasion.
  - Glaucoma — IOP elevated, Disc cupping, Visual field defect,
    Optic disc pallor.
  - Oculoplastics / Lids — Chalazion, Blepharitis, Entropion,
    Ectropion, Ptosis.
  - General — Conjunctivitis, Refraction change.
- **Speaker notes:** Provider pins favorites. Shortcuts are
  review prompts, not auto-charted text. The provider applies
  each one during documentation.
- **Visual:** Clinical tab pill grid.

## Slide 6 — Clinical Signal Filtering (the prime feature)

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

## Slide 7 — OD/OS retinal workflow

- **Title:** OD/OS retinal diagram, end to end.
- **Content:**
  - Findings text → proposed annotations → provider applies →
    save → sign.
  - Proposals are drafts until the provider applies them.
  - Accepted annotations preserve a "proposed,
    provider-accepted" trail for audit.
  - Once signed, the retinal artifact is **immutable in place**;
    edits create an explicit fork.
- **Speaker notes:** "You'd never get this from a generic
  SOAP-note generator." Highlight the OD/OS placement.
- **Visual:** OD/OS canvas with two demo annotations (drusen +
  flame hemorrhage inferior).

## Slide 8 — Retina + glaucoma specialty tracking

- **Title:** Provider-reviewed specialty tracking.
- **Content:**
  - **Retina tracking.** Per patient, per eye — condition,
    severity, last OCT date, last fundus date, follow-up
    interval, provider assessment, review status. Plus retina
    injection event history.
  - **Glaucoma tracking.** Per patient, per eye — glaucoma
    type, target IOP, latest IOP, cup-to-disc ratio, RNFL
    status, visual field status, medication plan, progression
    risk label. Plus IOP measurement events and visual field
    test events.
- **Speaker notes:** Every value is provider-entered. ChartNav
  does not autofill IOP, does not autofill cup-to-disc ratio,
  does not grade DR severity, does not select medications.
- **Visual:** Specialty Tracking panel with one retina card +
  one glaucoma card visible.

## Slide 9 — Imaging metadata + review pipeline

- **Title:** Imaging studies surface here.
- **Content:**
  - **Generic modality labels.** OCT macula, OCT RNFL, fundus
    photo, widefield fundus, visual field 24-2, visual field
    10-2, biometry packet, external PDF report.
  - **Metadata only.** ChartNav stores the storage URI, file
    name, content type, size, checksum — never image binaries.
  - **Review workflow.** Status transitions: pending upload →
    uploaded → ready for review → reviewed → archived. Mark
    reviewed is provider-only (admin or clinician).
- **Speaker notes:** ChartNav does not interpret OCT scans,
  fundus photographs, or visual fields. ChartNav does not
  integrate with any specific device or vendor today — the
  imaging metadata + review foundation is shipped; vendor
  adapters are roadmap.
- **Visual:** Imaging Pipeline panel with study list +
  selected-study detail.

## Slide 10 — Internal coordination (Chat)

- **Title:** Internal clinic coordination.
- **Content:**
  - Internal-only Chat tab with a recipient selector.
  - Recipient targets staff identities; selected conversations
    can be exported.
  - **No patient-facing messaging surface.** Internal staff
    coordination only.
- **Speaker notes:** Call this *internal coordination*, never
  *patient messaging*. ChartNav has no patient-side
  communication channel.
- **Visual:** Chat tab with the recipient selector open on a
  staff identity.

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
- **Speaker notes:** Read each bullet aloud — don't paraphrase.
- **Visual:** plain bullets.

## Slide 12 — Common questions (during the demo)

- **Title:** What practices typically ask.
- **Content:**
  - **HIPAA?** *"We follow HIPAA-aware data-handling practices.
    A BAA is required before any real PHI moves through
    ChartNav. ChartNav is not certified to HIPAA."*
  - **Just another scribe?** *"No. ChartNav also connects role
    dashboards, structured data, retina + glaucoma tracking,
    imaging metadata + review, OD/OS retinal annotations, and
    internal coordination."*
  - **Interpret OCTs?** *"No. ChartNav tracks imaging metadata
    and review status. Provider interpretation stays with the
    clinician."*
  - **Device integrations?** *"Today: imaging metadata + review
    foundation with generic modality labels. Vendor-specific
    adapters are on the roadmap."*
  - **Replacing my EHR?** *"No. ChartNav sits alongside your
    chart system."*
- **Speaker notes:** Full set lives in the buyer-objection-
  handling doc at
  `docs/commercial/objections/chartnav-buyer-objection-handling.md`.
  Don't extemporize.
- **Visual:** Q&A cards.

## Slide 13 — Close / next steps

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
