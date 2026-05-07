# ChartNav Monitoring + Logging Readiness (Phase 18)

> Operational signals + log-handling rules for a controlled-pilot
> deployment. This is a **technical-and-process** doc, not a
> compliance attestation. Real PHI handling still requires a
> Business Associate Agreement, practice security review, and
> written practice approval.

---

## What this doc covers

- What ChartNav emits (metrics, logs, audit events).
- What an operator must monitor in a controlled-pilot deployment.
- What MUST NOT appear in logs / metrics / tickets.
- Where logs go and who owns retention.
- How the existing audit subsystem already prevents PHI leakage.

---

## What ChartNav emits

### 1. Application logs (`apps/api`)

The FastAPI app logs at INFO level for normal traffic, WARNING
for non-fatal anomalies, and ERROR for unhandled exceptions /
failed requests.

**Logs include:**

- HTTP method + path + status code + latency.
- A request ID (UUID) per request.
- Auth failure category (e.g. `unknown_user_for_token`,
  `missing_token`) — but **never** the token itself.
- The actor's `users.id` (integer) — but **never** the email or
  any other identifier on a non-error path.

**Logs MUST NOT include:**

- ❌ JWT / Bearer tokens (full or partial).
- ❌ User passwords or any secret.
- ❌ Patient names, MRN, DOB, or any clinical body content
  (scribe text, findings text, summary body, brief body, action
  details).
- ❌ `findings_text`, `drawing_json`, or any column flagged as
  PHI in the `chart_artifacts` migration.

### 2. Audit events (`security_audit_events` table)

Written by `apps/api/app/audit.py::record(...)`. Every
state-changing API call emits one row. The contract is
**metadata-only**:

- `event_type` (e.g. `eye_diagram_signed`, `scribe_finalized`).
- `request_id`, actor `users.id`, `organization_id`, `path`,
  `method`, `status_code`.
- A short `detail` string with **no clinical body content**.
  E.g. `artifact_id=42 version=2 parent=41 signed=true`.

**Enforcement:**

- `apps/api/tests/test_end_to_end_clinical_workflow.py::TestEndToEndAuditRedaction`
  injects sentinel tokens into every clinical-body field
  (scribe text, findings, summary, review notes) and asserts
  none of them appear in any audit `detail` after the workflow
  runs.
- Sentinel tokens: `PHI_E2E_SOURCE_TOKEN_AAA`,
  `PHI_E2E_FINDINGS_TOKEN_BBB`, `PHI_E2E_SUMMARY_TOKEN_CCC`,
  `PHI_E2E_REVIEW_TOKEN_DDD`.
- The test runs on every CI commit.

### 3. Audit retention

- Configurable via `CHARTNAV_AUDIT_RETENTION_DAYS`
  (non-negative integer; `0` disables automatic pruning).
- Pruning CLI: `python scripts/audit_retention.py [--days N]
  [--dry-run]`.
- Tests: `apps/api/tests/test_enterprise.py::test_retention_*`
  cover disabled-when-zero, dry-run, and actual deletion.

The practice agrees the retention period in writing before
pilot go-live (see the controlled-pilot go-live checklist).

### 4. AI governance log (`ai_governance_log` table)

Records every AI-generator call (scribe synthesis, retinal
proposal generation, summary draft, etc.):

- `request_id`, actor `users.id`, `organization_id`, generator
  name, deterministic-vs-stub flag, and a short status code.
- Body content is **not** stored.

This is queried by the admin security posture surface to give
the operator visibility into how often AI generators ran. It is
**not** an alerting source on its own.

---

## What to monitor

