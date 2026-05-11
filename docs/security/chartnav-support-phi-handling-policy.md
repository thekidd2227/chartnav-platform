# ChartNav Support PHI Handling Policy

> **Phase:** 23.
> **Type:** Policy that governs how ChartNav support staff and
> practice users handle PHI during support interactions.
> Practice reviews and accepts this policy as part of Gate 9 of
> `chartnav-real-phi-go-live-gate.md`.

## 1. Cardinal rule

> **No PHI in support tickets.**

Support tickets — opened by the practice, opened by ChartNav,
internal triage notes — must never contain ePHI. This applies
to:

- Patient names, MRNs, dates of birth, addresses.
- Encounter notes, transcripts, clinical findings.
- Retinal diagrams, imaging metadata that identifies a patient.
- Audit details that mention specific patient identifiers.
- Screenshots of any ChartNav screen showing patient data.

## 2. Why the cardinal rule exists

The ticketing system is not approved for PHI. Support tickets
may transit through systems and processes (email forwarding,
backup, archival, search indexing) that are not under the
practice's BAA. PHI in a ticket is a disclosure outside the
approved data flow.

## 3. What to do instead

When the practice or ChartNav needs to discuss a specific
patient or encounter:

1. **Reference IDs only.** Use ChartNav-internal IDs (encounter
   id, note version id, audit event id) — never patient names
   or MRNs.
2. **Move to the secure evidence channel.** The practice
   designates a secure channel (e.g. practice-approved
   encrypted email, secure file share, video call with screen
   share that is not recorded) for any PHI-bearing
   conversation.
3. **Redact in transit.** If PHI accidentally enters a
   non-secure channel, redact immediately (edit the message),
   move the conversation to the secure channel, and file a
   SEV-4 incident per
   `chartnav-incident-breach-response-runbook.md`.

## 4. Screenshots

- Screenshots that include PHI must **never** be attached to a
  support ticket.
- If a screenshot is necessary for diagnosis, it must:
  - Be redacted before upload (black-box patient name / MRN /
    DOB / clinical text).
  - OR be transmitted through the practice's secure evidence
    channel.
- Synthetic / fake-data screenshots (e.g. `PT-1001 Morgan Lee`
  seeded encounter) are safe in support tickets.

## 5. Support access approval

- ChartNav support staff have **no access** to the practice's
  controlled-pilot environment by default.
- If access is needed for diagnosis:
  1. Practice security owner grants read-only access for a
     specific time window via the identity provider.
  2. Access generates audit events visible to the practice's
     admin.
  3. ChartNav support staff use a dedicated identity (not their
     personal IdP identity).
  4. Access is revoked at the end of the window.

## 6. Support evidence handling

For evidence that *must* contain PHI (e.g. an audit log export
showing the user activity around an incident):

- Transit through the practice's secure evidence channel.
- Store in the practice's approved secure storage.
- Hash and timestamp the evidence file.
- Reference the evidence by hash in the support ticket — never
  attach the evidence file to the ticket.
- Retain only as long as needed; delete per the practice's
  retention policy.

## 7. Ticket retention

- ChartNav retains support tickets per the practice's ticketing
  system's retention policy.
- If a ticket inadvertently contained PHI:
  - File the SEV-4 incident.
  - Determine whether the ticket should be deleted, redacted,
    or moved to a secure archive (depends on incident
    investigation needs).

## 8. Escalation path

- **SEV-3 / SEV-4 (non-PHI):** standard ticket triage.
- **SEV-1 / SEV-2 (suspected PHI exposure):** escalate
  immediately to incident response per
  `chartnav-incident-breach-response-runbook.md`.
- **Cardinal-rule violation (PHI in ticket):** SEV-4 minimum;
  redact, move, file incident, retrain operator.

## 9. Training

- Every ChartNav support staff member reviews this policy
  before being granted access to controlled-pilot environments.
- Every practice user with support-ticket access reviews this
  policy during onboarding.
- Re-review annually.

## 10. Practice-specific overrides

The practice may specify a stricter policy in the BAA or a
side letter (e.g. no support tickets accepted via email; only
through the practice's portal). ChartNav follows the stricter
of this policy and the practice's specification.

---

## What this policy does NOT do

- Does not approve PHI transit through any ChartNav-controlled
  channel that isn't the controlled-pilot environment itself.
- Does not list the practice's secure evidence channel by name
  — that is configured per practice.
- Does not bind specific ticket-tracking-system retention — the
  practice's policy applies.

## Policy review cadence

- Annually.
- After any cardinal-rule incident.
- After any change to ChartNav's support tooling or process.
