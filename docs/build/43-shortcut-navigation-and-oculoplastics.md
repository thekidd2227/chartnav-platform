# Phase 32 — Shift+Tab Backward + Per-User Usage + CSV Export + Oculoplastics

> Four tight wins on the Clinical Shortcuts surface: bidirectional
> blank navigation, an optional per-user breakdown on the admin
> usage summary, a CSV export path, and a curated Oculoplastics /
> lids / adnexa pack. Catalog is now 48 shortcuts across 10 groups
> with 79 curated abbreviation hints.

## 1. Shift+Tab backward blank navigation

- **New helper** `prevBlankBefore(body, fromOffset)` in
  `clinicalShortcuts.ts`. Returns the offset of the last `___`
  that starts **strictly before** `fromOffset`, or `-1`. The
  `-1` is what lets the handler hop away from a blank the caret
  is currently sitting on — without it, a second Shift+Tab
  press would resolve back to the same placeholder.
- **Extended `onKeyDown`** in `NoteWorkspace.tsx`:
  - `Tab` (no modifier) — walk to the next `___` at/after
    `selectionEnd` (phase-31 baseline).
  - `Shift+Tab` — walk to the previous `___` strictly before
    `selectionStart`.
  - Both fall through to the browser default when there's
    nothing left to walk to, preserving focus-cycle semantics.
  - Ctrl/Meta/Alt are still left alone.
- **Phase-29/30/31 caret-to-first-blank preserved** — inserting
  a shortcut still selects the first `___`; Tab walks forward,
  Shift+Tab walks back.

## 2. Per-user shortcut usage breakdown

- **New query flag** `by_user=true` on
  `GET /admin/shortcut-usage-summary`. Same admin-only
  protection, same org-scope, same window validation.
- **When set**, aggregation groups by `(actor_email, shortcut_ref)`
  instead of just `shortcut_ref`. Response gains a
  `distinct_users` counter, and each row carries
  `user_email` plus the usual `shortcut_ref / count / last_used_at`.
- **Shared aggregator** — extracted as
  `_build_shortcut_usage_summary` inside `routes.py` so the JSON
  handler, the CSV handler, and any future tooling hit the same
  query + parse + ranking + trimming path.
- **Deterministic ordering** — `(-count, user_email, shortcut_ref)`
  so the ranking is stable under repeat calls even with ties.

### Response shape when `by_user=true`
```json
{
  "window_days": 30,
  "organization_id": 1,
  "generated_at": "2026-04-19T…",
  "by_user": true,
  "total_events": 4,
  "distinct_refs": 2,
  "distinct_users": 2,
  "items": [
    {"user_email": "clin@chartnav.local", "shortcut_ref": "glc-01", "count": 2, "last_used_at": "…"},
    {"user_email": "clin@chartnav.local", "shortcut_ref": "cor-03", "count": 1, "last_used_at": "…"},
    {"user_email": "admin@chartnav.local", "shortcut_ref": "glc-01", "count": 1, "last_used_at": "…"}
  ]
}
```

### PHI invariant is enforced, not aspirational
A backend test creates a usage event with `note_version_id=77`
and asserts:
- every row's keys are exactly the expected set (no
  `note_version_id` / `encounter_id` bleeding in)
- the row-serialized text does not contain `note_version_id`,
  `encounter_id`, or the literal id `77`

(The envelope-level `generated_at` timestamp is
intentionally excluded from the PHI scan — it can coincidentally
carry repeating digits in its microsecond suffix and caused
a flake in the full-suite run; tightened the assertion to the
`items` list only.)

## 3. CSV export

- **New endpoint**
  `GET /admin/shortcut-usage-summary/export?days=&limit=&by_user=`.
  Admin-only; same gating + window validation as the JSON
  endpoint; reuses the shared aggregator.
- **Columns change with `by_user`:**
  - aggregate: `shortcut_ref,count,last_used_at`
  - by_user: `user_email,shortcut_ref,count,last_used_at`
- **Filename** — `chartnav-shortcut-usage-YYYYMMDDTHHMMSSZ[-by-user].csv`,
  same timestamp pattern as the phase-14 audit-export CSV.
- **Transport** — `text/csv; charset=utf-8` +
  `Content-Disposition: attachment`. Returns a `Response`
  rather than streaming, since the summary is already capped by
  `limit ≤ 200` rows.

## 4. Oculoplastics / lids / adnexa pack

Six conservative, specialist-grade shorthand phrases. Picked
because adnexal findings (chalazion, ectropion/entropion,
ptosis, dermatochalasis, lagophthalmos) show up in almost every
general ophthalmology visit, not just the oculoplastic subset.
All ids carry fill-in blanks (`___`) so the phase-30/31/32
caret + Tab chain feels natural.

