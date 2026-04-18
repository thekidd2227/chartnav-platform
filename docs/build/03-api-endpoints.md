# API Endpoints

Base URL (local dev): `http://127.0.0.1:8000` (or whatever port uvicorn binds).

## System

| Method | Path      | Response |
|--------|-----------|----------|
| GET    | `/health` | `{"status":"ok"}` |
| GET    | `/`       | `{"service":"chartnav-api","version":"0.1.0"}` |

## Org / location / user (read-only)

| Method | Path             | Notes                         |
|--------|------------------|-------------------------------|
| GET    | `/organizations` | Ordered by id.                |
| GET    | `/locations`     | Ordered by id.                |
| GET    | `/users`         | Ordered by id.                |

## Encounters

### GET `/encounters`

Query parameters (all optional, combinable, AND-ed):

| Param             | Type   | Notes                                  |
|-------------------|--------|----------------------------------------|
| `organization_id` | int≥1  | Exact match.                           |
| `location_id`     | int≥1  | Exact match.                           |
| `status`          | string | Must be in `ALLOWED_STATUSES` or 400.  |
| `provider_name`   | string | Exact match (case-sensitive).          |

Ordering: `ORDER BY id`. All SQL uses parameterized `?` placeholders.

### GET `/encounters/{encounter_id}`

`404 encounter_not_found` if missing.

### GET `/encounters/{encounter_id}/events`

`404 encounter_not_found` if the parent encounter does not exist.
Returns events oldest-first (`ORDER BY id`). `event_data` is JSON-parsed
before being returned to the client when it is valid JSON.

### POST `/encounters`

Body:
```json
{
  "organization_id": 1,
  "location_id": 1,
  "patient_identifier": "PT-1003",
  "patient_name": "Alex Chen",
  "provider_name": "Dr. Ortiz",
  "scheduled_at": "2026-04-18T14:30:00Z",
  "status": "scheduled"
}
```

Rules:
- `status` defaults to `"scheduled"` and may only be `scheduled` or `in_progress` at creation (deeper states can't be forged).
- `organization_id` + `location_id` must exist and the location must belong to the organization → otherwise 400.
- A `workflow_events` row `encounter_created` is appended automatically.
- Returns the full encounter row (201).

### POST `/encounters/{encounter_id}/events`

Body:
```json
{ "event_type": "note_draft_completed", "event_data": { "template": "glaucoma-initial" } }
```

`event_data` may be any JSON value (object/array/string/number/null). Objects
and arrays are stored as canonical JSON (sorted keys). Strings pass through
as-is.

### POST `/encounters/{encounter_id}/status`

Body: `{ "status": "draft_ready" }`.

- Validated against `ALLOWED_STATUSES` and `ALLOWED_TRANSITIONS`
  (`02-workflow-state-machine.md`).
- Same-status post is a no-op (no event recorded).
- On success, stamps `started_at`/`completed_at` per lifecycle rules
  and appends a `status_changed` event.

Error examples:
- `400 invalid_status` — unknown string.
- `400 invalid_transition` — disallowed edge in the state machine.
- `404 encounter_not_found` — no such encounter.
