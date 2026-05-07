# ChartNav Pilot Hand-Off Checklist

> Run this checklist after the live demo and before signing the
> pilot agreement. Once every box is checked, hand off to the
> Phase 14 pilot readiness packet
> (`docs/pilot/chartnav-pilot-readiness-checklist.md`).

---

## 1. Demo completed

- [ ] Practice has seen the live fake-patient demo.
- [ ] Demo ran on the seeded `demo-eye-clinic` / PT-1001 data
      (no real PHI).
- [ ] Demo covered the 7-stage workflow (scribe → proposals →
      diagram → summary → brief → action queue → guided demo).
- [ ] Practice has read or been read the negative-assertion
      safety bullets aloud.
- [ ] Practice has the pricing block (per-provider, per-practice
      flat, pilot fee, multi-practice discounts).

## 2. Champion identified

- [ ] **Clinical champion** — provider who will use ChartNav and
      advocate internally during the pilot.
- [ ] **Practice technical owner** — person responsible for
      hosting / auth / environment decisions.
- [ ] **Practice security/compliance owner** — person responsible
      for BAA execution and security review sign-off.

If any of the three is missing, the pilot does not start.

## 3. Security owner identified

- [ ] Security/compliance owner has the security review packet
      (`docs/pilot/chartnav-security-review-packet.md`).
- [ ] Security/compliance owner has the gating-items list (BAA
      executed; `bearer` auth; hosting; audit retention; backups;
      logging; incident response).
- [ ] Security/compliance owner has confirmed they can review
      the packet within the agreed timeline.

## 4. Fake-data demo accepted

- [ ] Practice has explicitly acknowledged the demo ran on fake
      seeded data.
- [ ] Practice understands real PHI requires BAA + security
      review before the controlled-pilot mode is deployed.
- [ ] Practice has had at least 24 hours after the demo to
      surface concerns.

## 5. BAA / security review needed before PHI

- [ ] BAA template shared with the practice's security owner.
- [ ] BAA target signature date agreed.
- [ ] Security review target completion date agreed.
- [ ] The practice has confirmed pilot start cannot precede BAA
      execution if real-PHI use is in scope.

If the pilot scope is fake-data-only, the BAA is still required
for any environment that may eventually hold PHI; flag this
explicitly.

## 6. Success metrics agreed

Pull 3–5 metrics from
`docs/pilot/chartnav-pilot-success-metrics.md`. Practice fills
in baselines and targets:

- [ ] **{{METRIC_1}}** — baseline / target / cadence agreed.
- [ ] **{{METRIC_2}}** — baseline / target / cadence agreed.
- [ ] **{{METRIC_3}}** — baseline / target / cadence agreed.
- [ ] (optional) **{{METRIC_4}}** — agreed.
- [ ] (optional) **{{METRIC_5}}** — agreed.

No fabricated baseline numbers — practice records its own
baseline from existing operations.

## 7. Pilot timeline agreed

- [ ] Pilot kick-off date set.
- [ ] Pilot length set (4–6 weeks template).
- [ ] Mid-pilot review date set (typically end of week 3).
- [ ] Post-pilot decision meeting date set.
- [ ] Pilot fee invoice + payment terms agreed
      ($10,000 flat — no discount unless case-by-case approved).

## 8. Hand-off to Phase 14 readiness checklist

After every box above is checked:

- [ ] Hand the Phase 14 pilot readiness packet
      (`docs/pilot/chartnav-pilot-readiness-checklist.md`,
      `chartnav-pilot-deployment-guide.md`,
      `chartnav-admin-onboarding-checklist.md`,
      `chartnav-security-review-packet.md`,
      `chartnav-support-runbook.md`,
      `chartnav-demo-to-pilot-transition-plan.md`,
      `chartnav-known-limitations-and-non-goals.md`,
      `chartnav-pilot-success-metrics.md`) to the practice.
- [ ] Confirm the practice has assigned an internal owner per
      doc.
- [ ] Schedule the kick-off call.

---

## What this checklist does not cover

- Order entry, coding, referrals, patient messaging — none of
  these are part of ChartNav.
- HIPAA / SOC 2 certification — we are not certified.
- EHR replacement — ChartNav sits alongside the EHR.
- Long-term commercial pricing (post-pilot) — that conversation
  happens at the post-pilot decision meeting, using the pricing
  block from
  `docs/commercial/pricing/chartnav-pricing-packaging-notes.md`.
