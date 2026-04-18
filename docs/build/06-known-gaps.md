# Known Gaps & Verification Matrix

## Verification matrix — dev auth + org scoping phase

All checks executed against local `uvicorn` with a fresh seeded DB.

### Auth

| Case                                | Expected | Actual |
|-------------------------------------|----------|--------|
| `GET /me` no header                 | 401      | 401    |
| `GET /me` unknown email             | 401      | 401    |
| `GET /me` empty header              | 401      | 401    |
| `GET /me` org1 admin                | 200 + `organization_id=1` | 200 + `organization_id=1` |
| `GET /me` org2 admin                | 200 + `organization_id=2` | 200 + `organization_id=2` |

### Encounter listing

| Case                                                      | Expected | Actual |
|-----------------------------------------------------------|----------|--------|
| `GET /encounters` no auth                                 | 401      | 401    |
| Org1 `GET /encounters`                                    | `[1, 2]` | `[1, 2]` |
| Org2 `GET /encounters`                                    | `[3]`    | `[3]`  |
| Org1 `GET /encounters?organization_id=2` (cross-org lens) | 403      | 403    |
| Org1 `GET /encounters?organization_id=1` (own lens)       | `[1, 2]` | `[1, 2]` |

### Encounter read

| Case                                     | Expected | Actual |
|------------------------------------------|----------|--------|
| Org1 `GET /encounters/1`                 | 200      | 200    |
| Org1 `GET /encounters/3` (other org)     | 404      | 404    |
| Org2 `GET /encounters/3`                 | 200      | 200    |
| Org2 `GET /encounters/1` (other org)     | 404      | 404    |
| Org1 `GET /encounters/1/events`          | 200      | 200    |
| Org1 `GET /encounters/3/events` (cross)  | 404      | 404    |

### Encounter create

| Case                                                       | Expected | Actual |
|------------------------------------------------------------|----------|--------|
| Org1 POST own-org body                                     | 201      | 201    |
| Org1 POST body `organization_id=2` (cross)                 | 403      | 403    |
| Org1 POST own org but `location_id` belongs to other org   | 403      | 403    |

### Encounter mutate

| Case                                                    | Expected | Actual |
|---------------------------------------------------------|----------|--------|
| Org1 POST `/encounters/1/events` (own)                  | 201      | 201    |
| Org1 POST `/encounters/3/events` (cross)                | 404      | 404    |
| Org1 POST `/encounters/1/status` `draft_ready` (valid)  | 200      | 200    |
| Org2 POST `/encounters/1/status` (cross)                | 404      | 404    |
| Org1 POST `/encounters/1/status` `completed` (invalid transition) | 400 | 400 |

## Real gaps (prioritized for next phase)

1. **Dev-only auth** — `X-User-Email` is trivially spoofable. Must graduate to JWT or an identity provider before any hosted deployment. The abstraction point (`require_caller`) is already in place.
2. **No role-based authorization** — every seeded user is `admin`. Need `role`-gated actions (clinician vs. admin vs. reviewer) for the state machine edges.
3. **`/organizations`, `/locations`, `/users` still unscoped** — left open intentionally this phase. Next auth phase should either scope them to caller org or gate by role.
4. **No pagination / cursor** on `GET /encounters`.
5. **No encounter update / delete / cancel** path; no `cancelled` status.
6. **No automated tests** — verification is still manual curl; need pytest + httpx `TestClient` covering auth, scoping, state machine, filters.
7. **No ORM / sessions** — raw `sqlite3` with per-request connections. Works for SQLite; Postgres parity untested.
8. **CORS `allow_origins=["*"]`** — must tighten before any hosted deploy.
9. **No audit log distinct from workflow_events** — auth failures, scoping violations are not persisted.
10. **No rate limiting**.
