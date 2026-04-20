# Build Log

Reverse-chronological.

---

## 2026-04-19 — Phase 33: audio intake + transcription wedge

The first real speech-to-chart path through ChartNav. File-upload
audio intake → ingestion pipeline runs through the phase-22 seam →
deterministic stub transcriber emits a clearly-labelled placeholder
(or canned text via test header) → clinician reviews + edits the
transcript before draft generation. No fake live vendor STT, no
browser mic, no ambient listening. Honest seams everywhere.

### Changes
- **New `app/services/audio_transcriber.py`** — deterministic stub
  with `[stub-transcript]` provenance prefix; honours
  `metadata.stub_transcript` and `stub_transcript_error` for test
  harnesses; registered at app bootstrap via `install_default()`.
- **`app/main.py`** — installs the stub at import time so audio
  uploads stop failing with `audio_transcription_not_implemented`
  by default. Vendor adapters overwrite via the existing
  `set_transcriber(...)` registry.
- **`app/config.py`** — `audio_upload_dir` (env
  `CHARTNAV_AUDIO_UPLOAD_DIR`, default `./audio_uploads`) and
  `audio_upload_max_bytes` (default 25 MiB).
- **Routes**:
  - `POST /encounters/{id}/inputs/audio` — multipart `audio`
    upload. Writes UUID-named blob under
    `<dir>/<encounter_id>/<uuid>.<ext>`, creates
    `encounter_inputs` row with `input_type='audio_upload'` +
    full `source_metadata` (filename, content_type, size,
    stored_path, original_filename), runs the pipeline inline,
    returns the final row with terminal `processing_status`.
    Format allowlist (WAV/MP3/MP4/M4A/OGG/WEBM/FLAC/AAC) +
    size cap; reviewer 403; cross-org 404.
  - `PATCH /encounter-inputs/{id}/transcript` — clinician
    review/edit, completed-only, ≥10 chars after trim. Audit
    detail records input_id + encounter_id + chars only — never
    the body.
- **Stub-test seam** — `X-Stub-Transcript` and
  `X-Stub-Transcript-Error` request headers thread into
  `source_metadata` so HTTP-level tests can drive the pipeline
  deterministically.
- **`pyproject.toml`** — `python-multipart>=0.0.20` added so
  Starlette's form parser actually works.
- **Frontend** —
  - `api.ts`: `uploadEncounterAudio` (FormData via `fetch`,
    error envelope unified with the rest of the API surface) +
    `patchEncounterInputTranscript`.
  - `NoteWorkspace.tsx`: new "Upload a dictation audio file"
    form above the existing paste textarea; clearly-labelled
    stub-transcriber notice; **Edit transcript** button on every
    completed input; review-modal with cancel/save and a 10-char
    minimum guard. Reviewer view hides both the upload form and
    the edit affordance.

### Tests
- Backend +18 (`tests/test_audio_intake.py`): row creation +
  metadata, empty body 400, unknown format 400, oversize 413,
  reviewer 403, cross-org 404, default placeholder lands as
  completed, canned transcript via header, stub forced-error
  lands as failed with `stub_transcription_failed`, retry path
  still fails honestly, edit on completed succeeds, edit on
  non-completed → 409, edit cross-org 404, edit reviewer 403,
  edit audit body-free (PHI invariant), generation blocked
  until completed audio exists, edited transcript flows into
  next generation (not the placeholder), provenance isolation
  from shortcut + quick-comment usage events.
  Two pre-existing phase-22 regression tests
  (`test_audio_upload_fails_when_no_transcriber_installed`,
  `test_run_one_records_failure_and_releases_claim`) tightened
  to explicitly uninstall the stub before asserting the legacy
  honest-failure path.
  Full backend suite: **327 passed** (309 + 18).
- Frontend +7 (`NoteWorkspace.test.tsx`): audio upload form
  renders for clinicians; hidden for reviewers; upload
  dispatches `uploadEncounterAudio` + refreshes inputs;
  completed audio renders Edit transcript; failed audio doesn't;
  edit modal saves via `patchEncounterInputTranscript` + closes;
  Save disabled <10 chars; Generate stays blocked with honest
  hint when no completed input exists.
  Full vitest suite: **122 passed** (19 + 20 + 83).
- Typecheck clean. Vite build 257.19 kB JS / 21.26 kB CSS
  (gzip 75.78 / 4.41 kB).

### Docs
- New `docs/build/44-audio-intake-and-transcription-wedge.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/app/services/audio_transcriber.py` (new)
- `apps/api/app/main.py`
- `apps/api/app/config.py`
- `apps/api/app/api/routes.py`
- `apps/api/pyproject.toml`
- `apps/api/tests/test_audio_intake.py` (new)
- `apps/api/tests/test_ingestion_lifecycle.py`
- `apps/api/tests/test_worker.py`
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `44-audio-intake-and-transcription-wedge.md` (new)

### Files intentionally avoided
- Marketing site.
- No live vendor STT (Deepgram/Whisper). No browser mic /
  ambient listening / mobile recorder UX / chunked upload.
- No object-storage adapter — local-disk only; `stored_path` is
  a string so an S3/GCS adapter slots in without schema change.
- No new migration — existing `encounter_inputs` columns
  (transcript_text, source_metadata, processing_status,
  retry_count, last_error, last_error_code, started_at,
  finished_at, worker_id) cover the wedge.

---

## 2026-04-19 — Phase 32: Shift+Tab + per-user usage + CSV export + Oculoplastics

Four tight wins on the Clinical Shortcuts surface: bidirectional
blank navigation, optional per-user breakdown on the admin usage
summary, a CSV export path, and a curated Oculoplastics / lids /
adnexa pack. A substring-vs-token search bug that the new `MRD1`
abbreviation would have surfaced is fixed at the same time.

### Changes
- **Shift+Tab backward blank nav** — new
  `prevBlankBefore(body, fromOffset)` helper; NoteWorkspace's
  `onKeyDown` adds a Shift+Tab branch that walks to the previous
  `___` strictly before `selectionStart`, selects its 3 chars,
  `preventDefault`s. No wrap, no mutation when there's no
  previous blank.
- **`by_user=true`** on the admin `GET /admin/shortcut-usage-summary`.
  Groups by `(actor_email, shortcut_ref)`; response gains a
  `distinct_users` counter and every row carries `user_email`.
  Shared `_build_shortcut_usage_summary` aggregator extracted
  from the JSON handler so the CSV path doesn't fork logic.
- **New** `GET /admin/shortcut-usage-summary/export` — CSV
  export with the same admin/org/window gating; columns change
  with `by_user`; filename carries an ISO UTC timestamp plus an
  optional `-by-user` suffix.
- **Oculoplastics pack** — 6 shortcuts covering ectropion,
  entropion, dermatochalasis, ptosis (MRD1 + levator function),
  chalazion, lagophthalmos. All carry blanks so the caret +
  Tab chain feels natural.
- **Abbreviation additions** (3 tightly-bound entries):
  `I&D`, `MRD1`, `MRD2`.
- **`clinicalShortcutMatches` bug fix** — pre-existing naïve
  `query.includes(lowerAbbr)` was flagging `RD` as a match on
  queries like `MRD1` (substring). Replaced with a token-aware
  match: query tokens must equal an abbreviation or a single
  query token must be a **prefix** of an abbreviation. Typing
  `mrd` still surfaces MRD1; typing `mrd1` no longer drags the
  RD group in.
- **PHI invariant tests tightened** — checks against the
  row-serialized text of `body["items"]`, not the whole envelope,
  so a coincidental `999` in `generated_at`'s microsecond
  suffix can never flake the assertion.

### Tests
- Backend +8 (`test_shortcut_usage_summary.py`, 16 total):
  `by_user` grouping + counts + `distinct_users`; `by_user`
  org scoping; `by_user` role gate; `by_user` response-keys
  invariant; CSV aggregate shape + ranked rows + filename;
  CSV by-user shape + `-by-user` filename suffix; CSV role
  gate; CSV org + window validation.
  Full backend suite: **309 passed** (301 + 8).
- Frontend +7 (`NoteWorkspace.test.tsx`): Shift+Tab walks
  backward through two blanks; fallback when no previous
  blank; Shift+Tab sitting on a blank hops to the previous
  one (not the same); Oculoplastics group renders; `MRD1`
  search surfaces ocp pack + drops PVD (regression check for
  the fixed matcher bug); `ectropion` search surfaces ocp-01;
  reviewer hides the Oculoplastics group entirely.
  The phase-31 "Shift+Tab is untouched" test was retired /
  reclassified — the behaviour has changed intentionally.
  Full vitest suite: **114 passed**.
- Typecheck clean. Vite build 252.84 kB JS / 21.26 kB CSS
  (gzip 74.51 / 4.41 kB).

