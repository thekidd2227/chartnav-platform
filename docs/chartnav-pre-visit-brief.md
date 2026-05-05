# ChartNav Pre-Visit Clinical Brief (Phase 10)

The pre-visit brief is a **provider-facing summary of the existing
ChartNav chart** for one patient. It is generated on demand from
already-persisted source artifacts so the provider can review what
ChartNav already knows before the visit.

It is explicitly **not**:

- An autonomous diagnosis or clinical decision.
- A patient-facing artifact. Nothing is sent to a patient.
- An order/coding tool.
- A treatment automation.
- An external-LLM summarizer.

It is a deterministic aggregation of records that the provider has
already entered or reviewed, plus a list of explicit gaps.

## Storage

**No persistence.** Phase 10 ships **no new table** and **no
migration**. The brief is a derived view computed on each call from
existing tables: `patients`, `encounters`, `workflow_events`,
`scribe_sessions`, `chart_artifacts`, `patient_summaries`.

Rationale:

- The brief is a pure aggregation. Persisting it would require
  invalidation hooks on five source tables; failing to invalidate
  would silently serve stale clinical context.
- Compute is cheap — a small set of org-scoped SELECTs per patient.
- No new table means no new audit-log shape, no new RBAC surface,
  and no migration risk.

## Workflow

```
              POST /pre-visit-briefs/generate
            +-------------------------------+
            | audited; emits                |
provider →  | pre_visit_brief_generated     |  → fresh brief response
            +-------------------------------+

              GET /pre-visit-brief
            +-------------------------------+
provider →  | read-only; not audited        |  → fresh brief response
            +-------------------------------+
```

Both endpoints compute against current source data. There is no
caching layer.

## API

| Method | Path                                                | Action                            | Required role        |
|--------|-----------------------------------------------------|-----------------------------------|----------------------|
| POST   | `/patients/{patient_id}/pre-visit-briefs/generate`  | explicit, audited generation      | `admin`, `clinician` |
| GET    | `/patients/{patient_id}/pre-visit-brief`            | read-only on-demand recompute     | `admin`, `clinician`, `reviewer` |

### Response shape

```jsonc
{
  "patient_id": 123,
  "brief_status": "generated",
  "last_visit_summary": "Most recent encounter on 2026-05-01 with Dr. Carter (status: in_progress).",
  "active_issues": ["..."],
  "retinal_artifact_summary": {
    "total": 2,
    "signed_count": 1,
    "unsigned_count": 1,
    "has_unsigned_drafts": true,
    "latest_signed": {
      "id": 100,
      "title": "OD/OS macula drawing",
      "signed_at": "2026-05-04T12:00:00+00:00",
      "version_number": 1,
      "encounter_id": 42
    }
  },
  "recent_scribe_session_summary": {
    "session_id": 50,
    "status": "reviewed",
    "chief_complaint_excerpt": "...",
    "plan_excerpt": "..."
  },
  "patient_summary_context": {
    "summary_id": 12,
    "status": "finalized",
    "source_kind": "finalized",
    "plain_language_excerpt": "...",
    "key_findings_count": 2,
    "next_steps_count": 1
  },
  "pending_items": [
    { "kind": "scribe_session", "id": 50, "status": "ready_for_review" }
  ],
  "suggested_review_items": [
    { "kind": "scribe_session", "id": 50, "reason": "scribe session ready for provider review" }
  ],
  "data_gaps": ["No retinal artifacts on file for this patient."],
  "source_counts": {
    "encounters": 2, "workflow_events": 5,
    "scribe_sessions": 1, "scribe_sessions_finalized": 1,
    "retinal_artifacts": 1, "retinal_artifacts_signed": 1,
    "patient_summaries": 1, "patient_summaries_finalized": 1
  },
  "generated_at": "2026-05-05T19:30:00+00:00",
  "notice": "Pre-visit brief — provider review required. ..."
}
```

### Error codes

| Code               | HTTP | Meaning                                              |
|--------------------|------|------------------------------------------------------|
| `patient_not_found`| 404  | Patient not in caller's org (also covers cross-org)  |
| `role_forbidden`   | 403  | Caller's role cannot perform this action             |

## Source priority

The generator pulls source content in this priority order. Sections
prefer higher-priority sources when both are available:

1. **Finalized patient summaries.** `patient_summary_context` selects
   the most recent `status == "finalized"` row; if none exists, falls
   back to the most recent `status == "reviewed"` and tags the source
   kind. Discarded summaries are excluded.
2. **Reviewed/finalized scribe sessions.** `recent_scribe_session_summary`
   selects the most recent session in `{reviewed, finalized}`; if
   none, falls back to the most recent non-discarded session and
   surfaces its status.
3. **Signed retinal artifacts.** `retinal_artifact_summary.latest_signed`
   uses `signed_at IS NOT NULL`. Unsigned drafts are counted but never
   surfaced as the latest-signed entry.
4. **Recent encounters.** `last_visit_summary` is composed from the
   most recent encounter (by `completed_at`, `started_at`, or
   `scheduled_at`, falling back to `created_at`). It contains date,
   provider, and status — never a diagnostic claim.
