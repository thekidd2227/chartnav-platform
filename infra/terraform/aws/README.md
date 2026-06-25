# ChartNav AWS infrastructure (Terraform)

Infrastructure-as-code for ChartNav as a hosted SaaS. **Nothing here has been
applied/provisioned.** This is the IaC foundation; running it creates billable
AWS resources and must be done deliberately by the ChartNav AWS account owner.

> **Not a compliance attestation.** Do not represent AWS services as
> BAA-covered, HIPAA-compliant, or security-approved until the ChartNav AWS
> account has executed and verified the appropriate agreements and service
> eligibility. This IaC provisions the technical building blocks only.

## Architecture

```
Clinic browser ──HTTPS──> CloudFront + WAF ──> S3 (React app, private/OAC)
        │
        └──HTTPS──> Route53 ──> ALB (TLS, WAF) ──> ECS Fargate (FastAPI, private)
                                                      ├──> RDS PostgreSQL (private, Multi-AZ, KMS, PITR)
                                                      ├──> S3 objects (private, KMS, versioned)
                                                      ├──> Secrets Manager (KMS)
                                                      └──> CloudWatch logs + alarms; AWS Backup
```

Files: `networking`, `security-groups`, `kms`, `rds`, `s3`, `ecs` (+ ECR),
`alb`, `cloudfront`, `waf`, `iam` (+ GitHub OIDC deploy role), `secrets`,
`logging`, `backups`, `monitoring`, `dns` (ACM + Route53). Inputs in
`variables.tf`; outputs in `outputs.tf`.

## Guarantees encoded

- Dedicated VPC; **no public RDS endpoint**; ECS + RDS in private subnets.
- Encrypted RDS (customer-managed KMS), automated backups + PITR, Multi-AZ +
  deletion-protection options, `rds.force_ssl=1` (TLS required).
- Private, **public-access-blocked**, versioned, KMS-encrypted S3 buckets;
  TLS-only bucket policy; lifecycle rules; Object Lock design documented.
- ECS Fargate API with least-privilege task role; ALB TLS listener (TLS 1.2+);
  HTTP→HTTPS redirect; immutable ECR with scan-on-push.
- CloudFront (OAC, security headers, SPA fallback) + WAF managed rules + rate
  limiting on both ALB and CloudFront.
- Secrets in Secrets Manager (KMS); **no secrets/account-ids/regions/domains
  hardcoded** (all variables).
- CloudWatch logs (KMS, configurable retention) + alarms (API 5xx/latency, task
  health, RDS CPU/storage, backup failures); AWS Backup vault + plan.
- GitHub Actions deploys via **OIDC** (no long-lived AWS keys).

## Usage (deliberate, by the account owner)

```bash
cd infra/terraform/aws
cp environments/staging.tfvars.example environments/staging.tfvars   # fill in
terraform init -backend-config=environments/staging.backend.hcl
terraform plan  -var-file=environments/staging.tfvars
terraform apply -var-file=environments/staging.tfvars
```

Remote state (S3 bucket + DynamoDB lock table) must exist first and be passed
via `-backend-config`. Validate staging before production; production uses a
protected GitHub environment with manual approval (see
`.github/workflows/deploy-production.yml`).

## Status / not-yet-done

- Not `terraform validate`/`plan`-run in this repo's CI environment (no AWS
  creds, no terraform binary here). Run `terraform fmt -check` + `validate` +
  `plan` via `.github/workflows/terraform-plan.yml`.
- Object Lock audit-export bucket is documented + commented, not enabled.
- PostgreSQL RLS (defense-in-depth) is documented in
  `docs/security/tenant-isolation.md`; app-layer org scoping is the enforced
  control today.
