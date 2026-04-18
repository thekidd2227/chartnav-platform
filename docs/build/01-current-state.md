# ChartNav — Current State

**As of:** 2026-04-18 (phase: invitations + settings schema + audit export + bulk)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/{ci.yml,release.yml}
├── Makefile
├── scripts/                 # build_docs · verify · pg_verify · release_build · staging_*
├── apps/
│   ├── api/
│   │   ├── app/             # main · config · db · auth · authz · audit · logging_config · middleware · metrics
│   │   │   └── api/routes.py  # + /users/{id}/invite · /invites/accept · audit export · /users/bulk · typed settings
│   │   ├── alembic/versions/  # 6 migrations through e5f6a7b8c9d0
│   │   ├── tests/             # 110 pytest (+20 invitations/bulk/export)
│   │   └── Dockerfile · entrypoint.sh · .env.example
│   └── web/
│       ├── src/
│       │   ├── App.tsx · AdminPanel.tsx · InviteAccept.tsx · api.ts
│       │   ├── identity.ts · styles.css · main.tsx
│       │   └── test/          # 25 Vitest
│       └── tests/e2e/         # 12 Playwright
├── infra/docker/{dev,prod,staging}.yml
└── docs/build/ 01 … 24
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core + PyJWT.
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Playwright.
- Auth: `header` (dev) or `bearer` (prod JWT via JWKS).
- RBAC: `admin` / `clinician` / `reviewer` (CHECK-constrained at DB level).
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}`.
- **Invitations** (phase 14): admin issues 7-day tokens via `POST /users/{id}/invite`; only sha256 hash stored; accept via `POST /invites/accept`; re-issue revokes prior token; frontend has a minimal `/invite?invite=<token>` accept screen.
- **Org settings**: typed `OrganizationSettings` pydantic model (extra=forbid) with `default_provider_name`, `encounter_page_size`, `audit_page_size`, `feature_flags`, `extensions`. 16 KB cap. UI edits each field with dedicated inputs.
- **Audit export**: `GET /security-audit-events/export` → CSV, honors existing filters + org scoping.
- **Event payload hardening** (phase 14): per-type value discipline (status enum, non-empty strings, non-negative ints).
- **Bulk user import**: `POST /users/bulk` with per-row pass/fail summary; UI exposes a CSV-like textarea dialog.
- Alembic head: `e5f6a7b8c9d0`.

## Testing layers

| Layer        | Tool         | Count | Notes |
|--------------|--------------|:-----:|-------|
| pytest       | pytest       |  110  | +20 invitations/bulk/export/event-hardening |
| shell smoke  | smoke.sh     |   9   | unchanged |
| vitest       | vitest       |  25   | +3 admin-panel (invite/bulk/export) |
| Playwright   | @playwright  |  12   | +1 admin invite + audit CSV download E2E |
| staging      | staging_verify.sh | 9 | unchanged |

## Verified working endpoints

Additions this phase:
- `POST /users/{id}/invite`
- `POST /invites/accept`
- `POST /users/bulk`
- `GET /security-audit-events/export`

Unchanged surfaces from phases 1–13 are all still green.

## Automation

- `make verify` → 110 pytest + 9 smoke
- `make web-verify` → 25 vitest + typecheck + build
- `make e2e` → 12 Playwright
- `make pg-verify` — Postgres parity
- `make staging-up / staging-verify / staging-rollback / staging-down`
- `make release-build VERSION=v0.1.0`
- `make dev` — backend + frontend
- CI gates unchanged (backend / frontend / e2e / backend-postgres / docker-build / docs / deploy-config).
