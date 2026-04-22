# Phase 60 — Production Deployment, Secrets, Storage, and Go-Live

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`
Alembic head: `e1f2a304150f`

## What this document is

The single authoritative runbook for standing a ChartNav instance
up in production. Written for a clinic IT/admin team with Docker
and a Postgres-capable host. Not a platform blueprint, not a
Kubernetes story, not a marketing pitch — one deterministic path.

## Stack reality

- **Backend**: FastAPI + SQLAlchemy, served by uvicorn.
- **Database**: Postgres 16 (dev uses SQLite; production must be
  Postgres — enforced by `deploy_preflight`).
- **Frontend**: static Vite/React build, served behind a reverse
  proxy or a CDN.
- **Transport**: Docker Compose (`infra/docker/docker-compose.prod.yml`).
- **Image hosting**: GHCR (`ghcr.io/${CHARTNAV_IMAGE_OWNER}/chartnav-api`).
- **No**: Kubernetes, Helm, Terraform, Electron, Tauri.

## Production env / secrets contract

Single source of truth: `infra/docker/.env.prod.example`. Copy to
`infra/docker/.env.prod` and fill in the REQUIRED fields.

**REQUIRED** (deploy_preflight refuses without these, or with
insecure defaults in production):

| key | purpose |
|---|---|
| `CHARTNAV_IMAGE_OWNER` | GHCR owner for the API image |
| `CHARTNAV_IMAGE_TAG` | pinned image tag (rollback = change this) |
| `CHARTNAV_ENV` | must be `production` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | compose Postgres credentials |
| `CHARTNAV_AUTH_MODE` | must be `bearer` in production |
| `CHARTNAV_JWT_ISSUER`, `CHARTNAV_JWT_AUDIENCE`, `CHARTNAV_JWT_JWKS_URL` | JWT validation |
| `CHARTNAV_CORS_ALLOW_ORIGINS` | explicit frontend origin; must NOT include localhost |

**OPTIONAL** (sensible defaults provided):

| key | default | notes |
|---|---|---|
| `CHARTNAV_JWT_USER_CLAIM` | `email` | |
| `CHARTNAV_RATE_LIMIT_PER_MINUTE` | `120` | 0 disables |
| `CHARTNAV_AUDIT_RETENTION_DAYS` | `0` | 0 = retain forever |
| `CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS` | _unset_ | JSON keyring for signed bundles |
| `CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY` | _unset_ | legacy single-key env; auto-aliased as `default` |
| `CHARTNAV_PLATFORM_MODE` | `standalone` | `integrated_readthrough` / `integrated_writethrough` |
| `CHARTNAV_INTEGRATION_ADAPTER` | `stub` | `fhir` for real FHIR read-through |
| `CHARTNAV_FHIR_*` | _unset_ | required only when adapter=`fhir` |
| `CHARTNAV_AUDIO_*` | dev defaults | used by audio intake |
| `CHARTNAV_STT_PROVIDER` | `stub` | `openai_whisper` for real STT |
| `CHARTNAV_RUN_SEED` | `0` | set to `1` on first-install only |

### Secrets handling

- NEVER commit `.env.prod` with real values. Use your org's secret
  store (AWS SSM / HashiCorp Vault / Azure Key Vault / Doppler /
  equivalent) to materialise it at deploy time.
- Process secrets (HMAC keyring, JWT signing material at your IdP,
  any bearer tokens for FHIR adapters) MUST live in env, not in the
  per-org `organizations.settings` JSON — that JSON is readable to
  org admins and would leak material cross-tenant.

## Storage contract

| concern | location | backed up by |
|---|---|---|
| Primary DB | Docker volume `chartnav_pgdata` (mounted at `/var/lib/postgresql/data` inside the `db` service) | **your infrastructure team** — Postgres-level backup (pg_dump / WAL archive / snapshot) is required; ChartNav does not operate a DB backup service |
| Audio uploads | `CHARTNAV_AUDIO_UPLOAD_DIR` on the API container filesystem | mount a persistent volume at this path if audio intake is in use |
| Audit sink (jsonl mode) | file path on the API container filesystem | mount a persistent or durable volume at the configured path |
| **Practice backup bundle** (Phase 58) | **operator's local disk** (browser Save-As) | operator — this is the survivable copy for the "delete-and-reinstall" flow |
| Evidence export snapshots | Postgres row (`note_export_snapshots.artifact_json`) | Postgres backup above |
| Evidence chain events | Postgres row (`note_evidence_events`) | Postgres backup above |

**Unsupported**:

- running with SQLite in production (`DATABASE_URL=sqlite://...`) —
  preflight refuses.
