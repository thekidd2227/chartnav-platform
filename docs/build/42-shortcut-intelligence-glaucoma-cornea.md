# Phase 31 — Shortcut Intelligence + Glaucoma/Cornea Expansion

> Three narrow wins on the phase-29/30 Clinical Shortcuts surface:
> Tab-to-next-blank inside the draft textarea, an admin usage-summary
> read over the existing audit stream, and a conservative
> subspecialty expansion into Glaucoma and Cornea / anterior segment.
> Catalog is now 42 shortcuts across 9 groups with 76 curated
> abbreviation hints.

## 1. Tab-to-next-blank

### Behaviour
- Pressing `Tab` inside the draft textarea finds the next `___`
  at or after the current `selectionEnd` and selects its three
  characters. The clinician types straight over it.
- Modifier keys (Shift, Ctrl, Meta, Alt) pass through to the
  browser default (Shift+Tab still focuses the previous element).
- When no `___` remains after the caret, the handler does
  nothing — the default Tab event runs, moving focus to the next
  DOM element. Nothing about the draft is mutated.

### Implementation
- New helper `nextBlankAfter(body, fromOffset)` in
  `apps/web/src/clinicalShortcuts.ts`. Re-uses
  `SHORTCUT_BLANK_TOKEN` from phase 30.
- New `onKeyDown` handler on the editable draft textarea in
  `NoteWorkspace.tsx`. Reads `ta.value` + `ta.selectionEnd`,
  calls `nextBlankAfter`, and either `preventDefault()` +
  `setSelectionRange` (land on the next blank) or returns (let
  Tab escape).
- Preserves the phase-30 **caret-to-first-blank** on insertion
  — a Tab press after a freshly-inserted shortcut walks from
  the first blank to the second without extra work.

## 2. Shortcut usage intelligence

### Endpoint
```
GET /admin/shortcut-usage-summary?days=30&limit=50
```

- **Admin-only.** Clinicians + reviewers → 403. Org-scoped
  (reads `security_audit_events.organization_id`).
- **Days window** — `[1, 365]`, default 30. `<1` or `>365`
  → 422 from FastAPI validation.
- **Limit** — `[1, 200]`, default 50.
- **Aggregation** — reads `security_audit_events` where
  `event_type = 'clinician_shortcut_used'`, regex-parses the
  `shortcut_id=<ref>` token out of the detail string, aggregates
  to `{shortcut_ref, count, last_used_at}`. Ranked
  most-used-first, ties broken by ref for deterministic order.

### Response shape
```json
{
  "window_days": 30,
  "organization_id": 1,
  "generated_at": "2026-04-19T…",
  "total_events": 47,
  "distinct_refs": 9,
  "items": [
    {"shortcut_ref": "pvd-01", "count": 12, "last_used_at": "2026-04-19T…"},
    {"shortcut_ref": "glc-05", "count": 8,  "last_used_at": "2026-04-18T…"},
    …
  ]
}
```

### Why this shape (not a bigger dashboard)
- Reuses the existing audit stream. No new storage, no worker,
  no cron. The `clinician_shortcut_used` event was already being
  emitted since phase 29; we just read it.
- PHI minimising by construction: the detail string only ever
  carried `shortcut_id`, `note_version_id`, `encounter_id`. The
  summary response discards the last two — only the catalog ref
  + count + timestamp.
- Operational lens, not a per-patient data view. A backend test
  asserts that `note_version_id` / `encounter_id` never appear
  in any row of the response even when the upstream event
  carried them.

## 3. Glaucoma + Cornea expansion — 12 new shortcuts

Conservative AAO-style phrasing. Blanks (`___`) are intentional
fill-in points; Tab walks between them after insertion.

### Glaucoma (`glc-01 … glc-06`)
| ID | Coverage |
|---|---|
| `glc-01` | POAG severity + C/D OD/OS + VF + RNFL + drops + target IOP |
| `glc-02` | OHT without glaucomatous optic neuropathy + C/D + IOP + CCT + target |
| `glc-03` | PXF / PDS on gonioscopy → secondary OAG + drops + target |
| `glc-04` | Narrow angles without ACG → prophylactic LPI |
| `glc-05` | Post-op s/p trabeculectomy + bleb + AC + IOP + steroid taper |
| `glc-06` | Post-op s/p glaucoma drainage device + tube position + IOP |

### Cornea / anterior segment (`cor-01 … cor-06`)
| ID | Coverage |
|---|---|
| `cor-01` | DED with SPK OU + reduced TBU + Schirmer + ATs / warm compresses / lid hygiene |
| `cor-02` | MGD + inspissated glands + lid-margin telangiectasia + posterior blepharitis |
| `cor-03` | Keratoconus + inferior steepening + K-max + pachymetry + CXL vs. obs |
| `cor-04` | Recurrent corneal erosion → BSCL + lubrication + debridement / PTK if refractory |
| `cor-05` | Fuchs endothelial dystrophy + central guttae + pachymetry + DSEK counseling |
| `cor-06` | Post-op s/p DSEK + graft adherence + interface fluid + steroid taper |

