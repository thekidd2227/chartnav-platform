# ChartNav — Current State

**As of:** 2026-04-18 (phase: Playwright E2E + release pipeline)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/
│   ├── ci.yml            # backend-sqlite · backend-postgres · frontend · e2e · docker-build · docs
│   └── release.yml       # NEW — tag-driven GHCR push + GitHub Release
├── Makefile              # verify · pg-verify · docker-* · web-* · e2e · release-build · dev
├── scripts/
│   ├── build_docs.py
│   ├── verify.sh
│   ├── pg_verify.sh
│   └── release_build.sh  # NEW — reproducible release bundle
├── apps/
│   ├── api/              # unchanged
│   └── web/
│       ├── package.json           # + test:e2e / :headed / :ui
│       ├── playwright.config.ts   # NEW — backend + frontend webServer
│       ├── tests/e2e/
│       │   └── workflow.spec.ts   # NEW — 8 browser tests
│       ├── src/test/              # 12 vitest tests (phase 8)
│       └── ...
├── infra/docker/{docker-compose,docker-compose.prod}.yml
└── docs/build/ 01 … 17
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core, SQLite or Postgres.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + **Playwright**.
- Auth: `CHARTNAV_AUTH_MODE=header` (dev) or `bearer` (prod placeholder 501).
- RBAC: `admin` / `clinician` / `reviewer`.
- Alembic head: `a1b2c3d4e5f6`. No schema changes this phase.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.

## Testing layers

| Layer        | Tool        | Count | Scope                              |
|--------------|-------------|:-----:|------------------------------------|
| pytest       | `pytest`    | 28    | backend units + integration        |
| shell smoke  | `scripts/smoke.sh` | 9  | live HTTP contract (SQLite + Postgres) |
| vitest       | `vitest`    | 12    | frontend integration (mocked API)  |
| **Playwright E2E** | `@playwright/test` | 8 | full-stack browser (live backend + frontend) |

## Release / deploy

- **Artifacts** (via `scripts/release_build.sh`):
  - `chartnav-api-<version>.tar` (docker save, loadable anywhere).
  - `chartnav-web-<version>.tar.gz` (static bundle from `apps/web/dist`).
  - `MANIFEST.txt` with git sha, ref, build time, sha256 sums.
- **Registry**: `ghcr.io/<owner>/chartnav-api:<version>` (and `:latest`) on tagged builds.
- **GitHub Release**: auto-created on `v*.*.*` tag pushes with notes + artifacts attached.
- Runtime stack: `infra/docker/docker-compose.prod.yml` (API + Postgres).

## Verified working endpoints

No endpoint behavior changed this phase.

## Automation

- `make verify` — SQLite backend gate.
- `make pg-verify` — Postgres parity.
- `make web-verify` — frontend unit gate.
- `make e2e` — full-stack browser tests.
- `make release-build VERSION=v0.1.0` — produce the release bundle locally.
- `make dev` — boot backend + frontend together.
- CI: `backend-sqlite` + `frontend` run in parallel; `e2e` gates on both;
  `backend-postgres`, `docker-build`, `docs` chain on `backend-sqlite`.
