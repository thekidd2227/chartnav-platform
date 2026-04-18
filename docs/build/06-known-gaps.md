# Known Gaps & Verification Matrix

## Verification evidence — phase 13

### Local gates

| Gate                                     | Result |
|------------------------------------------|--------|
| `make verify` (backend)                  | ✅ **88/88 pytest + 9/9 smoke** |
| `cd apps/web && npx tsc --noEmit`        | ✅ clean |
| `cd apps/web && npx vitest run`          | ✅ **22/22** |
| `cd apps/web && npm run build`           | ✅ 175 KB JS / 8.2 KB CSS |
| `cd apps/web && npx playwright test`     | ✅ **11/11** in ~17s |
| `apps/api/.venv/bin/python scripts/build_docs.py` | ✅ HTML + PDF |

### pytest summary (88)

| Suite                       | Count | Notes |
|-----------------------------|:-----:|-------|
| `test_admin.py`             | 20    | admin governance (phase 12) |
| `test_auth.py`              | 5     | header mode |
| `test_auth_modes.py`        | 11    | real JWT bearer |
| `test_control_plane.py` ✦   | **17**| **org settings + audit read + invited_at (phase 13)** |
| `test_observability.py`     | 3     | `/ready`, `/metrics` |
| `test_operational.py`       | 12    | request id, audit, rate limit, CORS |
| `test_rbac.py`              | 12    | role-gated writes + per-edge transitions |
| `test_scoping.py`           | 8     | org scoping |

### Vitest summary (22)

| File                       | Count | Notes |
|----------------------------|:-----:|-------|
| `App.test.tsx`             | 13    | unchanged |
| `AdminPanel.test.tsx`      | 9     | +4 Organization + Audit tests |

### Playwright summary (11)

| # | Scenario                                                          |
|---|-------------------------------------------------------------------|
| 1 | Default identity resolves |
| 2 | Identity switch org1 → org2 |
| 3 | Admin opens detail, creates encounter |
| 4 | Admin appends `manual_note` workflow event |
| 5 | Clinician operational transitions; reviewer edge not offered |
| 6 | Reviewer sees review-stage controls, no create, no composer |
| 7 | Unknown email → `identity-error` |
| 8 | Admin creates user + location via admin panel |
| 9 | **Admin edits organization settings and inspects audit log** (new) |
| 10 | Clinician cannot see Admin button |
| 11 | Status filter narrows the list |

## Real gaps (prioritized for next phase)

1. **No OpenTelemetry / distributed tracing.**
2. **Metrics + rate limiter are per-process** — multi-worker needs coordination.
3. **No log shipping / retention policy defined.**
4. **No audit-table archival / retention.** Rows accumulate indefinitely.
5. **No audit export** (CSV/JSON download).
6. **Forward-only migrations.**
7. **No automated staging deploy from CI.**
8. **No signing / SBOM / provenance** on release artifacts.
9. **No JWKS-rotation test, no refresh-token / revocation flow.**
10. **No token-based invitation workflow or email delivery.** `invited_at` is a badge only.
11. **No org-level slug change** — intentionally immutable.
12. **No bulk-import for users or locations.**
13. **No organization settings schema** — the column is free-form JSON; no specific keys are consumed by the app yet.
14. **No pagination/search on users and locations lists** (fine at current scale).
15. **No visual-regression / a11y audits** on the frontend.
16. **pytest matrix on Postgres** not wired (fixture env-driven, ready to flip).
