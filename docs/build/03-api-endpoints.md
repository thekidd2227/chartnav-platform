# API Endpoints

Base URL (local dev): `http://127.0.0.1:8000`.

Auth: every endpoint tagged **🔒** requires header `X-User-Email: <seeded user email>`.
See `07-auth-and-scoping.md` for the full model.

## System (open)

| Method | Path      | Response |
|--------|-----------|----------|
| GET    | `/health` | `{"status":"ok"}` |
| GET    | `/`       | `{"service":"chartnav-api","version":"0.1.0"}` |

## Identity

| Method | Path  | Auth | Response |
|--------|-------|------|----------|
| GET    | `/me` | 🔒   | `{user_id, email, full_name, role, organization_id}` |

## Org / location / user (open, read-only)

These are **not** org-scoped this phase. Tracked in `06-known-gaps.md`.

| Method | Path             |
|--------|------------------|
| GET    | `/organizations` |
| GET    | `/locations`     |
| GET    | `/users`         |

## Encounters (🔒 org-scoped)

### GET `/encounters`

Always filtered to `caller.organization_id`.

Additional optional query parameters (all AND-ed, parameterized):

| Param             | Type   | Notes                                              |
|-------------------|--------|----------------------------------------------------|
| `organization_id` | int≥1  | Must equal `caller.organization_id` — else 403.    |
| `location_id`     | int≥1  | Narrows within caller org.                         |
| `status`          | string | Must be in `ALLOWED_STATUSES` or 400.              |
| `provider_name`   | string | Exact match.                                       |

### GET `/encounters/{encounter_id}`

Returns encounter if it belongs to caller's org. Otherwise **404 `encounter_not_found`** — same response whether it doesn't exist or belongs to another org (no cross-org existence oracle).

### GET `/encounters/{encounter_id}/events`

404 if the parent encounter doesn't exist or is cross-org.
Returns events oldest-first; `event_data` is JSON-parsed when valid.

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
- `organization_id` **must equal** `caller.organization_id` → else 403 `cross_org_access_forbidden`.
- `location_id` must exist and belong to caller's org → else 400 `location_not_found` or 403.
- `status` defaults to `"scheduled"`; only `scheduled` or `in_progress` permitted at creation (deeper states can't be forged).
- Appends `workflow_events` row `encounter_created` with `{status, created_by}`.

### POST `/encounters/{encounter_id}/events`

404 if cross-org. Body:
```json
{ "event_type": "note_draft_completed", "event_data": { "template": "glaucoma-initial" } }
```

`event_data` may be any JSON value. Objects/arrays stored as canonical JSON.

### POST `/encounters/{encounter_id}/status`

404 if cross-org. Body: `{ "status": "draft_ready" }`.

- Validated against `ALLOWED_STATUSES` and `ALLOWED_TRANSITIONS` (`02-workflow-state-machine.md`).
- Same-status = no-op.
- On success: stamps `started_at`/`completed_at` per lifecycle rules, appends `status_changed` event with `{old_status, new_status, changed_by}`.

### Error summary

| Code | Detail                          | When                                          |
|------|---------------------------------|-----------------------------------------------|
| 401  | `missing_auth_header`           | `X-User-Email` missing or empty.              |
| 401  | `unknown_user`                  | Email not in `users`.                         |
| 403  | `cross_org_access_forbidden`    | Body/query asserts a different org or location. |
| 400  | `invalid_status`                | Bad status string.                            |
| 400  | `invalid_transition: a -> b…`   | Disallowed state-machine edge.                |
| 400  | `invalid_initial_status: …`     | Creating with status other than scheduled/in_progress. |
| 400  | `location_not_found`            | `location_id` does not exist.                 |
| 404  | `encounter_not_found`           | Missing or cross-org encounter.               |
