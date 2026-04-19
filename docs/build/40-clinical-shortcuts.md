# Phase 29 — Clinical Shortcuts (specialist shorthand pack)

> A doctor-only specialist shorthand phrase bank, separate from the
> phase-27 Quick Comments pad. Ten verbatim clinical phrases across
> three retina groups (PVD, Retinal detachment, Wet/Dry AMD),
> abbreviation-aware search, subtle hover help on high-value
> ophthalmic abbreviations, cursor-position insertion, and a
> dedicated usage-audit stream so shorthand ergonomics can be
> analysed without noise from Quick Comments clicks.

## Why a separate surface from Quick Comments

- **Different product semantic.** Quick Comments are clinician
  clipboard-style snippets (preloaded picks + per-user custom
  authored text). Clinical Shortcuts are a **curated shorthand
  phrase bank** of structured note fragments subspecialists
  actually write.
- **Different persistence model.** Quick Comments' custom items live
  per-user in `clinician_quick_comments` on the backend. Clinical
  Shortcuts are shared UI content — identical for every clinician —
  and ship as a static TypeScript module. No DB table, no seed.
- **Separate analytics channel.** Mixing the two usage streams into
  one audit event would defeat the "which shorthand do doctors
  actually reach for?" question. A new `clinician_shortcut_used`
  event keeps the two streams cleanly separable.

## What ships

- **10 shortcuts** in three groups — verbatim from the brief:

  - **PVD** (3) — acute, symptomatic, chronic.
  - **Retinal detachment** (4) — rhegmatogenous preop, localized SRF,
    retina-attached-under-oil/gas, post-op follow-up.
  - **Wet/Dry AMD** (3) — dry with drusen/RPE mottling, intermediate
    nonexudative, exudative with IRF/SRF/PED.

  Phrasing preserves clinical blanks like `___` and `/` (e.g.
  "macula on / macula off") so the clinician fills them in after
  insertion. These are intentional shortcuts, not template bugs.

- **Curated abbreviation reference** (29 entries) — a narrow subset
  of the Spokane Eye Clinic common ophthalmic abbreviations sheet,
  restricted to terms that appear in — or are likely-searched
  alongside — the shipped shortcuts. The full sheet is deliberately
  NOT dumped into the UI. Entries include:
  AMD, ARMD, CME, C/D, DFE, D&Q, ERM, IOP, IRF, OCT, ONH, OD, OS,
  OU, PED, PDR, NPDR, PPV, PR, PRP, PVD, RAPD, RD, RPE, RT, SB,
  SLE, SRF, VMT.

- **Abbreviation-aware search.** The single search input filters on
  the union of the shortcut body, group name, explicit tag list,
  and — crucially — the expanded meaning of any abbreviation whose
  token appears in the query. So typing `RD` surfaces every phrase
  whose tags include `rd` OR whose body spells out "retinal
  detachment"; typing `SRF` surfaces both `rd-02` (body mentions
  "subretinal fluid") and `rd-04` (body mentions "SRF" literally);
  typing `AMD` restricts to the Wet/Dry AMD group.

- **Subtle hover help** on abbreviations that appear inside a
  shortcut body — rendered with `<abbr title="...">` so the hover
  tooltip is native, dotted-underline styling so it reads as "more
  info" rather than a clickable link. Longest-match tokenization so
  `NPDR` isn't split into `N` + `PDR`. Word-boundary guard so
  `IRF` inside an unrelated word can't trigger.

- **Cursor-position insertion** — reuses phase-28's splice logic via
  a freshly-extracted `spliceIntoDraft(body, flashLabel)` helper
  shared with Quick Comments. Cursor lands at the end of the
  inserted phrase after a `requestAnimationFrame` re-focus; browser
  undo over subsequent keystrokes stays coherent.

- **Dedicated usage-audit stream** —
  `POST /me/clinical-shortcuts/used` emits a
  `clinician_shortcut_used` audit event whose detail carries only
  the shortcut ref ID plus optional `note_version_id` /
  `encounter_id`. **Never** the body. Fire-and-forget: telemetry
  failures never block the clinician.

## Data flow

```
 Doctor clicks a Clinical Shortcut
   → NoteWorkspace.insertClinicalShortcut(shortcut)
   → spliceIntoDraft(body)        ── edits `editBody` at cursor
   → recordClinicalShortcutUsage  ── fire-and-forget POST
       → audit event: clinician_shortcut_used
         detail: shortcut_id=<id> note_version_id=<id> encounter_id=<id>
```

The spliced body lives in the doctor's draft buffer and only reaches
`note_versions.note_text` if the doctor explicitly saves the draft
through the existing PATCH path. The artifact pipeline (phase 25)
sees only what the doctor actually saved; the shortcut audit event
is a separate tell-tale that the insertion happened, not a bypass
into the note record.

## Gating

- **Role** — admin + clinician only. Reviewers never see the panel
  and the usage-audit POST returns 403
  `role_cannot_edit_quick_comments` (reused from phase 27's role
  helper — shorthand insertion is the same class of clinician-author
  action).
- **Signed notes** — every shortcut button is `disabled` when the
  note is signed/exported. A defensive guard inside
  `spliceIntoDraft` also refuses silently if somehow invoked.
- **No encounter scoping** — the shortcut catalog is static UI
  content. There's no per-encounter or per-org list to leak.

