# Known Gaps & Verification Matrix

## Verification evidence — phase 14

### Local gates

| Gate                                        | Result |
|---------------------------------------------|--------|
| `make verify` (backend)                     | ✅ **110/110 pytest + 9/9 smoke** |
| `cd apps/web && npx tsc --noEmit`           | ✅ clean |
| `cd apps/web && npx vitest run`             | ✅ **25/25** |
| `cd apps/web && npm run build`              | ✅ 184 KB JS / 8.2 KB CSS |
| `cd apps/web && npx playwright test`        | ✅ **12/12** in ~15s |
| `apps/api/.venv/bin/python scripts/build_docs.py` | ✅ HTML + PDF |

### pytest summary (110)

| Suite                       | Count | Notes |
|-----------------------------|:-----:|-------|
| `test_admin.py`             | 20    | admin governance (phase 12) |
| `test_auth.py`              | 5     | header mode |
| `test_auth_modes.py`        | 11    | real JWT bearer |
| `test_control_plane.py`     | 19    | org settings + audit read + invited_at (phase 13 updated for typed settings) |
| `test_invitations.py` ✦     | **20**| **invitations + audit export + event hardening + bulk users (phase 14)** |
| `test_observability.py`     | 3     | `/ready`, `/metrics` |
| `test_operational.py`       | 12    | request id, audit, rate limit, CORS |
| `test_rbac.py`              | 12    | role-gated writes + per-edge transitions |
| `test_scoping.py`           | 8     | org scoping |

### Vitest summary (25)

| File                       | Count | Notes |
|----------------------------|:-----:|-------|
| `App.test.tsx`             | 13    | unchanged |
| `AdminPanel.test.tsx`      | 12    | +3 (invite / bulk summary / audit export) on top of phase 13 |

### Playwright summary (12)

Adds "admin can issue an invitation and download audit CSV" on top of
the 11 scenarios shipped through phase 13.

## Real gaps (prioritized for next phase)

1. **No email delivery** for invitations — admin manually shares the token.
2. **No SSO → users mapping change** (still by `CHARTNAV_JWT_USER_CLAIM`).
3. **Metrics + rate limiter per-process** — multi-worker still needs coordination.
4. **No OpenTelemetry / distributed tracing.**
5. **No log shipping / retention** defined; no audit-table archival.
6. **No CSV export for users or locations** (audit export only).
7. **Forward-only migrations** (acknowledged policy).
8. **No automated staging deploy from CI**.
9. **No signing / SBOM / provenance** on release artifacts.
10. **No JWKS-rotation test, no refresh-token / revocation flow.**
11. **No org-level slug change** (intentional).
12. **No feature-flag consumer yet** — the settings field exists but the app doesn't read it.
13. **No pagination/search on users and locations lists** (fine at current scale).
14. **No visual-regression / a11y audits**.
15. **pytest matrix on Postgres** not wired (fixture env-driven, ready to flip).
16. **No invite-accept screen polish** (redirect to main app on success, proper routing, a11y review) — only the minimal success banner exists.
