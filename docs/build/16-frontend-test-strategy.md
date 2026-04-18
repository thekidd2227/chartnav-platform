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

## Operator control-plane tests (phase 13)

- `AdminPanel.test.tsx` — 4 new tests: Organization tab loads + PATCH dispatch, local JSON parse error path, Audit tab row render + filter dispatch, Audit 403 surfaces as error banner.
- Playwright — 1 new scenario: admin opens Organization tab → edits name → saves → opens Audit tab → audit table + filter UI render.

## Admin governance tests (phase 12)

- `src/test/AdminPanel.test.tsx` — 5 Vitest tests: user list, create user success + 409 error, self-row disabled, location create on the Locations tab.
- `src/test/App.test.tsx` — added 1 test asserting the Admin button is visible to admins only.
- E2E `workflow.spec.ts` — 2 new scenarios: admin creates a user + a location end-to-end; clinician never sees the Admin button.

## Gaps not yet covered
- No visual regression / accessibility audits.
- The create modal doesn't exercise location-list errors yet.
- Loading skeletons / spinner content not asserted.
