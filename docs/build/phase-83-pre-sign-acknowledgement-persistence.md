# Phase 83 — Pre-Sign Acknowledgement Persistence + Audit Trail

**Date:** 2026-06-10
**Branch:** `feature/phase-83-pre-sign-acknowledgement-persistence`
**Base:** `main` at `693df07` (after Phase 82)
**Status:** Sixth Phase 2 Clinical Intelligence surface — persistence + audit layer

## Purpose

Phase 82 surfaced deterministic pre-sign validation warnings with
in-session acknowledgement checkboxes. Phase 83 persists those
acknowledgements as **metadata-only** audit rows in
`security_audit_events`, surfaces "Acknowledged by {name} ({role}) at
{timestamp}" inline on the rail, and folds the events into the
Phase 76 cross-artifact evidence timeline as new
`note_validation`/`acknowledged` rows.

**No clinical free text ever lands on the persisted record.** The
acknowledgement payload deliberately accepts only three fields
(`validation_item_id`, `validation_category`, `acknowledgement_type`),
and the service-side canary rejects any free-text key (`note`,
`detail`, `findings`, `diagnosis`, …) with `422 forbidden_payload_field`.

This is **NOT** autonomous sign blocking. The existing
sign-attestation flow remains untouched. Acknowledgement is provider-
driven and reversible (a `rescinded` row supersedes an earlier
`acknowledged` row in the rail's display logic, with both rows
preserved in the append-only audit trail).

## Schema

**None.** Audit rows live in the existing `security_audit_events`
table (event_type `note_validation_acknowledged`, JSON metadata in
the `detail` column).

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `POST` | `/api/v1/encounters/{encounter_id}/note-validation/acknowledgements` | required | any authenticated role with encounter access |
| `GET`  | `/api/v1/encounters/{encounter_id}/note-validation/acknowledgements` | required | same |

Cross-org returns 404 (no existence leak), matching the rest of the
encounter surface.

## Persisted metadata

Each acknowledgement row carries the following fields (in the audit
`detail` JSON, surfaced verbatim on the GET response):

| Field | Source |
|---|---|
| `encounter_id` | path |
| `validation_item_id` | payload (CHECK ID, e.g. `laterality:rollup`) |
| `validation_category` | payload (one of laterality / follow_up / unsigned_upstream / review_state / specialty_data) |
| `acknowledgement_type` | payload (`acknowledged` or `rescinded`) |
| `actor_id` | caller user id |
| `actor_display_name` | caller user `full_name` (falls back to email) |
| `actor_role` | caller role |
| `acknowledgement_timestamp` | server-generated ISO UTC |

The `security_audit_events.actor_email` and `organization_id` columns
are populated by the existing `audit.record()` helper. The audit
trail is **append-only**: every toggle generates a new row. The Phase
83 rail derives the "currently acknowledged" state by taking the
newest row per `(encounter_id, validation_item_id)` and dropping it
if its `acknowledgement_type` is `rescinded`.

## Evidence-timeline integration (Phase 76 fold-in)

The Phase 76 retina-visit-summary service now folds ack rows into the
cross-artifact `evidence_timeline` as new entries:

```jsonc
{
  "artifact_type": "note_validation",
  "event_type": "acknowledged",
  "ref_id": 42,                              // security_audit_events.id
  "timestamp": "2026-06-10T04:00:00Z",       // acknowledgement_timestamp
  "actor_display_name": "Casey Clinician",
  "actor_role": "clinician",
  "validation_item_id": "laterality:rollup",
  "validation_category": "laterality",
  "acknowledgement_type": "acknowledged"
}
```

Phase 76's existing rendering picks these up automatically — they
sort chronologically alongside vitals / visit-draft / fundus events
with no clinical text.

## Frontend

| File | Description |
|---|---|
| `apps/web/src/features/note-validation/noteValidationTypes.ts` | Adds `NoteValidationAcknowledgement` + `AcknowledgementType`. |
| `apps/web/src/features/note-validation/noteValidationApi.ts` | Adds `getNoteValidationAcknowledgements()` + `postNoteValidationAcknowledgement()`. |
| `apps/web/src/features/note-validation/NoteValidationRail.tsx` | Hydrates persisted ack history on mount, seeds checkbox state from server, optimistically toggles + POSTs on click, reverts on failure with an ack-error banner. Shows "Acknowledged by {name} ({role}) at {timestamp}" inline on each persisted check. |
| `apps/web/src/features/retina-summary/retinaSummaryTypes.ts` | Widens `RetinaArtifactType` to include `note_validation` and `RetinaEventType` to include `acknowledged`; adds the three metadata fields. |
| `apps/web/src/features/retina-summary/RetinaVisitSummaryPanel.tsx` | Picks up new artifact/event labels for the timeline. |
| `apps/web/src/test/NoteValidationRail.test.tsx` | +4 vitest cases for hydration, POST on toggle, rescind on untick, failure revert. |
| `apps/web/src/test/RetinaVisitSummaryPanel.test.tsx` | +1 vitest case for the new `note_validation/acknowledged` row in the timeline. |

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_note_validation_acknowledgements.py -v` | **14 / 14 PASS** |
| Phase 76/77/82/83 regression | **43 / 43 PASS** |
| Targeted backend regression (15 suites) | **PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 855 / 855 tests across 49 files** (was 850; +5 net) |
| All 5 claim/safety scripts | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox); the persistence
flow is additive and touches no demo/smoke scripts.

## Caveats

- The Phase 82 `NoteValidationRail` previously kept ack state purely
  in `useState` and reset it on refresh. Phase 83 changes the
  semantics: on mount the rail issues a parallel GET to hydrate
  checkbox state from server, so a refresh now correctly reflects
  what the provider previously persisted. Existing Phase 82 vitest
  cases were updated to mock the new fetcher (the post mock is also
  primed so the existing toggle tests continue to fire without
  hitting the wire). All ten original Phase 82 tests still pass.
- Audit rows are append-only by design. The Phase 83 rail does not
  expose a delete endpoint; a "rescinded" row is simply a new audit
  entry. This keeps the audit trail tamper-evident.
- Acknowledgement events on the Phase 76 timeline are sorted with
  every other artifact event by their ISO timestamp; if the
  acknowledgement happens after a signed artifact, it appears
  chronologically after that signed event.

## Next phase recommendation

**Phase 84 — Pre-Sign Acknowledgement Compliance Snapshot.** Extend
the Phase 76 visit summary aggregator + Phase 77 packet export to
include a per-encounter `acknowledgement_summary` (counts by
category, by status, latest-by-item map) so the buyer-demo packet
includes verifiable evidence the provider acknowledged every Phase 82
warning before signing. Same boundary: deterministic, metadata-only,
no autonomous gating, no clinical free text.
