# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 10: real JWT bearer + operational hardening

### Step 1 — Baseline
- Head: `74fe8dd` (Playwright E2E + release pipeline).
- 28 pytest + 12 vitest + 8 Playwright + 9 smoke all green.

### Step 2 — Real JWT bearer validation
- Added `pyjwt[crypto]>=2.8` to `pyproject.toml` dependencies (core, not an extra — bearer mode is a first-class path now).
- `apps/api/app/config.py` gains `jwt_user_claim`, `cors_allow_origins`, `rate_limit_per_minute`; claim default `email`; CORS default covers Vite dev on `:5173` and E2E on `:5174`.
- `apps/api/app/auth.py`:
  - Removed the 501 placeholder.
  - New `resolve_caller_from_bearer`: parses `Authorization: Bearer …`, runs `PyJWKClient(settings.jwt_jwks_url).get_signing_key_from_jwt(token)`, then `jwt.decode(...)` requiring `exp`, `iss`, `aud`; algorithm allowlist `RS256/384/512` + `ES256/384/512`.
  - Distinct error codes: `invalid_authorization_header`, `invalid_token`, `invalid_issuer`, `invalid_audience`, `token_expired`, `missing_user_claim`, `unknown_user`.
  - Module-level `_jwk_client` with `set_jwk_client(...)` test hook so tests inject a local RSA key; production uses `PyJWKClient` against the real JWKS URL.
  - `require_caller` now takes `Request` so it can stash the resolved `Caller` onto `request.state`. That's what lets the access log and audit writer reference the caller.

### Step 3 — Structured logging + request IDs
- New `apps/api/app/logging_config.py`: line-delimited JSON formatter, UTC timestamps, `extra={}` fields merged onto every record.
- New `apps/api/app/middleware.py::RequestIdMiddleware`: honors inbound `X-Request-ID` (≤ 64 chars), else generates a UUID4 hex. Echoed on every response including errors.
- `AccessLogMiddleware`: one `INFO request` line per response with `request_id`, `method`, `path`, `status`, `duration_ms`, `user_email`, `organization_id`, `remote_addr`.

### Step 4 — Audit trail
- New Alembic migration `b2c3d4e5f6a7 — add security_audit_events` with indexes on `event_type`, `actor_email`, `created_at`.
- New `apps/api/app/audit.py`:
  - `AUDITED_ERROR_CODES` set.
  - `record(...)` writes a row; never raises (internal exceptions are logged at ERROR and swallowed so they can't mask the underlying denial).
  - `query_recent(limit)` read helper used by tests and operator debugging.
- `apps/api/app/main.py` adds an `@app.exception_handler(HTTPException)` that:
  - Writes an audit row on any 401/403 or known-audited `error_code`.
  - Always copies `X-Request-ID` to the error response.
  - Emits a `WARNING auth_denied` structured log.

### Step 5 — CORS + runtime defaults
- Removed `allow_origins=["*"]`. Driven by `CHARTNAV_CORS_ALLOW_ORIGINS`.
- Narrowed `allow_methods` and `allow_headers` to the set the app actually uses.
- `expose_headers=["X-Request-ID"]` so browsers can surface it for debugging.

### Step 6 — Rate limiting
- `RateLimitMiddleware` — in-memory, per-process sliding 60-second window keyed on `(client_ip, path)`.
- Protects the authed path prefixes `/me`, `/encounters`, `/organizations`, `/locations`, `/users`. Leaves `/health` and `/` untouched.
- `CHARTNAV_RATE_LIMIT_PER_MINUTE` (default 120). `0` disables.
- On limit: writes an audit row with `event_type=rate_limited`, returns HTTP 429 with the standardized envelope.
- Limitation documented: per-process only; multi-worker deployments should add an edge limiter.

### Step 7 — Tests
- `apps/api/tests/test_auth_modes.py` rewritten for real JWT:
  - Local RSA keypair, sign tokens with `PyJWT`, inject a `_TestJWKSClient` stub via `set_jwk_client(...)`.
  - Added 9 bearer scenarios (valid, missing, malformed header, garbage, wrong iss, wrong aud, expired, unknown user, missing claim).
  - Fixed first-run bug: initial stub built a full PyJWK dict and hit a base64 encoding mismatch — now returns a minimal object carrying just `.key`.
- New `apps/api/tests/test_operational.py` (12 tests): request-id round-trip, request-id generation, request-id on 401, audit on missing-auth / unknown-user / cross-org / role-forbidden, no-audit on success, 429 rate-limit behavior, rate-limit disabled when 0, CORS allowed/disallowed preflight.
- Full suite: **48/48 passed**.

### Step 8 — CI
- CI already installs `[dev,postgres]` in all backend jobs. Because `pyjwt[crypto]` moved to the core `dependencies` block, every backend job (sqlite / postgres / e2e / docker-build) picks it up automatically. No workflow changes were necessary.
- Docs build still picks up the new sections via `scripts/build_docs.py`.

### Step 9 — Verification
- `make verify` (SQLite backend) → **48/48 pytest + 9/9 smoke green**.
- Header mode live `/me` still returns 200 for admin.
- YAML workflows still parse.
- Dev DB reset; audit log table shipped via new migration.
- `apps/api/.venv/bin/python scripts/build_docs.py` regenerated final HTML + PDF.

### Step 10 — Hygiene
- `.gitignore` already covers caches/`*.db`/release output.
- Migration is additive; Alembic head moves to `b2c3d4e5f6a7` — existing migrations untouched.

---

## Prior phases

- **Phase 9 — Playwright E2E + release pipeline** (`74fe8dd`)
- **Phase 8 — Create UI + vitest + frontend CI** (`f83d748`)
- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