### Docs
- New `docs/build/43-shortcut-navigation-and-oculoplastics.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_shortcut_usage_summary.py`
- `apps/web/src/clinicalShortcuts.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `43-shortcut-navigation-and-oculoplastics.md` (new)

### Files intentionally avoided
- Marketing site.
- No new DB table (summary remains a read over the audit stream).
- No Playwright scenario (shared `spliceIntoDraft` helper is
  already covered by phase-28's cross-stack spec; the Tab/
  Shift+Tab semantics are unit-tested precisely).
- No whole-PDF abbreviation dump (now 79 curated entries).

---

## 2026-04-19 — Phase 31: Tab-to-next-blank + shortcut usage summary + glaucoma/cornea

Three narrow ergonomic wins on the phase-29/30 Clinical Shortcuts
surface. Tab inside the draft textarea walks from one `___`
placeholder to the next so multi-blank phrases can be filled in a
single keyboard flow. An admin `/admin/shortcut-usage-summary`
endpoint rolls up the existing `clinician_shortcut_used` audit
stream into a ranked `{ref, count, last_used_at}` list — no new
storage, PHI-minimising. Catalog grows from 30 to 42 shortcuts
with 12 new conservative specialist phrases across Glaucoma and
Cornea / anterior segment. Abbreviation reference grows from 50
to 76 curated entries — only terms the new live content uses.

### Changes
- **Backend** — new `GET /admin/shortcut-usage-summary?days&limit`
  route (admin-only, org-scoped). Reads `security_audit_events`
  where `event_type='clinician_shortcut_used'`, regex-parses the
  `shortcut_id=<ref>` token, aggregates per-ref counts +
  last_used_at. Ranked most-used-first with stable tie-break.
  No new tables, no cron. `days` clamped [1,365]; `limit`
  clamped [1,200].
- **Catalog** — 12 new shortcuts in `clinicalShortcuts.ts`:
  - **Glaucoma** (`glc-01..06`): POAG severity+target; OHT+CCT;
    PXF/PDS secondary OAG; narrow angles→LPI; post-op trab;
    post-op GDD.
  - **Cornea / anterior segment** (`cor-01..06`): DED+SPK+
    Schirmer+ATs; MGD; keratoconus+CXL vs obs; RCE→BSCL/PTK;
    Fuchs+guttae+DSEK counseling; post-op DSEK.
- **Abbreviation table** grew by 26 entries (ACG, CCT, GDD,
  LPI, NAG, OHT, PDG, PDS, POAG, PXF, PXFG, RNFL, SLT, Trab,
  VF, AT, BSCL, CXL, DED, DSEK, KC, KCS, MGD, PTK, RCE, SPK,
  TBU) — only additions the new shortcuts actually use or
  plausibly search. Full PDF still not dumped.
- **Tab-to-next-blank** — new `nextBlankAfter(body, fromOffset)`
  helper; draft-textarea `onKeyDown` handler previews the next
  `___` from `selectionEnd`, selects its 3 chars, and
  `preventDefault()`s. Modifier keys (Shift/Ctrl/Meta/Alt) pass
  through to browser default — no regression on existing keyboard
  navigation.

### Tests
- Backend +8 (`test_shortcut_usage_summary.py`): clinician +
  reviewer 403, ranked rollup with counts + last_used_at,
  cross-org isolation, days validation (422 on out-of-range),
  limit caps rows but not `distinct_refs`, PHI invariant
  (note_version_id + encounter_id never surface), quick-comment
  events not conflated into the shortcut summary.
  Full backend suite: **301 passed** (293 + 8).
- Frontend +6 (`NoteWorkspace.test.tsx`): new glaucoma + cornea
  groups render with verbatim phrasing spot-checks; abbreviation-
  aware search for `POAG` surfaces glaucoma (drops retina),
  `CXL` surfaces cornea with keratoconus; Tab inside the draft
  walks first→second `___`; Tab fallback when no blanks
  (`defaultPrevented===false`, no mutation); Shift+Tab is
  untouched by the handler.
  Full vitest suite: **108 passed** (19 + 20 + 69).
- Typecheck clean. Vite build 251.18 kB JS / 21.26 kB CSS
  (gzip 74.05 / 4.41 kB).

### Docs
- New `docs/build/42-shortcut-intelligence-glaucoma-cornea.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_shortcut_usage_summary.py` (new)
- `apps/web/src/clinicalShortcuts.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `42-shortcut-intelligence-glaucoma-cornea.md` (new)

### Files intentionally avoided
- Marketing site.
- No new DB table for usage analytics — summary reads the audit
  stream directly.
- No unified favorites table.
- No backward Tab (Shift+Tab walks backward) — scope was "next
  blank" only.
- No Playwright scenario — existing phase-28 spec covers the
  cross-stack insertion wedge through the shared splice helper.

---

## 2026-04-19 — Phase 30: shortcut favorites + caret-to-blank + retina expansion

Three narrow ergonomic wins on the phase-29 Clinical Shortcuts
surface: per-doctor shortcut favorites (separate table from the
phase-28 quick-comment favorites), caret jumps to the first
`___` placeholder on insertion with the three underscores
pre-selected so typing replaces them in one gesture, and 20
retina-heavy clinical phrases across 4 new groups (DR/DME, ERM/
VMT/MH, vascular, post-op). Abbreviation reference grew from 29 to
50 hints — only where the new content uses them. `s/p` now hover-
renders via a case-insensitive matcher that normalises to the
canonical uppercase key.

### Changes
- **Migration e1f2a3041505** — new `clinician_shortcut_favorites`
  table keyed on the catalog's stable string refs. One row per
  `(user, shortcut_ref)` via UNIQUE.
- **Routes** — `GET/POST/DELETE /me/clinical-shortcuts/favorites`
  (idempotent POST upsert, DELETE via query param). Admin/
  clinician only (reviewer 403). Audit events
  `clinician_shortcut_favorited` + `_unfavorited`.
- **Catalog** — 20 new shortcuts in clinicalShortcuts.ts with
  stable IDs (`dm-01..dm-05`, `mac-01..mac-05`,
  `vasc-01..vasc-05`, `post-01..post-05`). All AAO-style
  conservative shorthand; blanks are intentional fill-in points.
- **Abbreviation table** grew by 21 entries — AC, BRAO, BRVO,
  CRAO, CRVO, DM, DME, FA, FTMH, ILM, IVT, ME, MH, NV, NVD, NVE,
  NVG, NVI, PCP, S/P, VA. Only additions that the new shortcuts
  actually use or that are plausible search terms.
- **Matcher** — segmentAbbreviations flipped to `gi` +
  uppercase-normalised key lookup so `s/p PPV` renders with
  hover help without twin upper/lower dictionary keys. Word-
  boundary guards unchanged.
- **spliceIntoDraft** — now scans the inserted body for the
  first `___`, lands the caret there, and selects the three
  underscores. Falls back to end-of-insertion when no
  placeholder exists (phase-28 baseline).
- **Frontend api.ts** — ClinicalShortcutFavorite type +
  listMyClinicalShortcutFavorites / favoriteClinicalShortcut /
  unfavoriteClinicalShortcut.
- **NoteWorkspace** — shortcut favorites state, loader, toggle;
  ★ Favorites strip at the top of the Clinical Shortcuts panel;
  ☆/★ star toggle per catalog row with `aria-pressed` semantics;
  orphaned favorites (ref no longer in catalog) filtered out,
  never broken.

### Tests
- Backend +8 (`tests/test_clinical_shortcut_favorites.py`):
  happy path, idempotency, list scoping, unfavorite
  idempotence, reviewer 403 across all three endpoints, empty
  ref rejected, audit events, surface isolation (no leak to
  encounter reads).
  Full backend suite: **293 passed** (285 + 8).
- Frontend +10 (`NoteWorkspace.test.tsx`): four new groups
  render with verbatim phrasing (spot-check via
  `toHaveTextContent` so `<abbr>` wrappers don't break
  substring matching), abbreviation-aware search for DME /
  CRVO / FTMH, star toggle dispatch + refresh, Favorites strip
  render with aria-pressed, reviewer hides strip + no fetch,
  caret-to-first-blank selects the three underscores, caret
  fallback when no blank, case-insensitive `s/p` hover help.
  Full vitest suite: **102 passed** (19 + 20 + 63).
- Typecheck clean. Vite build 246.74 kB JS / 21.26 kB CSS
  (gzip 72.46 / 4.41 kB).

