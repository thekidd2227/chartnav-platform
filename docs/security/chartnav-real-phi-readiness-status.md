# ChartNav Real PHI Readiness Status (Phase 18)

> **Bottom line:** ChartNav is **not** approved for real PHI by
> default. ChartNav can be prepared for a controlled-pilot
> environment that may process real PHI **only after** BAA
> execution, practice security review, production bearer
> authentication, Postgres hosting, backups, monitoring,
> audit-retention agreement, incident-response contacts, and
> written practice approval.
>
> Read this doc end-to-end before any real-PHI conversation with
> a practice. Read it again before the first real-PHI session.

---

## 1. Current status

| Question | Answer |
|---|---|
| Is ChartNav HIPAA-certified? | **No.** ChartNav is not HIPAA-certified. Covered entities and business associates implement HIPAA; ChartNav supports those obligations contractually via BAA. |
| Is ChartNav SOC 2-certified? | **No.** SOC 2 is not pursued at this stage. |
| Is ChartNav FDA-cleared? | **No.** FDA clearance is not pursued; ChartNav is documentation support, not a clinical decision device. |
| Is ChartNav HITRUST-certified? | **No.** HITRUST is not pursued at this stage. |
| Is ChartNav a certified EHR? | **No.** ChartNav is a documentation + review assistant that lives alongside an existing EHR. |
| Is real PHI safe in the local demo? | **No.** Local demo is fake-data only by construction. The reset script refuses non-local `DATABASE_URL`. |
| Is real PHI safe in staging? | **No.** Staging is fake-data only. |
| Is real PHI safe in a controlled-pilot deployment? | **Conditionally.** Only after every gate in the controlled-pilot go-live checklist is met, AND the practice signs off in writing. |

---

## 2. What is technically ready

Phase 6 → Phase 18 has built and tested:

- **Provider-reviewed clinical workflow** (scribe lifecycle,
  retinal proposal review, OD/OS canvas with immutable signed
  artifacts, patient-friendly summary draft, pre-visit brief,
  provider action review queue).
- **Bearer JWT auth** (`apps/api/app/auth.py`) with signature +
  issuer + audience + expiry validation, 11 dedicated tests in
  `apps/api/tests/test_auth_modes.py`.
- **Role-based access control** (`apps/api/app/authz.py`),
  reviewer read-only enforcement asserted by
  `apps/api/tests/test_rbac.py`.
- **Per-organization isolation** — cross-org requests fail closed
  (`404 patient_not_found`); enforced at every clinical surface
  with explicit tests.
- **Metadata-only audit log** — sentinel-token regression tests
  in `apps/api/tests/test_end_to_end_clinical_workflow.py::TestEndToEndAuditRedaction`
  guarantee no clinical body content reaches `security_audit_events.detail`.
- **Audit retention** — `CHARTNAV_AUDIT_RETENTION_DAYS` env var
  + `scripts/audit_retention.py` operator CLI + 3 retention
  tests in `apps/api/tests/test_enterprise.py`.
- **Postgres parity** — `scripts/pg_verify.sh` runs the full
  smoke suite against a throwaway Postgres on every CI commit.
- **Docker production compose** — `infra/docker/docker-compose.prod.yml`
  with Postgres + healthcheck.
- **Phase 18 tooling** — env validator, backup, restore, verify,
  smoke test scripts (all under `scripts/`).
- **Phase 18 documentation** — production-auth readiness,
  monitoring/logging readiness, incident response plan,
  controlled-pilot go-live checklist (all under
  `docs/security/` and `docs/pilot/`).

---

## 3. What still requires practice / legal / security action

