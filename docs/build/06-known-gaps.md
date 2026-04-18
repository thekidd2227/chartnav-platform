# Known Gaps & Verification Matrix

## Verification evidence — phase 12

### Local gates

| Gate                                                      | Result |
|-----------------------------------------------------------|--------|
| `make verify` (backend)                                   | ✅ **91/91 pytest + 9/9 smoke** |
| `cd apps/web && npx tsc --noEmit`                         | ✅ clean |
| `cd apps/web && npx vitest run`                           | ✅ **18/18** |
| `cd apps/web && npm run build`                            | ✅ 168 KB JS / 8.1 KB CSS |
| `cd apps/web && npx playwright test`                      | ✅ **10/10** in ~16s |
| `bash scripts/staging_verify.sh http://127.0.0.1:8000`    | ✅ 9 assertions (against local dev API) |
| `apps/api/.venv/bin/python scripts/build_docs.py`         | ✅ HTML + PDF regenerated |

### pytest summary (91)

| Suite                       | Count | Notes |
|-----------------------------|:-----:|-------|
| `test_admin.py` (new)       | **20**| DB role CHECK, user/location CRUD, event-schema validation, pagination |
| `test_auth.py`              | 5     | header mode |
| `test_auth_modes.py`        | 11    | header + real JWT bearer |
| `test_observability.py`     | 3     | `/ready`, `/metrics` |
| `test_operational.py`       | 12    | request id, audit trail, rate limit, CORS |
| `test_rbac.py`              | 12    | role-gated writes + per-edge transitions |
| `test_scoping.py`           | 8     | org scoping + cross-org denial |
| `test_auth_modes.py` (bearer JWT — counted above)  | —   | — |

### Vitest summary (18)

| File                       | Count | Notes |
|----------------------------|:-----:|-------|
| `App.test.tsx`             | 13    | existing 12 + new "admin button visibility" test |
| `AdminPanel.test.tsx`      | **5** | list users, create user, create error 409, self-row disabled, create location |

### Playwright summary (10)

| # | Scenario | Result |
|---|----------|--------|
| 1 | App boots, default identity resolves | ✅ |
| 2 | Identity switch org1 → org2 | ✅ |
| 3 | Admin opens detail, creates encounter, sees it appear | ✅ |
| 4 | Admin appends `manual_note` workflow event | ✅ |
| 5 | Clinician operational transitions; review edge not offered | ✅ |
| 6 | Reviewer sees review-stage controls, no create button, no event composer | ✅ |
| 7 | Unknown email → `identity-error` with `unknown_user` | ✅ |
| 8 | **Admin creates user + location via admin panel** | ✅ |
| 9 | **Clinician cannot see the Admin button** | ✅ |
| 10 | Status filter narrows the list | ✅ |

## Real gaps (prioritized for next phase)

1. **No OpenTelemetry / distributed tracing.**
2. **Metrics + rate limiter are per-process** — multi-worker needs coordination.
3. **No log shipping / retention policy defined.**
4. **No audit-table archival / retention.**
5. **Forward-only migrations** — rollback cannot reverse destructive DDL.
6. **No automated staging deploy from CI** — tag push publishes image; operator runs `make staging-up`.
7. **No signing / SBOM / provenance** on release artifacts.
8. **No JWKS-rotation test, no refresh-token / revocation flow.**
9. **No org-level CRUD** — `PATCH /organizations/{id}` is intentionally absent.
10. **No user-invitation / email workflow** — admins type emails directly.
11. **No bulk-import** for users or locations.
12. **No audit log UI** — `security_audit_events` is operator-inspected only.
13. **Free-form event payloads beyond required keys** — extra keys are accepted; deep-schema per type (values types, enums) is not enforced.
14. **No pagination on audit table, users, or locations** — fine at current scale.
15. **No visual-regression / a11y audits** on the frontend.
16. **pytest matrix on Postgres** not wired (fixture env-driven, ready to flip).
