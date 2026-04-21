# Phase 52 — Clinical Approval and Record Finalization (Wave 7)

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-roi-wave-1`
Alembic head: `e1f2a3041509` (up from `e1f2a3041508`)

## What Wave 7 implemented

Wave 7 turns physician final approval into a server-authoritative
record-finalization step, distinct from electronic signing. The prior
model had a single "signed" gate — sign was attestation, export was
hand-off, and there was no second authoritative act by a designated
doctor. Wave 7 splits that apart:

1. **Sign** is unchanged. Any admin or clinician may sign, subject to
   the existing Wave 3 release-blocker gates. Sign now also seeds
   `final_approval_status = 'pending'` on the row, and the attestation
   string is stamped with the signer's `full_name` rather than email.

2. **Final approval** is a new, dedicated act. Only users flagged
   `is_authorized_final_signer = true` in their org may perform it.
   The doctor must type their exact stored `full_name`; the server
   compares case-sensitively (leading/trailing whitespace trimmed,
   interior whitespace preserved). A successful match stamps four
   new columns on the row and emits `note_final_approved` to the
   audit sink.

3. **Export is now gated on final approval.** A signed note with
   `final_approval_status = 'pending'` or `'invalidated'` returns 409
   `export_blocked_by_gate` and emits `note_export_blocked`. Legacy
   rows (status NULL, predating Wave 7) pass through untouched so
   existing pilot data is not retroactively locked.

4. **Amendment invalidates prior approval.** When a signed, approved
   note is amended, the original row is marked
   `final_approval_status = 'invalidated'`, the invalidation
   timestamp and reason are stamped, and the dedicated
   `note_final_approval_invalidated` audit event fires (only when the
   prior state was actually `approved`, not a mere `pending`). The
   approval record itself is preserved — the invalidation is
   additive, so the chain still shows who had approved and when.

## Data model

### `users`

- `is_authorized_final_signer BOOLEAN NOT NULL DEFAULT FALSE`
  — explicit, per-user privilege. Independent of role. Defaults to
  FALSE so no existing user is silently granted the privilege on
  upgrade.

### `note_versions`

- `final_approval_status VARCHAR(16) NULL` — one of `'pending'`,
  `'approved'`, `'invalidated'`. NULL on legacy rows.
- `final_approved_at DATETIME(tz) NULL`
- `final_approved_by_user_id INTEGER NULL`
- `final_approval_signature_text VARCHAR(255) NULL` — the exact
  string the doctor typed, case-preserved and trimmed. Independent
  of any later `users.full_name` rename.
- `final_approval_invalidated_at DATETIME(tz) NULL`
- `final_approval_invalidated_reason VARCHAR(500) NULL`
- `ix_note_versions_final_approval_status` — query-side index for
  admin readouts.

No existing column was dropped. Migration is purely additive.

## Service layer

`apps/api/app/services/note_final_approval.py` is the single source
of truth. It is pure (no DB I/O); routes own persistence. Key
exports:

- `is_authorized_final_signer(user_row)` — the authz predicate.
  Requires both `is_authorized_final_signer = true` AND
  `is_active = true`. Role is irrelevant.
- `compare_typed_signature(typed, stored_full_name)` — case-sensitive
  exact equality after edge-trim. Surfaces structured reason codes:
  `signature_required`, `signature_mismatch`,
  `signer_has_no_stored_name`.
- `can_attempt_final_approval(note_row)` — precondition check. Rows
  must be `signed`/`exported`/`amended`, not superseded, not already
  `approved`.
- `export_requires_final_approval(note_row)` — gate helper used by
  the release-blockers service.
- `approval_state_on_sign()` — canonical string (`"pending"`) stamped
  on every fresh sign.
- `invalidation_reason_for_amendment()` — canonical string stamped
  when an amendment invalidates prior approval.

Lifecycle integration: `compute_release_blockers(..., target="exported")`
now emits `final_approval_pending` or `final_approval_invalidated`
blockers (both `severity="error"`). Legacy rows (`status` is NULL)
return no Wave 7 blocker and export works as before.

## HTTP surface

- `GET /me` — response now includes `is_authorized_final_signer:
  bool`.
- `POST /note-versions/:id/sign` — still role-gated to
  `admin`/`clinician`; additionally stamps
  `final_approval_status='pending'` and uses `caller.full_name` in
  the attestation.
- `POST /note-versions/:id/export` — now runs the export
  release-blocker check; 409 `export_blocked_by_gate` when pending
  or invalidated; emits `note_export_blocked` on block.
- `POST /note-versions/:id/amend` — unchanged role guard; now
  flips the original row's `final_approval_status` to
  `'invalidated'` and stamps the invalidation reason. Emits
  `note_final_approval_invalidated` when the prior state was
  `approved`.
- **NEW** `POST /note-versions/:id/final-approve` —
  body `{"signature_text": "..."}`.
  - 404 `note_not_found` — cross-org or missing id (org-scope
    check runs first so existence is not leaked via 403).
  - 403 `role_cannot_final_approve` — caller is not an authorized
    final signer.
  - 409 `not_signable_state` / `already_approved` / `note_superseded`
    — state conflicts.
  - 422 `signature_mismatch` / `signature_required` — typed name did
    not match.
  - 400 `signer_has_no_stored_name` — user row has no full_name.
  - 200 — approval recorded. Returns the updated `NoteVersion`.

## Audit events added

| event_type | emitted when |
|---|---|
| `note_final_approved` | successful final approval |
| `note_final_approval_unauthorized` | caller without the flag attempted approval |
| `note_final_approval_signature_mismatch` | typed name did not match |
| `note_final_approval_invalid_state` | approval attempted on a non-approvable row |
| `note_final_approval_invalidated` | amendment invalidated a previously-approved row |
| `note_export_blocked` | export attempted while approval pending/invalidated |

## How authorized-doctor final approval works

1. An org admin seeds or edits a user with
   `is_authorized_final_signer = true`. Seed helper
   `_ensure_user(..., is_authorized_final_signer=True)` supports this;
   the default in the seed and in the migration is `false`.
2. The clinician (or any role carrying the flag) signs a note through
   the existing flow. The sign path stamps `final_approval_status =
   'pending'`.
3. The authorized doctor opens the same note in the workspace. The
   `NoteLifecyclePanel` renders the Wave 7 subsection with a typed
   signature input when `me.is_authorized_final_signer === true` AND
   the row is `pending`.
4. The doctor types their exact stored `full_name`. The client
   submits to `/final-approve`. The server re-validates authz,
   re-compares the string case-sensitively against
   `users.full_name`, and on match writes the four approval
   columns and emits `note_final_approved`.
5. A subsequent export request now succeeds.

If the doctor later needs to correct the record, they issue an
amendment. The amendment service creates a new `note_versions` row
with its own fresh lifecycle and `final_approval_status = null` (the
amendment must be signed and approved in its own right); the
original row is marked superseded AND its approval is flipped to
`invalidated` with a canonical reason string. Export on the
superseded row is now blocked with the `final_approval_invalidated`
blocker.

## Frontend surface

- `apps/web/src/api.ts`:
  - `Me.is_authorized_final_signer: boolean`
  - `NoteVersion.final_approval_status` plus five related fields.
  - `finalApproveNoteVersion(email, noteId, body)` helper.
- `apps/web/src/NoteLifecyclePanel.tsx`: adds a dedicated
  "Final physician approval" section that renders differently for
  `pending` / `approved` / `invalidated`. The typed-signature input
  is only shown when `me.is_authorized_final_signer === true` and the
  row is `pending` and not superseded. Unauthorized viewers see a
  clear restriction note. The approved view shows the approving
  user, timestamp, and the verbatim signature. The invalidated view
  shows the invalidation reason and timestamp.
- `apps/web/src/styles.css`: adds `.lifecycle-approval*` styling and
  the base `.lifecycle-panel*` styling that the Wave 3 panel was
  also missing.

## Testing

- Backend pytest: 444/444 passing (26 new Wave 7 tests;
  4 pre-existing Wave 3 / transcript / bridge tests updated to
  account for the new export gate + attestation source).
- Frontend typecheck: clean.
- Frontend vitest: 185/185 passing.
- Frontend production build: clean.
- Alembic upgrade-from-empty on a fresh sqlite: clean.

Wave 7 test file: `apps/api/tests/test_note_final_approval_wave7.py`.

## What remains for later enterprise/clinical governance waves

- **Approval delegation / multi-signer flows.** The current model is
  a single designated approver. Some specialty environments may
  require a primary + counter-signer; this fits cleanly as a new
  service-layer rule, but was intentionally out of scope.
- **DB-level CHECK constraint on `final_approval_status`.** The
  application enforces the allowed set; a database CHECK can land
  once the vocabulary has stabilised in production.
- **Content immutability beyond fingerprint.** The Wave 3 content
  fingerprint detects drift; a true append-only / tamper-evident
  log remains a separate concern.
- **Admin surface: lists of pending-approval notes.** The data is
  there; a dedicated admin readout (filtered by
  `final_approval_status = 'pending'`) is a small follow-up.
- **OIDC / step-up auth for the approval action.** The current
  session governance from Wave 2 continues to apply; a dedicated
  re-auth / step-up prompt at the moment of approval is a separate
  hardening pass.
