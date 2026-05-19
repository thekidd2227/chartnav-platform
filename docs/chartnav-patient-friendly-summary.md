# ChartNav Patient-Friendly Summary (Phase 9)

Phase 9 introduces a provider-reviewed, patient-friendly summary
artifact. It is generated **for** the provider, edited and reviewed
**by** the provider, and finalized **by** the provider. The endpoint
never sends anything to a patient — patient delivery is explicitly
deferred to a later phase.

This document is the contract: lifecycle, generator rules, RBAC,
audit safety, organization isolation, error codes, and the list of
non-goals.

## Storage

Single table — `patient_summaries`, owned by Phase 9 and untouched
by any earlier phase.

| Column                | Type      | Notes                                              |
|-----------------------|-----------|----------------------------------------------------|
| `id`                  | INTEGER   | PK                                                 |
| `organization_id`     | INTEGER   | FK → `organizations.id`, NOT NULL, indexed         |
| `patient_id`          | INTEGER   | FK → `patients.id`, NOT NULL, indexed              |
| `encounter_id`        | INTEGER   | FK → `encounters.id`, nullable                     |
| `scribe_session_id`   | INTEGER   | FK → `scribe_sessions.id`, nullable, indexed       |
| `created_by_user_id`  | INTEGER   | FK → `users.id`, NOT NULL                          |
| `reviewed_by_user_id` | INTEGER   | FK → `users.id`, nullable                          |
| `status`              | TEXT      | CHECK in (`draft`,`reviewed`,`finalized`,`discarded`) |
| `plain_language_summary` | TEXT   | Patient-readable paragraph                         |
| `key_findings`        | TEXT (JSON) | JSON array of strings, normalized on read       |
| `next_steps`          | TEXT (JSON) | JSON array of strings, normalized on read       |
| `questions`           | TEXT (JSON) | JSON array of strings, normalized on read       |
| `limitations_notice`  | TEXT      | Always present; default explains "draft, may be incomplete" |
| `review_notes`        | TEXT      | Provider-only notes; never sent to patient         |
| `finalized_at`        | TIMESTAMP | nullable                                           |
| `reviewed_at`         | TIMESTAMP | nullable                                           |
| `discarded_at`        | TIMESTAMP | nullable                                           |
| `created_at`          | TIMESTAMP | default now                                        |
| `updated_at`          | TIMESTAMP | default now, bumped on every write                 |

Indexes on `organization_id`, `patient_id`, `encounter_id`,
`scribe_session_id`, and `status`.

## Lifecycle

```
                  +-----+      review       +----------+    finalize    +-----------+
   POST create -->|draft| ----------------> | reviewed | -------------> | finalized |
                  +-----+                   +----------+                +-----------+
                     |   \                       |
                     |    \------- discard ------+----> +-----------+
                     +-------- discard ----------+----> | discarded |
                                                        +-----------+
```

- `draft → reviewed` requires explicit `POST /review`.
- `reviewed → finalized` requires explicit `POST /finalize`.
- `discard` is allowed from `draft` or `reviewed`.
- `finalized` and `discarded` are terminal and immutable.
- Direct `draft → finalize` is rejected with
  `409 patient_summary_invalid_transition`.
- Any mutation against a terminal summary returns
  `409 patient_summary_immutable`.

## Generator (v1, deterministic)

The v1 generator is a **deterministic regex/template** over already-
stored structured note fields. It does **not** call any LLM.

Inputs it considers, in order:

1. If `scribe_session_id` is supplied and that session is
   `finalized`, the generator reads the session's
   `structured_note_json` and `draft_note_text`.
2. If no scribe session is supplied, the generator emits a placeholder
   draft body that says explicitly the provider will fill it in.
3. `provider_instructions` is appended verbatim to the
   `plain_language_summary` body when supplied. It is not interpreted
   as a directive to the engine — only as context the provider wants
   reflected in the draft.

What it produces:

- `plain_language_summary` — a short paragraph composed from the
  chief complaint, plan, and follow-up interval pulled from the
  source structured note (when present).
- `key_findings` — array of plain-language restatements of the
  source's chief complaint and plan items. Empty when no source.
- `next_steps` — array derived from the source's plan and follow-up.
  Empty when no source.
- `questions` — a small fixed set of open-ended prompts the patient
  may want to ask the provider. Always benign and never diagnostic.
- `limitations_notice` — always present; default reads:
  *"This summary is a draft for provider review and may be
  incomplete."*

What the generator never does:

- It never invents a diagnosis the source does not contain.
- It never adds treatment recommendations beyond what the source
  already contains.
