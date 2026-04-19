# API Endpoints

Base URL (local dev): `http://127.0.0.1:8000`. All error bodies use
`{"detail": {"error_code": "...", "reason": "..."}}`.

## System (open)

| Method | Path      |
|--------|-----------|
| GET    | `/health` |
| GET    | `/`       |

## Identity

| Method | Path  | Auth | Roles |
|--------|-------|------|-------|
| GET    | `/me` | 🔒   | any   |

## Org metadata (🔒, org-scoped)

| Method | Path             | Behavior                                       |
|--------|------------------|------------------------------------------------|
| GET    | `/organizations` | Returns only caller's org row.                 |
| GET    | `/locations`     | `WHERE organization_id = caller.org`. Supports `limit` (1..500, default 100), `offset` (≥0), `q` (substring search on `name`), plus `include_inactive` (admin). Emits `X-Total-Count`, `X-Limit`, `X-Offset` headers. |
| GET    | `/users`         | `WHERE organization_id = caller.org`. Supports `limit`, `offset`, `q` (substring on `email` or `full_name`), `role` (valid roles only — invalid → 400 `invalid_role`), `include_inactive` (admin). Emits `X-Total-Count`, `X-Limit`, `X-Offset` headers. |

## Native clinical layer (🔒, org-scoped) — phase 18

| Method | Path          | Behavior |
|--------|---------------|----------|
| GET    | `/patients`   | `WHERE organization_id = caller.org`. Supports `limit`/`offset`/`q` (substring on MRN or name)/`include_inactive`. Emits `X-Total-Count`, `X-Limit`, `X-Offset`. |
| POST   | `/patients`   | Admin or clinician creates a native patient. `integrated_readthrough` → 409 `native_write_disabled_in_integrated_mode`. Duplicate `(org, patient_identifier)` → 409 `patient_identifier_conflict`. |
| GET    | `/providers`  | `WHERE organization_id = caller.org`. Supports `limit`/`offset`/`q` (substring on `display_name`/`specialty`/`npi`)/`include_inactive`. Headers same as above. |
| POST   | `/providers`  | Admin only. `integrated_readthrough` → 409 `native_write_disabled_in_integrated_mode`. `invalid_npi` (400) when `npi` present but not 10 digits. `npi_conflict` (409) on duplicate NPI within org. |

Encounter responses now also include `patient_id` + `provider_id`
nullable FKs pointing at the rows above.

## Encounter write gating per platform mode (phase 20)

| Route                              | `standalone`          | `integrated_readthrough` | `integrated_writethrough` |
|------------------------------------|-----------------------|---------------------------|----------------------------|
| `GET /encounters`                  | native adapter (SQL)  | adapter dispatch          | adapter dispatch           |
| `GET /encounters/{id}`             | native adapter        | adapter dispatch          | adapter dispatch           |
| `POST /encounters`                 | allowed               | **409 `encounter_write_unsupported`** | **409 `encounter_write_unsupported`** |
| `POST /encounters/{id}/status`     | native state machine  | **409 `encounter_write_unsupported`** | adapter dispatch; **501 `adapter_write_not_supported`** if adapter raises `AdapterNotSupported` |
| `POST /encounters/{id}/events`     | allowed               | allowed (ChartNav-native) | allowed                    |
| `POST /encounters/{id}/inputs`     | allowed               | allowed                   | allowed                    |
| `POST /encounters/{id}/notes/generate` | allowed           | allowed (native-only for now; see `31-adapter-driven-encounters.md`) | allowed |

Every encounter row now carries `_source` (`chartnav` in standalone,
adapter key in integrated modes) and `_external_ref` where applicable.

## Transcript → note workflow (🔒, org-scoped) — phase 19

