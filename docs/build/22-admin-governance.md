# Admin Governance

Phase 12 adds real administrative control on top of the RBAC +
observability stack: admins can manage users and locations for their
org, the DB enforces role vocabulary, workflow events are schema-bound,
and the encounter list paginates. No more read-only metadata; no more
free-form event drift.

## 1. DB-level role constraint

Migration `c3d4e5f6a7b8` adds a CHECK constraint:

```
CHECK (role IN ('admin', 'clinician', 'reviewer'))
```

SQLite's `batch_alter_table` rebuilds the `users` table to install it;
Postgres picks it up as a normal `ADD CONSTRAINT`. `app.authz.KNOWN_ROLES`
matches exactly. Inserts with any other role now bounce at the
`IntegrityError` layer, before the app even sees them.

The same migration adds `is_active BOOLEAN NOT NULL DEFAULT true` to
`users` and `locations` so metadata can be soft-deleted without
breaking FK integrity on historical encounters, workflow events, or
audit rows.

## 2. Admin CRUD API

All admin endpoints require role `admin` via `authz.require_admin`. Any
other role gets `403 role_admin_required`. All operations are strictly
scoped to the caller's org.

### Users
| Method | Path               | Body / Query                                                | Errors                             |
|--------|--------------------|-------------------------------------------------------------|------------------------------------|
| GET    | `/users`           | `?include_inactive=1`                                       | —                                  |
| POST   | `/users`           | `{email, full_name?, role}`                                 | `invalid_role` (400), `user_email_taken` (409), `role_admin_required` (403) |
| PATCH  | `/users/{id}`      | `{email?, full_name?, role?, is_active?}`                   | `invalid_role`, `user_email_taken`, `cannot_demote_self`, `cannot_deactivate_self`, `user_not_found` (cross-org) |
| DELETE | `/users/{id}`      | soft-delete (sets `is_active=0`)                            | `cannot_deactivate_self`, `user_not_found` |

### Locations
| Method | Path                    | Body / Query                         | Errors                      |
|--------|-------------------------|--------------------------------------|-----------------------------|
| GET    | `/locations`            | `?include_inactive=1`                | —                           |
| POST   | `/locations`            | `{name}`                             | `role_admin_required`       |
| PATCH  | `/locations/{id}`       | `{name?, is_active?}`                | `location_not_found` (cross-org) |
| DELETE | `/locations/{id}`       | soft-delete                          | `location_not_found`        |

Self-protection rules:
- An admin cannot demote their own role (`cannot_demote_self`).
- An admin cannot deactivate their own account (`cannot_deactivate_self`).

Cross-org accesses return **404 `user_not_found` / `location_not_found`** —
same shape as "doesn't exist" so the API doesn't leak existence of other
orgs' data.

## 3. Event schema discipline

`app.api.routes.EVENT_SCHEMAS` is the single source of truth for
workflow events. New or unlisted types are rejected.

| event_type              | required keys           | Who writes it                         |
|-------------------------|-------------------------|---------------------------------------|
| `encounter_created`     | `status`                | Server, on `POST /encounters`          |
| `status_changed`        | `old_status`, `new_status` | Server, on successful status transition |
| `note_draft_requested`  | `requested_by`          | Client (admin / clinician)            |
| `note_draft_completed`  | `template`              | Client                                |
| `note_reviewed`         | `reviewer`              | Client                                |
| `manual_note`           | `note`                  | Client — generic operator-authored event |

Validation lives in `_validate_event(event_type, event_data)`:
- Unknown `event_type` → 400 `invalid_event_type` with the full
  allowed list in the reason.
- `event_data` missing when required → 400 `invalid_event_data`.
- `event_data` not a JSON object → 400 `invalid_event_data`.
- Missing required keys → 400 `invalid_event_data` listing them.

Server-written events bypass the validator (they construct known-good
payloads directly). That keeps `encounter_created` / `status_changed`
hot paths free of needless checks while client-submitted events run
through a strict gate.

## 4. Pagination

`GET /encounters` now accepts:

