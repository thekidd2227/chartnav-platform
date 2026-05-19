# ChartNav Project Proposal Deck

> Customer-facing project proposal. 9 slides. Per-practice
> template — replace every `{{PLACEHOLDER}}` before the meeting.
> Pricing values are constant across practices and are pre-filled.

**Audience:** the specific ophthalmology practice's decision
makers — owner, clinical champion, security / compliance owner,
technical owner.
**Purpose:** convert verbal interest into a signed pilot
agreement with explicit scope, timeline, and success metrics.
**CTA / next step:** sign the pilot agreement and kick off the
security review for **{{PRACTICE_NAME}}**.

**Safe-claims contract.** Every slide obeys the approved-language
list at `docs/commercial/chartnav-approved-claims-language.md`.
ChartNav is provider-reviewed workflow support — no proposal copy
may promise certifications we don't hold or capabilities (orders /
coding / referrals / patient messaging) we don't ship.

---

## Slide 1 — Cover

- **Title:** ChartNav — pilot project proposal for
  **{{PRACTICE_NAME}}**.
- **Visual:** logo + practice name.

## Slide 2 — Pilot scope

- **Title:** What's in the pilot.
- **Content:**
  - **Providers:** **{{PILOT_PROVIDERS}}**.
  - **Patients:** **{{PATIENT_SCOPE}}** (specific cohort or all).
  - **Surfaces:** the full clinical workflow — Clinical Signal
    Filtering, AI scribe lifecycle, retinal proposal review,
    OD/OS canvas, patient-friendly summary, pre-visit brief, and
    provider action review queue.
  - **Mode:** controlled-pilot deployment after BAA + security
    review.
- **Speaker notes:** Match scope to what the practice signed.
- **Visual:** scope table.

## Slide 3 — Clinical Signal Filtering — what gets validated in the pilot

- **Title:** Filters conversation. Captures findings. Builds the diagram.
- **Content:**
  - The pilot validates Clinical Signal Filtering against
    **{{PRACTICE_NAME}}**'s actual ophthalmology dictation.
  - We'll measure how often the filter:
    - correctly ignores casual chatter,
    - correctly extracts clinical findings,
    - correctly flags uncertain phrasing for provider review,
    - correctly proposes retinal diagram annotations.
  - Provider applies, edits, or rejects every proposal.
  - Findings that should have been flagged but weren't, and
    findings flagged that shouldn't have been, both feed the
    weekly tuning conversation.
- **Speaker notes:** Practice owners care about this — it makes
  the pilot a partnership, not a unilateral product test.
- **Visual:** four-row card showing the four classifications +
  a "tuning loop" callout.

## Slide 4 — Timeline

- **Title:** Pilot timeline.
- **Content:**
  - Week 0: agreement signed, technical readiness verified,
    users provisioned.
  - Week 1: first-session walkthroughs against fake demo data;
    real-encounter use begins after gating.
  - Week 2: real-encounter use; daily 5-min check-ins for the
    first three days; weekly health check after.
  - Week 3: mid-pilot review.
  - Week 4: continue or adjust based on review.
  - Weeks 5–6: wind-down + final metrics + decision meeting.
- **Speaker notes:** Pilot readiness checklist gates the start
  date.
- **Visual:** 6-row timeline.

## Slide 5 — Responsibilities

- **Title:** Who does what.
- **Content:**
  - **Practice clinical champion:** drives provider adoption,
    surfaces friction.
  - **Practice technical owner:** environment + authentication +
    hosting decisions.
  - **Practice security / compliance owner:** BAA + security
    review sign-off + audit retention.
  - **ChartNav engineering lead:** deploy + smoke + rollback +
    incident response.
  - **ChartNav product lead:** weekly health check + mid-pilot
    review + post-pilot decision meeting.
- **Speaker notes:** Specific names go in the customized
  version.
- **Visual:** RACI-lite table.

## Slide 6 — Pilot fee + post-pilot pricing

- **Title:** Pilot fee + what comes next.
- **Content:**
  - **Pilot fee:** $10,000 flat for the pilot window.
  - **Per-provider monthly subscription (post-pilot):** $299–$499
    per provider per month.
  - **Per-practice flat tier (post-pilot):** $5,000 per practice
    per month.
  - **Multi-practice annual discounts:** 2–4 = 10%; 5–9 = 15%;
    10+ = enterprise.
  - Pilot fees not discounted unless approved case-by-case.
- **Speaker notes:** Practice picks per-provider OR per-practice;
  not both.
- **Visual:** pricing-tier table.

## Slide 7 — Success metrics

- **Title:** What we measure together.
- **Content:**
  - 3–5 metrics chosen with the practice up front.
  - Each metric has a practice-supplied baseline, a target, and
    a measurement cadence.
  - Clinical Signal Filtering accuracy is one of the metrics —
    practice supplies the dictation samples.
- **Speaker notes:** Practice fills in baselines and targets.
  We do not invent numbers.
- **Visual:** 5-row table with **{{METRIC_*}}** placeholders.

## Slide 8 — Risks

- **Title:** What could go wrong.
- **Content:**
  - Hosting decision delays.
  - Security review duration.
  - Provider adoption friction.
  - Workflow fit gaps.
  - Practice-internal politics.
- **Speaker notes:** Each risk has a documented mitigation in
  the support runbook.
- **Visual:** 5-bullet card.

## Slide 9 — What is NOT in this pilot

- **Title:** Out of scope.
- **Content:**
  - Orders, coding, referrals, or patient messaging — none of
    these are surfaces ChartNav ships today.
  - EHR integration beyond the existing FHIR adapter shape.
  - External LLM enabling — current generators are deterministic.
  - Real-PHI use without a BAA + security review.
  - Public marketing site changes.
- **Speaker notes:** Boundaries are part of the proposal.
- **Visual:** 5-bullet card.
- **Contact:** jeanmax@arivergroup.com · chartnavmd.com