| Method | Path                                    | Role | Notes |
|--------|-----------------------------------------|------|-------|
| `POST` | `/encounters/{id}/inputs`               | admin + clinician | `input_type`, optional `transcript_text` (required for text_paste / manual_entry / imported_transcript); text inputs default `processing_status=completed`; audio uploads default `queued`. |
| `GET`  | `/encounters/{id}/inputs`               | any authed | List DESC by id. |
| `POST` | `/encounters/{id}/notes/generate`       | admin + clinician | Creates `extracted_findings` + `note_versions` v+1. Defaults to most recent `completed` input; returns `{note, findings}`. |
| `GET`  | `/encounters/{id}/notes`                | any authed | Versions DESC. |
| `GET`  | `/note-versions/{id}`                   | any authed | Returns `{note, findings}`. |
| `PATCH`| `/note-versions/{id}`                   | admin + clinician | Edits narrative; auto-flips to `revised` + `generated_by=manual`. Signed/exported → 409 `note_immutable`. |
| `POST` | `/note-versions/{id}/submit-for-review` | admin + clinician | `draft` / `revised` → `provider_review`. |
| `POST` | `/note-versions/{id}/sign`              | admin + clinician only | Stamps `signed_at` + `signed_by_user_id`. Reviewer → 403 `role_cannot_sign`. |
| `POST` | `/note-versions/{id}/export`            | admin + clinician | `signed` → `exported`; stamps `exported_at`. Pre-sign → 409 `note_not_signed`. |

Emits audit events: `encounter_input_created`,
`note_version_generated`, `note_version_submitted`,
`note_version_signed`, `note_version_exported`.

New error codes: `invalid_input_type`, `transcript_required`,
`invalid_processing_status`, `input_not_found`, `input_not_ready`,
`no_completed_input`, `invalid_note_format`, `invalid_note_status`,
`invalid_note_transition`, `note_immutable`, `role_cannot_sign`,
`note_already_signed`, `note_not_signed`, `note_not_found`.

## Encounters (🔒, org-scoped + RBAC)

### GET `/encounters`
Any authenticated role. Always `WHERE organization_id = caller.org`.

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

### POST `/encounters` — admin, clinician
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

### POST `/encounters/{id}/events` — admin, clinician
Reviewer → 403. 404 if cross-org.

### POST `/encounters/{id}/status`
Per-edge RBAC:

| From            | To             | Roles allowed                 |
|-----------------|----------------|-------------------------------|
| scheduled       | in_progress    | admin, clinician              |
| in_progress     | draft_ready    | admin, clinician              |
| draft_ready     | in_progress    | admin, clinician              |
| draft_ready     | review_needed  | admin, reviewer               |
| review_needed   | draft_ready    | admin, reviewer               |
| review_needed   | completed      | admin, reviewer               |

Same-state POST = no-op (200). Role violation → 403 `role_cannot_transition`. Invalid transition → 400 `invalid_transition`. Cross-org → 404.

## Admin endpoints (🔒 `admin` role only, org-scoped)

| Method | Path                    | Body                                          |
|--------|-------------------------|-----------------------------------------------|
| POST   | `/users`                | `{email, full_name?, role}`                   |
| PATCH  | `/users/{id}`           | `{email?, full_name?, role?, is_active?}`     |
| DELETE | `/users/{id}`           | soft-delete (sets `is_active=0`)              |
| POST   | `/locations`            | `{name}`                                      |
| PATCH  | `/locations/{id}`       | `{name?, is_active?}`                         |
| DELETE | `/locations/{id}`       | soft-delete                                   |

Error codes introduced:
- `role_admin_required` (403) — non-admin tried an admin action.
- `invalid_role` (400) — role not in `{admin, clinician, reviewer}`.
- `user_email_taken` (409) — email uniqueness conflict.
- `cannot_demote_self` (400), `cannot_deactivate_self` (400) — admin self-protection.
- `user_not_found` / `location_not_found` (404) — includes cross-org lookups (no existence leak).

See `22-admin-governance.md` for the governance model.

### Organization settings (🔒 org-scoped)

| Method | Path            | Auth            | Body                          |
|--------|-----------------|-----------------|-------------------------------|
| GET    | `/organization` | any authed role | —                             |
| PATCH  | `/organization` | admin only      | `{ name?, settings? }`        |

Rules:
- `slug` is **immutable** — not accepted by PATCH.
- `settings` is a JSON object; non-object → 422; serialized > 16 KB → 400 `settings_too_large`.
- PATCH always scopes to caller's org — no cross-org parameter exists.

