# Invitations, Governance & Bulk Operations

Phase 14 closes the "scaffolding only" loops from the operator
control plane:

- invitations are a real token flow (admin issues, user accepts) —
  no email delivery, but everything else operates like production;
- organization `settings` is typed and extra-forbidden (plus an
  `extensions` bucket for forward-compat drift);
- audit events export to CSV;
- `event_data` payloads now enforce value types / enum membership;
- bulk user import lands (JSON body, per-row pass/fail).

## 1. Invitation workflow

### Data shape (migration `e5f6a7b8c9d0`)
Three new columns on `users`:
- `invitation_token_hash TEXT NULL` — **sha256 hex only**; the raw
  token is never stored. Indexed for O(1) accept lookups.
- `invitation_expires_at DATETIME NULL` — 7 days from issue.
- `invitation_accepted_at DATETIME NULL` — set on successful accept;
  presence blocks re-issue.

### API

| Method | Path                   | Auth    | Notes                                                                  |
|--------|------------------------|---------|------------------------------------------------------------------------|
| POST   | `/users/{id}/invite`   | admin   | Issues (or re-issues) a token. Returns raw token ONCE. Inactive user → 400 `user_inactive`. Already-accepted → 400 `user_already_accepted`. Cross-org → 404 `user_not_found`. |
| POST   | `/invites/accept`      | unauth  | Body: `{ token }`. Invalid / expired / replayed → 400 `invalid_invite` / `invite_expired`. On success the hash is cleared so the same token can't be reused. |

### Security notes
- Only a sha256 hash is persisted. The raw token is echoed back in
  the admin response and is expected to be shared out-of-band.
- Tokens are generated via `secrets.token_urlsafe(32)` (≥ 256 bits
  of entropy).
- `/invites/accept` is rate-limited via the middleware's protected
  prefix list (`/invites`).
- Re-issuing an invite overwrites the hash: the old token is
  immediately invalid.
- Accept is idempotent in the wrong direction — a second accept
  with the same token fails with `invalid_invite` because the hash
  was cleared on the first success.

### UI
- Admin panel → Users tab: every active, non-self user row gets an
  **Invite** button. Clicking it surfaces the raw token in a
  one-shot banner with a "Dismiss" button; the user is told to
  copy immediately.
- Minimal `/invite?invite=<token>` accept screen in the frontend
  (no router dependency; see `apps/web/src/InviteAccept.tsx` +
  `main.tsx` branch). On success it stores the accepted email as
  `localStorage.chartnav.devIdentity` so the main app picks it up
  for header-mode dev use.

