# Phase 27 — Clinician Quick-Comment Pad

> A doctor-only clipboard. Preloaded ophthalmology picks + per-user
> custom snippets. Click to insert into a draft. Never autopopulates
> a signed note. Labeled as clinician-entered so nobody confuses it
> with AI findings or transcript content.

## What's in the pad

**Preloaded (shipped with the frontend bundle — `apps/web/src/quickComments.ts`).**
50 entries, grouped into five categories:

| Category | Items |
|---|---|
| Symptoms / HPI | 1–20 |
| Visual function / basic exam | 21–30 |
| External / anterior segment | 31–40 |
| Posterior segment | 41–47 |
| Assessment / plan / counseling | 48–50 |

These are shared UI content, identical for every clinician. No DB
seed — keeps the persistence surface narrow and lets the list render
with zero round-trips.

**Custom (per-user, persisted on the backend).**
`clinician_quick_comments` table. Each row is owned by one
clinician and one organization. Doctor authors it through the
`Add Custom Comment` modal. Edit + soft-delete supported. Another
clinician in the same org cannot see or edit it.

## Where it lives in the UI

`apps/web/src/NoteWorkspace.tsx` renders a dedicated section
**Quick Comments** below the existing encounter workspace:

- Header with a `clinician-entered` trust pill.
- Help caption: *"Click a phrase to insert it into the draft. These
  are clinician quick-picks, not transcript findings or AI-generated
  content."*
- Search input that filters both preloaded + custom by substring.
- `[ Add Custom Comment ]` button → opens a modal with a textarea
  + Cancel / Save actions.
- Grouped preloaded picks.
- Separate **My Custom Comments** section with per-row Edit + Delete
  actions.

The panel is gated on `canEdit` (admin + clinician). Reviewers never
see it — they cannot author comments and the backend would 403 any
read attempt anyway.

## Insertion behavior

`insertQuickComment(body)` appends `\n\n{body}\n` to `editBody` (the
local draft buffer, already part of the existing patch-save path).
It **never** writes to the server, **never** modifies
`generated_note_text`, **never** touches a signed note. If the active
note is signed/exported or no draft exists, the click is a silent
no-op plus a toast; the preloaded + custom buttons are also
`disabled` in that state.

Because the insertion goes through the existing `editBody` →
`patchNoteVersion` path, any insert a doctor then saves gets the
same audit trail as any other manual edit (the PATCH route emits
`note_version_submitted`/`_revised` on transition).

## API surface

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/me/quick-comments` | Caller's own active custom comments. `?include_inactive=true` shows soft-deleted too. |
| `POST`   | `/me/quick-comments` | Create a new custom comment. |
| `PATCH`  | `/me/quick-comments/{id}` | Edit `body` and/or `is_active`. |
| `DELETE` | `/me/quick-comments/{id}` | Soft-delete (`is_active=false`). Idempotent. |

All four require admin/clinician role (reviewers → 403
`role_cannot_edit_quick_comments`). Cross-user + cross-org reads
mask to 404 `quick_comment_not_found` — same leak-prevention
pattern the note/encounter reads use.

## Data model

```
clinician_quick_comments (
  id,
  organization_id,        -- FK organizations, org scope
  user_id,                -- FK users, owning clinician
  body,                   -- TEXT NOT NULL
  is_active,              -- BOOL NOT NULL DEFAULT true (soft delete)
  created_at, updated_at
)
INDEX ix_clinician_quick_comments_owner_active
  ON (organization_id, user_id, is_active)
