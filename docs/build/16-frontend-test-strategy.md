# Frontend Test Strategy

## Stack

- **Vitest** (`vitest` + `@vitest/ui`) — same Vite runtime as the app.
- **jsdom** — DOM environment.
- **@testing-library/react** + **@testing-library/user-event** — user-centric queries, realistic events.
- **@testing-library/jest-dom** — richer DOM matchers.

## Layout

```
apps/web/
├── vite.config.ts            # vitest config block (jsdom, globals, setup file)
├── src/test/
│   ├── setup.ts              # imports jest-dom matchers, cleans DOM + localStorage between tests
│   └── App.test.tsx          # 12 integration tests against the mocked API layer
└── package.json              # scripts.test = vitest run, test:watch = vitest
```

## Mocking strategy

`vi.mock("../api", ...)` replaces every backend call with a `vi.fn()`
while preserving the pure helpers (`allowedNextStatuses`, `ApiError`,
etc.). That keeps tests decoupled from the network, deterministic, and
fast — but still exercises the real `App.tsx` component tree.

The mocks emulate the server's real error envelope so the UI code's
`{error_code, reason}` branch is actually tested.

## Coverage (12 tests)

| Scenario                                                            | Check |
|---------------------------------------------------------------------|-------|
| `/me` resolves → identity badge shows email/role/org                | ✅    |
| Mocked list renders both seeded encounters                          | ✅    |
| Changing `status` filter calls `listEncounters` with filter arg, list updates | ✅ |
| Selecting an encounter loads detail + timeline; status shown        | ✅    |
| Clinician sees only operational transition buttons (`draft_ready`)  | ✅    |
| Reviewer sees review-stage transitions (`completed`, `draft_ready`) | ✅    |
| Reviewer sees no event composer, replaced by `event-denied` note    | ✅    |
| Reviewer cannot see the `+ New encounter` button                    | ✅    |
| Admin: open create modal, submit, success banner, modal closes      | ✅    |
| Create failure: backend 403 `cross_org_access_forbidden` surfaces in modal error, modal stays open | ✅ |
| Switching identity refetches `/me` and the list (org1 → org2)       | ✅    |
| Unknown-user identity: custom email path surfaces the 401 chip      | ✅    |
| Status transition call path refreshes detail + events, success banner | ✅  |

## Run

```bash
# one-shot (CI + local gate)
cd apps/web && npm test

# watch mode
cd apps/web && npm run test:watch

# combined frontend gate
make web-verify      # typecheck + test + build
```

Result at time of writing: **12 passed in ~2.5s**.

## Philosophy

- The UI is tested the way a user drives it — click, select, type — not
  via internal implementation details.
- We assert the UI **reflects the server's authority**: when the backend
  returns a 4xx envelope, the UI must show the `error_code` and
  `reason` verbatim, not invent its own copy.
- Role-aware affordances are tested by identity switching in the
  picker, not by poking at internal state.

## End-to-end tests (Playwright)

Full browser coverage ships in phase 9 — see `17-e2e-and-release.md`.
Playwright boots real backend + frontend, runs 8 scenarios in Chromium,
and tears both servers down cleanly. Command: `make e2e`.

Vitest and Playwright are fully isolated: Vitest's `test.include` is
narrowed to `src/**/*.test.{ts,tsx}` and excludes `tests/**`, so the
two suites never cross-contaminate.

## Invitations + bulk + export tests (phase 14)

- `AdminPanel.test.tsx`:
  - Invite button on a user row issues a token and surfaces it in `admin-invite-token`.
  - Bulk import summary renders created/skipped/errors counts.
  - Audit Export CSV button wires `downloadAuditExport` with current filters.
- Playwright: 1 new end-to-end scenario — admin creates a user, clicks **Invite**, token banner visible; Audit tab → **Export CSV** triggers a real browser download with the expected filename pattern.
- Backend's 20 `test_invitations.py` tests are the source of truth for server behavior; the UI tests verify wiring and user-visible states.

## Operator control-plane tests (phase 13)

- `AdminPanel.test.tsx` — 4 new tests: Organization tab loads + PATCH dispatch, local JSON parse error path, Audit tab row render + filter dispatch, Audit 403 surfaces as error banner.
- Playwright — 1 new scenario: admin opens Organization tab → edits name → saves → opens Audit tab → audit table + filter UI render.

## Admin governance tests (phase 12)

