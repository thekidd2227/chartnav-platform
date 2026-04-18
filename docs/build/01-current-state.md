# ChartNav — Current State

**As of:** 2026-04-18 (phase: admin governance + event discipline + pagination)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/
│   ├── ci.yml            # backend-sqlite · backend-postgres · frontend · e2e · docker-build · deploy-config · docs
│   └── release.yml
├── Makefile              # staging-up/verify/rollback · web-* · e2e · release-build · dev
├── scripts/              # build_docs.py · verify.sh · pg_verify.sh · release_build.sh · staging_*.sh
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py · config.py · db.py · auth.py · authz.py
│   │   │   ├── audit.py · logging_config.py · middleware.py · metrics.py
│   │   │   └── api/routes.py    # + admin CRUD, event schemas, pagination
│   │   ├── alembic/versions/    # 4 migrations through c3d4e5f6a7b8
│   │   ├── scripts_seed.py
│   │   ├── scripts/smoke.sh
│   │   ├── tests/               # 91 pytest (+20 admin, +3 observability)
│   │   └── Dockerfile · entrypoint.sh · .env.example
│   └── web/
│       ├── package.json · playwright.config.ts · vite.config.ts · tsconfig.json
│       ├── src/
│       │   ├── App.tsx          # + Admin button, pagination, event-type dropdown
│       │   ├── AdminPanel.tsx   # NEW — users + locations tabs
│       │   ├── api.ts           # + admin methods + listEncountersPage
│       │   ├── identity.ts · styles.css · main.tsx
│       │   └── test/            # 18 Vitest (+6 admin, +1 app)
│       └── tests/e2e/           # 10 Playwright (+2 admin)
├── infra/docker/{docker-compose,docker-compose.prod,docker-compose.staging}.yml
└── docs/build/ 01 … 22
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `header` (dev) or `bearer` (prod JWT via JWKS).
- RBAC: `admin` / `clinician` / `reviewer`. Enforced at **app level AND DB level** via CHECK constraint (migration `c3d4e5f6a7b8`).
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- **Admin governance**: `POST/PATCH/DELETE /users` + `POST/PATCH/DELETE /locations` (admin only, org-scoped, soft-delete via `is_active`).
- **Event discipline**: `EVENT_SCHEMAS` allowlist with per-type required keys; invalid `event_type` or `event_data` → 400.
- **Pagination**: `GET /encounters?limit=&offset=` + `X-Total-Count`/`X-Limit`/`X-Offset` headers.
- Observability: `/health` · `/ready` · `/metrics` (Prometheus text).
- Audit trail: `security_audit_events` table.
- CORS + rate-limit + request-id + structured logs: unchanged.
- Alembic head: `c3d4e5f6a7b8`.

## Testing layers

| Layer        | Tool         | Count | Scope                                                                  |
|--------------|--------------|:-----:|------------------------------------------------------------------------|
| pytest       | pytest       |  91   | backend (auth, RBAC, scoping, state machine, JWT, operational, observability, admin/governance/events/pagination) |
| shell smoke  | smoke.sh     |   9   | live HTTP contract (SQLite + Postgres)                                 |
| vitest       | vitest       |  18   | frontend integration (mocked API, incl. AdminPanel)                    |
| Playwright   | @playwright  |  10   | full-stack browser (incl. admin create-user/location, non-admin denial) |
| staging      | staging_verify.sh | 9 | live staging stack                                                    |

## Verified working endpoints

### Open
- `GET /health`, `GET /`
- `GET /ready`, `GET /metrics`

### Authenticated (any role)
- `GET /me`
- `GET /organizations`, `GET /locations`, `GET /users` (+ `?include_inactive=1`)
- `GET /encounters` (filters + pagination), `GET /encounters/{id}`, `GET /encounters/{id}/events`
- `POST /encounters` (admin, clinician)
- `POST /encounters/{id}/events` (admin, clinician; event-type + schema validated)
- `POST /encounters/{id}/status` (per-edge RBAC)

### Admin only (org-scoped, soft-delete semantics)
- `POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}`
- `POST /locations`, `PATCH /locations/{id}`, `DELETE /locations/{id}`

## Automation

- `make verify` — backend gate (91 pytest + 9 smoke)
- `make web-verify` — frontend gate (18 vitest + typecheck + build)
- `make e2e` — Playwright (10 scenarios)
- `make pg-verify` — Postgres parity
- `make staging-up / staging-verify / staging-rollback TAG=... / staging-down`
- `make release-build VERSION=v0.1.0`
- `make dev` — backend + frontend
- CI: backend-sqlite + frontend + deploy-config in parallel; e2e needs backend+frontend; backend-postgres + docker-build + docs chain on backend-sqlite.
