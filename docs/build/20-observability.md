# Observability

ChartNav's observability baseline is honest: three surfaces (`/health`, `/ready`, `/metrics`), one structured log stream, and one audit table. No platform fantasy.

## Surfaces

### `GET /health`  — liveness
Cheap. Never touches the DB. Use it for load-balancer keepalives where "the process is answering" is enough.

```
200 {"status":"ok"}
```

### `GET /ready`  — readiness
Runs `SELECT 1` against the database. Use it for orchestrator healthchecks where you want to gate traffic on DB reachability. `503 not_ready` if the DB is unreachable.

```
200 {"status":"ready","database":"ok"}
```

In `infra/docker/docker-compose.staging.yml`, the API container's `HEALTHCHECK` targets `/ready` — not `/health` — because a running uvicorn with a broken DB connection is worse than no uvicorn.

### `GET /metrics`  — Prometheus text exposition
Unauthed. Exposed on the internal network only; restrict at the edge if you must expose publicly (see below).

Counters emitted:

| Metric                                            | What it answers |
|---------------------------------------------------|-----------------|
| `chartnav_requests_total{method,path,status}`     | Traffic by (method, path, status bucket `1xx..5xx`). |
| `chartnav_auth_denied_total{error_code}`          | Denied auth/scoping attempts, keyed on the stable error codes from the `{error_code, reason}` envelope. |
| `chartnav_rate_limited_total`                     | 429 `rate_limited` responses. |
| `chartnav_audit_events_total{event_type}`         | Audit rows written, by event type. |
| `chartnav_http_request_duration_ms_sum`           | Cumulative request latency, milliseconds. |
| `chartnav_http_request_duration_ms_count`         | Sample count matching the sum. Divide for a mean. |

Honest caveats:
- **In-process, single-worker.** Same caveat as the rate limiter. Multi-worker uvicorn = each worker scrapes its own counters. A proper metrics lib backed by Prometheus multiprocess mode is the next step if that becomes a real problem.
- No histograms / percentiles. `sum + count` is the honest minimum; percentiles lie when they're synthesized from one bucket.

## Structured logs

