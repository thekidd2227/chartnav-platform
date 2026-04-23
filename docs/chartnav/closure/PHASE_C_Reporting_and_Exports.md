# Phase C — Reporting and Exports

## 1. Problem solved
Three different audiences need structured output from ChartNav and
none of them is currently served:
- Clinic operators need operational reports to run the practice.
- Billers need a reviewable handoff bundle so they can submit a claim
  in their own system.
- Compliance officers and auditors need date-ranged exports of audit
  and clinical records, and need to know they can take their data with
  them if the contract ends.

Buyers ask "can we export our data?" in almost every conversation; if
the answer is not "yes, here is the export surface," the conversation
ends.

## 2. Current state
- The Phase B admin dashboard shows live counts for encounters,
  drafts, and reminders.
- There is no report-rendering route, no `reports_runs` table, no
  signed-URL-backed download, and no bulk-export surface.
- `workflow_events` and `security_audit_events` are queryable through
  the admin audit tab but cannot be exported as CSV today.
- Billing handoff is a manual copy-paste out of the signed note.

## 3. Required state
Four report families, one shared rendering pipeline, one export API,
one history table, and one bulk-export surface. Everything produced
is labeled honestly: ChartNav renders operational and compliance
reports; it does not render "certified" quality measures.

Report families:
- Operational: daily encounter volume, sign-to-export lag,
  missing-provider-verify-flag rate, reminders completion percentage.
- Compliance: audit log CSV scoped by date range, role, and user.
- Clinical: encounters by template, encounters by provider, draft-to-
  signed turnaround.
- Billing handoff: CSV and JSON bundle per signed note containing
  patient identifier, encounter date, provider NPI, accepted CPT
  suggestions, carried ICD codes, chief complaint. This is labeled
  in-product as "handoff export" — not "claim submission."
- Bulk full-data export: per-organization zip containing CSV and JSON
  of encounters, notes, structured inputs, reminders, and events.
  Compliance-driven and available on demand.

## 4. Acceptance criteria
- New table `reports_runs` exists with the schema in Section 5.
- Endpoint `POST /admin/reports/{report_key}/render` accepts a
  JSON body with scope fields (`from`, `to`, `provider_id`,
  `template_id`, `role`, `user_id` as applicable) and returns
  `{ run_id, status, signed_url | null }`.
- Endpoint `GET /admin/reports/runs/{run_id}` returns the run record.
- Endpoint `POST /admin/exports/bulk` produces a zip, gated behind
  `clinic_admin` role and logged in `security_audit_events`.
- All report rows are organization-scoped via `ensure_same_org`.
- Pytest files: `backend/tests/test_reports_render.py`,
  `backend/tests/test_bulk_export.py`.
- Frontend: `data-testid="reports-page"`,
  `data-testid="report-card-{report_key}"`,
  `data-testid="report-render-btn"`,
  `data-testid="bulk-export-btn"`,
  `data-testid="bulk-export-confirm-modal"`.
- Every billing-handoff export is stamped with the phrase "Handoff
  export — not a claim submission" in the file header.

## 5. Codex implementation scope
Create:
- `backend/app/models/reports_run.py`
- `backend/app/services/reports/__init__.py`
- `backend/app/services/reports/operational.py`
- `backend/app/services/reports/compliance.py`
- `backend/app/services/reports/clinical.py`
- `backend/app/services/reports/billing_handoff.py`
- `backend/app/services/reports/bulk_export.py`
- `backend/app/routes/admin_reports.py`
- `backend/alembic/versions/xxxx_reports_runs.py`
- `backend/tests/test_reports_render.py`
- `backend/tests/test_bulk_export.py`
- `frontend/src/pages/admin/Reports.tsx`
- `frontend/src/components/reports/ReportCard.tsx`
- `frontend/src/components/reports/BulkExportModal.tsx`
- `frontend/tests/reports.test.tsx`

Modify:
- `frontend/src/pages/admin/Dashboard.tsx` adds a Reports tile link
- `backend/app/routes/__init__.py` registers `admin_reports`

SQL sketch:

```sql
CREATE TABLE reports_runs (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL,
  report_key TEXT NOT NULL,
  scope_json JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued','running','ready','failed')),
  requested_by_user_id UUID NOT NULL,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL,
  artifact_path TEXT NULL,
  signed_url_expires_at TIMESTAMPTZ NULL,
  error_text TEXT NULL
);
CREATE INDEX ON reports_runs (organization_id, report_key, requested_at);
```

Signed-URL contract: `signed_url_expires_at` is always within 15
minutes of issue. The artifact is stored on the operator-controlled
object store configured at deploy time. In standalone mode this is a
local path and the signed URL is a short-lived token-gated download.

Billing handoff CSV header (first line of every file):

```text
# ChartNav Handoff Export — not a claim submission
# org=<org_id> generated_at=<iso8601> run_id=<uuid>
```

## 6. Out of scope / documentation-or-process only
- Live BI dashboards beyond the Phase B admin tiles.
- Scheduled email delivery of reports. This requires the messaging
  seam, which is a separate workstream.
- Custom report builder UI. All reports are defined server-side in v1.
- Certified clinical quality measures (MIPS, HEDIS). Reports are
  operational; we do not claim quality-measure compliance.

## 7. What can be demoed honestly now vs later
Now: the render surface, the history page, a rendered CSV of operational
metrics, a rendered compliance audit CSV, and the bulk-export zip.

Later, once billing handoff has accepted CPT suggestions to carry, the
handoff export becomes meaningful rather than structural. Before that,
we can demo the surface and show the honest header.

## 8. Dependencies
- Phase C CPT suggestion logic for the billing-handoff export to carry
  accepted codes. Until shipped, the handoff export emits an empty
  `accepted_cpt` array with a footer note.
- Operator-controlled object store or signed-URL-capable local path.
- Messaging seam for any future scheduled delivery (explicitly out of
  scope in v1).

## 9. Truth limitations
- Reports are operational metrics and compliance exports; they are
  not certified quality measures.
- The handoff export is a structured bundle for a biller's downstream
  system; it is not a claim, not a 837, not a clearinghouse submission.
- Bulk export accuracy depends on the operator running the audit-
  retention script at the documented cadence; excessively aggressive
  retention can shrink exported history.

## 10. Risks if incomplete
- "Can we get our data out?" becomes a pilot-blocking question that
  sales cannot answer confidently.
- Billers do not perceive the chart as actionable and pilot ROI
  arguments fail at readout.
- Compliance teams treat ChartNav as a data roach-motel and will not
  sign a BAA.
