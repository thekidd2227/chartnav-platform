# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 7: frontend workflow UI

### Step 1 — Baseline
- Starting head: `700bb0b` (prod auth seam + Docker + Postgres parity).
- `apps/web/` was a placeholder — a single `App.jsx` hitting `/health` and an unrelated `main.tsx`.

### Step 2 — Typed API client
- New `apps/web/src/api.ts`:
  - `API_URL` from `VITE_API_URL`, fallback `http://localhost:8000`.
  - `ApiError(status, error_code, reason)` surfaces the backend envelope.
  - Typed wrappers for `/health`, `/me`, `/encounters`, `/encounters/{id}`, `/encounters/{id}/events`, `POST /encounters/{id}/events`, `POST /encounters/{id}/status`, `/locations`.
  - Pure helpers `allowedNextStatuses(role, status)` and `canCreateEvent(role)` that mirror `authz.TRANSITION_ROLES` — for UI affordances only; backend still governs.
- New `apps/web/src/identity.ts` — seeded users list (all 5 demo identities), localStorage persistence, safe fallback.
- New `apps/web/src/vite-env.d.ts` — Vite ambient types for `import.meta.env`.

### Step 3 — App shell
- Rewrote `apps/web/src/App.tsx` as the full workflow app:
  - Sticky header: brand, caller chip, API chip, identity picker (seeded + custom).
  - Two-column layout (collapses on mobile).
- `apps/web/src/main.tsx` imports `App` + `styles.css`.
- New `apps/web/src/styles.css`: one file, CSS variables, color-coded status pills, filter/list/detail/timeline/form styles.

### Step 4 — Encounter list + filters
- Filter bar for `status`, `provider_name`, `location_id`; `clear` button when filters are set.
- Loading / empty / error states in the list.
- Row click selects an encounter (and keyboard Enter/Space).

### Step 5 — Encounter detail + timeline
- Facts grid (org, location, scheduled/started/completed/created).
- Color-coded status pill.
- Timeline renders `event_data` as a readable `key: value · …` line (objects), verbatim for strings; falls back to `—` when null.

### Step 6 — Role-aware actions
- Allowed transitions rendered as buttons based on `(role, current_status)`. When none are allowed, a clean note explains why — no fake-disabled buttons.
- Event composer hidden for reviewers with an explanation; admins + clinicians get it.
- On success: refresh detail + events + list; show a green banner.
- On failure: render the exact `{status} {error_code} — {reason}` string in a red banner. Nothing is silently swallowed.

### Step 7 — Dev UX
- New `apps/web/.env.example` — `VITE_API_URL`.
- Makefile: `web-install`, `web-dev`, `web-build`, `web-typecheck`, `dev` (boots both).
- `make dev` uses a trap-based teardown so Ctrl-C kills both backend and frontend.

### Step 8 — Local verification
- `npx tsc --noEmit` clean after adding `vite-env.d.ts`.
- `npm run build` → `dist/` produced (154 KB JS / 6 KB CSS / 0.4 KB HTML).
- Ran uvicorn + exercised every endpoint the UI depends on against all 5 seeded roles:
  - `/me` returns 200 for all 5, 401 for unknown/empty.
  - `/encounters` scoped correctly (org1 sees 2 rows, org2 sees `[3]`).
  - Filter `status=in_progress` → `['PT-1001']`.
  - Clinician `in_progress → draft_ready` → 200.
  - Clinician `review_needed → completed` → 403 `role_cannot_transition`.
  - Reviewer `review_needed → completed` → 200.
  - Reviewer `POST event` → 403 `role_cannot_create_event`.
  - Admin `POST event` → 201.
- Backend tests still pass (no backend changes this phase).

### Step 9 — Docs
- New: `15-frontend-integration.md`.
- Updated: `01-current-state.md`, `05-build-log.md`, `06-known-gaps.md`, `08-test-strategy.md`, `12-runtime-config.md`.
- Diagrams updated: `system-architecture`, `api-data-flow` (with frontend layer).
- `scripts/build_docs.py` now picks up section 15.
- Final HTML + PDF regenerated.

### Step 10 — Hygiene
- Removed stale `apps/web/src/App.jsx`.
- `.gitignore` already excludes `node_modules`, `dist`, caches; reran `npm install` and only `package-lock.json` grew.
- Dev DB reset before commit.

---

## Prior phases

- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
