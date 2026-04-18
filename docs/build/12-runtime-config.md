# Runtime Configuration

Single source of truth: `apps/api/app/config.py` (`settings`). Every
other module imports from there; nothing else reads `os.environ`.

## The contract

| Variable                            | Required?                        | Default                                | Purpose |
|-------------------------------------|----------------------------------|----------------------------------------|---------|
| `CHARTNAV_ENV`                      | no                               | `dev`                                  | Informational label. |
| `DATABASE_URL`                      | no (dev default)                 | `sqlite:///apps/api/chartnav.db`       | SQLAlchemy URL. SQLite + Postgres. |
| `CHARTNAV_AUTH_MODE`                | no                               | `header`                               | `header` (dev) or `bearer` (prod, real JWT). |
| `CHARTNAV_JWT_ISSUER`               | **yes iff** `AUTH_MODE=bearer`   | —                                      | OIDC issuer URL. |
| `CHARTNAV_JWT_AUDIENCE`             | **yes iff** `AUTH_MODE=bearer`   | —                                      | Expected `aud` claim. |
| `CHARTNAV_JWT_JWKS_URL`             | **yes iff** `AUTH_MODE=bearer`   | —                                      | JWKS endpoint for signing-key lookup. |
| `CHARTNAV_JWT_USER_CLAIM`           | no                               | `email`                                | Token claim used to map to `users.email`. |
| `CHARTNAV_CORS_ALLOW_ORIGINS`       | no                               | `http://localhost:5173,127.0.0.1:5173,localhost:5174,127.0.0.1:5174` | CSV. Empty string ⇒ same-origin only. |
| `CHARTNAV_RATE_LIMIT_PER_MINUTE`    | no                               | `120`                                  | Per-process sliding window on authed paths. `0` disables. |
| `CHARTNAV_RUN_SEED`                 | no                               | `0`                                    | Entrypoint: run seed after migrations. Keep `0` in prod. |
| `API_HOST` / `API_PORT`             | no                               | `0.0.0.0` / `8000`                     | Uvicorn bind. |
| `CHARTNAV_AUDIT_RETENTION_DAYS`     | no                               | `0` (never prune)                      | Operator-invoked retention helper (`scripts/audit_retention.py`). Never invoked from a request path. |
| `CHARTNAV_PLATFORM_MODE`            | no                               | `standalone`                           | Operating mode (phase 16). `standalone` · `integrated_readthrough` · `integrated_writethrough`. |
| `CHARTNAV_INTEGRATION_ADAPTER`      | no                               | `native` (standalone) / `stub` (integrated) | Selects the external-system adapter in integrated modes. `standalone` rejects any value other than `native`. Vendor adapters plug in via `register_vendor_adapter(key, factory)` in `app/integrations/__init__.py`. |

## Validation on startup

`app.config._load()` is evaluated at import time. It enforces:

- `CHARTNAV_AUTH_MODE ∈ {header, bearer}`.
- If `AUTH_MODE=bearer`, **all three** JWT vars must be set — otherwise
  a `RuntimeError` is raised listing the missing names. The app will
  not boot half-configured.
- `CHARTNAV_PLATFORM_MODE ∈ {standalone, integrated_readthrough,
  integrated_writethrough}` — any other value raises at import time.
- `CHARTNAV_PLATFORM_MODE=standalone` + `CHARTNAV_INTEGRATION_ADAPTER`
  anything other than `native` raises at import time (operator error;
  native is the only valid adapter in standalone mode).
- `CHARTNAV_RATE_LIMIT_PER_MINUTE` / `CHARTNAV_AUDIT_RETENTION_DAYS`
  must be non-negative integers.

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

## Staging env contract (phase 11)

`infra/docker/.env.staging.example` captures the contract for the
staging compose file. Every critical value is `${VAR:?}`-guarded in
`infra/docker/docker-compose.staging.yml` so missing env blocks
startup loudly. Extra staging-only vars:

| Variable                | Purpose                                                        |
|-------------------------|----------------------------------------------------------------|
| `CHARTNAV_IMAGE_OWNER`  | GHCR namespace (e.g. `thekidd2227`).                           |
| `CHARTNAV_IMAGE_TAG`    | Pinned image tag. Rollback = change this + restart.            |
| `POSTGRES_DB` / `USER` / `PASSWORD` / `PORT` | Required. Never commit real values.     |

Dev continues to use `apps/api/.env.example`. Runbook: `21-staging-runbook.md`.

## Frontend runtime config

The web app reads exactly one env var at build time:

| Variable        | Required? | Default                  | Purpose                              |
|-----------------|-----------|--------------------------|--------------------------------------|
| `VITE_API_URL`  | no        | `http://localhost:8000`  | Base URL the API client points at.   |

Template: `apps/web/.env.example`. Copy to `.env` to override for a
non-default backend.

Vite substitutes `import.meta.env.VITE_API_URL` into the bundle at build.
Nothing else about the UI comes from env today — dev identity is
selected inside the app and stored in `localStorage`.

## What this phase explicitly does NOT do

- No secret store integration (AWS SM, Vault, etc.).
- No `.env` auto-loading in the API (docker-compose and operators load env).
- No per-request feature flags / remote config.

Those are safe to layer on top of this contract without reshaping it.
