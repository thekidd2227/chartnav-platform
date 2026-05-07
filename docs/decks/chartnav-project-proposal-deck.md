# ChartNav Project Proposal Deck

> Internal or customer-facing project proposal. 8 slides. Per-
> practice template — replace every `{{PLACEHOLDER}}` before the
> meeting. Pricing values are constant across practices and are
> pre-filled.

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
  - **Surfaces:** Phase 5B / 6 / 8 / 9 / 10 / 11 / 13 / 15 (the
    full clinical workflow).
  - **Mode:** controlled-pilot (Postgres, `bearer` auth, backups,
    monitoring).
- **Speaker notes:** Match scope to what the practice signed.
- **Visual:** scope table.

## Slide 3 — Timeline

- **Title:** Pilot timeline.
- **Content:**
  - Week 0: agreement signed, technical readiness verified, users
    provisioned.
  - Week 1: first-session walkthroughs against fake demo data;
    real-encounter use begins after gating.
  - Week 2: real-encounter use; daily 5-min check-ins for the
    first three days; weekly health check after.
  - Week 3: mid-pilot review.
  - Week 4: continue or adjust based on review.
  - Weeks 5–6: wind-down + final metrics + decision meeting.
- **Speaker notes:** Reference
  `chartnav-pilot-readiness-checklist.md`.
- **Visual:** 6-row timeline.

## Slide 4 — Responsibilities

- **Title:** Who does what.
- **Content:**
  - **Practice clinical champion:** drives provider adoption,
    surfaces friction.
  - **Practice technical owner:** environment + auth + hosting
    decisions.
  - **Practice security/compliance owner:** BAA + security review
    sign-off + audit retention.
  - **ChartNav engineering lead:** deploy + smoke + rollback +
    incident response.
  - **ChartNav product lead:** weekly health check + mid-pilot
    review + post-pilot decision meeting.
- **Speaker notes:** Names go in the customized version.
- **Visual:** RACI-lite table.

## Slide 5 — Pilot fee + post-pilot pricing

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

## Slide 6 — Success metrics

- **Title:** What we measure.
- **Content:**
  - Pull 3–5 metrics from
    `docs/pilot/chartnav-pilot-success-metrics.md`.
  - Practice-specific baseline / target / cadence per metric.
- **Speaker notes:** Practice fills in baselines and targets.
- **Visual:** 5-row table with **{{METRIC_*}}** placeholders.

## Slide 7 — Risks

- **Title:** What could go wrong.
- **Content:**
  - Hosting decision delays.
  - Security review duration.
  - Provider adoption friction.
  - Workflow fit gaps.
  - Practice-internal politics.
- **Speaker notes:** Each risk has a documented mitigation in the
  support runbook.
- **Visual:** 5-bullet card.

## Slide 8 — What is NOT in this pilot

- **Title:** Out of scope.
- **Content:**
  - Orders / coding / referrals / patient messaging.
  - EHR integration beyond the existing FHIR adapter shape.
  - External LLM enabling.
  - Real-PHI use without a BAA + security review.
  - Marketing site changes.
- **Speaker notes:** Boundaries are part of the proposal.
- **Visual:** 5-bullet card.
