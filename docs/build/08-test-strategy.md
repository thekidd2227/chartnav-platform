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

## Backend coverage (phase 21)

- **196 pytest.** New `tests/test_encounter_bridge.py` (+11):
  - bridge creates native row + carries `external_ref` +
    `external_source` + `_bridged: True`.
  - second call idempotent → same `id`, `_bridged: False`.
  - standalone refusal (409).
  - RBAC: reviewer → 403, admin + clinician OK.
  - integrated_writethrough allowed.
  - invalid status → 400 `invalid_status`.
  - **full wedge**: transcript ingest → generate → sign → export →
    workflow event, all on the bridged native id.
  - phase-20 status-write gate still holds on bridged row.
  - org scoping: same `external_ref` in two orgs → two native rows.
  - standalone regression: native encounters keep `external_ref=NULL`.
- Frontend: **45 Vitest** — bridge button dispatches
  `bridgeEncounter`; external-note copy asserts on "bridg".
- Playwright: 17/17 workflow + a11y unchanged. Visual baselines
  refreshed (4/4 local).

## Backend coverage (phase 20)

- **185 pytest.** New `tests/test_integrated_encounters.py` (+11):
  standalone list/detail carry `_source: "chartnav"`; integrated
  readthrough + stub dispatches list/detail to the adapter and
  returns stub rows; readthrough refuses `POST /encounters` and
  `POST /encounters/{id}/status` with 409
  `encounter_write_unsupported`; workflow events still writable;
  writethrough + stub allows status writes (stub records in-process);
  writethrough + fhir refuses with 501 `adapter_write_not_supported`;
  FHIR `list_encounters` normalizes Bundle entries through the
  status mapping and fixture transport; `/encounters` still requires
  auth. `tests/test_fhir_adapter.py` existing encounter test
  updated for the new normalized shape.
- Frontend: **44 Vitest** (+2) — native chip renders, external
  encounter hides transitions + workspace + shows SoT banner.
- Playwright: 17 workflow+a11y unchanged. Visual baselines refreshed.

## Backend coverage (phase 19)

- **174 pytest.** New `tests/test_transcript_to_note.py` (+19):
  - input creation defaults (text/audio); `transcript_required`
    for text-type inputs; reviewer RBAC denial; cross-org 404.
  - `POST /encounters/{id}/notes/generate` creates v1 + findings;
    regeneration produces v2 and preserves v1; `no_completed_input`
    when only queued inputs exist.
  - missing-flag emission on a sparse transcript
    (`iop_missing`, `visual_acuity_missing`, `plan_missing`).
  - provider PATCH flips `generated_by=manual` +
    `draft_status=revised`.
  - submit-for-review → `provider_review`.
  - sign: reviewer → 403 `role_cannot_sign`; clinician stamps
    `signed_at` + `signed_by_user_id`; signed → immutable
    (PATCH → 409 `note_immutable`).
  - export requires signed state; stamps `exported_at`.
  - `GET /note-versions/{id}` returns both note and findings.
  - audit trail verifies `encounter_input_created`,
    `note_version_generated`, `note_version_signed`,
    `note_version_exported`.
- Frontend: **42 Vitest** including +8 NoteWorkspace tests.
- Playwright: 17 workflow+a11y unchanged. Visual baselines
  refreshed (4 local) for the new workspace tiers.

## Backend coverage (phase 18)

- **155 pytest.** New:
  - `test_clinical.py` (13) covers migration + seed linkage, patient
    + provider CRUD, RBAC, uniqueness + NPI validation, cross-org
    isolation, readthrough-blocks-writes with
    `native_write_disabled_in_integrated_mode`.
  - `test_fhir_adapter.py` (11) covers config validation (missing
    base URL, bearer missing token, invalid auth type), Patient +
    Encounter normalization against fixture resources, bearer
    header threading, honest `AdapterNotSupported` on write paths,
    `resolve_adapter` resolves FHIR under `integrated_readthrough`.
- Platform-mode tests updated for the native adapter now supporting
  patient read/write (phase 18 deliberate promotion).
- Frontend: **34 Vitest** (+3 Patients/Providers admin tabs).
- Playwright unchanged contract (17 workflow + a11y); visual
  baselines refreshed for the new tabs.

## Backend coverage (phase 16)

- **131 pytest.** `test_platform_mode.py` (13) covers:
  - Config parsing: default mode, integrated defaults, invalid
    mode raises, standalone-forbids-non-native-adapter.
  - Adapter resolution: standalone → native, integrated_readthrough
    + stub (writes refused), integrated_writethrough + stub (writes
    recorded in-process), unknown vendor key raises, vendor
    registration path works.
  - Native adapter: honestly refuses patient operations today.
  - `GET /platform` endpoint: returns mode + adapter + source-of-truth;
    no secret leakage (no `jwt` / `database_url` substrings); requires
    auth (401 without identity).
- Frontend: **30 Vitest.** `AdminPanel.test.tsx` adds 2 tests —
  platform banner standalone + integrated-readthrough variants.

## Backend coverage (phase 15)

- 118 pytest. `test_enterprise.py` (8) covers admin list pagination
  (`limit`/`offset`/`X-Total-Count`), `q` substring search on
  `/users` + `/locations`, valid + invalid `role` filter on `/users`
  (400 `invalid_role`), cross-org isolation of paginated listings,
  retention helper (`disabled` / `dry_run` / actual delete paths),
  and feature-flag JSON round-trip through `PATCH /organization`.
- Frontend: 28 Vitest. `AdminPanel.test.tsx` adds 3 tests —
  `audit_export=false` hides **Export CSV**, `bulk_import=false`
  hides **Bulk import…**, search input dispatches
  `listUsersPage({q})`.
- E2E: 21 Playwright = 12 workflow + **5 a11y** (axe-core;
  `serious`/`critical` blocking) + **4 visual** (local only; macOS
  baselines; CI skips due to OS-specific pixel rendering).

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
