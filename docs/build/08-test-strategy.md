# Test & Smoke Strategy

## Stack

- `pytest` + FastAPI `TestClient` for unit/integration.
- Per-test temporary SQLite (fresh migrate + seed per test).
- Shell-level smoke via `apps/api/scripts/smoke.sh` against a real
  running uvicorn.
- All of it runs in CI (`.github/workflows/ci.yml`).

## Layout

```
apps/api/tests/
├── conftest.py          # fixtures: test_db, client, seeded_ids, role headers
├── test_auth.py         # authn surface
├── test_scoping.py      # org scoping across every list/read endpoint
└── test_rbac.py         # role-gated writes + state transitions

apps/api/scripts/
└── smoke.sh             # curl-level live smoke (health, me, encounters, cross-org)
```

## Coverage matrix

### Auth (5)
Health open; `/me` missing/empty/unknown/valid.

### Scoping (8)
Orgs/locs/users scoped per tenant. `/organizations` 401 without auth.
Encounters disjoint across tenants. Cross-org GET → 404.
`?organization_id=<other>` → 403. Filters don't leak.

### RBAC (12)
Admin + clinician create encounter. Reviewer create → 403. Reviewer
event → 403. Clinician operational transition OK. Clinician review-
stage transition 403. Reviewer complete/kick-back OK. Cross-org mutate
→ 404. Invalid transition preserved as 400. `status_changed` carries
`old_status`/`new_status`/`changed_by`. Cross-org body mismatch → 403.

### Smoke (9)
Exercise live HTTP. Commands in `09-ci-and-deploy-hardening.md`.

## How to run

```bash
# just the pytest suite
cd apps/api && pytest tests/ -v

# everything (reset DB + pytest + boot + smoke)
make verify

# smoke only, against an already-running API
cd apps/api && bash scripts/smoke.sh http://127.0.0.1:8000
```

## Results at time of writing

- `pytest`: **25 passed in ~12s**
- `make verify`: all 9 smoke assertions pass after pytest succeeds

## Gaps not yet covered

- Concurrent writers / race conditions
- `event_data` schema per `event_type`
- Pagination (not yet implemented)
- Auth transport swap (needs its own harness when JWT/SSO lands)
- Long-running soak / memory behavior
