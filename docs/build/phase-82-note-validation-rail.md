# Phase 82 — Note Validation Rail

**Date:** 2026-06-10
**Branch:** `feature/phase-82-note-validation-rail`
**Base:** `main` at `3d3f430` (after Phase 81)
**Status:** Fifth Phase 2 Clinical Intelligence surface — the pre-sign safety rail

## Purpose

Deterministic pre-sign rail that surfaces structured workflow
completeness checks across every Phase 1 + Phase 2 surface. The rail
is informational by design: it does **not** autonomously block
signing. Provider attestation on the existing sign-and-lock checkbox
remains the existing hard blocker. Warnings the rail emits require
explicit provider acknowledgement, but the provider — not ChartNav —
decides whether to proceed.

This is **NOT** autonomous clinical judgment.

## Check categories

| Category | Rule |
|---|---|
| `laterality` | One check per source surface (vitals / fundus / anti_vegf / cataract) reporting whether laterality was recorded. A rollup check warns when ≥2 sources disagree (disjoint eye sets) and passes when at least one eye is shared. |
| `follow_up` | Pass if anti-VEGF interval *or* cataract post-op cadence has any provider-entered non-`unknown` value. Otherwise warning with acknowledgement required. |
| `unsigned_upstream` | Warning per unsigned vitals workup or unsigned fundus chart on this encounter. Pass-aggregate when none. |
| `review_state` | Visit-draft (scribe session) lifecycle plus a pass note that the existing sign-attestation checkbox is still required. |
| `specialty_data` | Pass/missing flags for anti-VEGF + cataract presence at the patient level. |

Hard rule: no clinical free text is ever surfaced in a check `detail` — only metadata (artifact ids, statuses, laterality codes, dates). The backend test `test_no_forbidden_clinical_language` writes canary `technician_notes` and `complication_note` strings and asserts neither leaks into the response.

## Schema

**None.** Pure aggregation over existing tables (`encounters`, `visit_vitals_workups`, `fundus_charts`, `scribe_sessions`, `anti_vegf_injections`, `cataract_workflow_records`).

## Endpoint

| Method | Path | Auth |
|---|---|---|
| `GET` | `/api/v1/encounters/{encounter_id}/note-validation` | any authenticated caller; org-scoped |

Cross-org returns 404 (no existence leak).

## Item shape

```jsonc
{
  "check_id": "laterality:rollup",
  "category": "laterality",
  "label": "Laterality consistency across sources",
  "status": "warning",                       // pass | warning | missing | blocked
  "laterality": "OU",                        // OD | OS | OU | null
  "source": "visit_draft",                   // 8-value source enum
  "detail": "Laterality differs across surfaces: vitals=OD, fundus=OS. ...",
  "requires_provider_acknowledgement": true,
  "source_artifact_id": null
}
```

Response wrapper carries `checks`, `totals` (4-status counts), `acknowledgements_required`, `disclosure` verbatim.

`status="blocked"` is reserved for the existing sign-attestation rule and emitted only when there is unfinalized upstream AND a finalized visit draft — the existing "must acknowledge to proceed" condition.

## Frontend

| File | Description |
|---|---|
| `apps/web/src/features/note-validation/noteValidationTypes.ts` | Typed shapes. |
| `apps/web/src/features/note-validation/noteValidationApi.ts` | Fetch wrapper. |
| `apps/web/src/features/note-validation/NoteValidationRail.tsx` | Pre-sign rail panel — totals header, per-check rows with status/source/laterality/ack-required badges, inline "Provider acknowledged" checkboxes for ack-required checks, acknowledgement summary ("N / M acknowledged") plus banner that transitions from amber-outstanding to green-recorded once all ticks fire. Crucially the banner always says **"Sign attestation is still the existing hard blocker; this rail does not block sign-off"** — provider autonomy is preserved. |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Wires rail into the Overview tab between the Phase 81 action queue and the Phase 76 retina summary. |
| `apps/web/src/test/NoteValidationRail.test.tsx` | 10 vitest cases. |

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_note_validation.py -v` | **14 / 14 PASS** |
| Targeted regression (11 suites) | **200 / 200 PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 850 / 850 tests across 49 files** (was 840; +10) |
| All 5 claim/safety scripts | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox); rail is additive and touches no demo/smoke scripts.

## Caveats

- The rail is wired in the **Overview** tab (above the Phase 76 retina summary). The ambient documentation panel's `data-testid="ambient-sign-btn"` and the vitals/fundus sign-attestation flows are untouched — the existing hard sign blockers remain in place. Phase 82 does not couple the rail's acknowledgement state to any sign button; it surfaces and records the acknowledgement in local component state for now. A future phase can post acknowledgement events to an audit endpoint if desired.
- `ack` state resets on refetch, deliberately: any state that survives a refetch could create the appearance of an autonomous gate. Provider acknowledgement is a per-render rail check, not a persisted record.

## Next phase recommendation

**Phase 83 — Pre-Sign Acknowledgement Persistence + Audit Trail.** Optional follow-up: persist provider acknowledgement of validation warnings to `security_audit_events` (metadata-only — check_id, encounter_id, actor user id, timestamp), surface a "last acknowledged at" stamp on the rail, and expose recent acknowledgements via the Phase 73 audit-trail view. Same boundary: no autonomous sign blocking, acknowledgement is provider-driven.
