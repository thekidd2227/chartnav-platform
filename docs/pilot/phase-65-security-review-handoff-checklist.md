# Phase 65 Security-Review Handoff Checklist

Status: internal operator checklist
Audience: ChartNav pilot owner, buyer security owner, buyer IT owner

## Purpose

This checklist organizes the handoff from a successful fake-data demo
or Phase 64 buyer conversation into security review. It does not
approve real PHI. It helps the operator assemble evidence and identify
practice-specific gaps before a limited pilot is discussed.

## Before Scheduling Security Review

- [ ] Buyer has seen or been offered the controlled fake-data demo.
- [ ] Phase 63C functional smoke is green on the demo path.
- [ ] Buyer accepts that the demo is fake-data only.
- [ ] Buyer understands that real-PHI use is a separate controlled
      process.
- [ ] Buyer has named a security/compliance owner.
- [ ] Buyer has named an IT owner.
- [ ] Buyer has named a clinical champion.
- [ ] Pilot scope is narrow enough to review.

## Packet to Send or Walk Through

| Topic | Repo source | Handoff note |
| --- | --- | --- |
| Product truth | `docs/build/current-product-truth.md` | Use as internal source of truth; do not embellish |
| Buyer Q&A boundaries | `docs/demo/phase-61-buyer-qa-safe-answers.md` | Safe answers for EHR, PHI, LLM, diagnosis, orders, billing |
| Demo evidence posture | `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` | Fake-data demo evidence only |
| Controlled pilot go-live | `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` | Master pre-real-PHI gate |
| Pilot readiness | `docs/pilot/chartnav-pilot-readiness-checklist.md` | Existing practical pilot checklist |
| Security review packet | `docs/pilot/chartnav-security-review-packet.md` | Primary security-review doc |
| Real-PHI status | `docs/security/chartnav-real-phi-readiness-status.md` | Current readiness and blockers |
| Vendor/BAA readiness | `docs/security/chartnav-baa-vendor-readiness-checklist.md` | Vendor and subprocessor posture |
| Incident response | `docs/security/chartnav-incident-response-plan.md` | S1 response and evidence preservation |
| Backup / DR | `docs/security/chartnav-backup-disaster-recovery-policy.md` | Backup/restore expectations |
| Risk analysis | `docs/security/chartnav-security-risk-analysis-template.md` | Template for joint risk register |
| Release evidence | `docs/release/release-evidence-checklist.md` | General release evidence shape |

## Questions to Ask the Buyer

Security/legal:

- Who signs or approves the BAA or equivalent agreement?
- Is a DPA required?
- Does the practice require a subprocessor list before a pilot?
- Does the practice require a written risk assessment before any
  real-PHI start date?

Identity/access:

- Which identity provider will be used?
- Who owns user provisioning and deprovisioning?
- Which roles are needed for the first pilot?
- Who approves role changes?

Environment:

- Where may the pilot be hosted?
- What region or residency requirements apply?
- What network egress is allowed?
- Is Postgres hosting approved?

Logging/audit:

- What audit retention period is required?
- Who reviews audit logs?
- What log destination is approved?
- Are request bodies stripped by default?

Backup/restore:

- What backup destination is approved?
- What backup retention period is required?
- Who owns restore testing?
- What RPO/RTO is acceptable?

Incident response:

- Who is the security/compliance contact?
- Who is the clinical champion?
- Who is the IT contact?
- What notification channel should be used for S1 events?

Vendors:

- Are external STT vendors allowed?
- Are external LLM vendors allowed?
- If any vendor is allowed, who verifies BAA/subprocessor status?
- If no vendor is allowed, confirm all relevant provider flags stay
  disabled.

## Handoff Output

Create a private, practice-specific security review note outside the
repo with:

- Practice name.
- Named owners.
- Pilot scope.
- Security-review date.
- Open blockers.
- Evidence links sent.
- Decision: accepted, conditionally accepted, rejected, or needs more
  information.

Do not include patient names, MRNs, DOBs, visit details, screenshots
with PHI, secrets, tokens, API keys, or signed legal documents in the
repo.

## Stop Conditions

Stop the handoff and do not proceed toward real PHI if:

- Buyer asks to upload real patient data before security review.
- Buyer requires a claim ChartNav cannot support.
- Buyer demands autonomous clinical behavior.
- Buyer requires production LLM without separate approval.
- Buyer cannot name a security/compliance owner.
- Buyer cannot approve hosting, backup, incident response, or access
  controls.
