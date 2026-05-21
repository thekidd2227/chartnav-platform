# Phase 65 Pilot Issue and Incident Triage Template

Status: template
Audience: support owner, pilot owner, engineering owner

Use this template in a practice-approved private tracker. Do not paste
real PHI into this file or into repo issues.

## Severity Definitions

| Severity | Definition | Initial action |
| --- | --- | --- |
| S1 | Data-safety concern, possible cross-org leak, sensitive content in logs/audit, wrong environment, token compromise | Stop affected use, preserve evidence, notify practice contacts |
| S2 | Core workflow blocker for pilot users, repeated 5xx/auth failures, cannot review/sign | Pause affected workflow, triage same business day |
| S3 | Nonblocking workflow friction or confusing UI/error state | Track for weekly review |
| S4 | Docs, question, cosmetic issue | Track for backlog |

## Intake Template

```text
Issue ID:
Date/time:
Reported by:
Reporter role:
Practice/org:
Environment:
Severity:
Workflow surface:
Affected role(s):
Affected user count:
Encounter/patient numeric IDs only:
What happened:
Expected behavior:
Actual behavior:
Exact visible error:
API route or URL:
Console/network evidence:
Backend log request_id if available:
Reproducible? yes/no/unknown:
Immediate action taken:
Safety concern? yes/no:
Real PHI in ticket? must be no:
Owner:
Next update due:
Resolution:
Regression test needed? yes/no:
```

## Evidence Rules

Allowed:

- Numeric IDs.
- Request IDs.
- Route names.
- Timestamp.
- Role.
- Redacted screenshot with no patient identifiers.
- Error banner text if it contains no clinical content.

Forbidden:

- Patient name.
- MRN.
- DOB.
- Address.
- Phone.
- Clinical note text.
- Transcript text.
- Vitals values tied to a real patient.
- Fundus findings tied to a real patient.
- JWTs, Authorization headers, API keys, passwords, database URLs.

## S1 Escalation Path

1. Stop affected workflow.
2. Preserve logs and audit rows in practice-approved storage.
3. Notify practice security/compliance owner.
4. Notify ChartNav engineering owner.
5. Do not restart, reset, prune, delete, or force-push until evidence
   is preserved.
6. Follow `docs/security/chartnav-incident-response-plan.md`.
7. Complete a post-incident note out-of-repo.

## Closure Criteria

S1:

- [ ] Practice security/compliance owner reviewed.
- [ ] Evidence preserved.
- [ ] Root cause documented.
- [ ] Fix or mitigation approved.
- [ ] Regression or monitoring added when applicable.
- [ ] Practice approves return to operation.

S2:

- [ ] Workflow restored or workaround approved.
- [ ] Root cause documented.
- [ ] Regression test or smoke coverage considered.
- [ ] Pilot owner approves close.

S3/S4:

- [ ] Backlog or docs update created.
- [ ] Reporter notified.
