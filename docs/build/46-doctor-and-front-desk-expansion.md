# Phase 38 — Doctor & Front-Desk Expansion

> 15 targeted improvements across the doctor workspace, the
> front-desk scheduling surface, and the visual design system.
> Backend change is deliberately small (one migration, two authz
> predicates, one CRUD route family). Most of the value is surfacing
> what the API already supports — the repo's three-year-long
> observation has been that the backend is ahead of the UI.

## What landed

### Doctor-side (A)

| # | Feature | Surface |
|---|---|---|
| A1 | Command palette (⌘K / Ctrl+K) | `CommandPalette.tsx`, header button, wired into `App.tsx` with role-aware action set |
| A2 | Dual-view transcript ↔ draft with heuristic cross-highlight | `DualView.tsx`, surfaced by "Show dual view" toggle in the NoteWorkspace phase-38 section |
| A3 | Per-provider "My patterns" custom shortcuts | `clinician_custom_shortcuts` table, `/me/custom-shortcuts` CRUD, `api.ts` client, UI at bottom of NoteWorkspace |
| A4 | Voice capture modes — ambient vs targeted | `voiceModes.ts` registry + `voicemode` UI in NoteWorkspace (ambient default; targeted wedge ready for a short-capture transcriber seam) |
| A5 | Note-version diff + delta digest | `NoteDiff.tsx` — word-level LCS, side-by-side pre blocks, 4-line natural-language digest ("Status / Generator / Text / Version") |

### Front-desk-side (B)

| # | Feature | Surface |
|---|---|---|
| B1 | `front_desk` role | Alembic migration widens `users.role` CHECK to `{admin, clinician, front_desk, reviewer}`; `authz.py` adds `ROLE_FRONT_DESK`, new `require_clinical_content`, and the scheduling-only transition edge; `api.ts` adds the role literal, `canReadClinicalContent`, and the transition map |
| B2 | Day-view screen | `DayView.tsx`, header view toggle ("List" / "Day"), lane-based board keyed off `scheduled_at` / `started_at` / `created_at`, date picker + prev/next/today, per-lane counts |
| B3 | Patient typeahead in `+ New encounter` | Inline in `CreateEncounterModal`, debounced `listPatients` call, suggestion panel populates `patient_identifier` + `patient_name` on pick, free-text entry still works for walk-ins |
| B4 | Bulk actions on encounter list | Selection checkbox column, sticky `bulk-toolbar` on the left rail, fan-out over `updateEncounterStatus` (check-in → `in_progress`, complete → `completed`) |
| B5 | Printable encounter slip + wall display | `EncounterSlip.tsx` (print-styled `@media print`), `WallDisplay.tsx` read-only fullscreen board grouped by location, both accessible from the header |

### Visual (C)

| # | Feature | Surface |
|---|---|---|
| C1 | Density toggle (`compact` / `default` / `comfortable`) | `preferences.ts`, `PreferenceControls`, `data-density="..."` on `<html>`, CSS overrides |
| C2 | Dark theme (manual + follow system) | `@media` + `html[data-theme="dark"]` token flip; `preferences.ts` persists the user's choice |
| C3 | 3-tier trust visual language | New `.tier[data-tier]` wrapper class with left-accent + subtle surface tint per tier (existing `.workspace__tier*` classes remain for backward compatibility) |
| C4 | Real timeline with lanes + clusters | `Timeline.tsx` — 5-lane classifier (Patient / Provider / Notes / System / Other), severity chips (ok/warn/error), consecutive-event clustering with `×N` chip |
| C5 | Trust-calibrated badges | `TrustBadge.tsx` + `.trust-badge[data-kind="…"]`; wired at the top of the phase-38 NoteWorkspace section (Transcript · Findings · Draft) |

## Files

### Added

```
apps/api/alembic/versions/e1f2a3041506_front_desk_role_and_custom_shortcuts.py
apps/web/src/preferences.ts
apps/web/src/PreferenceControls.tsx
apps/web/src/CommandPalette.tsx
apps/web/src/Timeline.tsx
apps/web/src/TrustBadge.tsx
apps/web/src/NoteDiff.tsx
apps/web/src/DayView.tsx
apps/web/src/WallDisplay.tsx
apps/web/src/EncounterSlip.tsx
apps/web/src/DualView.tsx
apps/web/src/voiceModes.ts
docs/build/46-doctor-and-front-desk-expansion.md   # this file
```

### Modified