- `src/test/AdminPanel.test.tsx` — 5 Vitest tests: user list, create user success + 409 error, self-row disabled, location create on the Locations tab.
- `src/test/App.test.tsx` — added 1 test asserting the Admin button is visible to admins only.
- E2E `workflow.spec.ts` — 2 new scenarios: admin creates a user + a location end-to-end; clinician never sees the Admin button.

## Enterprise quality tests (phase 15)

- `AdminPanel.test.tsx` extends to **12 tests** (+3). New mocks:
  `listUsersPage`, `listLocationsPage`, `getOrganization`, `inviteUser`,
  `bulkCreateUsers`, `downloadAuditExport` — all required because
  AdminPanel now holds feature-flag-aware org state and calls the
  paginated list endpoints.
  - `audit_export=false` → `admin-audit-export` absent, `admin-audit-refresh` still present.
  - `bulk_import=false` → `admin-user-bulk-open` absent.
  - Users-tab search input dispatches `listUsersPage({ q })`.
- Playwright grows to **21 tests**:
  - `workflow.spec.ts` — 12 (unchanged).
  - `a11y.spec.ts` — **5 axe-core scans** across app shell, encounter
    list, encounter detail, admin Users tab, admin Audit tab, invite
    accept. `serious`/`critical` findings are blocking. Fixes landed
    with the baseline: `aria-label="Event type"` on the composer
    `<select>`; `aria-label="Role for <email>"` on each inline role
    `<select>`.
  - `visual.spec.ts` — **4 Playwright screenshots** (encounter list,
    admin Users, admin Audit, invite accept). Viewport 1280×820,
    animations disabled via injected stylesheet,
    `maxDiffPixelRatio: 0.02`. Baselines are OS-specific and shipped
    for macOS only (`*-chromium-darwin.png`). **Local-only** gate:
    `make e2e-visual` / `make e2e-visual-update`. CI skips visual
    because Linux Chromium renders slightly differently.
- Rate limiter: Playwright's backend webServer sets
  `CHARTNAV_RATE_LIMIT_PER_MINUTE=0` — the full suite (workflow +
  a11y + visual) runs many requests from 127.0.0.1 and would
  otherwise hit the 120/min limit. Safe because the E2E DB is
  always ephemeral.

## Platform mode tests (phase 16)

- `AdminPanel.test.tsx` extends to **17 tests** (+2).
- New mocks: `getPlatform`. The default `beforeEach` seeds a
  standalone-native platform response; individual tests override
  to integrated-readthrough.
- Assertions:
  - `admin-platform-banner` renders on every admin view.
  - `admin-platform-mode` content changes with
    `platform_mode` — standalone vs integrated_readthrough.
  - `admin-platform-adapter` content matches the adapter's
    `display_name`.

## Native clinical layer tests (phase 18)

- `AdminPanel.test.tsx` now covers **20 tests** (+3).
  - Standalone Patients tab → renders table, renders create form,
    `createPatient` is called with the submitted fields.
  - Integrated read-through mode → read-through banner visible and
    the create form is absent.
  - Providers tab → create form submits through `createProvider`
    with the NPI carried through.
- Mocks extended: `listPatients`, `createPatient`, `listProviders`,
  `createProvider`.

## NoteWorkspace tests (phase 19)

- **+8 tests** in `src/test/NoteWorkspace.test.tsx`.
- Covers: three-tier render (transcript/findings/draft), findings
  block + confidence indicator + `data-confidence` attribute,
  missing-data flags banner, provider edit flips generated-by
  label to `provider (edited)`, submit-for-review + sign chain,
  reviewer role hides Sign button + renders `note-sign-disabled-note`,
  export switches draft to read-only, paste-to-generate happy path.
- Mocks extend the test harness with the full phase-19 api surface
  (`listEncounterInputs`, `generateNoteVersion`, `patchNoteVersion`,
  `signNoteVersion`, `exportNoteVersion`, etc.).
- `App.test.tsx` extends mocks so the workspace mounting inside
  `EncounterDetail` doesn't fetch-miss during App-level tests.

## Encounter source-of-truth tests (phase 20)

- **+2** in `src/test/App.test.tsx`:
  - Native encounter detail renders `ChartNav (native)` chip, no
    external banner, transitions visible.
  - Externally-sourced encounter (`_source: "fhir"`) hides
    transitions, hides `NoteWorkspace`, shows the SoT banner,
    renders the `External (FHIR)` chip, surfaces the native-only
    note-drafting subtle-note.
- `api.ts` helpers `encounterIsNative` / `encounterSourceLabel`
  exercised indirectly; add direct unit tests when more code
  consumes them.

