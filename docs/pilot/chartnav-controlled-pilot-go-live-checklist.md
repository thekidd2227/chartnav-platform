# ChartNav Controlled-Pilot Go-Live Checklist (Phase 18)

> The master pre-real-PHI gate. Every box must be checked **and**
> evidence stored before any real patient data moves through
> ChartNav.
>
> If a box is unchecked, the system is **not** ready for real PHI.
>
> This checklist does **not** substitute for the practice's BAA,
> security review, or written approval. It enumerates the gates
> ChartNav and the practice agree on jointly.

---

## How to use this checklist

1. The operator (Jean-Max / ARCG Systems) and the practice's
   designated owners walk this list together.
2. Each item is checked only when **evidence** exists — a
   document, a screenshot, an email, a signed PDF. Verbal
   assurances do not check the box.
3. The **practice security / compliance owner** signs off at the
   end. ChartNav does not unilaterally declare go-live.
4. Once signed, the operator records the real-PHI start date in
   the practice's notebook (out-of-repo).

---

## Section A — Legal + agreements

- [ ] **Business Associate Agreement (BAA) executed** between the
      practice (covered entity) and Ariel's River Contracting
      Group, LLC dba ARCG Systems (business associate).
- [ ] **Pilot agreement signed**, including pricing, success
      metrics, escalation contacts, and pilot end / decision date.
- [ ] **Data processing addendum** (DPA) signed if the practice
      requires one separate from the BAA.
- [ ] **Subprocessor list** acknowledged (hosting provider,
      monitoring vendor, etc.). Each subprocessor must have its
      own BAA chain or be excluded from the PHI path.
- [ ] **STT / external-LLM vendor** decision documented. If
      `CHARTNAV_STT_PROVIDER=openai_whisper` (or any external
      vendor), the practice has approved external PHI egress in
      writing AND a BAA chain exists with that vendor. Otherwise
      `CHARTNAV_STT_PROVIDER=stub` (no external speech-to-text).

## Section B — Practice owners identified

- [ ] **Practice clinical champion** identified by name + role +
      mobile + email.
- [ ] **Practice security / compliance owner** identified.
- [ ] **Practice IT lead** identified.
- [ ] **Practice billing / admin owner** identified (for
      invoicing and pilot fee reconciliation).
- [ ] Contacts stored in the operator's notebook **out-of-repo**.

## Section C — Security review packet accepted

- [ ] Practice security owner has read
      `docs/pilot/chartnav-security-review-packet.md`.
- [ ] Practice security owner has read
      `docs/security/chartnav-production-auth-readiness.md`.
- [ ] Practice security owner has read
      `docs/security/chartnav-monitoring-logging-readiness.md`.
- [ ] Practice security owner has read
      `docs/security/chartnav-incident-response-plan.md`.
- [ ] Practice has accepted ChartNav's stated **non-claims**:
      ChartNav is not HIPAA-certified, not SOC 2-certified, not
      a certified EHR, not autonomous diagnosis, and does not
      create orders / coding / referrals / patient messages.

## Section D — Deployment + hosting

- [ ] **Deployment mode** = controlled-pilot (not local, not
      staging).
- [ ] **Hosting platform** chosen and approved by practice
      (cloud account ID, region, residency).
- [ ] **Postgres** is the database. SQLite is **not** used in
      controlled-pilot.
- [ ] `DATABASE_URL` is set to the practice-approved Postgres URL
      with **rotated** (non-default) credentials.
- [ ] **Network egress** rules reviewed by practice. ChartNav is
      not allowed to reach unapproved external endpoints.

## Section E — Production authentication

- [ ] `CHARTNAV_AUTH_MODE=bearer` (header auth is forbidden in
      controlled-pilot).
- [ ] OIDC issuer (`CHARTNAV_JWT_ISSUER`) configured against the
      practice's IdP.
- [ ] OIDC audience (`CHARTNAV_JWT_AUDIENCE`) registered in the
      IdP.
- [ ] JWKS URL (`CHARTNAV_JWT_JWKS_URL`) reachable over **HTTPS**
      from the API host.
- [ ] User-claim mapping (`CHARTNAV_JWT_USER_CLAIM`) confirmed
      against IdP token shape.
- [ ] **All pilot users provisioned** in `users` table with
      correct `role` (`admin` / `clinician` / `reviewer`) and
      `organization_id`.
- [ ] **Reviewer role** confirmed read-only via smoke test.
- [ ] **Token lifetime** ≤ 1 hour at the IdP.
- [ ] **Refresh token rotation / revocation** verified at the IdP.

