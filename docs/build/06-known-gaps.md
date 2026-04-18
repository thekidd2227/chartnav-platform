# Known Gaps & Verification Matrix

## Verification evidence — phase 9

### Local gates
| Gate                  | Result |
|-----------------------|--------|
| `make verify` (SQLite backend + pytest 28 + smoke 9) | ✅ |
| `make pg-verify` (Postgres parity)                  | ✅ (from preceding phase, no backend changes here) |
| `make web-verify` (tsc + vitest 12 + build)         | ✅ |
| `make e2e` (Playwright 8 tests in chromium)         | ✅ **8/8 in ~14s** |

### Playwright E2E matrix (8)

| # | Scenario                                                                 | Result |
|---|--------------------------------------------------------------------------|--------|
| 1 | App boots, default seeded identity resolves                              | ✅ |
| 2 | Identity switch admin1 → admin2 changes visible scope                    | ✅ |
| 3 | Admin opens detail, creates encounter, sees it in the list               | ✅ |
| 4 | Admin appends a workflow event; timeline reflects it                     | ✅ |
| 5 | Clinician drives operational transitions; review edge not offered        | ✅ |
| 6 | Reviewer sees completion/kick-back, no create button, no event composer  | ✅ |
| 7 | Unknown email surfaces `identity-error` with `unknown_user`              | ✅ |
| 8 | Status filter narrows the list                                           | ✅ |

### CI YAML
- `ci.yml` jobs: `backend-sqlite`, `backend-postgres`, `frontend`, `e2e`, `docker-build`, `docs`.
- `release.yml` triggers: `push` on `v*.*.*` tags + `workflow_dispatch`.
- Both parse cleanly via PyYAML. No `act` available locally for live workflow execution.

### Release script dry-sanity
- `bash scripts/release_build.sh` resolves version, builds the API image + web bundle, writes a MANIFEST with sha256s under `dist/release/<version>/`. Output directory is gitignored.

## Real gaps (prioritized for next phase)

1. **JWT validation still stubbed** — bearer mode returns 501 honestly. Wire PyJWT + JWKS cache.
2. **Release flow doesn't deploy anywhere** — GHCR push + GitHub Release is the limit. No staging / prod deploy automation, no rollback driver.
3. **No signing / SBOM / provenance** on release artifacts.
4. **No automated Postgres E2E** — Playwright uses SQLite for speed. `backend-postgres` still proves parity at the HTTP level.
5. **`/organizations`, `/locations`, `/users`** remain read-only.
6. **`users.role`** free VARCHAR at DB layer.
7. **No pagination** on `GET /encounters`.
8. **Free-form `event_data`**; no per-event_type schema.
9. **CORS `allow_origins=["*"]`.**
10. **No distinct audit log** for auth/scoping failures.
11. **No rate limiting / lockout / structured logging.**
12. **No visual-regression / a11y audits** on the frontend.
13. **pytest matrix on Postgres** — fixture env-driven but not yet multi-DB.
