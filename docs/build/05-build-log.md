# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 8: create UI + frontend tests + frontend CI

### Step 1 — Baseline
- Head: `c4f6e4f` (frontend workflow UI).
- Backend unchanged; 28/28 pytest still passing.

### Step 2 — Encounter-create flow
- `api.ts`: new `createEncounter(email, input)` + `canCreateEncounter(role)` helper (admin, clinician).
- `App.tsx`: `+ New encounter` button in header (only visible for roles that can create); new `CreateEncounterModal` component. Modal fetches `/locations` (already scoped server-side), auto-selects when there's one, validates required fields, disables submit while in-flight, and surfaces backend `{error_code, reason}` inline. On success the list is refreshed and the new encounter is auto-selected.
- `styles.css`: small modal styles (backdrop, card, body form).

### Step 3 — UX hardening
- All mutating buttons (transition / event append) now disable while their request is in flight and show a pending label.
- Detail pane returns `null` cleanly during loading to avoid flashing stale content after identity switches.
- Create and status banners annotated with `role="alert"` / `role="status"` and `data-testid` for accessibility + tests.
- Identity badge distinguishes loading (`identity-loading`), error (`identity-error`), and resolved (`identity-badge`) states.

### Step 4 — Frontend test harness
- Installed `vitest`, `@vitest/ui`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, `@types/node`.
- `vite.config.js` → `vite.config.ts` with a `test` block (environment `jsdom`, globals, setup file, CSS off).
- `src/test/setup.ts`: wires jest-dom matchers + per-test cleanup (DOM + localStorage).
- `tsconfig.json`: added `types: ["vite/client", "vitest/globals", "@testing-library/jest-dom"]` and included `vite.config.ts`.

### Step 5 — Frontend tests
- `src/test/App.test.tsx`: **12 integration tests** mocking `./api`:
  - Identity badge resolves from `/me`.
  - Mocked list renders both seeded encounters.
  - Status filter calls `listEncounters({status})` and updates the visible list.
  - Selecting an encounter loads detail + timeline.
  - Clinician / reviewer each see only their permitted transition buttons.
  - Reviewer sees `event-denied` note; event composer absent.
  - Reviewer cannot see the `+ New encounter` button; admin can.
  - Create happy path: form submit → backend call → success banner → modal closes.
  - Create sad path: backend 403 `cross_org_access_forbidden` surfaces inline; modal stays open.
  - Switching identity via the picker refetches `/me` + list.
  - Unknown email (custom input) shows `identity-error` with `unknown_user`.
  - Status transition call refreshes detail + events and shows success banner.
- Known harness quirk: vitest 4 runs the tests on Node 24 where `localStorage` is a native-but-unconfigured feature, so we drive identity switches through the UI rather than writing to `localStorage` directly. The `./identity` module's localStorage calls are already wrapped in `try/catch` — the app keeps working either way.

### Step 6 — Frontend CI
- New `frontend` job in `.github/workflows/ci.yml`: Node 20 + npm cache keyed on `apps/web/package-lock.json` → `npm ci` → `npm run typecheck` → `npm test` → `npm run build`.
- Runs on `push` to `main` and every PR, in parallel with `backend-sqlite`.

### Step 7 — Dev UX
- Makefile gains `web-test`, `web-verify` (typecheck + test + build) alongside existing `web-install / web-dev / web-build / web-typecheck`.
- `make dev` (boot both) unchanged.
- `apps/web/.env.example` unchanged — still `VITE_API_URL=http://localhost:8000`.

### Step 8 — Docs
- New: `16-frontend-test-strategy.md`.
- Updated: `01-current-state`, `05-build-log`, `06-known-gaps`, `08-test-strategy`, `09-ci-and-deploy-hardening`, `12-runtime-config`, `15-frontend-integration`.
- Diagrams refreshed: `system-architecture` (add Vitest), `api-data-flow` (include create flow + frontend CI gate).
- `scripts/build_docs.py` picks up section 16.
- Final HTML + PDF regenerated.

### Step 9 — Hygiene
- Removed `apps/web/vite.config.js` (superseded by `.ts`).
- Dev DB reset to pristine seeded state.
- `.gitignore` already excludes `node_modules`, `dist`, `coverage` (default), caches.

---

## Prior phases

- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