## Section F — CORS + transport

- [ ] `CHARTNAV_CORS_ALLOW_ORIGINS` lists only practice-approved
      production frontend hosts. **No** `*`. **No** localhost / 127.0.0.1.
- [ ] All public traffic is over **HTTPS**. HTTP-only listening
      sockets are rejected.
- [ ] `Authorization` headers are dropped by every log forwarder.

## Section G — Audit + retention

- [ ] `CHARTNAV_AUDIT_RETENTION_DAYS` set to the practice-agreed
      retention period.
- [ ] Audit pruning scheduled (e.g. cron / k8s CronJob) per
      retention policy.
- [ ] Sentinel-token regression test (`TestEndToEndAuditRedaction`
      in `apps/api/tests/test_end_to_end_clinical_workflow.py`)
      passes on the controlled-pilot CI.

## Section H — Backup + restore

- [ ] Backup destination chosen and approved by practice
      (`CHARTNAV_BACKUP_DIR` or off-host equivalent).
- [ ] Backup destination has **encryption at rest**.
- [ ] Backup destination is **not the repo, not a developer
      laptop, not the API host's local filesystem alone**.
- [ ] Backup cadence agreed (recommend: daily).
- [ ] `bash scripts/backup_controlled_pilot_postgres.sh` runs
      cleanly (exit 0, non-empty `.sql.gz`).
- [ ] `bash scripts/verify_controlled_pilot_backup.sh <file>`
      reports schema fingerprint OK.
- [ ] **Restore tested** against an isolated Postgres instance.
      Document the date and result.
- [ ] Restore-test cadence agreed (recommend: monthly).

## Section I — Monitoring + logging

- [ ] Log destination configured (`CHARTNAV_LOG_DESTINATION` or
      platform-equivalent).
- [ ] Log destination drops `Authorization` headers before
      persisting.
- [ ] Log destination drops request bodies on POST / PATCH paths
      that touch clinical content, OR all request bodies are
      stripped by default.
- [ ] Health check (`/health`) wired to the practice's monitoring
      system.
- [ ] Alert rules from
      `docs/security/chartnav-monitoring-logging-readiness.md`
      configured (5xx rate, auth failures, cross-org 404 burst,
      disk usage, backup-script exit, audit-prune lag).
- [ ] On-call rotation defined.

## Section J — Incident response

- [ ] `docs/security/chartnav-incident-response-plan.md` reviewed
      with the practice's IT + compliance owners.
- [ ] Severity escalation path documented (S1 → page on-call
      within 15 min → notify practice within 1 hour).
- [ ] Evidence-preservation procedure agreed.
- [ ] Practice's breach-notification process named (ChartNav is
      not the breach-notification owner — the practice is).

## Section K — Operational gating + sign-offs

- [ ] **Env validator passes**: `bash scripts/validate_controlled_pilot_env.sh`
      reports `PASSED` (zero FAIL).
- [ ] **Smoke test passes**: `bash scripts/smoke_controlled_pilot.sh`
      against the controlled-pilot environment (admin / clinician
      / reviewer paths, cross-org isolation against the
      designated pilot test org).
- [ ] **Rollback plan approved** by practice.
- [ ] **First-session plan scheduled** — date, time, staff
      attending, expected encounter count, success criteria.
- [ ] **Real PHI start date** set in writing (email or signed
      doc) by practice clinical champion AND practice security /
      compliance owner.

## Section L — Final sign-off

| Role | Name | Signature / Email confirmation | Date |
|---|---|---|---|
| Practice clinical champion | | | |
| Practice security / compliance owner | | | |
| Practice IT lead | | | |
| ARCG Systems operator (Jean-Max Charles) | | | |

Once all four are signed and every box above is checked, the
real-PHI start date is approved. **Until then, ChartNav runs
fake-data only.**

---

## Reminders

- **No real PHI in the local demo environment.** The reset script
  (`scripts/reset_demo_state.sh`) refuses non-local
  `DATABASE_URL` by design.
- **No real PHI in the staging environment.**
- **No screenshots / video clips / voice-over recordings of real
  PHI.** All capture happens against the seeded fake patient
  Morgan Lee / PT-1001.
- **No real PHI in support tickets, Slack messages, GitHub
  issues, or any non-controlled-pilot surface.**
- ChartNav is not approved for real PHI by default. ChartNav can
  be prepared for a controlled-pilot environment that may
  process real PHI only after BAA execution, practice security
  review, production bearer authentication, Postgres hosting,
  backups, monitoring, audit-retention agreement, incident-
  response contacts, and written practice approval.