## Provenance invariants preserved

- Clinical Shortcuts are NOT stored in, joined to, or returned by
  any of: `encounter_inputs`, `extracted_findings`,
  `note_versions` (except as body text the doctor explicitly
  typed/inserted + saved), or transmitted artifact payloads.
- The `clinician_shortcut_used` audit detail never contains the
  shortcut body — a backend test proves the invariant by sneaking
  a `body` field into the request and asserting it never lands in
  any recorded detail.
- The Clinical Shortcuts panel renders in its own top-level section
  inside `NoteWorkspace`, structurally disjoint from the
  Quick Comments panel. A frontend test asserts the two panels
  neither contain nor are contained by each other.

## Test coverage

- **Backend** (+6 in `tests/test_clinical_shortcuts.py`):
  - clinician happy path → 202 + `clinician_shortcut_used` event
    whose detail carries `shortcut_id`, `note_version_id`,
    `encounter_id`.
  - empty `shortcut_id` → 400/422 (Pydantic validator + handler
    guard).
  - reviewer → 403 `role_cannot_edit_quick_comments`.
  - PHI invariant: sneaking a `body` field into the request
    never lands in any audit detail.
  - two event streams co-exist: both
    `clinician_shortcut_used` and `clinician_quick_comment_used`
    appear after firing one of each.
  - surface isolation: the shortcut detail does not leak to
    `/encounters/{id}` or `/encounters/{id}/events`.
  - Full backend suite: **285 passed** (279 + 6).
- **Frontend** (+11 in `src/test/NoteWorkspace.test.tsx`):
  - reviewer hides the panel and skips the audit POST.
  - all three groups render with verbatim phrasing (spot-check
    includes the explicit "macula on / macula off" slash).
  - abbreviations inside bodies render as `<abbr title="...">`
    with the expected expansion for AMD and RPE.
  - click-to-insert lands the full phrase in the draft.
  - click fires `recordClinicalShortcutUsage` with the ref id
    and no `body` key.
  - signed note disables the buttons.
  - abbreviation-aware search for `RD`, `SRF`, `AMD`: each query
    returns the expected filtered groups/rows.
  - structural panel-isolation assertion (Clinical Shortcuts
    and Quick Comments are siblings, neither a descendant of
    the other).
  - separate streams: a shortcut click must NOT fire
    `recordQuickCommentUsage`.
  - Full vitest suite: **92 passed** (19 + 20 + 53). Typecheck
    + Vite build clean (238 kB JS / 21.26 kB CSS).

## Files touched

- `apps/api/app/api/routes.py` — new shortcut-usage route
- `apps/api/tests/test_clinical_shortcuts.py` (new)
- `apps/web/src/clinicalShortcuts.ts` (new) — catalog, abbreviation
  table, abbreviation-aware search predicate, body segmenter
- `apps/web/src/api.ts` — `recordClinicalShortcutUsage` helper
- `apps/web/src/NoteWorkspace.tsx` — extracted `spliceIntoDraft`,
  new `insertClinicalShortcut`, new panel with grouped render +
  search + `<abbr>` hover help
- `apps/web/src/styles.css` — shortcut section + `.cn-abbr` style
- `apps/web/src/test/NoteWorkspace.test.tsx` — 11 new tests + mock
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `40-clinical-shortcuts.md` (new)

## Deliberately not done

- **No DB table for the catalog.** Static UI content only. Adding a
  `clinical_shortcuts` table would be persistence cost with no gain
  — the catalog isn't per-user, per-org, or author-editable today.
- **No free-form custom shortcut authoring.** Quick Comments already
  covers that ergonomic. Clinical Shortcuts is a curated pack.
- **No whole-PDF dump.** The ophthalmic abbreviations reference is
  narrowed to entries relevant to the ten shipped shortcuts.
- **No Playwright spec.** The existing phase-28
  `quick-comments.spec.ts` already proves the cross-stack wedge
  (identity → encounter → draft → insert); the shortcut path reuses
  the same splice helper and the same audit plumbing with a
  different URL, so a second e2e scenario would duplicate coverage.
  Add one when the catalog grows enough to justify it.

## Follow-on work

1. **Per-group favorites.** Reuse the phase-28 favorites model by
   adding a `shortcut_ref` column alongside the existing
   `preloaded_ref` / `custom_comment_id` so a doctor can pin three
   or four specialist shortcuts to a compact strip above the main
   catalog.
2. **Fill-in-the-blank assist.** Phrases like
   "involving ___ quadrants" would benefit from placing the caret
   on the first `___` after insertion. Small change to the
   `spliceIntoDraft` helper.
3. **Org-shared catalog extensions.** If subspecialty groups want
   their own phrasings, layer a small
   `clinical_shortcut_extensions` table per organization that the
   frontend appends to the static catalog. Out of scope here.
4. **Full subspecialty pack.** Glaucoma, cornea, oculoplastics,
   peds, strabismus, uveitis — same structure, same infra. Add a
   new group array + entries in `clinicalShortcuts.ts` when the
   phrases are reviewed.
5. **Abbreviation coverage.** The current 29-entry subset can grow
   organically as new shortcuts ship. Adding every term from the
   reference sheet would clutter hover help without improving
   charting; keep the bar at "appears in a live shortcut or a
   plausible search".
