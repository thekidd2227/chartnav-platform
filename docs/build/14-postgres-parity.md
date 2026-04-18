# Postgres Parity

## Why this phase

The app was born on SQLite. This phase proves the same code runs on
Postgres — migrations, seed, auth, scoping, RBAC, state machine.

## Code-level changes that made this possible

The DB layer was rewritten to use **SQLAlchemy Core** (`apps/api/app/db.py`).
That single switch buys cross-dialect behavior:

- All SQL uses **named** bind parameters (`:name`). No more `?`.
- Portable functions only — `COALESCE` replaced `IFNULL`; `CURRENT_TIMESTAMP` already worked on both.
- `insert_returning_id(conn, table, values)` helper encapsulates the
  dialect split: `RETURNING id` on Postgres, `cursor.lastrowid` on
  SQLite. Callers never touch either.
- `transaction()` context manager gives a SA connection with `begin()`
  semantics on either backend.

Consumers changed:
- `apps/api/app/api/routes.py` — all queries now use `:name` binds
  and `transaction()`.
- `apps/api/scripts_seed.py` — rewritten to `transaction()` +
  `insert_returning_id`, no more raw `sqlite3`.
- `apps/api/app/auth.py` — uses `fetch_one` from the new `db` module.
- `apps/api/alembic/env.py` — honors both `-x sqlalchemy.url=` and
  `DATABASE_URL` env, so migrations can run against either backend.

No existing migration (`43ccbf363a8f`, `a1b2c3d4e5f6`) needed changes.
They already used SQLAlchemy constructs and portable defaults.

## Proof — `scripts/pg_verify.sh`

Single reproducible command. Launches `postgres:16-alpine` in a
throwaway container, runs migrations + seed, boots the API against it,
runs the full smoke, then does a live **status transition** + reads
the resulting `workflow_events` row back.

Local run on 2026-04-18:

```
==> alembic upgrade head on Postgres
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Running upgrade  -> 43ccbf363a8f, create initial chartnav tables
INFO  [alembic.runtime.migration] Running upgrade 43ccbf363a8f -> a1b2c3d4e5f6, add encounters and workflow_events

==> seed (idempotent, run twice)
Seed complete.
  demo-eye-clinic: organization_id=1 location_id=1
  northside-retina: organization_id=2 location_id=2

==> smoke: http://127.0.0.1:8766
  ok  /health 200
  ok  /health body.status=ok
  ok  /me 401 without auth
  ok  /me 200 role=admin org=1
  ok  /encounters 401 without auth
  ok  /encounters 200 admin1
  ok  /encounters?organization_id=2 (cross-org) -> 403
  ok  GET /encounters/1 as admin1 -> 200
  ok  GET /encounters/3 cross-org -> 404
==> all smoke checks passed
==> extra: status transition on Postgres
  ok  PT-1001 in_progress -> draft_ready (clinician)
  ok  workflow_events row recorded on Postgres
==> Postgres parity: PASS
```

## CI coverage

`.github/workflows/ci.yml` → `backend-postgres` job:

1. Spins up a `postgres:16-alpine` service container on port 5432.
2. Installs the API with the `[postgres]` extra.
3. `alembic upgrade head` (direct env `DATABASE_URL=postgresql+psycopg://…`).
4. Seeds twice (idempotency proof).
5. Boots uvicorn, waits for `/health`.
6. Runs `scripts/smoke.sh`.
7. Executes the same `clinician → draft_ready` status transition and
   asserts the returned row.

If any step fails, the job fails and nothing merges.

## What's covered / not covered

| Surface                          | Verified on Postgres |
|----------------------------------|:--------------------:|
| Schema migrations                | ✅                   |
| Idempotent seed                  | ✅                   |
| App boot                         | ✅                   |
| `/health`, `/me`                 | ✅                   |
| `/encounters` (list + filters + cross-org 403) | ✅         |
| `/encounters/{id}` 200 / 404 cross-org | ✅             |
| State transition write + event emit    | ✅             |
| pytest suite (28 tests)          | Runs on SQLite only today — see Known Gaps. |

The pytest suite still targets SQLite because the TestClient fixture
uses `tmp_path` file DBs. Migrating that to a Postgres matrix is the
obvious next CI upgrade; the DB layer is ready for it.
