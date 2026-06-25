# Incident response

A starting runbook for the hosted ChartNav service. **Provisional** — owners,
contacts, and SLAs must be confirmed before launch.

## Severity

| Sev | Definition | Examples |
|---|---|---|
| SEV1 | Outage or suspected PHI exposure | API down, data breach suspicion, auth bypass |
| SEV2 | Major degradation | elevated 5xx/latency, failed deploy, backup failures |
| SEV3 | Minor / single-tenant | isolated feature bug |

## Detection

CloudWatch alarms → SNS topic (`*-alarms`, email subscription): API 5xx,
p99 latency, ECS running-task count, RDS CPU/free-storage, AWS Backup job
failures (`infra/terraform/aws/monitoring.tf`). Structured JSON access logs +
audit events (`security_audit_events`) support investigation by
`request_id`/`organization_id`.

## Response

1. **Acknowledge** the alarm; declare severity; open an incident channel.
2. **Assess blast radius** — which org(s), endpoints, data. Use request-id
   correlation; never copy PHI into the incident channel.
3. **Mitigate** — roll back the service to the previous task-definition revision
   (`release-and-rollback.md`); scale out; or, for a suspected auth/data issue,
   consider disabling the affected path / rotating IdP + app secrets
   (Secrets Manager).
4. **Communicate** — status to affected clinics per the comms plan.
5. **Recover** — restore data if needed (`backup-and-restore.md`); verify
   `/readyz` + spot checks.
6. **Post-incident** — blameless review; track corrective actions.

## Suspected PHI exposure

Treat as SEV1. Preserve logs/audit trail, scope the affected records + orgs,
engage the privacy/compliance owner, and follow the breach-notification
obligations applicable to the BAA/regulatory posture **once that posture is
formally established** (it is not yet — do not assume HIPAA breach procedures
are in force until verified).

## Status

No on-call rotation, paging, or formal SLAs are configured. This runbook is a
scaffold pending operational ownership.
