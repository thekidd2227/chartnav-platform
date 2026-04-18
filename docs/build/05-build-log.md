# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 6: production seam + deploy target + Postgres parity

### Step 1 — Baseline
- Starting head: `cfa8ca9` (CI + runtime hardening).

### Step 2 — Runtime config module
- New `apps/api/app/config.py`. All env reads centralized into
  `settings = _load()`. Validates `CHARTNAV_AUTH_MODE` and demands the
  three `CHARTNAV_JWT_*` vars if mode is `bearer` — otherwise raises at
  import time. No module besides `app.config` touches `os.environ`.
- New `apps/api/.env.example` with the full documented contract.

### Step 3 — DB layer (SQLAlchemy Core, cross-dialect)
- New `apps/api/app/db.py` — `engine`, `transaction()`, `fetch_all`,
  `fetch_one`, `insert_returning_id`. SQLite connect-args and PRAGMA
  FK enforcement handled automatically.
- Refactored `apps/api/app/api/routes.py`: every query now uses named
  (`:name`) bind parameters and `transaction()` for writes. The old
  `sqlite3`-specific `lastrowid` is gone.
- Refactored `apps/api/scripts_seed.py` to the same shape. Swapped
  `IFNULL` → `COALESCE`. Timestamp columns still use server-side
  `CURRENT_TIMESTAMP` for dialect-agnostic behavior.
- `apps/api/app/auth.py` now reads users via `db.fetch_one`; no more
  direct sqlite3 use.
- `apps/api/alembic/env.py` now also honors `DATABASE_URL` from env
  (already honored `-x sqlalchemy.url=`), so Alembic works uniformly in
  CI and the deploy entrypoint.

### Step 4 — Auth seam hardening
- Split resolvers: `resolve_caller_from_header` (dev) and
  `resolve_caller_from_bearer` (prod-shaped placeholder). `require_caller`
  dispatches via `settings.auth_mode`.
- Bearer mode returns **501** `auth_bearer_not_implemented` when a
  token is actually presented. That's deliberate — it's better to fail
  loudly than pretend half-auth.
- Added `apps/api/tests/test_auth_modes.py` (3 tests) asserting:
  - bearer-mode without JWT env → `RuntimeError` at `import app.config`
  - bearer-mode with JWT env but a token → 501
  - bearer-mode without a token → 401 `missing_auth_header`
  - header-mode (default) still returns correct caller

### Step 5 — Deploy target
- `apps/api/Dockerfile` rewritten: non-root user, `curl`-based
  HEALTHCHECK, `entrypoint.sh`, installs the `[postgres]` extra.
- `apps/api/entrypoint.sh` NEW: asserts `DATABASE_URL`, runs
  `alembic upgrade head`, optionally runs seed when
  `CHARTNAV_RUN_SEED=1`, then `exec`s uvicorn.
- `infra/docker/docker-compose.prod.yml` NEW: API + Postgres with a
  healthcheck dependency gate and env-driven defaults.

### Step 6 — Postgres parity
- `apps/api/pyproject.toml` gains a `[postgres]` extra pinning
  `psycopg[binary]>=3.2`.
- `scripts/pg_verify.sh` NEW: throwaway `postgres:16-alpine` container
  → migrate → seed twice (idempotency) → boot API → run the shared
  smoke script → live status transition → confirm `workflow_events`
  row was written. Traps cleanup on any exit.
- Local run: **PASS** on 2026-04-18.

### Step 7 — CI expansion
- `.github/workflows/ci.yml` now has four jobs:
  - `backend-sqlite` — existing pytest + SQLite smoke (unchanged contract).
  - `backend-postgres` — service-container Postgres, alembic upgrade,
    seed twice, boot, smoke, live status transition.
  - `docker-build` — buildx build of the API image, run it with
    SQLite + `CHARTNAV_RUN_SEED=1`, smoke the live container.
  - `docs` — regenerate HTML + PDF, upload as artifact.
- `docker-build` and `docs` both `needs: backend-sqlite`;
  `backend-postgres` also `needs: backend-sqlite`.

### Step 8 — Makefile + tooling
- New targets: `pg-verify`, `docker-build`, `docker-up`, `docker-down`.
- `verify.sh` already tolerant of missing `.venv/bin/uvicorn` (falls
  back to PATH) so both local and CI paths work.

### Step 9 — Tests updated
- `apps/api/tests/conftest.py` now sets `DATABASE_URL` via monkeypatch
  per test and flushes cached `app.*` modules so `settings` re-reads
  env cleanly. Works identically for SQLite (today) and Postgres (a
  matrix we'll flip when ready).
- pytest suite: **28 passed** locally and in `backend-sqlite`.

### Step 10 — Docs
- New: `11-production-auth-seam.md`, `12-runtime-config.md`,
  `13-deploy-target.md`, `14-postgres-parity.md`.
- Updated: `01-current-state.md`, `05-build-log.md`, `06-known-gaps.md`,
  `07-auth-and-scoping.md`, `08-test-strategy.md`,
  `09-ci-and-deploy-hardening.md`. Diagrams refreshed
  (`system-architecture`, `api-data-flow`).
- `scripts/build_docs.py` now picks up `11…14` automatically.
- Final HTML + PDF regenerated.

### Step 11 — Hygiene
- Dev DB reset to seeded state before commit.
- `.gitignore` already excludes `.pytest_cache`, `__pycache__`, `*.db`.

---

## Prior phases

- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
