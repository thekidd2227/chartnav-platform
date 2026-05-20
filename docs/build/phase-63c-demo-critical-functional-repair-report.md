# Phase 63C — Demo-Critical Functional Repair Report

> **Buyer-demo decision: NO-GO until the operator runs the new
> functional smoke (`scripts/demo/phase63c_functional_smoke.sh`) on
> their iMac stack and it returns `BUYER-DEMO FUNCTIONAL GO: YES`.**
>
> The Phase 63B audit (on branch `feature/phase-63b-functional-
> demo-qa-audit`, not yet merged) identified 14 defects blocking
> the controlled fake-data buyer demo. Phase 63C fixes the three
> root causes that cascade into the rest:
>
> 1. Frontend feature API clients now use the configured `API_URL`
>    + `X-User-Email` (3 files).
> 2. `manual_note` payload is shaped client-side so the backend's
>    object requirement is met (1 helper + caller).
> 3. The Desktop bundle's `start-api.sh` now auto-runs
>    `alembic upgrade head` + idempotent seed before booting, so a
>    stale DB self-heals on next start.
>
> Plus a new functional smoke script (`scripts/demo/
> phase63c_functional_smoke.sh`) that replaces the Phase 63A
> media-presence gate with live HTTP verification of all three
> workflows.
>
> **No backend product code, no new migrations, no API contract
> changes, no claim policy changes, no public website changes, no
> deploy.** Everything Phase 63C touches is either a) the
> frontend's misrouting bug, b) the demo's boot ergonomics, or c)
> a new gate script + evidence doc.

## 1. Defects fixed mapped to QA-63B IDs

| QA ID | Severity | Root cause | Fixed by | Verification |
|---|---|---|---|---|
| QA-63B-001 | P0 | Local DB stale of Alembic head | bundle `start-api.sh` auto-runs `make migrate seed` before `make boot` (non-destructive; opt out via `CHARTNAV_DEMO_SKIP_MIGRATE=1`) | `bash scripts/check_alembic_safety.sh` (PASS); functional smoke § 1 |
| QA-63B-002 | P0 | `vitalsApi.ts` / `fundusApi.ts` / `ambientApi.ts` called relative paths against the Vite origin | All three rewritten to use `API_URL` + `X-User-Email` (read from explicit arg or `localStorage.chartnav.devIdentity`) | `Phase63cFeatureApiRouting.test.tsx` (8 cases); functional smoke § 3/4/5 |
| QA-63B-003 | P1 | Dashboard backend 500s from missing `work_queue_items` | Cascade resolves once QA-63B-001 lands. Dashboard component itself unchanged; the underlying graceful-empty UX is already coded for empty state. | Operator-side: open Dashboard after start-api auto-migrate — no red TypeError banner |
| QA-63B-004 | P1 | Multi-Clinic summary fails — same `work_queue_items` cascade | Cascade resolves with QA-63B-001 | Operator-side: open Multi-Clinic after start-api auto-migrate |
| QA-63B-005 | P1 | Frontend `onAddEvent` sent raw string for `manual_note` | New helper `apps/web/src/utils/shapeEventData.ts` wraps free-text as `{ note: "..." }`, passes through valid JSON objects, refuses empty manual_note client-side | `Phase63cShapeEventData.test.ts` (10 cases); functional smoke § 6; backend already covers rejection in `test_admin.py` and `test_invitations.py` |
| QA-63B-006 | P0 | Vitals workflow blocked by QA-63B-001 + QA-63B-002 | Cascades resolve with the two parent fixes | `Phase63cFeatureApiRouting.test.tsx`; existing `VitalsWorkupPanel.test.tsx` (13 cases) still passes; functional smoke § 3 |
| QA-63B-007 | P1 | Specialty tracking endpoints 500'd on stale tables | Cascade resolves with QA-63B-001 | Operator-side: open Clinical / Ophthalmology after start-api auto-migrate |
| QA-63B-008 | P1 | "Audio consent CORS preflight" was the browser symptom of a backend 500 (no CORS headers on 5xx). CORS middleware is correctly configured; the audit itself documents this in § 6 "Note: several CORS-looking browser errors are likely the browser-facing symptom of backend 500s without a CORS response header." | Cascade resolves with QA-63B-001 (the audio-consent route uses tables created by older migrations that the stale DB had, but the response error envelopes flow through the same middleware). The `apps/web/src/AudioConsentPanel.tsx` already uses the central `api.ts` helpers (`fetchAudioConsent` / `setAudioConsent`), so no frontend change. | Operator-side: open Documentation, save consent after start-api auto-migrate |
| QA-63B-009 | P0 | VisitDraft generation routed to Vite origin | Resolves with QA-63B-002 (ambientApi rewrite) | `Phase63cFeatureApiRouting.test.tsx`; existing `AmbientDocumentationPanel.test.tsx` (19 cases) still passes; functional smoke § 4 |
| QA-63B-010 | P1 | Shortcuts inert because the active draft was unreachable | Resolves transitively with QA-63B-009 (draft becomes reachable; existing shortcut logic targets the live draft) | Operator-side: open Documentation, generate a draft, click a shortcut — inserts into the draft |
| QA-63B-011 | P1 | Imaging pipeline failed on missing `imaging_studies` table | Cascade resolves with QA-63B-001 | Operator-side: open Imaging after start-api auto-migrate |
| QA-63B-012 | P0 | Fundus generate/review/sign blocked by QA-63B-001 + QA-63B-002 | Cascades resolve with the two parent fixes | `Phase63cFeatureApiRouting.test.tsx`; existing `FundusChartPanel.test.tsx` (23 cases) still passes; functional smoke § 5 |
| QA-63B-013 | P2 | Encounter list contaminated by manual Maria/QA records | Documented operator recovery: `bash scripts/reset_demo_state.sh` (existing, non-destructive guards in place) wipes the local DB and re-seeds. The auto-migrate added in QA-63B-001 is intentionally non-destructive (no `rm -f`), so existing Maria/QA rows survive a normal start — by design. | Operator-side: run `bash scripts/reset_demo_state.sh` once for a clean Morgan-only state |
| QA-63B-014 | P0 (readiness) | Phase 63A media GO was a file-presence gate, not a functional gate | New `scripts/demo/phase63c_functional_smoke.sh` exercises all three workflows over HTTP and exits 0 only if every gate passes. Phase 63A is unchanged but now superseded by 63C as the readiness signal. | Run the new smoke; CI-style exit code |

