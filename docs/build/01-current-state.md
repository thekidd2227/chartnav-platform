# ChartNav — Current State

**As of:** 2026-04-17 (phase: RBAC + full scoping + tests)

## Repo layout (relevant)

```
chartnav-platform/
├── apps/
│   ├── api/
│   │   ├── app/main.py
│   │   ├── app/auth.py              # authn only (header transport today)
│   │   ├── app/authz.py             # NEW — RBAC roles + dependencies
│   │   ├── app/api/routes.py        # all routes authed + scoped + role-gated
│   │   ├── alembic.ini
│   │   ├── alembic/env.py           # now honors `-x sqlalchemy.url=` for tests
│   │   ├── alembic/versions/        # 2 migrations (unchanged this phase)
│   │   ├── scripts_seed.py          # 2 orgs, 5 users across 3 roles
│   │   ├── tests/                   # NEW — pytest + TestClient
│   │   │   ├── conftest.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_scoping.py
│   │   │   └── test_rbac.py
│   │   └── pyproject.toml
│   └── web/
├── infra/docker/docker-compose.yml
└── docs/
    ├── build/                       # living docs
    ├── diagrams/                    # Mermaid sources
    └── final/                       # consolidated HTML/PDF
```

## Runtime baseline

- Python 3.11+, FastAPI, raw `sqlite3` driver.
- SQLite at `apps/api/chartnav.db` (gitignored).
- Alembic head: `a1b2c3d4e5f6` (no new migrations this phase).
- Auth transport: `X-User-Email` → `users` lookup (dev only).
- Auth seam: `app.auth.require_caller` with `CHARTNAV_AUTH_MODE` env flag for future JWT/SSO swap.
- Authorization: `app.authz` with `ROLE_ADMIN` / `ROLE_CLINICIAN` / `ROLE_REVIEWER`, role-gated dependencies for create/event/transition.
- Error envelope standardized: `{"detail": {"error_code": "...", "reason": "..."}}`.

## Verified working endpoints

### Open
- `GET /health`, `GET /`

### Authenticated (require `X-User-Email`)
- `GET /me`
- `GET /organizations` — scoped to caller's org (single row)
- `GET /locations` — scoped to caller's org
- `GET /users` — scoped to caller's org
- `GET /encounters` — scoped + filterable
- `GET /encounters/{id}` — 404 if cross-org
- `GET /encounters/{id}/events` — 404 if cross-org

### Authenticated + role-gated
- `POST /encounters` — admin or clinician (RBAC); body `organization_id` must match caller
- `POST /encounters/{id}/events` — admin or clinician
- `POST /encounters/{id}/status` — per-edge RBAC (see `07-auth-and-scoping.md`)

## Seeded tenants / users

| org_id | slug               | email                     | role      |
|--------|--------------------|---------------------------|-----------|
| 1      | `demo-eye-clinic`  | admin@chartnav.local      | admin     |
| 1      | `demo-eye-clinic`  | clin@chartnav.local       | clinician |
| 1      | `demo-eye-clinic`  | rev@chartnav.local        | reviewer  |
| 2      | `northside-retina` | admin@northside.local     | admin     |
| 2      | `northside-retina` | clin@northside.local      | clinician |
