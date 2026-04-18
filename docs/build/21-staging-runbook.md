# Staging Runbook

Operator-grade playbook. Every command is real and reproducible. No magic.

---

## 0. Prerequisites

- Docker + `docker compose` v2.
- Access to `ghcr.io/<owner>/chartnav-api` (at minimum anonymous pull; the image is published public on release).
- A JWKS URL from your IdP (for bearer mode).
- Ability to place DNS / reverse-proxy config in front of port 8000 on the staging host. The compose file binds to `127.0.0.1:8000` — your reverse proxy is expected to handle public exposure and TLS.

## 1. First-time provisioning

```bash
# on the staging host
git clone https://github.com/thekidd2227/chartnav-platform.git
cd chartnav-platform
cp infra/docker/.env.staging.example infra/docker/.env.staging
# edit .env.staging with real values — see docs/build/19-staging-deployment.md
```

Validate before starting anything:

```bash
docker compose \
  --env-file infra/docker/.env.staging \
  -f infra/docker/docker-compose.staging.yml \
  config >/dev/null
```

Failure here (`required variable X is missing`) is good: the compose file intentionally `${VAR:?}`-blocks on every critical var.

## 2. Deploy

```bash
make staging-up          # == bash scripts/staging_up.sh
make staging-verify      # == bash scripts/staging_verify.sh
```

Expected finish:
```
==> staging verify: PASS
```

If verify fails at `/ready`, the API can't reach the DB. Check in order:
1. `docker compose -f infra/docker/docker-compose.staging.yml ps` — db should be `healthy`.
2. `docker compose -f infra/docker/docker-compose.staging.yml logs --tail=100 db`.
3. `docker compose -f infra/docker/docker-compose.staging.yml logs --tail=100 api`.

If verify fails at the auth-denial metrics check, the app is up but the exception handler didn't record the denial — check the API container's logs for a Python traceback.

## 3. Exercising bearer mode

`staging_verify.sh` only drives `/me` + `/encounters` as an authed caller when `CHARTNAV_AUTH_MODE=header`. In bearer mode the script stops after unauth surfaces + observability checks, because it cannot mint tokens.

Manual path:

