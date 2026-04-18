# Known Gaps & Verification Matrix

## Verification evidence — phase 7 (frontend)

### Backend still green
- `make verify` (SQLite): **28/28 pytest** + 9/9 smoke + clean teardown.
- No backend code changed this phase. All previous verification stands.

### Frontend build + typecheck
```
$ cd apps/web && npx tsc --noEmit   # clean
$ npm run build
✓ 33 modules transformed.
dist/index.html                   0.40 kB │ gzip:  0.27 kB
dist/assets/index-*.css           6.24 kB │ gzip:  1.79 kB
dist/assets/index-*.js          154.44 kB │ gzip: 49.66 kB
✓ built in 639ms
```

### Live integration (uvicorn + curl as a UI stand-in)

| Flow the UI depends on                                        | Result |
|---------------------------------------------------------------|--------|
| `GET /me` for all 5 seeded identities                         | ✅ 200 |
| `GET /me` unknown / empty                                     | ✅ 401 (UI shows red chip) |
| `GET /encounters` org1 vs org2 scoping                        | ✅ disjoint |
| `GET /encounters?status=in_progress` filter                   | ✅ `['PT-1001']` |
| `GET /encounters/{id}` + `GET /encounters/{id}/events`        | ✅ 200, 3 events |
| Clinician `in_progress → draft_ready`                         | ✅ 200 |
| Clinician `review_needed → completed`                         | ✅ 403 `role_cannot_transition` |
| Reviewer `review_needed → completed`                          | ✅ 200 |
| Reviewer `POST /encounters/{id}/events`                       | ✅ 403 `role_cannot_create_event` |
| Admin `POST /encounters/{id}/events`                          | ✅ 201 |

### UI affordances sanity

| Role      | Transition buttons shown                                         | Event composer |
|-----------|------------------------------------------------------------------|----------------|
| admin     | Any forward or rework edge valid from the current state          | visible        |
| clinician | `scheduled→in_progress`, `in_progress→draft_ready`, rework back  | visible        |
| reviewer  | `draft_ready→review_needed`, `review_needed→{completed,draft_ready}` | hidden w/ note |

When no transition is available (terminal `completed` or role mismatch),
the UI shows a note rather than fake-disabled buttons. Backend remains
authoritative — a mismatch between the UI's `allowedNextStatuses` and
the server is surfaced as a 4xx banner with the exact `error_code`.

## Real gaps (prioritized for next phase)

1. **No automated frontend tests.** All frontend verification this phase is build/typecheck + live-curl parity. Next: a small Vitest or Playwright pass.
2. **JWT validation still stubbed.** Bearer mode returns 501; the frontend currently only implements header mode.
3. **No encounter creation UI.** The frontend can add events and move statuses but cannot create encounters yet (backend endpoint exists).
4. **No pagination.** Works fine at seed scale; first real dataset will need it on both ends.
5. **No optimistic updates.** Every mutation re-fetches.
6. **No global state manager.** Fine at this size; watch for prop-drill as flows multiply.
7. **No encounter update / delete / cancel.** No `cancelled` status.
8. **Free-form `event_data`** still lacks per-event_type schema.
9. **Raw `sqlite3` → SA Core refactor complete** — pytest matrix against Postgres is the next CI upgrade.
10. **CORS `allow_origins=["*"]`** remains.
11. **No distinct audit log** for auth/scoping failures.
12. **No rate limiting, lockout, or structured logging.**
13. **No CI job for the frontend.** The `docker-build` + `docs` jobs don't cover the web bundle. A `frontend-build` CI job is a small, honest addition.
