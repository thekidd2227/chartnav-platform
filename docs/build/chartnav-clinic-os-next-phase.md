# ChartNav Clinic-OS Next Phase — Build Notes

> Frontend-only build slice that advances ChartNav from "ophthalmology
> workflow tool" toward "ophthalmology workflow infrastructure with
> AI documentation, specialty shortcuts, explicit workflow states,
> rules-based quality controls, and a measurable proof + rollout
> surface." Five real surfaces shipped; no backend changes.

## Why this phase

The competitive thesis: ChartNav wins by being the **clinic operating
system** ophthalmology practices already need (lane handoffs,
role-based dashboards, retina / glaucoma tracking, imaging metadata
review, provider-reviewed documentation, internal coordination),
with AI scribe drafting as **one surface** inside that OS — not the
whole product.

The audit (see §"Audit findings" below) showed the live repo already
has the bones for this. The gap was operator-visible:

- shortcuts existed but had no **multi-shortcut composable template**
  for a full visit type;
- workflow states existed across encounter + scribe-session lifecycles
  but had no **single explicit 6-lane visualisation** mapping the
  operator-facing names buyers use;
- no **rules-based quality linter** surface existed for the draft;
- no **proof + rollout** surface combined live KPIs with rollout
  readiness per location.

This phase adds those five surfaces.

## What shipped

### 1. `apps/web/src/specialtyTemplates.ts` — composable note skeletons

10 specialty templates (retina, glaucoma, cornea, cataract,
oculoplastics — across follow-up / new-patient / post-op / monitoring
visit types) that compose existing `CLINICAL_SHORTCUTS` by stable
id. Pure module. Adds:

- `SPECIALTY_TEMPLATES` library (10 entries, every shortcut id
  asserted-to-exist by `specialtyTemplates.test.ts`).
- `resolveSpecialtyTemplate()` — pure resolver that surfaces missing
  ids inline instead of dropping a section.
- `renderSpecialtyTemplate()` — deterministic plain-text block,
  preserves `___` blanks for the existing
  `firstBlankOffset` / `nextBlankAfter` Tab-walk helpers in
  `NoteWorkspace.tsx`.
- `filterSpecialtyTemplates()` — picker filter (specialty +
  visitType + role).
- `specialtyTemplateShortcutGroups()` — UI hint surface.

Role-aware: every template carries `role: "clinician"`. Front-desk /
technician / reviewer do not see clinical templates today.

### 2. `apps/web/src/EncounterWorkflowStatusBar.tsx` — 6 explicit lanes

A compact derivation-only bar that maps the live encounter status
(5 values) + optional scribe-session status (6 values) into 6
operator-facing lanes:

1. Intake pending
2. Transcript queued
3. Transcript ready
4. Physician review in progress
5. Note approved
6. Export / billing ready

Each lane carries one of four states (`done | active | blocked |
pending`). The bar **never advances state automatically**; provider
review stays explicit. The "export / billing ready" lane is held at
`blocked` when the caller's quality flags include any `block`-severity
entry — that's the integration point with the new quality linter.

Pure `deriveLaneStates()` is exported separately and tested
exhaustively (14 cases) so the mapping table is the operator-facing
source of truth.

### 3. `apps/web/src/noteQualityChecks.ts` — rules-based quality linter

Pure-function quality linter. Returns flags + completeness percent.
Five rule classes:

- **Laterality** — `block` when encounter laterality contradicts the
  draft (encounter is OD, draft says OS, no bilateral anchor).
  `info` when encounter laterality is set but the draft has no OD/
  OS/OU anchor at all.
- **Missing critical elements** — `warn` per missing required
  section (per-specialty `REQUIRED_SECTIONS` map covering retina /
  glaucoma / cornea / cataract / oculoplastics / general).
- **Completeness scoring** — percent of required sections that have
  a header **and** body content. `completeness_low` warn under 60%,
  `completeness_partial` info between 60–99%.
- **Banned-phrase guard** — `warn` per match against the public-
  website safe-claims contract (auto-grade DR, autonomous
  diagnosis, automatic orders, chart fills itself, etc.). The chart
  should never adopt a phrase the website forbids.
- **Rules-based contradiction guard** — `warn` when the draft
  asserts a probe phrase ("retinal detachment", "retinal tear",
  "vitreous hemorrhage", "macular hole", "neovascularization") that
  the upstream extracted-findings string negates, or vice versa.
  Intentionally conservative; not paraphrastic. Not AI.
- **Duplicate critical section** — `warn` when a required section
  header repeats.

`hasBlockingFlags` and `severityCounts()` are convenience views the
UI gates on. The linter does **not** auto-correct, **does not** edit
the draft, **does not** call an LLM, and **does not** block sign-off
on its own — it produces evidence the caller decides to act on.

### 4. `apps/web/src/NoteQualityFlagsPanel.tsx` — quality flags UI