All logs are line-delimited JSON on stdout. Ship them with whatever collector the deploy target uses (compose log driver, cloudwatch agent, vector, fluent-bit — the app doesn't care).

### Access log (INFO, `logger=chartnav.http`)
Emitted once per request:

```json
{
  "timestamp": "2026-04-18T15:22:10Z",
  "level": "INFO",
  "logger": "chartnav.http",
  "message": "request",
  "request_id": "a1b2c3...",
  "method": "POST",
  "path": "/encounters/1/status",
  "status": 200,
  "duration_ms": 7.42,
  "user_email": "clin@chartnav.local",
  "organization_id": 1,
  "remote_addr": "10.0.0.42"
}
```

### Auth-denied log (WARNING, `logger=chartnav`)
Emitted alongside every audited denial — mirror image of the audit row:

```json
{
  "timestamp": "2026-04-18T15:22:10Z",
  "level": "WARNING",
  "logger": "chartnav",
  "message": "auth_denied",
  "request_id": "a1b2c3...",
  "path": "/me",
  "method": "GET",
  "status": 401,
  "error_code": "missing_auth_header",
  "user_email": null,
  "organization_id": null
}
```

### Request failure log (ERROR)
Uncaught exceptions surface with a stack trace via the access-log middleware. Always carries `request_id`.

### Fields guaranteed across all records

- `timestamp` — UTC ISO8601
- `level` — standard logging level
- `logger`
- `message`
- `request_id` — when the log is request-scoped

### Collection notes

- Docker compose: default stdout goes to the `json-file` driver unless you override `logging.driver` on the service. For staging, point at your collector (`loki`, `fluent-bit`, etc.) via a compose override file; the app emits valid JSON already.
- Do not parse with `grep` in production. Ship to a log store and query by `request_id`, `error_code`, or `user_email`.

## Audit table (`security_audit_events`)

See `18-operational-hardening.md` for the schema. The audit table is a durable peer to the logs: logs answer "what happened and when", the audit table answers "what denied-access attempts, who did them, to which org, how often". They're not redundant — logs churn, audit rows persist.

Query examples:

```sql
-- recent denials by error_code
SELECT error_code, COUNT(*) AS n
FROM security_audit_events
WHERE created_at > now() - interval '24 hours'
GROUP BY error_code
ORDER BY n DESC;

-- repeated cross-org attempts from one actor
SELECT actor_email, path, COUNT(*) AS n
FROM security_audit_events
WHERE event_type = 'cross_org_access_forbidden'
  AND created_at > now() - interval '7 days'
GROUP BY actor_email, path
HAVING COUNT(*) >= 3;
```

## What to check during staging smoke

The one-shot is `make staging-verify` (see `21-staging-runbook.md`). Interactively, an operator should look at:

1. **Liveness**: `curl -fsS http://.../health`  →  `200`.
2. **Readiness**: `curl -fsS http://.../ready`  →  `200 database=ok`. If this fails, API logs will explain; `docker compose logs db` will confirm.
3. **Request id round-trip**: `curl -I -H "X-Request-ID: probe-$$" http://.../health` — response must carry the same id back.
4. **Auth surface**:
   - `curl -i http://.../me` without auth → 401 + a `missing_auth_header` entry on the next `/metrics` scrape.
   - `GET /metrics` contains `chartnav_auth_denied_total{error_code="missing_auth_header"}`.
5. **Rate-limit sanity**: quickly spam `GET /me` to exceed the configured `CHARTNAV_RATE_LIMIT_PER_MINUTE`; expect a 429 and `chartnav_rate_limited_total` to tick up.
6. **Audit row check**: `docker compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT event_type, COUNT(*) FROM security_audit_events GROUP BY 1 ORDER BY 2 DESC;"`.

## Alert points (contract, not implementation)

When an operator wires alerting, these are the knobs that carry real meaning:

| Signal                                                            | Meaning                                                   |
|-------------------------------------------------------------------|-----------------------------------------------------------|
| `/ready` failing for >1 minute                                    | DB connection lost or pool exhausted.                     |
| `chartnav_auth_denied_total{error_code="invalid_token"}` burst     | IdP trouble or attack traffic hitting `Authorization:`.   |
| `chartnav_auth_denied_total{error_code="cross_org_access_forbidden"}` spike | Misconfigured client, token reuse across orgs, or probing. |
| `chartnav_rate_limited_total` steep climb                         | Abuse or a stuck client.                                  |
| Audit table growth rate ≫ steady-state                            | Investigate; correlate with the two metrics above via request_id. |

This phase does not ship dashboards or alert rules. The plumbing is in place; wire them in your observability platform of choice (Grafana/Datadog/CloudWatch/etc.).

## Audit retention (phase 15)

The app no longer has to silently prune old audit rows to stay bounded.
Operators run `scripts/audit_retention.py` (or `make audit-prune`)
against the API venv; the script honors `CHARTNAV_AUDIT_RETENTION_DAYS`
(default `0` = never prune) and can be invoked with `--dry-run` for a
report-only pass. JSON output covers `matched` / `deleted` / `cutoff`.
A nightly cron is the expected wiring. Full framing in
`25-enterprise-quality-and-compliance.md`; cron example in
`21-staging-runbook.md`.

This keeps two concerns explicit: (1) the app never changes audit
state outside of a request-scoped write path, and (2)
compliance-facing retention lives in ops with a scripted contract
instead of hidden behavior.

## Remaining gaps

- No tracing / span propagation yet (OpenTelemetry is the natural next layer).
- Metrics are per-process.
- Retention is handled by an operator-invoked helper, archival-to-S3 and SIEM shipping are still ops infra's job.
