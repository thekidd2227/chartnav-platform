# ChartNav Incident / Breach Response Runbook

> **Phase:** 23.
> **Companion to:** `docs/security/chartnav-incident-response-plan.md`
> (the Phase 20A.1 high-level plan). This runbook is the
> step-by-step operational sequence.
>
> **Breach-notification timelines below are placeholders. They
> must be reviewed and finalized by the practice's legal counsel
> before real-PHI start. The HIPAA Breach Notification Rule
> applies to the practice as a Covered Entity; ChartNav as a
> Business Associate is bound by the BAA and applicable law. Do
> not rely on this runbook as legal advice.**

---

## 1. Severity levels

| Severity | Definition | Examples |
|---|---|---|
| **SEV-1 (Critical)** | Confirmed unauthorized access or disclosure of ePHI, or imminent threat thereof | Stolen credentials with confirmed PHI access; ePHI emailed to wrong recipient |
| **SEV-2 (High)** | Suspected unauthorized access or disclosure of ePHI; system failure that prevents access to ePHI by authorized users | Misconfigured role gives broader access than intended; production outage |
| **SEV-3 (Medium)** | Security event without confirmed ePHI exposure; control failure | Backup-failure alert; cross-org test failure in CI |
| **SEV-4 (Low)** | Operational anomaly; policy violation without ePHI impact | PHI accidentally typed into support ticket (immediately redacted) |

## 2. Suspected incident intake

When a potential incident is identified (by ChartNav engineer,
practice staff, or vendor), execute these steps **immediately**.

1. **Stop posting**. Do not discuss in public chat or support
   tickets.
2. **Capture the timestamp** of first observation (UTC).
3. **Note the observer** (name, role, contact).
4. **Open a private incident channel** (practice-approved
   channel; not a support ticket, not email if email could carry
   PHI).
5. **Assign an incident commander** — typically the on-call
   ChartNav engineer for SEV-1/2; practice security owner is
   notified within 1 hour.
6. **Notify the practice security owner** for any SEV-1/2 within
   1 hour of confirmation.

## 3. Containment

For SEV-1 / SEV-2:

- [ ] Disable the affected account / role / token if account
      compromise is suspected.
- [ ] Rotate credentials (DB, JWT signing key, API tokens).
- [ ] Disable the affected endpoint / feature via feature flag or
      deploy rollback if a code defect is suspected.
- [ ] Block traffic from the suspected origin at the WAF /
      hosting-provider firewall.
- [ ] Preserve evidence **before** any rollback (see §4).

For SEV-3 / SEV-4:

- [ ] File a follow-up ticket in the practice's tracking system.
- [ ] Open a PR or code fix if a control gap is identified.

## 4. Evidence preservation

Before any rollback or system change:

- [ ] Snapshot the Postgres database (use the existing
      `scripts/backup_controlled_pilot_postgres.sh`). Tag the
      backup file with the incident ID.
- [ ] Export `security_audit_events` for the incident window via
      `/admin/security/events` (admin auth required).
- [ ] Capture relevant application logs (no PHI bodies; logs are
      metadata-only by contract).
- [ ] Capture identity-provider sign-in logs for the suspected
      account.
- [ ] Hash and timestamp all evidence files.
- [ ] Store evidence in the practice's approved secure storage —
      **never** in a public bug tracker or chat.

## 5. Investigation

| Step | Owner | Output |
|---|---|---|
| Reconstruct timeline from audit events | ChartNav | Timeline document |
| Identify affected users / patients / encounters | Practice + ChartNav | Scope estimate |
| Determine root cause | ChartNav | Root-cause statement |
| Assess whether ePHI was actually accessed / disclosed | Practice + ChartNav | Breach-or-not determination |
| Document findings | Both | Investigation report |

## 6. Breach assessment

Run the assessment **only after** containment and evidence
preservation. The assessment determines whether the incident
meets the HIPAA Breach Notification Rule definition of a
"breach" (45 CFR §164.402) — that determination is the
practice's, with legal counsel.

