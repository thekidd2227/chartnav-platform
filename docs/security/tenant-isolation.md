# Tenant isolation

ChartNav is multi-tenant by `organization_id`. Isolation is enforced at the
**service / data-access layer**, not merely in the frontend.

## Model

- Every tenant-owned row carries `organization_id`.
- The authenticated `Caller` (from `require_caller`) carries
  `organization_id`, `user_id`, and `role`.
- Patient-scoped reads/writes resolve the patient through an org-scoped loader
  that compares `row.organization_id == caller.organization_id`. A miss —
  whether the row doesn't exist or belongs to another org — returns the **same
  non-disclosing 404** (`patient_not_found`), so existence never leaks across
  tenants.
  - `apps/api/app/api/routes.py::_load_patient_for_caller` (patient detail /
    encounters / chart-sections).
  - `apps/api/app/api/eye_diagrams.py::_resolve_patient_in_org` +
    `app/services/chart_artifacts.py` (`get_for_patient` filters by
    `organization_id` and `patient_id`).
- Object storage keys are org-prefixed (`org/<id>/…`) and an explicit
  `key_belongs_to_org` check guards every read/delete
  (`apps/api/app/storage/`).

## Tests (runtime, enforced)

- `tests/test_eye_diagrams.py::TestOrgIsolation` — cross-org list/get/sign → 404.
- `tests/test_patient_chart_foundation.py` — cross-org GET/PATCH/encounters/
  chart-sections → 404.
- `tests/test_object_storage.py` — cross-org presign/delete refused; keys are
  org-scoped.
- `tests/test_admin.py` — admin/org governance.
- Static guard: `scripts/production/verify_tenant_isolation.py`.

## PostgreSQL RLS (defense-in-depth) — designed, NOT yet implemented

Application-layer scoping is the **enforced** control today. PostgreSQL
Row-Level Security is a planned additional layer:
- a per-request `SET LOCAL app.current_org = <id>` on the pooled connection;
- `ENABLE ROW LEVEL SECURITY` + a `USING (organization_id = current_setting(
  'app.current_org')::int)` policy on tenant tables.

RLS is **not** implemented or tested yet, so we do **not** claim row-level
security. It must not replace application-layer scoping — it augments it. Track
before any claim of DB-enforced isolation.
