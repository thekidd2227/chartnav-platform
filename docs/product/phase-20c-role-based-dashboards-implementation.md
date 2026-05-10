# Phase 20C — Role-Based Clinic Dashboards (Implementation)

> **Status:** Implemented (this PR).
> **Type:** Backend role enum extension + 6 dashboard endpoints
> + frontend `RoleDashboard` view + sidebar wiring + tests.
> **Builds on:** Phase 20B Structured Data Layer (work queue +
> role view presets) and Phase 20A.1 (HIPAA readiness scaffolding).
> **Branch:** `feature/phase-20c-role-based-dashboards`.

This phase ships read-only, role-aware dashboards that summarize
the active clinic state for each role, without exposing PHI
bodies, clinical text, or operational controls beyond what those
roles already had. It does not introduce specialty modules,
imaging tables, multi-clinic scheduling, or HIPAA controls
(those remain Phase 21+ scope).

## Roles

`users.role` is extended from `('admin','clinician','reviewer')`
to also include `('front_desk','technician')`. The CHECK
constraint is rewritten via Alembic
`d5e6f7a8b9c0_phase_20c_extend_user_roles`, using
`op.batch_alter_table` so the SQLite test database picks the
change up too.

`app.authz.KNOWN_ROLES` and `DASHBOARD_ROLES` are updated to
match. The new roles do **not** acquire encounter-mutation
rights (`canCreateEncounter`, `canCreateEvent`,
`allowedNextStatuses`); they only gain the right to read their
own dashboard endpoint.

## Endpoints (6)

| Method | Path | Role |
|---|---|---|
| GET | `/dashboards/front-desk` | `front_desk` (admin override) |
| GET | `/dashboards/technician` | `technician` (admin override) |
| GET | `/dashboards/doctor` | `clinician` (admin override) |
| GET | `/dashboards/reviewer` | `reviewer` (admin override) |
| GET | `/dashboards/admin` | `admin` |
| GET | `/dashboards/me` | dispatches by `caller.role` |

All endpoints accept `?location_id=` and `?provider_id=`
optional filters. `admin` may pass `?role=` to view any other
role's dashboard payload (`/dashboards/me` does the same
automatically). All other callers may only read their own role.

### RBAC + isolation

- Caller resolution is the standard `Depends(require_caller)`.
- Cross-org isolation: every query is scoped to
  `caller.organization_id`; cross-org rows are unreachable.
- `_resolve_dashboard_role()` raises `403
  role_dashboard_forbidden` when a non-admin attempts to read
  another role's dashboard, and `403 role_dashboard_unknown` if
  an admin asks for an unknown role.
- Audit metadata-only contract: dashboard reads are not
  high-risk, but the standard `/dashboards/*` access path inherits
  the `RequestIdMiddleware` + `AccessLogMiddleware` chain. No
  PHI is logged.

### PHI surface

Queue items returned from the dashboard endpoints are filtered
through `_compact_queue_item()`, which drops the entire
`payload_json` body. Only IDs (encounter, patient, provider,
location), `queue_type`, `status`, `priority`, timestamps, and
`due_at` are exposed.

## Frontend

### `apps/web/src/api.ts`

- Added types: `DashboardRole`, `DashboardScope`,
  `DashboardQueueItemCompact`, `FrontDeskDashboard`,
  `TechnicianDashboard`, `DoctorDashboard`, `ReviewerDashboard`,
  `AdminDashboard`, `DashboardSummary`, `DashboardFilters`.
- Added 6 functions: `getMyDashboard`,
  `getFrontDeskDashboard`, `getTechnicianDashboard`,
  `getDoctorDashboard`, `getReviewerDashboard`,
  `getAdminDashboard`.
- Extended the `Role` enum to include `front_desk` and
  `technician` (mirrors backend CHECK).

### `apps/web/src/RoleDashboard.tsx`

Single self-contained component. Internal `DashboardBody`
dispatches by `data.role` to one of five subcomponent views
(front-desk, technician, doctor, reviewer, admin). Admin users
see a `View as` `<select>` that swaps the active payload (and
calls the targeted endpoint). Non-admins do not see the
selector.

Each role view renders:
- A grid of count cards (the hero numbers).
- A queue-item list (technician/doctor/reviewer) or a recent
  activity strip (front-desk), or breakdown tables (admin).
