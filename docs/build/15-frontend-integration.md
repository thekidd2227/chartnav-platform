# Frontend Integration

## Goal

Turn the backend workflow slice into a usable app. An operator should
be able to identify themselves, filter their org's encounters, open one,
see its timeline, append events, and drive role-appropriate status
transitions — all through the UI — without the backend contract changing.

## Stack

- Vite 5 + React 18 + TypeScript (already in the repo).
- No component library yet — one small CSS file (`styles.css`) + inline
  attributes. Easy to swap later if the UI grows.
- No state library — `useState` / `useEffect` around a typed API module.

## Source layout

```
apps/web/src/
├── api.ts            # typed API client (single fetch surface)
├── identity.ts       # dev identity helpers (seeded list + localStorage)
├── App.tsx           # shell, list, detail, timeline, actions
├── main.tsx          # React entrypoint, imports styles.css
├── styles.css        # one CSS file (CSS variables; no build config)
└── vite-env.d.ts     # Vite ambient types
```

## `api.ts` — contract

- `API_URL` comes from `VITE_API_URL` (falls back to `http://localhost:8000`).
- Every function takes an `email: string`; the client sets
  `X-User-Email` on each request. When the backend moves to bearer
  mode, only this module changes.
- `ApiError(status, errorCode, reason)` — every non-2xx response is
  converted to this, so UI code can render the backend's
  `{error_code, reason}` envelope directly.
- Exposed functions (match the backend 1:1):
  - `getHealth()`
  - `getMe(email)`
  - `listEncounters(email, filters)`
  - `getEncounter(email, id)`
  - `getEncounterEvents(email, id)`
  - `createEncounterEvent(email, id, {event_type, event_data})`
  - `updateEncounterStatus(email, id, status)`
  - `listLocations(email)`
- Pure helpers used for UI affordances only:
  - `allowedNextStatuses(role, currentStatus)` — mirrors
    `authz.TRANSITION_ROLES`. Drives which transition buttons appear.
  - `canCreateEvent(role)` — drives the "Add event" composer.
  - **Backend remains the source of truth** — the UI never assumes the
    server will accept anything; any 4xx surfaces as a banner with the
    error code + reason.

## Dev identity

- `apps/web/src/identity.ts` ships the seeded demo users:
  - Org 1: `admin@`, `clin@`, `rev@chartnav.local`
  - Org 2: `admin@`, `clin@northside.local`
- Selector in the header lets operators switch caller without editing
  code. "Custom email…" lets a real/unseeded email be entered for
  testing 401 paths.
- Selection persists in `localStorage.chartnav.devIdentity`.

## UI layers

### Header
- Brand wordmark.
- Chip showing the resolved caller (`email · role · org N`) — or the
  auth error if `/me` failed.
- Chip with the current API base URL.
- Identity picker.

### Layout (two-column, collapses below 920px)
- **Encounter list (left)** — filter bar (`status`, `provider_name`,
  `location_id`) + row list with patient id, name, provider, and a
  color-coded status pill.
- **Detail pane (right)** — headline + status pill, facts grid
  (organization / location / scheduled / started / completed / created),
  allowed-transition buttons, timeline of events, and "Add event"
  composer when the current role is permitted to write.

### Role-aware actions
- Allowed transitions are shown as buttons. If none are available for
  the (role, current_status) pair, we show a note instead of fake
  disabled buttons.
- The "Add event" composer is hidden for reviewers (matches
  `CAN_CREATE_EVENT`). Reviewers still get a subtle note explaining why.
- After any successful action the UI refreshes: detail, events, and
  list.
- After a failure, the UI shows the exact `error_code` + `reason` from
  the backend in a top banner.

## UX states

| State          | Surface                                                  |
|----------------|----------------------------------------------------------|
| Loading        | "Loading…" in list / detail                              |
| Empty list     | "No encounters match these filters."                     |
| 401 / unknown  | Red chip in the header: `auth: 401 unknown_user — ...`   |
| 403 role       | Banner: `403 role_cannot_transition — ...`               |
| 404 cross-org  | Banner: `404 encounter_not_found — ...`                  |
| 400 bad status | Banner: `400 invalid_transition — ... allowed next ...`  |