### Intentionally out of scope
- Email delivery / templating.
- Self-serve signup.
- IdP pre-provisioning (the app will always map back through the
  `users` table; that's the production-auth claim seam).

## 2. Organization settings — typed schema

`app.api.routes.OrganizationSettings` (pydantic `extra=forbid`):

| field                   | type                  | notes                                      |
|-------------------------|-----------------------|--------------------------------------------|
| `default_provider_name` | `str` ≤ 255           | suggestion used by UI for create flows     |
| `encounter_page_size`   | `int 10..200`         | caller-facing default page size            |
| `audit_page_size`       | `int 10..200`         | audit-log default page size                |
| `feature_flags`         | `dict[str, bool]`     | on/off toggles                             |
| `extensions`            | `dict[str, Any]`      | explicit forward-compat bucket             |

PATCH `/organization` body:
```json
{
  "name": "Demo Eye Clinic",
  "settings": {
    "default_provider_name": "Dr. Carter",
    "encounter_page_size": 50,
    "feature_flags": {"beta_ui": true},
    "extensions": {"brand_color": "#0B6E79"}
  }
}
```

Validation:
- Top-level unknown keys → 422 (pydantic `extra=forbid`).
- Oversized blob (≥ 16 KB after JSON serialization) → 400 `settings_too_large`.
- Stored as JSON text in `organizations.settings`; normalized via
  `model_dump(exclude_none=True)` so the blob only contains keys the
  operator actually set.

UI (`AdminPanel.tsx` → Organization tab): dedicated inputs for each
typed field, plus an **Extensions** textarea for the forward-compat
bucket. The frontend no longer exposes a raw settings textarea.

## 3. Audit export

`GET /security-audit-events/export` — admin only. Honors the same
filters as the audit read endpoint (`event_type`, `error_code`,
`actor_email`, `q`) and the same org-scoping rule (caller's org OR
`NULL`). Returns CSV with a stable column order:

```
id, created_at, event_type, error_code, actor_email, actor_user_id,
organization_id, method, path, request_id, remote_addr, detail
```

Browser download: Content-Disposition attachment with a timestamped
filename (`chartnav-audit-YYYYMMDDTHHMMSSZ.csv`).

Frontend: admin panel → Audit log tab has an **Export CSV** button
that fetches with the auth header and triggers a local download
(required because `<a href>` alone can't send `X-User-Email`).

## 4. Event payload hardening

Beyond "required keys exist" (phase 12), each event type now enforces
value types / enum membership:

| event_type              | hardening                                                                 |
|-------------------------|---------------------------------------------------------------------------|
| `status_changed`        | `old_status` & `new_status` must be in `ALLOWED_STATUSES`                 |
| `encounter_created`     | `status` must be in `ALLOWED_STATUSES`                                    |
| `manual_note`           | `note` must be a non-empty string ≤ 4000 chars                            |
| `note_draft_requested`  | `requested_by` non-empty string; optional `template` non-empty string     |
| `note_draft_completed`  | `template` non-empty string; optional `length_words` non-negative int     |
| `note_reviewed`         | `reviewer` non-empty string ≤ 255                                         |

Any violation → 400 `invalid_event_data` with a specific reason.

## 5. Bulk user import

`POST /users/bulk` (admin only) accepts up to 500 rows at a time.

Request body:
```json
{
  "users": [
    { "email": "a@x.test", "full_name": "A", "role": "clinician" },
    { "email": "b@x.test", "role": "reviewer" }
  ]
}
```

Response:
```json
{
  "created": [/* full user rows */],
  "skipped": [{ "row": 0, "email": "admin@chartnav.local", "error_code": "user_email_taken" }],
  "errors":  [{ "row": 1, "email": "x@y.test", "error_code": "invalid_role" }],
  "summary": { "requested": 4, "created": 2, "skipped": 1, "errors": 1 }
}
```

Rules:
- Per-row validation — one bad row does not abort the batch.
- Strictly org-scoped: every created row belongs to `caller.organization_id`.
- `invited_at` stamped on every newly created row (bulk import is by
  definition an "invitation needed" event).
- Admin-only (`role_admin_required` 403 otherwise).
- Empty batch → 422 (pydantic `min_length=1`).

UI: Users tab → **Bulk import…** opens a dialog with a CSV-like
textarea (`email,full_name,role` per line; header row optional). On
submit the dialog surfaces created / skipped / errors inline and then
refreshes the list.

## 6. Tests

### Backend (`apps/api/tests/test_invitations.py`, 20 new)
Invite issue + accept happy path, invalid/expired/replayed/reissued
tokens, cross-org denial, inactive-user denial, already-accepted
denial. Audit CSV: admin-only, honors filters, has expected shape.
Event hardening: bogus status values, empty/non-string `note`,
empty `requested_by`. Bulk import: created/skipped/errors summary,
org-scoped, admin-only, empty-body 422.

### Frontend (`apps/web/src/test/AdminPanel.test.tsx`, 3 new on top of phase 13)
- `admin-user-invite-<id>` surfaces the one-time raw token banner.
- Bulk import summary renders created/skipped/errors counts.
- Audit export button wires `downloadAuditExport` with current filters.

### E2E (`apps/web/tests/e2e/workflow.spec.ts`, 1 new)
- Admin creates a new user, clicks **Invite**, raw token appears.
  Audit log → **Export CSV** triggers a real browser download with
  the expected filename pattern.

Totals: **pytest 110/110, Vitest 25/25, Playwright 12/12**.

## 7. What this phase explicitly does NOT do

- No email delivery for invitations.
- No SSO claim → user mapping changes (the auth seam from phase 10 still applies).
- No organization or audit data export beyond users (CSV export is audit-only).
- No role-based access for the invite accept URL (anyone with the token can accept; that's how invitations work by design).
- No CRUD for the `security_audit_events` table from the API — read + export only.
