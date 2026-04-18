# Staging Deployment

## Shape

ChartNav's staging deploy unit is a **pinned Docker image** (`ghcr.io/<owner>/chartnav-api:<tag>`) plus a `postgres:16-alpine` container, wired together by `infra/docker/docker-compose.staging.yml`. That's the whole substrate. There is no Kubernetes, no Terraform, no serverless. Rolling out = change a tag + restart. Rolling back = change the tag back + restart.

This is intentional. ChartNav is still a small service; a boring, reproducible compose deploy is the honest size. Phase-out-to-something-bigger will be a deliberate future phase, not an accident.

## Artifacts added this phase

| Path                                          | Purpose                                          |
|-----------------------------------------------|--------------------------------------------------|
| `infra/docker/docker-compose.staging.yml`     | API + Postgres, pinned image, healthcheck on `/ready`, volumes, restart policy. |
| `infra/docker/.env.staging.example`           | The env contract. Copy to `.env.staging` and fill in. |
| `scripts/staging_up.sh`                       | `docker compose config`-validate then `up -d`.    |
| `scripts/staging_verify.sh`                   | Smoke + observability check against the running stack. |
| `scripts/staging_rollback.sh <prev_tag>`      | Repin `CHARTNAV_IMAGE_TAG`, pull, restart API, wait for `/ready`. |

## Topology

```
    ┌────────────────┐       ┌────────────────────────┐
    │  reverse proxy │──TLS──▶  api:8000 (127.0.0.1)  │
    │  (ops layer)   │       │  ghcr.io/..../chartnav  │
    └────────────────┘       │  -api:${TAG}            │
                             │  entrypoint: migrate    │
                             │  + uvicorn              │
                             └───────────┬─────────────┘
                                         │ postgresql+psycopg
                                         ▼
                              ┌────────────────────┐
                              │ db:5432            │
                              │ postgres:16-alpine │
                              │ volume:            │
                              │  chartnav_staging_ │
                              │  pgdata            │
                              └────────────────────┘
```

- API and DB both bind to `127.0.0.1` on the host — reverse proxy terminates TLS and handles public routing.
- Healthcheck runs `curl -fsS http://127.0.0.1:8000/ready` inside the container: because `/ready` touches the DB, that one call also verifies migrations ran and the DB connection is live.
- DB persistence: named volume `chartnav_staging_pgdata`. Volumes survive `docker compose down`; they do **not** survive `docker compose down -v`. A rollback to a prior image tag never needs to touch the volume.

## Migration-on-start

`apps/api/entrypoint.sh` runs `alembic upgrade head` before it execs `uvicorn`. Staging respects that, so "deploy = new image" and "migrate" are the same action. Two properties fall out for free:
- Deploys are idempotent: apply the same tag twice, get the same schema.
- Downgrade paths are an image concern, not an ops concern: redeploying an older image with its own Alembic head will only try to apply migrations it knows about.

If a migration ever needs to run offline (big data reshape), that's the one thing this flow doesn't help with — pin the old image, take an outage window, run `alembic` manually, then deploy the new image.

## Required env contract (summary)

Full reference: `12-runtime-config.md`. Staging adds nothing new; it just requires real values for what was optional in dev:

| Var                              | Notes                                           |
|----------------------------------|-------------------------------------------------|
| `CHARTNAV_IMAGE_OWNER` / `_TAG`  | GHCR owner + pinned tag.                        |
| `POSTGRES_DB/USER/PASSWORD`      | Never commit real values.                       |
| `CHARTNAV_AUTH_MODE`             | `bearer` in real staging. `header` only for first-touch QA. |
| `CHARTNAV_JWT_*`                 | Required when `AUTH_MODE=bearer`; the app refuses to import otherwise. |
| `CHARTNAV_CORS_ALLOW_ORIGINS`    | **Never `*`**. Real staging frontend origin(s) only. |
| `CHARTNAV_RATE_LIMIT_PER_MINUTE` | Defaults to 120; bump for load-test windows.    |

Compose uses `${VAR:?message}` for the critical vars so a missing value blocks `docker compose up` with an explicit error.

## Commands

```bash
# first-time: copy + fill in
cp infra/docker/.env.staging.example infra/docker/.env.staging
# edit infra/docker/.env.staging with real values

# deploy
make staging-up          # docker compose config + up -d
make staging-verify      # smoke + observability checks (see 21)
# real traffic

# rollback to a previously-published tag
make staging-rollback TAG=v0.0.9
make staging-verify

# teardown (keeps the DB volume)
make staging-down
# nuke DB too
cd infra/docker && docker compose -f docker-compose.staging.yml --env-file .env.staging down -v
```

## Rollback — honest description

"Rollback" in this deploy is:

1. `scripts/staging_rollback.sh <prev_tag>` rewrites `CHARTNAV_IMAGE_TAG` in `.env.staging`.
2. `docker compose pull api` fetches the prior image from GHCR.
3. `docker compose up -d api` restarts only the API service; Postgres is untouched.
4. The script polls `/ready` and fails loudly if it doesn't come back green within ~40s.

What rollback **cannot** do on this substrate:
- Undo a destructive migration. If revision N dropped a column, going back to N-1's image won't restore the column. Treat destructive migrations as one-way on this deploy.
- Blue/green. There's one API replica.
- In-flight request draining. `docker compose up -d` is SIGTERM-then-wait. If you need graceful draining of long operations, put them behind a queue, not the web process.

Those are fair tradeoffs for a compose-based staging. The migration-on-start path also means the rollback script doesn't need to run Alembic by hand — the old image knows its own head.

## CI validation

`.github/workflows/ci.yml` → `deploy-config` job: on every push/PR it runs `docker compose … config` on all three compose files (dev/staging/prod) and `shellcheck` on every repo script. A broken compose file or sloppy script lands a failing check before the operator ever tries to `staging-up`.