Renders the linter output as a compact list, ordered block → warn →
info. Each flag shows a severity pill, a one-line message, and an
optional acknowledge button wired up by the caller. A
`block-hint` line appears under any draft with unresolved blocks,
reminding the operator that those must be acknowledged or resolved
before sign-off. The subtitle restates the safe-claims contract:
"Provider review remains the source of truth — ChartNav does not
auto-correct, auto-grade, or replace clinical judgement."

### 5. `apps/web/src/ProductionReadinessPanel.tsx` — proof + rollout

New admin-only top view combining:

- **Proof KPIs** (Phase 6 of the brief). Six metrics derived from
  the live admin dashboard:
  - Open queue items — `live`
  - Overdue items — `live` (or `warn` if non-zero)
  - Unsigned notes — `live`
  - Non-overdue share — `live` (proxy for same-day-signed until a
    real `signed_within_24h` metric ships)
  - Edit burden after AI draft — **`pending`** with explanation
  - Denied-claim correlation — **`pending`** with explanation
  Pending KPIs render with a `pending` status attribute and an
  explanation of what data seam is missing. **No fabricated
  numbers.**

- **Rollout readiness by location** — per-location table:
  - Role coverage counts for the 5 required roles (admin /
    clinician / reviewer / front_desk / technician)
  - Specialty template count
  - Fake-data demo wedge presence
  - Derived overall readiness (`ready` / `gaps`)
  Unassigned / org-scoped users render in an explicit
  `Unassigned / org-scoped` row so the operator sees the data
  honestly. Today every seeded user is org-scoped (no `location_id`
  field on the User shape), so locations show zero coverage and the
  unassigned bucket holds the actual role mix — the panel is
  transparent about that.

- **Specialty template coverage** — one card per specialty showing
  how many templates are available to clinicians today.

Admin-only. Non-admin identities see a blocked notice.

### Wiring

- `apps/web/src/App.tsx` — added `"production-readiness"` to the
  `TopView` union, mounted the new panel under that view, added a
  sidebar item (`sidebar-item-production-readiness`) under the
  Admin group right after `Security Readiness`. Admin-gated like
  the existing Security Readiness entry.
- `apps/web/src/styles.css` — minimal teal-themed styles for the
  three new components.

## What did **not** ship (intentional)

- No new backend endpoints, no new database tables, no new
  migrations. The brief explicitly authorized "implement the
  strongest real next-phase slice the live repo supports" — the
  current backend has no `signed_within_24h` aggregate, no
  per-event diff size on scribe-session edits, no claim-denial
  feed. Those become real seams when the data exists; until then
  the panel marks them as pending.
- No automatic state advancement. Provider review remains explicit.
- No AI-generated content. The quality linter is rules-based.
- No public-website changes. The Spanish-localization branch is
  separate.
- No changes to existing tests. The 535 tests on `main` were a
  regression target — they all still pass.

## Audit findings

| Area | Live state at start of phase |
|---|---|
| Clinical shortcuts | `clinicalShortcuts.ts` ships 10 specialty groups, abbreviation-aware lookup, `<abbr>` segmentation, `___` blank traversal helpers, Phase 30 per-doctor favorites. **Strong foundation, no multi-shortcut composition.** |
| Encounter state | 5-state machine (`scheduled → in_progress → draft_ready → review_needed → completed`), role-gated edges. |
| Scribe session | 6-state machine (`draft → processing → ready_for_review → reviewed → finalized → discarded`), finalize endpoint. |
| Dashboards | Phase 20C `RoleDashboard` (5 roles), Phase 22 `MultiClinicDashboard`, Phase 23 `SecurityReadinessPanel`. **No proof / rollout layer.** |
| Quality controls | None. No laterality / completeness / contradiction surface anywhere in the workspace. |
| Admin panel | Phase 13 admin panel covers users / locations / org / audit / invitations. **No rollout-readiness pane.** |

## Verification

- `cd apps/web && npx tsc --noEmit` — clean.
- `cd apps/web && npx vitest run` — **598/598 across 31 test files**
  (was 535/535 across 26; +63 new tests, 0 regressions).
- `cd apps/web && npm run build` — succeeds (453 KB / 120 KB
  gzipped).
- `bash scripts/check_commercial_claims.sh` — 0 fail / 0 warn.
- `bash scripts/check_demo_claims.sh` — 0 hits across 15 files.

## Recommended next phase

A backend-side seam that lights up the two `pending` proof KPIs
honestly:

1. **Edit-burden seam.** `scribe_session_events` table (or extension
   of the existing scribe-session table) capturing per-update diff
   size + timestamp so the panel can compute median edits between
   AI draft and finalize per provider per week.
2. **Same-day-signed seam.** A derived rollup on the admin
   dashboard that counts `scribe_session.finalized_at -
   scribe_session.created_at < 24h` per provider per week.

Both are additive: existing tables + one additive migration. Neither
requires AI, external services, or new product modules.
