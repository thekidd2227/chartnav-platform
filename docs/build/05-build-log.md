# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 14: invitations, settings schema, audit export, event hardening, bulk users

### Step 1 — Baseline
- Head: `5a5d846` (operator control plane).
- 88 pytest + 22 vitest + 11 Playwright green.

### Step 2 — Migration `e5f6a7b8c9d0`
- `users.invitation_token_hash TEXT NULL` (indexed).
- `users.invitation_expires_at DATETIME NULL`.
- `users.invitation_accepted_at DATETIME NULL`.

### Step 3 — Backend endpoints
- `POST /users/{id}/invite` — admin-only. Generates `secrets.token_urlsafe(32)`, stores only `sha256(token)`, returns the raw token once. 7-day expiry. Cross-org → 404 `user_not_found`; inactive → 400 `user_inactive`; already accepted → 400 `user_already_accepted`. Re-issue overwrites the hash.
- `POST /invites/accept` — unauth. Hashes the provided token, validates presence + active target + not-yet-accepted + not-expired. Clears the hash on success (idempotent in the wrong direction). Added `/invites` to the rate-limit protected prefixes.
- `GET /security-audit-events/export` — admin-only CSV; same filters as the read endpoint; same org-scoping (`caller.org OR organization_id IS NULL`); Content-Disposition attachment with timestamped filename.
- `POST /users/bulk` — admin-only. Per-row validation with `summary: {requested, created, skipped, errors}`. 500-row cap at pydantic layer. One bad row never aborts the batch. Stamps `invited_at` on every created row.
- Typed `OrganizationSettings` (pydantic `extra=forbid`) with fields `default_provider_name`, `encounter_page_size (10..200)`, `audit_page_size (10..200)`, `feature_flags`, `extensions`. `PATCH /organization` now validates against the model; persists `model_dump(exclude_none=True)` JSON.
- Per-type event-data hardening in `_validate_event`:
  - `status_changed` — both statuses must be in `ALLOWED_STATUSES`.
  - `encounter_created` — status must be in `ALLOWED_STATUSES`.
  - `manual_note.note` — non-empty string ≤ 4000 chars.
  - `note_draft_requested.requested_by` — non-empty string; optional `template` non-empty string.
  - `note_draft_completed.template` — non-empty string; optional `length_words` non-negative int.
  - `note_reviewed.reviewer` — non-empty string ≤ 255.
- `USER_COLUMNS` now includes `invitation_expires_at` + `invitation_accepted_at` (raw token hash is not returned by any endpoint).

### Step 4 — Backend tests (`test_invitations.py`, 20 new)
- Invite: issue returns raw token, non-admin 403, cross-org 404, inactive-user 400, already-accepted 400, re-issue revokes prior token.
- Accept: happy path, invalid token, replay, expired (via direct DB time rewind).
- Audit export: CSV content-type + filename + respects filters + admin-only.
- Event hardening: bogus status values, empty/non-string `note`, empty `requested_by`.
- Bulk import: mixed happy/dup/bad-role returns correct summary; admin-only; empty body 422; org-scoped.
- Also updated `test_control_plane.py` settings tests to match the new typed schema (extra-forbid, extensions bucket for forward compat, size limit via `extensions`).
- Full backend suite: **110/110 passed**.

### Step 5 — Frontend
- `api.ts`:
  - `OrganizationSettings` typed interface; `Organization.settings` is now typed.
  - `UserInvite`, `BulkImportSummary`, `BulkUserResult` interfaces.
  - `inviteUser`, `acceptInvite`, `bulkCreateUsers` functions.
  - `auditExportUrl(filters)` + `downloadAuditExport(email, filters)` — the download helper fetches with the auth header and triggers a local blob download (a plain `<a href>` can't send `X-User-Email`).
- `AdminPanel.tsx`:
  - Users tab — **Invite** button per active user row (hidden on self); one-shot banner with the raw token + timestamp + "Dismiss". **Bulk import…** button opens a dialog with a CSV-like textarea; inline summary on submit.
  - Organization tab — typed inputs for `name`, `default_provider_name`, `encounter_page_size`, `audit_page_size` + an **Extensions** JSON textarea for forward-compat.
  - Audit tab — **Export CSV** button next to **Refresh**; honors current filters.
- New `InviteAccept.tsx` + branch in `main.tsx` — minimal hash-split routing so `/invite?invite=<token>` and `/accept` render the accept screen. On success it stores the email into `localStorage.chartnav.devIdentity` so the main app picks it up for header-mode dev use.
- Typecheck clean; `vite build` emits 184 KB JS / 8.2 KB CSS.

### Step 6 — Frontend tests
- `AdminPanel.test.tsx`:
  - `admin-user-invite-<id>` produces the one-shot token banner.
  - Bulk import renders the created/skipped/errors summary.
  - Audit Export CSV button wires `downloadAuditExport` with current filters.
  - Updated the phase-13 "local JSON parse error" assertion from "settings JSON" → "extensions JSON" to match the new typed form.
- `App.test.tsx` unchanged.
- Vitest: **25/25 passed**.

### Step 7 — E2E
- New scenario "admin can issue an invitation and download audit CSV":
  - Creates a user, clicks **Invite**, asserts the token box is visible and non-empty.
  - Clicks **Export CSV** on the Audit tab and waits for the browser download event; asserts the filename matches `chartnav-audit-*.csv`.
- Existing event-composer E2E still uses the dropdown + `manual_note` + `{note: ...}` payload, which the hardened validator accepts.
- Playwright: **12/12 passed** in ~15s.

### Step 8 — Docs
- New `docs/build/24-invitations-and-governance.md`.
- Updated `01-current-state`, `05-build-log`, `06-known-gaps`, `02-workflow-state-machine` (event hardening), `03-api-endpoints` (4 new endpoints + error codes), `04-data-model` (invitation columns), `08-test-strategy`, `15-frontend-integration` (invite/accept/bulk/export UI), `16-frontend-test-strategy`, `18-operational-hardening` (audit export surface), `22-admin-governance` (invitations done).
- `scripts/build_docs.py` picks up section 24.
- Final HTML + PDF regenerated.

### Step 9 — CI
- **No workflow YAML changes.** New tests live in paths `backend-sqlite` / `frontend` / `e2e` already collect. New migration runs via each backend job's existing `alembic upgrade head`.
- Same `deploy-config` (compose + shellcheck) lane still covers all scripts.

### Step 10 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- `.gitignore` unchanged (already excludes caches, `.db`, dist, etc.).

---

## Prior phases

- **Phase 13 — Operator control plane** (`5a5d846`)
- **Phase 12 — Admin governance** (`4ff4e28`)
- **Phase 11 — Staging deployment + observability** (`ee7cf43`)
- **Phase 10 — Real JWT bearer + operational hardening** (`cbc5184`)
- **Phase 9 — Playwright E2E + release pipeline** (`74fe8dd`)
- **Phase 8 — Create UI + vitest + frontend CI** (`f83d748`)
- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
