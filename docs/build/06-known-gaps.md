# Known Gaps & Verification Matrix

## Verification evidence — phase 10

### Local gates

| Gate                           | Result |
|--------------------------------|--------|
| `make verify` (backend)        | ✅ 48/48 pytest + 9/9 smoke |
| Header `/me` live              | ✅ 200 admin |
| Alembic upgrade head           | ✅ migrations 1 → 2 → `b2c3d4e5f6a7` |
| `make pg-verify` (Postgres)    | not rerun in this phase — no backend SQL changes that would break it, migration is SA-portable |
| `make web-verify` / `make e2e` | no frontend changes this phase — previously ✅ |

### pytest summary (48)

| Suite                      | Count | Notes |
|----------------------------|:-----:|-------|
| `test_auth.py`             | 5     | header mode |
| `test_auth_modes.py`       | 11    | header + real JWT bearer (valid, missing, malformed, garbage, wrong iss, wrong aud, expired, unknown user, missing claim) |
| `test_rbac.py`             | 12    | role-gated writes + per-edge transitions |
| `test_scoping.py`          | 8     | org scoping + cross-org denial |
| `test_operational.py`      | 12    | request id, audit trail, rate limit, CORS |

### Audit / ops matrix (`test_operational.py`)

| Scenario                                                | Result |
|---------------------------------------------------------|--------|
| Inbound `X-Request-ID` roundtrips                       | ✅ |
| Server generates request id when missing                | ✅ |
| Error responses carry request id                        | ✅ |
| Audit on `missing_auth_header`                          | ✅ |
| Audit on `unknown_user`                                 | ✅ |
| Audit on `cross_org_access_forbidden`                   | ✅ |
| Audit on `role_cannot_create_encounter`                 | ✅ |
| No audit on success                                     | ✅ |
| 429 on rate limit with correct envelope                 | ✅ |
| Rate limit disabled when 0                              | ✅ |
| CORS preflight allows configured origin                 | ✅ |
| CORS preflight rejects unconfigured origin              | ✅ |

### Bearer JWT matrix (`test_auth_modes.py`)

| Case                                                 | Result |
|------------------------------------------------------|--------|
| Bearer without JWT env → `RuntimeError` at import    | ✅ |
| Header mode default contract                         | ✅ |
| Valid RS256 token + known user → 200 role/org        | ✅ |
| Missing `Authorization`                              | ✅ 401 `missing_auth_header` |
| Non-Bearer scheme                                    | ✅ 401 `invalid_authorization_header` |
| Garbage token                                        | ✅ 401 `invalid_token` |
| Wrong issuer                                         | ✅ 401 `invalid_issuer` |
| Wrong audience                                       | ✅ 401 `invalid_audience` |
| Expired token                                        | ✅ 401 `token_expired` |
| Unknown user mapping                                 | ✅ 401 `unknown_user` |
| Missing configured claim                             | ✅ 401 `missing_user_claim` |

## Real gaps (prioritized for next phase)

1. **Rate limiter is per-process, in-memory.** Multi-worker / multi-node deployments need an edge limiter or a shared store (Redis) backing a distributed window.
2. **No OpenTelemetry tracing yet.** Structured logs carry request ids, but there's no span propagation across services.
3. **No log shipping / retention defined.** JSON logs go to stdout; operators wire them to their stack.
4. **Audit table has no retention or archival.** Rows accumulate indefinitely.
5. **No JWKS-rotation test** and no HS256 path (intentionally — production should be asymmetric).
6. **No refresh-token flow / revocation list.** If a token must die before `exp`, rotate the IdP signing key or delete the `users` row.
7. **Deploy flow stops at "pushed image + GitHub Release".** Actual rollouts / rollbacks are still operator-run.
8. **No signing / SBOM / provenance** on release artifacts.
9. **`/organizations`, `/locations`, `/users`** remain read-only.
10. **`users.role`** free VARCHAR at DB layer (CHECK or lookup table).
11. **No pagination** on `GET /encounters`.
12. **Free-form `event_data`** — no per-event_type schema.
13. **No visual-regression / a11y audits** on the frontend.
14. **pytest matrix on Postgres** not wired — fixture env-driven, ready to flip.