1. Pull a real JWT from your IdP (e.g. `auth0` CLI, `okta` CLI, a curl against the IdP's token endpoint).
2. Confirm the token's `email` claim (or whatever you set `CHARTNAV_JWT_USER_CLAIM` to) matches a row in `users`.
3. Run:
   ```bash
   curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/me | jq
   curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/encounters | jq 'length'
   ```
4. Watch `docker compose logs -f api` in another terminal; the access log should show `user_email` and `organization_id`.

If bearer validation fails, the `error_code` in the 401 body pinpoints the reason — `invalid_token`, `invalid_issuer`, `invalid_audience`, `token_expired`, `missing_user_claim`, `unknown_user`. Every one of those also writes a `security_audit_events` row.

## 4. Rollback

The contract: "image tag rollback restores behavior, not data."

```bash
# Pin a previously-published tag and restart the API only.
make staging-rollback TAG=v0.0.9
make staging-verify
```

What the script does (honest):
1. Rewrites `CHARTNAV_IMAGE_TAG=` in `infra/docker/.env.staging`.
2. `docker compose pull api`.
3. `docker compose up -d api`.
4. Polls `/ready` for ≤40s.

What it does **not** do:
- Reverse any migrations. If release `N` applied a destructive migration (dropped a column, dropped a table), going back to `N-1`'s image will **not** restore data. Forward-only migrations are the policy — plan accordingly before tagging a release.
- Blue/green. There's one API replica. During the restart, `/ready` will go red for a handful of seconds; the reverse proxy should drain accordingly.

If rollback fails `/ready`, you're worse off than before rollback and need to triage:
1. `docker compose logs --tail=200 api`.
2. Pin the **current broken** tag back (`make staging-rollback TAG=<the tag you started from>`) — sometimes the issue is "the image didn't actually pull".
3. If the DB is broken (not the image), the recovery path is a DB restore from your backup. That is out-of-band of this repo; document it in your infra runbook.

## 5. Health / observability quick checks

```bash
# liveness + readiness
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready

# metrics snapshot
curl -fsS http://127.0.0.1:8000/metrics | grep -E '^(chartnav_requests_total|chartnav_auth_denied_total|chartnav_rate_limited_total|chartnav_audit_events_total)'

# recent audit rows (inside the db container)
docker compose -f infra/docker/docker-compose.staging.yml \
  --env-file infra/docker/.env.staging \
  exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT id, event_type, actor_email, path, error_code, created_at \
      FROM security_audit_events ORDER BY id DESC LIMIT 20;"

# follow logs (JSON; pipe through jq for readability)
docker compose -f infra/docker/docker-compose.staging.yml \
  --env-file infra/docker/.env.staging \
  logs -f api | sed 's/^[^{]*//' | jq -cR 'fromjson? | select(.) | .'
```

See `20-observability.md` for the full field reference.

## 6. Teardown

```bash
# soft — keep the DB volume
make staging-down

# hard — DROP ALL DATA
cd infra/docker && docker compose \
  --env-file .env.staging -f docker-compose.staging.yml down -v
```

Never run the hard teardown on a shared staging host without confirming with whoever else uses it.

## 7. Common failures, honest fixes

| Symptom                                            | Likely cause                                                     | Fix                                                              |
|----------------------------------------------------|------------------------------------------------------------------|------------------------------------------------------------------|
| `required variable CHARTNAV_JWT_JWKS_URL is missing`| `CHARTNAV_AUTH_MODE=bearer` but JWT config blank in `.env.staging` | Fill in the three JWT vars or set `AUTH_MODE=header` for triage. |
| `db` never becomes healthy                         | Volume permissions / old volume with wrong password              | `docker volume rm docker_chartnav_staging_pgdata` **iff** you accept data loss. |
| Smoke passes but app UX is broken                  | Stale frontend bundle vs. backend contract                       | Re-pin frontend asset (out of scope of this compose) — the API is fine. |
| 429 everywhere                                     | `CHARTNAV_RATE_LIMIT_PER_MINUTE` too low for a load test          | Temporarily raise; remember it's per-process, per-path, per-IP. |
| `invalid_issuer`/`invalid_audience` flood          | Wrong `CHARTNAV_JWT_ISSUER` or `_AUDIENCE` vs. the IdP's tokens   | Inspect a sample token's `iss` / `aud`; align env.              |

## 8. Audit retention cron (phase 15)

ChartNav never silently prunes audit rows. Retention is explicit,
operator-invoked, and scripted:

```bash
# dry-run against current env default
make audit-prune ARGS="--dry-run"

# explicit threshold, report-only
python scripts/audit_retention.py --days 90 --dry-run

# actually delete
python scripts/audit_retention.py --days 90
```

The helper reads `CHARTNAV_AUDIT_RETENTION_DAYS` (default `0` =
never) when `--days` is omitted. Output is JSON: `status`,
`retention_days`, `cutoff`, `matched`, `deleted`, `dry_run`.

A typical cron hook on the staging host:

```cron
# every day at 02:30 UTC, prune anything older than 90 days
30 2 * * *  cd /srv/chartnav && \
  apps/api/.venv/bin/python scripts/audit_retention.py --days 90 \
    >> /var/log/chartnav/audit-prune.jsonl 2>&1
```

Check the last run by tailing the log or by inspecting the
`security_audit_events` row count. Full framing in
`25-enterprise-quality-and-compliance.md` and `20-observability.md`.

## 9. What this runbook intentionally does not cover

- Backup & restore. That's your infra concern; the app is stateless beyond Postgres.
- DNS / TLS / edge routing.
- Disaster recovery beyond image rollback.
- Secret rotation. Rotate in your secret store, then `make staging-up` re-reads env on container restart.

When any of these become first-class ChartNav concerns, they graduate to their own build-log phase and doc section.