## 2. Defects intentionally not fixed in this PR (and why)

- **No new product UI**, no new component, no card-title rename
  (the on-screen "Provider-Reviewed Ambient Documentation Assist"
  text stays — Phase 62A pinned that distinction; the narration
  label "Provider-Reviewed VisitDraft Assist" lives in docs only).
- **No backend API change.** All three workflow routes
  (`/api/v1/encounters/{id}/vitals-workups`, `/api/v1/encounters/
  {id}/fundus-charts/generate`, `/patients/{id}/scribe-sessions/
  {id}/draft-ambient`) work as documented; the bug was on the
  frontend. The audit's "Direct API also fails" notes were a
  consequence of the stale DB, not the route logic.
- **No new migration.** Head is `b1c2d3e4f5a6`. The fix is to
  upgrade the operator's local DB to head, not to add another
  migration.
- **No claim policy change.** All three scanners
  (commercial / website / demo) still PASS unchanged.
- **No CORS middleware change.** The middleware is already
  configured for `localhost:5173 / 127.0.0.1:5173 / :5174`; the
  audit's "CORS preflight blocked" was the browser symptom of a
  backend 500 (5xx responses bypass the CORS-headers happy path).
- **No `phase63a_capture_demo_media.mjs` change.** The Phase 63A
  capture script is left in place; its file-presence gate is
  now explicitly documented as **media GO**, distinct from
  **buyer-demo functional GO** (which requires the new 63C smoke).

## 3. DB reset / migration behaviour

| Surface | Before Phase 63C | After Phase 63C |
|---|---|---|
| `bash scripts/reset_demo_state.sh` | `rm -f` dev DB → `make migrate seed`. Refused to run with non-default `DATABASE_URL`. Unchanged. | Unchanged. |
| Desktop bundle `./start-api.sh` | `make boot` directly. If DB was stale, missing tables caused 500s with no warning. | `make migrate` → `make seed` (idempotent) → `make boot`. Stale DBs self-heal at next start. Opt-out: `CHARTNAV_DEMO_SKIP_MIGRATE=1`. Refuses to boot if migrate fails (clear recovery message). |
| `scripts/demo/phase63a_start_demo_stack.sh` | Already calls `scripts/reset_demo_state.sh`. Unchanged. | Unchanged (the auto-migrate in start-api is a no-op when the stack has already been reset). |

