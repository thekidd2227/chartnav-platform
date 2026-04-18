# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 11: staging deployment + observability

### Step 1 — Baseline
- Head: `cbc5184` (real JWT + operational hardening).
- 48/48 pytest, 9/9 smoke green. Rate limiter / audit / structured logs all in place.

### Step 2 — Observability surfaces
- New `apps/api/app/metrics.py`: in-process Prometheus-text counters behind a threading lock. Counters are narrow on purpose:
  - `chartnav_requests_total{method,path,status}`
  - `chartnav_auth_denied_total{error_code}`
  - `chartnav_rate_limited_total`
  - `chartnav_audit_events_total{event_type}`
  - `chartnav_http_request_duration_ms_{sum,count}`
- `middleware.py::AccessLogMiddleware` now observes every response's `(method, path, status bucket, duration_ms)`.
- `middleware.py::RateLimitMiddleware` now bumps `rate_limited_total` before it writes the audit row.
- `audit.py::record(...)` now bumps `audit_events_total{event_type}` before inserting. Fails-closed still applies — metric or insert failure cannot mask the original 4xx.
- `main.py::_http_exception_handler` now bumps `auth_denied_total{error_code}` alongside the audit + WARNING log it already emits.
- New `GET /ready` — runs `SELECT 1` against the DB, returns `503 not_ready` if it fails. Designed to back container healthchecks.
- New `GET /metrics` — unauthed Prometheus text exposition. Documented as "internal network only" in `20-observability.md`.

### Step 3 — Staging deployment artifacts
- New `infra/docker/docker-compose.staging.yml`: pinned image (`CHARTNAV_IMAGE_TAG`), 127.0.0.1-bound ports (reverse proxy expected), DB healthcheck, API healthcheck on `/ready`, named volume for Postgres, `restart: unless-stopped`, every critical env var blocked with `${VAR:?msg}`.
- New `infra/docker/.env.staging.example`: the full staging contract (image owner/tag, DB creds, bearer auth, CORS, rate-limit, seed, API port). Annotated with guardrails ("NEVER put `*` in CORS", etc.).
- New runbook scripts:
  - `scripts/staging_up.sh` — validates compose config, optional `--pull`, then `up -d`.
  - `scripts/staging_verify.sh` — health + ready + metrics + unauth 401 + request-id round-trip + (header-mode only) full workflow mutation + audit signal assertion.
  - `scripts/staging_rollback.sh <prev_tag>` — atomic rewrite of `CHARTNAV_IMAGE_TAG` via python shim, `docker compose pull api`, `up -d api`, poll `/ready` ≤40s.
- All three scripts pass `shellcheck` clean.

### Step 4 — Release bundle expansion
- `scripts/release_build.sh` now also tars the staging artifact set (`docker-compose.staging.yml` + `.env.staging.example` + all three runbook scripts + docs 19/20/21) into `chartnav-staging-<version>.tar.gz`.
- `MANIFEST.txt` sha256s all three artifacts.
- `release.yml` attaches the staging tarball to tag-based GitHub Releases.

### Step 5 — CI: `deploy-config` job
- New `deploy-config` lane in `.github/workflows/ci.yml`:
  - `docker compose config` on all three compose files (dev / staging / prod).
  - `shellcheck` on every repo script.
- Runs on every push/PR. A broken compose file or sloppy script lands a red check before an operator ever hits `staging-up`.

### Step 6 — Makefile
- New targets: `staging-up`, `staging-verify`, `staging-rollback TAG=...`, `staging-down`.

### Step 7 — Tests
- New `apps/api/tests/test_observability.py` (3 tests):
  - `/ready` returns 200 with `database=ok`.
  - `/metrics` is Prometheus text, exposes the expected series, and reflects an `auth_denied` after an unauth `/me`.
  - `/metrics` `chartnav_rate_limited_total` ticks when a request crosses the configured limit.
- Full suite now **51/51 passing**.

### Step 8 — Verification
- `make verify` → 51 pytest + 9 smoke, clean teardown.
- Ran `staging_verify.sh` against a live `uvicorn` on `:8000` — all 9 assertions green including the audit/metrics check.
- `docker compose --env-file .env.staging.test config` against the staging compose file parses (normalized output prints cleanly).
- Both `ci.yml` and `release.yml` YAML parse.
- Docs regenerated.

### Step 9 — Hygiene
- `.gitignore` already excludes `*.db`, caches, `dist/release/`. Staging runbook mentions never committing `.env.staging` (real values); the `.example` file stays committed.

---

## Prior phases

- **Phase 10 — Real JWT bearer + operational hardening** (`cbc5184`)
- **Phase 9 — Playwright E2E + release pipeline** (`74fe8dd`)
- **Phase 8 — Create UI + vitest + frontend CI** (`f83d748`)
- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
