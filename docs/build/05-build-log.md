# Build Log

Reverse-chronological.

---

## 2026-04-17 — Phase: RBAC + full scoping + automated tests

### Step 1 — Baseline
- Starting head: `efb5b56` (dev auth + org scoping).
- No schema changes needed this phase.

### Step 2 — RBAC module
- New `apps/api/app/authz.py`:
  - Role constants `ROLE_ADMIN`, `ROLE_CLINICIAN`, `ROLE_REVIEWER`.
  - `CAN_CREATE_ENCOUNTER`, `CAN_CREATE_EVENT` sets.
  - `TRANSITION_ROLES` map keyed on (from_status, to_status).
  - Dependencies: `require_roles(*)`, `require_create_encounter`, `require_create_event`.
  - `assert_can_transition(caller, from, to)` enforces per-edge RBAC with an admin safety-net for unmapped edges.

### Step 3 — Routes wiring
- `POST /encounters` now depends on `require_create_encounter` → reviewer 403.
- `POST /encounters/{id}/events` now depends on `require_create_event` → reviewer 403.
- `POST /encounters/{id}/status` calls `assert_can_transition` after the state machine accepts the edge. Clinician cannot drive review-stage edges; reviewer cannot drive charting edges.
- `/organizations`, `/locations`, `/users` now require auth and filter `WHERE organization_id = caller.org` (previously unauthenticated).
- Error envelope standardized: every 4xx/5xx now returns `{detail: {error_code, reason}}`. Stable error codes inventoried in `03-api-endpoints.md`.

### Step 4 — Auth seam hardening
- `apps/api/app/auth.py` now reads `CHARTNAV_AUTH_MODE` (default `"header"`) as the single swap point for future transports. Module docstring calls out dev vs. prod.
- Errors routed through a private `_error(code, reason, status)` helper so the shape is consistent with authz.
- Authn vs. authz strictly separated: `auth.py` answers "who" only, `authz.py` answers "may".

### Step 5 — Seed expansion
- `scripts_seed.py` now provisions 5 users across 2 orgs covering all three roles (admin/clinician/reviewer in org1, admin/clinician in org2). Users upserted on re-seed so role changes in the seed converge deterministically. Still idempotent.

### Step 6 — Automated tests
- New `apps/api/tests/` with pytest + FastAPI `TestClient`.
- Per-test temp SQLite fixture: each test gets a fresh migrated + seeded DB, so writes never leak across tests.
- Added `-x sqlalchemy.url=...` support in `alembic/env.py` so the test fixture can migrate an ephemeral DB without rewriting `alembic.ini`.
- Added `pytest` and `httpx` as dev deps.
- Tests cover: auth surface, org scoping across every list/read, cross-org 404, cross-org 403 lens, per-role create/event/transition rules, invalid transitions, event provenance (`changed_by`).
- Run: `pytest tests/ -v` → **25 passed** in ~12s.

### Step 7 — Verification
- `alembic upgrade head` against a fresh DB → both migrations apply.
- Seed idempotent across back-to-back runs (user count stable).
- `pytest` suite green (25/25).
- Full manual sanity: `/me` across all seeded roles returns correct `role` + `organization_id`.

### Step 8 — Documentation
- Updated `01-current-state.md`, `03-api-endpoints.md` (error inventory), `04-data-model.md` (role coverage), `05-build-log.md`, `06-known-gaps.md`, `07-auth-and-scoping.md` (RBAC section + diagram).
- New `08-test-strategy.md` covering harness, matrix, and run command.
- Regenerated `docs/final/chartnav-workflow-state-machine-build.{html,pdf}` with this phase's evidence.

### Step 9 — Git hygiene
- DB reset to seeded state before commit.
- Gitignore already covers `.venv`, `__pycache__`, `.pytest_cache`, `*.db`.

---

## Prior phases (preserved)

### 2026-04-17 — Dev auth + org scoping (phase 3)
Auth dependency, `X-User-Email` transport, `Caller` ctx, cross-org 404/403, two-tenant seed.

### 2026-04-17 — Strict state machine + filtering (phase 2)
`ALLOWED_TRANSITIONS` map, standardized 400 errors on invalid edges, `GET /encounters` filters.

### 2026-04-17 — Workflow spine (phase 1)
Alembic migration `a1b2c3d4e5f6`, idempotent seed, six encounter endpoints.
