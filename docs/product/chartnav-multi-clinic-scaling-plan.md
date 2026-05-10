# ChartNav Multi-Clinic / Multi-Provider Scaling — Plan

> **Phase scope target:** Phase 22 (build), Phase 20A (this plan).
> **Type:** Planning only.

ChartNav already supports multiple `locations` per `organization`
(20-table audit confirms `locations` table is shipped + scoped).
Encounters carry a nullable `location_id`. What's missing is the
**operational scaffolding** that lets a multi-location practice
actually run as such:

- Which providers practice at which locations (and on which days)?
- Which rooms exist at each location, and what kind?
- When is each clinic open?
- What's the cross-location admin view?

This plan defines the minimum-viable multi-clinic schema +
endpoint surface, scoped tightly so it doesn't accidentally
become a scheduling product.

## What this plan is not

- ❌ Not a patient appointment booking system (booking lives in
  the practice's existing scheduling system)
- ❌ Not a clinician calendar / EHR-replacement
- ❌ Not an in-room device assignment system
- ❌ Not a billing-by-location system
- ✅ A multi-clinic operational scaffold so the role-based
  dashboards can answer "which encounters / queue items belong
  to which location, which provider, which room?"

## Existing surfaces this plan extends

| Existing | This plan adds |
|---|---|
| `organizations` (tenant root) | unchanged |
| `locations` (org-scoped, name + is_active) | adds rooms, operating hours, schedule blocks |
| `users` (admin/clinician/reviewer) | (Phase 20C adds `front_desk` and `technician`) |
| `providers` (org-scoped directory; NPI + specialty) | adds explicit location assignments |
| `encounters` (already has `location_id` nullable FK) | unchanged; dashboards filter on existing FK |

## Proposed tables

### `provider_location_assignments`

One row per (provider, location). A provider can practice at
multiple locations; each assignment can be marked primary +
active.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `provider_id` | int FK → providers | |
| `location_id` | int FK → locations | |
| `is_primary` | bool | one primary per provider |
| `is_active` | bool | soft-disable |
| `created_at` | datetime | |

Unique constraint `(provider_id, location_id)`.

### `location_rooms`

Per-location rooms — exam rooms, imaging rooms, injection
rooms, ASC procedure rooms.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `location_id` | int FK | |
| `name` | string | "Exam 1", "OCT room", "Injection 2", "ASC bay 3" |
| `room_type` | string | `exam` \| `imaging` \| `injection` \| `procedure` \| `dilation_bay` \| `consultation` \| `other` |
| `is_active` | bool | |
| `created_at` | datetime | |

### `provider_schedule_blocks`

Lightweight schedule scaffold. **Not** a booking system — these
are coarse availability blocks (clinic, surgery, ASC, off).
Consumed by the front-desk + admin dashboards to answer "is
this provider in clinic on Wednesday?"

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `provider_id` | int FK | |
| `location_id` | int FK | nullable (off-blocks) |
| `start_at` | datetime | |
| `end_at` | datetime | |
| `block_type` | string | `clinic` \| `surgery` \| `asc` \| `meeting` \| `off` |
| `capacity` | int | nullable; informational ("12 slots / 4 hours") |
| `created_at` | datetime | |

### `clinic_operating_hours`

Per-location weekly hours. Front-desk dashboard reads from this.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `location_id` | int FK | |
| `day_of_week` | int | 0–6 (Sunday–Saturday) |
| `opens_at` | time | |
| `closes_at` | time | |
| `is_closed` | bool | flag for "closed all day" |
| `created_at`, `updated_at` | datetime | |

Unique constraint `(location_id, day_of_week)`.

## How dashboards consume these tables

| Dashboard | Reads from |
|---|---|
| Front desk | `clinic_operating_hours` (today's hours), `provider_schedule_blocks` (who's in clinic), `location_rooms` (room status — future) |
| Technician | `provider_schedule_blocks` (which provider's queue is active), `location_rooms` (room assignment — future) |
| Doctor | `provider_location_assignments` (which locations the doctor practices at) |
| Reviewer | location-agnostic by default; optional location filter |
| Admin | cross-location aggregates from `encounters` joined with `provider_location_assignments` and `location_rooms` |

## Existing org-isolation pattern (preserved)

Every new table follows the same pattern as the rest of the
schema:

- `organization_id NOT NULL` foreign key
- read endpoint `ensure_same_org(caller, target_org_id)` guard
- 404 (not 403) on cross-org access — preserves the no-existence-
  leak invariant the audit framework already enforces

## How location/provider filters appear in the UI

| Surface | Filter affordance |
|---|---|
| Top-bar location selector (admin/front-desk roles) | Dropdown of `locations WHERE is_active`. Persisted to per-user preference. |
| Top-bar provider selector (admin/front-desk roles) | Dropdown of `providers JOIN provider_location_assignments WHERE location_id = current_location` |
| Doctor dashboard | No selector — defaults to `assigned_user_id = caller.user_id` |
| Reviewer dashboard | Optional location filter for cross-location practices |
| Patient header | Shows the current encounter's location + provider already (existing behavior) |

## Required APIs

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /provider-location-assignments` | any | list assignments (filtered by org) |
| `POST /provider-location-assignments` | admin | assign provider to location |
| `PATCH /provider-location-assignments/{id}` | admin | toggle primary / active |
| `GET /locations/{id}/rooms` | any | list rooms |
| `POST /locations/{id}/rooms` | admin | add room |
| `PATCH /locations/{id}/rooms/{room_id}` | admin | edit room |
| `GET /provider-schedule-blocks` | any | list blocks (filtered by org + optional provider/date range) |
| `POST /provider-schedule-blocks` | admin | create block |
| `GET /clinic-operating-hours` | any | list weekly hours |
| `POST /clinic-operating-hours` | admin | set hours |
| `PATCH /clinic-operating-hours/{id}` | admin | edit hours |
| `GET /locations/{id}/dashboard` | any (filtered) | location-scoped operational rollup |
| `GET /providers/{id}/dashboard` | any (filtered) | provider-scoped operational rollup |
| `GET /admin/multi-clinic-summary` | admin | cross-location aggregates |

## API audit / RBAC contract (applies to every endpoint above)

- All reads scoped via `ensure_same_org` against
  `target_org_id` derived from the path's primary entity.
- All writes require `admin` role unless explicitly noted.
- Audit row written for every write — `event_type`, `actor`,
  `path`, `error_code`. **No** location floor plans, **no**
  schedule body, **no** room descriptions in audit.
- Cross-org access returns `404` (no existence leak).

## Frontend consumers (per endpoint, summary)

| Endpoint | Frontend consumer |
|---|---|
| `provider-location-assignments` | Top-bar location/provider selectors; admin settings panel |
| `locations/{id}/rooms` | Technician dashboard (room status — Phase 22+); admin settings |
| `provider-schedule-blocks` | Front-desk dashboard (today's providers); admin schedule view |
| `clinic-operating-hours` | Front-desk dashboard; admin settings |
| `locations/{id}/dashboard` | Admin location drill-down |
| `providers/{id}/dashboard` | Admin provider drill-down |
| `admin/multi-clinic-summary` | Admin cross-location summary card |

## Required tests

- Migration up/down on SQLite + Postgres
- Org isolation on every endpoint
- Cross-org `provider-location-assignments` write returns 403
- Cross-org `locations/{id}/rooms` read returns 404
- Unique constraint on `(provider_id, location_id)` enforced
- Unique constraint on `(location_id, day_of_week)` enforced
- `is_primary` constraint: at most one primary per provider per
  org (validated on write; UI surfaces the "demote previous
  primary" flow before write)
- Soft-delete pattern: `is_active = false` rather than DELETE
  for assignments and rooms (preserves historical encounter →
  location/provider links)
- Schedule-block conflict guard at admin write time (warn but
  do not block on overlap)
- Audit row written for every write

## Hard constraints

- ❌ No automatic appointment booking
- ❌ No automatic provider assignment from encounter creation
  (clinician + location are entered by front desk / admin)
- ❌ No automatic room assignment from queue position
- ❌ No automatic clinic-hours enforcement (e.g., no automatic
  "encounter closed because clinic is closed" — clinical state
  is clinician-driven)
- ❌ No multi-org cross-location view (org isolation absolute)
- ✅ Every multi-location aggregate respects RBAC at drill-down
- ✅ Every soft-deleted assignment / room preserves historical
  references so the encounter audit trail stays valid

# Section 6 — API Design (cross-cutting)

This section consolidates the API surface across the four
data-layer plans (structured data, specialty modules, imaging,
multi-clinic) so a future implementation phase can read one
table.

## Cross-cutting conventions

- Every endpoint accepts a `Caller` (existing `app.auth`
  contract) and resolves `caller.organization_id`.
- Every list endpoint supports `?limit=` + `?cursor=`
  pagination and a small set of typed filters.
- Every write endpoint writes a `security_audit_events` row
  with `event_type` set to `data_modify_<entity>` and
  `detail` limited to entity ID + action.
- Every cross-org read returns `404` (preserves the no-
  existence-leak invariant).
- Every endpoint is documented in the OpenAPI spec; no hidden
  endpoints.

## Endpoint inventory

### Structured data layer (Phase 20B)

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/segments` | any | list segments + counts |
| POST | `/segments` | admin | create segment definition |
| PATCH | `/segments/{id}` | admin | edit / disable |
| GET | `/patients/{id}/segments` | any | list segments containing patient |
| POST | `/patients/{id}/segments` | admin | manual add |
| DELETE | `/patients/{id}/segments/{segment_id}` | admin | manual remove |
| GET | `/patients/{id}/tags` | clinician | list tags |
| POST | `/patients/{id}/tags` | clinician | add tag |
| DELETE | `/patients/{id}/tags/{tag_id}` | clinician | remove tag |
| GET | `/patients/{id}/problem-list` | clinician | list problem-list rows |
| POST | `/patients/{id}/problem-list` | clinician | add problem |
| PATCH | `/patients/{id}/problem-list/{id}` | clinician | edit / resolve |
| GET | `/work-queues` | any (filtered) | dashboard read |
| POST | `/work-queues` | admin / system | manual queue creation |
| PATCH | `/work-queues/{id}` | role with assignment | claim / progress / complete |
| GET | `/role-views` | any | resolve presets for caller's role |
| POST | `/role-views` | any | save preset |
| PATCH | `/role-views/{id}` | owner | edit |

### Specialty modules (Phase 21A)

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/patients/{id}/retina` | clinician/reviewer | list retina tracking rows |
| POST | `/patients/{id}/retina` | clinician | create tracking row |
| PATCH | `/patients/{id}/retina/{id}` | clinician | update |
| GET | `/patients/{id}/retina/injections` | clinician/reviewer | injection log |
| POST | `/patients/{id}/retina/injections` | clinician | record injection |
| GET | `/patients/{id}/glaucoma` | clinician/reviewer | list tracking rows |
| POST | `/patients/{id}/glaucoma` | clinician | create tracking row |
| PATCH | `/patients/{id}/glaucoma/{id}` | clinician | update |
| GET | `/patients/{id}/glaucoma/iop` | clinician/reviewer | IOP series |
| POST | `/patients/{id}/glaucoma/iop` | clinician/technician | record IOP |
| GET | `/patients/{id}/glaucoma/visual-fields` | clinician/reviewer | VF series |
| POST | `/patients/{id}/glaucoma/visual-fields` | clinician | record VF metadata |
| (similar) | Cornea, Cataract, Oculoplastics, Pediatric — same shape | | |

### Imaging pipeline (Phase 21B)

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/patients/{id}/imaging-studies` | clinician/reviewer/admin | list patient studies |
| POST | `/patients/{id}/imaging-studies` | clinician/technician | create study record |
| GET | `/imaging-studies/{id}` | clinician/reviewer | study detail |
| PATCH | `/imaging-studies/{id}` | clinician | update notes / status |
| POST | `/imaging-studies/{id}/files` | clinician/technician | upload file |
| PATCH | `/imaging-studies/{id}/review` | clinician | mark reviewed_at |

### Multi-clinic (Phase 22)

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/provider-location-assignments` | any | list |
| POST | `/provider-location-assignments` | admin | assign |
| PATCH | `/provider-location-assignments/{id}` | admin | edit |
| GET | `/locations/{id}/rooms` | any | list rooms |
| POST | `/locations/{id}/rooms` | admin | add |
| PATCH | `/locations/{id}/rooms/{room_id}` | admin | edit |
| GET | `/provider-schedule-blocks` | any | list blocks |
| POST | `/provider-schedule-blocks` | admin | create block |
| GET | `/clinic-operating-hours` | any | list weekly hours |
| POST | `/clinic-operating-hours` | admin | set hours |
| PATCH | `/clinic-operating-hours/{id}` | admin | edit hours |
| GET | `/locations/{id}/dashboard` | any (filtered) | location-scoped rollup |
| GET | `/providers/{id}/dashboard` | any (filtered) | provider-scoped rollup |
| GET | `/admin/multi-clinic-summary` | admin | cross-location summary |
