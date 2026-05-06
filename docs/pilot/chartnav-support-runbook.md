# ChartNav Support Runbook

How to handle pilot support — from a routine "I can't log in" to a
data-safety incident. This runbook is intentionally short and
practical.

---

## How to report an issue

1. Capture the issue immediately while it is still reproducible.
2. Open a ticket through the practice's preferred channel
   (**to confirm** with each practice — email, ticketing system,
   chat).
3. Include the information from "What information to collect"
   below.
4. Choose a severity level honestly — see "Severity levels."
5. For any data-safety concern, **escalate per the data-safety
   incident escalation path** below before continuing.

---

## What information to collect

When a user reports an issue, capture:

- Reporter name, role, and contact.
- Practice / organization slug.
- Browser + OS (e.g., "Chrome 119 / macOS 14").
- The page or panel where the issue happened (eye-diagram, scribe
  session, patient-summary, pre-visit-brief, provider action
  queue, demo workflow guide).
- The action that triggered it (e.g., "clicked Generate proposals
  from findings").
- The exact error banner text, if any.
- Time of the issue (UTC if possible).
- The encounter ID and patient ID (numeric — not a name).
- Whether the issue is reproducible.
- Any recent change on the practice's side (browser update, VPN
  change, hosting change).

**Do not** include patient names, MRNs, DOBs, or any free-form
clinical text in a support ticket. Use IDs only.

---

## Severity levels

| Severity | Definition | Response target |
|----------|------------|-----------------|
| **S1**   | Data-safety incident — possible PHI exposure, audit-log integrity question, cross-org leak suspicion. | Acknowledge within 1 hour; escalate per the data-safety incident path immediately. |
| **S2**   | Workflow blocker — clinician cannot complete a session / cannot sign / cannot generate a key artifact. | Acknowledge within 4 business hours. |
| **S3**   | Workflow friction — non-blocking bug, UX papercut, awkward error message. | Acknowledge within 1 business day. |
| **S4**   | Cosmetic / docs / question. | Acknowledge within 3 business days. |

Practice-specific response targets are agreed in the pilot
agreement and may override the table above.

---

## Examples of severity

- **S1**: "I logged in as Dr. Patel and saw an encounter for a
  patient who isn't ours." Treat as a possible cross-org leak.
- **S1**: "The audit log on this row contains the patient's chief
  complaint." Treat as a possible audit-redaction regression.
- **S2**: "Clicking Sign on the diagram returns 500 and won't
  complete." Workflow blocker.
- **S2**: "The action queue won't generate; backend returns 500."
- **S3**: "The reason text is hard to read on small monitors."
- **S3**: "The error banner says `internal_error` instead of a
  friendly message."
- **S4**: "Typo in the patient-summary banner copy."

---

## Support workflow

```
S1 ── escalate immediately ──► practice security/compliance owner +
                                ChartNav engineering lead
                              (do not close ticket until reviewed)

S2 ── triage same business day ──► engineering identifies fix ──►
                                    deploy patch / workaround ──►
                                    ticket closed with notes

S3 / S4 ── triage within target ──► add to backlog or ship in next
                                     PR ──► ticket closed
```

For every ticket, record:

- Reporter contact.
- Severity.
- Reproduction steps.
- Resolution.
- Whether a regression test was added (yes for S1/S2; recommended
  for S3/S4).

---

## Troubleshooting — local demo

| Symptom | First thing to try |
|---------|--------------------|
| Workspace empty after identity switch | Confirm `localStorage.chartnav.devIdentity` matches a seeded user. Refresh. |
| `/health` not 200 | `make boot` running? Port `:8000` free? Logs in shell? |
| Demo guide missing | Confirm `patientId !== null` for the encounter. Hard-refresh the browser. |
| Prior demo's edits still visible | `make reset-db && make seed`. |
| `vitest` cannot find a file | Run `make web-install` to refresh node modules. |
| `pytest` cannot find a fixture | Run `make install` to refresh the venv. |

---

## Troubleshooting — pilot deployment

| Symptom | First thing to try |
|---------|--------------------|
| 401 unknown_user on every call | Confirm `CHARTNAV_AUTH_MODE` and the JWT issuer / audience / JWKS URL match the practice's OIDC provider. |
| 404 patient_not_found on a known patient | Confirm the caller's `organization_id` matches the patient's. Cross-org lookups are supposed to look like 404. |
| 403 role_forbidden on a write | Confirm the caller's role is `admin` or `clinician`. `reviewer` is read-only. |
| 409 artifact_signed_immutable | Signed retinal artifacts are immutable in place; pass `?fork=true` to create a new unsigned version. |
| 409 patient_summary_immutable | Finalized / discarded patient summaries are immutable. Create a new draft. |
| Frontend 502 / preview broken | Check Vercel deployment status. Confirm `VITE_API_URL` points at a reachable API host. |
| Postgres connection error | Confirm `DATABASE_URL` is reachable from the API host. Confirm migrations ran. |
| `audit_prune` did not run | Confirm `CHARTNAV_AUDIT_RETENTION_DAYS` is set. |

---

## Data-safety incident escalation

A *data-safety incident* is anything that suggests PHI may have been
exposed, an audit-log entry contains clinical body content, a
cross-org leak is possible, or a signed artifact has been altered
out-of-band.

Escalation path:

1. **Stop** routine work on the affected pilot.
2. Open an `S1` ticket via the practice's preferred channel.
3. Notify the practice's security/compliance owner directly.
4. Notify ChartNav engineering lead directly.
5. Preserve evidence — do **not** truncate logs, do **not** drop
   audit rows, do **not** force-push branches.
6. Wait for the security/compliance owner's go-ahead before any
   data-affecting remediation step.
7. After resolution, file an incident note (out-of-repo) with:
   - timeline of events,
   - what was exposed (or confirmed not exposed),
   - what changed in code, config, or docs,
   - a regression test if applicable.

The practice's pilot agreement may include additional notification
obligations (state law, regulator, patient). ChartNav does not
override those.

---

## Rollback / disable pilot

If a pilot needs to be paused:

- **Disable user access** — the practice's admin can mark users
  inactive (**to confirm** — verify the admin UI exposes this for
  pilot use; otherwise this is an engineering touch).
- **Roll back the API image** to the prior tagged release if a
  recent deploy is suspected.
- **Restore from backup** if a migration or data write is
  suspected.
- **Stop ingestion** by setting `CHARTNAV_STT_PROVIDER=none` if the
  pilot uses Whisper for audio.

The engineering lead is responsible for executing the rollback in
coordination with the practice's owner.

---

## Known limitations

Repeats from
`chartnav-known-limitations-and-non-goals.md` — keep this list
visible to support so it is not relearned per ticket:

- ChartNav is not a certified EHR.
- The clinical-language scan on the action queue is not a primary
  safety net.
- Pre-visit brief data gaps are explicit; missing entries are not
  bugs.
- Signed artifacts are immutable in place by design.
- Finalized / discarded summaries and dismissed / completed action
  items are immutable by design.
- ChartNav does not diagnose, order, code, bill, refer, or message
  patients.

If a support ticket asks "why doesn't ChartNav do X?" and X is on
that list, the answer is "by design." Reference the relevant
contract doc.
