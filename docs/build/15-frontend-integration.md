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

## What this phase explicitly does NOT do

- No real login flow — `X-User-Email` is still dev transport.
- No global state manager (Redux/Zustand) — state lives in `App.tsx`.
- No UI component library.
- No pagination (the backend doesn't paginate yet).
- No optimistic updates — every mutation re-fetches the relevant slice.

Those are future phases. The API client + identity seam make them
cheap to add without rewriting.
