# Phase 28 — Clinician Quick-Comment Hardening

> Favorites strip + cursor-position insertion + an honest usage-audit
> signal. Keeps the feature doctor-only, provenance-clear, and
> PHI-minimising. Narrow surface, production-safe changes.

## What changed

1. **Favorites / pinning** — per-user, unified across preloaded picks
   and custom comments. New table
   `clinician_quick_comment_favorites`. Four new endpoints under
   `/me/quick-comments/favorites`. Idempotent POST (re-firing the
   same ref returns the existing row). DELETE takes query params so
   every HTTP client transports reliably. A Favorites strip renders
   above the main library whenever at least one pin resolves.
2. **Cursor-position insertion** — `NoteWorkspace` now carries a
   `ref` to the draft textarea. When the doctor clicks a quick
   comment, the body is spliced at the current
   `selectionStart`/`selectionEnd` instead of appended at the end.
   Caret moves to the end of the inserted text after the next
   animation frame so the doctor can keep typing immediately.
   Falls back cleanly to append-at-end when no selection state
   exists (textarea not mounted, jsdom, e2e reload, etc.).
3. **Usage audit** — new `POST /me/quick-comments/used` that
   emits a single `clinician_quick_comment_used` audit event per
   insertion. Frontend fires it as fire-and-forget after every
   successful click. PHI-minimising: the audit detail carries the
   ref (`preloaded_ref=…` or `custom_comment_id=…`) plus optional
   `note_version_id` / `encounter_id`, **never** the comment body.
4. **Playwright smoke** — one focused spec in
   `apps/web/tests/e2e/quick-comments.spec.ts` that drives a real
   browser through identity-select → open encounter → ingest
   transcript → generate draft → click a preloaded quick comment →
   assert the text lands in the draft. The usage-audit POST is
   observed firing in the backend server log during the same run.

## Data model

```
clinician_quick_comment_favorites (
  id,
  organization_id,            -- FK organizations
  user_id,                    -- FK users
  preloaded_ref  VARCHAR(64), -- stable id from the preloaded pack
  custom_comment_id INTEGER,  -- FK clinician_quick_comments
  created_at,
  CHECK (exactly one of preloaded_ref / custom_comment_id is NOT NULL),
  UNIQUE (user_id, preloaded_ref),
  UNIQUE (user_id, custom_comment_id)
)
```

- The `preloaded_ref` uses stable string IDs (`sx-01`, `post-44`,
  …), not DB ids, so if the frontend reorders the preloaded list
  nothing breaks.
- The two unique constraints both have a nullable column; SQLite +
  Postgres treat `NULL` as distinct, which means a clinician can
  favorite one preloaded ref + one custom comment id on separate
  rows, but cannot double-favorite the same ref.
- No `is_active` / `updated_at`. A favorite is removed by
  deleting the row; it doesn't have a lifecycle.

Migration: `e1f2a3041504`.

## API surface

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/me/quick-comments/favorites` | List the caller's favorites (ordered by `created_at` asc). |
| `POST`   | `/me/quick-comments/favorites` | Idempotent upsert. Body: `{preloaded_ref}` XOR `{custom_comment_id}`. Returns 201 with the existing row if already favorited. |
| `DELETE` | `/me/quick-comments/favorites?preloaded_ref=…` OR `?custom_comment_id=…` | Removes the favorite. Second-call returns `{removed: 0}` — idempotent. |
| `POST`   | `/me/quick-comments/used` | Records an insertion. Body: `{preloaded_ref}` XOR `{custom_comment_id}`, plus optional `note_version_id`, `encounter_id`. Returns 202. |

All four require admin/clinician role → 403
`role_cannot_edit_quick_comments` for reviewers. Cross-user /
cross-org references to a `custom_comment_id` → 404
`quick_comment_not_found`. Both `favorites` and `used` routes refuse
the *both refs* and *no ref* cases with 400
`quick_comment_ref_required`. Soft-deleted custom comments cannot
be favorited → 409 `quick_comment_inactive`.

**Path-conflict fix.** The phase-27 `PATCH` and `DELETE` routes on
`/me/quick-comments/{comment_id}` were constrained to
`{comment_id:int}` so `/me/quick-comments/favorites` (a literal
segment) cannot accidentally match them. Without that converter,
FastAPI matches by pattern before type-coercing, so `favorites`
was being parsed as a non-int `comment_id` and returning 422.

## Cursor-position insertion

The splice path is self-contained in `NoteWorkspace.insertQuickComment`:

```
if the draft textarea is mounted AND
   selectionStart/selectionEnd are valid indices within editBody:
    splice(before, body, after), move caret to end of inserted text
else:
    fallback: append body to the end of editBody