### Docs
- New `docs/build/41-shortcut-ergonomics-and-retina-expansion.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/alembic/versions/e1f2a3041505_clinical_shortcut_favorites.py`
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_clinical_shortcut_favorites.py` (new)
- `apps/web/src/clinicalShortcuts.ts`
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `41-shortcut-ergonomics-and-retina-expansion.md` (new)

### Files intentionally avoided
- Marketing site.
- No unified favorites table (quick-comment favorites and
  shortcut favorites stay on separate tables).
- No Playwright scenario (phase-28's spec already proves the
  cross-stack insertion wedge through the shared splice helper).
- No whole-PDF abbreviation dump (now 50 curated entries).

---

## 2026-04-19 — Phase 29: Clinical Shortcuts (specialist shorthand pack)

A second doctor-only layer on the clinician workspace: a curated
specialist shorthand phrase bank ("Clinical Shortcuts"), separate
from the phase-27 Quick Comments clipboard. 10 verbatim phrases
across PVD, Retinal detachment, and Wet/Dry AMD groups, with
abbreviation-aware search and subtle hover help on 29 curated
ophthalmic abbreviations. Click-to-insert reuses the phase-28
cursor splice. Dedicated usage-audit stream
(`clinician_shortcut_used`) so shorthand ergonomics can be analysed
independently of Quick Comments clicks.

### Changes
- **Frontend static catalog** — new `apps/web/src/clinicalShortcuts.ts`:
  10 shortcuts with stable IDs (`pvd-01`…`amd-03`), per-group
  tags for search, `ABBREVIATION_HINTS` (29 curated entries from
  the Spokane Eye Clinic sheet), longest-first token list,
  `clinicalShortcutMatches()` abbreviation-aware predicate,
  `segmentAbbreviations()` body tokenizer for `<abbr>` rendering.
- **Backend** — `POST /me/clinical-shortcuts/used` emits a new
  `clinician_shortcut_used` audit event. Admin/clinician only
  (reviewer → 403 `role_cannot_edit_quick_comments`).
  PHI-minimising: the audit detail carries only
  `shortcut_id`, optional `note_version_id`, `encounter_id`;
  never the phrase body.
- **NoteWorkspace refactor** — extracted `spliceIntoDraft(body,
  flashLabel)` from phase-28's `insertQuickComment`. Both
  `insertQuickComment` and the new `insertClinicalShortcut`
  delegate to it, so cursor placement, newline handling, and
  undo behaviour stay identical across both insertion paths.
  Shortcut clicks fire `recordClinicalShortcutUsage` fire-and-
  forget.
- **UI** — new section below Quick Comments titled
  **Clinical Shortcuts** with the brief's exact helper text.
  Grouped by condition with a single search input
  ("Search by phrase, group, or abbreviation (e.g. RD, SRF,
  AMD)…"). Each shortcut body renders with inline `<abbr title>`
  wrappers on known abbreviations (dotted-underline). Disabled
  state when note is signed/exported or no draft exists.
- **api.ts** — `recordClinicalShortcutUsage` helper,
  error-swallowing.

### Tests
- Backend +6 (`test_clinical_shortcuts.py`): happy path + audit
  detail shape; empty id rejected; reviewer 403; PHI invariant
  (sneaked `body` never lands in audit); shortcut stream is
  distinct from quick-comment stream; surface isolation (doesn't
  leak into encounter reads).
  Full backend suite: **285 passed** (279 + 6).
- Frontend +11 (`NoteWorkspace.test.tsx`): reviewer hides panel
  + skips audit POST; three groups render with verbatim phrasing;
  `<abbr>` hover help for AMD + RPE; click inserts full phrase;
  click fires `recordClinicalShortcutUsage` with id and no `body`
  key; signed note disables buttons; abbreviation-aware search
  for `RD`, `SRF`, `AMD`; panel-isolation assertion (separate
  from Quick Comments); two audit streams stay separate.
  Full vitest suite: **92 passed** (19 + 20 + 53). Typecheck
  clean. Vite build 238 kB JS / 21.26 kB CSS
  (gzip 70.22 kB / 4.41 kB).

### Docs
- New `docs/build/40-clinical-shortcuts.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_clinical_shortcuts.py` (new)
- `apps/web/src/clinicalShortcuts.ts` (new)
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `40-clinical-shortcuts.md` (new)

### Files intentionally avoided
- Marketing site.
- `note_versions` / `encounter_inputs` / `extracted_findings`.
- No DB table for the catalog (shared static UI content).
- No whole-PDF abbreviation dump (narrowed to 29 curated entries).
- No second Playwright spec (phase-28's
  `quick-comments.spec.ts` already proves the cross-stack wedge
  through the shared splice helper + audit plumbing).

---

## 2026-04-19 — Phase 28: quick-comment favorites + cursor insertion + usage audit

Production-readying pass on the phase-27 doctor quick-comment pad.
Adds three things on a narrow surface: favorites/pinning across
preloaded + custom comments, cursor-position splice instead of
end-append, and a PHI-minimising usage-audit signal. Plus one
focused Playwright scenario that exercises the full cross-stack
wedge.

### Changes
- **Migration e1f2a3041504** — `clinician_quick_comment_favorites`
  table (per-user, org-scoped; exactly one of `preloaded_ref` or
  `custom_comment_id` per row via CHECK constraint; unique per user
  per ref).
- **Routes** — `GET/POST/DELETE /me/quick-comments/favorites`
  (idempotent POST upsert, DELETE via query params) and
  `POST /me/quick-comments/used` (202-acknowledged usage audit).
  Audit events: `clinician_quick_comment_favorited`,
  `_unfavorited`, `_used`. Phase-27 PATCH + DELETE paths
  constrained to `{comment_id:int}` so `/favorites` literal can't
  collide.
- **Frontend — api.ts** — `ClinicianQuickCommentFavorite` type,
  `listMyQuickCommentFavorites`, `favoriteQuickComment`,
  `unfavoriteQuickComment`, `recordQuickCommentUsage` (error-swallowing).
- **Frontend — NoteWorkspace** — draft textarea `ref` wired; star
  toggle on every preloaded + custom row; Favorites strip rendered
  above the main library when at least one pin resolves; cursor-
  aware `insertQuickComment(body, ref)` that splices at
  `selectionStart`/`selectionEnd` with sane newline handling and
  post-insert caret restore; fires `recordQuickCommentUsage`
  fire-and-forget.
- **Styles** — favorites strip + star button primitives.

### Tests
- Backend +16 (`test_quick_comment_favorites.py`): happy paths for
  preloaded + custom favorites, idempotency, validation (both/neither
  ref → 400), cross-user custom → 404, soft-deleted custom → 409,
  list scoping, unfavorite idempotence, reviewer 403 on all four,
  audit event shape for favorites + usage, PHI invariant (body not
  in audit detail), surface isolation (no leakage to encounter
  endpoints).
  Full backend suite: **279 passed** (263 + 16).
- Frontend +8 (`NoteWorkspace.test.tsx`): preloaded star dispatch,
  favorites strip renders pinned preloaded + `aria-pressed=true`,
  favorites strip surfaces a pinned custom comment, reviewer view
  hides strip and skips API fetch, cursor-position splice at mid-text
  caret, append fallback when no selection, usage audit POST shape
  for preloaded + custom with no body key.
  Full vitest suite: **81 passed** (19 + 20 + 42).
- Playwright +1 (`tests/e2e/quick-comments.spec.ts`): identity-select
  → open encounter → ingest transcript → generate draft → click
  preloaded pick → assert text in draft. Server log confirms
  `POST /me/quick-comments/used status=202` during the run.
- Typecheck clean. Vite build 231.84 kB JS / 21.10 kB CSS
  (gzip 68 kB / 4.35 kB).

### Docs
- New `docs/build/39-quick-comment-hardening.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/alembic/versions/e1f2a3041504_quick_comment_favorites.py`
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_quick_comment_favorites.py`
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `apps/web/tests/e2e/quick-comments.spec.ts`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `39-quick-comment-hardening.md` (new)

### Files intentionally avoided
- Marketing site.
- `note_versions` / `encounter_inputs` / `extracted_findings` —
  favorites + usage remain orthogonal to the transcript/findings
  trust tiers.
- No new platform abstractions; no vendor-specific code paths.

---

## 2026-04-19 — Phase 27: clinician quick-comment pad (doctor-only)

Doctor-only clipboard surface. 50 preloaded ophthalmology picks
grouped into five categories (shipped with the frontend bundle),
plus per-user custom comments persisted on the backend. Click to
insert into the draft — never auto-populates a signed note, never
surfaces on any patient-facing path, labeled as clinician-entered
so it never reads as AI output.

### Changes
- **Migration `e1f2a3041503`** — new `clinician_quick_comments`
  table. Per-user, org-scoped. Soft delete via `is_active`. Index
  on `(organization_id, user_id, is_active)`. Deliberately not
  linked to any `encounter_id` / `note_version_id` — these are
  clipboard content, not encounter data.
- **Routes** — `GET/POST /me/quick-comments`,
  `PATCH/DELETE /me/quick-comments/{id}`. Admin/clinician only
  (reviewers 403). Cross-user + cross-org masks to 404. Emits
  `clinician_quick_comment_created/updated/deleted` audit events.
- **Frontend pack** — `apps/web/src/quickComments.ts` ships the
  50 preloaded picks with stable string ids (e.g. `sx-01`,
  `post-44`) and five categories.
- **API helpers** — `api.ts` gains `ClinicianQuickComment` type +
  `listMyQuickComments`, `createMyQuickComment`,
  `updateMyQuickComment`, `deleteMyQuickComment`.
- **UI** — `NoteWorkspace.tsx` renders a new `Quick Comments`
  section gated on `canEdit` (admin + clinician). Header carries a
  `clinician-entered` trust pill + help caption explicitly calling
  out "not transcript findings or AI-generated content". Search
  filters across preloaded + custom. `Add Custom Comment` opens a
  lightweight modal. Custom list renders with Edit/Delete per row.
- **Insertion** — click appends `\n\n{body}\n` to the draft
  buffer (`editBody`) that feeds the existing PATCH-save path.
  Disabled when the note is signed/exported; button is not shown
  and a guard toast fires if somehow invoked.
- **Styles** — styles.css grows a compact quick-comment layout and
  a minimal modal primitive reusing existing tokens.

### Tests
- Backend +12 (`tests/test_quick_comments.py`): role gate,
  clinician create, empty body rejection, list scoping (own-only,
  same org different user → own-only; different user cross-user
  PATCH/DELETE → 404), cross-org → 404, PATCH body, soft-delete +
  include_inactive, idempotent delete, audit events for
  create/update/delete, surface isolation (quick comments do not
  appear on `/encounters/{id}` or its events).
  Full backend suite: **263 passed** (251 + 12).
- Frontend +9 (`NoteWorkspace.test.tsx`): reviewer hides panel,
  preloaded renders in all five categories with verbatim text,
  click inserts into editable draft, signed note disables
  preloaded buttons, search filters preloaded, Add Custom opens
  modal + Save dispatches `createMyQuickComment`, custom rows
  render + click inserts, delete dispatches
  `deleteMyQuickComment`, structural clinician-only surface
  assertion.
  Full vitest suite: **73 passed** (19 + 20 + 34). Typecheck clean.
  Vite build 228 kB JS / 20.65 kB CSS.

### Docs
- New `docs/build/38-clinician-quick-comments.md`.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/alembic/versions/e1f2a3041503_clinician_quick_comments.py`
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_quick_comments.py`
- `apps/web/src/quickComments.ts`
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `38-clinician-quick-comments.md` (new)

### Files intentionally avoided
- Public marketing site.
- `note_versions` / `encounter_inputs` / `extracted_findings` —
  quick comments are a separate data class.
- No auto-insertion into signed notes. No org-shared library.

---

## 2026-04-19 — Phase 26: FHIR transport / write-path groundwork

Builds the honest write-path on top of phase 25's packaging. No vendor
delivery faked; no SMART-on-FHIR theatre. The adapter protocol grows
one typed method, three adapters answer honestly (native refuses,
stub records, generic FHIR R4 POSTs the DocumentReference), and every
attempt is logged append-only with hash provenance.

### Changes
- **Migration `e1f2a3041502`** — new `note_transmissions` table. One
  row per attempt; monotonic `attempt_number` per note-version;
  unique `(note_version_id, attempt_number)`. Columns capture adapter
  key, target system, `transport_status`, `request_body_hash`
  (matches phase-25 content hash), HTTP response code + snippet,
  remote id, error code/reason, attempt + completion timestamps,
  creator user id, denormalized `encounter_id` + `organization_id`
  for fast scoping.
- **Adapter protocol** — `ClinicalSystemAdapter.transmit_artifact`
  added. Takes the canonical ChartNav artifact **and** the FHIR
  DocumentReference (phase 25 builds both). Returns a typed
  `TransmitResult` — never raises on HTTP-level failure. New
  capability `AdapterInfo.supports_document_transmit`.
- **FHIR adapter** — implements `transmit_artifact` generically.
  POSTs JSON to `{base_url}/DocumentReference`, Bearer auth when
  configured, carries custom provenance headers
  (`X-ChartNav-Note-Version-Id`, `X-ChartNav-Artifact-Hash`). Parses
  `Location:` header or response `.id` for remote id. 4xx/5xx land
  as `TransmitResult(status="failed", ...)` rather than exceptions.
  Transport errors (DNS/timeout) still raise `AdapterError`.
  Injected `write_transport` for tests.
- **Stub adapter** — `transmit_artifact` succeeds in writethrough
  (records into `self.recorded_writes`, returns synthetic remote id);
  refuses in readthrough.
- **Native adapter** — `transmit_artifact` raises `AdapterNotSupported`
  with a clear reason; native is already the system of record.
- **Service `app/services/note_transmit.py`** — mode + role + signed
  + adapter-capability + idempotency gating. Persists a
  `dispatching` row before calling the adapter so crashes mid-call
  still leave a trace. Updates the row with the `TransmitResult`.
  `force=true` in the body allows a re-transmission after a prior
  success.
- **Routes** —
  - `POST /note-versions/{id}/transmit` (admin/clinician only,
    integrated_writethrough only, signed notes only)
  - `GET  /note-versions/{id}/transmissions` (cross-org masked via
    shared note-load helper)
  - `/platform` response grows `adapter.supports.document_transmit`.
