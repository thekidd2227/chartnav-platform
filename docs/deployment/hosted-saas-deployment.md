# Hosted SaaS deployment

How ChartNav is delivered as a hosted application to medical offices. **Nothing
here is provisioned yet** — this describes the target and the steps to stand it
up deliberately in the ChartNav AWS account.

## Target experience (medical office)

1. Clinic receives a secure invitation email.
2. Staff open **https://app.chartnavmd.com** in a current browser
   (Chrome / Edge / Safari / Firefox, latest 2 versions).
3. Sign in through the identity provider with **MFA** (IdP-enforced).
4. No clinic user installs Python, Node, Docker, PostgreSQL, or source.
5. ChartNav centrally manages deployments, backups, monitoring, upgrades.

## Architecture

```
Browser ─HTTPS→ CloudFront + WAF ─→ S3 (React app, private/OAC)
   └────HTTPS→ Route53 → ALB (TLS, WAF) → ECS Fargate (FastAPI, private subnets)
                                            ├─ RDS PostgreSQL (private, KMS, Multi-AZ, PITR)
                                            ├─ S3 objects (private, KMS, versioned)
                                            ├─ Secrets Manager (KMS)
                                            └─ CloudWatch logs + alarms; AWS Backup
```

IaC: `infra/terraform/aws/` (see its README). Containers:
`apps/api/Dockerfile` (+ `entrypoint.sh migrate|serve`), `apps/web/Dockerfile.production`.

## Bring-up (account owner, deliberate)

1. Create remote-state S3 bucket + DynamoDB lock table (out of band).
2. Create the OIDC app in the IdP; note issuer / audience / JWKS; require MFA.
3. `terraform apply` **staging** (`environments/staging.tfvars`). Set the
   `app`/`database-url` Secrets Manager values (IdP issuer/JWKS).
4. Configure GitHub Actions repo **vars** (role ARN, region, hostnames,
   bucket/distribution/cluster/service/subnets/SG) + protected `production`
   environment reviewers.
5. Deploy staging (`deploy-staging.yml`): builds image, runs the one-off
   migration task, rolls the service, verifies `/readyz`.
6. Run `scripts/production/production_readiness_check.py --env-file <prod env>`
   — must be green.
7. `terraform apply` **production**; promote the staging-verified image via
   `deploy-production.yml` (manual, reviewer-approved).

## Runtime config

See `docs/build/12-runtime-config.md` and `apps/api/.env.example` /
`apps/web/.env.example`. Production requires `CHARTNAV_ENV=prod`,
`CHARTNAV_AUTH_MODE=bearer`, a PostgreSQL `DATABASE_URL` with `sslmode=require`,
`CHARTNAV_STORAGE_BACKEND=s3` + KMS key, explicit HTTPS CORS, and multi-year
audit retention — all enforced by the readiness gate + config startup refusals.

## Honest status

Not deployed. No AWS resources provisioned; no BAA/HIPAA/security attestation.
Terraform has not been `validate`/`plan`-run in this repo (no terraform binary /
AWS creds here) — run it via `terraform-plan.yml`. Remaining blockers in
`release-and-rollback.md` and the final report.
