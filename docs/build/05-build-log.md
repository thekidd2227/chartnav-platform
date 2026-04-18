# Build Log

Reverse-chronological. Each entry is a concrete, verifiable step.

---

## 2026-04-17 — Phase: workflow state machine + filtering

### Step 1 — Baseline inspection
- Confirmed current migrations, seed, and routes compile and run as documented in `01-current-state.md`.
- Confirmed Alembic head: `a1b2c3d4e5f6`.
- No ORM in use — raw `sqlite3` calls via helpers in `routes.py`.

### Step 2 — Strict status state machine
- Added `ALLOWED_TRANSITIONS` map in `apps/api/app/api/routes.py`.
- `update_encounter_status()` now:
  - Validates `status` is in `ALLOWED_STATUSES` → else 400.
  - Treats same-status post as a no-op (no event written).
  - Validates the source→target edge is in `ALLOWED_TRANSITIONS` → else 400 with explicit message.
  - Only stamps `started_at` on entry to `in_progress` if currently NULL.
  - Stamps `completed_at` on entry to `completed` (and backfills `started_at` if null).
  - Appends `status_changed` event with `old_status` / `new_status` (replacing the prior `from` / `to` keys).
- `POST /encounters` now restricts initial status to `scheduled` or `in_progress` so deeper states can't be forged at creation.

### Step 3 — Encounter filtering
- `GET /encounters` accepts `organization_id`, `location_id`, `status`, `provider_name`.
- All filters use parameterized SQL; clauses AND-ed; ordering preserved.
- Invalid `status` filter → 400 with enumerated allowed values.

### Step 4 — Expanded seed
- `scripts_seed.py` now seeds **two** encounters:
  - PT-1001 at `in_progress` with 3 events (create, status_changed, note_draft_requested).
  - PT-1002 at `review_needed` with 5 events walking the full forward flow.
- Seed remains idempotent; both encounters and their events use composite uniqueness checks before insert.
- Timestamp handling at seed time: `started_at = CURRENT_TIMESTAMP` for any status that implies the visit began; `completed_at` only for `completed`.

### Step 5 — Local verification
- `rm -f chartnav.db && alembic upgrade head` → both migrations ran cleanly.
- `python scripts_seed.py` ran twice; event counts stable at 3 / 5.
- `uvicorn` boot clean; all baseline endpoints returned 200.
- Filter matrix verified — see `06-known-gaps.md` for matrix.
- State-machine matrix verified — 4 valid transitions 200, 4 invalid transitions 400 with explicit detail.
- OpenAPI now exposes the four new query parameters on `GET /encounters`.

### Step 6 — Documentation
- Created `docs/build/*` living docs.
- Created `docs/diagrams/*` Mermaid sources (architecture, ER, status machine, sequence).
- Generated `docs/final/chartnav-workflow-state-machine-build.html` and `.pdf`.

### Step 7 — Git hygiene
- `chartnav.db` is gitignored; not committed.
- `.venv/` is gitignored.
- Committed source + docs in a single atomic commit.
