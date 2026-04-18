# Known Gaps

## Verification matrix (proof this phase shipped)

### Filter matrix — `GET /encounters?...`

| Query                                              | Expected ids | Actual |
|----------------------------------------------------|--------------|--------|
| `status=in_progress`                               | `[1]`        | `[1]`  |
| `status=review_needed`                             | `[2]`        | `[2]`  |
| `provider_name=Dr. Patel`                          | `[2]`        | `[2]`  |
| `organization_id=1&location_id=1&status=in_progress` | `[1]`      | `[1]`  |
| `organization_id=999`                              | `[]`         | `[]`   |
| `status=bogus`                                     | 400          | 400    |

### State machine matrix — `POST /encounters/{id}/status`

| Encounter | From            | To              | Expected | Actual |
|-----------|-----------------|-----------------|----------|--------|
| 1         | in_progress     | draft_ready     | 200      | 200    |
| 1         | draft_ready     | in_progress     | 200      | 200    |
| 1         | in_progress     | completed       | 400      | 400    |
| 1         | in_progress     | scheduled       | 400      | 400    |
| 2         | review_needed   | completed       | 200      | 200    |
| 2         | completed       | in_progress     | 400      | 400    |
| 1         | in_progress     | `"whatever"`    | 400      | 400    |

## Real gaps (prioritized)

1. **No ORM / no sessions** — routes still use raw `sqlite3` with per-request connections. Works for single-file SQLite; will not scale cleanly to Postgres or multi-writer.
2. **No auth / no tenant scoping** — any caller sees any org's data. Needs `organization_id` derived from authenticated identity, not client input.
3. **No pagination** — `GET /encounters` returns all matching rows. Needs `limit`, `cursor`, and a stable order.
4. **No update / delete paths** — encounters cannot be edited (patient name typo) or cancelled. Need `PATCH /encounters/{id}` and a `cancelled` status (or soft-delete).
5. **No automated tests** — verification is manual curl matrices. Need pytest + httpx `TestClient` covering state machine + filters.
6. **Free-form `event_data`** — no per-event_type schema validation.
7. **SQLite-only** — Alembic constructs are SQLite-compatible but Postgres parity hasn't been exercised (docker compose has a Postgres intent but api still points at SQLite).
8. **Frontend not wired** — `apps/web` does not yet consume `/encounters`.
9. **CORS wide-open** (`allow_origins=["*"]`) — fine for dev, must be tightened before any hosted deploy.
10. **No request IDs / structured logging** — hard to trace a specific 400 in a busy log.
