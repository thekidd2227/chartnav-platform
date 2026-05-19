# ChartNav Customer Pitch Deck — Template

> Customizable per practice. Replace every `{{PLACEHOLDER}}`
> before the meeting. 10 slides. Pricing values are constant
> across practices and are pre-filled.

**Audience:** specific ophthalmology practice — owner / clinical
champion / compliance lead by name.
**Purpose:** convert a discovery conversation into a pilot
agreement, anchored in their stated pains and Clinical Signal
Filtering.
**CTA / next step:** schedule the live fake-patient demo for
**{{PRACTICE_NAME}}** and identify the pilot champion + security
owner.

**Safe-claims contract.** Read
`docs/commercial/chartnav-approved-claims-language.md` before
editing. Replacing placeholders does not authorize HIPAA-
compliance, certified-EHR, autonomous-diagnosis, or automatic-
orders / coding / referrals / patient-messaging claims.

---

## Slide 1 — Cover

- **Title:** A ChartNav workflow proposal for **{{PRACTICE_NAME}}**.
- **Content:**
  - Practice: **{{PRACTICE_NAME}}**.
  - Primary contact: **{{PRACTICE_CHAMPION}}**.
  - Date: **{{DATE}}**.
- **Speaker notes:** Open with their name and the date.
- **Visual:** logo + practice name.

## Slide 2 — Workflow pains heard

- **Title:** What we heard from **{{PRACTICE_NAME}}**.
- **Content:**
  - Pain 1: *{{PAIN_1}}*.
  - Pain 2: *{{PAIN_2}}*.
  - Pain 3: *{{PAIN_3}}*.
- **Speaker notes:** Quote them where possible (with permission).
- **Visual:** quote cards.

## Slide 2b — Subspecialty mix

- **Title:** What **{{PRACTICE_NAME}}** specializes in.
- **Content:**
  - Subspecialty mix: **{{PRACTICE_SUBSPECIALTY_MIX}}**.
  - Examples: *Retina-heavy injection clinic / Glaucoma
    surveillance clinic / Comprehensive (cataract + cornea) /
    Pediatric / Oculoplastics.*
  - Map subspecialty mix to ChartNav surfaces:
    - **Retina-heavy** → retina tracking + retina injection
      events + OCT macula / fundus / widefield imaging metadata
      + OD/OS retinal diagram.
    - **Glaucoma surveillance** → glaucoma tracking + IOP
      measurement events + visual field tests + OCT RNFL +
      visual field 24-2 / 10-2 imaging metadata.
    - **Cataract / refractive** → biometry packet metadata +
      external PDF report metadata + clinical shortcut bank.
    - **Cornea / anterior segment** → clinical shortcut bank
      (Dry eye, Keratitis, Pterygium, etc.).
    - **Oculoplastics** → clinical shortcut bank (Chalazion,
      Blepharitis, Entropion, Ectropion, Ptosis).
    - **Pediatric / strabismus** → planned. No structured
      tracking shipped yet — only the clinical shortcut bank.
- **Speaker notes:** Fill `{{PRACTICE_SUBSPECIALTY_MIX}}` with the
  practice's stated mix from discovery. Do not promise pediatric
  or cornea structured tracking — those are planned, not
  shipped. Do not claim a device-vendor adapter.
- **Visual:** subspecialty chip strip with the practice's mix
  highlighted.

## Slide 3 — Clinical Signal Filtering — tailored for **{{PRACTICE_NAME}}**

- **Title:** Filters conversation. Captures findings. Builds the diagram.
- **Content:**
  - Doctors at **{{PRACTICE_NAME}}** described:
    *{{DICTATION_PAIN}}*.
  - Retinal-workflow gap heard:
    *{{RETINAL_WORKFLOW_PAIN}}*.
  - **What ChartNav does on a line like:**
    *{{PRACTICE_EXAMPLE_FINDING}}*
  - ChartNav separates:
    - **Ignored chatter** — the parts that aren't clinical signal.
    - **Clinical finding** — what goes into the chart.
    - **Uncertain phrase** — flagged for provider review.
    - **Proposed diagram annotation** — applied, edited, or
      rejected by the provider before anything is saved.
  - The provider applies, edits, or rejects every proposal —
    nothing finalizes without a click.