**Why non-destructive auto-migrate, not auto-reset.** A clean
Morgan-only landing is the operator's choice
(`bash scripts/reset_demo_state.sh`). Operators sometimes
intentionally create QA records and don't want them wiped on
every API restart. The auto-migrate path covers the "missing
tables" problem (which is what the audit cared about) without
destroying state.

## 4. API routing changes (frontend only)

Three feature clients were rewritten to:

1. Import `API_URL` from `apps/web/src/api.ts` (which resolves to
   `import.meta.env.VITE_API_URL` or `http://localhost:8000`).
2. Prefix every path with `API_URL`.
3. Set `X-User-Email` from an optional explicit `email` arg or,
   if absent, `localStorage.chartnav.devIdentity` (the convention
   `App.tsx` already uses for the dev identity selector).

| File | Path prefix | Before | After |
|---|---|---|---|
| `apps/web/src/features/vitals/vitalsApi.ts` | `/api/v1/...` | `fetch("/api/v1/...")` → hits Vite origin | `fetch("${API_URL}/api/v1/...")` with `X-User-Email` |
| `apps/web/src/features/fundus/fundusApi.ts` | `/api/v1/...` | same | same fix |
| `apps/web/src/features/ambient/ambientApi.ts` | `/patients/...` | `fetch("/patients/...")` (empty `BASE`) | `fetch("${API_URL}/patients/...")` with `X-User-Email` |

The change is backwards-compatible for callers: every exported
function adds an optional trailing `email` arg. Existing call
sites pass nothing, and the function reads from `localStorage`.
When the app eventually moves away from localStorage-based
identity (real auth), the panels will start threading `email`
explicitly.

## 5. Workflows verified