5. **Workflow events.** Counted in `source_counts.workflow_events`
   for the patient's recent encounters; their bodies are never
   rendered into the brief response.

`active_issues` is composed from (1) finalized patient summary
`key_findings` plus (2) `assessment` items from a finalized scribe
session's `structured_note_json`. Items are deduplicated
case-insensitively, preserving order. The generator does **not**
interpret, paraphrase, or rank them.

## `source_counts` behavior

`source_counts` is a sorted-key dictionary of integer counts:

- `encounters` — most recent encounters considered (capped at 10)
- `workflow_events` — recent workflow events across those encounters
  (capped at 25)
- `scribe_sessions` — total scribe sessions for this patient in this
  org
- `scribe_sessions_finalized` — count in `{reviewed, finalized}`
- `retinal_artifacts` — total chart_artifacts of any signed state
- `retinal_artifacts_signed` — count where `signed_at IS NOT NULL`
- `patient_summaries` — total patient summaries for this patient
- `patient_summaries_finalized` — count where `status = "finalized"`

These counts are also encoded into the audit `detail` field for the
`pre_visit_brief_generated` event — they are metadata, not body
content.

## `data_gaps` behavior

`data_gaps` is a list of explicit, human-readable strings. Each entry
identifies a missing or weakly-populated source:

- "No recent encounters on file for this patient."
- "No workflow events recorded against this patient's encounters."
- "No scribe sessions on file for this patient."
- "No reviewed or finalized scribe session on file; context above
  falls back to the most recent draft."
- "No retinal artifacts on file for this patient."
- "No signed retinal artifacts on file; only unsigned drafts exist."
- "No patient-friendly summaries on file for this patient."
- "No finalized patient-friendly summary; using the latest
  reviewed/draft summary for context."

Gaps are intentionally conservative — they surface what's missing
without claiming whether it should be there clinically. The
provider decides.

## RBAC

- **`admin`, `clinician`** — may both generate (POST) and read (GET).
- **`reviewer`** — read-only. May call GET; POST returns `403
  role_forbidden`. This matches the read-only convention applied on
  patient summaries and scribe sessions.
- **Org isolation** — patient is resolved inside the caller's
  organization first. Cross-org or unknown returns `404
  patient_not_found` (no existence leak). Every per-source SELECT
  re-filters by `organization_id` for defense in depth.

## Audit / PHI safety

A single audit event type — `pre_visit_brief_generated` — is emitted
on every POST `/generate`. The `detail` column contains exactly:

```
patient_id=<id> generated_at=<iso> counts[<sorted key=value pairs>]
```

The audit detail **never includes** any of:

- `last_visit_summary` body
- `active_issues` entries
- retinal artifact title or `findings_text`
- scribe session `chief_complaint_excerpt`, `plan_excerpt`, or any
  `source_text` / `transcript_text` / `draft_note_text`
- patient summary `plain_language_excerpt` or any of the JSON-list
  fields
- `pending_items`, `suggested_review_items`, or `data_gaps` body

GET `/pre-visit-brief` is read-only and does **not** emit an audit
event, consistent with the read-side of `patient_summaries` and
`scribe_sessions`. Sentinel-token regression tests assert this for
every section body.

## Deterministic v1 generation behavior

The generator is fully deterministic:

- All source rows are queried org-scoped via raw SQL with named
  bind parameters. The same query plan runs on SQLite and Postgres.
- Section bodies are composed via dataclass aggregation —
  no `eval`, no template engine, no LLM call.
- Excerpt fields are truncated to fixed character limits with a
  trailing ellipsis.
- Dedup of `active_issues` is case-insensitive but preserves order
  of first appearance.
- The notice string is a constant: `PROVIDER_REVIEW_NOTICE`.

## Provider review requirement

The brief is always labeled with the provider-review notice. The
panel surfaces:

> Pre-visit brief — provider review required. This brief summarizes
> available ChartNav records and may be incomplete.

The panel intentionally exposes no patient-send action, no order
button, no coding action, and no automation control. The brief is
read-only context for the provider.

## Limitations (v1)

- No specialty-specific risk scoring.
- No longitudinal trend math (no IOP/visual-acuity trajectory plots).
- No external data ingestion — anything not already in ChartNav is
  invisible to the brief.
- No invalidation hooks — every call re-reads source data, so a
  brief returned by `GET` reflects the database at query time.
- No paginated history — the most recent N encounters / events are
  used; full history is not presented.

## Deferred

- **External-LLM summarization.** The generator is regex / aggregation
  only. A future phase may add an LLM source under the same
  provider-review contract — not Phase 10.
- **Specialty-specific risk scoring** (glaucoma progression, AMD
  progression, post-op infection risk, etc.).
- **Patient-portal delivery** of any kind.
- **Orders / coding** based on the brief.
- **Automated follow-up creation** (no calendar writes, no encounter
  creation).
- **Longitudinal trend analytics** (cross-visit numeric trajectories).
