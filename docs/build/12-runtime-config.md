# Runtime Configuration

Single source of truth: `apps/api/app/config.py` (`settings`). Every
other module imports from there; nothing else reads `os.environ`.

## The contract

| Variable                  | Required?                        | Default                       | Purpose |
|---------------------------|----------------------------------|-------------------------------|---------|
| `CHARTNAV_ENV`            | no                               | `dev`                         | Informational label (`dev`/`test`/`ci`/`prod`). |
| `DATABASE_URL`            | no (dev default)                 | `sqlite:///apps/api/chartnav.db` | SQLAlchemy URL. Supports `sqlite:///...` and `postgresql+psycopg://...`. |
| `CHARTNAV_AUTH_MODE`      | no                               | `header`                      | `header` (dev only) or `bearer` (prod placeholder). |
| `CHARTNAV_JWT_ISSUER`     | **yes iff** `AUTH_MODE=bearer`   | —                             | OIDC issuer URL. |
| `CHARTNAV_JWT_AUDIENCE`   | **yes iff** `AUTH_MODE=bearer`   | —                             | Expected `aud` claim. |
| `CHARTNAV_JWT_JWKS_URL`   | **yes iff** `AUTH_MODE=bearer`   | —                             | JWKS endpoint for signing-key lookup. |
| `CHARTNAV_RUN_SEED`       | no                               | `0`                           | Entrypoint: run `scripts_seed.py` after migrations. Keep `0` in prod. |
| `API_HOST` / `API_PORT`   | no                               | `0.0.0.0` / `8000`            | Uvicorn bind. |

## Validation on startup

`app.config._load()` is evaluated at import time. It enforces:

- `CHARTNAV_AUTH_MODE ∈ {header, bearer}`.
- If `AUTH_MODE=bearer`, **all three** JWT vars must be set — otherwise
  a `RuntimeError` is raised listing the missing names. The app will
  not boot half-configured.

## Dev / CI / Prod profiles

| Profile | How config is supplied | DB                          | Auth mode | Seed |
|---------|------------------------|-----------------------------|-----------|------|
| Dev     | `apps/api/.env.example` → `.env`; Makefile targets | `sqlite:///apps/api/chartnav.db` | `header` | ad-hoc (`make seed`) |
| Tests   | `apps/api/tests/conftest.py` sets env per-test      | per-test SQLite in `tmp_path`    | `header` | via `scripts_seed.main()` |
| CI      | `.github/workflows/ci.yml` inline env + services    | SQLite + live Postgres service   | `header` | seed + re-seed in workflow |
| Prod    | platform env / secret store                         | `postgresql+psycopg://...` via `infra/docker/docker-compose.prod.yml` | `bearer` (when JWT validation is wired) | off by default |

## Example files

- `apps/api/.env.example` — full dev contract with comments.
- `infra/docker/docker-compose.prod.yml` — wires the API container to
  a Postgres service using these env vars; each has a documented
  default so the file is runnable as-is for local parity tests.

## Database URL specifics

- **SQLite:** `sqlite:///relative/or/absolute/path.db` (three slashes +
  absolute path, or three slashes + relative path).
- **Postgres:** `postgresql+psycopg://user:pass@host:5432/dbname`.
  The `+psycopg` driver selector is important — SQLAlchemy defaults to
  `psycopg2` which is not installed. `psycopg[binary]` is declared in
  `apps/api/pyproject.toml` as the `[postgres]` extra.

## What this phase explicitly does NOT do

- No secret store integration (AWS SM, Vault, etc.).
- No `.env` auto-loading in the API (docker-compose and operators load env).
- No per-request feature flags / remote config.

Those are safe to layer on top of this contract without reshaping it.
