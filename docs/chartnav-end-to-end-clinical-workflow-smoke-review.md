# ChartNav End-to-End Clinical Workflow Smoke Review (Phase 12)

Phase 12 is a **hardening / verification pass**, not a new product
surface. It exercises the existing ChartNav clinical workflow across
phases 6 / 8 / 9 / 10 / 11 in a single seeded context to catch
integration cracks, missing wiring, stale assumptions, audit-leak
regressions, and unsafe language.

The phase introduces:

- new backend integration tests
- new frontend smoke tests
- one Playwright e2e smoke spec
- a documented safety-language scan
- this contract document

**No new product surface, no new database table, no migrations, no
new feature.**

## Verified workflow path

```
patient context
    │
    ▼
scribe session ── phase 8 ───┐
    │                        │
    ▼                        │
findings → proposals ── phase 6
    │                        │
    ▼                        │
retinal diagram ── phase 5B+6│
    │                        │
    ▼                        │
patient-friendly summary ── phase 9
    │                        │
    ▼                        │
pre-visit brief ── phase 10  │
    │                        │
    ▼                        │
provider action review ── phase 11
```

Each step is exercised against a single seeded org / user / patient /
encounter so we catch wiring defects between modules — not just
within one phase.

## Test coverage map

| Phase | Surface                       | Read | Write | Audit | Cross-org | RBAC |
|-------|-------------------------------|------|-------|-------|-----------|------|
| 5B    | `chart_artifacts` (eye diagrams) | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6     | `propose-from-findings` (read-only) | ✓ | n/a | ✓ | ✓ | ✓ |
| 8     | `scribe_sessions` lifecycle   | ✓ | ✓ | ✓ | ✓ | ✓ |
| 9     | `patient_summaries` lifecycle | ✓ | ✓ | ✓ | ✓ | ✓ |
| 10    | pre-visit brief (on-demand)   | ✓ | ✓ | ✓ | ✓ | ✓ |
| 11    | provider action queue         | ✓ | ✓ | ✓ | ✓ | ✓ |

Coverage notes:

- **Read** — list / get is hit on every phase by the route-sanity
  group of tests so a missing router include surfaces immediately.
- **Write** — every phase that supports a write is driven through at
  least one full lifecycle (create → process → review → finalize for
  scribe; create → review → finalize for summary; sign for retinal
  artifact; accept → complete and dismiss for action items).
- **Audit** — sentinel tokens are injected at every clinical-body
  field across all phases, then a single test asserts none of those
  sentinels appears in any `security_audit_events` row after the full
  workflow completes.
- **Cross-org** — every patient-id-bearing route is hit from a
  different-org caller and asserted to return `404 patient_not_found`.
- **RBAC** — a reviewer is allowed to read every phase's surface and
  asserted to be rejected with `403 role_forbidden` on every write
  surface.

## Backend integration coverage

`apps/api/tests/test_end_to_end_clinical_workflow.py` adds **17 new
integration tests** organized by intent:

| Group | Tests | Purpose |
|-------|-------|---------|
| `TestRouteSanity` | 8 | Every Phase 5B/6/8/9/10/11 list/generate route answers a documented status — never 404 due to missing router. |
| `TestScribeToProposal` | 1 | Finalize a scribe session and pull diagram proposals from its findings text. Confirms `propose-from-findings` is read-only on data. |
| `TestRetinalArtifactLifecycle` | 1 | Create unsigned artifact → apply proposal-shaped payload (`source=ai_approved`) → sign → confirm signed-immutable. |
| `TestPatientSummaryFromFinalizedScribe` | 1 | Create summary from a finalized scribe → edit → review → finalize → confirm finalized-immutable. |
| `TestPreVisitBriefIncludesAllSources` | 1 | Once scribe + summary + signed artifact exist, the brief reports `source_counts > 0` for each, includes the provider-review notice, and contains no unsafe language. |
| `TestProviderActionLifecycleOverFullChart` | 1 | Full chart drives both workflow-completion and clinical-language action types. Walk accept→complete on one, dismiss on another, assert direct suggested→complete is rejected with 409. |
| `TestEndToEndAuditRedaction` | 1 | Inject sentinel tokens in every clinical-body field across all phases. Walk the full workflow. Assert no sentinel appears in any `security_audit_events.detail` row. |
| `TestEndToEndOrgIsolation` | 1 | Build a chart in chartnav org. Confirm every patient-id-bearing route returns `404 patient_not_found` to a northside-org caller. |
| `TestEndToEndSafetyLanguage` | 1 | Scan every text field returned by every user-facing route for forbidden phrases (orders, coding, referral, patient-message, autonomous, external-LLM). |
| `TestReviewerReadOnlyAcrossWorkflow` | 1 | Reviewer can read every phase's surface; reviewer's write attempts on every phase return `403 role_forbidden`. |

All 17 pass locally in ~30 seconds against the SQLite test DB.

