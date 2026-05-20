# Phase 65 Controlled Pilot Go/No-Go Gate

Status: operator checklist
Audience: internal pilot owner, security reviewer, commercial owner

## Purpose

This gate turns the Phase 65 plan into a decision tool. It decides
whether a practice may move from fake-data demo and paid pilot
conversation into controlled pilot setup.

This is not a launch checklist. It does not approve real PHI by
itself. Real-PHI use remains blocked until the practice-specific
security, legal, environment, access, backup, logging, and incident
response evidence is complete.

## Decision States

| State | Meaning | Allowed next action |
| --- | --- | --- |
| Demo GO | Phase 63C smoke is green; fake-data demo may proceed | Run controlled fake-data demo and discovery |
| Pilot Conversation GO | Buyer is qualified and accepts fake-data boundaries | Discuss paid pilot scope and security review |
| Security Review GO | Practice security owner has accepted or conditionally accepted the packet | Prepare controlled-pilot environment checklist |
| Limited Pilot GO | All required real-PHI gates are closed with evidence | Start named-user monitored pilot |
| NO-GO | Any blocking gate is open | Stop, document blocker, assign owner |

## Gate 0 - Fake-Data Demo Only

Entry criteria:

- [ ] Current `main` is synced.
- [ ] Phase 63C smoke returns `BUYER-DEMO FUNCTIONAL GO: YES`.
- [ ] Runtime safety validator passes.
- [ ] Claim scanners pass.
- [ ] Demo uses synthetic data only.

Allowed:

- Controlled buyer demo.
- Phase 64 outreach conversations.
- Security-review scheduling.
- Paid pilot discovery.

Forbidden:

- Real PHI.
- Live clinical operations.
- Production LLM.
- Real vendor API keys.
- Any claim that ChartNav is a certified EHR, replaces an EHR,
  diagnoses, recommends treatment, interprets images, places orders,
  sends referrals or patient messages, bills, codes, integrates with
  devices, or supports remote patient monitoring.

Evidence:

- `scripts/demo/phase63c_functional_smoke.sh` output.
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`.
- `docs/demo/phase-61-buyer-qa-safe-answers.md`.

Exit criteria:

- Buyer understands fake-data boundaries and requests pilot
  qualification or security review.

## Gate 1 - Paid Pilot Conversation

Entry criteria:

- [ ] Gate 0 is green.
- [ ] Buyer is a realistic small or mid-size ophthalmology/retina
      practice or equivalent early pilot candidate.
- [ ] Buyer accepts that ChartNav is a provider-reviewed workflow
      layer, not a replacement system.
- [ ] Buyer names a clinical or operational owner.

Allowed:

- Discuss pilot scope.
- Discuss limited user count.
- Discuss security review.
- Discuss operational success metrics.
- Discuss fake-data demo evidence.

Forbidden:

- Promising a real-PHI start date.
- Promising compliance certification.
- Promising production LLM.
- Promising EHR writeback, device integration, billing/coding,
  orders, referrals, or patient messages.
- Publishing pilot claims externally.

Evidence:

- Buyer qualification notes.
- Phase 64 commercial package, if available.
- `docs/build/current-product-truth.md`.

Exit criteria:

- Buyer agrees the next step is security review before real PHI.

## Gate 2 - Security Review

Entry criteria:

- [ ] Practice security/compliance owner identified.
- [ ] Practice IT owner identified.
- [ ] Practice clinical champion identified.
- [ ] Security packet shared.
- [ ] Pilot scope remains narrow.

Allowed:

- Review security packet.
- Discuss hosting, auth, access, audit, logging, backup, vendor, and
  incident response posture.
- Create gap list.

Forbidden:

- Processing real PHI.
- Turning on external vendor egress with PHI.
- Deploying production-like environment without written approval.

Evidence:

- `docs/pilot/chartnav-security-review-packet.md`.
- `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`.
- `docs/security/chartnav-real-phi-readiness-status.md`.
- `docs/security/chartnav-baa-vendor-readiness-checklist.md`.
- `docs/security/chartnav-incident-response-plan.md`.
- `docs/security/chartnav-backup-disaster-recovery-policy.md`.

Exit criteria:

- Practice security owner either accepts the packet, conditionally
  accepts it with named blockers, or rejects the pilot.

## Gate 3 - Limited Real-PHI Pilot Approval

Entry criteria:

- [ ] Gate 2 closed or conditionally accepted with all blockers
      resolved.
- [ ] BAA/legal review complete if applicable.
- [ ] Controlled-pilot environment approved.
- [ ] Bearer auth/OIDC configured if the environment may hold PHI.
- [ ] Postgres selected for any real-PHI environment.
- [ ] Role/user roster reviewed.
- [ ] Audit retention agreed.
- [ ] Logging reviewed for sensitive-content exposure.
- [ ] Backup and restore evidence complete.
- [ ] Incident contacts captured out-of-repo.
- [ ] Written real-PHI start approval received.

Allowed:

- Start named-user, limited-scope, monitored pilot.

Forbidden:

- Broad rollout.
- Public claims based on pilot activity.
- Production LLM unless separately approved.
- Demo/fake-data adapters with real PHI.

Evidence:

- Signed approval stored out-of-repo.
- Environment validator output.
- Backup/restore proof.
- Access review.
- Incident contact sheet stored out-of-repo.

Exit criteria:

- First monitored session is scheduled and support owner is on call.

## Gate 4 - Monitored Pilot Operation

Entry criteria:

- [ ] Gate 3 complete.
- [ ] Users onboarded.
- [ ] Operator runbook reviewed.
- [ ] Issue triage template ready.
- [ ] Success metric tracker ready.

Allowed:

- Limited monitored pilot.
- Daily/weekly check-ins.
- Operational metric collection.
- Issue triage.

Forbidden:

- Scope expansion without Gate 5 review.
- New vendors or new integrations without security review.
- Any unattended clinical automation.

Evidence:

- Weekly pilot notes.
- Issue log.
- Success tracker.
- Safety exceptions log.

Exit criteria:

- Pilot period completes or is stopped safely.

## Gate 5 - Expansion Decision

Entry criteria:

- [ ] Gate 4 complete.
- [ ] Metrics reviewed.
- [ ] S1/S2 issues resolved or accepted as blockers.
- [ ] Practice decision maker attends exit review.

Allowed:

- Continue, expand, renew, pause, or stop.

Forbidden:

- Expanding on unresolved safety gaps.
- Publishing unsupported results.
- Treating fake-data demo success as production evidence.

Evidence:

- `docs/pilot/phase-65-pilot-exit-criteria-decision-memo-template.md`
  completed out-of-repo or in a practice-approved private location.

Exit criteria:

- Written decision.
