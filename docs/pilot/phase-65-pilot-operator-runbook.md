# Phase 65 Pilot Operator Runbook

Status: internal operator runbook
Audience: pilot owner, implementation lead, support owner

## Purpose

This runbook describes how to operate a controlled pilot once the
practice has passed the required security and legal gates. It is not
for fake-data demos; use the Phase 61 and Phase 62 demo runbooks for
that.

This runbook does not approve real PHI. It starts only after Gate 3 in
`phase-65-controlled-pilot-go-no-go-gate.md` is complete.

## Roles

| Role | Responsibility |
| --- | --- |
| Pilot owner | Owns schedule, scope, check-ins, decision log |
| Practice clinical champion | Owns workflow fit and provider feedback |
| Practice security/compliance owner | Owns security review, incident process, PHI approval |
| Practice IT owner | Owns IdP, network, hosting, backup/logging coordination |
| Support owner | Owns issue triage and escalation |
| Engineering owner | Owns fixes, rollback, smoke/regression evidence |

Store names, phone numbers, and private contact details out-of-repo.

## Pre-Session Checklist

- [ ] Gate 3 approval is complete.
- [ ] Pilot scope is documented: users, workflows, locations, time
      window, and stop criteria.
- [ ] User roster is reviewed.
- [ ] Practice owners know the first-session date and support channel.
- [ ] Runtime safety validator passed in the target environment.
- [ ] Environment uses the approved auth mode.
- [ ] Database and backup posture match the approved environment.
- [ ] Logs are configured to avoid sensitive content.
- [ ] Incident response contacts are available.
- [ ] Success metric tracker is ready.

## First Session

1. Confirm this is a controlled pilot session, not a demo.
2. Confirm named users only are present.
3. Re-state boundaries:
   - provider-reviewed workflow layer;
   - no autonomous documentation;
   - no diagnosis;
   - no treatment recommendation;
   - no image interpretation;
   - no orders, referrals, patient messages, billing, or coding;
   - no production LLM unless separately approved.
4. Walk through the exact workflow in scope.
5. Confirm review/sign/attestation behavior.
6. Log any issue in the triage template.
7. End with a decision: continue, pause, or escalate.

## Daily Check-In During Week 1

Capture:

- Number of pilot sessions attempted.
- Number completed.
- Failed workflow attempts.
- Support tickets opened.
- Any S1/S2 issues.
- Provider or technician friction.
- Any safety-boundary concern.
- Any user/role confusion.
- Any evidence that scope needs to shrink.

Do not capture clinical body text in the check-in note.

## Weekly Check-In After Week 1

Review:

- Success metric tracker.
- Issue log.
- Any recurring friction.
- Any unresolved S1/S2 issue.
- Any requested scope change.
- Any security or access-control question.

Scope change rule: any new workflow, location, vendor, integration, or
LLM/STT path goes back through security review.

## Stop / Pause Criteria

Pause the pilot immediately if:

- S1 data-safety incident is suspected.
- Practice asks to pause.
- Wrong-role or wrong-org access is suspected.
- Logs/audit appear to contain sensitive content.
- Runtime safety validator fails.
- Backup or restore evidence becomes invalid.
- Production LLM or unapproved vendor egress is detected.
- Clinician cannot complete review/sign safely.

## After Each Pilot Week

The pilot owner writes a private weekly note with:

- scope used;
- users active;
- metrics snapshot;
- issues opened/closed;
- risk changes;
- decision for next week.

Keep the note out-of-repo if it references a practice, user, or real
patient workflow.

## End of Pilot

Use `phase-65-pilot-exit-criteria-decision-memo-template.md` to decide:

- continue as-is;
- continue with narrower scope;
- expand after new review;
- pause for repairs;
- stop.
