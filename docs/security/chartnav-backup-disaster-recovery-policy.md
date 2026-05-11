# ChartNav Backup / Disaster Recovery Policy

> **Phase:** 23.
> **Type:** Policy applied to any ChartNav environment that may
> process real PHI. Practice reviews and accepts this policy as
> part of Gate 4 of `chartnav-real-phi-go-live-gate.md`.

## 1. Scope

This policy covers backups and disaster recovery for the
ChartNav controlled-pilot Postgres database. It does **not**
cover:

- The practice's own EHR (separate system).
- The practice's storage backend for imaging binaries — Phase
  21B stores metadata only; binaries live in the practice's
  storage and are backed up per the practice's own policy.
- ChartNav's source repository (handled by GitHub).

## 2. Database

- **Production:** Postgres only. SQLite is forbidden in any
  environment that may process real PHI (the validator gates on
  this).
- **Encryption at rest:** managed by the hosting provider.
- **Encryption in transit:** TLS-only.

## 3. Backup tooling

- `scripts/backup_controlled_pilot_postgres.sh` is the
  authoritative backup script. It:
  - Refuses to run against a SQLite connection string.
  - Refuses to print secrets.
  - Produces a single dump file (encrypted at the hosting layer
    where supported).
- `scripts/verify_controlled_pilot_backup.sh` confirms the
  backup file exists, is non-empty, and matches the expected
  format.

## 4. Backup cadence

| Cadence | Default |
|---|---|
| Full Postgres dump | **Daily** at a practice-agreed time |
| Audit-event archive (`security_audit_events`) | **Daily** (included in the full dump) |
| Verification check | **Daily**, immediately after the backup completes |

The practice may set a different cadence in the BAA or a side
letter. The validator captures the configured cadence.

## 5. Backup destination

- Must be an **approved storage destination** owned by the
  practice or contracted by ChartNav with a BAA on file.
- Examples (none assumed without practice approval): hosting
  provider's managed backup, practice-owned S3 bucket,
  practice-approved third-party backup vendor.
- **No PHI backups may be committed to any source repository.**
  The `.gitignore` excludes backup-file naming patterns.

## 6. Backup retention

- Practice-agreed retention duration.
- Default working assumption: **30 days** for daily backups, but
  the practice may set longer (e.g. 7 years for regulatory
  reasons).
- Retention enforcement is the storage destination's
  responsibility, not ChartNav's.

## 7. Restore tooling

- `scripts/restore_controlled_pilot_postgres.sh` is the
  authoritative restore script. It:
  - Requires explicit confirmation before running.
  - Refuses to run against a SQLite connection string.
  - Restores the most recent verified backup unless a specific
    file is specified.

## 8. Restore testing

- **Restore test required** before real-PHI start.
- The practice (or a designated operator) executes the restore
  against a non-production environment and documents the
  result.
- Frequency after go-live: **quarterly** at minimum.
- Evidence: restore-test log in the practice's records.

## 9. RPO / RTO

| Metric | Working default | Practice may override |
|---|---|---|
| RPO (Recovery Point Objective) | 24 hours | Yes |
| RTO (Recovery Time Objective) | 4 hours | Yes |

RPO is bounded by the backup cadence; RTO is bounded by the
practice's operational tolerance. Both are placeholders until
the practice specifies its tolerance in the BAA or a side
letter.

## 10. Backup failure alerting

- The hosting environment must alert on backup failure within
  the cadence window.
- Alert destination is the practice's on-call security owner.
- ChartNav is notified via the practice's standard channel.

## 11. Disaster recovery scenarios

| Scenario | Recovery procedure |
|---|---|
| Database corruption | Restore most recent verified backup; replay any audit gaps |
| Hosting outage | Failover within hosting provider; restore-test verifies recoverability |
| Region failure | Cross-region restore (if hosting provider supports it); RTO may exceed default |
| Encryption-key loss | **Catastrophic.** Practice and ChartNav must establish key-escrow policy before real-PHI start. |
| Backup corruption | Step back to previous-day backup; longer recovery window |

## 12. Roles and approvals

| Action | Approver |
|---|---|
| Scheduled backup | Automated |
| Off-cycle backup | Practice administrator |
| Restore to staging | ChartNav engineer |
| Restore to production | Practice security owner + ChartNav incident commander (joint approval) |
| Backup deletion | Practice administrator |

## 13. What is **not** in backups

- ChartNav does not back up the practice's storage backend
  (imaging binaries live there; practice owns its backup).
- ChartNav does not back up identity-provider state (IdP owns
  its backups).
- ChartNav does not back up source code (GitHub).

## 14. Audit of backup operations

- Backup script invocations are logged at the operating-system
  level by the hosting provider.
- Restore script invocations record an audit event in
  `security_audit_events` when run against the controlled-pilot
  environment (planned addition; current scripts log to stdout
  and the hosting log forwarder).

---

## Policy review cadence

- Annually.
- After any incident involving backup or restore.
- After any change to the hosting provider or backup
  destination.