```

Migration: `e1f2a3041503_clinician_quick_comments.py`.

Deliberately not linked to any `encounter_id` or `note_version_id` —
these are doctor clipboard content, not encounter data. Insertion
into a specific note's draft happens on the client.

## Surface isolation (what quick comments are *not*)

| Surface | Contains quick comments? |
|---|---|
| Transcript (`encounter_inputs`) | No. Different table, different semantics. |
| Findings (`extracted_findings`) | No. |
| Generated draft (`note_versions.generated_note_text`) | No — immutable snapshot of AI output; quick comments never touch it. |
| Clinician final (`note_versions.note_text`) | Only if the doctor explicitly clicked to insert and then saved the draft via the existing PATCH path. Never auto-inserted. |
| Signed artifact (phase 25) | Only through the clinician-final body, if inserted + signed. Artifact JSON labels the block as `clinician_final` / `edit_applied=true`, so provenance stays clear. |
| Patient-facing surfaces | None exist in the app today, and the panel is rendered inside the clinician workspace gated on `canEdit`. The test `no patient-facing surface…` structurally asserts the panel is a descendant of the workspace section. |

## Audit

Three event types, one per mutation:

- `clinician_quick_comment_created` — detail: `quick_comment_id={id} chars={n}`
- `clinician_quick_comment_updated` — detail: `quick_comment_id={id} changed=body,is_active`
- `clinician_quick_comment_deleted` — detail: `quick_comment_id={id} soft=true`

Insertion into a draft is **not** a separate audit event — the
existing `note_version_*` events already log edits, and piling on
another event for every click would spam the audit log without
adding trust. If a product-level "which snippet did the doctor
reach for?" question comes up later, we can add
`clinician_quick_comment_inserted` at that point.

## Test coverage

- Backend (`apps/api/tests/test_quick_comments.py`) — **12 scenarios**:
  reviewer create / list 403; clinician create 201; empty body
  rejected; list scoping (own only, same org); cross-user PATCH/DELETE
  → 404; cross-org 404; PATCH body; soft-delete + `include_inactive`;
  idempotent delete; audit events for all three mutations; surface
  isolation (not in `/encounters/{id}` or
  `/encounters/{id}/events`).
- Frontend (`apps/web/src/test/NoteWorkspace.test.tsx`) — **+9**:
  reviewer view hides panel + no API fetch; preloaded renders in
  five categories with verbatim text spot-checked; click preloaded
  inserts into editable draft; signed note disables preloaded
  buttons; search filters preloaded; Add Custom opens modal + Save
  dispatches `createMyQuickComment` + list refresh; custom comments
  render + click inserts; delete dispatches `deleteMyQuickComment`
  + refresh; structural "clinician-only surface" assertion.
- Suite totals: backend **263 passed**, frontend **73 passed**
  (19 App + 20 AdminPanel + 34 NoteWorkspace). Typecheck + Vite
  build clean.

## Files touched

- `apps/api/alembic/versions/e1f2a3041503_clinician_quick_comments.py` (new)
- `apps/api/app/api/routes.py` — four new routes + helpers
- `apps/api/tests/test_quick_comments.py` (new)
- `apps/web/src/quickComments.ts` (new) — preloaded pack
- `apps/web/src/api.ts` — `ClinicianQuickComment` type + CRUD helpers
- `apps/web/src/NoteWorkspace.tsx` — panel, modal, insertion logic
- `apps/web/src/styles.css` — quick-comment styles + lightweight modal
- `apps/web/src/test/NoteWorkspace.test.tsx` — 9 new tests + mocks
- `docs/build/05-build-log.md`,
  `docs/build/16-frontend-test-strategy.md`,
  `docs/build/38-clinician-quick-comments.md` (new)

## Follow-on work

1. **Favorite / pin preloaded picks.** Extend `clinician_quick_comments`
   with a nullable `preloaded_ref` column or a sibling
   `clinician_quick_comment_favorites` table so a doctor can star
   their most-used picks and have them bubble to the top.
2. **Insertion audit event.** If ops asks "which picks actually get
   used?", add `clinician_quick_comment_inserted` emitted from the
   client (or better: via a thin `/me/quick-comments/{id}/mark-used`
   call that just records an audit event without mutating the row).
3. **Order-preserving insertion.** Today insertion appends to the
   end of `editBody`. A real cursor-position insert (the doctor
   might want the phrase in the middle of the HPI) needs the
   `note-draft-textarea` ref + a selection offset; straightforward
   but not in this phase.
4. **Rich-text / template variables.** Current comments are plain
   text. Future: support `{patient_first_name}` or `{today}` tokens.
5. **Org-shared library.** A small "org admin can author shared
   picks that appear for every clinician" surface. Different data
   model (shared, not per-user). Deferred because the per-user
   wedge covers the product brief.
