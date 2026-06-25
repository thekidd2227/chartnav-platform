# Backup and restore

## What is backed up

- **RDS automated backups** — `backup_retention_period`
  (`db_backup_retention_days`; 14 staging / 35 production) with a daily window,
  enabling **point-in-time recovery (PITR)**.
- **AWS Backup** — a vault (`*-vault`, KMS-encrypted) + daily plan covering the
  RDS instance, with separate retention. (`infra/terraform/aws/backups.tf`)
- **S3 object versioning** — the objects bucket is versioned with lifecycle
  rules; prior versions are retained for recovery from accidental
  overwrite/delete. (`s3.tf`)
- Final snapshot on RDS deletion (`final_snapshot_identifier`); production has
  `deletion_protection`.

## Restore runbook (RDS)

1. Identify the target time / snapshot (CloudWatch + RDS console).
2. **PITR:** `aws rds restore-db-instance-to-point-in-time` → a NEW instance
   (never restore in place over production).
3. Verify the restored instance (schema at expected Alembic head, row spot
   checks) in isolation.
4. Cut over: update the `database-url` secret to the restored endpoint, run a
   one-off `migrate` task if needed, roll the ECS service, verify `/readyz`.
5. Decommission the old instance once verified.

Restore from AWS Backup: `aws backup start-restore-job` with the recovery point
ARN; then the same verify/cutover steps.

## Object restore

Restore a prior S3 object version (versioning enabled): copy the desired
version id back to the live key.

## Verification cadence

Restore drills should be run on a schedule (e.g. quarterly) into an isolated
environment, and the restore time recorded. **No restore drill has been
performed yet** — this runbook is unexercised until staging is provisioned.

## Status

Backups are defined in IaC but **not provisioned** (no AWS apply yet). RPO/RTO
targets must be set with the business and validated by an actual drill before
any availability/durability claim.