## Local dev

```bash
# one terminal — backend
make install          # venv + pip install -e "apps/api[dev,postgres]"
make reset-db         # fresh SQLite + seed
make boot             # uvicorn on 8000

# second terminal — frontend
make web-install      # npm install
make web-dev          # vite on 5173

# or both at once (Ctrl-C to stop both)
make dev
```

`VITE_API_URL` in `apps/web/.env.example` defaults to
`http://localhost:8000`, matching `make boot`. Copy to `.env` if you
need to point at a different backend.

## Build / verification

```bash
make web-typecheck    # tsc --noEmit
make web-build        # vite build -> apps/web/dist
```

Verified manually on 2026-04-18:

| Check                                                    | Result |
|----------------------------------------------------------|--------|
| `tsc --noEmit`                                           | ✅     |
| `npm run build` emits dist/                              | ✅ (154 KB JS / 6 KB CSS) |
| `GET /me` for all 5 seeded users                         | ✅     |
| `GET /encounters` org-scoped (org1 → 2 rows; org2 → `[3]`)| ✅     |
| `GET /encounters?status=in_progress`                     | ✅ `['PT-1001']` |
| `GET /encounters/{id}/events` hydrated                   | ✅ 3 events  |
| Clinician in_progress → draft_ready                      | ✅ 200 |
| Clinician review_needed → completed (denied)             | ✅ 403 `role_cannot_transition` |
| Reviewer review_needed → completed                       | ✅ 200 |
| Reviewer POST event (denied)                             | ✅ 403 `role_cannot_create_event` |
| Admin POST event                                         | ✅ 201 |
| Switching identity re-fetches `/me` and list             | ✅     |

## Encounter creation (phase 8)

- Header shows `+ New encounter` for admin + clinician; hidden for reviewer.
- `CreateEncounterModal` fetches `/locations` (server-scoped to caller org), auto-selects when only one option exists, and submits `{ organization_id, location_id, patient_identifier, patient_name, provider_name, status }`.
- Required fields (`patient_identifier`, `provider_name`, `location_id`) block submit until filled.
- While in-flight the submit button disables and shows `Creating…`.
- On success the list refreshes, the new encounter auto-selects, and a green banner shows `#<id> created`.
- On failure the modal stays open and the exact `{error_code, reason}` appears inline, so reviewers can correct and retry.

## UX hardening (phase 8)

- Every mutating control (transition, append event, create) disables while its request is in flight and shows a pending label.
- Identity badge has explicit states (`identity-loading`, `identity-error`, `identity-badge`) so loading vs. failed vs. resolved are distinguishable.
- Banners use ARIA `role="alert" | "status"` and `data-testid` so assistive tech + tests can target them.
- When no transition is legal for the current `(role, status)` pair, we show a plain note — no fake-disabled buttons.

## Full-stack E2E (phase 9)

Playwright boots both backend (SQLite + seeded) and frontend together,
and runs 8 Chromium scenarios that exercise the real UI end-to-end —
identity resolution, scope switching, encounter create, event append,
role-aware transitions, reviewer restrictions, unknown-email auth
surface, filters. Details in `17-e2e-and-release.md`. Command:
`make e2e`.

## Admin governance (phase 12)

- **Admin button** in the header renders only when `isAdmin(role)`. Clinician / reviewer never see it.
- Opens `<AdminPanel />` — a modal with **Users** and **Locations** tabs.
  - Users: create form (email / full name / role), table with inline role change + deactivate/reactivate. Self-row is disabled so admins can't lock themselves out.
  - Locations: create form + inline rename (click-to-edit) + deactivate.
- Every mutating control disables in flight and surfaces backend `{error_code, reason}` in a per-tab banner on failure.
- The event composer's event_type is now a `<select>` wired to the backend allowlist (`EVENT_TYPES`), so the UI can't submit invalid types.
- Encounter list paginates 25 rows at a time via `listEncountersPage`, rendering Prev/Next + "N-M of T" when `total > 25`.

