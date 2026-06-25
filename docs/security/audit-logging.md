# Audit logging

ChartNav writes structured, append-only audit events to the
`security_audit_events` table via `apps/api/app/audit.py::record(...)`.

## Events captured (today)

Authentication outcomes (where available), patient record access
(`patient_viewed`), chart section read/write (`patient_updated`), retina
workflow read/write/sign (`eye_diagram_*` from `eye_diagrams.py`), note
review/sign/export/amend, imaging metadata access, file upload/download
authorization + deletion (storage callers), user/role changes, organization
changes, and security-configuration changes (existing admin-security audit).

## Record fields

`timestamp`, `organization_id`, actor `user_id` + email, `action`/`event_type`,
resource type + id, `outcome`/`error_code`, request/correlation id
(`X-Request-ID`), source IP + user agent where safely available.

## What is NEVER logged

Access tokens, passwords, secrets, dictated audio content, full note bodies,
`findings_text`, `drawing_json`, or unrestricted PHI. Audit `detail` is
metadata only (e.g. `patient_id=… artifact_id=…`, field *names* not values).
This is asserted by tests:
`tests/test_eye_diagrams.py::TestAuditDoesNotLogClinicalContent` and
`tests/test_patient_chart_foundation.py::test_audit_records_view_and_update`.

## Retention + export

- Retention is configured by `CHARTNAV_AUDIT_RETENTION_DAYS` (production
  expected to be multi-year, e.g. 2555 days ≈ 7y). The production-readiness
  gate fails if retention ≤ 0.
- **Export path:** audit rows export to the encrypted object store
  (`docs/security/object-storage.md`) for long-term, tamper-evident retention.
  An **Object Lock (WORM)** audit-export bucket is designed in
  `infra/terraform/aws/s3.tf` (commented) for immutable exports.

## Not yet operational

The export job + Object Lock bucket are designed, not provisioned. Centralized
log aggregation/alerting beyond CloudWatch is not configured. No claim of
tamper-proof audit retention until Object Lock is enabled and verified.
