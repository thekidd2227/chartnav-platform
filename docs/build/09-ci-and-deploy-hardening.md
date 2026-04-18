# CI & Deploy Hardening

## GitHub Actions

File: `.github/workflows/ci.yml`. Triggers on **push to `main`** and **every pull request**.

### `backend-sqlite`
Install deps → `alembic upgrade head` against an isolated `$RUNNER_TEMP/chartnav_ci.db` via `DATABASE_URL` → seed **twice** (idempotency proof) → `pytest tests/ -v` (28 tests) → `bash scripts/verify.sh` (boots uvicorn, runs `scripts/smoke.sh`).

### `backend-postgres` (needs: `backend-sqlite`)
Service container `postgres:16-alpine` on localhost:5432. Install deps (incl. `[postgres]` extra) → `alembic upgrade head` on Postgres → seed twice → boot uvicorn → `scripts/smoke.sh` → live status transition asserts the returned row. Fails the workflow if Postgres parity breaks.

### `frontend`
Node 20 + npm cache keyed on `apps/web/package-lock.json` → `npm ci` → `npm run typecheck` → `npm test` (vitest, 12 integration tests) → `npm run build`. Runs in parallel with `backend-sqlite` — the frontend is a peer quality gate, not blocked by backend CI.

### `deploy-config`
Independent — runs in parallel with the backend/frontend gates.
- `docker compose config` on all three compose files (dev/staging/prod).
- `shellcheck` on every repo script (`scripts/*.sh`, `apps/api/scripts/smoke.sh`).
A broken compose file or sloppy script lands a red check before anyone runs `staging-up`.

### `e2e` (needs: `backend-sqlite`, `frontend`)
Python 3.11 + Node 20 installed. `pip install -e "apps/api[dev,postgres]"` + `npm ci` in `apps/web`. `npx playwright install --with-deps chromium`. Then `npx playwright test tests/e2e/workflow.spec.ts tests/e2e/a11y.spec.ts --reporter=list` — Playwright boots backend on 8001 (SQLite, `CHARTNAV_RATE_LIMIT_PER_MINUTE=0` because all traffic comes from 127.0.0.1) and frontend on 5174, runs the 12 workflow scenarios + **5 axe-core a11y scans** (hard gate — `serious`/`critical` findings fail CI), tears both down. On failure, `playwright-report/` and `test-results/` are uploaded as a workflow artifact for triage.

**Visual regression is intentionally excluded from CI** (`tests/e2e/visual.spec.ts`, 4 snapshots) — baselines are OS-specific (`*-chromium-darwin.png`) and CI runs on Linux; running visual there would fail first-run. Visual is a local-only gate (`make e2e-visual`). Honest limitation, documented in `25-enterprise-quality-and-compliance.md`.

### `release.yml` (separate workflow)
Triggers on `v*.*.*` tag push and manual dispatch. Builds + pushes `ghcr.io/<owner>/chartnav-api:<version>` (+ `:latest`), runs `scripts/release_build.sh` to produce `dist/release/<version>/` (docker-saved image tar, web bundle tar.gz, MANIFEST with sha256s, **SBOM JSON `chartnav-sbom-<v>.json`**, and **image digest `chartnav-api-<v>.digest.txt`** — both added in phase 15), uploads the directory as an artifact, and on tag pushes attaches the files (including SBOM + digest) to a GitHub Release with auto-generated notes. Full reference in `17-e2e-and-release.md`.

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