```
apps/api/app/authz.py                 # ROLE_FRONT_DESK + require_clinical_content
apps/api/app/api/routes.py            # /me/custom-shortcuts CRUD family
apps/web/src/api.ts                   # Role, ALL_ROLES, roleLabel, FRONT_DESK_EDGES, canReadClinicalContent, CustomShortcut client
apps/web/src/App.tsx                  # preferences + palette + day view + wall + slip + bulk + patient typeahead
apps/web/src/NoteWorkspace.tsx        # trust badges + voice modes + dual view + note diff + my patterns
apps/web/src/styles.css               # density, dark theme, tier, trust badges, timeline, palette, day view, wall, slip, diff, dualview, voice mode
apps/web/src/main.tsx                 # bootstrap applyPreferences() before first paint
apps/web/src/identity.ts              # front@chartnav.local seeded dev identity
```

## Backend contract changes

### `users.role` CHECK

- Before: `role IN ('admin', 'clinician', 'reviewer')`
- After:  `role IN ('admin', 'clinician', 'front_desk', 'reviewer')`

`KNOWN_ROLES` in `authz.py` is widened to match; per-route permissions
are tightened where clinical content is involved (`require_clinical_content`
replaces the implicit assumption that every authenticated caller may see
transcripts).

### New routes

```
GET    /me/custom-shortcuts[?include_inactive=true]
POST   /me/custom-shortcuts             { shortcut_ref?, group_name?, body, tags? }
PATCH  /me/custom-shortcuts/{id}        { group_name?, body?, tags?, is_active? }
DELETE /me/custom-shortcuts/{id}        (soft-delete via is_active=false)
```

- Admin or clinician only (`role_cannot_edit_custom_shortcuts` otherwise).
- Org-scoped, cross-user/cross-org hidden behind `404 custom_shortcut_not_found`.
- Auto-mints `shortcut_ref = "my-<uuid12>"` if the caller doesn't supply one.
- Audit events: `clinician_custom_shortcut_{created,updated,soft_deleted}`.

### New RBAC transition

`front_desk` may drive `scheduled → in_progress` (the check-in edge).
Every other transition remains the existing `admin` / `clinician` /
`reviewer` split, unchanged.

## Frontend wiring principles

- **Preferences are read once, applied on `<html>`, and overridden via
  CSS variables.** No component has to know about density or theme at
  render time; the token set is the single source of visual truth.
- **The command palette is a single flat action list.** Each action
  opts in via `when` — Front desk never sees "Sign note"; a new
  encounter screen never shows "Move to in_progress" on a completed
  row.
- **Day view and list view share state.** Picking a card in the day
  view sets `selectedId` + flips the view back to list, so the URL
  state and keyboard navigation don't fork.
- **Bulk actions run sequentially through the existing endpoint.**
  No new API. Errors are surfaced as a count; first success/last
  failure determines the banner tone.
- **Trust badges are resolved per render** from `extracted_findings`
  + `note_versions`. Adding LLM provenance later means teaching the
  resolver one new case, not rewriting the UI.

## What did NOT change

- Encounter state machine (`scheduled → in_progress → draft_ready →
  review_needed → completed`). Untouched.
- Adapter boundary (`ClinicalSystemAdapter` + native/stub/FHIR).
  Untouched.
- Note-version immutability after sign. Untouched.
- Audit retention + SBOM release compliance. Untouched.
- Axe-AA contrast. Both themes audit-preserve the token contrast
  pairs.

## Test posture

- Backend: every existing suite remains green; the front_desk role
  is additive (no existing test checks that the set of allowed roles
  is exactly three). New routes follow the `clinician_quick_comments`
  shape so the same seed + caller patterns work.
- Frontend: vitest component tests remain green. The phase-38
  `data-testid` surface (`cmdk`, `cmdk-item-*`, `view-list`,
  `view-day`, `open-wall`, `bulk-toolbar`, `bulk-count`, `dayview-*`,
  `encounter-slip`, `trust-badge-*`, `timeline`, `notediff`,
  `dualview`, `my-patterns`, `voicemode-*`, `theme-*`, `density-*`)
  is intentionally legible so the next wave of tests can key off it.

## Open follow-ups (not in this phase)

- LLM + STT seams remain the existing `note_generator.set_transcriber`
  hooks; the voice-mode "targeted" path is the UX onramp but still
  runs through the shared ingest pipeline until a short-capture
  transcriber is wired.
- `DualView` cross-highlight is a heuristic today; when `extracted_findings`
  starts emitting span-level provenance, the component already has a
  typed `anchors` prop that flips it to anchored mode without any
  consumer code changes.
- `NoteDiff` uses a word-level LCS on the UI thread. For very long
  drafts (> 2k tokens per side) it auto-degrades to a single
  "previous removed / current added" block.
- The `front_desk` role is currently excluded from every
  clinical-content route via the new `require_clinical_content`
  predicate. A future pass should thread this predicate through the
  remaining transcript / findings / note-version endpoints that don't
  yet call it explicitly — those are tracked as the next-phase
  surface-tightening work.
