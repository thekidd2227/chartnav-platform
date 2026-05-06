# ChartNav Pilot Deployment Guide

How to deploy ChartNav for a pilot. Three deployment modes are
supported today — pick the one that matches the pilot's data
posture and security posture.

This document does not invent infrastructure that does not exist.
Where a deployment detail is environment-specific or
practice-specific, it is marked **to confirm**.

This document does **not** include real secrets. Any secret value
shown is a placeholder.

---

## Deployment modes

| Mode                | Frontend host                          | Backend host             | Database                                      | Real PHI | Use for                                |
|---------------------|----------------------------------------|--------------------------|-----------------------------------------------|----------|----------------------------------------|
| `local`             | `vite dev` on `127.0.0.1:5173`         | `uvicorn` on `:8000`     | SQLite (`chartnav.db` in `apps/api/`)         | **No.**  | Engineering / fake-data demo.          |
| `staging`           | Vercel preview or self-hosted          | Compose stack on staging | Postgres (managed or self-hosted)             | **No.**  | Buyer demo, internal pre-pilot.        |
| `controlled-pilot`  | Vercel production project or self-host | Compose stack with backups + monitoring | Postgres with backups | **Only after** BAA + security review. | Single ophthalmology pilot practice.   |

`local` mode is the default. `staging` is documented in
`chartnav-clinical-workflow-demo-script.md` for buyer demos.
`controlled-pilot` is the only mode that may hold real PHI, and only
after the security review packet's gating items are met.

---

## Environment variables (no secrets)

These are the variables ChartNav reads. Names are stable; values
are environment-specific. **Never commit a real secret to the
repo** — they belong in your deployment platform's secret store.

### Backend

| Variable                                 | Purpose                                                       | Default                          | Notes                                          |
|------------------------------------------|---------------------------------------------------------------|----------------------------------|------------------------------------------------|
| `DATABASE_URL`                           | SQLAlchemy URL.                                               | `sqlite:///chartnav.db`          | Postgres in any PHI env.                       |
| `CHARTNAV_AUTH_MODE`                     | `header` (dev) or `bearer` (prod).                            | `header`                         | Use `bearer` for any PHI env.                  |
| `CHARTNAV_JWT_ISSUER`                    | OIDC issuer URL.                                              | unset                            | Required when `bearer`.                        |
| `CHARTNAV_JWT_AUDIENCE`                  | Expected `aud` claim.                                         | unset                            | Required when `bearer`.                        |
| `CHARTNAV_JWT_JWKS_URL`                  | JWKS endpoint for signing keys.                               | unset                            | Required when `bearer`.                        |
| `CHARTNAV_JWT_USER_CLAIM`                | Claim that maps to `users.email`.                             | `email`                          |                                                |
| `CHARTNAV_RATE_LIMIT_PER_MINUTE`         | Per-caller rate limit. `0` disables.                          | `120`                            | Disable for E2E only.                          |
| `CHARTNAV_CORS_ALLOW_ORIGINS`            | Comma-separated CORS origins.                                 | none                             | **No `*`.** Listed origins only.               |
| `CHARTNAV_AUDIT_RETENTION_DAYS`          | Days before `audit_prune` removes rows.                       | practice policy                  | **To confirm** per practice.                   |
| `CHARTNAV_STT_PROVIDER`                  | `stub` / `openai_whisper` / `none`.                           | `stub`                           | `stub` for fake-data demos.                    |
| `CHARTNAV_OPENAI_API_KEY`                | Whisper key when STT provider is `openai_whisper`.            | unset                            | **Only if** the practice has approved it.      |

### Frontend

| Variable           | Purpose                              | Default              | Notes                                  |
|--------------------|--------------------------------------|----------------------|----------------------------------------|
| `VITE_API_URL`     | Origin where the API answers.        | dev `:8000` proxy    | Set per environment.                   |
| `E2E_BASE_URL`     | Playwright override.                 | `127.0.0.1:5174`     | E2E only.                              |
| `E2E_API_URL`      | Playwright API override.             | `127.0.0.1:8001`     | E2E only.                              |

A complete inventory lives in `apps/api/app/config.py`. Update this
table when a new env var is added.

---

## Local demo deployment

```
make install           # creates venv + installs backend dev deps
make migrate           # apply alembic migrations to ./apps/api/chartnav.db
make seed              # idempotent fake-data seed
make boot              # API on :8000 (Ctrl-C to stop)
make web-dev           # web on :5173 (in a second shell)
```

Or boot both at once:

```
make dev
```

This is the **only** mode to use for fake-data demos. Reset between
demos with `make reset-db`.

---

## Staging pilot deployment

Staging is for buyer demos and pre-pilot dry-runs against fake data.

```
make staging-up        # boots the staging compose stack
make staging-verify    # runs smoke + observability checks
make staging-rollback  # rolls back the API image (TAG=v0.1.0)
make staging-down      # tears down the stack
```

Required staging env file: `infra/docker/.env.staging`. **Do not
check this file into the repo.** A redacted template lives at
`infra/docker/.env.staging.example` (**to confirm** — verify the
template exists and is current).

Staging must:

- run Postgres, not SQLite,
- run with `CHARTNAV_AUTH_MODE=bearer`,
- have a documented backup cadence (even though it is fake-data
  only),
- have monitoring or log shipping configured (**to confirm** with
  the operations owner).

---

## Controlled-pilot deployment

Controlled-pilot is the only mode that may hold real PHI. Before
this mode is used:

- BAA (or equivalent) executed.
- Security review completed against
  `chartnav-security-review-packet.md`.
- Authentication is `bearer` against a real OIDC issuer.
- Database is Postgres with documented backup cadence and tested
  restore.