- **Frontend** — `api.ts`: `NoteTransmission` type,
  `transmitNoteVersion`, `listNoteTransmissions`, new
  `document_transmit` flag on `PlatformInfo`. NoteWorkspace renders
  **Transmit to EHR** (flips to **Re-transmit** after success) only
  when the adapter advertises the capability; a transmission-history
  pane renders attempt rows with status, HTTP code, remote id,
  error code.

### Tests
- Backend +11 (`tests/test_note_transmit.py`): standalone refuses,
  readthrough stub refuses, writethrough stub success + persisted row
  + audit event, writethrough FHIR success via injected transport,
  FHIR 400 persisted as failed, unsigned refused, cross-org 404,
  reviewer role 403, double without force → 409 already_transmitted,
  double with force → new attempt (attempt_number increments), GET
  cross-org masked.
  Full backend suite: **251 passed** (240 + 11).
- Frontend +3 (`NoteWorkspace.test.tsx`): Transmit hidden when
  `document_transmit=false`, visible when true, click dispatches
  `transmitNoteVersion` + refreshes history pane.
  Full vitest suite: **64 passed** (22 + 20 + 22).
- Typecheck clean. Vite build 218 kB JS / 18.9 kB CSS.

### Emitted audit event
- `note_version_transmitted` — detail string carries note_id,
  transmission_id, adapter key, transport_status, attempt_number.

### Docs
- New `docs/build/37-fhir-write-path-groundwork.md` — adapter
  protocol growth, gating matrix, trust-tier preservation through
  the wire path, what this phase deliberately did not do.
- Updated `docs/build/16-frontend-test-strategy.md`.

