# ChartNav — Current State

**As of:** 2026-04-18 (phase: frontend workflow UI)

## Repo layout (relevant)

```
chartnav-platform/
├── .github/workflows/ci.yml     # backend-sqlite · backend-postgres · docker-build · docs
├── Makefile                     # install · verify · pg-verify · docker-* · web-* · dev
├── scripts/                     # build_docs.py · verify.sh · pg_verify.sh
├── apps/
│   ├── api/
│   │   ├── Dockerfile · entrypoint.sh
│   │   ├── .env.example
│   │   ├── app/{main,config,db,auth,authz}.py
│   │   ├── app/api/routes.py
│   │   ├── alembic/
│   │   ├── scripts_seed.py
│   │   ├── scripts/smoke.sh
│   │   └── tests/               # 28 pytest incl. 3 auth-mode tests
│   └── web/
│       ├── .env.example         # NEW — VITE_API_URL contract
│       ├── src/
│       │   ├── api.ts           # NEW — typed API client
│       │   ├── identity.ts      # NEW — dev identity helpers
│       │   ├── App.tsx          # NEW — full workflow UI
│       │   ├── main.tsx         # wires App.tsx + styles.css
│       │   ├── styles.css       # NEW — single CSS file
│       │   └── vite-env.d.ts    # NEW — Vite ambient types
│       └── package.json
├── infra/docker/{docker-compose.yml,docker-compose.prod.yml}
└── docs/build/01..15            # now including 15-frontend-integration.md
```

## Runtime baseline

- Backend: Python 3.11, FastAPI, SQLAlchemy Core, SQLite or Postgres.
- Frontend: Vite 5 + React 18 + TypeScript; vanilla CSS.
- Auth: `CHARTNAV_AUTH_MODE=header` (dev) or `bearer` (placeholder 501).
- DB: SQLite default (`apps/api/chartnav.db`), Postgres via `DATABASE_URL=postgresql+psycopg://…`.
- Alembic head: `a1b2c3d4e5f6`. No schema changes this phase.
- RBAC: `admin`, `clinician`, `reviewer`.
- Error envelope: `{"detail": {"error_code": "...", "reason": "..."}}` — the frontend surfaces these verbatim.

## Frontend capabilities (new)

- Header with brand, caller chip (`email · role · org N`), API base URL, identity picker (5 seeded users + custom).
- Encounter list with filters (`status`, `provider_name`, `location_id`) and color-coded status pills.
- Encounter detail with facts grid, current status, allowed transitions (role-aware), event timeline.
- Event composer for admin / clinician; hidden with explanation for reviewer.
- All API errors surface as banners with `error_code` + `reason`.
- Dev identity persists in `localStorage`; switching reloads `/me` and list.

## Verified working endpoints

No endpoint behavior changed this phase. All 28 pytest tests still pass;
the UI exercises the full surface through the typed client.

## Automation

- `make verify` — SQLite: reset-db + pytest + boot + smoke.
- `make pg-verify` — Postgres parity proof.
- `make web-install` / `web-dev` / `web-build` / `web-typecheck`.
- `make dev` — boots API (8000) + Vite (5173) together with a shared trap-based teardown.
- CI: `backend-sqlite` → `backend-postgres` + `docker-build` + `docs`.