- Monitoring + log shipping are in place.

Topology (**to confirm** per practice):

- Frontend host: Vercel production project, self-hosted under the
  practice's control, or a managed host approved in the security
  review.
- Backend host: Docker compose on a managed VM, managed Kubernetes,
  or another approved host.
- Database: Postgres on the host or a managed Postgres service the
  practice has approved.

Deployment is the same compose-based flow as staging, but with
production-grade env vars, backups, monitoring, and access control.

---

## Database migration expectations

- ChartNav uses Alembic. Every PR that adds a migration ships it
  under `apps/api/alembic/versions/`.
- Migrations are forward-only by design. Downgrades exist but are
  not used in the pilot path.
- `make migrate` is idempotent.
- `make reset-db` drops and re-seeds the **dev** SQLite DB. **Do
  not run `reset-db` against staging or controlled-pilot.**

To deploy a new migration in staging or controlled-pilot:

1. Confirm the new alembic revision is the head.
2. Take a backup of the database before the migration.
3. Run alembic upgrade against the target.
4. Verify with the smoke test.
5. Roll back via the documented rollback procedure if anything
   regresses.

---

## Seed / reset expectations

- `scripts_seed.py` is idempotent against any environment, but it
  is **only intended for local + staging fake-data flows**.
- Do **not** run the seed against a controlled-pilot database —
  the seed inserts demo organizations / patients / users which
  must not coexist with real practice data.
- Phase 13's demo guide reuses the seeded `demo-eye-clinic` /
  `PT-1001` patient. This is fake-data only.

---

## Vercel / frontend notes

The frontend deploys to Vercel for staging and (per practice
agreement) for controlled-pilot. Environment-specific
`VITE_API_URL` is required.

Per-PR Vercel preview deploys run automatically and are visible in
the PR check `Vercel Preview Comments`. Preview deploys are
fake-data only and never carry PHI.

---

## Backend / API deployment notes

The repo ships a production Docker image build target (`make
docker-build`) and a production compose stack (`make docker-up` /
`make docker-down`). Use these as the starting point for staging
and controlled-pilot.

The compose stack reads `infra/docker/.env.production` and brings up
API + Postgres. **To confirm** per practice: whether Postgres is
inside the compose stack or a managed external service.

---

## Postgres notes

- Use Postgres 14+ (matches CI's `Backend (Postgres) — parity proof`
  job).
- Cross-dialect parity is asserted on every PR by that CI job;
  every SQL statement uses portable constructs (`COALESCE`, named
  binds).
- Index on `(organization_id, *)` is the default for every clinical
  table; query patterns are org-scoped first.

---

## Smoke test checklist

Run after every deploy:

- [ ] `GET /health` returns 200.
- [ ] `GET /patients/{id}/eye-diagrams` returns 200 with the
      expected pilot user.
- [ ] `GET /patients/{id}/scribe-sessions` returns 200.
- [ ] `GET /patients/{id}/patient-summaries` returns 200.
- [ ] `GET /patients/{id}/pre-visit-brief` returns 200 (or
      `404 patient_not_found` for an unknown patient — test both).
- [ ] `GET /patients/{id}/provider-action-items` returns 200.
- [ ] Cross-org caller returns `404 patient_not_found` on each.
- [ ] Reviewer write returns `403 role_forbidden` on each.

Phase 12 already encodes these as the `TestRouteSanity` group plus
the cross-org and reviewer RBAC tests. CI's `Backend (SQLite) —
migrate · seed · test · smoke` job runs them on every PR.

---

## Rollback checklist

When a deploy regresses:

- [ ] Capture logs from the failing process (API, web, DB).
- [ ] Identify the breaking change (commit SHA / migration / env
      var).
- [ ] Roll back the API image to the prior tagged release
      (`make staging-rollback TAG=<prior>` for staging; the
      controlled-pilot equivalent depends on the host).
- [ ] If a migration is involved, restore from the pre-migration
      backup.
- [ ] Re-run the smoke test.
- [ ] File an incident note per `chartnav-support-runbook.md`.

---

## Branch / PR flow

- Every change lands on `main` via a PR.
- Every PR must pass all 8 CI checks (Backend SQLite, Backend
  Postgres parity, Frontend, E2E Playwright, Deploy config, Docker,
  Docs, Vercel preview).
- Squash-merge is the default.
- A merge to `main` is the trigger for a staging deploy (**to
  confirm** with the operations owner — verify the pipeline maps
  this).

---

## CI required checks

| Check | Purpose |
|---|---|
| Backend (SQLite) — migrate · seed · test · smoke | full pytest + alembic + seed + smoke against SQLite |
| Backend (Postgres) — parity proof | same migrations + tests against Postgres |
| Frontend — typecheck · test · build | tsc + vitest + vite build |
| E2E — Playwright against live stack | full e2e against booted API + web |
| Deploy config — compose + scripts validate | compose + script validation |
| Docker — production image builds | the prod image actually builds |
| Docs — regenerate HTML + PDF | the docs build pipeline |
| Vercel Preview Comments | preview deploy summary |

All 8 must be green before merge.

---

## Sign-off before pilot

Before a controlled-pilot deploy starts:

- [ ] Engineering lead has confirmed the deploy mode and env vars.
- [ ] Security/compliance owner has signed off on the security
      review packet items.
- [ ] Operations owner has signed off on backups + monitoring.
- [ ] Product owner has signed off on the pilot agreement.
- [ ] Practice's primary contact has signed off on the safety
      contract acknowledgment.

Sign-off is recorded out-of-repo (in the pilot agreement document
or the practice's preferred system). The repo only carries the
checklist.