```

Newline handling: we insert a leading `\n` only if the character
immediately before the caret isn't already a newline, and always
follow with a trailing `\n`, so sequential insertions each land on
their own line. The caret restore happens inside
`requestAnimationFrame` after React re-renders — so the doctor's
caret lands at the end of the inserted phrase, not back at the
start of the textarea.

The textarea's `onChange` is unchanged, so the browser's undo
stack still works coherently on subsequent doctor typing.

## Usage audit — PHI minimisation

The audit event carries:

- user + org + timestamp (from the existing audit pipeline)
- `kind` — `preloaded` or `custom`
- `preloaded_ref=…` OR `custom_comment_id=…`
- optional `note_version_id=…` `encounter_id=…`

It deliberately does **not** carry:

- the comment body (the author sees it on their own pad; the
  audit log doesn't need to duplicate)
- anything else from the draft

Frontend fires it as fire-and-forget (the wrapper swallows network
errors) so telemetry never blocks the clinician. A backend test
asserts the comment body does not appear in any recorded audit
detail even when the ref is a doctor-authored custom comment.

## Isolation invariants preserved

- Quick comments, favorites, and usage records are NOT linked to
  `encounter_inputs`, `extracted_findings`, `note_versions`, or
  any transmitted artifact. A backend test asserts that the
  encounter endpoints (`/encounters/{id}`, `/encounters/{id}/events`)
  never contain the favorite ref. Signed notes continue to carry
  only what the clinician explicitly typed + inserted + saved.
- Reviewer role is invisible to the whole surface: three new
  backend tests + one new frontend test confirm favorites
  endpoints 403 reviewers, and the Favorites strip + star buttons
  do not render in a reviewer's NoteWorkspace view.

## Test coverage

- **Backend** +16 (`tests/test_quick_comment_favorites.py`):
  - favorite preloaded happy path; idempotency; custom happy path
  - validation: exactly-one-ref, both refs, neither ref → 400
  - cross-user custom favorite → 404; soft-deleted custom → 409
  - list scoping (own-only in the same org)
  - unfavorite removes one row; second-call is a no-op
  - reviewer 403 across GET/POST/DELETE
  - audit events `clinician_quick_comment_favorited` /
    `…_unfavorited`
  - usage audit: preloaded + custom variants, ctx includes
    `note_version_id`, body-body invariant, validation refusals,
    cross-user 404, reviewer 403
  - surface isolation — favorites don't leak into
    `/encounters/{id}` payload
  - Full backend suite: **279 passed** (263 prior + 16).
- **Frontend** +8 (`src/test/NoteWorkspace.test.tsx`):
  - preloaded star → dispatches `favoriteQuickComment` + refresh
  - favorites strip renders pinned preloaded + `aria-pressed=true`
  - favorites strip surfaces a pinned custom comment
  - favorites strip absent for reviewers + no API fetch
  - cursor-position splice: caret mid-text inserts there, not end
  - fallback: no selection → append at end
  - click preloaded fires `recordQuickCommentUsage` with
    `preloaded_ref`, no `body` key
  - click custom fires `recordQuickCommentUsage` with
    `custom_comment_id`, no `body` key
  - Full vitest suite: **81 passed** (19 + 20 + 42).
- **Playwright** +1 (`tests/e2e/quick-comments.spec.ts`):
  - real browser: identity-select → open encounter → ingest
    transcript → generate draft → click preloaded pick → assert
    text appears in draft. `POST /me/quick-comments/used status=202`
    observed in the backend log during the same run. **1 passed.**
- Typecheck + Vite build clean (232 kB JS / 21.10 kB CSS gzip
  68.28 kB JS / 4.35 kB CSS).

## Files touched

- `apps/api/alembic/versions/e1f2a3041504_quick_comment_favorites.py` (new)
- `apps/api/app/api/routes.py` — four new routes, int-constrained
  phase-27 PATCH/DELETE paths
- `apps/api/tests/test_quick_comment_favorites.py` (new)
- `apps/web/src/api.ts` — favorites + usage helpers + typed envelope
- `apps/web/src/NoteWorkspace.tsx` — cursor splice, favorites strip,
  star toggles, usage audit wiring
- `apps/web/src/styles.css` — favorites strip + star button styles
- `apps/web/src/test/NoteWorkspace.test.tsx` — 8 new tests + mocks
- `apps/web/tests/e2e/quick-comments.spec.ts` (new)
- `docs/build/05-build-log.md`, `16-frontend-test-strategy.md`,
  `39-quick-comment-hardening.md` (new)

## Follow-on work

1. **Drag-reorder Favorites.** Order today is
   `created_at ASC`; a tiny `position` column + a drag handle would
   let clinicians put the most-used ref at the top.
2. **Insertion undo-ability.** The current `setEditBody` call is a
   single React update, which is good for the browser-level undo
   stack on subsequent keystrokes. Explicit Cmd-Z over the
   insertion itself (roll back the splice as one atomic op) needs
   a small undo-history layer on the textarea.
3. **Aggregation view.** A `GET /admin/quick-comment-usage-summary`
   that rolls up last-90-days per `preloaded_ref` and
   `custom_comment_id` — lightweight read, same pattern as the
   audit-export CSV from phase 14.
4. **Soft-delete cascade.** When a favorited custom comment is
   soft-deleted, the favorite row currently survives (the UI
   filters it out). A nightly compaction job could reap orphaned
   favorites; not urgent.
