# ChartNav — Current State

**As of:** 2026-04-17 (phase: dev auth + org scoping)

## Repo layout (relevant)

```
chartnav-platform/
├── apps/
│   ├── api/
│   │   ├── app/main.py              # app factory, CORS, router mount
│   │   ├── app/auth.py              # NEW — dev auth + org-scoping helpers
│   │   ├── app/api/routes.py        # HTTP handlers, all encounter routes org-scoped
│   │   ├── alembic.ini
│   │   ├── alembic/env.py
│   │   ├── alembic/versions/        # 2 migrations (unchanged this phase)
│   │   ├── scripts_seed.py          # now seeds 2 orgs for scoping proof
│   │   └── pyproject.toml
│   └── web/                         # untouched this phase
├── infra/docker/docker-compose.yml
└── docs/
    ├── build/                       # living docs
    ├── diagrams/                    # Mermaid sources
    ├── final/                       # consolidated HTML/PDF (regenerated)
    └── releases/
```

## Runtime baseline

- Python 3.11+, FastAPI, raw `sqlite3` driver.
- SQLite at `apps/api/chartnav.db` (gitignored).
- Alembic head: `a1b2c3d4e5f6` (no new migrations this phase).
- CORS still wide-open (`*`) for local dev.
- Dev auth: every protected route reads `X-User-Email` and resolves the
  caller from the `users` table. See `07-auth-and-scoping.md`.

## Verified working endpoints

### Open (no auth)
- `GET /health`, `GET /`
- `GET /organizations`, `GET /locations`, `GET /users`
  — intentionally left open this phase; see known gaps.

### Authenticated (require `X-User-Email`)
- `GET /me` — NEW. Returns the resolved caller context.
- `GET /encounters` — caller's org only; rejects cross-org filter.
- `GET /encounters/{id}` — 404 if cross-org.
- `GET /encounters/{id}/events` — 404 if cross-org.
- `POST /encounters` — forces `organization_id` to caller's org; location must also belong.
- `POST /encounters/{id}/events` — 404 if cross-org.
- `POST /encounters/{id}/status` — 404 if cross-org; strict state machine still applies.

## Seeded tenants

| org_id | slug               | admin email                | encounters   |
|--------|--------------------|----------------------------|--------------|
| 1      | `demo-eye-clinic`  | `admin@chartnav.local`     | PT-1001, PT-1002 |
| 2      | `northside-retina` | `admin@northside.local`    | PT-2001      |