- sharing the compose volume across hosts via an unsupported
  network filesystem without proper locking.
- relying on the ChartNav practice backup as a substitute for
  Postgres backup. The practice backup is for **delete-and-reinstall
  recovery** (a one-shot restore into an empty org), not for
  point-in-time recovery. Postgres backups are still required.

## Install sequence

One-time, on a host with Docker and Docker Compose v2:

```bash
git clone https://github.com/thekidd2227/chartnav-platform.git
cd chartnav-platform
make install                                  # venv + backend deps
cp infra/docker/.env.prod.example infra/docker/.env.prod
$EDITOR infra/docker/.env.prod                # fill REQUIRED fields
make deploy-preflight ENV_FILE=infra/docker/.env.prod
make prod-bootstrap ENV_FILE=infra/docker/.env.prod
```

`prod-bootstrap` runs preflight, `docker compose up -d`, waits for
`/health`, then runs `enterprise_validate`. Output ends with an
admin next-steps block.

Alembic runs inside the API container on start, so schema is at
head for the pinned image tag automatically. If you must run
migrations outside the container (e.g. in a maintenance window
with the API stopped), use:

```bash
docker compose --env-file infra/docker/.env.prod \
  -f infra/docker/docker-compose.prod.yml \
  run --rm api alembic upgrade head
```

## Upgrade sequence

For a new release tag `vX.Y.Z` that contains new migrations:

```bash
# 1. Snapshot first. Postgres backup + practice backup for every org.
#    Postgres: your infra team runs pg_dump / WAL archive.
#    Per-org:  Admin → Backup → Create backup (for each org).
# 2. Pin the new tag.
$EDITOR infra/docker/.env.prod        # CHARTNAV_IMAGE_TAG=vX.Y.Z
# 3. Preflight still green.
make deploy-preflight ENV_FILE=infra/docker/.env.prod
# 4. Bring up with the new tag; alembic runs on start.
cd infra/docker
docker compose --env-file .env.prod -f docker-compose.prod.yml pull api
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d api
# 5. Validate.
make enterprise-validate URL=http://localhost:8000
```

## Rollback sequence

For image-only rollback (schema-compatible tags):

```bash
make prod-rollback TAG=vA.B.C ENV_FILE=infra/docker/.env.prod
```

`scripts/deploy_rollback.sh` pins the older tag, restarts, waits
for `/health`, and runs `enterprise_validate`.

**If the newer tag advanced the schema**, image-only rollback is
not safe — a newer-schema DB can reject operations expected by the
older API. Use the recovery flow instead.

## Recovery / disaster-reinstall sequence

When the DB is unreliable OR an upgrade went badly and image
rollback is not enough:

```
1. Operator creates a practice backup for each org
     (Admin → Backup → Create backup; saves .json locally).
2. Stop and remove the compose stack:
     docker compose -f infra/docker/docker-compose.prod.yml down -v
3. Reinstall from a clean state (install sequence above).
     Optionally pin CHARTNAV_IMAGE_TAG to the known-good older tag.
4. Log in to the fresh empty org.
5. Admin → Backup → Restore backup: upload the saved .json.
6. Confirm counts + a few spot checks.
```

See `docs/build/59-practice-backup-restore-reinstall.md` for the
full restore contract.

## Post-deploy validation

Enterprise validation runs these checks (all via
`scripts/enterprise_validate.sh`):