The operator (or the practice's IT lead) must wire these to the
practice's monitoring stack. ChartNav does not ship a
prepackaged dashboard.

### Health + availability

| Signal | How |
|---|---|
| API up | `GET http://<host>/health` returns 200 |
| Database connectivity | API `/health` includes a DB ping; failures surface as 503 |
| Frontend up | A periodic GET against the public URL |

### Auth + access patterns

| Signal | Why |
|---|---|
| Auth failures (`401`) | Spike may indicate token-vendor outage, MFA failure, or attempted token replay |
| Cross-org `404 patient_not_found` | Spike may indicate misconfigured token mapping OR a probe |
| `403 role_forbidden` | Spike may indicate a user changed roles in the IdP but ChartNav `users.role` wasn't updated |

### Error patterns

| Signal | Threshold |
|---|---|
| 5xx rate | > 1% of requests over 5 minutes |
| 4xx rate (excluding 401/403) | > 5% of requests over 5 minutes |
| Latency p95 | > 2 seconds on read endpoints |

### Operational

| Signal | Why |
|---|---|
| Audit prune runs | Confirm `python scripts/audit_retention.py` ran on schedule |
| Backup success | `scripts/backup_controlled_pilot_postgres.sh` exit 0 + non-empty `.sql.gz` |
| Backup verification | `scripts/verify_controlled_pilot_backup.sh` exit 0 |
| Disk / storage usage | Postgres data volume + backup destination volume |
| Restore test cadence | At least once per month against an isolated Postgres instance |

### Suspicious patterns

| Signal | Action |
|---|---|
| Same actor receiving cross-org `404` repeatedly | Investigate IdP mapping for that user |
| Admin actions outside business hours | Confirm with the practice that the admin is real and authorized |
| Bursty `eye_diagram_*` audit events from a single actor | Confirm the activity matches the schedule |

---

## What MUST NOT appear in logs / metrics / tickets

- ❌ Full JWTs, partial JWTs, refresh tokens, session IDs.
- ❌ User passwords or any secret value.
- ❌ Database connection strings (`DATABASE_URL`) — scrub from
   any error output before paste.
- ❌ Patient names, MRN, DOB, or any other identifier.
- ❌ Clinical body text (scribe text, findings, summary, brief,
   review notes, drawing JSON).
- ❌ Audit detail bodies (these are metadata-only by contract,
   but never quote them in tickets — paraphrase instead).

If a log line contains any of the above, treat it as a
data-handling incident and follow the incident response plan.

---

## Logging destination contract

ChartNav writes logs to stdout/stderr. The deployment platform
(Docker, Kubernetes, ECS, Fargate, etc.) is responsible for
forwarding to a log aggregator.

**Constraints on the log aggregator:**

- Storage must be on practice-approved infrastructure (per
  BAA + security review).
- Storage must NOT retain auth headers — most aggregators
  retain HTTP headers by default; explicitly drop `Authorization`
  before persisting.
- Storage must NOT retain request bodies on POST / PATCH paths
  that touch clinical content (most aggregators do not retain
  bodies by default; if your stack does, configure the drop
  rule explicitly).
- Retention period must match what the practice agreed in the
  BAA / DPA.

The validator at `scripts/validate_controlled_pilot_env.sh`
checks for `CHARTNAV_LOG_DESTINATION` and warns if unset.

---

## Backup / restore signals

- **Backup schedule**: at least daily for any environment that
  may handle real PHI. Practice + operator agree the cadence in
  the controlled-pilot go-live checklist.
- **Backup destination**: practice-approved storage with
  encryption-at-rest. Never the repo. Never a developer laptop.
  Never an unencrypted volume.
- **Backup verification**: run
  `bash scripts/verify_controlled_pilot_backup.sh <file>` after
  each backup. The script confirms gzip integrity + ChartNav
  schema fingerprint without decoding clinical content.
- **Restore test cadence**: at least monthly against an isolated
  Postgres instance (NOT the live controlled-pilot DB). The
  restore script (`scripts/restore_controlled_pilot_postgres.sh`)
  refuses to run without `CHARTNAV_RESTORE_CONFIRM=I_UNDERSTAND`.

---

## Suggested alert rules (operator-tunable)

| Rule | Threshold | Action |
|---|---|---|
| API health failing | 2 consecutive failures | Page on-call |
| 5xx rate > 1% / 5min | sustained | Page on-call |
| Auth failures > 50 / 1min from same IP | sustained | Investigate (may be a probe) |
| Cross-org 404 pattern from same actor | > 5 in 1 min | Investigate IdP mapping |
| Backup script exit non-zero | once | Page on-call |
| Audit prune missed | > 24 hours overdue | Page operator |
| Disk usage > 80% | once | Page operator |

---

## Tooling pointers

- `scripts/validate_controlled_pilot_env.sh` — env-shape gate.
- `scripts/backup_controlled_pilot_postgres.sh` — Postgres dump.
- `scripts/restore_controlled_pilot_postgres.sh` — destructive
  restore (refuses without confirmation flag).
- `scripts/verify_controlled_pilot_backup.sh` — structural check.
- `scripts/smoke_controlled_pilot.sh` — token-driven smoke (no
  PHI required).
- `scripts/audit_retention.py` — operator pruning CLI.

---

## What this doc is NOT

- **Not** a turn-key monitoring dashboard. The practice + operator
  must wire ChartNav's stdout/stderr to their preferred stack
  (Datadog, Grafana, CloudWatch, etc.).
- **Not** a SIEM or HIDS / NIDS solution. Network-level monitoring
  is the practice's responsibility.
- **Not** a compliance attestation. ChartNav is **not**
  HIPAA-certified, SOC 2-certified, or a certified EHR.
