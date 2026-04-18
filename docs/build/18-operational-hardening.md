# Operational Hardening

Landing this phase gives ChartNav four production-baseline primitives
that every long-running service needs: **request correlation**,
**structured logs**, **audit trail for denied access**, and **abuse
protection**.

## 1. Request correlation

Middleware: `apps/api/app/middleware.py::RequestIdMiddleware`.

- Every request gets a `request_id` on `request.state`.
- Honors an inbound `X-Request-ID` if it's a reasonable length (≤ 64 chars); else generates a fresh UUID4 hex.
- Always echoed back as `X-Request-ID` on the response — including error responses (the exception handler copies it through).

## 2. Structured logging

Module: `apps/api/app/logging_config.py`.

- JSON-per-line to stdout via `JsonFormatter`.
- Fields: `timestamp` (UTC ISO8601), `level`, `logger`, `message`, plus any `extra={}` the caller passes.
- `AccessLogMiddleware` emits one line per request with `request_id`, `method`, `path`, `status`, `duration_ms`, `user_email` (from resolved caller), `organization_id`, `remote_addr`.
- The HTTP exception handler emits a `WARNING auth_denied` line for every denied auth/scoping response, attaching `error_code` and caller context.
- Uvicorn's access logger is quieted to avoid duplicating our access log.

Log sample (pretty-printed here for readability):
```json
{"timestamp":"2026-04-18T05:35:45Z","level":"INFO","logger":"chartnav.http",
 "message":"request","request_id":"494e2888ab414831805bf79cdefa7fc2",
 "method":"GET","path":"/me","status":401,"duration_ms":3.55,
 "user_email":null,"organization_id":null,"remote_addr":"testclient"}
```

## 3. Security audit trail

Module: `apps/api/app/audit.py`.
Migration: `b2c3d4e5f6a7 — add security_audit_events`.

### Schema
Table `security_audit_events`:
- `id`, `event_type`, `request_id`, `actor_email`, `actor_user_id`, `organization_id`, `path`, `method`, `error_code`, `detail`, `remote_addr`, `created_at`.
- Indexed on `event_type`, `actor_email`, `created_at`.

### What gets audited
The HTTP exception handler (`apps/api/app/main.py::_http_exception_handler`) writes an audit row when:
- The response is **401** or **403**, or
- The response `error_code` is in the `AUDITED_ERROR_CODES` set:
  `missing_auth_header`, `unknown_user`, `invalid_authorization_header`, `invalid_token`, `token_expired`, `invalid_issuer`, `invalid_audience`, `missing_user_claim`, `cross_org_access_forbidden`, `role_forbidden`, `role_cannot_create_encounter`, `role_cannot_create_event`, `role_cannot_transition`, `rate_limited`.

### What is NOT audited
- No raw JWT or `Authorization` header value.
- No password material (there isn't any, but explicitly).
- No successful requests — those belong in the access log.

### Never-throw guarantee
`audit.record(...)` swallows its own exceptions. A broken audit insert cannot mask the underlying 4xx the user actually hit.

## 4. CORS

- `allow_origins=["*"]` is gone.
- Driven by `CHARTNAV_CORS_ALLOW_ORIGINS` (comma-separated). Default covers Vite dev on `:5173` + E2E on `:5174`.
- In production, set it explicitly to the real frontend origin(s).
- Empty string → same-origin only.
- `allow_credentials=true`; `allow_headers` is limited to `Authorization`, `Content-Type`, `X-User-Email`, `X-Request-ID`; `expose_headers` exposes `X-Request-ID` so browsers can surface it for debugging.

## 5. Rate limiting

Middleware: `apps/api/app/middleware.py::RateLimitMiddleware`.

- In-memory sliding window (60s), per-process.
- Keyed on `(client_ip, path)`.
- `CHARTNAV_RATE_LIMIT_PER_MINUTE` (default 120). `0` disables.
- Protects `/me`, `/encounters`, `/organizations`, `/locations`, `/users` (and descendants). `/health` and `/` are never rate-limited.
- On limit exceed: `HTTP 429` with standardized envelope `{error_code: "rate_limited", reason: ...}` AND an audit row.
- Honest limitation: **per-process**, not distributed. Multi-worker / multi-node deployments should sit behind an edge limiter that coordinates globally. Documented in `12-runtime-config.md`.

## Config reference

| Env var                              | Default                                             |
|--------------------------------------|-----------------------------------------------------|
| `CHARTNAV_CORS_ALLOW_ORIGINS`        | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174` |
| `CHARTNAV_RATE_LIMIT_PER_MINUTE`     | `120`                                               |

See `12-runtime-config.md` for the full contract.

## Test coverage

`apps/api/tests/test_operational.py` (12 tests):

| Scenario                                                      | Result |
|---------------------------------------------------------------|--------|
| Inbound `X-Request-ID` round-trips                            | ✅ |
| Missing `X-Request-ID` → server generates one                 | ✅ |
| Error responses also carry `X-Request-ID`                     | ✅ |
| Audit row on `missing_auth_header`                            | ✅ |
| Audit row on `unknown_user`                                   | ✅ |
| Audit row on `cross_org_access_forbidden` (query lens)        | ✅ |
| Audit row on `role_cannot_create_encounter`                   | ✅ |
| No audit row on successful requests                           | ✅ |
| Rate limit returns **429 `rate_limited`** with envelope       | ✅ |
| Rate limit disabled when `CHARTNAV_RATE_LIMIT_PER_MINUTE=0`   | ✅ |
| CORS preflight allows a configured origin                     | ✅ |
| CORS preflight rejects an unconfigured origin                 | ✅ |

## Observability (phase 11 additions)

This baseline now includes a live observability surface — see
`20-observability.md`:

- `GET /ready` — DB-aware readiness. Backs the staging container `HEALTHCHECK`.
- `GET /metrics` — Prometheus text exposition. Counters cover request traffic, auth denials (by `error_code`), rate-limited responses, audit event writes (by `event_type`), and request latency sum/count.
- Middleware + exception handler now feed those counters as part of normal request handling. `audit.record` also bumps `chartnav_audit_events_total{event_type}` before the DB insert.

## Remaining gaps

- Rate limiter is in-memory per process — same caveat applies to the new metrics.
- Distributed tracing (OpenTelemetry) not wired yet.
- No log shipping / retention policy defined.
- Audit table has no retention/archival yet.
- No dashboards/alerts are shipped — `20-observability.md` documents the alert points, wiring is the operator's responsibility.