### Invitations (phase 14)

| Method | Path                     | Auth   |
|--------|--------------------------|--------|
| POST   | `/users/{id}/invite`     | admin  |
| POST   | `/invites/accept`        | unauth |

Admin response returns raw `invitation_token` **once**; only the
sha256 hash is stored. 7-day expiry. Accept body `{ token }`. Errors:
`user_not_found` (404 cross-org), `user_inactive` (400),
`user_already_accepted` (400), `invalid_invite` (400),
`invite_expired` (400).

### Bulk user import

| Method | Path           | Auth   |
|--------|----------------|--------|
| POST   | `/users/bulk`  | admin  |

Body: `{ users: [{ email, full_name?, role }, ...] }` (1..500 rows).
Response: `{ created, skipped, errors, summary }`. Per-row validation;
one bad row never aborts the batch. Strictly org-scoped.

### Audit export

| Method | Path                                 | Auth  |
|--------|--------------------------------------|-------|
| GET    | `/security-audit-events/export`      | admin |

Same filters and org-scoping as the audit read endpoint. Returns
`text/csv` with a stable column order and a timestamped attachment
filename.

### Security audit read (🔒 admin only)

| Method | Path                           |
|--------|--------------------------------|
| GET    | `/security-audit-events`       |

Query: `event_type`, `error_code`, `actor_email`, `q` (substring
match against `path` or `detail`), `limit` (1..500, default 50),
`offset` (≥0). Response: array ordered newest-first; pagination
metadata on `X-Total-Count` / `X-Limit` / `X-Offset` headers.

Scoping: rows where `organization_id = caller.org` **OR**
`organization_id IS NULL` (pre-auth failures have no caller and are
visible to every admin; cross-org denials with an identity stay
private to that identity's org). See `23-operator-control-plane.md`
for the rationale.

## Event validation (phase 12)

`POST /encounters/{id}/events` is now schema-bound:

| event_type              | required keys           |
|-------------------------|-------------------------|
| `manual_note`           | `note`                  |
| `note_draft_requested`  | `requested_by`          |
| `note_draft_completed`  | `template`              |
| `note_reviewed`         | `reviewer`              |

Server-written types (`encounter_created`, `status_changed`) bypass the
validator — they're constructed internally with known-good payloads.
Unknown types → 400 `invalid_event_type`. Non-object or missing-keys
`event_data` → 400 `invalid_event_data`.

## Pagination (phase 12)

`GET /encounters` accepts `limit` (1..500, default 50) and `offset` (≥0,
default 0). Response body is still an array — **backward compatible**.
Totals come on response headers: `X-Total-Count`, `X-Limit`, `X-Offset`.

## Error code inventory

| Code                               | HTTP | Origin                              |
|------------------------------------|------|-------------------------------------|
| `missing_auth_header`              | 401  | auth transport                      |
| `unknown_user`                     | 401  | auth transport                      |
| `auth_mode_unsupported`            | 500  | `CHARTNAV_AUTH_MODE` set to unknown |
| `role_forbidden`                   | 403  | generic `require_roles`             |
| `role_cannot_create_encounter`    | 403  | POST /encounters                    |
| `role_cannot_create_event`         | 403  | POST /encounters/{id}/events        |
| `role_cannot_transition`           | 403  | POST /encounters/{id}/status        |
| `cross_org_access_forbidden`       | 403  | body/query asserts other org        |
| `encounter_not_found`              | 404  | missing or cross-org encounter      |
| `location_not_found`               | 400  | bad location_id                     |
| `invalid_status`                   | 400  | unknown status string               |
| `invalid_initial_status`           | 400  | POST /encounters bad init           |
| `invalid_transition`               | 400  | disallowed state-machine edge       |

## Verification

This full surface is now locked in by two layers:
- pytest (`apps/api/tests/`) — 25 tests, per-test ephemeral SQLite.
- Live smoke (`apps/api/scripts/smoke.sh`) — 9 assertions against a running API.

Both run in CI on every push/PR. See `09-ci-and-deploy-hardening.md`.