- **Speaker notes:** Replace `{{DICTATION_PAIN}}`,
  `{{RETINAL_WORKFLOW_PAIN}}`, and `{{PRACTICE_EXAMPLE_FINDING}}`
  with the practice's own words from discovery — that's what
  makes this slide land.
- **Visual:** four-row card showing the four classifications,
  with the practice's example highlighted at the top.

## Slide 4 — Before / With ChartNav

- **Title:** Before / With ChartNav.
- **Content:**
  - **Before:** free-form notes, manual chart prep, paper retinal
    diagrams, summaries from scratch.
  - **With ChartNav:** provider-reviewed structured note,
    OD/OS canvas, finalized summary, pre-visit brief, action
    review queue, Clinical Signal Filtering applied across the
    workflow.
- **Speaker notes:** Match this slide to **{{PRACTICE_NAME}}**'s
  stated pains.
- **Visual:** before/after split.

## Slide 5 — Pilot proposal

- **Title:** Proposed pilot for **{{PRACTICE_NAME}}**.
- **Content:**
  - Pilot timeline: **{{PILOT_WEEKS}}** weeks (template = 4–6).
  - Providers in pilot: **{{PILOT_PROVIDERS}}**.
  - Patients in scope: **{{PATIENT_SCOPE}}**.
  - Hosting: **{{HOSTING_DECISION}}** (controlled-pilot mode).
  - BAA / security review: **{{GATING_STATUS}}**.
  - **Pilot fee:** $10,000 flat for the pilot window.
- **Speaker notes:** Make the BAA / security review the gate,
  not a surprise.
- **Visual:** simple table.

## Slide 6 — Success metrics

- **Title:** What we measure together.
- **Content (3–5 metrics):**
  - **{{METRIC_1}}** — baseline / target / cadence.
  - **{{METRIC_2}}** — baseline / target / cadence.
  - **{{METRIC_3}}** — baseline / target / cadence.
- **Speaker notes:** Pull from
  `docs/pilot/chartnav-pilot-success-metrics.md`. The practice
  fills in their own baseline numbers; we do not invent them.
- **Visual:** small metrics table.

## Slide 7 — Provider-in-control safety

- **Title:** ChartNav surfaces context. Your provider decides.
- **Content:**
  - Draft → reviewed → finalized.
  - Signed retinal artifacts immutable; edits create an
    explicit fork.
  - Audit-friendly design with metadata-only logging.
  - Per-organization isolation; cross-organization requests
    fail closed.
  - **No orders. No coding. No referrals. No patient messages.**
- **Speaker notes:** Read the negative-assertion bullets aloud.
- **Visual:** state diagram.

## Slide 8 — Post-pilot pricing

- **Title:** What ChartNav costs after the pilot.
- **Content:**
  - **Per-provider monthly subscription:** $299–$499 / provider /
    month.
  - **Per-practice flat tier:** $5,000 / practice / month
    (alternative to per-provider).
  - **Multi-practice annual discounts:** 2–4 = 10% off; 5–9 = 15%
    off; 10+ = enterprise pricing.
  - Pilot fees are not discounted unless approved case-by-case.
- **Speaker notes:** Practice picks per-provider OR per-practice;
  not both.
- **Visual:** pricing-tier table.

## Slide 9 — Decision path

- **Title:** How we decide.
- **Content:**
  - Demo this week (fake patient).
  - Pilot agreement + security review next.
  - Pilot kickoff in **{{PILOT_KICKOFF_WEEK}}**.
  - Mid-pilot review at week 3.
  - Post-pilot decision: continue → paid pilot, pause, or end.
- **Speaker notes:** Decision framework lives in the
  demo-to-pilot transition plan.
- **Visual:** 5-step path.

## Slide 10 — Next step

- **Title:** What we'd like from **{{PRACTICE_NAME}}**.
- **Content:**
  - Confirm the demo time.
  - Identify pilot champion.
  - Identify security / compliance owner.
  - Confirm the start of the security review.
- **Speaker notes:** Walk away with a single CTA.
- **Visual:** checklist.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
