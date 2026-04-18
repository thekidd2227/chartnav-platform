# ChartNav — Current State

**As of:** 2026-04-18 (phase: operator control plane — org settings, audit read, user-lifecycle signal)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/{ci.yml,release.yml}
├── Makefile
├── scripts/                # build_docs.py · verify.sh · pg_verify.sh · release_build.sh · staging_*.sh
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py · config.py · db.py · auth.py · authz.py
│   │   │   ├── audit.py · logging_config.py · middleware.py · metrics.py
│   │   │   └── api/routes.py      # + /organization + /security-audit-events
│   │   ├── alembic/versions/      # 5 migrations through d4e5f6a7b8c9
│   │   ├── tests/                 # 88 pytest (+17 control-plane)
│   │   └── Dockerfile · entrypoint.sh · .env.example
│   └── web/
│       ├── src/
│       │   ├── App.tsx
│       │   ├── AdminPanel.tsx     # 4 tabs — Users · Locations · Organization · Audit log
│       │   ├── api.ts             # + org + audit helpers
│       │   ├── identity.ts · styles.css · main.tsx
│       │   └── test/              # 22 Vitest (+4 control-plane)
│       └── tests/e2e/             # 11 Playwright (+1 org/audit)
├── infra/docker/
└── docs/build/ 01 … 23
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `header` (dev) or `bearer` (prod JWT via JWKS).
- RBAC: `admin` / `clinician` / `reviewer` (CHECK-constrained at DB level).
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- **Org settings**: `GET /organization` (any authed role), `PATCH /organization` (admin). 16 KB cap on `settings` JSON; slug immutable.
- **Audit read**: `GET /security-audit-events` (admin, org-scoped `OR organization_id IS NULL`, filterable, paginated).
- **User lifecycle**: `invited_at` stamped on admin create; UI renders "Invited" badge.
- Event discipline: `EVENT_SCHEMAS` allowlist with per-type required keys.
- Encounter pagination: `limit`/`offset` + `X-Total-Count`/`X-Limit`/`X-Offset` headers.
- Observability: `/health` · `/ready` · `/metrics` (Prometheus text).
- CORS + rate-limit + request-id + structured logs: unchanged.
- Alembic head: `d4e5f6a7b8c9`.

## Testing layers

| Layer        | Tool         | Count | Notes |
|--------------|--------------|:-----:|-------|
| pytest       | pytest       |  88   | +17 `test_control_plane.py` (org settings, audit read, invited_at) |
| shell smoke  | smoke.sh     |   9   | unchanged |
| vitest       | vitest       |  22   | +4 admin-panel tests for Organization + Audit tabs |
| Playwright   | @playwright  |  11   | +1 org settings + audit tab E2E |
| staging      | staging_verify.sh | 9 | unchanged |

## Verified working endpoints

Additions this phase:
- `GET /organization`, `PATCH /organization`
- `GET /security-audit-events`

Unchanged from phase 12: `/health`, `/`, `/ready`, `/metrics`, `/me`,
`/organizations`, `/locations`, `/users`, `/encounters` (+ pagination +
filters), admin CRUD for users + locations, event-validated
`POST /encounters/{id}/events`, per-edge RBAC on status transitions.

## Automation

- `make verify` → 88 pytest + 9 smoke
- `make web-verify` → 22 vitest + typecheck + build
- `make e2e` → 11 Playwright
- `make pg-verify` — Postgres parity
- `make staging-up / staging-verify / staging-rollback TAG=... / staging-down`
- `make release-build VERSION=v0.1.0`
- `make dev` — backend + frontend
- CI: backend-sqlite + frontend + deploy-config in parallel; e2e needs backend+frontend; backend-postgres + docker-build + docs chain on backend-sqlite.
