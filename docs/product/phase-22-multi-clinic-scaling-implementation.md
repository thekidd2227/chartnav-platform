# Phase 22 — Multi-Clinic / Multi-Provider Scaling Foundation

> **Status:** Implemented (this PR).
> **Type:** New backend migration (4 tables) + new router (17
> endpoints) + new admin-facing frontend panel + 32 backend tests
> + 7 frontend tests.
> **Builds on:** Phase 20B (Structured Data Layer), Phase 20C
> (Role-Based Dashboards), Phase 21A (retina + glaucoma tracking),
> Phase 21B (imaging pipeline).
> **Branch:** `feature/phase-22-multi-clinic-scaling`.

This phase turns ChartNav from a single-clinic demo into a
**multi-location ophthalmology platform**. It persists the
operational scaffolding a group practice needs to run real-world
operations: which providers serve which locations, which rooms
exist at each location, when each provider is scheduled at each
location, and the per-day operating hours of each location.

It does **not** ship: appointment booking, calendar integration,
patient-facing scheduling, automated room assignment, automated
provider-for-visit recommendation, billing / claims / insurance,
HIPAA compliance controls, device-vendor integrations, real PHI,
or autonomous decision support.

## How this extends the existing platform

Phase 22 is additive. None of the existing components are
modified beyond a single sidebar entry:

- Phase 20B `work_queue_items` is **referenced** by the new
  dashboard summary endpoints (counts by status / priority /
  role / queue type, plus per-location and per-provider
  rollups). The schema is unchanged.
- Phase 20C `RoleDashboard.tsx` is unchanged.
- Phase 21A `SpecialtyTrackingPanel.tsx` is unchanged.
- Phase 21B `ImagingPipelinePanel.tsx` is unchanged.
- `EyeDiagramPanel`, `RetinalDrawingCanvas`,
  `RetinalProposalReview`, `NoteWorkspace`, `ScribeSessionPanel`,
  `clinicalShortcuts`, `quickComments` are all unchanged.

What changes:

- 4 new tables persist multi-clinic scaffolding.
- 17 new endpoints (CRUD for the 4 resources + 3 dashboard
  summaries).
- A new `MultiClinicDashboard.tsx` admin-facing panel renders the
  operational rollup.
- A new sidebar entry under OPERATIONS routes admin identities to
  the new panel; non-admin identities see the entry as disabled.

## Data model — 4 tables

| Table | Purpose |
|---|---|
| `provider_location_assignments` | Which providers serve which locations (a provider may serve multiple; a location may have multiple). `is_primary` + `is_active` flags. Unique on `(org, provider, location)`. |
| `location_rooms` | Exam / imaging / testing / procedure / admin / other rooms (lanes) per location. CHECK-constrained `room_type` enum. Unique on `(org, location, name)`. |
| `provider_schedule_blocks` | Clinic / surgery / injection / testing / admin / unavailable / other blocks per provider per location per time window. CHECK enforces `start_at < end_at` and `capacity >= 0`. |
| `clinic_operating_hours` | Per-location, per-day-of-week open / close hours with explicit `is_closed` flag. CHECK enforces `day_of_week` in 0..6. Unique on `(org, location, day_of_week)`. |

All four tables are `organization_id`-scoped. Foreign keys
enforce referential integrity within the org. The route layer
enforces the standard 404-on-cross-org no-existence-leak
invariant.

Booleans use `sa.text("true")` / `sa.text("false")` server
defaults for Postgres compatibility (no `1`/`0` literals).

Migration revision: `a8b9c0d1e2f3_phase_22_multi_clinic_scaling`
(chains off Phase 21B `f7a8b9c0d1e2`).

## API surface — 17 endpoints

### Provider-location assignments (3)

| Method | Path | Role policy |
|---|---|---|
| GET | `/provider-location-assignments` | any read role |
| POST | `/provider-location-assignments` | **admin only** |
| PATCH | `/provider-location-assignments/{id}` | **admin only** |

Query filters: `provider_id`, `location_id`, `is_active`. Create
is idempotent on `(org, provider, location)` — re-posting returns
the existing row.

### Location rooms (3)

| Method | Path | Role policy |
|---|---|---|
| GET | `/locations/{id}/rooms` | any read role |
| POST | `/locations/{id}/rooms` | **admin only** |
| PATCH | `/location-rooms/{id}` | **admin only** |

Validates `room_type` against the enum; invalid → `400
invalid_room_type`.

### Provider schedule blocks (3)

