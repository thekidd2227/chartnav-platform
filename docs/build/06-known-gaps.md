# Known Gaps & Verification Matrix

## Verification evidence — phase 6

### Local `make verify` (SQLite)

| Step                                 | Result |
|--------------------------------------|--------|
| `rm -f apps/api/chartnav.db`         | ✅     |
| `alembic upgrade head`               | ✅     |
| `scripts_seed.py` (x2 idempotent)    | ✅     |
| `pytest tests/ -v`                   | ✅ **28/28** |
| `uvicorn` boots                      | ✅     |
| `scripts/smoke.sh` 9 assertions      | ✅     |
| teardown clean                       | ✅     |

### Local `make pg-verify` (Postgres 16)

| Step                                      | Result |
|-------------------------------------------|--------|
| throwaway `postgres:16-alpine` comes up   | ✅     |
| `alembic upgrade head` on Postgres        | ✅ both revisions applied |
| seed on Postgres (run twice, idempotent)  | ✅     |
| uvicorn boots against Postgres            | ✅     |
| `scripts/smoke.sh` 9 assertions           | ✅     |
| clinician status transition `in_progress → draft_ready` | ✅ |
| `workflow_events` row written with `old_status`/`new_status`/`changed_by` | ✅ |
| container torn down (trap)                | ✅     |

### Auth seam tests (`tests/test_auth_modes.py`)

| Case                                                               | Result |
|--------------------------------------------------------------------|--------|
| `CHARTNAV_AUTH_MODE=bearer` w/o JWT env → RuntimeError at import   | ✅     |
| bearer with JWT env, no token → 401 `missing_auth_header`          | ✅     |
| bearer with JWT env, token present → 501 `auth_bearer_not_implemented` | ✅  |
| header mode default → 200 + correct role/org                       | ✅     |

### Docker build
- `docker build -t chartnav-api:local apps/api` — runs locally.
- CI `docker-build` job builds with buildx and smokes the live
  container — enforced per PR.

## Real gaps (prioritized for next phase)

1. **JWT/SSO validation is still a stub.** Bearer mode rejects all traffic with 501. Next phase: PyJWT + JWKS fetch/cache, issuer/audience validation, claim → user mapping.
2. **pytest runs on SQLite only.** Postgres parity is asserted by `pg_verify.sh` + the `backend-postgres` CI job (which exercises the live surface). A pytest Postgres matrix is the next CI upgrade; `conftest.py` already reads env so this is mostly wiring.
3. **No image push / release pipeline.** CI builds the Docker image but doesn't publish it.
4. **Secrets are still plain env vars.** No AWS SM / Vault integration.
5. **No RBAC-gated writes for org metadata** (`/organizations` etc. remain read-only).
6. **`users.role` is still free VARCHAR** at DB level; no CHECK/lookup.
7. **No pagination / cursor** on `GET /encounters`.
8. **No encounter update / delete / cancel**; no `cancelled` status.
9. **Free-form `event_data`** — no per-event_type schema.
10. **CORS `allow_origins=["*"]`** still open.
11. **No distinct audit log** for auth/scoping failures.
12. **No rate limiting, no lockout, no structured logging.**
