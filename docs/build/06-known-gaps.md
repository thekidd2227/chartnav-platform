# Known Gaps & Verification Matrix

## Verification evidence — phase 5

### Automated pytest (unchanged contract, now in CI)
```
$ cd apps/api && pytest tests/ -v
... 25 passed in ~12s
```

### `make verify` (canonical local gate)
Steps executed in order:

| Step                                            | Result |
|-------------------------------------------------|--------|
| `rm -f apps/api/chartnav.db`                    | ✅     |
| `alembic upgrade head`                          | ✅     |
| `scripts_seed.py`                               | ✅ (idempotent)|
| `pytest tests/ -v`                              | ✅ (25/25) |
| `uvicorn app.main:app --port 8765` boots        | ✅     |
| `/health` reachable within 10s                  | ✅     |
| `scripts/smoke.sh` all 9 assertions             | ✅     |
| boot process torn down cleanly                  | ✅     |

### Smoke assertions (`scripts/smoke.sh`)

| Assertion                                                          | Result |
|--------------------------------------------------------------------|--------|
| `GET /health` → 200, body `status=ok`                              | ✅     |
| `GET /me` without auth → 401                                       | ✅     |
| `GET /me` with admin1 → 200, `role=admin`, `organization_id=1`     | ✅     |
| `GET /encounters` without auth → 401                               | ✅     |
| `GET /encounters` with admin1 → 200                                | ✅     |
| `GET /encounters?organization_id=2` as org1 admin → 403             | ✅     |
| `GET /encounters/1` as admin1 → 200                                | ✅     |
| `GET /encounters/3` as admin1 (cross-org) → 404                    | ✅     |

### Doc pipeline
- `python scripts/build_docs.py` → wrote 59KB HTML + 1.1MB PDF via headless Chrome.
- Both artifacts regenerate deterministically from `docs/build/` + `docs/diagrams/`.

### CI YAML sanity
- YAML parses cleanly (verified by PyYAML load).
- Limitation: no `act` binary available to run the workflow locally; CI behavior is asserted by parity with `make verify` and by the structural review of the YAML.

## Real gaps (prioritized for next phase)

1. **Auth transport still dev-only.** `X-User-Email` spoofable. Swap via `CHARTNAV_AUTH_MODE` + JWT/SSO.
2. **No `act` or local workflow runner** — YAML syntactic parse only. Add `act` or accept first-push feedback loop.
3. **No RBAC-gated write endpoints for org metadata.** `/organizations`, `/locations`, `/users` are read-only.
4. **`users.role` free VARCHAR at the DB level** — no CHECK constraint; enforced at app layer only.
5. **No pagination / cursor** on `GET /encounters`.
6. **No encounter update / delete / cancel**; no `cancelled` status.
7. **Free-form `event_data`** — no per-event_type schema.
8. **Raw `sqlite3`** per-request connections; Postgres parity (docker compose) untested.
9. **CORS `allow_origins=["*"]`** remains.
10. **No distinct audit log** for auth/scoping failures (only successful workflow events).
11. **No rate limiting, no lockout, no structured logging.**
12. **No deploy target** — CI builds + tests but does not ship anything.