## Encounter bridge tests (phase 21)

- **+1** in `src/test/App.test.tsx` — bridge button on an external
  encounter detail dispatches `bridgeEncounter` with the vendor ref
  + adapter source + mirror fields; location-navigate is stubbed
  so the test doesn't actually reload.
- External-note assertion updated from "ChartNav-native" to
  matching `/bridg/i` since the copy now explains the bridge path
  instead of a blanket native-only limitation.

## Ingestion lifecycle tests (phase 22)

- **+4** in `src/test/NoteWorkspace.test.tsx`:
  - `failed` input renders the `banner--error` with
    `last_error_code` + `last_error`; Retry button is present and
    dispatches `retry` then `process`.
  - `retry_count > 0` renders the `retries N` trailing chip.
  - `queued` input renders the Process-now button and Generate is
    disabled until a `completed` input exists.
  - Generate is enabled when a `completed` input is present.

## Signed-note transmission (phase 26)

- **+3** in `src/test/NoteWorkspace.test.tsx`:
  - `getPlatform` returns `document_transmit=false` → no Transmit
    button, no transmission-history pane.
  - `getPlatform` returns `document_transmit=true` → Transmit button
    renders with label "Transmit to EHR"; flips to "Re-transmit"
    after a prior success.
  - Click Transmit → `transmitNoteVersion(email, id, {force: false})`
    dispatched, then `listNoteTransmissions` re-fetched and the new
    row renders in `note-transmissions` with its status chip,
    HTTP code, remote id, and error code (if any).
- New mocks in the NoteWorkspace test harness: `getPlatform`,
  `transmitNoteVersion`, `listNoteTransmissions`. Default mock
  returns a standalone / `document_transmit=false` shape so the
  Transmit surface stays hidden in every pre-phase-26 scenario.
- Vitest suite total: **64 tests** (NoteWorkspace 25, App 19,
  AdminPanel 20), full run ~9s.

## Signed-note artifact export (phase 25)

- **+3** in `src/test/NoteWorkspace.test.tsx`:
  - signed note renders the artifact actions row (`note-artifact-actions`)
    with three buttons — `note-artifact-json`, `note-artifact-text`,
    `note-artifact-fhir` — and the expected labels.
  - unsigned notes hide the artifact actions row entirely.
  - click on `note-artifact-fhir` dispatches `downloadNoteArtifact`
    with `(email, id, "fhir")`.
- New mock: `downloadNoteArtifact: vi.fn()` in the NoteWorkspace test
  harness. Mocking at the `api.ts` seam means the test never touches
  jsdom's `Blob` / anchor download plumbing — the component's
  intent is what we're asserting.
- Vitest suite total grows to **61 tests** (NoteWorkspace 22, App 19,
  AdminPanel 20), full run 6.65s.
- Playwright not extended in this phase; artifact download plumbing
  needs a file-handler harness change. Sign-then-export scenarios
  continue to cover the surrounding UI path.

## Operator-UX hardening for async ingestion (phase 24)

- **+3** in `src/test/NoteWorkspace.test.tsx`:
  - empty-state blocked hint: "Generation unlocks once a transcript…"
  - queued/processing blocked hint: "Generation is waiting on
    transcript processing. Background work continues…"
  - failed/needs-review blocked hint: "The most recent input failed
    or needs review. Retry it…"
- Existing queue-banner tests updated for the tightened copy
  (differentiated "queued in the background" vs "processing in
  the background" variants).
- **New Playwright spec** `apps/web/tests/e2e/note-workspace-hardening.spec.ts`
  (3 scenarios): baseline blocked-hint on a fresh encounter,
  ingest→completed unlocks Generate, manual Refresh actually
  re-fetches the input list via an intercepted response.

## Background-processing UX tests (phase 23)

- **+4** in `src/test/NoteWorkspace.test.tsx`: queued-input renders
  the background banner with "waiting for a worker" copy;
  processing-claimed row renders "currently processing"; banner
  absent when all inputs are completed; manual refresh re-fetches
  the input list.
- **+2** in `src/test/App.test.tsx`: bridged-native encounter shows
  the refresh banner and dispatches `refreshBridgedEncounter`;
  reviewer sees the banner with a disabled-note and no button.

## Gaps not yet covered
- Visual regression not in CI (documented; OS-specific baselines).
- No keyboard-only / screen-reader manual QA pass beyond axe's
  automated ruleset.
- The create modal doesn't exercise location-list errors yet.
- Loading skeletons / spinner content not asserted.