- It never alters numeric clinical values (visual acuity, IOP).
- It never claims certainty.
- It never includes provider-internal review notes in the patient-
  facing fields.

## API

All routes are scoped under `/patients/{patient_id}/patient-summaries`.
Patient is resolved inside the caller's organization first; cross-org
returns `404 patient_not_found`.

| Method | Path                               | Action               | Required role        |
|--------|------------------------------------|----------------------|----------------------|
| POST   | `/`                                | create draft         | `admin`, `clinician` |
| GET    | `/`                                | list for patient     | any in-org role      |
| GET    | `/{summary_id}`                    | detail               | any in-org role      |
| PATCH  | `/{summary_id}`                    | edit non-terminal    | `admin`, `clinician` |
| POST   | `/{summary_id}/review`             | draft → reviewed     | `admin`, `clinician` |
| POST   | `/{summary_id}/finalize`           | reviewed → finalized | `admin`, `clinician` |
| POST   | `/{summary_id}/discard`            | non-terminal → discarded | `admin`, `clinician` |

`reviewer` is read-only here (matches the scribe-session contract);
write attempts return `403 role_forbidden`.

### Error codes

| Code                                     | HTTP | Meaning                                             |
|------------------------------------------|------|-----------------------------------------------------|
| `patient_not_found`                      | 404  | Patient not in caller's org (also covers cross-org) |
| `encounter_not_found`                    | 404  | Encounter not in caller's org                       |
| `patient_encounter_mismatch`             | 400  | Encounter belongs to a different patient            |
| `patient_summary_not_found`              | 404  | Summary not in caller's org / patient               |
| `scribe_session_not_found`               | 404  | Scribe session in another org or another patient    |
| `patient_summary_immutable`              | 409  | Mutation attempted on `finalized` or `discarded`    |
| `patient_summary_invalid_transition`     | 409  | Action illegal from current status                  |
| `role_forbidden`                         | 403  | Caller's role cannot write summaries                |

## Audit safety

Every mutation emits a `patient_summary_*` event into
`security_audit_events`. The `event_type` values are:

- `patient_summary_created`
- `patient_summary_updated`
- `patient_summary_reviewed`
- `patient_summary_finalized`
- `patient_summary_discarded`

The `detail` column is **metadata-only** and contains exactly:

```
summary_id=<id> patient_id=<id> encounter_id=<id|None> scribe_session_id=<id|None> status=<status>
```

Summary body, key findings, next steps, questions, limitations notice,
and review notes are **never** written to the audit log.
Sentinel-token regression tests assert this for every event type.

## Organization isolation

- Patient is resolved inside the caller's organization before any
  other lookup. Cross-org patient → `404 patient_not_found`.
- Cross-org `encounter_id` → `404 encounter_not_found`.
- Cross-org or cross-patient `scribe_session_id` → raised internally
  as `PatientSummarySourceMismatch` and translated to
  `404 scribe_session_not_found` to avoid leaking that the session
  exists at all in another org.
- List/detail/get always join on `organization_id` so existence
  leakage across orgs is impossible at the DB layer too.

## Frontend (PatientSummaryPanel)

`apps/web/src/PatientSummaryPanel.tsx` mounts in
`apps/web/src/NoteWorkspace.tsx` for any numeric `patientId`. It:

- Lists existing summaries with status badges.
- Opens an editor for the selected summary, or a "new draft" form.
- The new-draft form accepts an optional source scribe session id and
  optional provider instructions; it prefills `encounter_id` from the
  workspace.
- The editor exposes `plain_language_summary`, `key_findings`,
  `next_steps`, `questions`, `limitations_notice`, and `review_notes`
  as editable fields (one item per line for the array fields).
- Action buttons are gated on status: `draft` shows save / mark
  reviewed / discard; `reviewed` shows save / finalize / discard;
  `finalized` and `discarded` show no actions and disable the
  textareas.
- Banner copy: *"Patient summary draft — provider review required.
  Do not send to patient until finalized by the provider."*
- There is **no** patient-send action on the panel.

## Non-goals (Phase 9)

- **No autonomous diagnosis.** The generator never invents a finding,
  diagnosis, severity, or recommendation.
- **No external LLM call.** The v1 generator is deterministic regex
  over already-stored structured note text.
- **No patient delivery.** The endpoint never sends to a patient. The
  panel renders no email / SMS / portal / PDF action.
- **No automatic write into `chart_artifacts` or `scribe_sessions`.**
  Patient summaries are a separate artifact.
- **No edits to retinal, scribe, or chart_artifacts schemas.** Phase 9
  ships exactly one new migration: `patient_summaries`.
