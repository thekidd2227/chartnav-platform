# Release and rollback

## Release flow

1. Merge to `main` → CI (tests, typecheck, build).
2. Promote to the `staging` branch → `deploy-staging.yml`:
   build + push **immutable** API image (tagged with the commit SHA), build +
   upload frontend to S3 + invalidate CloudFront, register a new ECS task
   definition revision, run a **one-off migration task**, roll the service, and
   verify `/readyz`.
3. Verify staging (smoke + targeted checks).
4. Production: `deploy-production.yml` (manual dispatch, **protected
   environment**, reviewer approval). Promotes the **same image tag** verified
   in staging — no rebuild-from-branch, no auto-deploy.

## Migration policy

- Migrations run as a **separate one-off task** (`entrypoint.sh migrate`), never
  on steady-state API start (`entrypoint.sh serve`).
- **Single Alembic head** is required (CI/readiness gate checks this).
- Migrations must be **backward compatible** with the currently-running image
  for the duration of a rolling deploy (expand → migrate → contract). Prefer
  additive changes; do destructive changes in a later release after the old
  code is gone.
- Always run + verify a migration on **staging** before production.

## Rollback

- **App rollback (fast):** point the ECS service back at the previous
  task-definition revision and wait for stable:
  ```
  aws ecs update-service --cluster <c> --service <s> --task-definition <previous-revision>
  aws ecs wait services-stable --cluster <c> --services <s>
  ```
  Images are immutable + SHA-tagged, so the prior version is always available.
- **Frontend rollback:** re-sync the previous build artifact to S3 + invalidate
  CloudFront (keep the prior `dist` or rebuild the prior SHA).
- **Schema rollback:** prefer **forward-fix** over `alembic downgrade` in
  production (downgrades can lose data). If a migration is bad, ship a
  corrective forward migration. Downgrade only as a last resort, from a backup,
  in an isolated restore (`backup-and-restore.md`).

## Traceability

Every deploy is traceable by the image **SHA tag** (== git SHA) and the ECS task
definition revision. Record both in the deploy record.

## Status

Pipelines are authored but **not yet run** against real infrastructure (no AWS
account wired here). First real release is gated on Terraform apply + the
remaining blockers in the final report.
