# ChartNav — Current State

**As of:** 2026-04-18 (phase: production seam, deploy target, Postgres parity)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/ci.yml         # backend-sqlite + backend-postgres + docker-build + docs
├── Makefile                         # install · migrate · seed · test · verify · pg-verify · docker-*
├── scripts/
│   ├── build_docs.py                # reproducible HTML/PDF build
│   ├── verify.sh                    # boot + smoke teardown
│   └── pg_verify.sh                 # NEW — end-to-end Postgres parity proof
├── apps/
│   ├── api/
│   │   ├── Dockerfile               # hardened: non-root, healthcheck, entrypoint
│   │   ├── entrypoint.sh            # NEW — migrate-on-start, optional seed, exec CMD
│   │   ├── .env.example             # runtime contract (env-first)
│   │   ├── app/main.py
│   │   ├── app/config.py            # NEW — central settings from env
│   │   ├── app/db.py                # NEW — SA Core, cross-dialect
│   │   ├── app/auth.py              # header + bearer resolvers behind one seam
│   │   ├── app/authz.py             # RBAC
│   │   ├── app/api/routes.py        # all queries now :name-bound
│   │   ├── alembic.ini
│   │   ├── alembic/env.py           # honors `-x` AND `DATABASE_URL`
│   │   ├── alembic/versions/        # 2 migrations (unchanged)
│   │   ├── scripts_seed.py          # rewritten on SA; cross-dialect
│   │   ├── scripts/smoke.sh         # shell smoke (reused across envs)
│   │   └── tests/
│   │       ├── conftest.py          # env-based per-test DB
│   │       ├── test_auth.py
│   │       ├── test_auth_modes.py   # NEW — header + bearer seam
│   │       ├── test_rbac.py
│   │       └── test_scoping.py
│   └── web/
├── infra/docker/
│   ├── docker-compose.yml           # dev stack
│   └── docker-compose.prod.yml      # NEW — API + Postgres
└── docs/
    ├── build/ 01 … 14
    ├── diagrams/
    └── final/*.html / *.pdf
```

## Runtime baseline

- Python 3.11+, FastAPI, **SQLAlchemy Core** now underpins all DB access.
- Database: `DATABASE_URL` → `sqlite:///apps/api/chartnav.db` (dev default) or `postgresql+psycopg://…` (prod / parity CI).
- Alembic head: `a1b2c3d4e5f6`. No new migrations this phase.
- Auth: `CHARTNAV_AUTH_MODE` (`header` dev / `bearer` prod-shaped placeholder). Config refuses to import if `bearer` is set without JWT env.
- RBAC: `admin` / `clinician` / `reviewer`.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- Deploy target: Docker image + `docker-compose.prod.yml` (API + Postgres).
- Tests: 28 pytest on SQLite (incl. 3 new auth-mode tests); Postgres parity proved end-to-end via `scripts/pg_verify.sh` and a dedicated CI job.

## Verified working endpoints

Unchanged since phase 4. Now verified on BOTH SQLite and Postgres where applicable:

- Open: `GET /health`, `GET /`
- Authed: `GET /me`, `GET /organizations`, `GET /locations`, `GET /users`, `GET /encounters` (+ filters), `GET /encounters/{id}`, `GET /encounters/{id}/events`
- Authed + RBAC: `POST /encounters` (admin, clinician), `POST /encounters/{id}/events` (admin, clinician), `POST /encounters/{id}/status` (per-edge roles)

## Automation

- `make verify` — SQLite: reset-db + pytest (28) + boot + smoke (9) + teardown.
- `make pg-verify` — spins throwaway Postgres, migrates + seeds + boots + smokes + exercises state transition. Teardown trap-guaranteed.
- `make docker-build` / `make docker-up` / `make docker-down`.
- `python scripts/build_docs.py` — deterministic HTML + PDF.
- CI: `backend-sqlite` → `backend-postgres` + `docker-build` + `docs` (each gated on its predecessor where it matters).