End-to-end (functional smoke, run on the operator's stack):

1. **Vitals** — clinician POSTs to
   `/api/v1/encounters/1/vitals-workups`, reviews, signs.
2. **VisitDraft** — clinician POSTs to
   `/patients/1/scribe-sessions`, drafts ambient, reviews,
   finalizes.
3. **Fundus** — clinician POSTs to
   `/api/v1/encounters/1/fundus-charts/generate`, reviews, signs.
4. **manual_note shape** — string payload returns `400
   invalid_event_data`; object payload returns `201`.

Component-level (vitest):

- `VitalsWorkupPanel.test.tsx` (13 cases) PASS
- `FundusChartPanel.test.tsx` (23 cases) PASS
- `AmbientDocumentationPanel.test.tsx` (19 cases) PASS
- `App.test.tsx` (20 cases) PASS
- `Phase63cFeatureApiRouting.test.tsx` (8 cases) PASS (new)
- `Phase63cShapeEventData.test.ts` (10 cases) PASS (new)

## 6. Tests added / updated

**New**:
- `apps/web/src/test/Phase63cFeatureApiRouting.test.tsx` — 8 tests
  pinning that the 3 feature clients use `API_URL` + send
  `X-User-Email`, and that no feature path resolves on
  `localhost:5173`.
- `apps/web/src/test/Phase63cShapeEventData.test.ts` — 10 tests
  pinning the manual_note shaping helper (empty refused, free-text
  wrapped as `{ note: trimmed }`, JSON object passed through,
  legacy behaviour preserved for non-manual_note events).
- `apps/web/src/utils/shapeEventData.ts` — the helper itself,
  exported for the test.
- `scripts/demo/phase63c_functional_smoke.sh` — the new functional
  gate.

**Backend tests already cover** the manual_note rejection contract
(`apps/api/tests/test_admin.py:223-234`,
`apps/api/tests/test_invitations.py:176-179`), so no new backend
test was added.

**No backend code changed**, so existing backend tests for
vitals/fundus/scribe-sessions/runtime-safety were not modified.
The Alembic safety check still passes (head `b1c2d3e4f5a6`).

## 7. Screenshots / videos impact

**Phase 63A screenshots + videos are unaffected.** The bug was
that the *running stack* didn't function, not that the captures
were wrong. After running the new functional smoke and refreshing
the stack with the auto-migrate, the existing Phase 63A media
remains usable.

However, the captures may still benefit from a recapture once the
stack is verified GO — that's an operator-side step, not part of
this PR.

## 8. Buyer-demo GO / NO-GO

**Repo-side: GO** — every safety gate passes on this branch:

| Gate | Status |
|---|---|
| `scripts/check_runtime_safety.py` | PASS |
| `scripts/check_commercial_claims.sh` | PASS (0 fail / 0 warn) |
| `scripts/check_website_claims.sh` | PASS (0 fail / 0 warn) |
| `scripts/check_demo_claims.sh` | PASS (0 hits across 32 demo files) |
| `scripts/test_claim_policy_fixtures.sh` | PASS |
| `scripts/check_alembic_safety.sh` | PASS (head `b1c2d3e4f5a6`) |
| Frontend `npx tsc --noEmit` | clean |
| Frontend `npx vitest run` (new + affected) | 93/93 PASS |
| `git diff --check` | clean |

**Operator-side: NO-GO until functional smoke returns GO.** The
operator must run:

```bash
cd "$CHARTNAV_REPO_PATH"
git pull origin main          # once Phase 63C merges
rm -rf "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
cp -R "$CHARTNAV_REPO_PATH/artifacts/phase-62/desktop-bundle/" \
      "$HOME/Desktop/ChartNav-Buyer-Demo-Build"

# terminal 1
cd "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
./start-api.sh                # auto-migrates + seeds + boots

# terminal 2
cd "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
./start-web.sh

# terminal 3 — the new functional gate
cd "$CHARTNAV_REPO_PATH"
bash scripts/demo/phase63c_functional_smoke.sh
```

The smoke prints `BUYER-DEMO FUNCTIONAL GO: YES` only when all 6
gate-groups pass. Anything short of that is **NO-GO** for live
buyer demo.

## 9. Remaining risks

- **QA records still on disk.** The non-destructive auto-migrate
  leaves any existing rows (including the Maria/QA records the
  audit found) intact. Operators who want a clean Morgan-only
  landing must explicitly run `bash scripts/reset_demo_state.sh`.
  Documented but not enforced.
- **Identity propagation via localStorage.** The 3 feature clients
  read identity from localStorage when no explicit arg is passed.
  This is fine for the demo (the App's identity selector writes
  there) and for the Playwright capture script (Phase 63 wires
  the same key). When the app moves to real auth, the panels
  should pass `identity` explicitly — the feature client
  signatures already support it.
- **Phase 63A media gate language.** The Phase 63A report and the
  Phase 62A dry-run report aren't edited here; they continue to
  report file-presence as their gate. Operators reading those
  should treat them as **media GO** signals only, and run the
  new 63C smoke to get **buyer-demo functional GO**.
- **CORS preflight on backend 5xx.** If the stack regresses to a
  state where the DB is stale, browser fetches will surface
  "CORS preflight" errors. The real cause is the backend 500;
  the operator should run `make migrate` or
  `bash scripts/reset_demo_state.sh` to recover.

## 10. Exact commands for Jean-Max

After Phase 63C merges to main:

```bash
# 1. Sync local main and refresh the Desktop bundle.
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull origin main
git log --oneline -1
rm -rf "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
cp -R "$CHARTNAV_REPO_PATH/artifacts/phase-62/desktop-bundle/" \
      "$HOME/Desktop/ChartNav-Buyer-Demo-Build"

# 2. Optional clean slate (drops manually-created Maria/QA rows).
bash scripts/reset_demo_state.sh

# 3. Boot the stack. start-api.sh auto-runs migrate + seed.
# Terminal 1
cd "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
./start-api.sh

# Terminal 2
cd "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
./start-web.sh

# 4. New functional gate. Returns 0 only if every workflow passes.
# Terminal 3
cd "$CHARTNAV_REPO_PATH"
bash scripts/demo/phase63c_functional_smoke.sh

# Expected last line: BUYER-DEMO FUNCTIONAL GO: YES
```

If the smoke exits non-zero, scroll up to the `FAIL  …` lines for
the specific gate(s) that failed and the failure detail.

## Related documents

- `docs/build/phase-63b-functional-demo-qa-audit.md` (on
  `feature/phase-63b-functional-demo-qa-audit` branch; the source
  of truth for the 14 defects)
- `docs/build/phase-63a-automated-demo-media-capture-report.md`
  (the Phase 63A media report whose GO is now scoped to
  media-presence only)
- `docs/build/phase-63-safe-demo-media-website-report.md`
- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
- `docs/build/current-product-truth.md`
