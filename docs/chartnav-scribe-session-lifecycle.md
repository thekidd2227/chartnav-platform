# ChartNav Scribe Session Lifecycle — Phase 8

This doc describes the AI scribe session lifecycle that ships with the
`feature/scribe-session-lifecycle-a-plus` branch. It is intentionally
narrow: a deterministic processing pipeline with explicit provider
review gates, plus the storage / audit model around it.

## Purpose

A **scribe session** is one row representing a single unit of work
between a provider's source/transcript text and a finalized clinical
artifact. The lifecycle is explicit so we can:

- Keep the engine deterministic in v1 (heading-based parser; no LLM).
- Keep the provider in the loop on every state transition.
- Audit every transition with metadata only — never the clinical
  content itself.

## Lifecycle

| Status              | Meaning                                                    |
|---------------------|------------------------------------------------------------|
| `draft`             | Source/transcript captured; engine has not run.            |
| `processing`        | Reserved for future async processing; v1 transitions through this synchronously when `process` is invoked. |
| `ready_for_review`  | Engine produced a draft note + structured sections.        |
| `reviewed`          | Provider has reviewed; ready to be finalized.              |
| `finalized`         | Immutable. The final clinical state for this session.      |
| `discarded`         | Immutable. Session was discarded before finalize.          |

## Status transition matrix

| Action     | Allowed from                                            | Result              |
|------------|---------------------------------------------------------|---------------------|
| `process`  | `draft`                                                 | `ready_for_review`  |
| `review`   | `ready_for_review`                                      | `reviewed`          |
| `finalize` | `reviewed`                                              | `finalized`         |
| `discard`  | `draft`, `processing`, `ready_for_review`, `reviewed`   | `discarded`         |
| `update`   | any non-terminal status                                 | (in-place)          |

`finalized` and `discarded` are terminal. All mutation actions on a
terminal status return **HTTP 409 `scribe_session_immutable`**. All
other illegal transitions return **HTTP 409 `scribe_session_invalid_transition`**.

## Endpoints

All under `/patients/{patient_id}/scribe-sessions`. The patient is
resolved inside the caller's organization first; cross-org access
returns **404 `patient_not_found`** (no existence leak).

| Method | Path                             | Behavior                        |
|--------|----------------------------------|---------------------------------|
| `POST` | `/`                              | create draft                    |
| `GET`  | `/`                              | list for patient                |
| `GET`  | `/{session_id}`                  | detail                          |
| `PATCH`| `/{session_id}`                  | update non-terminal             |
| `POST` | `/{session_id}/process`          | draft → ready_for_review        |
| `POST` | `/{session_id}/review`           | ready_for_review → reviewed     |
| `POST` | `/{session_id}/finalize`         | reviewed → finalized            |
| `POST` | `/{session_id}/discard`          | non-terminal → discarded        |

## Data model

`scribe_sessions` table (migration `f1a2b3c4d5e6`):

| Column                  | Type                | Notes                                                                                             |
|-------------------------|---------------------|---------------------------------------------------------------------------------------------------|
| `id`                    | INTEGER PK          |                                                                                                   |
| `created_at`            | TIMESTAMP           | server default `CURRENT_TIMESTAMP`                                                                |
| `updated_at`            | TIMESTAMP           | refreshed on every mutation                                                                       |
| `organization_id`       | INTEGER FK          | `organizations.id`; required                                                                      |
| `patient_id`            | INTEGER FK          | `patients.id`; required                                                                           |
| `encounter_id`          | INTEGER FK          | `encounters.id`; nullable. Enforced same-org and (when the encounter row has a numeric `patient_id`) same-patient. |
| `created_by_user_id`    | INTEGER FK          | `users.id`                                                                                        |
| `status`                | VARCHAR(32)         | one of the lifecycle statuses; CHECK-constrained                                                  |
| `input_mode`            | VARCHAR(32)         | `pasted_text` / `transcript` / `audio_placeholder`; CHECK-constrained                             |
| `source_text`           | TEXT (nullable)     | provider input; **never logged in audit**                                                         |
| `transcript_text`       | TEXT (nullable)     | dictation transcript; **never logged in audit**                                                   |
| `draft_note_text`       | TEXT (nullable)     | engine-produced draft; **never logged in audit**                                                  |
| `structured_note_json`  | TEXT (nullable)     | JSON-encoded sections; **never logged in audit**                                                  |
| `linked_artifact_id`    | INTEGER FK          | `chart_artifacts.id`; nullable; same-org check                                                    |
| `review_notes`          | TEXT (nullable)     | reviewer notes; **never logged in audit**                                                         |
| `finalized_at`          | TIMESTAMP (nullable)| set when status becomes `finalized`                                                               |
| `reviewed_at`           | TIMESTAMP (nullable)| set when status becomes `reviewed`                                                                |
| `reviewed_by_user_id`   | INTEGER FK          | `users.id`; set on review                                                                         |
| `discarded_at`          | TIMESTAMP (nullable)| set when status becomes `discarded`                                                               |

