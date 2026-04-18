# Build Log

Reverse-chronological. Each entry is a concrete, verifiable step.

---

## 2026-04-17 — Phase: dev auth + org scoping

### Step 1 — Baseline
- Starting head commit: `505f025` (strict state machine + filtering phase).
- Alembic head still `a1b2c3d4e5f6` — no schema changes needed this phase.

### Step 2 — Auth foundation
- New `apps/api/app/auth.py`: `Caller` dataclass, `require_caller` FastAPI dependency, `ensure_same_org` guard.
- `require_caller` reads `X-User-Email`, looks up the user by email, and returns structured context. 401 on missing/empty header; 401 on unknown email.
- Added `GET /me` route that echoes the resolved caller — proves the auth wiring end-to-end.

### Step 3 — Org scoping on encounter routes
- `apps/api/app/api/routes.py`:
  - `GET /encounters` now always filters `organization_id = caller.organization_id`. `?organization_id=` query becomes a lens: mismatch → 403.
  - `GET /encounters/{id}`, `GET /encounters/{id}/events`, `POST /encounters/{id}/events`, `POST /encounters/{id}/status` use a shared `_load_encounter_for_caller` helper that returns 404 on cross-org (no existence oracle).
  - `POST /encounters` forces `organization_id` to the caller's org via `ensure_same_org`; location must also belong to caller org or 403.
  - `encounter_created` and `status_changed` events now record the acting user email (`created_by` / `changed_by`).

### Step 4 — Seed expansion
- `scripts_seed.py` now seeds two organizations (demo-eye-clinic + northside-retina) with their own admins, locations, and encounters — enough to actually exercise scoping.
- Still idempotent across N runs; verified with back-to-back executions.

### Step 5 — Local verification
- Fixed a bug introduced during auth scaffolding: `auth.py` initially resolved `chartnav.db` from the wrong parent (`apps/api/app/chartnav.db`); corrected to `Path(__file__).resolve().parents[1] / "chartnav.db"` (= `apps/api/chartnav.db`). Before fix all scoped routes returned 500.
- Post-fix: full matrix green — see `06-known-gaps.md` for the proof table.

### Step 6 — Documentation
- Updated `01-current-state.md`, `03-api-endpoints.md`, `04-data-model.md`, `05-build-log.md`, `06-known-gaps.md`.
- Added `07-auth-and-scoping.md`.
- Updated diagrams: `system-architecture.md`, `api-data-flow.md`, `er-diagram.md`.
- Regenerated `docs/final/chartnav-workflow-state-machine-build.{html,pdf}` so the consolidated artifact now covers Phase 1 (workflow spine) + Phase 2 (state machine + filtering) + Phase 3 (auth + scoping).

### Step 7 — Git hygiene
- DB reset to pristine seeded state before commit.
- SQLite `.db` file stays gitignored.
- One atomic commit with code + docs + regenerated final artifacts.

---

## 2026-04-17 — Phase: workflow state machine + filtering (prior)

See original entry preserved below for history.

### Step 2 — Strict status state machine
- Added `ALLOWED_TRANSITIONS` map.
- Edges: forward `scheduled→in_progress→draft_ready→review_needed→completed`; rework `draft_ready→in_progress`, `review_needed→draft_ready`.
- All other edges → 400 `invalid_transition` with explicit allowed-next-states listing.
- Same-status = no-op.
- `in_progress` stamps `started_at` if null; `completed` stamps `completed_at` (and backfills `started_at` if null).

### Step 3 — Filters
- `GET /encounters` accepts `organization_id`, `location_id`, `status`, `provider_name`. AND-ed, parameterized.

### Step 4 — Seed coverage
- Two encounters covering `in_progress` and `review_needed` with realistic event history.

### Step 5 — Verification
- Filter matrix + state-machine matrix all green.

---

## 2026-04-17 — Phase: workflow spine (earlier)

### Migration `a1b2c3d4e5f6`
- Added `encounters` and `workflow_events` tables with FKs and indexes.

### Seed
- Idempotent demo org / location / admin / encounter / events.

### Initial routes
- 6 encounter endpoints (3 read, 3 write).