| Method | Path | Role policy |
|---|---|---|
| GET | `/provider-schedule-blocks` | any read role |
| POST | `/provider-schedule-blocks` | **admin only** |
| PATCH | `/provider-schedule-blocks/{id}` | **admin only** |

Query filters: `provider_id`, `location_id`, `block_type`,
`start_after`, `start_before`. Validates `block_type` enum,
`start_at < end_at`, `capacity >= 0`. Invalid → `400
invalid_block_type` / `400 invalid_time_range`. Pydantic enforces
`capacity >= 0` at the schema layer (422).

### Clinic operating hours (3)

| Method | Path | Role policy |
|---|---|---|
| GET | `/clinic-operating-hours` | any read role |
| POST | `/clinic-operating-hours` | **admin only** |
| PATCH | `/clinic-operating-hours/{id}` | **admin only** |

POST is upsert on `(org, location, day_of_week)` — re-posting
returns the existing row. Validates `day_of_week` 0..6 and
`opens_at < closes_at` when not closed.

### Dashboard summaries (3)

| Method | Path | Role policy |
|---|---|---|
| GET | `/locations/{id}/dashboard` | any read role |
| GET | `/providers/{id}/dashboard` | any read role |
| GET | `/admin/multi-clinic-summary` | **admin only** |

Location dashboard returns: `open_queue_items`,
`ready_for_workup`, `imaging_needed`, `ready_for_doctor`,
`review_needed`, `provider_count`, `room_count`,
`active_schedule_blocks_today`. Provider dashboard returns:
`assigned_queue_items`, `ready_for_doctor`, `imaging_review`,
`signoff_needed`, `review_needed`, `schedule_blocks_today`,
`locations_today`. Admin summary returns per-location and
per-provider rollups plus `queue_by_status` / `queue_by_priority`
/ `queue_by_assigned_role` / `queue_by_queue_type`.

### Role rationale

- **admin** — full read + write across all four resources +
  admin multi-clinic summary.
- **clinician / reviewer / technician / front_desk** — read
  across all four resources + their own location / provider
  dashboards. Schedule and room metadata is operational, not
  clinical — read access is broad.
- **Writes** (create / patch) are admin-only.

All cross-org reads / writes return `404` (not `403`), preserving
the no-existence-leak invariant.

## Audit guarantee

Every create / patch records a metadata-only audit row.
`detail` contains only IDs, type / status / day-of-week / capacity
values. Names, opens_at / closes_at strings, and any free-text
fields are NEVER included in audit detail. Enforced by
`test_create_emits_metadata_only_audit` which seeds a sentinel
room name (`VERY-SECRET-ROOM-NAME`) and asserts it does not
appear in any audit row.

## Frontend

### `apps/web/src/api.ts`

Adds 6 enums / interfaces for the 4 resources + 3 dashboard
shapes, plus 15 typed functions:

- `listProviderLocationAssignments`, `createProviderLocationAssignment`,
  `updateProviderLocationAssignment`
- `listLocationRooms`, `createLocationRoom`, `updateLocationRoom`
- `listProviderScheduleBlocks`, `createProviderScheduleBlock`,
  `updateProviderScheduleBlock`
- `listClinicOperatingHours`, `createClinicOperatingHours`,
  `updateClinicOperatingHours`
- `getLocationDashboard`, `getProviderDashboard`,
  `getAdminMultiClinicSummary`

### `apps/web/src/MultiClinicDashboard.tsx`

Single self-contained admin panel. Renders:

- Summary cards: total locations, total providers, total open
  queue items, queue types active.
- Split view: locations list on the left + providers list on
  the right.
- Selecting a location fetches `/locations/{id}/dashboard` and
  renders a detail card (open queue, ready-for-workup, imaging
  needed, ready-for-doctor, review needed, active providers,
  active rooms, schedule blocks today).
- Selecting a provider fetches `/providers/{id}/dashboard` and
  renders a detail card (assigned queue, ready-for-doctor,
  imaging review, sign-off needed, review needed, schedule
  blocks today, locations today).
- Breakdown tables by status / priority / role / queue type.

Disclaimer subtitle:

> "Cross-location, cross-provider operational view. Read-only
> summary built from the work queue, schedule blocks, location
> rooms, and provider-location assignments. Metadata only — no
> clinical body text, no billing, no patient messaging."

Non-admin identities see a blocked-state placeholder and the
component never calls the admin summary endpoint.

### `apps/web/src/App.tsx`

A new sidebar entry under OPERATIONS — **Multi-Clinic** — opens
the panel. Admin identities click through; non-admin identities
see the entry as disabled. The CORE > Dashboard (Phase 20C) and
CORE > Encounters entries are unchanged.

