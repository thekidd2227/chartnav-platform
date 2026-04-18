# CI & Deploy Hardening

## GitHub Actions workflow

File: `.github/workflows/ci.yml`

Triggers: **push to `main`** and **every pull request**.

### Job `backend` (ubuntu-latest, working directory `apps/api`)

1. `actions/checkout@v4`
2. `actions/setup-python@v5` — Python 3.11, pip cache on.
3. `pip install -e ".[dev]"` — installs backend plus `pytest` + `httpx` from `pyproject.toml [project.optional-dependencies].dev`.
4. **Migrate (isolated CI DB)** — `alembic -x "sqlalchemy.url=sqlite:///$CI_DB_PATH" upgrade head`. `CI_DB_PATH` lives under `$RUNNER_TEMP`, never in the repo.
5. **Idempotent seed run twice** — proves the seed is safe to re-run in live environments.
6. **Tests** — `pytest tests/ -v`. 25 tests must pass.
7. **API boot smoke** — launches uvicorn in-process against the CI DB, waits up to ~10s for `/health`, then runs `apps/api/scripts/smoke.sh`. Smoke script exercises `/health`, `/me` auth paths, `/encounters` scoped list, and the cross-org 403 lens.

### Job `docs` (ubuntu-latest, `needs: backend`)

1. Install Chromium via apt (`chromium-browser`).
2. Run `python scripts/build_docs.py` with `CHARTNAV_PDF_BROWSER=chromium-browser`.
3. Upload `docs/final/chartnav-workflow-state-machine-build.{html,pdf}` as a CI artifact — the `docs` job fails loudly if either artifact is missing.

### What CI catches

| Change                                       | Failure surface            |
|----------------------------------------------|----------------------------|
| Broken migration                             | `alembic upgrade` step     |
| Broken seed                                  | idempotent-seed step       |
| Any pytest regression (auth, RBAC, scoping, state machine) | pytest step |
| App can't boot / `/health` broken            | smoke script               |
| `/me` contract drift                         | smoke script               |
| Cross-org leak introduced                    | smoke 403 lens check       |
| Docs pipeline regression                     | `docs` job                 |

## Local verification path (canonical)

One command:

```bash
make verify
```

Under the hood that:
- resets the dev SQLite DB,
- applies Alembic migrations,
- re-seeds idempotently,
- runs pytest,
- boots uvicorn on port 8765,
- runs `apps/api/scripts/smoke.sh`,
- kills the boot process.

Individual targets:

| Target       | Purpose                                              |
|--------------|------------------------------------------------------|
| `make install` | venv + `pip install -e "apps/api[dev]"`           |
| `make migrate` | Alembic upgrade head on dev DB                    |
| `make seed`    | Idempotent seed on dev DB                         |
| `make test`    | Full pytest suite                                 |
| `make boot`    | Foreground uvicorn on port 8765                   |
| `make smoke`   | `scripts/smoke.sh` against running API            |
| `make docs`    | Rebuild `docs/final/*.html` + `.pdf`              |
| `make reset-db`| `rm -f chartnav.db` + migrate + seed              |
| `make clean`   | Remove DB + caches                                |

## Dev vs CI DB separation

| Surface                | Path                                     |
|------------------------|------------------------------------------|
| Developer local        | `apps/api/chartnav.db` (gitignored)      |
| pytest per-test        | `tmp_path / "chartnav.db"` (ephemeral)   |
| CI                     | `$RUNNER_TEMP/chartnav_ci.db` (ephemeral)|

The only path CI or tests ever touch inside the repo is the source code;
no DB file is shared between contexts.

## Smoke script

File: `apps/api/scripts/smoke.sh`

Shell-only curl-level checks. Takes an optional `BASE_URL`:

```bash
scripts/smoke.sh [BASE_URL=http://127.0.0.1:8000]
```

Exits non-zero on the first failed assertion. Exercises:

- `GET /health` → 200 + `status=ok`
- `GET /me` → 401 without auth; 200 with seeded admin header; role equals `admin`
- `GET /encounters` → 401 without auth; 200 with admin header
- `GET /encounters?organization_id=2` as org1 admin → 403 (cross-org lens)
- `GET /encounters/1` as org1 admin → 200
- `GET /encounters/3` as org1 admin → 404 (cross-org)

## What this phase explicitly does NOT do

- No container image build / push.
- No production deploy target.
- No Kubernetes, Terraform, or infra-as-code.
- No secrets management or signed build artifacts.

Those belong in a future "hosted deploy" phase. The seam is ready: CI
already reliably migrates, seeds, tests, and smokes the API.
