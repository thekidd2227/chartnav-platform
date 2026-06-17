# Next Steps for the Practice

**Audience:** Practice clinical owner, administrator, security
owner / CISO + ARCG commercial
**Posture:** Two parallel tracks. Fake-data pilot review is
unblocked today; real-PHI readiness approvals run in parallel.

## 1. Two parallel tracks

| Track | Owner | Goal |
|---|---|---|
| **A — Controlled fake-data pilot review** | Practice clinical owner + ARCG ops | 30-day window for the practice to walk the workspace, the Phase 100 launch gate output, and the Advanced Clinical Intelligence panel against the practice's workflow expectations. |
| **B — Real-PHI readiness approvals** | Practice security owner / CISO + ARCG legal | Close the eight blocks in `06-no-real-phi-attestation.md` Section 4. When both tracks land, ARCG and the practice book the real-PHI go-live date together. |

These tracks run **at the same time**. Track B does **not**
require Track A to finish first; Track A does not authorize
Track B on its own.

## 2. Track A — Controlled fake-data pilot review (Week 0 – Week 4)

| Week | Activity | Owner |
|---|---|---|
| Week 0 (kick-off) | ARCG operator walks the buyer demo (`02-buyer-demo-runbook.md`, `03-demo-talk-track.md`) and hands this package. | ARCG ops |
| Week 0 | Practice clinical owner + administrator open `00-executive-summary.md` and `01-controlled-demo-scope.md`. | Practice |
| Week 1 | Practice reviews the Advanced Clinical Intelligence panel, retina visit packet export, and the Phase 86 adaptive workspace against the practice's workflow expectations. | Practice clinical owner |
| Week 2 | Practice administrator reviews the role allowlist (admin / clinician / technician / reviewer) and the metadata-only audit posture. | Practice administrator |
| Week 3 | ARCG operator re-runs the Phase 100 launch gate + Phase 101 capture on the latest `main` SHA; hands the updated artifact dir paths to the practice. | ARCG ops |
| Week 4 (decision) | Practice clinical owner, administrator, ARCG ops, and ARCG commercial sign `05-go-no-go-form.md` (Scope A). | All signers |

Exit criteria: a signed Scope A GO / NO-GO form and a documented
next step (continue to Track B, schedule a follow-up demo, or
close).

## 3. Track B — Real-PHI readiness approvals (Week 0 – Week 8)

The eight blocks in `06-no-real-phi-attestation.md` Section 4
have a recommended cadence. ARCG can pair on each block; the
practice owns the practice-side artifacts.

| Block | Recommended target |
|---|---|
| 4.1 BAA + legal (BAA, DPA, subprocessor list) | Week 0 – Week 2 |
| 4.2 Vendor / LLM decision memo + STT readiness | Week 1 |
| 4.3 Security review (packet acceptance + HIPAA control matrix + customer responsibility matrix) | Week 1 – Week 3 |
| 4.4 Site / hosting (region, Postgres + PITR, OIDC issuer + audience, TLS) | Week 2 – Week 5 |
| 4.5 Access + logging (named-user roster, audit log destination, retention env) | Week 3 – Week 5 |
| 4.6 Backup / DR (rehearsal + DR drill within 90 days) | Week 4 – Week 6 |
| 4.7 Incident response (runbook walk, ARCG on-call, tabletop within 180 days) | Week 5 – Week 7 |
| 4.8 Written practice approval (clinical + security + administrator go-live signatures + locked go-live date) | Week 7 – Week 8 |

When the practice's CISO and ARCG legal countersign the
attestation and the Scope B rows on `05-go-no-go-form.md` are
GREEN, ARCG and the practice schedule a joint real-PHI go-live.

## 4. Commercial + agreement (parallel to Track A)

| # | Item | Owner |
|---|---|---|
| 1 | Pilot agreement signed | ARCG commercial + practice administrator |
| 2 | Pricing acknowledged in writing | ARCG commercial + practice administrator |
| 3 | Pilot success metrics agreed (see `docs/pilot/chartnav-pilot-success-metrics.md` in repo) | ARCG commercial + practice clinical owner |
| 4 | Pilot exit criteria + decision date locked | ARCG commercial + practice administrator |

## 5. Out of scope (still forbidden, even at Scope B GO)

- **Production LLM.** Every LLM-shaped surface remains
  deterministic / fake-adapter / disabled until a separate
  vendor program lands.
- **Live vendor scripts.** No live STT, no live FHIR write-back,
  no live registry submission.
- **Patient messaging.** No email / portal / SMS / phone
  outreach from ChartNav at any tier.
- **Billing / coding / claims submission.** ChartNav does not
  bill, code, submit, or transmit any claim at any tier.
- **EHR writeback.** ChartNav does not write back to the
  practice's EHR at any tier in this build.
- **Autonomous clinical decisions.** Never — including under
  real PHI.

## 6. Contact

| Role | Name / mailbox |
|---|---|
| ARCG ops owner | __________________________ |
| ARCG commercial owner | __________________________ |
| ARCG legal | __________________________ |
| Practice clinical owner | __________________________ |
| Practice administrator | __________________________ |
| Practice security owner / CISO | __________________________ |

(Operator fills these in before handing the package to the
practice.)
