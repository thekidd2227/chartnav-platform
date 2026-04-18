# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 13: operator control plane (org settings + audit read + user lifecycle)

### Step 1 — Baseline
- Head: `4ff4e28` (admin governance + event discipline + pagination).
- 71 pytest + 18 vitest + 10 Playwright green.

### Step 2 — Migration `d4e5f6a7b8c9`
- `organizations.settings TEXT NULL` for tenant preference JSON.
- `users.invited_at DATETIME NULL`; server stamps it on admin-create.
- Applied cleanly; seed still idempotent; seeded users keep `invited_at = NULL`.

### Step 3 — Backend endpoints
- `GET /organization` (any authed role), `PATCH /organization` (admin only).
  - Slug immutable by construction — no PATCH accepts it.
  - `settings` must be a JSON object; ≤ 16 KB after serialization or 400 `settings_too_large`.
- `GET /security-audit-events` (admin only):
  - Filters: `event_type`, `error_code`, `actor_email`, `q` (substring over `path` / `detail`).
  - Pagination: `limit` (1..500, default 50), `offset` (≥0); returns `X-Total-Count`, `X-Limit`, `X-Offset`.
  - Org scoping: `organization_id = caller.org OR organization_id IS NULL`. Pre-auth failures (no caller) are visible to every admin; cross-org denials with an identity stay private to that identity's org.
- `POST /users` now sets `invited_at = now()`.
- `list_users` / `list_users?include_inactive=1` include the `invited_at` column.

### Step 4 — Backend tests (`test_control_plane.py`, 17 new)
- `/organization` reads (all 3 roles + 401), admin PATCH name + settings, non-object settings → 422, oversized settings → 400, non-admin PATCH → 403, cross-org isolation on PATCH.
- Audit read admin-only; filters for `event_type`, `actor_email`, `q`; pagination with disjoint pages and correct headers; org-scoping never leaks cross-org rows.
- `invited_at` stamped on create; seeded rows are null.
- **Full backend suite: 88/88 passed** (~45s).

### Step 5 — Frontend API + UI
- `api.ts`:
  - Types: `Organization`, `SecurityAuditEvent`, `AuditFilters`; `invited_at` added to `User`.
  - Functions: `getOrganization`, `updateOrganization`, `listAuditEvents` (returns `{items, total, limit, offset}` from the header-based paginator).
- `AdminPanel.tsx` becomes 4 tabs:
  - **Users** — adds an "Invited" badge for active users with `invited_at` set.
  - **Locations** — unchanged.
  - **Organization** — loads current org, readonly slug, editable name + settings textarea (local JSON parse, server 16 KB cap).
  - **Audit log** — filter row (event_type / actor_email / free-text q), paginated table (25/page), newest-first.
- `styles.css` — textarea styling added to `.modal__body`.
- Typecheck clean; `vite build` emits 175 KB JS / 8.2 KB CSS.

### Step 6 — Frontend tests
- `AdminPanel.test.tsx` — added 4 tests: org-tab loads current, org PATCH fires with correct body, local JSON parse error (bracket-array) surfaces without hitting backend, audit tab loads + filter dispatches + 403 surfaces.
- `App.test.tsx` unchanged.
- Vitest: **22/22 passed**.

### Step 7 — E2E
- New scenario: "admin can edit organization settings and inspect audit log" — drives the Organization + Audit tabs against the live stack.
- Playwright: **11/11 passed** in ~17s.

### Step 8 — Docs
- New `docs/build/23-operator-control-plane.md`.
- Updated `01-current-state`, `05-build-log`, `06-known-gaps`, `03-api-endpoints` (new endpoints + error codes), `04-data-model` (new columns + migration), `08-test-strategy` / `16-frontend-test-strategy`, `15-frontend-integration` (control-plane UI), `18-operational-hardening` (audit read surface), `22-admin-governance` (user lifecycle signal note).
- Diagrams: `er-diagram` includes `settings` / `invited_at`; `api-data-flow` keeps phase-10/12 flows, still accurate for new admin endpoints (same dispatch model).
- `scripts/build_docs.py` picks up section 23.
- Final HTML + PDF regenerated.

### Step 9 — CI
- **No workflow YAML changes required.** New tests live in paths that `backend-sqlite` / `frontend` / `e2e` already collect. Alembic migration runs via the same `alembic upgrade head` step every backend job executes.
- `deploy-config` (compose + shellcheck) untouched.

### Step 10 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- `.gitignore` unchanged (already excludes caches, `.db`, dist, etc.).

---

## Prior phases

- **Phase 12 — Admin governance** (`4ff4e28`)
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
