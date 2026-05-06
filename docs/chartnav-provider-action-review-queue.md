# ChartNav Provider Action Review Queue (Phase 11)

The action queue is a **provider-facing review surface** for tasks
ChartNav has surfaced from existing chart records. The provider
explicitly Accepts, Dismisses, or Completes each item. ChartNav
itself **never** creates orders, sends referrals, posts billing or
coding entries, messages patients, or takes any clinical action.

This document is the contract: lifecycle, generator rules, source
priority, dedupe, RBAC, audit safety, and the explicit non-goals.

## Storage

Single new table — `provider_action_items`. Phase 11 ships exactly
one migration: `b3c4d5e6f7a8`.

| Column                  | Type        | Notes                                                  |
|-------------------------|-------------|--------------------------------------------------------|
| `id`                    | INTEGER     | PK                                                     |
| `organization_id`       | INTEGER     | FK → `organizations.id`, NOT NULL                      |
| `patient_id`            | INTEGER     | FK → `patients.id`, NOT NULL                           |
| `encounter_id`          | INTEGER     | FK → `encounters.id`, nullable                         |
| `source_type`           | VARCHAR(64) | Logical category — `scribe_session`, `patient_summary`, `chart_artifact`, `pre_visit_brief` (no FK; sources span tables) |
| `source_id`             | INTEGER     | Source row id; no FK by design                         |
| `action_type`           | VARCHAR(64) | Closed vocabulary — see below                          |
| `priority`              | VARCHAR(16) | CHECK in (`low`,`medium`,`high`)                       |
| `title`                 | VARCHAR(255)| Provider-facing short title. **Never audited.**        |
| `reason`                | TEXT        | Provider-facing rationale. **Never audited.**          |
| `status`                | VARCHAR(16) | CHECK in (`suggested`,`accepted`,`dismissed`,`completed`) |
| `created_by_system`     | BOOLEAN     | default true                                           |
| `generated_batch_id`    | VARCHAR(64) | Stable id for items emitted by a single generate call  |
| `accepted_by_user_id`   | INTEGER     | FK → `users.id`, nullable                              |
| `dismissed_by_user_id`  | INTEGER     | FK → `users.id`, nullable                              |
| `completed_by_user_id`  | INTEGER     | FK → `users.id`, nullable                              |
| `accepted_at`           | TIMESTAMP   | nullable                                               |
| `dismissed_at`          | TIMESTAMP   | nullable                                               |
| `completed_at`          | TIMESTAMP   | nullable                                               |
| `created_at`            | TIMESTAMP   | default now                                            |
| `updated_at`            | TIMESTAMP   | default now; bumped on every write                     |

Indexes on `(organization_id, patient_id)`,
`(organization_id, encounter_id)`, `(organization_id, status)`,
`(organization_id, action_type)`, `(organization_id, priority)`,
and `generated_batch_id`.

## Lifecycle

```
                accept                       complete
   suggested ---------------> accepted ---------------> completed
        |                         |
        |                         | dismiss
        | dismiss                 v
        +-----------------> dismissed
```

- `suggested → accepted` requires explicit `POST /accept`.
- `accepted → completed` requires explicit `POST /complete`.
- `dismiss` is allowed from `suggested` or `accepted`.
- `dismissed` and `completed` are terminal and immutable.
- Direct `suggested → completed` is rejected with
  `409 provider_action_invalid_transition`.
- Any mutation against a terminal item returns
  `409 provider_action_item_immutable`.

## Action-type vocabulary (closed)

The `action_type` column is restricted to a closed set. Any value
outside this set is rejected at the service layer. This is what
keeps the queue firmly in "review prompt" territory — the vocabulary
contains no order, coding, or referral types.

**Clinical review prompts** (triggered by language scans on
finalized chart text):

- `review_retinal_tear_language`
- `review_retinal_detachment_language`
- `review_neovascularization_language`
- `review_severe_hemorrhage_language`

**Workflow completion prompts:**

- `sign_unsigned_retinal_diagram`
- `review_pending_ai_diagram_proposals`
- `review_scribe_session`
- `finalize_scribe_session`
- `review_patient_summary`
- `finalize_patient_summary`