### `apps/web/src/styles.css`

Appends ~190 lines of `.multi-clinic__*` styles using existing
`--cn-*` tokens. No new design language.

## Tests

### Backend — 32 tests (`tests/test_phase_22_multi_clinic.py`)

| Class | Coverage |
|---|---|
| `TestAssignments` | Admin CRUD + filter + duplicate idempotent + non-admin blocked + cross-org provider/location 404 + clinician read allowed. |
| `TestRooms` | Admin CRUD + invalid `room_type` rejected (400) + non-admin blocked + cross-org location 404 + clinician read allowed. |
| `TestScheduleBlocks` | Admin CRUD + invalid `block_type` rejected + invalid time range rejected + invalid capacity rejected (Pydantic 422) + filters by provider/location/block_type/date + non-admin blocked + cross-org 404. |
| `TestOperatingHours` | Admin CRUD with upsert behavior + invalid `day_of_week` rejected (422) + invalid time range rejected (400) + cross-org location 404 + non-admin blocked. |
| `TestDashboards` | Location dashboard counts + provider dashboard counts + admin multi-clinic summary aggregates + non-admin blocked from admin summary + cross-org 404 + Org 2 admin sees only Org 2 in summary. |
| `TestAuditAndAuth` | Audit detail excludes sentinel `VERY-SECRET-ROOM-NAME` + unauthenticated returns 401 across the four key paths. |

### Frontend — 7 tests (`test/MultiClinicDashboard.test.tsx`)

- Non-admin renders blocked placeholder + no API calls.
- Reviewer is also blocked.
- Admin renders summary cards + locations + providers +
  breakdown tables; selecting picks defaults.
- Clicking a different location refetches the location
  dashboard.
- Empty state renders when no locations / providers exist.
- Error path renders the error banner.
- Forbidden-vocabulary + button scan: no billing / claims /
  patient-messaging / submit-order / send-referral copy or
  controls.

## Out of scope (intentional)

- ❌ No HIPAA compliance controls (deferred to Phase 23).
- ❌ No real PHI introduced.
- ❌ No automated appointment booking.
- ❌ No calendar / scheduling-system integration.
- ❌ No patient-facing scheduling surfaces.
- ❌ No automated room assignment.
- ❌ No automated provider-for-visit recommendation.
- ❌ No billing / claims / insurance / payment handling.
- ❌ No automatic orders / referrals / patient messaging.
- ❌ No autonomous diagnosis / image interpretation.
- ❌ No device-vendor integration.
- ❌ No DICOM ingestion.
- ❌ No binary image storage expansion beyond Phase 21B's
  metadata-only scope.
- ❌ No website / commercial-deck / media updates.
- ❌ No `chartnavmd.com` publish.

## Files touched

- `apps/api/alembic/versions/a8b9c0d1e2f3_phase_22_multi_clinic_scaling.py` (new)
- `apps/api/app/api/multi_clinic.py` (new)
- `apps/api/app/main.py` (router include)
- `apps/api/tests/test_phase_22_multi_clinic.py` (new, 32 tests)
- `apps/web/src/api.ts` (Phase 22 types/functions appended)
- `apps/web/src/MultiClinicDashboard.tsx` (new)
- `apps/web/src/App.tsx` (top-view switch + OPERATIONS >
  Multi-Clinic sidebar entry)
- `apps/web/src/styles.css` (multi-clinic CSS)
- `apps/web/src/test/MultiClinicDashboard.test.tsx` (new, 7
  tests)
- `docs/product/phase-22-multi-clinic-scaling-implementation.md`
  (this file)

## Migration roundtrip

`a8b9c0d1e2f3` applied cleanly via `alembic upgrade head` on a
fresh SQLite DB locally. Postgres parity is exercised by the CI
`backend-postgres` job.

## Next phases enabled

- **Phase 23** — HIPAA-regulated deployment readiness
  implementation (production auth hardening, approved hosting,
  backups, monitoring, vendor review, incident contacts).
- **Future** — Calendar / scheduling-system adapters, automated
  room assignment, capacity-aware workup routing. None of these
  are in Phase 22.

## Remaining limitations

- No admin-side **write** UI inside `MultiClinicDashboard.tsx`
  yet — assignments / rooms / schedule blocks / operating hours
  are write-API-only. A follow-up admin-tooling PR will add the
  write forms.
- No work-queue auto-assignment from schedule blocks. The lane
  cycle currently surfaces *what's queued* but not *who'll see
  it next.*
- No multi-org tenant-pooling features. ChartNav still serves
  one organization per request; cross-org dashboards are
  intentionally out of scope.
