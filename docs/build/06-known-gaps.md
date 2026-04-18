# Known Gaps & Verification Matrix

## Verification evidence — phase 8

### Frontend gate (`make web-verify`)

| Step                                  | Result |
|---------------------------------------|--------|
| `tsc --noEmit`                        | ✅ clean |
| `vitest run`                          | ✅ **12/12** in ~2.5s |
| `vite build`                          | ✅ 159 KB JS / 7.3 KB CSS |

### Frontend test matrix (12)

| Scenario                                                            | Result |
|---------------------------------------------------------------------|--------|
| `/me` resolves → identity badge                                     | ✅ |
| List renders mocked encounters                                      | ✅ |
| Status filter hits API + updates list                               | ✅ |
| Select encounter loads detail + timeline                            | ✅ |
| Clinician sees operational transitions only                         | ✅ |
| Reviewer sees review-stage transitions only + event composer hidden | ✅ |
| Reviewer cannot see `+ New encounter`                               | ✅ |
| Admin creates encounter → success banner, modal closed              | ✅ |
| Create 403 `cross_org_access_forbidden` surfaces inline             | ✅ |
| Identity switch refetches `/me` + list                              | ✅ |
| Unknown email → `identity-error` chip with `unknown_user`           | ✅ |
| Status transition refreshes detail + events                         | ✅ |

### Backend gate (`make verify`)

| Step                                   | Result |
|----------------------------------------|--------|
| reset-db + alembic + seed              | ✅ |
| pytest                                 | ✅ **28/28** |
| uvicorn boot + smoke.sh                | ✅ 9/9 |
| teardown                               | ✅ |

### Postgres parity (`make pg-verify`)

Still green from the prior phase; no code touched this phase changes it.

### CI YAML
- `yaml.safe_load(open(".github/workflows/ci.yml"))` — parses. Jobs now: `backend-sqlite`, `backend-postgres`, `frontend`, `docker-build`, `docs`.
- No `act` runner in shell — static parse + structural review only (same limitation as prior phases).

## Real gaps (prioritized for next phase)

1. **No end-to-end browser tests** against a live backend. Current verification is build + unit-level integration + curl parity. Playwright is the obvious next step.
2. **JWT validation still stubbed** — bearer mode returns 501 honestly. Needs PyJWT + JWKS cache.
3. **No image push / release pipeline** — CI builds, doesn't ship.
4. **No secret store integration.** Env-var only.
5. **`/organizations`, `/locations`, `/users`** remain read-only — no admin write UI for metadata.
6. **`users.role`** still free VARCHAR at DB layer (CHECK or lookup table).
7. **No pagination** on `GET /encounters` (backend or frontend).
8. **Free-form `event_data`** — no per-event_type schema.
9. **CORS `allow_origins=["*"]`.**
10. **No distinct audit log** for auth/scoping failures.
11. **No rate limiting / lockout / structured logging.**
12. **pytest matrix on Postgres** — fixture is env-driven but not yet multi-DB.
13. **No visual-regression / accessibility audits** on the frontend.