**Pre-visit readiness prompts:**

- `review_pre_visit_data_gaps`
- `review_missing_signed_retinal_artifact`
- `review_missing_finalized_patient_summary`
- `review_missing_reviewed_scribe_session`

**Data-hygiene prompts:**

- `reconcile_unsigned_artifacts`
- `review_unfinalized_patient_context`

Every emitted title uses *review*, *consider*, *reconcile*, or
*finalize* phrasing. Never *order*, *prescribe*, *send referral*,
*bill*, *code*, *email patient*, or *automatically*.

## Generator (deterministic v1)

The generator is a deterministic regex / aggregation over already-
persisted source tables. It does not call any LLM.

Inputs it considers, in this priority order:

1. **Explicit unsigned / unreviewed workflow state** — unsigned
   `chart_artifacts`, scribe sessions in `draft` /
   `ready_for_review` / `reviewed`, patient summaries in `draft` /
   `reviewed`. These produce `sign_unsigned_…`, `review_…`, and
   `finalize_…` prompts.
2. **Finalized patient summaries** — clinical-language scans run
   against the plain-language summary plus the JSON list bodies.
3. **Reviewed/finalized scribe sessions** — clinical-language scans
   run against `source_text`, `draft_note_text`, and the
   `structured_note_json` fields.
4. **Signed retinal artifacts** — clinical-language scans run
   against `title` and `findings_text`.
5. **Recent encounters** — used to gate the pre-visit readiness
   prompts (we only suggest "no signed retinal artifact on file" if
   there is at least one recent encounter to act against).
6. **Pre-visit brief data gaps** — when a patient has no scribe
   sessions, no chart artifacts, and no patient summaries, a single
   `review_pre_visit_data_gaps` prompt is emitted. Richer prompts
   above cover the partial-coverage cases.

Clinical-language scans use narrow regex patterns. False positives
are tolerable — they create noise but never harm — because the
provider always reviews each suggestion before accepting it.

## Source priority for clinical scans

Clinical-language scans only run against **finalized** content:

- finalized patient summaries
- reviewed/finalized scribe sessions
- signed retinal artifacts

Drafts and unsigned content are not scanned. The intent is: only
suggest a clinical-language review when the chart text has already
crossed a provider-review threshold.

## Dedupe behavior

Each candidate suggestion is keyed by
`(action_type, source_type, source_id, title)`. A candidate is
**dropped** if a row with the same key is already in `suggested` or
`accepted` for the same patient. Repeated `POST /generate` calls
therefore do not churn — `created_count` will be zero on the second
call when nothing new has happened.

Items in `dismissed` or `completed` do **not** participate in
dedupe — they are terminal, so a fresh generate may legitimately
re-surface the same suggestion if conditions still warrant it. The
provider may dismiss again.

The response includes `generated_count` (total candidates),
`created_count` (new rows persisted), and `reused_count` (candidates
suppressed by dedupe).

## API

| Method | Path                                                                      | Action            | Required role                    |
|--------|---------------------------------------------------------------------------|-------------------|----------------------------------|
| POST   | `/patients/{patient_id}/provider-action-items/generate`                   | run generator     | `admin`, `clinician`             |
| GET    | `/patients/{patient_id}/provider-action-items`                            | list (filterable) | `admin`, `clinician`, `reviewer` |
| GET    | `/patients/{patient_id}/provider-action-items/{action_id}`                | detail            | `admin`, `clinician`, `reviewer` |
| POST   | `/patients/{patient_id}/provider-action-items/{action_id}/accept`         | suggested → accepted | `admin`, `clinician`             |
| POST   | `/patients/{patient_id}/provider-action-items/{action_id}/dismiss`        | non-terminal → dismissed | `admin`, `clinician`     |
| POST   | `/patients/{patient_id}/provider-action-items/{action_id}/complete`       | accepted → completed | `admin`, `clinician`             |

`reviewer` is read-only here (matches the read-only convention on
patient summaries and scribe sessions). Write attempts return
`403 role_forbidden`.

### List filters

The list route accepts optional query parameters:

- `status` — one of `suggested`, `accepted`, `dismissed`, `completed`
- `priority` — one of `low`, `medium`, `high`
- `action_type` — any value from the closed vocabulary
- `encounter_id` — integer

An unknown `status`, `priority`, or `action_type` returns
`400 invalid_<filter>_filter`.

### Error codes

| Code                                  | HTTP | Meaning                                              |
|---------------------------------------|------|------------------------------------------------------|
| `patient_not_found`                   | 404  | Patient not in caller's org                          |
| `provider_action_item_not_found`      | 404  | Action item not in caller's org / patient            |
| `provider_action_item_immutable`      | 409  | Mutation attempted on dismissed/completed            |
| `provider_action_invalid_transition`  | 409  | Action illegal from current status                   |
| `role_forbidden`                      | 403  | Caller's role cannot perform this action             |
| `invalid_status_filter`               | 400  | Unknown `status` query value                         |
| `invalid_priority_filter`             | 400  | Unknown `priority` query value                       |
| `invalid_action_type_filter`          | 400  | Unknown `action_type` query value                    |

## RBAC and org isolation

- Patient is resolved inside the caller's org first; cross-org
  returns `404 patient_not_found` (no existence leak).
- `get_action_item` filters by `(organization_id, patient_id)` so
  an action_id from another org or another patient looks like
  `404 provider_action_item_not_found`.
- Every per-source SELECT (encounters, scribe_sessions,
  chart_artifacts, patient_summaries) re-filters by
  `organization_id` for defense in depth.

## Audit / PHI safety

Audit event types:

- `provider_action_items_generated` (POST `/generate`)
- `provider_action_item_accepted` (POST `/accept`)
- `provider_action_item_dismissed` (POST `/dismiss`)
- `provider_action_item_completed` (POST `/complete`)

The `detail` column is metadata-only.

For `provider_action_items_generated`:

```
patient_id=<id> batch_id=<hex> generated_count=<n> created_count=<n> reused_count=<n>
```

For per-item events:

```
action_id=<id> patient_id=<id> encounter_id=<id|None> action_type=<type>
priority=<level> status=<state> source_type=<str|None> source_id=<id|None>
```

The audit `detail` **never includes**:

- `title`
- `reason`
- the source row's clinical body (findings_text, source_text,
  draft_note_text, structured_note_json, plain_language_summary,
  key_findings, next_steps, questions, limitations notice, review notes,
  pre-visit brief section bodies)

Sentinel-token regression tests assert this for every event type
and for clinical-source body content.

GET `/list` and GET `/{action_id}` are read-only and emit no audit
events (consistent with the read side of patient_summaries and
scribe_sessions).

## Provider review requirement

The panel always renders the provider-review notice:

> Provider action suggestions — review required. ChartNav does not
> create orders, send referrals, message patients, or take action
> automatically.

Action buttons are gated on status:

- `suggested` → `Accept`, `Dismiss`
- `accepted` → `Complete`, `Dismiss`
- `dismissed` / `completed` → read-only

The panel intentionally exposes no order, coding, referral, or
patient-message control.

## Limitations (v1)

- The clinical-language scan vocabulary is small and ophthalmology-
  flavored. False negatives are expected; the provider should not
  rely on the queue as a primary safety net.
- Suggestions are scoped to one patient. There is no team queue or
  cross-patient triage.
- Dismissal is per-occurrence — dismissing one suggestion does not
  silence future re-emissions of the same suggestion if it
  legitimately re-fires after data changes.
- The queue does not propose specialty-specific risk scores or
  longitudinal trend analytics.
- The queue does not write back to any source table — it never
  signs an artifact, finalizes a session, or finalizes a summary on
  the provider's behalf.

## Deferred

- **Actual order creation** — out of scope and explicitly forbidden
  for this surface.
- **Referral submission** — out of scope.
- **Billing / coding workflows** — out of scope.
- **Patient messaging / portal delivery** — out of scope.
- **Specialty-specific risk scoring** — deferred.
- **External LLM reasoning** — deferred. v1 is deterministic
  regex/aggregation only.
- **Task assignment / team queues** — deferred.
- **EHR task sync** — deferred.
