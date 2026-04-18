# ChartNav — Current State

**As of:** 2026-04-18 (phase: JWT bearer auth + operational hardening)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/
│   ├── ci.yml            # backend-sqlite · backend-postgres · frontend · e2e · docker-build · docs
│   └── release.yml
├── Makefile
├── scripts/              # build_docs.py · verify.sh · pg_verify.sh · release_build.sh
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py              # CORS + middleware + exception-handler audit
│   │   │   ├── config.py            # + CORS, rate-limit, jwt-claim config
│   │   │   ├── db.py
│   │   │   ├── auth.py              # real JWT bearer via PyJWKClient
│   │   │   ├── authz.py
│   │   │   ├── audit.py             # NEW — security_audit_events writer
│   │   │   ├── logging_config.py    # NEW — JSON logs
│   │   │   ├── middleware.py        # NEW — request id / access log / rate limit
│   │   │   └── api/routes.py
│   │   ├── alembic/versions/        # 3 migrations (now + security_audit_events)
│   │   ├── scripts_seed.py
│   │   ├── scripts/smoke.sh
│   │   ├── tests/                   # 48 pytest (incl. 11 bearer + 12 operational)
│   │   └── Dockerfile · entrypoint.sh
│   └── web/
│       └── (unchanged this phase)
├── infra/docker/{docker-compose,docker-compose.prod}.yml
└── docs/build/ 01 … 18
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT. SQLite or Postgres.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `CHARTNAV_AUTH_MODE`
  - `header` (dev) — `X-User-Email` → `users` lookup.
  - `bearer` (prod) — real JWT validation (signature/iss/aud/exp) against `CHARTNAV_JWT_JWKS_URL`, claim → user via `CHARTNAV_JWT_USER_CLAIM`.
- RBAC: `admin` / `clinician` / `reviewer`.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}` — audited by the HTTP exception handler for 401/403 + listed codes.
- **CORS**: env-driven `CHARTNAV_CORS_ALLOW_ORIGINS`. No more `*`.
- **Rate limit**: `CHARTNAV_RATE_LIMIT_PER_MINUTE` (default 120), in-memory sliding window on authed paths.
- **Request correlation**: `X-Request-ID` inbound is honored, otherwise generated; always echoed.
- **Structured logs**: JSON-per-line; every request logs `request_id`, `method`, `path`, `status`, `duration_ms`, `user_email`, `organization_id`.
- **Audit table**: `security_audit_events` (migration `b2c3d4e5f6a7`); written on auth/scoping/role/rate-limit denials; never on success.

Alembic head: `b2c3d4e5f6a7`.

## Testing layers

| Layer        | Tool         | Count | Scope                                                                  |
|--------------|--------------|:-----:|------------------------------------------------------------------------|
| pytest       | pytest       |  48   | backend units + integration (auth, RBAC, scoping, state machine, bearer JWT, ops hardening) |
| shell smoke  | smoke.sh     |   9   | live HTTP contract (SQLite + Postgres)                                 |
| vitest       | vitest       |  12   | frontend integration (mocked API)                                      |
| Playwright   | @playwright  |   8   | full-stack browser (live backend + frontend)                           |

## Release / deploy

- `scripts/release_build.sh` builds a docker-saved API tar + web bundle + sha256 manifest under `dist/release/<version>/`.
- `.github/workflows/release.yml` on `v*.*.*` tags pushes `ghcr.io/<owner>/chartnav-api:<version>` + `:latest` and creates a GitHub Release with the bundle attached.

## Automation

- `make verify` (backend gate), `make pg-verify` (Postgres parity)
- `make web-verify` (frontend unit gate), `make e2e` (browser gate)
- `make release-build VERSION=v0.1.0` (reproducible bundle)
- `make dev` (boot backend + frontend)
- CI: `backend-sqlite` + `frontend` run in parallel; `e2e` gates on both; `backend-postgres`, `docker-build`, `docs` chain on `backend-sqlite`.
