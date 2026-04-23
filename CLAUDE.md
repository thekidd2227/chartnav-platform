# CLAUDE.md — chartnav-platform

Operating instructions for Claude Code working in this repository.

## What this repo is

Monorepo for the ChartNav clinical charting platform. Ophthalmology-first.
Two deployable apps plus infra and scripts.

```
apps/api    FastAPI + SQLAlchemy Core + PyJWT. Alembic migrations.
apps/web    Vite + React 18 + TypeScript. Vitest + Playwright.
infra/      Docker Compose starter.
qa/         QA artifacts and smoke plans.
scripts/    Dev + seed scripts.
docs/       Engineering docs.
```

The API is the system of record. The web app is a thin client. No
business rules live on the client. Lifecycle, release gating, signing,
amendment, and audit are server-authoritative.

## Non-negotiable invariants

1. **Server-authoritative lifecycle.** Every note transition goes through
   `apps/api/app/services/note_lifecycle.py`. Do not inline transition
   logic in routes. Do not branch on `draft_status` in the client to
   decide whether a write is allowed — always call the API.
2. **Org isolation.** Every DB read that joins user-owned rows goes
   through the `_load_note_for_caller` helper or an equivalent org-scoped
   filter. A route that returns a row without filtering on the caller's
   org is a bug.
3. **Immutability after sign.** Signed notes are never mutated in place.
   Corrections happen via `amend_signed_note`, which creates a new
   `note_versions` row and marks the original `superseded_at`. The
   `content_fingerprint` on a signed row is frozen and is used to detect
   silent DB drift.
4. **Audit everything that matters.** Sign, blocked sign, review, amend,
   export, and admin-surface actions emit to the audit sink introduced
   in wave 2. Adding a new governance action means adding an audit event.
5. **Release gates are structured.** `compute_release_blockers` returns
   a list of `ReleaseBlocker` objects with `code`, `message`, `severity`,
   and optional `field`. Do not collapse them to a boolean. The UI
   renders each one.
6. **Migrations only move forward.** `alembic upgrade head` is the single
   way to evolve schema. Never edit a shipped revision. Add a new one.

## Layout cheatsheet

```
apps/api/app/
  api/routes.py              HTTP surface. Thin. Orchestrates services.
  services/
    note_lifecycle.py        States, transitions, edge roles, blockers,
                             attestation template, content fingerprint.
    note_amendments.py       amend_signed_note, amendment_chain.
    kpi_scorecard.py         Latency + quality aggregations.
  db/                        SQLAlchemy Core tables + session.
  security/                  Auth, audit sink, org scoping.
alembic/versions/            Migrations. Head: e1f2a3041508.
tests/                       Pytest. One sqlite file per test.

apps/web/src/
  api.ts                     Typed HTTP client. Single source of truth
                             for server contract types.
  NoteWorkspace.tsx          Note authoring surface.
  NoteLifecyclePanel.tsx     Lifecycle status + blockers + review/amend.
  admin/                     Admin-only surfaces.
  test/                      Vitest component tests.
tests-e2e/                   Playwright specs.
```

## How to work here

**Reading first.** Before editing a service, read it. Before editing a
route, read the service it calls. The lifecycle and amendment services
are small on purpose — read them in full, not by grep.

**Tests are the contract.** If you change lifecycle, blocker, or amend
behavior, the corresponding pytest in `apps/api/tests/test_note_lifecycle_wave3.py`
must be updated in the same change. Do not "fix" a test by loosening
the assertion unless you can explain why the looser invariant is
correct.

**Ports and dev servers.** `.claude/launch.json` drives the dev runners.
`autoPort: true` is set at root and per-configuration; do not pin
ports in `runtimeArgs`. If a port is in use, the runner picks a free
one. Do not kill unrelated processes to claim a port.

**Never commit** generated PHI, real patient data, real transcripts,
or live secrets. Fixtures live in `apps/api/tests/fixtures/` and use
synthetic names and dates.

## Validation checklist before claiming a change is done

From repo root (each must be green):

```
# API
cd apps/api && .venv/bin/pytest -q

# Web typecheck + unit
cd apps/web && npm run typecheck && npm test

# Web build (catches import/export drift)
cd apps/web && npm run build

# E2E smoke if UI touched
cd apps/web && npm run test:e2e
```

A change that edits `apps/api/app/services/note_lifecycle.py`,
`note_amendments.py`, `routes.py`, or any migration is not done until
the full pytest suite passes, not just the tests you named.

## What not to do

- Do not introduce business logic in the React layer.
- Do not bypass `compute_release_blockers` at sign time.
- Do not edit a shipped Alembic revision. Add a new one.
- Do not add a new lifecycle state without updating
  `LIFECYCLE_TRANSITIONS`, `EDGE_ROLES`, every blocker branch that
  references states, and the frontend `NoteDraftStatus` union.
- Do not introduce hidden admin powers. Every admin capability must
  be auditable.
- Do not add marketing copy to platform UI strings. Plain clinical
  language only.

## Where to start for common tasks

- **Add a release gate:** extend `compute_release_blockers` in
  `note_lifecycle.py`, then add a test case in
  `test_note_lifecycle_wave3.py`, then surface it in
  `NoteLifecyclePanel.tsx` only if it needs distinct UI.
- **Add a role permission:** edit `EDGE_ROLES`. No other file should
  encode the mapping.
- **Add a KPI:** extend the query in `kpi_scorecard.py` and the payload
  shape. Update the KPI test.
- **Add an admin action:** route → service → audit event → test.
  Skipping the audit event is a bug, not a follow-up.
