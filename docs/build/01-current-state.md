# ChartNav — Current State

**As of:** 2026-04-17 (phase: CI + runtime hardening)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/
│   └── ci.yml                       # NEW — backend + docs CI
├── Makefile                         # NEW — canonical local verification
├── scripts/
│   └── build_docs.py                # NEW — reproducible HTML/PDF builder
├── apps/
│   ├── api/
│   │   ├── app/main.py
│   │   ├── app/auth.py
│   │   ├── app/authz.py
│   │   ├── app/api/routes.py
│   │   ├── alembic.ini
│   │   ├── alembic/env.py           # honors `-x sqlalchemy.url=`
│   │   ├── alembic/versions/        # 2 migrations (unchanged)
│   │   ├── scripts_seed.py          # 2 orgs, 5 users, 3 roles
│   │   ├── scripts/smoke.sh         # NEW — curl-level smoke
│   │   ├── tests/                   # pytest suite
│   │   └── pyproject.toml           # now declares [dev] extras + pytest config
│   └── web/
├── infra/docker/docker-compose.yml
└── docs/
    ├── build/                       # living docs 01–10
    ├── diagrams/                    # Mermaid sources
    └── final/                       # generated HTML + PDF
```

## Runtime baseline

- Python 3.11+, FastAPI, raw `sqlite3` driver.
- SQLite at `apps/api/chartnav.db` (gitignored). CI uses `$RUNNER_TEMP/chartnav_ci.db`.
- Alembic head: `a1b2c3d4e5f6` (no new migrations this phase).
- Auth transport: `X-User-Email` (dev). Seam: `CHARTNAV_AUTH_MODE`.
- RBAC roles: `admin`, `clinician`, `reviewer`.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- Every endpoint except `/health` and `/` requires auth. All data endpoints are caller-org scoped.

## Verified working endpoints

Unchanged since phase 4:
- `GET /health`, `GET /` (open)
- `GET /me`
- `GET /organizations`, `GET /locations`, `GET /users` (authed + scoped)
- `GET /encounters` (+ filters)
- `GET /encounters/{id}`, `GET /encounters/{id}/events`
- `POST /encounters` (admin, clinician)
- `POST /encounters/{id}/events` (admin, clinician)
- `POST /encounters/{id}/status` (per-edge RBAC)

## Automation now in place

- `make verify` — single command: reset DB, test, boot, smoke.
- `pytest tests/ -v` — 25 tests pass.
- `bash apps/api/scripts/smoke.sh <base>` — 9 curl assertions.
- `python scripts/build_docs.py` — regenerates consolidated HTML + PDF.
- `.github/workflows/ci.yml` — runs all of the above on push/PR + uploads rebuilt docs as a CI artifact.

## Seeded tenants / users

| org_id | slug               | email                    | role      |
|--------|--------------------|--------------------------|-----------|
| 1      | `demo-eye-clinic`  | admin@chartnav.local     | admin     |
| 1      | `demo-eye-clinic`  | clin@chartnav.local      | clinician |
| 1      | `demo-eye-clinic`  | rev@chartnav.local       | reviewer  |
| 2      | `northside-retina` | admin@northside.local    | admin     |
| 2      | `northside-retina` | clin@northside.local     | clinician |
