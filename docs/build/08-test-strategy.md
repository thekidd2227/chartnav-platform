# Test & Smoke Strategy

## Stack

- `pytest` + FastAPI `TestClient` for unit/integration.
- Per-test temporary SQLite (fresh migrate + seed per test); env-based wiring so the same fixture will later work against Postgres.
- Live shell smoke (`apps/api/scripts/smoke.sh`) used by:
  - `make verify` (SQLite)
  - `scripts/pg_verify.sh` (Postgres)
  - the built Docker image smoke job
- CI runs all of the above on every push / PR.

## Layout

```
apps/api/tests/
├── conftest.py          # env-based per-test DB, header presets
├── test_auth.py         # authn surface (5)
├── test_auth_modes.py   # header + bearer seam (3)
├── test_rbac.py         # role-gated writes + state transitions (12)
└── test_scoping.py      # org scoping (8)

apps/api/scripts/
└── smoke.sh             # curl-level live smoke (9 checks)

scripts/
├── verify.sh            # boot + smoke + teardown (SQLite)
└── pg_verify.sh         # same flow against a throwaway Postgres
```

## Coverage

| Surface                         | pytest | smoke | Postgres smoke | Docker-image smoke |
|---------------------------------|:------:|:-----:|:--------------:|:------------------:|
| `/health`, `/`                  |   ✓    |   ✓   |       ✓        |         ✓          |
| Header-mode auth                |   ✓    |   ✓   |       ✓        |         ✓          |
| Bearer-mode seam (501 / config) |   ✓    |       |                |                    |
| Org scoping                     |   ✓    |   ✓   |       ✓        |         ✓          |
| RBAC                            |   ✓    |       |                |                    |
| Filter on `/encounters`         |   ✓    |       |                |                    |
| State machine invariants        |   ✓    |       |       ✓        |                    |
| Event provenance (`changed_by`) |   ✓    |       |       ✓        |                    |
| Migrations                      |        |       |       ✓        |         ✓          |
| Seed idempotency (x2 runs)      |        |       |       ✓        |                    |

## How to run

```bash
# Fast pytest (SQLite)
cd apps/api && pytest tests/ -v

# Full local SQLite gate
make verify                 # resets DB, pytest, boot, smoke, teardown

# Postgres parity (docker required)
make pg-verify

# Docker image + smoke
make docker-build
```

## Results at time of writing

- `pytest`: **28 passed in ~19s**
- `make verify` (SQLite): 28 pytest + 9 smoke — all green
- `scripts/pg_verify.sh`: migrations + seed (x2) + smoke + status transition + event write — **PASS**

## Backend coverage (phase 14)

- 110 pytest. `test_invitations.py` (20) covers invite issue / accept happy path / invalid / expired / reused / reissued tokens, cross-org denial, inactive / already-accepted denial, CSV export (admin-only, filters honored, shape), event-hardening rejection cases, and bulk import summary + org scoping + admin-only.
- `test_control_plane.py` (19) updated for the typed settings schema (extra-forbid, extensions bucket, size cap via extensions).

## Backend coverage (phase 13)

- 88 pytest tests. `test_control_plane.py` (17) covers org settings read/patch (all roles + unauth), JSON validation (non-object → 422, oversized → 400 `settings_too_large`), admin PATCH cross-org isolation, audit read admin-only, filters for `event_type` / `actor_email` / `q`, pagination headers, org scoping (never surfaces cross-org rows with identity), and `invited_at` stamping on admin create.

## Backend coverage (phase 10)

- 48 pytest tests across `test_auth`, `test_auth_modes`, `test_rbac`, `test_scoping`, `test_operational`.
- Real JWT validation via a locally generated RSA keypair; no external IdP.
- Audit + request-id + rate-limit + CORS all asserted at the integration level.

## Frontend verification (phase 8)

- `make web-verify` = `npm run typecheck` + `npm test` + `npm run build`.
- Vitest + Testing Library + jsdom. 12 integration tests mocking
  `./api`. Full matrix in `16-frontend-test-strategy.md` and
  `06-known-gaps.md`.
- Vite production build still emits `dist/` in ~1s.
- CI now runs a dedicated `frontend` job on every push/PR: node 20,
  `npm ci`, typecheck, test, build.

## Gaps not yet covered

- pytest matrix against Postgres (the fixture is already env-driven).
- Concurrent writers / race conditions.
- `event_data` schema per `event_type`.
- Pagination behavior (not yet implemented).
- Bearer-mode JWT validation (placeholder only; see `11-production-auth-seam.md`).
