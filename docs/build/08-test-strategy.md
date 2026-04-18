# Test Strategy

## Stack

- `pytest` + FastAPI `TestClient` (httpx under the hood).
- Per-test temporary SQLite file: each test gets a fresh migrated +
  seeded DB so writes from one test cannot leak into another.
- No external services; tests run offline in under ~15 seconds.

## Layout

```
apps/api/tests/
├── conftest.py          # fixtures: test_db, client, seeded_ids, role headers
├── test_auth.py         # authn surface
├── test_scoping.py      # org scoping across every list/read endpoint
└── test_rbac.py         # role-gated writes + state transitions
```

## Coverage matrix

### Auth (`test_auth.py`)
- `/health` open.
- `/me` without header → 401 `missing_auth_header`.
- `/me` with empty header → 401.
- `/me` with unknown email → 401 `unknown_user`.
- `/me` with seeded admin → 200 + correct `organization_id` + role.

### Scoping (`test_scoping.py`)
- `/organizations` returns only caller org row (for both orgs).
- `/organizations` without auth → 401.
- `/locations` scoped to caller org.
- `/users` scoped to caller org (no cross-tenant leakage).
- `/encounters` returns disjoint sets for org1 vs org2.
- Cross-org `GET /encounters/{id}` → 404.
- `?organization_id=2` as org1 caller → 403.
- Filters (`status=`) work inside caller org and don't leak.

### RBAC (`test_rbac.py`)
- Admin can create encounter (201).
- Clinician can create encounter (201).
- Reviewer cannot create encounter (403 `role_cannot_create_encounter`).
- Reviewer cannot add events (403 `role_cannot_create_event`).
- Clinician can perform `in_progress → draft_ready`.
- Clinician cannot perform `review_needed → completed` (403 `role_cannot_transition`).
- Reviewer can complete a review (`review_needed → completed`).
- Reviewer can kick back (`review_needed → draft_ready`).
- Cross-org mutate → 404 (existence not leaked).
- Invalid transition still → 400 `invalid_transition`.
- Successful status change writes a `status_changed` event with `old_status`/`new_status`/`changed_by`.
- Cross-org body mismatch on `POST /encounters` → 403 `cross_org_access_forbidden`.

## How to run

From `apps/api/` with the venv active:

```bash
pytest tests/ -v
```

Result at time of writing: **25 passed in ~12s**.

## Guarantees we get from this suite

- Any regression that breaks auth, scoping, or a role gate surfaces in CI (when we add it).
- The error-code envelope is asserted against, so rename-by-accident is caught.
- Seed idempotency isn't tested directly here but is still exercised
  indirectly: each test reseeds cleanly without collision.

## Gaps not yet covered

- Concurrent writers / race conditions.
- Event JSON schema per `event_type`.
- Pagination behavior (not yet implemented).
- Auth transport swap (would warrant its own harness).
