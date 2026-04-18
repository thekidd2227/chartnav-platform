# Data Model

SQLite (local dev). Schema produced by Alembic migrations
`43ccbf363a8f → a1b2c3d4e5f6`. No schema changes in this RBAC/scoping phase.

## Tables (unchanged this phase)

### `organizations`
| column | type | constraints |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(255) | NOT NULL |
| slug | VARCHAR(255) | NOT NULL, UNIQUE |
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
| role | VARCHAR | NOT NULL default `"admin"` |
| created_at | DATETIME | NOT NULL default now() |

**Application-level role vocabulary** (enforced by `app/authz.py`):
`admin`, `clinician`, `reviewer`. The column remains a free VARCHAR in
SQL; constraint is enforced at the app layer. If you need a DB-level
CHECK constraint, add it in a future migration.

### `encounters` and `workflow_events`
Unchanged.

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

## Event taxonomy

| event_type           | Writer                                 | Shape                                                              |
|----------------------|----------------------------------------|--------------------------------------------------------------------|
| `encounter_created`  | `POST /encounters` / seed              | `{"status": "...", "created_by": "<email>"}`                        |
| `status_changed`     | `POST /encounters/{id}/status`         | `{"old_status": "...", "new_status": "...", "changed_by": "<email>"}` |
| user-supplied        | `POST /encounters/{id}/events`         | Any JSON                                                            |
