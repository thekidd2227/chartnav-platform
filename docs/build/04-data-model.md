# Data Model

SQLite (local dev). Schema reproduced by Alembic migrations
`43ccbf363a8f → a1b2c3d4e5f6`. No schema changes in this auth phase.

## Tables

### `organizations`
| column     | type         | constraints                   |
|------------|--------------|-------------------------------|
| id         | INTEGER      | PK                            |
| name       | VARCHAR(255) | NOT NULL                      |
| slug       | VARCHAR(255) | NOT NULL, UNIQUE              |
| created_at | DATETIME     | NOT NULL, default `now()`     |

### `locations`
| column          | type     | constraints                           |
|-----------------|----------|---------------------------------------|
| id              | INTEGER  | PK                                    |
| organization_id | INTEGER  | NOT NULL, FK → organizations(id)      |
| name            | VARCHAR  | NOT NULL                              |
| created_at      | DATETIME | NOT NULL, default `now()`             |

### `users`
| column          | type     | constraints                           |
|-----------------|----------|---------------------------------------|
| id              | INTEGER  | PK                                    |
| organization_id | INTEGER  | NOT NULL, FK → organizations(id)      |
| email           | VARCHAR  | NOT NULL, UNIQUE                      |
| full_name       | VARCHAR  | NULL                                  |
| role            | VARCHAR  | NOT NULL, default `"admin"`           |
| created_at      | DATETIME | NOT NULL, default `now()`             |

`users.email` is the authentication key for the dev auth layer.
`users.organization_id` is the authoritative source of caller org context.

### `encounters`
Unchanged. Indexed on `organization_id`, `location_id`, `patient_identifier`, `status`.

### `workflow_events`
Unchanged. Indexed on `encounter_id`, `event_type`.

## Relationships

```
organizations 1─┬─* locations
                ├─* users          (identity source for dev auth)
                └─* encounters ─* workflow_events
locations     1─* encounters
```

See `docs/diagrams/er-diagram.md`.

## Seeded tenants (two, for scoping proof)

### Org 1 — `demo-eye-clinic` (id=1)
- Location: `Main Clinic` (id=1)
- Admin: `admin@chartnav.local` / id=1

| encounter_id | patient  | provider    | status          | events |
|--------------|----------|-------------|-----------------|--------|
| 1            | PT-1001  | Dr. Carter  | `in_progress`   | 3      |
| 2            | PT-1002  | Dr. Patel   | `review_needed` | 5      |

### Org 2 — `northside-retina` (id=2)
- Location: `Northside HQ` (id=2)
- Admin: `admin@northside.local` / id=2

| encounter_id | patient  | provider   | status      | events |
|--------------|----------|------------|-------------|--------|
| 3            | PT-2001  | Dr. Ahmed  | `scheduled` | 1      |

## Event taxonomy

| event_type           | When                                   | Shape                                                       |
|----------------------|----------------------------------------|-------------------------------------------------------------|
| `encounter_created`  | On `POST /encounters` / seed           | `{"status":"...", "created_by":"<email>"}`                  |
| `status_changed`     | Every successful transition            | `{"old_status":"...", "new_status":"...", "changed_by":"<email>"}` |
| user-supplied        | `POST /encounters/{id}/events`         | Any JSON                                                    |
