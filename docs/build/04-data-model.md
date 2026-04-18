# Data Model

SQLite (local dev). Schema reproduced by Alembic migrations
`43ccbf363a8f → a1b2c3d4e5f6`.

## Tables

### `organizations`
| column     | type         | constraints                          |
|------------|--------------|--------------------------------------|
| id         | INTEGER      | PK                                   |
| name       | VARCHAR(255) | NOT NULL                             |
| slug       | VARCHAR(255) | NOT NULL, UNIQUE                     |
| created_at | DATETIME     | NOT NULL, default `now()`            |

### `locations`
| column          | type     | constraints                          |
|-----------------|----------|--------------------------------------|
| id              | INTEGER  | PK                                   |
| organization_id | INTEGER  | NOT NULL, FK → organizations(id)     |
| name            | VARCHAR  | NOT NULL                             |
| created_at      | DATETIME | NOT NULL, default `now()`            |

### `users`
| column          | type     | constraints                          |
|-----------------|----------|--------------------------------------|
| id              | INTEGER  | PK                                   |
| organization_id | INTEGER  | NOT NULL, FK → organizations(id)     |
| email           | VARCHAR  | NOT NULL, UNIQUE                     |
| full_name       | VARCHAR  | NULL                                 |
| role            | VARCHAR  | NOT NULL, default `"admin"`          |
| created_at      | DATETIME | NOT NULL, default `now()`            |

### `encounters`
| column              | type     | constraints                                  |
|---------------------|----------|----------------------------------------------|
| id                  | INTEGER  | PK                                           |
| organization_id     | INTEGER  | NOT NULL, FK → organizations(id), indexed    |
| location_id         | INTEGER  | NOT NULL, FK → locations(id), indexed        |
| patient_identifier  | VARCHAR  | NOT NULL, indexed                            |
| patient_name        | VARCHAR  | NULL                                         |
| provider_name       | VARCHAR  | NOT NULL                                     |
| status              | VARCHAR  | NOT NULL, default `"scheduled"`, indexed     |
| scheduled_at        | DATETIME | NULL                                         |
| started_at          | DATETIME | NULL (stamped on entering `in_progress`)     |
| completed_at        | DATETIME | NULL (stamped on entering `completed`)       |
| created_at          | DATETIME | NOT NULL, default `now()`                    |

### `workflow_events`
| column        | type     | constraints                                  |
|---------------|----------|----------------------------------------------|
| id            | INTEGER  | PK                                           |
| encounter_id  | INTEGER  | NOT NULL, FK → encounters(id), indexed       |
| event_type    | VARCHAR  | NOT NULL, indexed                            |
| event_data    | TEXT     | NULL (canonical JSON string)                 |
| created_at    | DATETIME | NOT NULL, default `now()`                    |

## Relationships

```
organizations 1─┬─* locations
                └─* users
                └─* encounters ─* workflow_events
locations     1─* encounters
```

See `docs/diagrams/er-diagram.md` for a Mermaid ER rendering.

## Event taxonomy (emitted automatically)

| event_type           | When                                          | Shape                                              |
|----------------------|-----------------------------------------------|----------------------------------------------------|
| `encounter_created`  | On `POST /encounters`                         | `{"status": "<initial>"}`                          |
| `status_changed`     | On every successful status transition         | `{"old_status": "...", "new_status": "..."}`       |
| user-supplied        | `POST /encounters/{id}/events`                | Any JSON                                           |

## Seeded demo data

Two encounters are seeded for `demo-eye-clinic` / `Main Clinic`:

| id | patient    | provider    | status          | event count | lifecycle covered    |
|----|------------|-------------|-----------------|-------------|----------------------|
| 1  | PT-1001    | Dr. Carter  | `in_progress`   | 3           | scheduled → in_progress |
| 2  | PT-1002    | Dr. Patel   | `review_needed` | 5           | scheduled → in_progress → draft_ready → review_needed |