Working questions:

- [ ] Was ePHI involved?
- [ ] Was the ePHI acquired, accessed, used, or disclosed?
- [ ] Was the disclosure to a third party (other than a
      workforce member)?
- [ ] Does an exception apply (de minimis disclosure, good-faith
      acquisition, etc.)?
- [ ] Was a low-probability-of-compromise analysis performed?

## 7. Notification

> **Timelines below are working defaults pending legal review.**
> The practice's legal counsel must confirm before real-PHI
> start; the timelines may be tighter (state law, BAA terms,
> contractual obligations) or looser (the HIPAA Breach
> Notification Rule's "without unreasonable delay" standard).

| Audience | Timing (working) | Owner | Channel |
|---|---|---|---|
| Practice security owner | Within 1 hour of confirmation | ChartNav | Pre-agreed contact channel |
| ChartNav incident commander | Within 1 hour of confirmation | Whoever observed | Pre-agreed contact channel |
| Affected vendors / subprocessors | Within 24 hours if vendor-side action required | ChartNav | Pre-agreed vendor contact |
| Practice's HIPAA compliance officer | Within 24 hours of containment | Practice security owner | Practice's internal channel |
| Practice's legal counsel | Within 24 hours of containment for any SEV-1 | Practice security owner | Practice's internal channel |
| Affected individuals (patients) | Per HIPAA Breach Notification Rule §164.404 — practice obligation | Practice | Per practice's notification protocol |
| HHS Office for Civil Rights | Per §164.408 — practice obligation | Practice | Per HIPAA portal |
| Media | Per §164.406 — practice obligation if breach affects 500+ | Practice | Per practice's PR policy |

ChartNav as a Business Associate is responsible for notifying
the practice (Covered Entity) of breaches it discovers under
the BAA. The practice is responsible for downstream
notifications to individuals, HHS, and media.

## 8. Rollback / disable plan

Pre-tested rollback steps (see also `chartnav-backup-disaster-recovery-policy.md`):

- **Disable an endpoint:** redeploy with the endpoint's router
  include commented out, or use a hosting-provider WAF rule.
- **Disable a feature flag:** flip the env variable, restart the
  service.
- **Disable a vendor (STT / LLM):** unset `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER`,
  flip the LLM config to deterministic-only.
- **Disable an account:** practice administrator deactivates at
  the identity provider.
- **Roll back a deploy:** redeploy the previous Docker image tag.
- **Restore from backup:** `scripts/restore_controlled_pilot_postgres.sh`
  (requires confirmation).

## 9. Support-ticket PHI prohibition

PHI in support tickets is its own incident class. See
`chartnav-support-phi-handling-policy.md`. If PHI is
inadvertently posted in a ticket:

- [ ] Immediately redact (edit the message; do not delete the
      thread without preserving evidence).
- [ ] File the incident as SEV-4 (or higher if the ticket has
      been read by unauthorized parties).
- [ ] Notify the practice security owner.
- [ ] Move the conversation to the practice's secure evidence
      channel.

## 10. Post-incident review

Within 5 business days of incident closure:

- [ ] Write a post-incident review document including:
      timeline, root cause, what went well, what didn't, what
      controls are added.
- [ ] Add any new control rows to the risk analysis template
      (`chartnav-security-risk-analysis-template.md`).
- [ ] Add audit-class coverage if a new audit class is needed.
- [ ] Brief the practice security owner.
- [ ] File the review in the practice's incident archive.

## 11. Annual exercise

Once per year (or after a significant architectural change),
the practice and ChartNav jointly walk a tabletop exercise
based on a realistic incident scenario. Output: a written
post-exercise review with action items.

---

## What this runbook does NOT do

- Does not constitute legal advice.
- Does not bind specific notification timelines outside what
  the BAA and applicable law require.
- Does not make ChartNav HIPAA-compliant.
- Does not replace the practice's own incident-response plan;
  it operates alongside it.
