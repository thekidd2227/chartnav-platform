# ChartNav — Current State

**As of:** 2026-04-17 (phase: workflow state machine + filtering)

## Repo layout (relevant)

```
chartnav-platform/
├── apps/
│   ├── api/                          # FastAPI service (SQLite local)
│   │   ├── app/main.py               # app factory, CORS, router mount
│   │   ├── app/api/routes.py         # all HTTP handlers
│   │   ├── alembic.ini
│   │   ├── alembic/env.py
│   │   ├── alembic/versions/         # 2 migrations
│   │   ├── scripts_seed.py           # idempotent demo seed
│   │   └── pyproject.toml
│   └── web/                          # Vite shell (untouched this phase)
├── infra/docker/docker-compose.yml
└── docs/
    ├── build/                        # living docs (this set)
    ├── diagrams/                     # Mermaid sources
    ├── final/                        # consolidated HTML/PDF
    └── releases/
```

## Runtime baseline

- Python 3.11+, FastAPI, raw `sqlite3` driver (no ORM yet).
- SQLite file resolved at `apps/api/chartnav.db` (gitignored).
- Alembic history: `43ccbf363a8f → a1b2c3d4e5f6` (head).
- CORS wide-open (`*`) for local dev.

## Verified working endpoints (preserved)

- `GET /health`, `GET /`
- `GET /organizations`, `GET /locations`, `GET /users`
- `GET /encounters` (now with filters — see `03-api-endpoints.md`)
- `GET /encounters/{id}`
- `GET /encounters/{id}/events`
- `POST /encounters`
- `POST /encounters/{id}/events`
- `POST /encounters/{id}/status` (now strict state machine — see `02-workflow-state-machine.md`)

## Demo data shipped by seed

| id | patient_id | provider  | status         | events |
|----|------------|-----------|----------------|--------|
| 1  | PT-1001    | Dr. Carter| in_progress    | 3      |
| 2  | PT-1002    | Dr. Patel | review_needed  | 5      |

See `04-data-model.md` and `05-build-log.md` for details.
