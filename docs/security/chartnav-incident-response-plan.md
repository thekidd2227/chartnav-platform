# ChartNav Incident Response Plan (Phase 18)

> What to do when something goes wrong on a controlled-pilot
> deployment. Read with `chartnav-support-runbook.md` (existing
> support runbook covers severity levels and rollback) and
> `chartnav-monitoring-logging-readiness.md` (what to monitor).

---

## Scope

This plan covers a **controlled-pilot deployment** that may
handle real PHI. For local fake-data demos there is no real-PHI
risk and the support runbook is sufficient.

This plan is **not** a HIPAA breach-notification procedure. If a
suspected breach occurs, the practice's compliance owner must
follow their own breach-notification process (HIPAA / state law /
practice policy). ChartNav supports that process by preserving
evidence and providing technical context, but ChartNav is not
the breach-notification owner.

---

## Severity levels

Aligned with `docs/pilot/chartnav-support-runbook.md`:

| Severity | Definition | Response |
|---|---|---|
| **S1** | Suspected data-safety incident — possible cross-org leak, audit content question, real PHI in logs / tickets, real PHI in a non-controlled environment, suspected token compromise | Stop the system. Page on-call within 15 minutes. Notify practice within 1 hour. |
| **S2** | Service degraded — auth failures, DB connectivity, 5xx > 5% | Page on-call within 1 hour. Investigate during business hours. |
| **S3** | Single-user issue — login problem, role mismatch, UI glitch | Resolve next business day. |

This plan focuses on **S1**.

---

## S1 — Suspected data-safety incident

### Step 1 — Stop

- If the incident occurred during a live demo or pilot session:
  - Stop the demo / session politely.
  - **Do not continue clicking through the workspace.**
  - **Do not paste log lines or screenshots into a Slack channel,
    JIRA ticket, or email** until the redaction step (below) is
    complete.

- If the incident occurred during automated traffic:
  - Disable the affected pilot environment (rollback / scale to
    zero) per `chartnav-support-runbook.md` § Rollback / disable
    pilot.

### Step 2 — Preserve evidence

Before changing anything else, preserve:

- **Application logs** for the affected time window. Pull them
  out of the log aggregator into a dated file in
  practice-approved storage (NOT a public bucket, NOT email).
- **Audit events** for the affected time window:
  ```
  python -c "from app.retention import query_recent; print(...)"
  ```
  or run a SQL `SELECT * FROM security_audit_events WHERE
  created_at >= ...` against a read-only DB connection.
  Save the result to practice-approved storage.
- **Database snapshot**: run
  `bash scripts/backup_controlled_pilot_postgres.sh` and store
  the resulting `.sql.gz` in practice-approved storage.
- **Browser HAR / screenshots from the operator's machine** —
  redact patient identifiers before saving.

Do **not** delete any of the above until the practice's compliance
owner has reviewed.

### Step 3 — Redact before sharing

Any log / ticket / chat message that will leave the controlled-
pilot environment must be scrubbed of:

- ❌ Patient names, MRN, DOB, any identifier.
- ❌ Clinical body text (scribe / findings / summary / brief /
   review notes / drawing JSON).
- ❌ JWT / Bearer tokens.
- ❌ DATABASE_URL (especially the password).
- ❌ Private keys.

When in doubt, paraphrase. "Cross-org 404 fired for actor
user_id=42 against patient_id=N in org 2 (caller is in org 1)"
is fine. Quoting actual patient text is not.

### Step 4 — Notify

| Who | When | What |
|---|---|---|
| ChartNav engineering lead | Within 15 minutes | Incident summary, severity, what was stopped, evidence preserved |
| Practice clinical champion | Within 1 hour | Plain-language summary of what happened and what's stopped |
| Practice security / compliance owner | Within 1 hour | Technical summary + preserved evidence pointer |
| Practice IT lead | Within 1 hour | If the incident touches IdP / auth / network |

Names, emails, and phone numbers go in the **operator's notebook
out-of-repo** — not committed to the repo.

The controlled-pilot go-live checklist requires the practice to
provide these contacts in writing before any real-PHI start
date. If you don't have them, the system isn't ready.

### Step 5 — Investigate

Common S1 patterns + first-line investigation:

| Pattern | Look at |
|---|---|
| Cross-org 404 from same actor multiple times | IdP user-to-org mapping; ChartNav `users.organization_id` for that account |
| Suspected token compromise | IdP audit log; `apps/api/app/auth.py` `iss/aud/exp` rejection patterns |
| PHI in logs | Log aggregator config (drop `Authorization`, drop request bodies on clinical paths) |
| PHI in audit detail | Bug — sentinel tests should have caught it. Snapshot, file an emergency ticket. |
| User in wrong org / wrong role | ChartNav `users.role` and `users.organization_id`; rotate the user's token at the IdP |
| Real PHI in a `local` or `staging` env | Reset the env. The reset script (`scripts/reset_demo_state.sh`) refuses non-local DB URLs by design — but if PHI made it in, the env is no longer trustworthy. |

### Step 6 — Rollback (if needed)

`docs/pilot/chartnav-support-runbook.md` covers rollback /
disable. Briefly:

- **Disable pilot**: scale the API and frontend to zero; keep
  Postgres up so logs and audit events stay queryable.
- **Hard rollback**: redeploy a known-good image from the prior
  release tag. Do NOT roll back the database forward — DB
  rollback is a separate, riskier procedure that requires
  practice approval.

If rollback requires a DB restore:

- Use `bash scripts/restore_controlled_pilot_postgres.sh` against
  an isolated DB.
- Verify with `bash scripts/verify_controlled_pilot_backup.sh`
  first.
- Coordinate the live cutover with the practice — do not surprise
  them.

### Step 7 — Post-incident review

Within 5 business days of the incident:

- Write a post-incident note (paraphrased — no PHI).
- File any code / config fixes against the engineering backlog.
- Update `docs/security/chartnav-monitoring-logging-readiness.md`
  if the incident reveals a missing alert rule.
- Update `docs/pilot/chartnav-support-runbook.md` if the response
  process needs tightening.
- Share the post-incident note with the practice's compliance
  owner — **paraphrased**, no PHI in the note itself.

---

## What NOT to do during an S1

- ❌ Do not paste log lines, screenshots, or audit rows into a
   public Slack channel, public JIRA, public email thread, or
   public Git issue.
- ❌ Do not file a public GitHub issue with PHI or with quoted
   error logs that may contain PHI.
- ❌ Do not delete logs / audit rows / database snapshots before
   the practice's compliance owner reviews.
- ❌ Do not rotate IdP keys without notifying the practice IT lead.
- ❌ Do not "just restart the API" — that may evict useful
   evidence from in-memory caches and request-id correlations.
- ❌ Do not wait for the next business day to notify the practice
   when an S1 has fired.

---

## Contact placeholders (operator-only, out-of-repo)

The operator maintains a private contact card with:

- ChartNav engineering on-call (mobile + email)
- Practice clinical champion (mobile + email)
- Practice security / compliance owner (mobile + email)
- Practice IT lead (mobile + email)
- IdP support / vendor support if applicable
- Hosting platform support (cloud provider account ID)

This card lives in the operator's password manager / private
notebook. It is **not** committed to the repo.

---

## Forbidden in this doc

This is a **process** doc. It does **not** claim:

- ❌ HIPAA-compliant.
- ❌ HIPAA-certified.
- ❌ SOC 2-certified.
- ❌ Certified EHR.
- ❌ Production-ready for PHI.

Real PHI handling requires BAA + practice security review +
written practice approval + the controlled-pilot go-live
checklist.