### Files touched
- `apps/api/alembic/versions/e1f2a3041502_note_transmissions_table.py`
- `apps/api/app/integrations/base.py`
- `apps/api/app/integrations/fhir.py`
- `apps/api/app/integrations/stub.py`
- `apps/api/app/integrations/native.py`
- `apps/api/app/services/note_transmit.py` (new)
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_note_transmit.py` (new)
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `37-fhir-write-path-groundwork.md` (new)

### Files intentionally avoided
- Public marketing site (separate lane).
- `docs/diagrams/*` — the wire shape is a flat POST, no new diagram.
- Playwright — deferred; the feature depends on platform_mode env
  wiring in the e2e backend that isn't configured for writethrough.

---

## 2026-04-19 — Phase 25: signed-note artifact + export interoperability groundwork

Exports the first **packaged, provenance-bearing** representation of a
ChartNav signed note. Not a SMART-on-FHIR transaction, not a vendor
write-back — a **document package** that downstream systems (humans,
EHRs, audit reviewers) can ingest in three shapes. Narrow wedge on
purpose: the wedge is that the artifact is correct *before* transport
is ever wired.

### Changes

- **Migration `e1f2a3041501`** — adds `note_versions.generated_note_text`
  (TEXT NULL), a one-shot snapshot of the generator's draft that is
  never mutated by subsequent provider edits. Backfills legacy rows
  from current `note_text` so existing data keeps rendering; the
  `edit_applied` flag in the artifact reads as False for those rows
  (honest — we never recorded their pre-edit text).
- **Orchestrator** writes both `note_text` and `generated_note_text`
  at draft creation; PATCH handler continues to mutate only `note_text`.
- **New service** `apps/api/app/services/note_artifact.py` — pure
  builder that reads the note + encounter + source input + findings
  + signer in one bundle, separates transcript-derived facts from
  generated draft from clinician-edited final, and renders three
  variants from a single canonical dict:
  - `chartnav.v1.json`  — MIME `application/vnd.chartnav.signed-note+json`
  - `chartnav.v1.text`  — plain text with metadata header + audit footer
  - `fhir.DocumentReference.v1` — FHIR R4 DocumentReference with the
    clinician-final text inlined as base64 `content.attachment.data`,
    typed as LOINC `11506-3` "Progress note", tagged with the
    ChartNav URN (`urn:chartnav:note:{id}:v{n}`). For externally-sourced
    encounters the `context.encounter` identifier carries the FHIR
    Encounter ref so a future integrator can tie back without a
    second round-trip.
- **Integrity** — every artifact carries
  `signature.content_hash_sha256 = sha256(version_number|note_format|clinician_final)`
  so downstream consumers can detect tamper. Not a cryptographic
  signature (ChartNav does not hold a signing key today); it is
  tamper-evidence.
- **HTTP** — new `GET /note-versions/{id}/artifact?format=json|text|fhir`.
  Read-only, does not mutate state. Cross-org → 404 (same contract as
  other note reads). Unsigned → 409 `note_not_signed`. Unknown format
  → 400 `unsupported_artifact_format`. Each successful call emits an
  audit event `note_version_artifact_issued` with the chosen variant
  in the detail string. The existing `POST /note-versions/{id}/export`
  state transition is unchanged; artifact retrieval is orthogonal.
- **Frontend** — `api.ts` gains `NoteArtifact` type, `getNoteArtifact`,
  `fetchNoteArtifactRaw`, and `downloadNoteArtifact` (triggers a
  browser anchor-click with a stable filename per note-id + format).
  NoteWorkspace renders three `Download JSON / TEXT / FHIR` buttons
  under the sign/export row once the note is signed; each button has
  a hover tooltip explaining when you'd reach for that format.

### Tests

- **Backend** +9 (`apps/api/tests/test_note_artifact.py`) — unsigned
  refused, cross-org 404, unsupported format 400, default json tiers +
  signature + hash, edit-applied flag when provider edits, text body
  contains header + hash, FHIR DocumentReference shape + base64
  round-trip + hash parity with canonical JSON, deterministic hash,
  audit event captures variant.
  Full backend suite: **240 passed in 2m 57s** (231 prior + 9 new).
- **Frontend** +3 (`src/test/NoteWorkspace.test.tsx`) — artifact
  actions row visible only on signed notes, button labels, click
  dispatches `downloadNoteArtifact(email, id, "fhir")`.
  Full vitest suite: **61 passed in 6.65s** (22 + 19 + 20).
- Typecheck clean. Vite build 216 KB JS / 18.85 KB CSS gzip 64 KB.

### Docs

- New `docs/build/36-signed-note-artifact-and-export.md` —
  shape, format variants, integrity model, what this is not (no
  vendor write-back), test coverage, files touched.
- Updated `docs/build/16-frontend-test-strategy.md` — new vitest
  count + phase-25 section.

### Files touched

- `apps/api/alembic/versions/e1f2a3041501_note_generated_text_snapshot.py`
- `apps/api/app/services/note_orchestrator.py`
- `apps/api/app/services/note_artifact.py` (new)
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_note_artifact.py` (new)
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`, `16-frontend-test-strategy.md`,
  `36-signed-note-artifact-and-export.md` (new)

### Files intentionally avoided

- Public marketing site (separate lane).
- `apps/api/app/integrations/fhir.py` — no write-back seam; the
  FHIR format variant is a packaging shape, not a transport.
- Playwright e2e — deferred; artifact feature is gated behind a signed
  note, and the existing sign-then-export scenarios already exercise
  the surrounding UI path. Add one scenario when the artifact
  buttons get a clickable e2e case.

---

## 2026-04-19 — Phase 24 (hardening): frontend operator UX for async ingestion

Lane-safe frontend/test/docs pass on top of the phase-22 async
ingestion lifecycle + phase-23 background-worker foundation. No
backend code touched; no migrations; no backend phase doc collisions.

### Changes
- **Queue banner copy** — split the single "Processing continues in
  the background" banner into two honest variants: a "Processing…"
  message for rows a worker has picked up, and a "Queued…" message
  with a nudge toward the **Process now** button for rows still
  waiting. Clearer "what happens next" at a glance.
- **Generate-blocked hint** — new `subtle-note` under the Generate
  button that tells the operator exactly why Generate is disabled
  (empty-state, still-processing, failed/needs-review, or generic).
  Rendered with `data-testid="generate-blocked-note"` +
  `.workspace__generate-blocked` utility.

### Tests
- Vitest +3 (`src/test/NoteWorkspace.test.tsx`): blocked-hint
  variants per state. Existing queue-banner tests updated for the
  tightened copy.
- Playwright — new `tests/e2e/note-workspace-hardening.spec.ts`
  (3 scenarios): baseline blocked-hint, ingest→completed unlocks
  Generate, manual Refresh actually re-fetches.
- 58/58 Vitest, 20/20 Playwright (17 workflow+a11y + 3 hardening).
- typecheck clean; build 215 KB JS / 18.9 KB CSS.

### Docs
- New `docs/build/35-frontend-operator-ux-for-async-ingestion.md`
  (scope, UI changes, test coverage, files touched + avoided,
  verification).
- Updated `docs/build/16-frontend-test-strategy.md`.
- Did NOT regenerate `docs/final/*` (lane-safe rule).

### Files touched
- apps/web/src/NoteWorkspace.tsx
- apps/web/src/styles.css
- apps/web/src/test/NoteWorkspace.test.tsx
- apps/web/tests/e2e/note-workspace-hardening.spec.ts
- docs/build/05-build-log.md, 16-frontend-test-strategy.md, 35-…md

### Files intentionally avoided
- apps/api/app/services/*, apps/api/app/api/routes.py,
  apps/api/alembic/versions/*
- docs/build/33-async-ingestion-lifecycle.md
- docs/build/34-background-worker-foundation.md
- docs/final/chartnav-workflow-state-machine-build.html / .pdf

---

## 2026-04-19 — Phase 23: background worker foundation + bridged-encounter refresh

### Step 1 — Migration `d0e1f2a30415`
- `encounter_inputs.claimed_by` (VARCHAR(64) nullable) +
  `claimed_at` (DATETIME nullable) via batch rewrite.
- New index on `(processing_status, claimed_by)` for cheap
  "unclaimed queued" queries.
- Pure additive; standalone + integrated flows unaffected.

### Step 2 — Worker service (`app/services/worker.py`)
- Atomic claim via conditional UPDATE + read-back confirm. Two
  concurrent callers never win the same row.
- `requeue_stale_claims()` recovers `processing` rows whose
  claim is older than `CHARTNAV_WORKER_CLAIM_TTL_SECONDS`
  (default 900s; 30s floor).
- `run_one()` = claim + run; `run_until_empty()` drains up to
  100 ticks. Failure path clears the claim so retry doesn't hit
  stale-claim logic.
- Worker identity: `<hostname>/<pid>` by default, overrideable
  via `CHARTNAV_WORKER_ID`.

### Step 3 — Bridge sync (`app/services/bridge_sync.py`)
- `refresh_bridged_encounter(native_id, organization_id)`
  re-fetches via the resolved adapter and reconciles only the
  four mirror fields (`patient_identifier`, `patient_name`,
  `provider_name`, `status`).
- Source-of-truth guards:
  - 409 `not_bridged` on standalone-native rows.
  - 409 `external_source_mismatch` when the active adapter key
    doesn't match the historical `external_source`.
  - Never writes back to the external EHR.
  - Never touches ChartNav-native workflow tables.

### Step 4 — HTTP + CLI surfaces
- `POST /workers/tick` (admin) — one tick.
- `POST /workers/drain` (admin) — drain up to 100.
- `POST /workers/requeue-stale` (admin) — recovery.
- `POST /encounters/{id}/refresh` (admin + clinician; 409 `not_bridged`
  if standalone-native; 409 `external_source_mismatch`; cross-org
  404; emits `encounter_refreshed` audit event).
- `scripts/run_worker.py` — `--once | --drain | --loop | --requeue-stale`;
  JSON-per-line output for ops tailing.

### Step 5 — Frontend
- `api.ts`: `runWorkerTick`, `drainWorkerQueue`, `requeueStaleClaims`,
  `refreshBridgedEncounter` helpers. `EncounterInput` gains
  `claimed_by`/`claimed_at`.
- `NoteWorkspace.tsx`: Tier 1 gains a manual "↻ Refresh" button +
  a "Processing continues in the background" info banner that
  differentiates "waiting for a worker" from "currently
  processing".
- `App.tsx`: new `BridgedEncounterRefreshBanner` component for
  native rows that carry an `external_ref`. `refreshDetail` now
  preserves the mounted detail pane on re-fetch (stops the
  "Loading…" flicker that was unmounting child banner state).
- `EncounterDetail` takes an `onRefreshDetail` prop so children can
  request a re-fetch without the App-level closure.

### Step 6 — Tests
- **Backend +21**:
  - `tests/test_worker.py` (12): claim atomicity, stamps,
    happy-path drive, failure-path claim release, drain,
    stale-claim recovery, fresh claim not recovered, HTTP tick +
    drain + requeue-stale admin-only, HTTP tick processes a row,
    no regression on the inline text wedge.
  - `tests/test_bridge_sync.py` (9): standalone refusal, mirror
    updates, idempotent re-run, native workflow tables untouched,
    source-of-truth mismatch, reviewer 403, cross-org 404, audit
    event.
- **Frontend +6**: queue banner (queued + processing variants +
  absent-when-all-completed), manual refresh, bridged refresh UX
  (admin dispatches + reviewer sees disabled note).
- Full suites: **231/231 pytest**, **55/55 Vitest**, 17/17
  Playwright + 4 visual (baselines refreshed).

### Step 7 — Docs
- New `docs/build/34-background-worker-foundation.md` — full phase
  reference (state machine, services, HTTP + CLI, UI contract,
  verification, explicit non-goals).
- Updated `01-current-state`, `03-api-endpoints`, `04-data-model`,
  `05-build-log` (this entry), `06-known-gaps`, `08-test-strategy`,
  `15-frontend-integration`, `16-frontend-test-strategy`;
  ER diagram gains the two new claim columns.
- `scripts/build_docs.py` picks up section 34; executive summary
  extended. Final HTML + PDF regenerated.

### Step 8 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines refreshed for the new bridged refresh banner.
- No new runtime deps; worker is stdlib + SQLAlchemy only.

---

## 2026-04-18 — Phase 22: async ingestion + orchestration lifecycle

### Step 1 — Migration `c9d0e1f2a304`
- `encounter_inputs` gains `retry_count` (NOT NULL default 0),
  `last_error`, `last_error_code`, `started_at`, `finished_at`,
  `worker_id`. Batch rewrite for SQLite portability.
- Backward compatible: all additions are nullable with sensible
  defaults. Seed unaffected.

### Step 2 — Ingestion service (`app/services/ingestion.py`)
- Owns the `queued → processing → completed | failed | needs_review`
  state machine.
- `run_ingestion_now(input_id)` synchronous entry point safe to
  call from the HTTP path.
- `enqueue_input(input_id)` flips terminal rows back to `queued` +
  increments `retry_count`.
- `set_transcriber(fn)` seam for real audio STT. Default is an
  honest `audio_transcription_not_implemented` stub.
- Explicit error codes: `input_not_found`, `input_not_queueable`,
  `transcript_too_short`, `audio_transcription_not_implemented`,
  `transcriber_contract_violation`, `invalid_input_type`,
  `unexpected_error`, `max_retries_exceeded`.

### Step 3 — Note orchestrator (`app/services/note_orchestrator.py`)
- Wraps the phase-19 generator so the HTTP handler never touches
  it directly.
- Enforces the pipeline contract: input ready → findings extracted
  → note drafted → provider review required.
- All writes inside a single transaction.
- `OrchestrationError(error_code, reason, status_code)` surfaces
  clean error codes (`no_completed_input`, `input_not_ready`,
  `input_not_found`, `generation_failed`).

### Step 4 — HTTP surface
- `POST /encounters/{id}/inputs` — every row now enters at
  `queued`; text inputs run the pipeline inline so existing
  callers still see `completed`. Failures are persisted.
- `POST /encounter-inputs/{id}/process` — drive a queued row
  through the pipeline; returns `{input, ingestion_error}`.
- `POST /encounter-inputs/{id}/retry` — flip failed → queued +
  increment retry_count; emits `encounter_input_retried` audit
  event.
- `POST /encounters/{id}/notes/generate` now delegates to the
  orchestrator. Same contract, cleaner error translation.
- Input responses now include `retry_count`, `last_error`,
  `last_error_code`, `started_at`, `finished_at`, `worker_id`.

### Step 5 — Frontend
- `api.ts`: `EncounterInput` gains job-lifecycle fields;
  `processEncounterInput` + `retryEncounterInput` helpers added.
- `NoteWorkspace.tsx`: transcript tier now renders
  `processing_status` as a color-coded pill, a `retries N` chip
  when `retry_count > 0`, an error banner when `failed` /
  `needs_review`, Retry + Process-now action buttons, and gates
  the Generate-draft button on at least one `completed` input.
- `styles.css`: color-coded pill rules for `queued` /
  `processing` / `failed` / `needs_review`; retry-count chip.

### Step 6 — Tests
- Backend **+14** in `tests/test_ingestion_lifecycle.py`:
  happy path, too-short failure, audio-queued default,
  no-transcriber refusal, transcriber seam, retry + process chain,
  retry refused on `completed`, audit event emitted, cross-org
  404, reviewer 403, generate refuses `failed`, generate happy
  path after refactor, process idempotent on `completed`.
- Frontend **+4** in `src/test/NoteWorkspace.test.tsx`:
  failed error banner + Retry dispatches retry→process;
  `retries N` chip; queued Process-now button + Generate-disabled
  gating; Generate enabled when completed input exists.
- **210/210 pytest**, **49/49 Vitest**, 17/17 Playwright workflow
  + a11y, 4/4 visual (baselines refreshed).

### Step 7 — Docs
- New `docs/build/33-async-ingestion-lifecycle.md` — full phase
  reference (state machine diagram, schema, service seams, HTTP
  surface, UI contract, verification, explicit non-goals).
- Updated `01-current-state`, `03-api-endpoints`, `04-data-model`,
  `05-build-log` (this entry), `06-known-gaps`, `08-test-strategy`,
  `15-frontend-integration`, `16-frontend-test-strategy`,
  `30-transcript-to-note` (points to section 33 for the real
  lifecycle), `er-diagram` (new columns on encounter_inputs).
- `scripts/build_docs.py` picks up section 33; executive summary
  extended. Final HTML + PDF regenerated.

### Step 8 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines refreshed.
- No new runtime deps (ingestion + orchestrator are stdlib only).

---

## 2026-04-18 — Phase 21: external encounter → native workflow bridge

### Step 1 — Migration `b8c9d0e1f203`
- `encounters.external_ref` (`VARCHAR(128)` nullable, indexed) +
  `encounters.external_source` (`VARCHAR(64)` nullable).
- New UNIQUE `(organization_id, external_ref, external_source)` —
  database-level guarantee of idempotent bridge.
- Backward compatible: standalone encounters leave both NULL.

### Step 2 — Service seam
- `apps/api/app/services/bridge.py::resolve_or_create_bridged_encounter(...)`.
  Idempotent on `(org, external_ref, external_source)`; returns the
  native row with `_bridged` tag so first-create UX differs from
  subsequent resolves.
- Falls back to the org's first active location when the caller
  doesn't supply one (encounters.location_id is NOT NULL today).
- Default status `scheduled` so ChartNav's state machine has a
  valid starting point that doesn't imply the external EHR's
  state.

### Step 3 — HTTP surface
- `POST /encounters/bridge` (admin + clinician):
  - refused in standalone mode
    (409 `bridge_not_available_in_standalone_mode`).
  - emits `encounter_bridged` audit event on first create; silent
    on idempotent resolve.
- `ENCOUNTER_COLUMNS` + native adapter's list/fetch queries extended
  to include `external_ref` + `external_source` so the frontend
  sees them on every encounter row.

### Step 4 — Frontend
- `api.ts` gains `EncounterBridgeBody`, `BridgedEncounter`, and
  `bridgeEncounter(email, body)`.
- External encounter detail now shows a **Bridge to ChartNav**
  button inside the SoT banner (admin + clinician only; reviewer
  sees an explicit disabled note). Clicking dispatches
  `bridgeEncounter` with `_external_ref` + `_source` + mirror
  fields, then navigates to `?encounter=<native_id>` so the detail
  pane remounts against the bridged native row. Because the new
  row is `_source="chartnav"`, the full `NoteWorkspace` appears
  immediately.
- Copy on the external-note section was rewritten to describe the
  bridge instead of a generic native-only limitation.

### Step 5 — Tests
- **Backend +11** in `tests/test_encounter_bridge.py`: create +
  idempotency + standalone refusal + RBAC + integrated_writethrough
  OK + invalid status 400 + **full wedge** (transcript → generate
  → sign → export + workflow event) + phase-20 status-write gate
  still holds on bridged row + org scoping + standalone regression.
- **Frontend +1** in `App.test.tsx` + 1 updated: bridge button
  dispatches `bridgeEncounter`; external-note copy changed to
  mention bridging.
- Full suites: **196/196 pytest**, **45/45 Vitest**, 17/17
  Playwright workflow+a11y, 4/4 visual (baselines refreshed).

### Step 6 — Docs
- New `docs/build/32-external-encounter-bridge.md` — full phase
  reference (SoT, schema, service, HTTP surface, UI flow,
  verification, explicit non-goals).
- Updated `01-current-state`, `03-api-endpoints`,
  `04-data-model` (new cols + unique constraint),
  `05-build-log` (this entry), `06-known-gaps`,
  `08-test-strategy`, `15-frontend-integration`,
  `16-frontend-test-strategy`,
  `26-platform-mode-and-interoperability`,
  `27-adoption-and-implementation-model`; ER diagram gains
  `external_ref`/`external_source` on encounters.
- `scripts/build_docs.py` picks up section 32; executive summary
  extended. Final HTML + PDF regenerated.

### Step 7 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines refreshed.
- No new runtime deps.

---

## 2026-04-18 — Phase 20: adapter-driven encounters + integrated write gating

### Step 1 — Protocol
- `ClinicalSystemAdapter.list_encounters(organization_id, location_id,
  status, provider_name, limit, offset) → EncounterListResult` added
  to `app/integrations/base.py`.
- `EncounterListResult` dataclass (`items`, `total`, `limit`, `offset`)
  added to match the HTTP paging headers one-to-one.
- `fetch_encounter` shape widened — every adapter now returns the full
  ChartNav row shape plus `_source` + `_external_ref` metadata.

### Step 2 — Adapter implementations
- **Native**: `list_encounters` queries `encounters` with the same
  filter surface the old direct-SQL handler used; rows tagged
  `_source: "chartnav"`. `fetch_encounter` returns the full column
  set.
- **Stub**: two deterministic canned external rows (`EXT-1001`,
  `EXT-1002`) tagged `_source: "stub"`; supports `status` and
  `provider_name` post-filters so integrated_readthrough is
  exercisable end-to-end without a real FHIR server.
- **FHIR**: `list_encounters` → `GET /Encounter?_count=...&status=<mapped>`;
  ChartNav→FHIR status translation (`in_progress→in-progress`,
  `completed→finished`, …). `fetch_encounter` + `_normalize_encounter`
  widened to emit the full shape; `_fhir_status` preserved alongside
  the mapped ChartNav status.

### Step 3 — HTTP handlers
- `GET /encounters` dispatches through `resolve_adapter()` in every
  mode. Standalone takes the native adapter (same SQL); integrated
  modes take whatever adapter is resolved.
- `GET /encounters/{id}` path param widened to `str` so FHIR vendor
  ids pass through. Standalone path preserved via the existing
  `_load_encounter_for_caller` (now emits `_source: "chartnav"`);
  integrated mode fetches via adapter, stamps caller's org when the
  adapter returns None, and translates adapter errors into clean
  HTTP codes (`encounter_not_found` → 404, other `AdapterError` →
  502).
- New helper `_assert_encounter_write_allowed()`: `POST /encounters`
  returns 409 `encounter_write_unsupported` in BOTH integrated modes.
- `POST /encounters/{id}/status` is mode-split: readthrough → 409
  `encounter_write_unsupported`; writethrough → adapter dispatch
  (`AdapterNotSupported` → 501 `adapter_write_not_supported`, other
  `AdapterError` → 502); standalone → native state machine.
- `POST /encounters/{id}/events` stays allowed in every mode — those
  are ChartNav-native workflow events, not encounter mutations.

### Step 4 — Frontend
- `Encounter` type widens `id` to `number | string`; optional
  `_source`, `_external_ref`, `_fhir_status` surface the tag.
- New helpers `encounterIsNative(enc)` + `encounterSourceLabel(enc)`.
- `EncounterDetail` header renders a **source chip** in a brand-teal
  soft background for native, info-blue for external. A
  `banner--info` SoT banner appears on external encounters; status
  transitions are suppressed; `NoteWorkspace` is replaced with a
  honest subtle-note explaining native-only note drafting.
- `getEncounter`, `getEncounterEvents`, `updateEncounterStatus`,
  `createEncounterEvent` accept `number | string`.
- New `.source-chip` / `.detail__head-right` CSS using the brand
  token scale.

### Step 5 — Tests
- **Backend +11** in `tests/test_integrated_encounters.py`:
  - standalone list/detail carry `_source: "chartnav"`.
  - integrated_readthrough + stub list/detail dispatch to the stub
    adapter and return `_source: "stub"`.
  - integrated_readthrough refuses encounter creation (409
    `encounter_write_unsupported`) and status writes (409).
  - workflow events still writable in integrated mode.
  - integrated_writethrough + stub allows status writes (stub
    records in-process).
  - integrated_writethrough + fhir refuses status writes with 501
    `adapter_write_not_supported`.
  - FHIR `list_encounters` normalizes Bundle entries; status mapping
    threads through the FHIR URL (`status=in-progress`).
  - RBAC: `/encounters` still requires auth in integrated mode.
  - Env cleanup in `finally` blocks so integrated-mode tests don't
    pollute the rest of the suite.
- `test_fhir_adapter.py` existing encounter test updated for the new
  normalized shape (`patient_identifier` + `_source` + `_fhir_status`).
- **Frontend +2** in `App.test.tsx`:
  - native encounter detail renders the `ChartNav (native)` source
    chip and no external banner; transitions visible.
  - external encounter (`_source: "fhir"`) hides transitions, hides
    `NoteWorkspace`, and renders the SoT banner + subtle-note
    explaining native-only note drafting.
- **185/185 pytest**, **44/44 Vitest**, 17/17 Playwright workflow+a11y,
  4/4 visual (baselines refreshed for the source chip).

### Step 6 — Docs
- New `docs/build/31-adapter-driven-encounters.md` — full phase
  reference (SoT rules, protocol, adapter implementations, HTTP
  changes, error codes, frontend UX, verification, non-goals).
- Updated `01-current-state`, `03-api-endpoints` (encounter write
  gating table), `04-data-model` (SoT matrix extended), `05-build-log`
  (this entry), `06-known-gaps`, `08-test-strategy`,
  `15-frontend-integration`, `16-frontend-test-strategy`,
  `26-platform-mode-and-interoperability` (adapter encounter
  methods), `27-adoption-and-implementation-model` (mode-aware
  encounter workflow).
- `scripts/build_docs.py` picks up section 31; executive summary
  extended. Final HTML + PDF regenerated.

### Step 7 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines refreshed.
- No new runtime deps.

---

## 2026-04-18 — Phase 19: transcript → findings → note draft → signoff

### Step 1 — Migration `a7b8c9d0e1f2`
- `encounter_inputs` (input_type, processing_status,
  transcript_text, confidence_summary, source_metadata JSON,
  created_by_user_id, timestamps, FK to `encounters`).
- `extracted_findings` (CC, HPI, OD/OS VA + IOP, structured_json
  blob, extraction_confidence, FK to input + encounter).
- `note_versions` (version_number unique per encounter,
  draft_status, note_format, note_text, source_input_id,
  extracted_findings_id, generated_by, provider_review_required,
  missing_data_flags JSON array, signed_at + signed_by_user_id,
  exported_at, timestamps).
- Booleans use `sa.text("true")` for Postgres parity.

### Step 2 — Note-generator seam
- New `apps/api/app/services/note_generator.py` + `services/__init__.py`.
- `generate_draft(transcript_text, patient_display, provider_display)`
  returns `GenerationResult(findings, note_text, missing_flags)`.
- Shipped body is a deterministic regex extractor + SOAP template
  (no LLM dependency, tests stable). A real model plugs into
  `_run_generator`; the output contract is locked. Never fabricates
  values the transcript does not contain — emits `<missing —
  provider to verify>` placeholders + a missing-flag code instead.

### Step 3 — HTTP surface
- New endpoints:
  - `POST /encounters/{id}/inputs`
  - `GET  /encounters/{id}/inputs`
  - `POST /encounters/{id}/notes/generate`
  - `GET  /encounters/{id}/notes`
  - `GET  /note-versions/{id}`
  - `PATCH /note-versions/{id}`
  - `POST /note-versions/{id}/submit-for-review`
  - `POST /note-versions/{id}/sign`
  - `POST /note-versions/{id}/export`
- Transitions + role rules enforced at the API layer. Signed notes
  are immutable (PATCH → 409 `note_immutable`). Only
  admin/clinician can sign. Export requires signed state. Audit
  events emitted on every meaningful action.

### Step 4 — Provider review UI
- New `apps/web/src/NoteWorkspace.tsx` — three-tier trust layout:
  transcript input · extracted findings (with confidence + missing
  flags) · note draft (editable → submit → sign → export).
- Provider-edit of the draft text auto-flips status to `revised`
  and `generated_by=manual` so the UI can always tell generator
  output from provider-edited content.
- Reviewer role sees a read-only note and an explicit disabled-sign
  subtle-note; admins + clinicians get full workflow.
- Version picker surfaces below the draft once v2+ exists.
- Signed notes → Export button stamps `exported_at` and downloads
  `chartnav-note-<encounter>-v<n>.txt`; Copy-to-clipboard button
  available post-sign.
- Trust breadcrumb at the top of the workspace spells out
  `transcript → extracted facts → AI draft → provider signed`.

### Step 5 — api.ts
- New types: `InputType`, `InputProcessingStatus`, `NoteDraftStatus`,
  `NoteFormat`, `EncounterInput`, `ExtractedFindings`, `NoteVersion`,
  `NoteWithFindings`.
- New functions: `createEncounterInput`, `listEncounterInputs`,
  `generateNoteVersion`, `listEncounterNotes`, `getNoteVersion`,
  `patchNoteVersion`, `submitNoteForReview`, `signNoteVersion`,
  `exportNoteVersion`.
- `MISSING_FLAG_LABELS` constant maps flag codes to human labels.

### Step 6 — Tests
- **Backend**: 174/174 pytest. New `tests/test_transcript_to_note.py`
  (+19) covers ingest defaults, RBAC, generation + versioning
  preservation, missing-flag emission, provider edit → revised,
  submit-for-review, sign (RBAC + metadata), signed-immutable,
  export-only-from-signed, cross-org 404, audit-event trail.
- **Frontend**: 42/42 Vitest. New
  `src/test/NoteWorkspace.test.tsx` (+8): three tiers render
  distinctly, findings + confidence + missing-flags visible,
  provider edit flips generated-by label, submit→sign path,
  reviewer sees no Sign button + disabled-note, export downloads +
  switches to read-only, paste+generate happy path.
- **E2E**: Playwright 17 workflow + a11y still green. Visual
  baselines refreshed for the new workspace tiers (4/4 local).

### Step 7 — Docs
- New `docs/build/30-transcript-to-note.md` — full phase reference
  (trust model, data model, generator seam, HTTP surface, UI
  layout, export, verification matrix, explicit non-goals).
- Updated `01-current-state`, `03-api-endpoints`, `04-data-model`,
  `05-build-log` (this entry), `06-known-gaps`, `08-test-strategy`,
  `09-ci-and-deploy-hardening`, `15-frontend-integration`,
  `16-frontend-test-strategy`, `26-platform-mode-and-interoperability`
  (export/handoff semantics), `02-workflow-state-machine` (note
  state machine), ER diagram, system-architecture + api-data-flow.
- `scripts/build_docs.py` picks up section 30; executive summary
  extended. Final HTML + PDF regenerated.

### Step 8 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines refreshed (`*-chromium-darwin.png`).
- No new runtime deps (generator uses stdlib only).

---

## 2026-04-18 — Phase 18: native clinical layer + FHIR adapter

### Step 1 — Migration `f6a7b8c9d0e1`
- Created `patients` (org-scoped, `external_ref` nullable,
  `patient_identifier` unique-per-org, `first_name`, `last_name`,
  `date_of_birth`, `sex_at_birth`, `is_active`, `created_at`).
- Created `providers` (org-scoped, `external_ref` nullable,
  `display_name`, `npi` unique-per-org when non-null, `specialty`,
  `is_active`, `created_at`).
- Added `encounters.patient_id` + `encounters.provider_id` as nullable
  FKs via batch rewrite so SQLite accepts the ALTER. Legacy
  `patient_identifier` / `provider_name` text fields kept for
  backward-compat reads.
- Booleans default to `sa.text("true")` for Postgres portability.

### Step 2 — Seed extended
- `scripts_seed.py` gained `_ensure_patient` + `_ensure_provider` +
  patient/provider fixtures per tenant. Existing seeded encounters
  now link to real FK rows; re-running seed backfills `patient_id`
  / `provider_id` on existing encounters without duplicating rows.
- `ENCOUNTER_COLUMNS` in `routes.py` now returns `patient_id` +
  `provider_id` so existing clients see the linkage.

### Step 3 — Native adapter (phase 16 follow-through)
- `NativeChartNavAdapter` now implements `fetch_patient` (by PK or
  `patient_identifier`) and `search_patients` against the new
  `patients` table. `supports_patient_read` / `supports_patient_write`
  flip to `True`; source-of-truth map reports `patient: CHARTNAV`
  and `provider: CHARTNAV`.
- Tests in `test_platform_mode.py` updated for the new honesty.

### Step 4 — FHIR R4 adapter
- New `app/integrations/fhir.py` — real implementation of the
  `ClinicalSystemAdapter` protocol. Pluggable `transport` parameter
  lets tests inject fixtures; default transport is `urllib.request`
  (no new runtime deps). Config-driven base URL + auth type
  (`none` / `bearer`) + bearer token. Normalizes FHIR `Patient` and
  `Encounter` resources into ChartNav's internal shape (MRN
  extraction, participant display, status mapping). Writes raise
  `AdapterNotSupported` honestly.
- Registered under key `fhir` at module import time in
  `app/integrations/__init__.py::_register_shipped_vendors()`.
- `Settings` gained `fhir_base_url`, `fhir_auth_type`,
  `fhir_bearer_token` with import-time validation.

### Step 5 — Native CRUD endpoints
- `GET /patients` / `POST /patients` — admin or clinician can create
  in standalone + integrated_writethrough modes; reviewer is read-only;
  integrated_readthrough returns 409
  `native_write_disabled_in_integrated_mode`. Search by MRN or name.
- `GET /providers` / `POST /providers` — admin-only writes, 10-digit
  NPI validation (`invalid_npi`), uniqueness (`npi_conflict`), org
  scoping, same mode-aware write gate.
- `ENCOUNTER_COLUMNS` now exposes the new FK columns; no changes
  to state-machine semantics.

### Step 6 — Tests
- **155 pytest.** New:
  - `tests/test_clinical.py` (13) — seed + CRUD + conflict paths +
    cross-org isolation + readthrough-blocks-writes.
  - `tests/test_fhir_adapter.py` (11) — config validation + fixture
    transport patient/encounter normalization + bearer header +
    readthrough+fhir resolves to FHIR adapter + honest write
    refusals.
- **34 Vitest.** `AdminPanel.test.tsx` adds 3 tests — Patients tab
  create form, integrated_readthrough hides the form + shows SoT
  banner, Providers tab create works.
- **17 Playwright workflow+a11y**, **4 visual** — visual baselines
  regenerated for the new admin tabs.

### Step 7 — Frontend
- `api.ts` gains `Patient`, `Provider`, `PatientCreateBody`,
  `ProviderCreateBody` types + `listPatients`, `createPatient`,
  `listProviders`, `createProvider`.
- `AdminPanel` gets two new tabs (`patients`, `providers`) between
  Locations and Organization. Both panes render a `banner--info`
  source-of-truth notice when `platform.platform_mode ===
  "integrated_readthrough"` and hide the create form.
- Providers pane gates the create form to admin-only, mirroring the
  backend RBAC.

### Step 8 — Docs
- New docs/build entries for each updated area. Section 29 captures
  the phase end-to-end: data model, adapter contract growth, FHIR
  normalization rules, operator verification matrix.
- `scripts/build_docs.py` picks up section 29; executive summary
  extended. Final HTML + PDF regenerated.

### Step 9 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines refreshed.
- No secrets in the FHIR test suite — fixture transports only.

---

## 2026-04-18 — Phase 17: brand & domain alignment

### Step 1 — Locate the relevant repos
- Product: `~/Desktop/ARCG/chartnav-platform` (this repo).
- Marketing/site: `~/arcg-live` (remote `thekidd2227/website`, deploys
  to GitHub Pages as `arcgsystems.com`). Serves the ChartNav public
  page at `/chartnav/...`.
- Brand assets source: `arcg-live/public/chartnav/brand/*.svg`.

### Step 2 — Domain: chartnav.ai safety-net (in `arcg-live`)
- `index.html` + `public/404.html` gained a host-based redirect
  that runs before React mounts / before the SPA redirect. If any
  visitor lands on `chartnav.ai` or `www.chartnav.ai`, they are
  bounced to `https://arcgsystems.com/chartnav/<path>` via
  `location.replace()`.
- `CNAME` intentionally unchanged; `arcgsystems.com` stays primary.
- `arcg-live/docs/chartnav-ai-domain-runbook.md` captures the
  operator workflow in the GoDaddy UI (exact clicks, DNS caveats,
  verification, rollback). GoDaddy 301 forwarding is the primary
  mechanism; the safety-net is belt-and-suspenders.

### Step 3 — Brand assets imported
- Copied `chartnav-logo.svg` (light variant for white backgrounds),
  `chartnav-mark.svg`, and `chartnav-favicon.svg` from
  `arcg-live/public/chartnav/brand/` into
  `apps/web/public/brand/`. Both repos now share the same SVG
  source of truth.

### Step 4 — Token system aligned
- Rewrote `apps/web/src/styles.css` into an explicit ChartNav token
  system (`--cn-*`) mirroring the marketing site's chartnav.css:
  teal `#0B6E79` primary + scale, surface `#FFFFFF`, page bg
  `#F4F8FA`, inter typography with cv02/03/04/11. Legacy tokens
  (`--fg`, `--muted`, …) kept as aliases so every existing class
  renders with zero component change.
- Shadow tokens unified (`sm`/`md`/`lg`), md shadow teal-tinted.
- `--cn-muted` tightened from `#64748B` → `#475569` and `--cn-dim`
  from `#94A3B8` → `#64748B` so axe AA contrast passes cleanly.

### Step 5 — App shell + footer
- `apps/web/index.html` loads Inter from Google Fonts, sets
  `theme-color=#0B6E79`, sets the favicon to the brand SVG,
  expands title + meta description.
- `App.tsx` header swaps the `<span>Chart</span><span>Nav</span>`
  approximation for the real `chartnav-logo.svg`. "Workflow"
  becomes a tidy pill chip next to the wordmark.
- `App.tsx` wraps the shell in a fragment and adds an `<footer
  className="app-footer">` after the modal mounts. Footer line:
  "ChartNav · Clinical workflow platform" on the left,
  `Powered by **ARCG Systems**` on the right (11px uppercase,
  letter-spacing 0.12em, muted). Exactly one attribution per page.
- `InviteAccept.tsx` inline colors swapped to the new AA muted.

### Step 6 — Tests
- Added `src/test/App.test.tsx::renders the brand footer with a
  subtle Powered by ARCG Systems line` — asserts the literal copy
  and that both test IDs (`app-footer`, `app-footer-arcg`) are
  present. **31/31 Vitest passed.**
- **131/131 pytest.** Backend untouched, run for regression
  confidence.
- **17/17 Playwright** (workflow + a11y) after a11y fixes.
- **4/4 Playwright visual**, baselines deliberately regenerated to
  reflect the new brand tokens + logo.

### Step 7 — Docs
- New `docs/build/28-brand-and-domain-alignment.md` covering both
  domain + brand work.
- Updated `01-current-state.md`, `05-build-log.md` (this entry),
  `06-known-gaps.md`, `15-frontend-integration.md`.
- Final HTML + PDF regenerated (`scripts/build_docs.py`).

### Step 8 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines committed (`.png` under
  `tests/e2e/visual.spec.ts-snapshots/`).

---

## 2026-04-18 — Phase 16: platform mode + interoperability

### Step 0 — CI fallout from phase 15 repaired first
- **Postgres parity failure** reproduced locally against a live
  Postgres 16. Root cause: migration `c3d4e5f6a7b8` used
  `sa.text("1")` as the default for `users.is_active` /
  `locations.is_active` (BOOLEAN). SQLite stores booleans as ints
  so it accepted the default; Postgres rejects with
  `DatatypeMismatch`. Fixed by switching to `sa.text("true")` —
  portable across both engines, no new revision required.
- **Frontend CI failure** reproduced in a clean `node:20` Linux
  container. Root cause: Vitest 4.1.4 transitively pulled rolldown
  + Vite 8 + esbuild 0.28; the resulting `package-lock.json` was
  missing the platform-specific `@esbuild/*` entries npm 10 on
  Linux requires (`EBADPLATFORM` / `Missing: … from lock file`).
  macOS npm 11 silently tolerated it. Fixed by pinning
  `vitest`/`@vitest/ui` to `^3.2.4` (Vitest 3 uses Vite 5 directly,
  no rolldown) and regenerating the lockfile. Linux CI replay now
  green.
- E2E was only skipped because upstream jobs failed; both fixes
  unblock it. Lead-intake / Airtable toast on
  `arcgsystems.com/chartnav/ophthalmology` is outside this repo
  (zero matches for airtable/webhook/arcgsystems across the repo)
  — external Make/Airtable automation owned by the marketing site.
- Head: `aab94c3` after CI fix.

### Step 1 — Define platform operating modes
- `app/config.py` gains `platform_mode` and `integration_adapter`
  on `Settings`. `CHARTNAV_PLATFORM_MODE` ∈ {`standalone`,
  `integrated_readthrough`, `integrated_writethrough`}. Default
  `standalone`. `integrated_*` defaults adapter to `stub`;
  `standalone` pins it to `native` and rejects any other value at
  import time.

### Step 2 — Adapter boundary
- New package `apps/api/app/integrations/`:
  - `base.py` — `ClinicalSystemAdapter` protocol
    (fetch_patient, search_patients, fetch_encounter,
    update_encounter_status, write_note, sync_reference_data,
    `info`), `AdapterInfo`, `SourceOfTruth` enum,
    `AdapterError` + `AdapterNotSupported`.
  - `native.py` — `NativeChartNavAdapter` (persists to ChartNav
    DB via the same SA Core surface the HTTP routes use; refuses
    patient ops honestly until a native `patients` table lands).
  - `stub.py` — `StubClinicalSystemAdapter(writes_allowed)`.
    Canned reads; write-through records writes to an in-process
    list, read-through raises `AdapterNotSupported`.
  - `__init__.py` — `resolve_adapter()` + mutable
    `_VENDOR_ADAPTERS` registry + `register_vendor_adapter(key,
    factory)`.

### Step 3 — HTTP surface
- New `GET /platform` (any authenticated caller). Returns mode +
  adapter key + display name + description + supports-* flags +
  source-of-truth map. Zero secret leakage (asserted in tests).

### Step 4 — Frontend mode awareness
- `api.ts` gains `PlatformInfo`, `PlatformMode`, `SourceOfTruth`
  types + `getPlatform(email)` + `platformModeLabel(mode)`.
- `AdminPanel.tsx` fetches `/platform` on mount (alongside
  `/organization`) and renders a **platform banner** above the
  tabs: "Platform mode: <mode> · <adapter display name>". Visible
  on every admin view.
- `styles.css` — new `.platform-banner` rule matching the
  existing admin look.

### Step 5 — Backend tests
- New `tests/test_platform_mode.py` (13 tests): default mode,
  integrated defaults, invalid mode, standalone-forbids-stub,
  adapter resolution per mode (native / stub read-through / stub
  write-through), unknown vendor key, vendor registration path,
  native refuses unsupported, `/platform` endpoint surface +
  auth guard. All 131 pytest pass.

### Step 6 — Frontend tests
- `AdminPanel.test.tsx` adds 2 tests — banner renders standalone
  default, banner reflects integrated-readthrough. All mocks
  updated (`getPlatform` added). Vitest: **30/30 passed**.

### Step 7 — Docs
- New `docs/build/26-platform-mode-and-interoperability.md`
  (engineering contract).
- New `docs/build/27-adoption-and-implementation-model.md`
  (operator/clinic adoption model).
- Updated `01-current-state`, `04-data-model`, `05-build-log`
  (this entry), `06-known-gaps`, `08-test-strategy`,
  `12-runtime-config`, `15-frontend-integration`,
  `16-frontend-test-strategy`.
- `docs/diagrams/system-architecture.md` — added adapter boundary.
- `docs/diagrams/api-data-flow.md` — added adapter resolution
  flow.
- `scripts/build_docs.py` picks up sections 26 + 27; executive
  summary extended; HTML + PDF regenerated.

### Step 8 — Verification
- Backend: **131/131 pytest**, 9/9 smoke via `make verify`.
- Frontend: **30/30 Vitest**, typecheck clean, build emits
  ~187 KB JS / 8.3 KB CSS.
- Postgres parity: `scripts/pg_verify.sh` — migrate / seed /
  smoke / status transition all green against Postgres 16.
- Standalone boot: `CHARTNAV_PLATFORM_MODE=standalone` → native
  adapter.
- Integrated boot: `CHARTNAV_PLATFORM_MODE=integrated_readthrough
  CHARTNAV_INTEGRATION_ADAPTER=stub` → stub adapter refuses
  writes.

---

## 2026-04-18 — Phase 15: enterprise quality + compliance signals

### Step 1 — Baseline
- Head: `3be3933` (invitations + settings schema + audit export + event hardening + bulk users).
- 110 pytest + 25 Vitest + 12 Playwright + 9 smoke green.

### Step 2 — Admin list scaling
- Backend: `GET /users` and `GET /locations` now accept `limit`
  (1..500, default 100), `offset` (≥0), `q` substring search, and
  `role` (users only). Both endpoints emit `X-Total-Count`, `X-Limit`,
  `X-Offset` headers. `include_inactive` continues to work.
- Invalid role filter → 400 `invalid_role`.
- Frontend: `api.ts` gains `listUsersPage` / `listLocationsPage` that
  return `{items, total, limit, offset}` by reading the headers.
- `AdminPanel.tsx`: Users + Locations tabs each get a search input +
  Prev/Next pager (25/page) + count header. Self-search resets offset
  on every change.

### Step 3 — Feature-flag consumption
- New `featureEnabled(org, flag)` helper in `api.ts` — flags default
  to `true` when unset so the UI doesn't silently strip features for
  orgs that haven't touched settings.
- AdminPanel loads `getOrganization(identity)` on mount, holds the
  result in state, and passes it into panes that gate UI.
- `audit_export=false` hides the **Export CSV** button. `bulk_import=false`
  hides the **Bulk import…** button. Both default-on.
- `flash` in AdminPanel is now `useCallback`-stable, avoiding an
  infinite refresh loop that showed up once children started holding
  it in `refresh` dependency arrays.

### Step 4 — Audit retention helper
- New `apps/api/app/retention.py::prune_audit_events(retention_days, dry_run)`.
  App never silently prunes; operators invoke the helper.
- New `CHARTNAV_AUDIT_RETENTION_DAYS` (default 0 = never) in `app/config.py`.
- New `scripts/audit_retention.py` CLI: supports `--days`, `--dry-run`;
  prints a JSON summary.
- New Makefile target `audit-prune ARGS="..."`.

### Step 5 — SBOM + image digest
- New `scripts/sbom.py`: captures project + git sha/tag/dirty + image
  tag (when set) + `pip list --format json` (API venv) + `npm list
  --all --json` (falls back to `package-lock.json` summary). Honest
  `.notes` field calls out that this is not a signed CycloneDX doc.
- `scripts/release_build.sh` now writes `chartnav-sbom-<v>.json` and
  `chartnav-api-<v>.digest.txt` (from `docker image inspect`).
- `MANIFEST.txt` sha256s both. `release.yml` attaches both to tag-based
  GitHub Releases.

### Step 6 — Accessibility baseline
- Installed `@axe-core/playwright`.
- New `apps/web/tests/e2e/a11y.spec.ts`: scans app shell + encounter
  list + encounter detail + admin panel (users, audit) + invite
  accept. `serious`/`critical` axe findings are blocking.
- Fixes landed while running the baseline:
  - `aria-label="Event type"` on the composer `<select>` in App.tsx.
  - `aria-label="Role for <email>"` on each inline role `<select>`
    in the admin Users table.

### Step 7 — Visual regression baseline
- New `apps/web/tests/e2e/visual.spec.ts`: 4 snapshots (encounter list,
  admin Users tab, admin Audit tab, invite accept). 1280×820 viewport,
  animations disabled via injected stylesheet, `maxDiffPixelRatio: 0.02`.
- Baselines committed for macOS only (`*-chromium-darwin.png`). CI
  does NOT run visual — Linux Chromium renders slightly differently.
  Honest limitation: documented in `25-enterprise-quality-and-compliance.md`.
- New `e2e-visual` / `e2e-visual-update` Make targets.

### Step 8 — CI wiring
- Existing `e2e` job now runs `workflow.spec.ts` + `a11y.spec.ts` (hard
  gate). Visual is excluded with a comment explaining why.
- Release workflow picks up SBOM + image digest automatically via the
  updated `scripts/release_build.sh`.

### Step 9 — Playwright rate-limit bugfix
- Running the full E2E suite (workflow + a11y + visual) was hitting
  the rate limiter (`CHARTNAV_RATE_LIMIT_PER_MINUTE=120` default)
  because all requests come from 127.0.0.1. Fix: set the env to `0`
  in `playwright.config.ts`'s backend webServer command, which is
  safe because the E2E DB is always ephemeral.

### Step 10 — Backend tests
- New `apps/api/tests/test_enterprise.py` (8 tests): pagination
  headers + offset + q + role filter + cross-org isolation; role
  filter 400; retention disabled / dry-run / actual delete; feature
  flags JSON round-trip.
- Full suite: **118/118 passed**.

### Step 11 — Frontend tests
- `AdminPanel.test.tsx` mocks extended for `listUsersPage`,
  `listLocationsPage`, `getOrganization` feature-flag variants.
- +3 Vitest tests: `audit_export=false` hides export button;
  `bulk_import=false` hides bulk button; user-search dispatches
  `listUsersPage({q})`.
- Vitest: **28/28 passed**.

### Step 12 — E2E
- a11y: **5/5 passed**.
- Visual: **4/4 passed** against freshly-generated macOS baselines.
- Workflow: **12/12 passed**.
- Total: **21/21 Playwright passed** in ~18s.

### Step 13 — Docs
- New `docs/build/25-enterprise-quality-and-compliance.md`.
- Updated `01-current-state`, `05-build-log`, `06-known-gaps`,
  `03-api-endpoints` (list pagination/search), `04-data-model`
  (feature_flags consumer note), `08-test-strategy`,
  `09-ci-and-deploy-hardening` (a11y lane + visual skipped reason),
  `15-frontend-integration` (search + pager + flag gating),
  `16-frontend-test-strategy` (a11y + visual), `17-e2e-and-release`
  (SBOM + digest bundle), `18-operational-hardening` + `20-observability`
  (retention notes), `21-staging-runbook` (retention runbook).
- `scripts/build_docs.py` picks up section 25.
- Final HTML + PDF regenerated.

### Step 14 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines committed under `apps/web/tests/e2e/visual.spec.ts-snapshots/`.
- `.gitignore` already excludes caches, `.db`, release dist.

---

## Prior phases

- **Phase 14 — Invitations + schema + audit export + bulk** (`3be3933`)
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
