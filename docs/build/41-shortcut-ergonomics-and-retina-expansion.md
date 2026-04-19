# Phase 30 — Shortcut Ergonomics + Retina Expansion

> Three narrow wins on the phase-29 Clinical Shortcuts surface:
> per-doctor shortcut favorites, caret-jump-to-first-blank, and a
> retina-heavy catalog expansion (diabetic retinopathy / DME,
> ERM / VMT / macular hole, BRVO / CRVO / retinal vascular, and
> post-injection / post-vitrectomy / post-op). Abbreviation reference
> grows only where the new content actually uses it.

## What changed

### 1. Shortcut favorites

- **New table** `clinician_shortcut_favorites` (migration
  `e1f2a3041505`) keyed on the catalog's stable string ref. One row
  per `(user, shortcut_ref)` via a `UNIQUE` constraint. Separate
  from phase-28's `clinician_quick_comment_favorites` because the
  two favoritism models evolve on different namespaces and have
  different soft-delete semantics — unifying them behind a 3-way
  CHECK constraint in SQLite would be harder to migrate than this
  narrow second table.
- **Three endpoints** under `/me/clinical-shortcuts/favorites`:
  - `GET` — list the caller's pins (ordered by creation).
  - `POST` — idempotent upsert of `{shortcut_ref}`; re-firing the
    same ref returns the existing row.
  - `DELETE ?shortcut_ref=…` — remove; second call is a clean
    `{removed: 0}`.
  - All three admin/clinician only (reviewer → 403
    `role_cannot_edit_quick_comments`, reusing the phase-27
    helper).
  - Audit events `clinician_shortcut_favorited` and
    `_unfavorited` on lifecycle mutations.
- **Frontend** — `api.ts` gains `ClinicalShortcutFavorite`,
  `listMyClinicalShortcutFavorites`, `favoriteClinicalShortcut`,
  `unfavoriteClinicalShortcut`. `NoteWorkspace` renders a **★
  Favorites** strip at the top of the Clinical Shortcuts panel
  whenever at least one pin still resolves (a favorite whose ref
  has been removed from the catalog is silently filtered out,
  never broken), and a `☆ / ★` toggle on every shortcut in the
  main catalog.

### 2. Caret-jump to first blank

- **New helper** `firstBlankOffset(body)` in
  `apps/web/src/clinicalShortcuts.ts`, plus a
  `SHORTCUT_BLANK_TOKEN = "___"` constant so any future token
  change is a one-line swap.
- **`spliceIntoDraft`** in `NoteWorkspace.tsx` now scans the
  inserted phrase for the first `___`. When found, the caret jumps
  to that offset **and selects the three underscores** so the
  clinician replaces the placeholder by typing in one gesture.
  When no placeholder exists, the behaviour is identical to the
  phase-28 baseline: caret lands at the end of the inserted text.
- Shared between Quick Comments and Clinical Shortcuts because
  the splice helper is — by design — the single insertion seam.
  Quick comments rarely carry `___`, but when they do, landing on
  it is the right default.
- Works for quick comments containing `___` too (harmless
  non-regression).

### 3. Retina expansion — 20 new shortcuts across 4 new groups

Clinical tone and vocabulary aligned with AAO-style subspecialty
charting. Nothing speculative, no junk filler. Blanks (`___`) are
intentional fill-in points.

| Group | IDs | Phrase count |
|---|---|---|
| Diabetic retinopathy / DME | `dm-01…dm-05` | 5 |
| ERM / VMT / macular hole | `mac-01…mac-05` | 5 |
| BRVO / CRVO / retinal vascular | `vasc-01…vasc-05` | 5 |
| Post-injection / post-vitrectomy / post-op | `post-01…post-05` | 5 |

Coverage at a glance:

- **DR/DME**: NPDR no DME observation; moderate NPDR + CI-DME →
  anti-VEGF; PDR s/p PRP stable; active PDR (NVD/NVE) → complete
  PRP; CI-DME on OCT with CST microns placeholder.
- **ERM/VMT/MH**: ERM + mild metamorphopsia; VMT + foveal
  distortion; FTMH stage/size placeholders + PPV/ILM/gas;
  post-op FTMH closed; lamellar MH stable observation.
- **Vascular**: BRVO + ME on OCT + anti-VEGF; non-ischemic CRVO
  + anti-VEGF + monitor conversion; ischemic CRVO + FA
  non-perfusion + NVI/NVG watch; BRAO + embolic workup;
  hypertensive retinopathy + BP counseling.
- **Post-op**: intravitreal injection procedural note (povidone
  5%, speculum); post-injection return precautions;
  post-op PPV day checklist (retina attached, IOP, AC, taper);
  post-op SB week (buckle in position, attached 360°);
  post-op PRP uptake check.

### 4. Abbreviation subset growth

Grew from **29** to **50** hints. Only added entries actually
used in — or plausibly searched alongside — the new shortcuts:

> `AC, BRAO, BRVO, CRAO, CRVO, DM, DME, FA, FTMH, ILM, IVT, ME,
> MH, NV, NVD, NVE, NVG, NVI, PCP, S/P, VA` (+ existing 29).

`ILM` is included even though it isn't in the Spokane Eye Clinic
sheet — it is clinically essential (`PPV + ILM peel`) and the
sheet's footnote explicitly states it is "not inclusive of all
medical abbreviations used." The full PDF is still **not** dumped
into the UI per the phase-29 rule.

