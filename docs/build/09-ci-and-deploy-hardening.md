# CI & Deploy Hardening

## GitHub Actions

File: `.github/workflows/ci.yml`. Triggers on **push to `main`** and **every pull request**.

### `backend-sqlite`
Install deps → `alembic upgrade head` against an isolated `$RUNNER_TEMP/chartnav_ci.db` via `DATABASE_URL` → seed **twice** (idempotency proof) → `pytest tests/ -v` (28 tests) → `bash scripts/verify.sh` (boots uvicorn, runs `scripts/smoke.sh`).

### `backend-postgres` (needs: `backend-sqlite`)
Service container `postgres:16-alpine` on localhost:5432. Install deps (incl. `[postgres]` extra) → `alembic upgrade head` on Postgres → seed twice → boot uvicorn → `scripts/smoke.sh` → live status transition asserts the returned row. Fails the workflow if Postgres parity breaks.

### `frontend`
Node 20 + npm cache keyed on `apps/web/package-lock.json` → `npm ci` → `npm run typecheck` → `npm test` (vitest, 12 integration tests) → `npm run build`. Runs in parallel with `backend-sqlite` — the frontend is a peer quality gate, not blocked by backend CI.

### `docker-build` (needs: `backend-sqlite`)
Buildx → build `chartnav-api:ci` from `apps/api/` → run the container with `DATABASE_URL=sqlite:///./chartnav.db` and `CHARTNAV_RUN_SEED=1` → poll `/health` → run `scripts/smoke.sh` against the live container. Proves the production image boots end-to-end.

### `docs` (needs: `backend-sqlite`)
apt-install Chromium → `python scripts/build_docs.py` with `CHARTNAV_PDF_BROWSER=chromium-browser` → upload HTML + PDF as `chartnav-docs-final` artifact (`if-no-files-found: error`).

### What CI catches

| Change                                       | Failure surface              |
|----------------------------------------------|------------------------------|
| Broken migration                             | alembic step (both DBs)      |
| Broken seed / re-seed collision              | seed step (both DBs)         |
| Any pytest regression                        | `backend-sqlite` pytest      |
| `/health` or auth drift                      | `scripts/smoke.sh` (all envs)|
| Cross-org / state-machine regression         | smoke + `backend-postgres` transition|
| Postgres-only SQL dialect break              | `backend-postgres`           |
| Image won't build or boot                    | `docker-build`               |
| Docs pipeline regression                     | `docs` job                   |

## Local verification

```bash
make verify        # SQLite end-to-end
make pg-verify     # Postgres end-to-end (Docker required)
make docker-build  # build the production image
make docker-up     # full API + Postgres stack (compose)
```

Individual recipes: `install | migrate | seed | test | boot | smoke | docs | reset-db | clean`.

## Dev / test / CI / prod DB separation

| Surface          | Path                                                  |
|------------------|-------------------------------------------------------|
| Developer local  | `apps/api/chartnav.db` (gitignored)                  |
| pytest per-test  | `tmp_path / "chartnav.db"` (ephemeral)                |
| CI (sqlite)      | `$RUNNER_TEMP/chartnav_ci.db` (ephemeral)             |
| CI (postgres)    | `postgres:16-alpine` service container                |
| Local pg-verify  | throwaway `chartnav-pg-verify` container on port 55432|
| Prod compose     | `chartnav_pgdata` persistent volume                   |

## Smoke script (shared contract)

`apps/api/scripts/smoke.sh [BASE_URL]` — 9 curl assertions:
`/health` (code + body), `/me` (401/200), `/encounters` (401/200), cross-org lens 403, own 200, cross-org 404. Exits non-zero on first failure. Used by **every** smoke path (local `make verify`, Postgres parity, Docker image CI).

## What this phase adds beyond CI

- Hardened `Dockerfile` (non-root, healthcheck).
- `apps/api/entrypoint.sh` for deterministic migrate-on-start.
- `infra/docker/docker-compose.prod.yml` for the API + Postgres stack.
- `scripts/pg_verify.sh` — reproducible Postgres parity proof.

## What this phase does NOT do

- No image push / registry release.
- No Kubernetes / Terraform / cloud-specific bits.
- No TLS termination or edge reverse proxy.
- No secret store integration.

Those land in a dedicated hosted-deploy phase. This phase makes sure
the seams are in place to plug any of them in without rewrites.