## 4. Abbreviation curation (50 → 76)

Added only terms that actually appear in the new live content or
are plausible search queries for glaucoma/cornea charting:

> **Glaucoma**: `ACG, CCT, GDD, LPI, NAG, OHT, PDG, PDS, POAG, PXF,
> PXFG, RNFL, SLT, Trab, VF`
>
> **Cornea**: `AT, BSCL, CXL, DED, DSEK, KC, KCS, MGD, PTK, RCE,
> SPK, TBU`

The full ophthalmic abbreviation sheet is still **not** dumped
into the UI. `CXL` and `BSCL` / `RCE` are included even though
they aren't in the Spokane Eye Clinic source sheet because they
are clinically essential to live shortcuts in this pack; the
sheet's own footnote explicitly disclaims completeness.

## Data + trust invariants preserved

- Shortcuts remain clinician-inserted content only.
- Shortcut favorites + usage events remain orthogonal to
  `encounter_inputs`, `extracted_findings`, `note_versions`, and
  transmitted artifacts.
- Reviewer role continues to be invisible across the entire
  Clinical Shortcuts surface (catalog, favorites, usage audit,
  and the new admin summary view).
- The new usage-summary response shape is a minimal
  `{ref, count, last_used_at}` tuple per row. PHI-minimising
  test asserts the wire output never carries `note_version_id` /
  `encounter_id` even when the upstream event did.

## Test coverage

- **Backend** (+8 in `tests/test_shortcut_usage_summary.py`):
  - clinician → 403, reviewer → 403 (admin-only route)
  - ranked rollup — counts correct per ref, ranking
    most-used-first with stable tie-break, last_used_at
    populated
  - cross-org events never leak into another org's summary
  - `days=0` and `days=400` → 422; `days=90` → 200 with
    `window_days=90`
  - `limit` caps the rows but `distinct_refs` reflects the full
    universe
  - PHI invariant: `note_version_id` / `encounter_id` never
    appear in any row of the response
  - Quick-comment usage events (`clinician_quick_comment_used`)
    are NOT conflated into the shortcut summary
  - Full backend suite: **301 passed** (293 + 8).
- **Frontend** (+6 in `src/test/NoteWorkspace.test.tsx`):
  - two new subspecialty groups render with verbatim phrasing
    spot-checks (`glc-02` / `glc-04` / `cor-03` / `cor-05`)
  - abbreviation-aware search: `POAG` surfaces Glaucoma and
    drops retina groups; `CXL` surfaces Cornea with
    keratoconus
  - Tab inside the draft with two placeholders walks
    first → second; selection starts match the expected
    offsets exactly
  - Tab fallback when no blanks remain: `defaultPrevented === false`
    and neither the value nor the selection mutates
  - Shift+Tab is left untouched by the next-blank handler —
    default browser behaviour runs
  - Full vitest suite: **108 passed** (19 + 20 + 69).
- Typecheck + Vite build clean (251.18 kB JS / 21.26 kB CSS).

## Files touched

- `apps/api/app/api/routes.py` — new `/admin/shortcut-usage-summary` route
- `apps/api/tests/test_shortcut_usage_summary.py` (new) — 8 scenarios
- `apps/web/src/clinicalShortcuts.ts` — 12 new shortcuts across 2
  new groups, 26 new abbreviation hints, `nextBlankAfter` helper
- `apps/web/src/NoteWorkspace.tsx` — Tab-to-next-blank onKeyDown
- `apps/web/src/test/NoteWorkspace.test.tsx` — 6 new tests
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `42-shortcut-intelligence-glaucoma-cornea.md` (new)

## Deliberately not done

- **No new storage for usage analytics.** The summary reads the
  audit stream directly. Adding a rollup table is easy if the
  query gets slow; not needed today.
- **No backward Tab (Shift+Tab walks backward through blanks).**
  Narrow scope — forward-only is the common case. Shift+Tab is
  deliberately left to the browser.
- **No per-user breakdown in the summary.** That's a
  potentially-sensitive "who reached for what" lens. If product
  asks, add a separate `?by_user=true` flag behind an
  explicitly-gated admin capability.
- **No Playwright scenario.** Existing phase-28
  `quick-comments.spec.ts` already proves the cross-stack
  insertion wedge. Adding a Tab-walk spec would duplicate
  coverage — unit tests cover the semantics directly.

## Follow-on work

1. **Shift+Tab backward walk** — if clinicians ask for it.
2. **Per-user usage summary** — behind an explicit flag
   (`?by_user=true`), same admin endpoint.
3. **Shortcut usage CSV export** — reuse the audit-export
   pattern from phase 14.
4. **Peds / uveitis / oculoplastics packs** — same structure,
   same infra. Add once the phrasings are reviewed.