| ID | Coverage |
|---|---|
| `ocp-01` | Involutional ectropion OD + exposure keratopathy → lubrication + lateral tarsal strip |
| `ocp-02` | Involutional entropion OS + trichiasis + corneal epithelial staining → epilation + lower lid retractor repair |
| `ocp-03` | Dermatochalasis OU with superior VF obstruction → functional upper blepharoplasty + pre-op VF |
| `ocp-04` | Aponeurotic ptosis OD with MRD1 ___ mm, levator function ___ mm → external levator advancement |
| `ocp-05` | Chalazion OD lower lid, stable ___ mm → warm compresses + lid hygiene, I&D if non-resolving |
| `ocp-06` | Lagophthalmos OD + exposure keratopathy → nocturnal lubricating ointment + gold weight / tarsorrhaphy |

### Abbreviation additions
Only three new entries; tightly bound to the live shorthand and
not a sheet-dump: `I&D`, `MRD1`, `MRD2`. (Pre-existing `VF` is
already in the phase-31 glaucoma reference, so no duplicate.)

## 5. Matcher bug fix uncovered by the oculoplastics pack

Adding `MRD1` surfaced a pre-existing bug in
`clinicalShortcutMatches`: the token scan used a naïve
`query.includes(lowerAbbr)` check, which fired on
`"mrd1".includes("rd")` and mis-surfaced every `RD`-tagged
retinal-detachment shortcut when a clinician searched for
`MRD1`.

### Fix
Tokenize the search query on whitespace + common punctuation,
then require either:
- an exact abbreviation-token match among the query tokens, OR
- a single-token query that is a **prefix** of the abbreviation
  (so typing `mrd` still surfaces `MRD1`, but typing `mrd1`
  never resolves back to `RD`).

Unit-tested by the phase-32 `'MRD1' surfaces the oculoplastics
pack` frontend assertion, which now also confirms the PVD group
is absent from the filtered view. The phase-29/30/31 search
regressions remain green (`DME`, `CRVO`, `FTMH`, `POAG`, `CXL`,
`ectropion`).

## Data + trust invariants preserved

- Shortcuts, favorites, usage events, and usage summaries
  remain orthogonal to `encounter_inputs`, `extracted_findings`,
  `note_versions`, and transmitted artifacts.
- Reviewer role is invisible across the entire surface —
  catalog, favorites, usage audit, JSON summary, CSV export,
  and the new Oculoplastics group.
- The CSV export cannot carry more PHI than the JSON summary;
  both reuse the same aggregator and the same row shape.

## Test coverage

- **Backend** (+8 in `tests/test_shortcut_usage_summary.py`,
  16 total):
  - `by_user=true` groups by `(email, ref)` with correct counts +
    `distinct_users`
  - `by_user` stays org-scoped
  - `by_user` 403s non-admins
  - `by_user` response keys invariant
  - CSV aggregate: headers + ranked rows + filename suffix
  - CSV by-user: headers + ranked rows + filename suffix
  - CSV 403 for non-admins
  - CSV respects org + window validation
- **Frontend** (+7 in `NoteWorkspace.test.tsx`):
  - Shift+Tab walks backward through two blanks
  - Shift+Tab fallback when no previous blank remains (default
    browser behaviour runs)
  - Shift+Tab sitting on a blank hops to the **previous** one,
    not the same one
  - Oculoplastics group renders with verbatim phrasing spot
    checks (`ocp-01`, `ocp-04`, `ocp-06`)
  - `MRD1` search surfaces Oculoplastics and drops PVD (the
    pre-existing token-bleed bug regression check)
  - `ectropion` search surfaces `ocp-01` and drops glaucoma
  - Reviewer view hides the Oculoplastics group entirely
- Full suites: backend **309 passed** (301 + 8); frontend
  **114 passed** (108 + 6 originally authored + 1 phase-31 test
  reclassified for the new Shift+Tab behaviour).
- Typecheck clean. Vite build 252.84 kB JS / 21.26 kB CSS
  (gzip 74.51 / 4.41 kB).

## Files touched

- `apps/api/app/api/routes.py` — `_build_shortcut_usage_summary`
  extraction, `by_user` flag, `/export` handler
- `apps/api/tests/test_shortcut_usage_summary.py` — +8 tests,
  2 flake-hardening tweaks
- `apps/web/src/clinicalShortcuts.ts` — `prevBlankBefore`
  helper, tokenized matcher, 6 oculoplastic shortcuts, 3
  abbreviation hints
- `apps/web/src/NoteWorkspace.tsx` — Shift+Tab branch in
  `onKeyDown`
- `apps/web/src/test/NoteWorkspace.test.tsx` — +7 tests,
  phase-31 Shift+Tab test reclassified
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `43-shortcut-navigation-and-oculoplastics.md` (new)

## Follow-on work

1. **Tab-wraparound.** Today `Tab` past the last blank leaves
   the textarea and `Shift+Tab` before the first one does
   similar. Wraparound could be a `?wrap=true` mode on the
   handler; deferred because the current behaviour matches
   what textareas normally do.
2. **Scheduled CSV export.** Ops may want a weekly emailed CSV.
   Trivial to bolt onto the existing cron harness once
   requested.
3. **Peds / uveitis / strabismus packs** — next subspecialty
   wave when reviewers have signed off on phrasing. Same
   infra, no code changes needed beyond catalog entries +
   abbreviation additions.
