# ChartNav — Current State

**As of:** 2026-04-18 (phase: platform mode & interoperability)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/{ci.yml,release.yml}
├── Makefile
├── scripts/                 # build_docs · verify · pg_verify · release_build · staging_*
│                            # audit_retention · sbom
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py · config.py · db.py · auth.py · authz.py
│   │   │   ├── audit.py · retention.py · logging_config.py · middleware.py · metrics.py
│   │   │   ├── integrations/    # adapter boundary (phase 16)
│   │   │   │   ├── __init__.py  # resolve_adapter + vendor registry
│   │   │   │   ├── base.py      # ClinicalSystemAdapter protocol + errors
│   │   │   │   ├── native.py    # NativeChartNavAdapter
│   │   │   │   └── stub.py      # StubClinicalSystemAdapter
│   │   │   └── api/routes.py    # + GET /platform (phase 16)
│   │   ├── alembic/versions/    # 6 migrations through e5f6a7b8c9d0
│   │   ├── tests/               # 131 pytest (+13 test_platform_mode)
│   │   └── Dockerfile · entrypoint.sh · .env.example
│   └── web/
│       ├── src/
│       │   ├── App.tsx · AdminPanel.tsx · InviteAccept.tsx · api.ts
│       │   ├── identity.ts · styles.css · main.tsx
│       │   └── test/            # 30 Vitest (+2 platform-mode UI)
│       └── tests/e2e/
│           ├── workflow.spec.ts (12)
│           ├── a11y.spec.ts (5)   # axe-core — hard gate in CI
│           └── visual.spec.ts (4) # screenshot regression — local only
├── infra/docker/{dev,prod,staging}.yml
└── docs/build/ 01 … 27
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `header` (dev) or `bearer` (prod JWT via JWKS).
- RBAC: `admin` / `clinician` / `reviewer` (CHECK-constrained).
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- **a11y**: axe-core baseline covering app shell, encounter list/detail, admin panel, invite page. `serious`/`critical` violations are blocking.
- **Visual regression**: 4 macOS-baseline screenshots; `maxDiffPixelRatio: 0.02`. Local gate; CI skips (OS-specific pixels).
- **Admin list scaling**: `GET /users`/`/locations` now take `limit`, `offset`, `q`, role (+users). `X-Total-Count` headers. UI has search + Prev/Next pagers on Users + Locations tabs.
- **Feature flags**: `organization.settings.feature_flags.audit_export` and `.bulk_import` actually gate the corresponding admin buttons.
- **Audit retention**: `scripts/audit_retention.py` prunes old rows per `CHARTNAV_AUDIT_RETENTION_DAYS`; the app never silently prunes.
- **Release compliance**: SBOM (`chartnav-sbom-<v>.json`) + image digest (`chartnav-api-<v>.digest.txt`) in every release bundle, attached to the GitHub Release.
- **Platform mode** (phase 16): `CHARTNAV_PLATFORM_MODE` ∈ {`standalone`, `integrated_readthrough`, `integrated_writethrough`}. Adapter boundary (`ClinicalSystemAdapter`) separates ChartNav core from any external EHR/EMR. Ships `NativeChartNavAdapter` (standalone) + `StubClinicalSystemAdapter` (integrated placeholder); vendor adapters plug in via `register_vendor_adapter`. Config fails loudly on misconfig. `GET /platform` surfaces mode + adapter + source-of-truth to the UI.
- Alembic head: `e5f6a7b8c9d0`.

## Testing layers

| Layer                | Tool         | Count | Notes |
|----------------------|--------------|:-----:|-------|
| pytest               | pytest       |  131  | +13 platform-mode + adapter resolution |
| shell smoke          | smoke.sh     |   9   | unchanged |
| Vitest               | vitest       |  30   | +2 platform-mode banner (standalone + integrated variants) |
| Playwright workflow  | @playwright  |  12   | unchanged contract |
| Playwright a11y      | @axe-core/playwright | 5 | NEW |
| Playwright visual    | Playwright snapshots | 4 | NEW (local only) |
| staging              | staging_verify.sh | 9 | unchanged |

## Verified working endpoints

No new endpoints this phase. `GET /users` and `GET /locations` gained
`q`/`role`/`limit`/`offset` query parameters + pagination headers;
older callers that pass no params still see the first 100 rows.

## Automation

- `make verify` → 131 pytest + 9 smoke
- `make web-verify` → 30 vitest + typecheck + build
- `make e2e` → 12 workflow + 5 a11y + 4 visual (local)
- `make e2e-a11y` / `make e2e-visual` / `make e2e-visual-update`
- `make audit-prune ARGS="--days 90 --dry-run"`
- `make sbom` → `dist/release/_sbom.json`
- `make pg-verify` / `make staging-*` / `make release-build VERSION=v0.1.0`
- `make dev` — backend + frontend together
- CI: backend-sqlite + frontend + deploy-config in parallel; e2e (workflow + a11y) gates on backend + frontend; backend-postgres + docker-build + docs chain on backend-sqlite.
