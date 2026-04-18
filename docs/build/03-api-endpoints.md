# API Endpoints

Base URL (local dev): `http://127.0.0.1:8000`.

Auth: every endpoint tagged **🔒** requires header `X-User-Email: <seeded user email>`.
Some endpoints are further role-gated — see `07-auth-and-scoping.md`.

All error bodies have the standardized shape:
```json
{"detail": {"error_code": "<stable_code>", "reason": "<human message>"}}
```

## System (open)

| Method | Path      |
|--------|-----------|
| GET    | `/health` |
| GET    | `/`       |

## Identity

| Method | Path  | Auth | Roles |
|--------|-------|------|-------|
| GET    | `/me` | 🔒   | any   |

## Org metadata (🔒, org-scoped, any role)

| Method | Path             | Behavior                                       |
|--------|------------------|------------------------------------------------|
| GET    | `/organizations` | Returns only the caller's org row.             |
| GET    | `/locations`     | `WHERE organization_id = caller.org`.          |
| GET    | `/users`         | `WHERE organization_id = caller.org`.          |

## Encounters (🔒, org-scoped + RBAC)

### GET `/encounters`
Any authenticated role. Always filtered to `caller.organization_id`.

Optional query params (AND-ed, parameterized):

| Param             | Rule                                                   |
|-------------------|---------------------------------------------------------|
| `organization_id` | Must equal `caller.org` — else 403.                    |
| `location_id`     | Narrows within caller org.                             |
| `status`          | Must be in `ALLOWED_STATUSES` — else 400.              |
| `provider_name`   | Exact match.                                            |

### GET `/encounters/{id}` — any role
404 if missing or cross-org.

### GET `/encounters/{id}/events` — any role
404 if parent missing or cross-org.

### POST `/encounters` — **admin, clinician**
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
- Reviewer → 403 `role_cannot_create_encounter`.
- `organization_id` must match caller org → 403 otherwise.
- `location_id` must exist and belong to caller org → 400 or 403 otherwise.
- Initial status restricted to `scheduled` or `in_progress`.

### POST `/encounters/{id}/events` — **admin, clinician**
Reviewer → 403 `role_cannot_create_event`. 404 if cross-org.

### POST `/encounters/{id}/status`
404 if cross-org. Status must be valid. Transition must be legal by the
state machine (`02-workflow-state-machine.md`). **Per-edge** RBAC:

| From            | To             | Roles allowed                 |
|-----------------|----------------|-------------------------------|
| scheduled       | in_progress    | admin, clinician              |
| in_progress     | draft_ready    | admin, clinician              |
| draft_ready     | in_progress    | admin, clinician              |
| draft_ready     | review_needed  | admin, reviewer               |
| review_needed   | draft_ready    | admin, reviewer               |
| review_needed   | completed      | admin, reviewer               |

Same-state POST = no-op (200). Role violation → 403 `role_cannot_transition`. Invalid transition → 400 `invalid_transition`.

## Error code inventory

| Code                               | HTTP | Origin                              |
|------------------------------------|------|-------------------------------------|
| `missing_auth_header`              | 401  | auth transport                      |
| `unknown_user`                     | 401  | auth transport                      |
| `auth_mode_unsupported`            | 500  | `CHARTNAV_AUTH_MODE` set to unknown |
| `role_forbidden`                   | 403  | generic `require_roles` gate        |
| `role_cannot_create_encounter`    | 403  | POST /encounters                    |
| `role_cannot_create_event`         | 403  | POST /encounters/{id}/events        |
| `role_cannot_transition`           | 403  | POST /encounters/{id}/status        |
| `cross_org_access_forbidden`       | 403  | body/query asserts another org      |
| `encounter_not_found`              | 404  | missing or cross-org encounter      |
| `location_not_found`               | 400  | bad location_id                     |
| `invalid_status`                   | 400  | unknown status string               |
| `invalid_initial_status`           | 400  | POST /encounters with bad init      |
| `invalid_transition`               | 400  | disallowed state-machine edge       |
