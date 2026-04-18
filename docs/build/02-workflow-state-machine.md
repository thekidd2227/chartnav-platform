# Encounter Workflow State Machine

## Status values

| Status          | Meaning                                          |
|-----------------|--------------------------------------------------|
| `scheduled`     | Visit is booked, patient has not arrived.        |
| `in_progress`   | Provider is seeing the patient / actively charting. |
| `draft_ready`   | Note draft has been generated and is awaiting review. |
| `review_needed` | Reviewer flagged the note — needs revision or sign-off. |
| `completed`     | Note signed off; encounter closed. **Terminal.** |

## Allowed transitions

Forward flow:

```
scheduled ─▶ in_progress ─▶ draft_ready ─▶ review_needed ─▶ completed
```

Explicit rework transitions (documented + enforced):

| From            | To             | Purpose                                  |
|-----------------|----------------|------------------------------------------|
| `draft_ready`   | `in_progress`  | Draft rejected, return to charting.      |
| `review_needed` | `draft_ready`  | Reviewer kicks note back for rewrite.    |

## Rejected transitions (examples that return HTTP 400)

- `scheduled → completed`
- `scheduled → review_needed`
- `scheduled → draft_ready`
- `in_progress → scheduled`
- `in_progress → completed` (must pass through draft_ready + review_needed)
- `completed → anything` (terminal)
- Any unknown status string (`invalid_status`)

Error body format:
```json
{"detail":"invalid_transition: in_progress -> completed is not permitted; allowed next states from in_progress: ['draft_ready']"}
```

## Idempotency

Posting the **same** status the encounter is already in is a no-op: the row
is returned unchanged and **no** `status_changed` event is appended.

## Side effects on successful transition

| Transition target | Timestamp action                             |
|-------------------|----------------------------------------------|
| `in_progress`     | set `started_at = now()` if currently NULL   |
| `completed`       | set `completed_at = now()`; also set `started_at = now()` if it was NULL |
| other             | no timestamp mutation                        |

Every successful transition appends a `workflow_events` row:

```json
{
  "event_type": "status_changed",
  "event_data": {"old_status": "...", "new_status": "..."}
}
```

## Diagram

See `docs/diagrams/encounter-status-machine.md` (Mermaid).

## Source of truth

`apps/api/app/api/routes.py`:

- `ALLOWED_STATUSES` — the 5 permitted status strings.
- `ALLOWED_TRANSITIONS` — `dict[str, set[str]]`, one entry per source state.
- `update_encounter_status()` — the single enforcement point.
