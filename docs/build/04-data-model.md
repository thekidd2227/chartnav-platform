# Data Model

SQLite (local dev). Schema produced by Alembic migrations
`43ccbf363a8f → a1b2c3d4e5f6`. No schema changes in this RBAC/scoping phase.

## Tables (unchanged this phase)

### `organizations`
| column | type | constraints |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE — **immutable via API** |
| settings | TEXT | NULL — JSON object, ≤ 16 KB (phase 13, `d4e5f6a7b8c9`). Typed schema as of phase 14 (`OrganizationSettings` — `retention_days`, `default_location_id`, `feature_flags`, `extensions`). Phase 15 wires two `feature_flags` consumers in the frontend — `audit_export` and `bulk_import` (see `25-enterprise-quality-and-compliance.md`). |
| created_at | DATETIME | NOT NULL default now() |

### `locations`
| column | type | constraints |
|---|---|---|
| id | INTEGER | PK |
| organization_id | INTEGER | NOT NULL, FK → organizations(id) |
| name | VARCHAR | NOT NULL |
| created_at | DATETIME | NOT NULL default now() |

### `users`
| column | type | constraints |
|---|---|---|
| id | INTEGER | PK |
| organization_id | INTEGER | NOT NULL, FK → organizations(id) |
| email | VARCHAR | NOT NULL, UNIQUE |
| full_name | VARCHAR | NULL |
| role | VARCHAR | NOT NULL default `"admin"`, **CHECK (`admin`/`clinician`/`reviewer`)** |
| is_active | BOOLEAN | NOT NULL default `true` |
| invited_at | DATETIME | NULL — stamped on admin create (phase 13, `d4e5f6a7b8c9`) |
| invitation_token_hash | VARCHAR(128) | NULL — sha256 hex (phase 14, `e5f6a7b8c9d0`) |
| invitation_expires_at | DATETIME | NULL (phase 14) |
| invitation_accepted_at | DATETIME | NULL (phase 14) |
| created_at | DATETIME | NOT NULL default now() |

**Role vocabulary** is enforced at BOTH layers since phase 12:
- App: `app/authz.py::KNOWN_ROLES`.
- DB: CHECK constraint installed by migration `c3d4e5f6a7b8`.

Rows with `is_active = 0` are hidden from the default `GET /users`.
Admins can list them with `?include_inactive=1`. Soft-delete preserves
FK integrity for audit rows, workflow events, and encounters.

### `locations`
Unchanged except for the `is_active` column added in migration
`c3d4e5f6a7b8` (same semantics as `users.is_active`).

### `encounters` and `workflow_events`
Unchanged. `event_data` is still stored as JSON text; the shape is now
gated at the API layer by `EVENT_SCHEMAS` (see
`22-admin-governance.md`).

### `security_audit_events` (added in phase 10)

| column          | type         | constraints                           |
|-----------------|--------------|---------------------------------------|
| id              | INTEGER      | PK                                    |
| event_type      | VARCHAR(100) | NOT NULL, indexed                     |
| request_id      | VARCHAR(64)  | NULL                                  |
| actor_email     | VARCHAR(255) | NULL, indexed                         |
| actor_user_id   | INTEGER      | NULL                                  |
| organization_id | INTEGER      | NULL                                  |
| path            | VARCHAR(512) | NULL                                  |
| method          | VARCHAR(16)  | NULL                                  |
| error_code      | VARCHAR(100) | NULL                                  |
| detail          | TEXT         | NULL                                  |
| remote_addr     | VARCHAR(64)  | NULL                                  |
| created_at      | DATETIME     | NOT NULL default now(), indexed       |

No FKs — audit rows must survive user/org deletion. Populated only on
denied or suspicious access (see `18-operational-hardening.md`).
Migration: `b2c3d4e5f6a7`.

**Retention (phase 15):** `scripts/audit_retention.py` (operator-invoked
only) deletes rows older than `CHARTNAV_AUDIT_RETENTION_DAYS` — the app
never silently prunes. See `25-enterprise-quality-and-compliance.md` and
the retention runbook in `21-staging-runbook.md`.

## Seeded tenants (two, with full role coverage)

### Org 1 — `demo-eye-clinic` (id=1)
Location: `Main Clinic` (id=1).

| email                  | role      |
|------------------------|-----------|
| admin@chartnav.local   | admin     |
| clin@chartnav.local    | clinician |
| rev@chartnav.local     | reviewer  |

Encounters:

