# Known Gaps & Verification Matrix

## Verification evidence — phase 11

### Local gates

| Gate                                      | Result |
|-------------------------------------------|--------|
| `make verify` (backend)                   | ✅ **51/51 pytest + 9/9 smoke** |
| `bash scripts/staging_verify.sh` (live API) | ✅ 9/9 assertions |
| `docker compose … config` (dev / staging / prod) | ✅ all three parse |
| `shellcheck` on all scripts               | ✅ clean (0 findings) |
| YAML parse on `ci.yml` + `release.yml`    | ✅ |
| `scripts/build_docs.py` → HTML + PDF      | ✅ regenerated |

### pytest summary (51)

| Suite                      | Count | Notes |
|----------------------------|:-----:|-------|
| `test_auth.py`             | 5     | header mode |
| `test_auth_modes.py`       | 11    | header + real JWT bearer |
| `test_rbac.py`             | 12    | role-gated writes + per-edge transitions |
| `test_scoping.py`          | 8     | org scoping + cross-org denial |
| `test_operational.py`      | 12    | request id, audit trail, rate limit, CORS |
| **`test_observability.py`**| **3** | **`/ready`, `/metrics` text, `/metrics` rate-limited counter** |

### Staging verify matrix (9)

| Assertion                                                      | Result |
|----------------------------------------------------------------|--------|
| `GET /health` 200                                              | ✅ |
| `GET /ready` 200 and `database=ok`                             | ✅ |
| `GET /metrics` 200 and exposes `chartnav_requests_total`       | ✅ |
| `GET /me` without auth → 401                                   | ✅ |
| `X-Request-ID` round-trips                                     | ✅ |
| Header-mode: `GET /me` with admin → 200                        | ✅ |
| Header-mode: `GET /encounters` with admin → 200                | ✅ |
| Header-mode: `POST /encounters/1/events` → 201 (or skip if no seed) | ✅ |
| `/metrics` reflects a `missing_auth_header` denial             | ✅ |

### Postgres parity
Not rerun this phase — no backend SQL changes since the last `make pg-verify` pass. Additive audit-table migration uses SA-portable constructs.

### Honest limitations
- CI has no `act`-style local workflow runner available in the dev shell; `deploy-config` was verified by running its component commands manually. The YAML parses cleanly.
- `staging_verify.sh` bearer path: the script can't mint real tokens, so in `CHARTNAV_AUTH_MODE=bearer` it only covers unauth surfaces + observability. The manual bearer path is documented in `21-staging-runbook.md`.
- Metrics & rate limiter are **per-process**; multi-worker deployments will see counters and limits split per worker. Edge aggregation is required for coordinated behavior.

## Real gaps (prioritized for next phase)

1. **No OpenTelemetry / distributed tracing** — correlation is by `request_id` only.
2. **No log shipping / retention defined** — stdout JSON is ready; operators wire the collector.
3. **No audit-table archival / retention policy.**
4. **Metrics are per-process** — multi-worker or multi-node needs a proper Prometheus multiprocess mode or a push gateway.
5. **Rollback cannot reverse destructive migrations** (forward-only policy; documented in `21-staging-runbook.md`).
6. **No automated staging deploy from CI** — tag pushes publish the image but the `make staging-up` handoff is manual. That's intentional until there's a protected target + secrets wired.
7. **No production equivalent of `staging_verify.sh`** yet. Extending it is trivial once the prod target exists.
8. **No JWKS-rotation test** — PyJWKClient caches aggressively; rotation is handled by the IdP.
9. **No refresh-token / revocation flow.**
10. **No signing / SBOM / provenance** on release artifacts.
11. **`/organizations`, `/locations`, `/users`** still read-only.
12. **`users.role`** free VARCHAR at DB layer.
13. **No pagination** on `GET /encounters`.
14. **Free-form `event_data`** — no per-event_type schema.
15. **No visual-regression / a11y audits** on the frontend.
16. **pytest matrix on Postgres** not wired — fixture env-driven, ready to flip.