Indexes on `(organization_id, encounter_id)`,
`(organization_id, patient_id)`, `(organization_id, status)`,
`(created_by_user_id)`, `(linked_artifact_id)`.

## RBAC

| Action                  | admin | clinician | reviewer |
|-------------------------|-------|-----------|----------|
| List / detail           | ✓     | ✓         | ✓        |
| Create                  | ✓     | ✓         | ✗ `role_forbidden` |
| Update                  | ✓     | ✓         | ✗ `role_forbidden` |
| Process / Review / Finalize / Discard | ✓ | ✓ | ✗ `role_forbidden` |
| Cross-org any action    | 404 `patient_not_found` |

This matches the rest of the patient-chart write surfaces (eye-diagram
artifacts, retinal proposals).

## Audit / PHI safety

Every mutation emits a row to `security_audit_events` via
`app.audit.record(...)`:

- `event_type` ∈ `{scribe_session_created, scribe_session_updated,
  scribe_session_processed, scribe_session_reviewed,
  scribe_session_finalized, scribe_session_discarded}`
- `detail` is **metadata only**:
  `session_id=N patient_id=N encounter_id=N|None status=X linked_artifact_id=N|None`

The audit detail string **never** includes:

- `source_text`
- `transcript_text`
- `draft_note_text`
- the structured note body
- `review_notes`

A regression test plants sentinel tokens in each of those fields and
asserts every audit row's `detail` is free of every sentinel.

## Processing v1

Deterministic regex-based heading parser. Recognized headings
(case-insensitive, line-leading, with `:` or `-` separator):

- `chief complaint` / `chief_complaint` / `cc` → `chief_complaint`
- `hpi`                                       → `hpi`
- `exam`                                      → `exam`
- `assessment`                                → `assessment`
- `plan`                                      → `plan`

Anything outside a known heading lands in `unassigned_text`. The
engine never claims a diagnosis; the rendered draft note always
begins with the explicit banner:

```
Draft — provider review required
```

Frontend treats `Draft — provider review required` as the only
authoritative provenance for the draft note text — there is no
client-side shortcut to finalize without going through `/review` then
`/finalize`.

## Provider review requirement

**No state can reach `finalized` without an explicit `review` action
followed by an explicit `finalize` action**, both performed by an
admin or clinician under the caller's organization. The engine cannot
self-finalize. The frontend does not expose a one-click finalize from
draft. Finalize is intentionally a separate button visible only after
review has succeeded.

## Limitations / explicit non-claims

- ❌ Not autonomous diagnosis. Every transition past `draft` requires
  explicit provider action.
- ❌ No external LLM. Processing v1 is deterministic regex over a
  closed vocabulary; phrasing outside that vocabulary lands in
  `unassigned_text`.
- ❌ No automatic charting. Finalization is metadata-only — it sets
  `finalized_at` and locks the row; it does not write into
  `chart_artifacts`. Linkage to a chart artifact is opt-in via
  `linked_artifact_id`.
- ❌ No orders, no e-prescribing, no coding side effects.
- ❌ Parser will miss unfamiliar phrasing. Provider must verify the
  draft before review/finalize.

## Deferred phases

- Clinical signal filter (transcript denoise / chatter removal at the
  ingest boundary).
- Findings-to-diagram proposals integration (link a finalized scribe
  session to a `chart_artifacts` retinal diagram via
  `linked_artifact_id`).
- Speech-to-text producer for `input_mode=transcript`.
- External LLM summarization variant of the processing engine, behind
  the same review/finalize gates.
- Patient summary export from a finalized session.
- Orders / coding workflows.
