# ChartNav Known Limitations and Non-Goals

A blunt, buyer-safe summary of what ChartNav is **not**, what it
**does not do**, and what its v1 generators **cannot** do. Hand
this to a buyer before the demo if you want to move quickly past
expectations mismatch.

This document is intentionally short. Each limitation appears
elsewhere in the per-phase contract docs; this is the consolidated
list for buyer conversations.

---

## What ChartNav is not

- **Not a certified EHR.** ChartNav does not replace the
  practice's EHR or chart system. It is documentation and review
  support that lives alongside the practice's existing chart
  system.
- **Not HIPAA-certified or SOC 2-certified.** Software is not
  certified to HIPAA. Compliance is implemented by covered
  entities and business associates; ChartNav is designed to support
  HIPAA-aware data-handling practices in a controlled-pilot
  deployment.
- **Not production-ready for PHI by default.** Real PHI may be
  used only after a BAA is executed and the security review
  packet items are signed off. See
  `chartnav-security-review-packet.md`.
- **Not a billing / coding tool.** No CPT, no ICD-10, no claim
  generation surface exists in the product.
- **Not an orders system.** No order entry surface exists in the
  product.
- **Not a referral routing system.** No referral submit surface
  exists in the product.
- **Not a patient messaging / portal system.** No patient-send
  surface exists in the product.
- **Not a primary-care charting assistant.** ChartNav is
  ophthalmology-specific. The retinal-diagram surface, the action
  queue's clinical-language scan, the structured note vocabulary,
  and the patient-summary template are all tuned to ophthalmology.

## What ChartNav does not do

These behaviors are intentionally absent and asserted by tests on
every PR:

- **Does not diagnose autonomously.** The provider diagnoses;
  ChartNav surfaces structured chart context for review.
- **Does not create orders automatically.** No order-creation code
  path exists.
- **Does not submit referrals automatically.** No referral-submit
  code path exists.
- **Does not post billing or coding entries automatically.** No
  billing/coding code path exists.
- **Does not send anything to a patient automatically.** No
  patient-send code path exists. The patient summary panel
  literally renders no patient-send action and the action queue
  banner-copy is an explicit negative assertion.
- **Does not call an external LLM by default.** The deterministic
  v1 generators are regex / aggregation over already-stored chart
  text. The architecture leaves room for an external-LLM source
  under the same provider-review contract; it is documented as
  deferred and is not enabled.

## v1 generator limitations

The deterministic v1 generators are intentionally narrow. False
negatives are expected.

- **Scribe session structured note** — the engine matches a closed
  heading vocabulary (chief complaint, HPI, exam, assessment,
  plan, unassigned text). Free-form clinical text outside that
  vocabulary lands in `unassigned_text`.
- **Findings-to-retinal-diagram proposals** — the proposer matches
  a small ophthalmology-specific phrase vocabulary. False
  negatives are expected and are the reason every proposal is
  read-only until the provider applies it.
- **Patient summary** — the v1 generator composes plain-language
  paragraphs from already-stored structured note fields. It does
  not invent diagnoses or recommendations beyond the source.
- **Pre-visit brief** — derived view of available chart records.
  Data gaps are listed explicitly. **Not** a clinical decision.
- **Provider action queue clinical-language scan** — four narrow
  regex patterns (retinal tear, retinal detachment,
  neovascularization, severe hemorrhage). **Not a primary safety
  net.** False negatives are expected and the queue is
  documented as such.

## Operational limitations

- **Audit retention is configurable.** The default is set per
  practice policy via `CHARTNAV_AUDIT_RETENTION_DAYS`. A practice
  that wants infinite retention will need a host with sufficient
  storage; ChartNav itself does not enforce a maximum.
- **Audit `detail` is metadata-only by code-and-test contract.**
  It is not enforced by a database constraint. Sentinel-token
  regression tests assert this on every PR.
- **Action items are persisted, but pre-visit briefs are not.**
  Briefs are computed on demand; their data freshness is the data
  freshness of the source tables.
- **Demo data is fake.** The seeded `demo-eye-clinic` /
  `PT-1001` data is fake by construction. No real PHI is in the
  repo.

## What requires legal / security review before PHI

- BAA executed.
- Authentication is `bearer` against a real OIDC issuer.
- Hosting decided and approved by the practice.
- Audit retention agreed.
- Backup / restore tested.
- Logging destination approved.
- Incident response contacts in place.
- Optional: external pen test / vuln scan if the practice
  requires one.

See `chartnav-security-review-packet.md` for the detailed gating
list.

## What is deferred (NOT a current product capability)

- External LLM reasoning under a feature flag.
- Specialty-specific risk scoring (glaucoma progression, AMD
  progression, post-op infection risk, etc.).
- Patient-portal delivery of any kind.
- Orders / coding / billing workflows.
- Automated follow-up creation (no calendar writes).
- Longitudinal trend analytics across encounters.
- EHR adapter integrations beyond the existing FHIR adapter shape.
- Team queues and task-assignment routing.

These are deferred — not promised, not currently available, and
not on the pilot's critical path. If a buyer requires one of these
to commit, the answer is "not in this pilot."