1. `/health` returns 200.
2. `/capability/manifest` returns 200 and contains
   `schema_version`.
3. `/deployment/manifest` returns 200 and contains `alembic_head`.
4. Reported `alembic_head` matches the newest revision file in
   the repo (catches mounting the wrong volume or a partially
   applied migration).
5. *(opt-in)* When `CHARTNAV_VALIDATE_ADMIN_EMAIL` is set,
   evidence chain integrity is re-verified via
   `/admin/operations/evidence-chain-verify`.

Exit code is non-zero on any failure with a colorised summary.

## Go-live checklist

Print this, work top-down. Every box must be ticked before
accepting clinical traffic.

### Identity

- [ ] IdP configured and issuing JWTs with the configured `iss`
      and `aud`.
- [ ] JWKS endpoint reachable from the API host.
- [ ] `CHARTNAV_AUTH_MODE=bearer` (preflight: OK).
- [ ] A seeded admin user exists for every org that will sign in.
- [ ] For every org with physicians, at least one user has
      `is_authorized_final_signer=true` (Wave 7 contract).

### Runtime health

- [ ] `/health` returns 200.
- [ ] `/deployment/manifest` alembic_head matches repo head.
- [ ] `/capability/manifest` returns your expected integration
      adapter and platform mode.
- [ ] API logs rotate and do not include any patient-identifiable
      payloads.

### Evidence operations

- [ ] Evidence signing mode decided (off OR hmac_sha256 with
      keyring set).
- [ ] If signing is on: `CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS` is
      populated with at least the key_id named by every org's
      `evidence_signing_key_id` (operations overview shows
      `evidence_signing_inconsistent == 0`).
- [ ] Evidence sink destination decided (disabled OR jsonl OR
      webhook).
- [ ] If sink is on: `/admin/operations/evidence-sink/test` probe
      returns `ok: true` for every configured org.
- [ ] Retention windows decided:
      `export_snapshot_retention_days` (floor 90) and
      `evidence_sink_retention_days` (floor 7). Null is fine if
      your policy is retain-forever.

### Backup destination

- [ ] Postgres backup strategy confirmed with your infra team
      (pg_dump cron / WAL archive / snapshot tool) — this is the
      authoritative DR path; the practice backup does not replace
      it.
- [ ] Practice backup flow verified end-to-end:
      1. Admin → Backup → Create backup; saves .json locally.
      2. Admin → Backup → Restore validates + dry-runs into an
         empty test org.
- [ ] Backup files stored off this host.

### Admin verification

- [ ] Admin panel opens under every admin's account.
- [ ] Audit log is writing rows.
- [ ] Operations overview Infrastructure bucket reports 0 open
      issues, OR the counts you expect from a fresh install
      (typically `security_policy_unconfigured=1` until you
      configure session timeouts + audit sink + admin allowlist).
- [ ] KPI scorecard renders (empty is fine on a fresh install).

### Final cut-over

- [ ] Notify the clinic that cut-over is starting.
- [ ] Route the frontend domain at the API host.
- [ ] Run `make enterprise-validate URL=<prod-url>` one last time.
- [ ] Confirm with a clinician: sign-in → ingest a test
      transcript → sign → final-approve → export → evidence bundle
      download. Delete the test data before live use.

## Known limits

- The practice backup does NOT include evidence chain events
  (intentional — chain continuity cannot transplant). If you do a
  restore-to-new-instance, the evidence chain restarts from that
  point. Prior bundles remain verifiable off-server against the
  HMAC keyring.
- Audit retention sweep (`scripts/audit_retention.py`) is manual.
  Set a cron on your host if you need enforced pruning.
- No built-in TLS termination. Put the API behind your reverse
  proxy / CDN and terminate TLS there. The API trusts
  `X-Forwarded-For` / `X-Forwarded-Proto` per the middleware in
  `apps/api/app/middleware.py`.
- `make docker-up` uses no `--env-file`; it is intended for a
  local parity test with dev-safe defaults. Production deploys
  MUST use `--env-file infra/docker/.env.prod`.
