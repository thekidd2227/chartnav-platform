# Frontend Operator UX for Async Ingestion (phase 24 — hardening pass)

This is a lane-safe frontend/test/docs hardening pass on top of the
phase-22 async ingestion lifecycle + phase-23 background-worker
foundation. It **does not** touch backend code, migrations, or the
primary phase-23 doc — all backend contracts remain source-of-truth.

## 1. Scope

- Operator-facing messaging in `NoteWorkspace.tsx` when an input
  is `queued`, `processing`, `failed`, or `needs_review`.
- Honest "why is Generate disabled" copy.
- Tighter queue-banner copy that differentiates "worker picked it
  up" from "waiting for a worker".
- Vitest coverage for the new blocked-hint states.
- A dedicated Playwright spec exercising the wedge under the
  delayed-processing assumption.

## 2. UI changes

### Queue banner (tier-1)
Before: one banner that said "Processing continues in the
background. An input is {currently processing | waiting for a
worker}." The two cases were buried in a single sentence.

After: two honest variants, chosen on the presence of a
`processing` row:

- **Processing variant**: "Transcript is processing in the
  background. A worker picked up the input and is extracting text.
  Draft generation will unlock automatically once processing
  finishes — click **Refresh** to pull the latest status, or step
  away and come back."
- **Queued variant**: "Transcript is queued in the background.
  It's waiting for a worker to pick it up. Click **Process now**
  on the queued row to run it immediately, or wait for the next
  worker tick."

### Generate-blocked hint
A new `subtle-note` under the Generate-draft button tells the
operator exactly why Generate is disabled. Four cases:

| State of input list | Hint text |
|---|---|
| empty (no rows) | "Generation unlocks once a transcript has been ingested and finished processing." |
| any `queued`/`processing` | "Generation is waiting on transcript processing. Background work continues — use Refresh to pull the latest status." |
| any `failed`/`needs_review` (no completed) | "The most recent input failed or needs review. Retry it, or ingest a fresh transcript before generating." |
| other (no completed but none of above) | "No completed input is available yet." |

Rendered with `data-testid="generate-blocked-note"` and the
`.workspace__generate-blocked` utility (soft left-border accent
on `--cn-surface-alt`). Never shown when a completed input
exists.

### No layout or brand changes
- Same trust-tier scaffolding (`.workspace__tier` 1/2/3).
- Same color system (`--cn-*` tokens).
- No restructure of the Transcript / Findings / Draft tiers.
- Same "Powered by ARCG Systems" footer handling in the shell.

## 3. Test coverage added

### Vitest (`src/test/NoteWorkspace.test.tsx`, +3)
- `generate-blocked hint: empty state tells the operator to ingest first` — no inputs + Generate disabled + empty-state copy.
- `generate-blocked hint: queued input tells the operator processing is pending` — processing-waiting copy.
- `generate-blocked hint: failed input tells the operator to retry` — retry-it copy + `retries N` chip still present.

Existing banner tests updated for the tightened copy (two
variants: queued / processing; both assert the correct
differentiating phrase).

### Playwright (`tests/e2e/note-workspace-hardening.spec.ts`, new, 3 tests)
- `generate-blocked hint appears when no transcript has been ingested` — baseline on seeded encounter.
- `happy path: ingest → completed → generate unlocks` — drives the real HTTP stack against the seeded backend; asserts either Generate-enabled + no blocked-hint (success) or the blocked-hint never reverts to empty-state copy on failure.
- `manual refresh button re-fetches without reloading the page` — intercepts `/encounters/1/inputs` response and proves the click triggers a new HTTP fetch (the live dev stack's pipeline runs inline, so the spec focuses on the *UX contract* rather than racing a worker).

All 3 deterministic on the local stack; CI inherits them through
the existing `e2e` job.

## 4. Files touched (lane-safe)

Changed:
- `apps/web/src/NoteWorkspace.tsx` — queue-banner copy variants + new blocked-hint block.
- `apps/web/src/styles.css` — `.workspace__generate-blocked` utility.
- `apps/web/src/test/NoteWorkspace.test.tsx` — +3 tests + 2 updated assertions.
- `apps/web/tests/e2e/note-workspace-hardening.spec.ts` — new Playwright spec.

Intentionally avoided (backend phase architecture; do not collide):
- `apps/api/app/services/*`
- `apps/api/app/api/routes.py`
- `apps/api/alembic/versions/*`
- `docs/build/33-async-ingestion-lifecycle.md` (live backend phase doc)
- `docs/build/34-background-worker-foundation.md` (live backend phase doc)
- `docs/final/chartnav-workflow-state-machine-build.html` / `.pdf`

## 5. Verification matrix

| Command | Result |
|---|---|
| `npm run typecheck` | ✅ clean |
| `npm test` | ✅ **58/58 Vitest** |
| `npm run build` | ✅ 215 KB JS / 18.9 KB CSS |
| `npx playwright test tests/e2e/note-workspace-hardening.spec.ts` | ✅ **3/3** |
| `npx playwright test tests/e2e/workflow.spec.ts tests/e2e/a11y.spec.ts tests/e2e/note-workspace-hardening.spec.ts` | ✅ **20/20** |

## 6. Remaining items

- Visual regression is still local-only (phase 15 gap, unchanged).
- Backend-side async processing is still inline on text inputs;
  the Playwright spec works around this by asserting the
  messaging contract rather than a real worker race. Once a
  deployment wires a real STT transcriber, the same spec
  exercises the real async path without changes.