These cannot be solved by ChartNav alone. The practice (or the
practice's IT / compliance owners) must provide:

- **Business Associate Agreement (BAA)** signed with ARCG Systems.
- **Practice security review acceptance** of
  `docs/pilot/chartnav-security-review-packet.md`.
- **Practice OIDC issuer** (or operator-managed equivalent) with
  registered ChartNav audience.
- **Practice-approved hosting** (cloud account, region,
  residency).
- **Practice-approved backup destination** with encryption at rest.
- **Practice-approved log destination** (no PHI in logs).
- **Practice-approved STT vendor** (default `stub` is safe;
  external STT requires BAA chain + written practice approval).
- **Incident response contacts** (clinical champion, security /
  compliance owner, IT lead).
- **Written real-PHI start date** signed by clinical champion AND
  security / compliance owner.
- **(Optional)** independent pen test / vulnerability scan if
  the practice requires one.

---

## 4. What is explicitly not ready

- ❌ Real PHI in local or staging environments — not now, not in
  the future. Local and staging are fake-data only.
- ❌ Auto-provisioning of users from JWT claims. Users must be
  explicitly added to the `users` table.
- ❌ Custom roles claims from JWT — ChartNav reads role from its
  own `users.role` column.
- ❌ External LLM source under the same provider-review contract —
  deferred.
- ❌ Specialty-specific risk scoring — deferred.
- ❌ Patient-portal delivery — deferred.
- ❌ Orders / coding / billing automation — deferred (and out of
  product scope for this phase numbering).
- ❌ Automated follow-up creation — deferred.
- ❌ Longitudinal trend analytics across encounters — deferred.
- ❌ EHR adapter integrations beyond the existing FHIR shape —
  deferred per practice.
- ❌ Team queues / task-assignment routing — deferred.

---

## 5. What is forbidden

- ❌ `CHARTNAV_AUTH_MODE=header` in any environment that may handle PHI.
- ❌ SQLite as `DATABASE_URL` in controlled-pilot.
- ❌ `CHARTNAV_CORS_ALLOW_ORIGINS=*` or any localhost / 127.0.0.1
  origin in controlled-pilot.
- ❌ Default placeholder credentials (`chartnav:chartnav`) in
  controlled-pilot DATABASE_URL.
- ❌ Backups committed to the repo or stored on developer laptops.
- ❌ JWTs / tokens / DATABASE_URL values in logs, tickets, Slack,
  email, or screenshots.
- ❌ Restore script invocation without `CHARTNAV_RESTORE_CONFIRM=I_UNDERSTAND`.
- ❌ External STT vendor without
  `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1` (or equivalent) AND
  written practice approval.
- ❌ Real PHI in any screenshot, video clip, voice-over, or demo
  deck.

---

## 6. Controlled-pilot go-live gates

Every gate below must be checked AND backed by evidence (a
document, an email, a signed PDF) before the first real-PHI
session. Verbal assurance is insufficient.

The full checklist is at
[`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`](../pilot/chartnav-controlled-pilot-go-live-checklist.md).

Top-level summary:

- A. Legal + agreements (BAA, pilot agreement, DPA, subprocessor
  list, STT vendor decision).
- B. Practice owners identified (clinical champion, security /
  compliance owner, IT lead, billing / admin owner).
- C. Security review packet accepted by practice.
- D. Deployment + hosting on practice-approved infra.
- E. Production bearer auth with practice IdP.
- F. Explicit CORS, HTTPS-only transport, log forwarders strip
  `Authorization`.
- G. Audit retention + pruning configured.
- H. Backup + verified restore.
- I. Monitoring + logging + alerts.
- J. Incident response contacts + breach-notification owner
  named.
- K. Env validator + smoke test pass.
- L. Final sign-off by all four owners.

---

## 7. Required sign-offs

| Role | What they sign off on |
|---|---|
| Practice clinical champion | Real-PHI start date, success metrics, escalation path |
| Practice security / compliance owner | Security review packet, retention period, incident response process, breach-notification ownership |
| Practice IT lead | Hosting + IdP + network egress + monitoring + backup destination |
| ARCG Systems operator | Env validator passes, smoke test passes, all evidence collected |

All four signatures are recorded in the practice's pilot
agreement (out-of-repo). The repo only carries the **process** —
not the signatures.

---

## 8. How to validate the environment

```
bash scripts/validate_controlled_pilot_env.sh
```

The script must report `PASSED` (zero FAIL). It checks (without
printing values):

- `CHARTNAV_AUTH_MODE=bearer`
- `CHARTNAV_JWT_ISSUER`, `CHARTNAV_JWT_AUDIENCE`,
  `CHARTNAV_JWT_JWKS_URL` set; JWKS uses HTTPS
- `DATABASE_URL` is Postgres (not SQLite, not the local demo file)
- `CHARTNAV_CORS_ALLOW_ORIGINS` explicit and dev-free
- `CHARTNAV_AUDIT_RETENTION_DAYS` is an integer
- `CHARTNAV_BACKUP_DIR` set or warned
- `CHARTNAV_LOG_DESTINATION` set or warned
- `CHARTNAV_STT_PROVIDER` is approved
- `CHARTNAV_RUN_SEED=0`
- Branch is `main`

---

## 9. How to back up and restore

**Backup** (idempotent, non-destructive):

```
CHARTNAV_BACKUP_DIR=/path/to/practice-approved/storage \
  bash scripts/backup_controlled_pilot_postgres.sh
```

Refuses against SQLite or unset `DATABASE_URL`. Writes a
timestamped `.sql.gz` file. Verifies non-empty after writing.

**Verify backup** (structural check, no DB connect):

```
bash scripts/verify_controlled_pilot_backup.sh /path/to/backup.sql.gz
```

**Restore** (DESTRUCTIVE — overwrites the live DB):

```
CHARTNAV_RESTORE_CONFIRM=I_UNDERSTAND \
  bash scripts/restore_controlled_pilot_postgres.sh /path/to/backup.sql.gz
```

Refuses without the confirm flag. Refuses against SQLite. Refuses
on missing or empty backup file. Includes a 10-second
countdown before executing.

Restore-test cadence: at least monthly against an isolated
Postgres instance. Document the date and result.

---

## 10. How to monitor

See [`chartnav-monitoring-logging-readiness.md`](./chartnav-monitoring-logging-readiness.md).

Highlights:

- API health (`/health`), DB connectivity, auth failure patterns,
  cross-org 404 bursts, 5xx rate, audit prune cadence, backup
  success, disk usage.
- Logs MUST drop `Authorization` headers and request bodies on
  clinical-write paths.
- Audit detail is metadata-only by code-and-test contract.

---

## 11. How to respond to incidents

See [`chartnav-incident-response-plan.md`](./chartnav-incident-response-plan.md).

Highlights:

- **S1 = data-safety incident.** Stop the system, preserve
  evidence, redact before sharing, notify practice within 1
  hour.
- ChartNav is not the breach-notification owner — the practice
  is. ChartNav supports the practice's process by preserving
  evidence and providing technical context.
- Never paste PHI / tokens / DATABASE_URL into a public ticket
  or chat.

---

## 12. Exact readiness statement

Use this exact wording in any external conversation about
ChartNav's readiness for real PHI:

> **ChartNav is not approved for real PHI by default. ChartNav
> can be prepared for a controlled-pilot environment that may
> process real PHI only after BAA execution, practice security
> review, production bearer authentication, Postgres hosting,
> backups, monitoring, audit-retention agreement, incident-
> response contacts, and written practice approval.**

Do not paraphrase this in a way that softens any of the gates.
Do not claim certifications ChartNav does not hold. Do not
promise a real-PHI start date that hasn't been signed by the
practice's clinical champion AND security / compliance owner.

---

## What this doc is NOT

- **Not** a HIPAA compliance attestation.
- **Not** a SOC 2 attestation.
- **Not** a certified-EHR claim.
- **Not** practice approval.
- **Not** a substitute for the BAA.
- **Not** a substitute for a practice security review.
- **Not** a guarantee — every gate has to be met for **each
  practice**, not once globally.