### 5. Case-insensitive abbreviation matcher

`segmentAbbreviations` now matches with the `i` flag and normalises
to the canonical uppercase key for the hint lookup. This lets
clinician shorthand like `s/p PPV` — which ophthalmology notes
always write lowercase — render with hover help
(`Status post`) without having to maintain twin uppercase/
lowercase keys. Word-boundary guards keep false-positive matches
inside ordinary prose impossible (verified with the regression set
in the existing tests).

## Data + trust invariants preserved

- Shortcuts remain clinician-inserted content only. They are not
  joined to `encounter_inputs`, `extracted_findings`,
  `note_versions`, or transmitted artifacts.
- Favorite rows carry only a `shortcut_ref` — never the body.
- Backend test sweeps `/encounters/{id}` and
  `/encounters/{id}/events` to confirm shortcut favorites never
  leak there.
- Reviewer role continues to be invisible to the entire surface.

## Test coverage

- **Backend** (+8 in `tests/test_clinical_shortcut_favorites.py`):
  happy-path create, idempotent upsert, list scoping (own-only
  across users in the same org), DELETE via query param +
  idempotent second-call, reviewer 403 on all three endpoints,
  empty `shortcut_ref` rejected, audit events for
  create + remove, surface isolation.
  Full backend suite: **293 passed** (285 + 8).
- **Frontend** (+10 in `NoteWorkspace.test.tsx`):
  - four new group testids render with verbatim phrasing
    spot-checks via `toHaveTextContent` (crosses `<abbr>`
    boundaries).
  - abbreviation-aware search: `DME` surfaces the diabetic
    group (and drops PVD), `CRVO` surfaces the retinal-vascular
    group, `FTMH` surfaces mac-03 + mac-04.
  - shortcut star toggle calls `favoriteClinicalShortcut` and
    triggers a list refetch.
  - Favorites strip renders above the main catalog when a pin
    exists; pinned main-catalog row reports `aria-pressed=true`.
  - Reviewer: Favorites strip + star buttons both hidden; no
    API fetch fires.
  - Caret-jump: clicking `rd-01` selects the three underscore
    placeholder; text `selectionStart`==`firstBlank`.
  - Caret fallback: clicking `pvd-03` (no blank) lands the
    collapsed caret after the seeded prefix, not on a phantom
    `___`.
  - `s/p` inside `dm-03` renders as `<abbr title="Status post">`
    via the case-insensitive matcher.
  - Full vitest suite: **102 passed** (19 App + 20 AdminPanel +
    63 NoteWorkspace).
- Typecheck clean. Vite build 246.74 kB JS / 21.26 kB CSS
  (gzip 72.46 / 4.41 kB).

## Files touched

- `apps/api/alembic/versions/e1f2a3041505_clinical_shortcut_favorites.py` (new)
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_clinical_shortcut_favorites.py` (new)
- `apps/web/src/clinicalShortcuts.ts` — 20 new shortcuts, 21
  new abbreviation hints, `SHORTCUT_BLANK_TOKEN` +
  `firstBlankOffset`, case-insensitive tokenizer
- `apps/web/src/api.ts` — shortcut-favorites helpers
- `apps/web/src/NoteWorkspace.tsx` — favorites state,
  Favorites strip, star toggle, caret-to-blank splice
- `apps/web/src/test/NoteWorkspace.test.tsx` — +10 tests + mocks
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `41-shortcut-ergonomics-and-retina-expansion.md` (new)

## Deliberately not done

- **No unified favorites model.** Phase-28 quick-comment favorites
  and phase-30 shortcut favorites remain on separate tables. A
  3-way CHECK constraint would complicate the migration story on
  SQLite and the two models already evolve independently (a
  custom quick-comment id can be soft-deleted; a shortcut ref
  cannot).
- **No next/prev blank hotkey.** Tab to the next `___` is a
  logical extension once clinicians ask for it. The current
  one-shot jump handles the most common case (single blank) and
  the caret lands on the first blank for phrases with multiple,
  which is where typing usually starts anyway.
- **No Playwright scenario.** Phase-28's `quick-comments.spec.ts`
  already proves the full cross-stack insertion wedge through the
  shared splice helper. Adding a second scenario that only swaps
  the URL would duplicate coverage.
- **No org-shared catalog extensions.** The catalog remains
  shared static content. Per-org / per-subspecialty additions
  will land when a clinical product owner reviews the phrasing.

## Follow-on work

1. **Tab-to-next-blank.** When a phrase has multiple `___`, a
   Tab keystroke inside the textarea could jump to the next one.
   Small addition to the `onKeyDown` for the draft textarea.
2. **Glaucoma / cornea / oculoplastics packs.** Same structure,
   same infra. Add once clinical reviewers sign off on phrasing.
3. **Favorites ordering.** Pinned shortcuts render in
   `created_at ASC`. A drag-handle + `position` column would let
   the doctor curate order.
4. **Usage-summary analytics view.** The audit log now has both
   `clinician_shortcut_favorited` + `_used` streams. A
   `GET /admin/shortcut-usage-summary?days=90` endpoint (same
   pattern as the audit-export CSV) would answer "which retina
   shortcuts get reached for most?" cleanly.