## Frontend smoke coverage

`apps/web/src/test/ClinicalWorkflowSmoke.test.tsx` adds **7 new
smoke tests** that mount the workspace with a numeric `patientId` so
all five clinical panels render:

1. Every clinical panel section mounts (eye-diagram / scribe /
   patient-summary / pre-visit-brief / provider-action-items).
2. Each panel surfaces its provider-review safety copy
   (negative-assertion banner copy is required and verified).
3. Full create→process→review→finalize→summary→brief→actions flow
   drives the right API calls in the right order, against mocked
   client functions.
4. No order / coding / referral / patient-message button is
   rendered across panels — even when the panels show real items.
5. Panel root text contains no autonomous-diagnosis or external-LLM
   language (`autonomous`, `openai`, `anthropic`, `gpt`, `llm`,
   `external llm`).
6. A mocked API error renders a safe banner — no raw stack trace,
   no autonomous-action language.
7. The patient-summary banner and the action-queue banner are
   negative assertions only; no actionable button matches "send to
   patient" or "send referral".

All 7 pass locally.

## Playwright / E2E coverage

`apps/web/tests/e2e/clinical-workflow-smoke.spec.ts` adds a new
Playwright spec that drives the **real** frontend against the **real**
backend (the existing `playwright.config.ts` boots both) and asserts:

1. Every clinical panel section mounts on the seeded encounter for
   PT-1001.
2. Each panel surfaces its provider-review safety copy.
3. No forbidden action button (`place order`, `send referral`,
   `send to patient`, etc.) is rendered in the workspace.
4. The workspace text contains no autonomous-diagnosis or external-
   LLM language.

The spec follows the exact identity / encounter pattern used by the
existing `note-workspace-hardening.spec.ts` — `localStorage`-based
identity selection and `enc-row-1` to open the seeded encounter.
This keeps the smoke deterministic under the shared Playwright stack
on ports 8001 / 5174.

The spec does **not** drive full lifecycle clicks against the live
stack — that is the job of the dedicated panel tests in
`src/test/*.test.tsx` and the backend integration test in Phase 12B.
The Playwright smoke is intentionally a "did the wires get
connected" check, not a regression net for behavior.

## Safety language scan results

A grep across every panel + every service + every route module for
the forbidden token list returned **four matches**, all classified as
**safe negative assertions**:

| Location | Match | Classification |
|----------|-------|----------------|
| `apps/web/src/ScribeSessionPanel.tsx:10` | "No autonomous diagnosis claims. No external LLM" | Header docstring — negative assertion. Not rendered. |
| `apps/web/src/ProviderActionItemsPanel.tsx:165` | "create orders, send referrals, message patients, or take action automatically." | Banner copy — explicit negative assertion that ChartNav does NOT do these things. |
| `apps/api/app/services/provider_action_items.py:11` | "calls an external LLM" | Module docstring — negative-assertion list of non-goals. |
| `apps/api/app/services/patient_summaries.py:19` | "calls an external LLM" | Module docstring — negative-assertion list of non-goals. |

No actionable code uses any of the forbidden tokens. The scan
script that produced this list is reproducible — see the PR body
for the exact `grep -niE` invocation.

## Known limitations

- **Phase 12 ships no schema changes.** All assertions are read-only
  against existing tables. If a real defect required schema changes,
  the right answer would be a follow-up phase, not a Phase 12 patch.
- **The Playwright smoke does not exercise full lifecycle clicks**
  against the live stack — see "Playwright / E2E coverage" above.
- **The clinical-language scan vocabulary in Phase 11 stayed
  unchanged** at four narrow regex patterns. False negatives are
  expected; the queue is documented as not a primary safety net.
- **The audit-redaction integration test injects sentinels at
  representative source fields** (scribe `source_text`, artifact
  `title` and `findings_text`, summary body / list / review notes).
  It does not enumerate every possible JSON-encoded substring — but
  the per-phase sentinel-token tests in earlier phases already do.

## Follow-up recommendations

These are noted for future phases — they are NOT part of Phase 12:

1. **Audit-volume budget.** Once the workflow is in real provider
   hands, snapshot a typical day's audit-event count per
   `event_type` and confirm the per-phase emit rates are consistent
   with intent (no accidental over-emit on read paths).
2. **Cross-source dedupe smoke.** When a future phase adds another
   source for action items (external LLM behind a feature flag, or
   a specialty-specific scorer), add a Phase 12-style smoke that
   exercises the dedupe key with mixed sources.
3. **A11y smoke for the queue.** The `a11y.spec.ts` Playwright spec
   exists but does not yet visit the provider-action-queue panel.
   A short follow-up could add it to the existing axe-core sweep.
4. **CI summary card.** A short post-test step on the `Backend
   (SQLite) — migrate · seed · test · smoke` job that prints a
   tiny summary of phase-level test counts would make slow drift
   obvious in PR comments.

None of these block Phase 12 merging.