| param    | default | range    |
|----------|---------|----------|
| `limit`  | 50      | 1 .. 500 |
| `offset` | 0       | ≥ 0      |

The response is still a JSON array (backward compatible), but three
headers carry the page metadata:

| Header           | Meaning                                |
|------------------|----------------------------------------|
| `X-Total-Count`  | Full filtered count (pre limit/offset) |
| `X-Limit`        | Echo of the applied limit              |
| `X-Offset`       | Echo of the applied offset             |

Existing clients that ignore headers keep working (they just see the
first page). The frontend client has a dedicated `listEncountersPage`
helper that surfaces the totals.

## 5. Frontend — admin UI

- Header shows an **Admin** button for role `admin` only.
- Clicking it opens a modal with two tabs: **Users** and **Locations**.
- **Users** tab: create form (email / full name / role), table with
  inline role select + deactivate/reactivate buttons. Self-row is
  disabled so admins can't lock themselves out. Role change goes
  through `PATCH /users/{id}` with the exact pydantic model; failures
  surface the `{error_code, reason}` envelope in a banner.
- **Locations** tab: create form (name), table with inline name edit
  (click to edit; Enter saves, Escape cancels) and Deactivate buttons.
- Encounter list now paginates 25 rows at a time with Prev/Next
  controls + "N-M of T" status line.

## 6. Tests

### Backend (`apps/api/tests/test_admin.py`) — 20 tests
- DB role CHECK rejects unknown role (raises `IntegrityError`).
- Admin can create / update / deactivate users and locations in own org.
- Non-admin (clinician / reviewer) receives 403 `role_admin_required` on every admin write.
- Admin cannot create a user with an unknown role (`invalid_role`).
- Admin cannot duplicate emails (`user_email_taken`).
- Pydantic email validation returns 422.
- Admin cannot demote / deactivate self.
- Cross-org admin mutations return 404 `user_not_found` / `location_not_found`.
- Soft-deleted users/locations disappear from default list; `?include_inactive=1` shows them.
- `POST /encounters/{id}/events` rejects unknown `event_type` (`invalid_event_type`) and invalid `event_data` (`invalid_event_data`), accepts valid `manual_note`.
- Pagination: headers returned, offset works, filters + pagination combine correctly.

### Frontend (`apps/web/src/test/AdminPanel.test.tsx`) — 5 Vitest tests
- Lists users on open.
- Create-user submit flows through `createUser` and shows success banner.
- Create-user 409 conflict surfaces error banner verbatim.
- Self-row role select + deactivate button are disabled.
- Create-location flow on the Locations tab.

Plus an App-level test asserting admin role sees the Admin button; clinician / reviewer do not.

### E2E (`apps/web/tests/e2e/workflow.spec.ts`) — 2 new scenarios
- Admin opens the panel, creates a user and a location end-to-end against the live stack; both appear in their respective tables.
- Non-admin (clinician) never sees the Admin button.

## 7. What this phase explicitly does NOT do

- No org-level CRUD — `PATCH /organizations/{id}` is deliberately absent. Renaming an org is a rare event; add it when it's real.
- No per-org SSO configuration.
- No bulk-import.
- No invitation / email workflow.
- **Phase 13 update — audit log UI shipped.** The `security_audit_events` table is now exposed at `GET /security-audit-events` and surfaced in the Admin panel → Audit log tab with filters + pagination. See `23-operator-control-plane.md`.
- **Phase 14 update — real invitation workflow shipped.** `POST /users/{id}/invite` (admin) + `POST /invites/accept` (unauth, token IS the credential), 7-day expiry, sha256-only storage, per-user one-shot raw token banner, minimal `/invite?invite=<token>` accept screen. Bulk user import, audit CSV export, and typed org settings also landed this phase. Full contract: `24-invitations-and-governance.md`.

## User lifecycle signal — `invited_at` (phase 13)

`users.invited_at` is stamped whenever an admin creates a user. The
admin panel renders an "Invited" badge for active users with
`invited_at` set. ChartNav does not send email; the badge is a real
signal that the operator should communicate out-of-band and is not a
token-based invitation flow. See `23-operator-control-plane.md` for
the scope trade-offs.
