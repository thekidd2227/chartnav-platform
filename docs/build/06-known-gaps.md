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

## Phase-17 additions

- **Brand-aligned UI**: `--cn-*` token system lifted from the ChartNav marketing site, real logo SVG in the header, Inter typography, subtle "Powered by ARCG Systems" footer, AA-safe muted text (`#475569`). Legacy token names kept as aliases — no component-level rewrites.
- **`chartnav.ai` domain**: safety-net host-based redirect in `arcg-live` (`index.html` + `public/404.html`). Primary 301 mechanism is GoDaddy forwarding, documented in `arcg-live/docs/chartnav-ai-domain-runbook.md`.
- **31 Vitest** (+1), **17 Playwright workflow+a11y**, **4 visual (local)** — visual baselines deliberately regenerated for the new brand look.

## Phase-16 additions

- **Platform modes**: `CHARTNAV_PLATFORM_MODE` wired — `standalone` / `integrated_readthrough` / `integrated_writethrough`. Config validates and refuses impossible combinations at import time.
- **Adapter boundary**: `app/integrations/` with `ClinicalSystemAdapter` protocol + `NativeChartNavAdapter` + `StubClinicalSystemAdapter`. Vendor adapters plug in via `register_vendor_adapter`.
- **`GET /platform`**: surfaces mode + adapter + source-of-truth. Admin panel renders a mode banner.
- **131 pytest** (+13 platform). **30 Vitest** (+2 platform banner). Playwright unchanged.
- **CI hardening rolled in with this phase**: migration boolean default portability (SQLite → Postgres) + vitest lockfile regen (Linux/Node 20). Both reproduced locally against docker postgres and `node:20` container; both now green.

## Phase-15 additions

- **a11y**: 5 axe-core scenarios in CI (`serious`/`critical` blocking). Fixed: event-type `<select>` and inline admin role `<select>` now have aria-labels.
- **Visual regression**: 4 macOS baselines; `make e2e-visual` locally; not in CI (see below).
- **Admin list scaling**: `GET /users`/`/locations` gained `limit`/`offset`/`q`/`role`; UI adds search + pager.
- **Feature flags**: `audit_export` and `bulk_import` in `feature_flags` actually hide the corresponding admin UI buttons (frontend-tested).
- **Retention**: `scripts/audit_retention.py` + `CHARTNAV_AUDIT_RETENTION_DAYS` env; backend tests cover disabled / dry-run / delete.
- **Release compliance**: `chartnav-sbom-<v>.json` + `chartnav-api-<v>.digest.txt` are produced by `release_build.sh` and attached to the GitHub Release.

## Real gaps (prioritized for next phase)

0. **No native `patients` table** — standalone mode's adapter refuses patient operations today. Next standalone-mode build should add the minimum native patient + provider schema.
0. **No real vendor adapter** (Epic / Cerner / Athena / FHIR). The contract + registry exist; vendor work plugs in. Recommended first target: FHIR read-through.
0. **Adapter path isn't fully exercised by HTTP routes yet** — `GET /platform` returns adapter metadata, but encounter/status routes still go through direct DB calls, not the adapter. Standalone that's a nop (native adapter wraps the same DB); for integrated modes this is where the real vendor translation work happens next.

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
