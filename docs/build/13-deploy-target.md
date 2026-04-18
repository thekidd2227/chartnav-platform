# Deploy Target

## Chosen path

Docker image built from `apps/api/Dockerfile`, wired to a Postgres
service via `infra/docker/docker-compose.prod.yml`. That's the single
supported deploy surface in this phase — no Kubernetes, no Terraform,
no cloud-specific glue yet.

## Hardened Dockerfile

`apps/api/Dockerfile`:

- `python:3.11-slim` base.
- `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, disabled pip cache.
- Installs `curl` only (for the container healthcheck).
- Installs the API with the `[postgres]` extra (`psycopg[binary]`).
- Copies `app/`, `alembic/`, `alembic.ini`, `scripts/`, `scripts_seed.py`, `entrypoint.sh`.
- Creates a non-root `chartnav` user (uid 1001) and runs as that user.
- `HEALTHCHECK` hits `/health` every 15s with 3 retries.
- `ENTRYPOINT` is `./entrypoint.sh`; `CMD` is the uvicorn invocation.

## Entrypoint

`apps/api/entrypoint.sh`:

1. Asserts `DATABASE_URL` is set (fails loudly otherwise).
2. `alembic upgrade head` — migrations always run at start-up.
3. If `CHARTNAV_RUN_SEED=1`, runs `python scripts_seed.py` (idempotent; off by default in prod).
4. `exec "$@"` — hands off to `CMD` so uvicorn becomes PID 1's child.

Migration-on-start is the right default for this app today. It is
idempotent, small, and the seed step is gated off in production.

## docker-compose.prod.yml

`infra/docker/docker-compose.prod.yml` brings up two services:

- `db` — `postgres:16-alpine` with a persistent volume, healthcheck,
  and dev-safe default credentials (operators must override for real
  deploys).
- `api` — built from `apps/api/Dockerfile`, depends on `db` with
  `condition: service_healthy`, reads all runtime config from env.

All sensitive values (`POSTGRES_PASSWORD`, JWT settings, etc.) are
`${VAR:-default}` so the file is runnable locally for parity tests but
ships nothing secret.

## Startup path

```bash
# clone + cd
cd infra/docker
# optional: override defaults via env
docker compose -f docker-compose.prod.yml up --build
```

Boot sequence per container:
1. Postgres starts, becomes healthy (~5s).
2. API container starts, entrypoint runs migrations.
3. uvicorn binds 0.0.0.0:8000.
4. HEALTHCHECK turns green.

## Runtime config path

Every variable is documented in `12-runtime-config.md`. The
image respects only those — there's no bespoke `config.yaml`,
Consul, etc. to reason about.

## CI build verification

`.github/workflows/ci.yml` → `docker-build` job:

1. Buildx sets up.
2. Builds `chartnav-api:ci` from `apps/api/`.
3. Runs the container with `DATABASE_URL=sqlite:///./chartnav.db` and
   `CHARTNAV_RUN_SEED=1`.
4. Polls `/health`.
5. Runs the same `scripts/smoke.sh` the backend-sqlite job uses.
6. Tears down.

If the image can't boot, serve `/health`, or pass smoke, the job fails.

## Out of scope this phase

- Image registry push (no target credentials by default).
- Kubernetes manifests, Helm charts, Terraform.
- TLS termination — expected to be handled by a reverse proxy in front.
- Secret management integration (AWS SM, Vault, etc.).
- Blue/green or rolling deployment orchestration.

Those are the next "hosted deploy" phase's job. The Docker seam is
real and ready to be plugged into any of them.