## Operator control plane (phase 13)

- Admin panel is now **4 tabs**: Users, Locations, **Organization**, **Audit log**.
- Organization tab: readonly `slug`, editable `name` + free-form `settings` JSON (16 KB cap enforced server-side). Local JSON parse errors surface before any PATCH is fired.
- Audit log tab: filter row (`event_type`, `actor_email`, free-text `q`), paginated table (25/page) ordered newest-first with timestamp / event / actor / method+path / error code / request id columns. Backend 4xx surfaces as banner.
- Users tab renders an "Invited" badge for active users with `invited_at` set.

## Invitations + bulk + audit export (phase 14)

- Users tab now has an **Invite** button per active non-self row; clicking it surfaces the raw token in a one-shot banner (never shown again, dismissible).
- Users tab also has a **Bulk import…** button that opens a CSV-style textarea dialog; the submit result renders an inline created/skipped/errors summary before closing.
- Organization tab replaced the raw JSON textarea with typed inputs for `name`, `default_provider_name`, `encounter_page_size`, `audit_page_size`, plus an **Extensions** JSON textarea for forward-compat drift.
- Audit log tab has an **Export CSV** button that fetches with the auth header and triggers a local download (must use fetch + blob — a raw `<a href>` can't send `X-User-Email`).
- New minimal **Invite accept** screen (`apps/web/src/InviteAccept.tsx`) mounted at `/invite?invite=<token>` and `/accept`. On success stores the email into `localStorage.chartnav.devIdentity` so the main app picks it up for header-mode dev use.

## Admin list scaling + feature flags + a11y (phase 15)

- Users + Locations tabs now have a **search input** + **Prev/Next pager** (25/page) + count header, powered by `listUsersPage` / `listLocationsPage` which read `X-Total-Count`/`X-Limit`/`X-Offset` headers and return `{items, total, limit, offset}`. Self-search on either tab resets `offset` to 0 so pagination never strands the user mid-query. Users tab also supports a `role` filter.
- `featureEnabled(org, flag)` is a new helper in `api.ts` — flags default to `true` when unset so untouched orgs keep full UI. `AdminPanel` loads `getOrganization(identity)` on mount and threads the org object into panes that gate UI. `feature_flags.audit_export=false` hides the **Export CSV** button on the Audit tab; `feature_flags.bulk_import=false` hides the **Bulk import…** button on the Users tab. Server is unchanged — this is a UX toggle, not a security control.
- `flash` in `AdminPanel` is now a stable `useCallback` — child panes that put it in a `refresh` dep array no longer hit an infinite refresh loop. (Regression landed while wiring feature-flag reloads; fix validated by Vitest + E2E.)
- Accessibility: event-type `<select>` in the encounter detail composer now carries `aria-label="Event type"`; inline role `<select>`s in the admin Users table carry `aria-label="Role for <email>"`. These were the only `serious`/`critical` axe findings — the suite is now clean.

## Platform mode awareness (phase 16)

- `api.ts` gains `getPlatform(email)` + `PlatformInfo` /
  `PlatformMode` / `SourceOfTruth` types + `platformModeLabel`
  helper.
- `AdminPanel` calls `/platform` on mount (alongside
  `/organization`) and renders a **platform banner** above the
  tabs: `Platform mode: <label> · <adapter display name>`. Visible
  on every admin view so the deployment's semantics are never
  implicit.
- Two Vitest scenarios (`src/test/AdminPanel.test.tsx`):
  - Standalone default renders "ChartNav native" adapter label.
  - Integrated read-through renders the stub adapter label +
    "Integrated — read-through" mode text.
- No UI changes for clinicians — the banner is admin-only, inside
  the admin modal.

## What this phase explicitly does NOT do

- No real login flow — `X-User-Email` is still dev transport.
- No global state manager (Redux/Zustand) — state lives in `App.tsx`.
- No UI component library.
- No pagination (the backend doesn't paginate yet).
- No optimistic updates — every mutation re-fetches the relevant slice.

Those are future phases. The API client + identity seam make them
cheap to add without rewriting.