- No PHI bodies, no patient names, no DOB, no note text.

### `apps/web/src/App.tsx`

A new `topView` state (`"encounters" | "dashboard"`) gates the
right-pane render. The CORE > Dashboard sidebar item is now
clickable (was disabled placeholder). The CORE > Encounters
item also calls a handler so users can switch back. The
identity badge friendly-label set is extended to render
"Front Desk" and "Technician" for the new roles.

### `apps/web/src/identity.ts`

`SEEDED_IDENTITIES` adds 4 dev identities (front desk +
technician for each seeded org) so the dev identity picker can
exercise every role.

### `apps/web/src/styles.css`

Appends `~150` lines of `.role-dashboard__*` styles using the
existing `--cn-*` palette. No new tokens introduced.

## Tests

### Backend (22 tests, all passing)

`apps/api/tests/test_phase_20c_role_dashboards.py` covers:
- `TestAuthAndRBAC` — unauthenticated access blocked; non-admin
  cannot read other roles; admin override works; `/me` dispatches
  by role.
- `TestOrgIsolation` — cross-org rows never appear; admin in
  Org 2 only sees Org 2 work queue.
- `TestLaneCounts` — front-desk / technician / doctor counts
  match seeded queue rows.
- `TestStatusExclusion` — completed / cancelled rows excluded
  from open counts.
- `TestAdminAggregates` — group-by-status / -priority / -role /
  -queue_type aggregates correct; overdue + unsigned-notes
  counts correct.
- `TestPHISafety` — payload bodies never returned; only
  compacted queue items.
- `TestRoleEnumExtension` — `front_desk` and `technician`
  identities can authenticate; user table accepts the new roles.

### Frontend

`apps/web/src/test/RoleDashboard.test.tsx` covers:
- Each role renders the correct lane labels + count values.
- Admin `View as` selector swaps the rendered payload.
- Non-admin does not see the selector.
- Error path renders the banner (`role_dashboard_forbidden`).
- Forbidden-vocabulary scan: no `billing`, `claim`, `insurance`,
  `copay`, `deductible`, `cpt`, `icd-10`, `eob`, `remit`.
- PHI scan: no patient names or DOB-shaped strings in the
  rendered DOM.

## Out of scope (intentionally deferred)

- Specialty modules (Phase 21A).
- Imaging tables / DICOM storage (Phase 21B).
- Multi-clinic / cross-location scheduling (Phase 22).
- HIPAA controls beyond Phase 20A.1 readiness scaffolding
  (Phase 23).
- Website or commercial-deck updates (intentionally not
  shipped — the dashboards are operator-facing, not buyer-facing).
- Real PHI (the seeded data remains synthetic).

## Migration roundtrip

`d5e6f7a8b9c0_phase_20c_extend_user_roles`:
- `upgrade()`: rewrites `users.role` CHECK to include
  `front_desk` + `technician`. Uses `batch_alter_table` for
  SQLite parity.
- `downgrade()`: restores the original 3-value CHECK; will fail
  if seed rows include the new roles (intentional — downgrade
  is a developer-only operation).

## Files touched

- `apps/api/alembic/versions/d5e6f7a8b9c0_phase_20c_extend_user_roles.py` (new)
- `apps/api/app/api/role_dashboards.py` (new)
- `apps/api/app/main.py` (router include)
- `apps/api/app/authz.py` (role enum + `DASHBOARD_ROLES`)
- `apps/api/scripts_seed.py` (4 new dev identities)
- `apps/api/tests/conftest.py` (4 new identity headers)
- `apps/api/tests/test_phase_20c_role_dashboards.py` (new, 22 tests)
- `apps/web/src/api.ts` (Role enum + dashboard types/functions)
- `apps/web/src/RoleDashboard.tsx` (new)
- `apps/web/src/App.tsx` (top-view switch + sidebar wiring +
  friendly role labels)
- `apps/web/src/identity.ts` (4 new seeded identities)
- `apps/web/src/styles.css` (role-dashboard CSS)
- `apps/web/src/test/RoleDashboard.test.tsx` (new)
- `docs/product/phase-20c-role-based-dashboards-implementation.md` (this file)
