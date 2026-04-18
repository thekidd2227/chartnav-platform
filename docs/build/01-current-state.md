# ChartNav — Current State

**As of:** 2026-04-18 (phase: staging deployment + observability)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/
│   ├── ci.yml            # backend-sqlite · backend-postgres · frontend · e2e · docker-build · deploy-config · docs
│   └── release.yml       # now also bundles the staging artifact tar
├── Makefile              # + staging-up · staging-verify · staging-rollback · staging-down
├── scripts/
│   ├── build_docs.py
│   ├── verify.sh · pg_verify.sh · release_build.sh
│   └── staging_up.sh · staging_verify.sh · staging_rollback.sh
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py              # CORS + middleware + exception-handler audit
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── auth.py              # real JWT bearer
│   │   │   ├── authz.py
│   │   │   ├── audit.py
│   │   │   ├── logging_config.py
│   │   │   ├── middleware.py        # request-id · access log · rate limit
│   │   │   ├── metrics.py           # NEW — in-process Prometheus counters
│   │   │   └── api/routes.py        # adds /ready, /metrics
│   │   ├── alembic/versions/        # 3 migrations through b2c3d4e5f6a7
│   │   ├── scripts_seed.py · scripts/smoke.sh
│   │   ├── tests/                   # 51 pytest (+ 3 observability)
│   │   └── Dockerfile · entrypoint.sh · .env.example
│   └── web/
│       └── (unchanged this phase)
├── infra/docker/
│   ├── docker-compose.yml           # dev
│   ├── docker-compose.prod.yml      # generic prod
│   ├── docker-compose.staging.yml   # NEW — pinned image, /ready healthcheck, volumes
│   └── .env.staging.example         # NEW — explicit staging contract
└── docs/build/ 01 … 21
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `header` (dev) or `bearer` (prod, real JWT with JWKS cache).
- RBAC: `admin` / `clinician` / `reviewer`.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- **Observability**: `/health` (liveness), `/ready` (DB-aware), `/metrics` (Prometheus text).
- **Audit trail**: `security_audit_events` table; written on 401/403 + listed error codes + 429 rate_limited.
- **CORS**: env-driven, no wildcard.
- **Rate limit**: per-process sliding window on authed paths.
- **Request correlation**: `X-Request-ID` inbound is honored, otherwise generated; always echoed.
- **Structured logs**: JSON per line.
- Alembic head: `b2c3d4e5f6a7`.

## Testing layers

| Layer        | Tool         | Count | Scope                                                                 |
|--------------|--------------|:-----:|-----------------------------------------------------------------------|
| pytest       | pytest       |  51   | backend (auth, RBAC, scoping, state machine, bearer JWT, operational, observability) |
| shell smoke  | smoke.sh     |   9   | live HTTP contract (SQLite + Postgres)                                |
| vitest       | vitest       |  12   | frontend integration                                                  |
| Playwright   | @playwright  |   8   | full-stack browser                                                    |
| staging smoke| staging_verify.sh | 9 | live staging stack (health + ready + metrics + auth + audit signal)   |

## Deploy / release

- Release: `.github/workflows/release.yml` on `v*.*.*` tags pushes `ghcr.io/<owner>/chartnav-api:<tag>` + `:latest`, produces `chartnav-api-<v>.tar`, `chartnav-web-<v>.tar.gz`, `chartnav-staging-<v>.tar.gz`, and `MANIFEST.txt` in a GitHub Release.
- Staging deploy: `infra/docker/docker-compose.staging.yml` + `.env.staging` on the staging host; one-shot `make staging-up` / `staging-verify` / `staging-rollback TAG=...`.
- Prod: `infra/docker/docker-compose.prod.yml` remains available; it's the generic ancestor of the staging compose.

## Automation

- `make verify` (backend gate), `make pg-verify` (Postgres parity), `make web-verify`, `make e2e`
- `make staging-up / staging-verify / staging-rollback TAG=... / staging-down`
- `make release-build VERSION=v0.1.0`
- `make dev` (boot backend + frontend)
- CI: `backend-sqlite` + `frontend` + `deploy-config` in parallel; `e2e` gates on backend+frontend; `backend-postgres`, `docker-build`, `docs` chain on `backend-sqlite`.