| id | patient | provider   | status         | events |
|----|---------|------------|----------------|--------|
| 1  | PT-1001 | Dr. Carter | `in_progress`  | 3      |
| 2  | PT-1002 | Dr. Patel  | `review_needed`| 5      |

### Org 2 — `northside-retina` (id=2)
Location: `Northside HQ` (id=2).

| email                   | role      |
|-------------------------|-----------|
| admin@northside.local   | admin     |
| clin@northside.local    | clinician |

Encounters:

| id | patient | provider  | status      | events |
|----|---------|-----------|-------------|--------|
| 3  | PT-2001 | Dr. Ahmed | `scheduled` | 1      |

## Relationships

Unchanged — see `docs/diagrams/er-diagram.md`.

### `patients` (phase 18)

| column             | type         | constraints |
|--------------------|--------------|-------------|
| id                 | INTEGER      | PK |
| organization_id    | INTEGER      | NOT NULL, FK → organizations(id), indexed |
| external_ref       | VARCHAR(128) | NULL (vendor id — FHIR Patient.id / Epic MRN / …) |
| patient_identifier | VARCHAR(64)  | NOT NULL; unique per org (local MRN) |
| first_name         | VARCHAR(128) | NOT NULL |
| last_name          | VARCHAR(128) | NOT NULL |
| date_of_birth      | DATE         | NULL |
| sex_at_birth       | VARCHAR(16)  | NULL — free-form; no vocabulary imposed |
| is_active          | BOOLEAN      | NOT NULL default `true` |
| created_at         | DATETIME     | NOT NULL default now() |

Unique `(organization_id, patient_identifier)` → 409
`patient_identifier_conflict`. Unique `(organization_id,
external_ref)` when set → prevents dupe mirror rows for the same
vendor id.

### `providers` (phase 18)

| column          | type         | constraints |
|-----------------|--------------|-------------|
| id              | INTEGER      | PK |
| organization_id | INTEGER      | NOT NULL, FK → organizations(id), indexed |
| external_ref    | VARCHAR(128) | NULL |
| display_name    | VARCHAR(255) | NOT NULL |
| npi             | VARCHAR(16)  | NULL; 10-digit check enforced at the API layer, DB unique per org when non-null |
| specialty       | VARCHAR(128) | NULL |
| is_active       | BOOLEAN      | NOT NULL default `true` |
| created_at      | DATETIME     | NOT NULL default now() |

### `encounters` — native linkage (phase 18)

Two new nullable FK columns land on `encounters`:

| column      | type    | constraints |
|-------------|---------|-------------|
| patient_id  | INTEGER | NULL, FK → patients(id), indexed |
| provider_id | INTEGER | NULL, FK → providers(id), indexed |

Legacy text fields (`patient_identifier`, `patient_name`,
`provider_name`) remain as denormalized display values so existing
reads keep working. In standalone mode native linkage is the
preferred source of truth going forward; integrations can populate
`external_ref` on the corresponding `patients`/`providers` row and
the encounter FK for full lineage.

## Source of truth per platform mode (phase 16 + 18)

| Object         | `standalone`     | `integrated_readthrough` (stub) | `integrated_writethrough` (stub) |
|----------------|------------------|-----------------------------------|------------------------------------|
| organization   | ChartNav         | mirrored                          | mirrored                           |
| location       | ChartNav         | mirrored                          | mirrored                           |
| user           | ChartNav         | ChartNav                          | ChartNav                           |
| encounter      | ChartNav         | external                          | external                           |
| workflow_event | ChartNav         | ChartNav                          | ChartNav                           |
| patient        | not supported    | external                          | external                           |
| document       | ChartNav (as `workflow_events`) | external (read)    | external (write via adapter)       |

Adapter implementations declare their own source-of-truth map in
`AdapterInfo.source_of_truth` — the HTTP surface at `GET /platform`
returns whatever the live adapter says. Frontend surfaces this in the
admin banner. See `26-platform-mode-and-interoperability.md`.

## Event taxonomy

| event_type           | Writer                                 | Shape                                                              |
|----------------------|----------------------------------------|--------------------------------------------------------------------|
| `encounter_created`  | `POST /encounters` / seed              | `{"status": "...", "created_by": "<email>"}`                        |
| `status_changed`     | `POST /encounters/{id}/status`         | `{"old_status": "...", "new_status": "...", "changed_by": "<email>"}` |
| user-supplied        | `POST /encounters/{id}/events`         | Any JSON                                                            |
