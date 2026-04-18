# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 12: admin governance + event discipline + pagination

### Step 1 — Baseline
- Head: `ee7cf43` (staging deployment + observability).
- 51 pytest + 12 vitest + 8 Playwright green.

### Step 2 — DB role constraint + soft-delete columns
- New Alembic migration `c3d4e5f6a7b8`:
  - `CHECK (role IN ('admin','clinician','reviewer'))` on `users.role` via `batch_alter_table` (works on SQLite + Postgres).
  - `is_active BOOLEAN NOT NULL DEFAULT true` on `users` and `locations`.
- Applied cleanly; seed still idempotent.

### Step 3 — Admin authz dependency
- `app.authz.require_admin`: FastAPI dep that 403s non-admins with `role_admin_required`.

### Step 4 — Event schema discipline
- New `EVENT_SCHEMAS` map in `routes.py` with per-type required keys for `encounter_created`, `status_changed`, `note_draft_requested`, `note_draft_completed`, `note_reviewed`, `manual_note`.
- New `_validate_event(event_type, event_data)` — rejects unknown types, non-object payloads, and missing required keys with stable error codes (`invalid_event_type`, `invalid_event_data`).
- `POST /encounters/{id}/events` runs through the validator. Server-written events bypass (known-good by construction).

### Step 5 — Pagination
- `GET /encounters` accepts `limit` (default 50, 1..500) and `offset` (≥0). Returns headers `X-Total-Count`, `X-Limit`, `X-Offset`. Response body stays a JSON array — backward compatible with clients that ignore headers.

### Step 6 — Admin CRUD endpoints
- `POST/PATCH/DELETE /users`, `POST/PATCH/DELETE /locations`, all admin-only, strictly org-scoped.
- Self-protection: admin cannot demote self (`cannot_demote_self`) or deactivate self (`cannot_deactivate_self`).
- Cross-org mutation → `404 *_not_found` (no existence leak).
- Email uniqueness check (`user_email_taken` 409); email format via Pydantic regex (422 on invalid).
- Soft-delete flips `is_active = 0`; `GET` lists filter to active by default, `?include_inactive=1` shows all.

### Step 7 — Backend tests
- New `apps/api/tests/test_admin.py` — **20 tests** covering DB role CHECK, admin create/update/deactivate users + locations, non-admin denial, cross-org denial (404), event type + data validation, pagination headers + filter combinations.
- Existing suites untouched by the new validator: role-gated tests still 403 before reaching the validator; status-change path writes server-constructed event data which matches the schema.
- Full backend suite: **91/91 passed**.

### Step 8 — Frontend
- `apps/web/src/api.ts`: typed `User`, `Location` interfaces; `createUser`, `updateUser`, `deactivateUser`, `listUsers`, `createLocation`, `updateLocation`, `deactivateLocation`, `listLocations`, `listEncountersPage`; `isAdmin(role)`; `EVENT_TYPES` + `EVENT_TYPE_REQUIRED` constants mirroring the backend schema.
- `requestWithResponse(...)` helper exposes response headers so the pagination helper can read `X-Total-Count` / `X-Limit` / `X-Offset` cleanly.
- `apps/web/src/AdminPanel.tsx` — NEW modal with Users + Locations tabs. Create forms with validation + in-flight disabled state. Users table exposes inline role change + deactivate/reactivate; self-row is disabled. Locations table supports inline rename + deactivate.
- `App.tsx`:
  - Header gains the **Admin** button for `isAdmin` callers.
  - Encounter list uses `listEncountersPage` and renders Prev/Next/"N-M of T" controls when `total > PAGE_SIZE` (25).
  - Event composer's `event_type` input became a `<select>` wired to `EVENT_TYPES` — the UI can no longer submit unknown types.
- `styles.css` — admin modal/table/pagination layout.

### Step 9 — Frontend tests
- New `apps/web/src/test/AdminPanel.test.tsx` — **5 Vitest tests**: lists users, submits create-user, surfaces 409 error, disables self-row controls, creates a location on the Locations tab.
- Existing `App.test.tsx` — added 1 test for admin-button visibility across roles; updated the list mock to use `listEncountersPage`.
- Frontend suite: **18/18 passed**.

### Step 10 — E2E
- Updated `apps/web/tests/e2e/workflow.spec.ts`:
  - Event composer test now uses the `<select>`-based event-type + `manual_note` payload.
  - New: admin creates a user AND a location end-to-end via the admin panel, asserts they appear in the tables.
  - New: non-admin (clinician) does not see the Admin button.
- `scripts/staging_verify.sh` also updated to post a valid `manual_note` event.
- Playwright: **10/10 passed** in ~16s.

### Step 11 — Verification summary
- `make verify` → 91/91 pytest + 9/9 smoke + teardown clean.
- `cd apps/web && npm run build` → 168 KB JS / 8.1 KB CSS.
- `cd apps/web && npx tsc --noEmit` → clean.
- `cd apps/web && npx vitest run` → 18/18.
- `cd apps/web && npx playwright test` → 10/10.
- `scripts/build_docs.py` → HTML + PDF regenerated.
- Dev DB reset to pristine seeded state before commit.

### Step 12 — CI
- No workflow edits required: the new tests live in `apps/api/tests/` and `apps/web/src/test/` + `apps/web/tests/e2e/`, which the existing `backend-sqlite` / `frontend` / `e2e` jobs already pick up. New migration is applied by the same `alembic upgrade head` every job runs.
- `deploy-config` lane (compose config + shellcheck) still applies to the modified `scripts/staging_verify.sh`.

### Step 13 — Docs
- New `docs/build/22-admin-governance.md`.
- Updated `01-current-state`, `05-build-log`, `06-known-gaps`, `02-workflow-state-machine` (event schema section), `03-api-endpoints` (admin routes + pagination), `04-data-model` (role CHECK + is_active), `15-frontend-integration` (admin UI + pagination + event dropdown), `16-frontend-test-strategy` (admin panel tests).
- Diagrams: `er-diagram` notes role CHECK + is_active; `api-data-flow` keeps prior flows, still accurate.
- `scripts/build_docs.py` picks up section 22.
- Final HTML + PDF regenerated.

---

## Prior phases

- **Phase 11 — Staging deployment + observability** (`ee7cf43`)
- **Phase 10 — Real JWT bearer + operational hardening** (`cbc5184`)
- **Phase 9 — Playwright E2E + release pipeline** (`74fe8dd`)
- **Phase 8 — Create UI + vitest + frontend CI** (`f83d748`)
- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
