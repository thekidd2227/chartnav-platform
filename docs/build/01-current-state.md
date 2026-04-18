# ChartNav — Current State

**As of:** 2026-04-18 (phase: create UI + frontend tests + frontend CI)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/ci.yml   # backend-sqlite · backend-postgres · frontend · docker-build · docs
├── Makefile                   # verify · pg-verify · docker-* · web-* (incl. web-test / web-verify) · dev
├── scripts/                   # build_docs.py · verify.sh · pg_verify.sh
├── apps/
│   ├── api/                   # (unchanged this phase)
│   │   ├── app/{main,config,db,auth,authz}.py + app/api/routes.py
│   │   ├── alembic/ · scripts_seed.py · scripts/smoke.sh
│   │   ├── tests/ (28 pytest)
│   │   └── Dockerfile · entrypoint.sh
│   └── web/
│       ├── .env.example
│       ├── package.json          # scripts: dev · build · preview · typecheck · test · test:watch
│       ├── vite.config.ts        # also hosts vitest config (jsdom)
│       ├── tsconfig.json         # includes vitest/globals + testing-library types
│       └── src/
│           ├── api.ts            # typed client, createEncounter, canCreateEncounter
│           ├── identity.ts
│           ├── App.tsx           # + CreateEncounterModal, pending-state buttons
│           ├── styles.css        # + modal styles
│           ├── main.tsx · vite-env.d.ts
│           └── test/
│               ├── setup.ts
│               └── App.test.tsx  # 12 integration tests
├── infra/docker/{docker-compose,docker-compose.prod}.yml
└── docs/build/ 01 … 16          # incl. 15-frontend-integration, 16-frontend-test-strategy
```

## Runtime baseline

- Backend: FastAPI + SQLAlchemy Core, SQLite or Postgres (via `DATABASE_URL`).
- Frontend: Vite 5 + React 18 + TypeScript + Vitest + Testing Library.
- Auth: `CHARTNAV_AUTH_MODE=header` (dev) or `bearer` (prod placeholder 501).
- RBAC: `admin` / `clinician` / `reviewer`.
- Alembic head: `a1b2c3d4e5f6`. No schema changes this phase.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}` — surfaced verbatim in the UI.

## Frontend capabilities (delta this phase)

- `+ New encounter` button in the header for admin/clinician; hidden for reviewer.
- `CreateEncounterModal`:
  - Fetches `/locations` (already org-scoped server-side).
  - Fields: patient_identifier*, patient_name, provider_name*, location_id*, initial status (`scheduled` / `in_progress`).
  - Disables submit while in-flight, validates required fields.
  - Success → refresh list, auto-select new encounter, show success banner.
  - Failure → inline error with exact `error_code` + `reason`; modal stays open for retry.
- Transition / append-event buttons now show a pending label and disable while the request is in flight.
- Banners annotated with ARIA roles; `data-testid` hooks added to enable a11y + tests.

## Automation

- `make verify` — SQLite backend gate (reset-db + pytest + boot + smoke).
- `make pg-verify` — Postgres parity proof.
- `make web-verify` — frontend gate (typecheck + test + build).
- `make dev` — backend + frontend together with trap teardown.
- CI: `backend-sqlite` + `frontend` run in parallel; `backend-postgres` + `docker-build` + `docs` are chained after `backend-sqlite`.
