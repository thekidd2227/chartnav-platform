# ChartNav Patient Chart Foundation

This doc describes the **persistence shell** for retinal diagram
artifacts that ships with the `feature/retinal-artifact-persistence-shell`
branch. It is intentionally narrow: storage, identity, versioning,
signing, RBAC, and audit redaction.

## Scope

This is **not** the final clinical drawing tool, **not** the AI proposal
generator, and **not** the apply/reject workflow. The goal is to land
the smallest credible foundation that other surfaces can build on
without re-litigating data shape later.

| In | Out |
|---|---|
| `chart_artifacts` table | OD/OS clinical drawing canvas widget |
| `/patients/{id}/eye-diagrams` CRUD + sign | Speech / dictation filter |
| Versioning + parent/fork on signed-edit | AI-proposed annotations |
| Org/RBAC/audit redaction | Provider apply/reject workflow |
| JSON drawing payload (any object) | `source=ai_approved` provenance |
| Minimal JSON-shell UI panel | Marketing site / docs export |

## Backend

### Migration

`apps/api/alembic/versions/e1f2a3041507_chart_artifacts.py` creates the
`chart_artifacts` table.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `created_at`, `updated_at` | TIMESTAMP | server default `CURRENT_TIMESTAMP` |
| `organization_id` | INTEGER FK | `organizations.id`; required |
| `patient_id` | INTEGER FK | `patients.id`; required |
| `encounter_id` | INTEGER FK | `encounters.id`; nullable |
| `created_by_user_id` | INTEGER FK | `users.id` |
| `artifact_type` | VARCHAR(64) | only `retinal_diagram` ships in this PR |
| `title` | VARCHAR(255) | optional |
| `findings_text` | TEXT | provider note; **never logged in audit** |
| `drawing_json` | TEXT | JSON-encoded; **never logged in audit** |
| `version_number` | INTEGER | starts at 1 |
| `parent_artifact_id` | INTEGER FK | self-reference; set on forks |
| `signed_at` | TIMESTAMP | nullable |
| `signed_by_user_id` | INTEGER FK | nullable |

Indexes on `(organization_id, patient_id)`, `(organization_id, encounter_id)`,
`(parent_artifact_id)`, and `(organization_id, artifact_type, created_at)`.

`drawing_json` is a `TEXT` column with JSON content (same pattern as
`ai_governance_log.security_events`) — portable across SQLite and
Postgres without native-JSON dialect dependencies.

### Endpoints

All under `/patients/{patient_id}/eye-diagrams`. The patient is resolved
inside the caller's organization first; cross-org access returns
**404 `patient_not_found`** (no existence leak).

| Method | Path | Notes |
|---|---|---|
| `GET` | `/` | list artifacts for patient (most recent first) |
| `GET` | `/{artifact_id}` | fetch one |
| `POST` | `/` | create new artifact (version 1, unsigned) |
| `PATCH` | `/{artifact_id}` | update unsigned in place |
| `PATCH` | `/{artifact_id}?fork=true` | edit a signed artifact → new version |
| `POST` | `/{artifact_id}/sign` | stamp `signed_at`/`signed_by_user_id` |

### Versioning + signing rules

- **Create**: `version_number = 1`, `parent_artifact_id = null`, unsigned.
- **Update unsigned in place**: refreshes `updated_at`. Same id.
- **Sign**: stamps `signed_at` and `signed_by_user_id`. Becomes immutable.
- **Edit signed without `?fork=true`**: HTTP **409 `artifact_signed_immutable`**.
- **Edit signed with `?fork=true`**: insert a new row whose
  `parent_artifact_id` is the original id and `version_number =
  parent.version_number + 1`. The fork starts unsigned. Fields not
  supplied in the patch are inherited from the parent.
- **Re-sign already signed**: HTTP **409 `artifact_already_signed`**.

### RBAC

Routes use `require_caller` and check role inside the handler — same
pattern as `/patients`:

| Action | admin | clinician | reviewer |
|---|---|---|---|
| List / detail | ✓ | ✓ | ✓ |
| Create | ✓ | ✓ | ✗ `role_forbidden` |
| Update | ✓ | ✓ | ✗ `role_forbidden` |
| Sign | ✓ | ✓ | ✗ `role_forbidden` |
| Cross-org any action | 404 `patient_not_found` |

Reviewers are read-only on this surface. Sign authority belongs to the
clinician who created the artifact (mirrors how clinicians sign their
own encounter notes today).

### Audit safety

Every create / update / fork / sign emits a row to `security_audit_events`
via `app.audit.record(...)`:

- `event_type` ∈ {`eye_diagram_created`, `eye_diagram_updated`,
  `eye_diagram_forked`, `eye_diagram_signed`}
- `detail` is **metadata only**: `artifact_id=N version=N parent=N|None signed=bool`
- **No `findings_text`. No `drawing_json`.** A regression test
  (`TestAuditDoesNotLogClinicalContent`) asserts neither appears in
  any audit row's `detail` after create/update/sign.

## Frontend

### API client (`apps/web/src/api.ts`)

```ts
listPatientEyeDiagrams(email, patientId)
getPatientEyeDiagram(email, patientId, artifactId)
createPatientEyeDiagram(email, patientId, input)
updatePatientEyeDiagram(email, patientId, artifactId, input, { fork? })
signPatientEyeDiagram(email, patientId, artifactId)
```

Types: `EyeDiagramArtifact`, `EyeDiagramListResponse`,
`EyeDiagramCreateInput`, `EyeDiagramUpdateInput`. `drawing_json` is
typed as `Record<string, unknown>` so any structured payload round-trips.

### UI (`apps/web/src/EyeDiagramPanel.tsx`)

Embedded inside `NoteWorkspace.tsx` and gated on the encounter having a
numeric `patient_id` (FHIR-bridged encounters with no native patient
row hide the panel). The panel:

- Lists saved retinal diagrams for the patient
- Loads any artifact and restores `title`, `findings`, and
  `drawing_json` (rendered as pretty-printed JSON in a textarea)
- Saves a new artifact, updates an unsigned one in place, or signs
- Detects signed artifacts on load and replaces the "Save / Sign"
  buttons with a "Save as new version" (fork) button + an inline
  warning that explains the fork semantics
- Surfaces version number, parent linkage, signed status, and
  `created_at` / `updated_at` for whichever artifact is loaded

This is a **persistence shell**: the drawing payload is edited as raw
JSON. The clinical drawing canvas is a follow-up.

## Phase 5B — OD/OS retinal drawing canvas

The persistence shell's JSON textarea is replaced by a real SVG
drawing surface. **No backend or storage contract changes.** The
canvas saves and loads through the same `/patients/{id}/eye-diagrams`
routes; the new content lives entirely inside `drawing_json` under a
versioned, structured schema.

### `drawing_json` schema (v1)

```jsonc
{
  "schema_version": 1,
  "canvas_type": "retinal_diagram",
  "annotations": [
    {
      "id": "a_<timestamp>_<n>",
      "kind": "symbol" | "freehand" | "text",
      "eye": "OD" | "OS",
      "x": 0.42,           // normalized 0..1 within the eye pane
      "y": 0.58,
      "color": "#c1121f",
      "source": "manual",  // reserved; AI proposals will populate later
      "created_at": "<iso8601>",

      // kind === "symbol":
      "symbol_type": "drusen" | "dot_blot_hemorrhage" | ...,
      "label": "<optional>",

      // kind === "freehand":
      "points": [{ "x": 0.4, "y": 0.5 }, ...],

      // kind === "text":
      "text": "<provider label>"
    }
  ]
}
```

Coordinates are **normalized 0..1** per eye pane so resizing the SVG
never breaks position. The `source` field is reserved — every
annotation in this PR is `"manual"`. AI-proposed annotations will land
later under a different `source` value without a schema bump.

### Symbol library v1

13 ophthalmology symbols ship in this PR (see
`apps/web/src/retinalAnnotations.ts` `SYMBOL_LIBRARY`):

drusen · dot/blot hemorrhage · flame hemorrhage · microaneurysm ·
hard exudates · cotton-wool spot · neovascularization · retinal tear ·
retinal detachment · laser/scar · disc pallor · RPE change ·
lattice degeneration

Severity selection (mild / moderate / severe) is **not** in this PR —
the `severity` field stays reserved.

### Tools

- Select / freehand / text label (the three primary modes)
- 13-button symbol palette
- Color picker
- Undo / redo (whole-state snapshots, capped at **50** entries)
- Move selected annotation by dragging in select mode
- Delete selected
- Clear current eye / clear all

### Findings auto-summary

The findings textarea is updated automatically as the canvas changes,
but **only inside a fenced block**:

```
<!-- retinal-auto-summary:start -->
Retinal diagram auto-summary:
OD: drusen near macula
OS: flame hemorrhage superior
<!-- retinal-auto-summary:end -->
```

Provider text **outside** these markers is never modified. If the
fence is missing, a fresh block is appended. If present, only the
content between the markers is replaced. The summary respects rough
zone names (superior / inferior / nasal / temporal / near macula)
based on the normalized coordinates, and merges duplicates with `×N`
counts.

### Signed / fork behavior

- A signed artifact loads in **read-only** mode: the toolbar is
  hidden, pointer events on the canvas are ignored, and an inline
  note explains how to amend.
- The button strip below the canvas swaps to **"Save as new version"**.
- Saving issues `PATCH /patients/{id}/eye-diagrams/{id}?fork=true`,
  which the existing backend turns into a new unsigned row whose
  `parent_artifact_id` is the original. No backend behavior change.

### Legacy payload handling

When a Phase-5A persistence-shell artifact (any non-`schema_version: 1`
shape) is loaded, the canvas mounts empty and surfaces a small inline
note: *"This artifact was saved before the drawing canvas existed."*
The original `drawing_json` is preserved on the server until the user
saves new canvas content. This keeps the rollout safe; we never
silently destroy a legacy payload.

### What's still deferred

- AI-proposed annotations (consumer of the same `drawing_json`)
- Provider apply/reject workflow + `source: "ai_approved"`
- Clinical speech / signal filter
- Rendered snapshot or PDF export of the signed diagram
- Symbol library expansion beyond v1
- Severity UI for symbols

All of those continue to ride on the same `chart_artifacts` table and
the same `drawing_json` schema — no migration needed when they land.

## Phase 6 — findings → diagram proposals (deterministic, with provider review)

The first AI-assisted clinical workflow on top of the canvas. **No
external LLM in this PR.** The proposal engine is deterministic and
rule-based; it lives in `apps/api/app/services/retinal_proposals.py`.
**Zero schema changes** — proposals never touch the database directly,
and applied annotations ride on the same `drawing_json` schema with an
extended (additive, optional) annotation shape.

### Endpoint

```
POST /patients/{patient_id}/eye-diagrams/propose-from-findings
```

Request:

```jsonc
{
  "findings_text": "OD drusen at macula. OS flame hemorrhage superior.",
  "drawing_json": { ... }   // optional, currently unused by the parser
}
```

Response:

```jsonc
{
  "clinical_text": "...",
  "ignored_chatter": [...],
  "uncertain_phrases": [...],
  "proposed_annotations": [
    {
      "proposal_id": "p_<sha256-16>",
      "kind": "symbol",
      "symbol_type": "drusen",
      "eye": "OD",
      "x": 0.5, "y": 0.5,
      "zone": "macula",
      "text": "OD drusen at macula",
      "color": "#c1121f",
      "confidence": 0.85,
      "confidence_band": "high" | "medium" | "low",
      "source_phrase": "OD drusen at macula",
      "source_start": 0, "source_end": 19,
      "reason": "matched finding=drusen + eye=OD + zone=macula",
      "missing_flags": [],
      "source": "ai_proposed"
    }
  ],
  "confidence_summary": { "high": 1, "medium": 0, "low": 0, "needs_review": true },
  "missing_flags": [
    { "code": "missing_laterality", "detail": "...", "source_phrase": "...", "source_start": 0, "source_end": 17 }
  ]
}
```

Rules enforced in the engine:

- **No DB writes.** The endpoint is read-only on the data side.
- **Stable proposal IDs.** `proposal_id = "p_" + sha256(normalized_phrase + finding + eye + zone)[:16]`. Same input ⇒ same id.
- **Missing laterality ⇒ no auto-placement.** A `missing_laterality` flag is emitted instead so the UI can show the provider what to clarify.
- **OU / bilateral / both eyes ⇒ two proposals** (OD + OS) with distinct ids.
- **Chatter is ignored** (greetings, filler) and surfaced separately in `ignored_chatter`.
- **Unknown clinical-sounding phrases ⇒ `uncertain_phrases`**, never an auto-proposal.
- **Coordinate convention matches `RetinalDrawingCanvas.tsx`:**
  - OD: optic disc on the right (x > 0.5); nasal = right, temporal = left.
  - OS: optic disc on the left (x < 0.5); nasal = left, temporal = right.
  - Superior is y < 0.5; inferior is y > 0.5; eye-independent.

### Supported v1

- **Findings** (13): drusen, dot/blot hemorrhage, flame hemorrhage,
  microaneurysm, hard exudates, cotton-wool spot, neovascularization,
  retinal tear/hole, retinal detachment, laser/scar, disc pallor,
  RPE change, lattice degeneration.
- **Laterality**: `OD`, `OS`, `OU`, `right eye`, `left eye`, `bilateral`,
  `bilaterally`, `both eyes`.
- **Zones**: macula, optic disc, superior, inferior, nasal, temporal,
  superior temporal / superotemporal, superior nasal / superonasal,
  inferior temporal / inferotemporal, inferior nasal / inferonasal,
  periphery.

### RBAC + org isolation

- **Admin + clinician only.** Reviewers are denied (`role_forbidden`).
  Even though the data layer is read-only, this endpoint produces
  clinical suggestions and follows write-like access.
- **Patient resolved inside the caller's org first.** Cross-org
  patient ids return **404 `patient_not_found`** (no existence leak).

### Audit safety

A single `eye_diagram_proposed` row is written to
`security_audit_events` per request. The detail string is
**metadata-only** — `patient_id`, `proposal_count`, `uncertain_count`,
`missing_flag_count`. The raw `findings_text` and proposal bodies are
**never** written to the audit log. Sentinel-token regression test
asserts neither leaks.

### Apply / reject lifecycle

- The proposal review panel (`apps/web/src/RetinalProposalReview.tsx`)
  surfaces every proposal with its source phrase, reason, confidence
  band, and missing flags.
- "Apply" inserts a fresh annotation into the working
  `DrawingDocument` with:
  - `source: "ai_approved"`
  - `proposal_id` retained for traceability
  - `source_phrase`, `confidence`, `reason` carried as optional fields
- "Reject" updates only transient UI state. Rejected proposals never
  reach `onApply`, never enter `drawing_json`, and never persist on
  save.
- "Apply remaining" / "Reject remaining" act only on still-pending
  proposals — already-applied ones are not re-applied.
- The **"Generate diagram proposals from findings"** button is
  disabled when `findings_text` is empty and **hidden** when the
  artifact is signed (the canvas is read-only there; provider must
  fork via "Save as new version" first).

### Annotation schema additions (additive, no `schema_version` bump)

The `Annotation` type gains four optional fields and a second source
value. Existing v1 documents and tests are unaffected:

```ts
type AnnotationSource = "manual" | "ai_approved";

interface BaseAnnotation {
  // ...existing fields...
  source: AnnotationSource;
  proposal_id?: string;
  source_phrase?: string;
  confidence?: number;
  reason?: string;
}
```

### Validation

- **Backend:** 27 new tests in `tests/test_retinal_proposals.py`
  covering laterality detection, zones, OU expansion, chatter,
  uncertain phrases, missing flags, stable ids, coordinate convention,
  RBAC, cross-org 404, no-DB-write, and audit redaction (sentinel
  tokens absent).
- **Frontend:** 7 specs for `RetinalProposalReview`, plus 4 new
  panel-flow specs in `EyeDiagramPanel.test.tsx` covering apply
  persistence, reject non-persistence, mixed manual + applied save
  payloads, and signed-artifact behavior.

### Limitations / explicit non-claims

- ❌ Not autonomous diagnosis. Every proposal requires explicit
  provider apply.
- ❌ No external LLM. The parser is deterministic regex over a closed
  vocabulary; phrasing outside that vocabulary lands in
  `uncertain_phrases`.
- ❌ No automatic charting. Applied proposals enter the in-memory
  document; the artifact is persisted only when the provider clicks
  Save / Save as new version.
- ❌ No orders, no e-prescribing, no coding side effects.
- ❌ Parser will miss unfamiliar phrasing. Provider must verify the
  diagram against their own findings text — that's the job, not a bug.

## Future phases (still deferred)

1. **Clinical speech filter** — filter dictated text into clinical
   findings before it reaches the artifact.
2. **External LLM proposal source** — same review-required contract,
   different producer.
3. **Severity UI for symbols** (mild / moderate / severe).
4. **Symbol library v2** — broader ophthalmology coverage.
5. **Rendered snapshot / PDF export** of signed diagrams.

Each rides on the same `chart_artifacts` table, the same `drawing_json`
schema (additive), and the same `eye_diagram_*` audit event family.

## Phase 8 — AI scribe session lifecycle

The scribe session lifecycle introduces an explicit unit of work
between provider source/transcript text and a finalized clinical
artifact. **Zero retinal-side changes.** Phase 8 lives entirely in
its own table (`scribe_sessions`), its own routes
(`/patients/{id}/scribe-sessions/...`), and its own panel
(`ScribeSessionPanel.tsx`).

**Lifecycle states:** `draft` → `processing` → `ready_for_review` →
`reviewed` → `finalized`, plus `discarded` reachable from any
non-terminal state. `finalized` and `discarded` are immutable.

**Provider review is mandatory.** No state can reach `finalized`
without an explicit `review` action followed by an explicit `finalize`
action. The processing engine is deterministic regex over a closed
heading vocabulary; the rendered draft always begins with
`Draft — provider review required`. Audit detail is metadata-only —
`source_text`, `transcript_text`, `draft_note_text`,
`structured_note_json`, and `review_notes` never appear in
`security_audit_events.detail`. Sentinel-token regression tests
assert this for every event type.

**Linkage to retinal artifacts** is opt-in via the
`scribe_sessions.linked_artifact_id` foreign key into
`chart_artifacts`. Finalizing a scribe session does **not** write into
`chart_artifacts` — that's a separate explicit action that lives in a
later phase.

See `docs/chartnav-scribe-session-lifecycle.md` for the full lifecycle
contract, transition matrix, RBAC, audit safety, and limitations.

## Phase 9 — provider-reviewed patient-friendly summaries

Phase 9 adds a provider-facing surface for drafting plain-language
summaries that a clinician can review, finalize, or discard. **Zero
retinal-side changes. Zero scribe-session-side changes.** Phase 9 lives
entirely in its own table (`patient_summaries`), its own routes
(`/patients/{id}/patient-summaries/...`), and its own panel
(`PatientSummaryPanel.tsx`).

**Lifecycle states:** `draft` → `reviewed` → `finalized`, plus
`discarded` reachable from `draft` or `reviewed`. `finalized` and
`discarded` are immutable; `update`, `review`, `finalize`, and
`discard` from a terminal state return `409 patient_summary_immutable`.
Direct `draft → finalize` is rejected with
`409 patient_summary_invalid_transition`.

**Provider review is mandatory.** A summary cannot reach `finalized`
without an explicit `review` step. The v1 generator is deterministic
— it composes plain-language paragraphs from already-stored structured
note fields (chief complaint, plan, follow-up) when seeded from a
finalized scribe session, and falls back to a placeholder draft when
no source is provided. **It never invents diagnoses, never adds
treatment recommendations beyond what the source already contains,
and always includes a limitations notice** that the draft is
incomplete and requires provider review.

**Patient delivery is explicitly deferred.** The endpoint never sends
anything to a patient. The panel renders no patient-send action
(no email, no SMS, no portal push, no PDF export). Banner copy on
the panel reads: *"Patient summary draft — provider review required.
Do not send to patient until finalized by the provider."*

**Org isolation:** patient is resolved inside the caller's
organization first; cross-org returns
`404 patient_not_found` (no existence leak). A `scribe_session_id`
that exists but in a different org or for a different patient
returns `404 scribe_session_not_found` to avoid existence leakage of
sessions in other orgs.

**RBAC:** `admin` and `clinician` can write (`create`, `update`,
`review`, `finalize`, `discard`). `reviewer` is read-only on this
surface (matches the scribe-session contract). Read access still
requires the caller to be in the same org as the patient.

**Audit:** every mutation emits a `patient_summary_*` event whose
`detail` is metadata-only — `summary_id`, `patient_id`, `encounter_id`,
`scribe_session_id`, and `status`. Summary body, key findings,
next steps, questions, limitations notice, and review notes are
**never** written to `security_audit_events`. Sentinel-token
regression tests assert this for every event type.

See `docs/chartnav-patient-friendly-summary.md` for the full
generator rules, transition matrix, RBAC, audit safety, and the
list of explicit non-goals.

## Phase 10 — provider-facing pre-visit clinical brief

Phase 10 adds a **provider-facing pre-visit brief**: a deterministic,
on-demand summary of the existing ChartNav chart for one patient
that a clinician can review before the visit. **Zero new tables.
Zero new migrations.** Phase 10 lives entirely in its own service
(`apps/api/app/services/pre_visit_briefs.py`), its own routes
(`/patients/{id}/pre-visit-brief...`), and its own panel
(`PreVisitBriefPanel.tsx`).

**Lifecycle:** none. The brief is computed on each call from the
existing source tables (encounters, workflow_events, scribe_sessions,
chart_artifacts, patient_summaries) and never stored. Two routes:

- `POST /patients/{id}/pre-visit-briefs/generate` — explicit, audited
  generation. Emits `pre_visit_brief_generated` with metadata-only
  detail (patient_id, source_counts, generated_at).
- `GET /patients/{id}/pre-visit-brief` — read-only on-demand
  recompute. Not audited (consistent with read-side of
  patient_summaries / scribe_sessions).

**Source priority:** finalized patient summaries → reviewed/finalized
scribe sessions → signed retinal artifacts → recent encounters →
workflow events.

**Generator is fully deterministic.** No LLM, no autonomous diagnosis,
no treatment recommendations beyond source content, no orders, no
coding, no patient-side delivery. Section excerpts are truncated to
fixed character limits; `active_issues` are pulled verbatim from
already-finalized chart fields and deduplicated case-insensitively.
A constant `PROVIDER_REVIEW_NOTICE` is included in every response.

**`data_gaps` is explicit.** Missing or weakly-populated sources are
listed by name (e.g., "No signed retinal artifacts on file…"). The
brief tells the provider what is *not* in the chart, not what
clinically *should* be.

**`source_counts` is metadata only.** The eight integer counts that
describe the brief's inputs are also encoded into the audit detail
field — they are the only body-derived information that ever reaches
the audit log.

**Org isolation:** patient is resolved inside the caller's
organization first; cross-org returns `404 patient_not_found` (no
existence leak). Every per-source SELECT re-filters by
`organization_id` for defense in depth.

**RBAC:** `admin` + `clinician` can both POST and GET. `reviewer` is
read-only on this surface (GET allowed; POST → `403 role_forbidden`).

**Audit:** every generation emits a `pre_visit_brief_generated`
event with metadata-only `detail`. `last_visit_summary`,
`active_issues`, retinal/scribe excerpts, patient summary excerpts,
`pending_items`, `suggested_review_items`, and `data_gaps` body
strings are **never** written to `security_audit_events`.
Sentinel-token regression tests assert this for every section body.

See `docs/chartnav-pre-visit-brief.md` for the full contract,
including the response shape, generator rules, source priority,
data-gap behavior, RBAC, audit safety, and the explicit deferred-work
list.

## Phase 11 — provider action review queue

Phase 11 adds a **persisted, provider-reviewable action queue**.
ChartNav surfaces deterministic review tasks from existing chart
records; the provider explicitly Accepts, Dismisses, or Completes
each one. ChartNav itself **never** creates orders, sends referrals,
posts billing or coding entries, messages patients, or takes any
clinical action.

Phase 11 lives in its own table (`provider_action_items`), its own
service (`apps/api/app/services/provider_action_items.py`), its own
routes (`/patients/{id}/provider-action-items/...`), and its own
panel (`ProviderActionItemsPanel.tsx`). Single new migration:
`b3c4d5e6f7a8`. **Zero changes** to retinal, EyeDiagram,
chart_artifacts, scribe_sessions, patient_summaries, or pre_visit
schemas — Phase 11 reads them but never writes.

**Lifecycle states:** `suggested → accepted → completed`, plus
`dismissed` reachable from `suggested` or `accepted`. `dismissed`
and `completed` are immutable. Direct `suggested → completed` is
rejected with `409 provider_action_invalid_transition`.

**Action-type vocabulary is closed.** The service rejects any
`action_type` outside the explicit set, which keeps the queue in
review-prompt territory: every type begins with `review_`,
`finalize_`, `sign_`, or `reconcile_`. There is no order, coding,
referral, prescribe, or message type, and there cannot be one
without a code change to the closed enum.

**Generator is deterministic.** No LLM. Inputs in priority order:
explicit unsigned/unreviewed workflow state, finalized patient
summaries, reviewed/finalized scribe sessions, signed retinal
artifacts, recent encounters, and pre-visit data gaps. Clinical-
language scans run only against finalized chart text (signed
artifacts, finalized summaries, reviewed/finalized scribe sessions).
Drafts and unsigned content are not scanned.

**Dedupe** keys on
`(action_type, source_type, source_id, title)`. Repeated generates
do not churn while a prior suggestion is still in `suggested` or
`accepted`. The response reports `generated_count`,
`created_count`, and `reused_count`.

**Org isolation** is patient-resolved-first; cross-org returns
`404 patient_not_found`. Every per-source SELECT re-filters by
`organization_id` for defense in depth.

**RBAC:** `admin` and `clinician` can generate / accept / dismiss /
complete. `reviewer` is read-only.

**Audit:** four metadata-only event types
(`provider_action_items_generated`,
`provider_action_item_accepted`,
`provider_action_item_dismissed`,
`provider_action_item_completed`). The `title` and `reason` columns
and any source clinical body are **never** written to
`security_audit_events`. Sentinel-token regression tests assert this.

See `docs/chartnav-provider-action-review-queue.md` for the full
contract, including the closed action-type vocabulary, lifecycle
matrix, source priority, dedupe rules, audit detail format, and the
explicit deferred-work list.

## Phase 12 — end-to-end clinical workflow smoke review

Phase 12 is a hardening / verification pass, **not** a new product
surface. It exercises the existing ChartNav clinical workflow across
phases 6 / 8 / 9 / 10 / 11 in a single seeded context (org / user /
patient / encounter) to catch integration cracks, missing wiring,
audit-leak regressions, and unsafe language across module
boundaries.

**No new product surface.** Zero new tables, zero new migrations,
zero new client-facing endpoints, zero new UI panels.

**What Phase 12 adds:**

- 17 backend integration tests in
  `apps/api/tests/test_end_to_end_clinical_workflow.py` covering
  route sanity (every Phase 5B/6/8/9/10/11 list-or-generate route
  registered), the full provider workflow (scribe → propose →
  retinal → summary → brief → actions), end-to-end audit redaction
  with sentinel tokens injected at every clinical-body field,
  end-to-end org isolation, end-to-end safety-language scan over
  service-emitted strings, and reviewer read-only RBAC.
- 7 frontend smoke tests in
  `apps/web/src/test/ClinicalWorkflowSmoke.test.tsx` covering
  workspace mount of all five clinical panels, panel safety copy,
  full mocked-API workflow drive, no-forbidden-button assertions,
  no autonomous-diagnosis or external-LLM language, and
  safe-error banner behavior.
- 1 Playwright e2e smoke in
  `apps/web/tests/e2e/clinical-workflow-smoke.spec.ts` confirming
  the panels mount on a real seeded encounter and the safety copy
  renders against the live stack.

**Safety-language scan.** A reproducible grep across every clinical
panel and every service/route module returned four matches — all
classified as safe negative assertions (banner copy or module
docstring saying ChartNav does *not* do the forbidden thing). No
actionable code uses any of the forbidden tokens.

**Documented limitations and follow-ups** live in
`docs/chartnav-end-to-end-clinical-workflow-smoke-review.md`. None
block this phase merging.

See that document for the full coverage map, audit-redaction
methodology, and follow-up recommendations.

## Phase 13 — demo-ready clinical workflow package

Phase 13 is a **demo-packaging phase**, not a new product surface.
Its only goal is to make the existing ChartNav clinical workflow
understandable in five minutes by a buyer, pilot user, advisor, or
investor — without misrepresenting what the product does.

**No new clinical automation. No new schema. No new API surface.
No backend changes.** Phase 13 ships:

- a small collapsible in-app guide (`DemoClinicalWorkflowGuide`)
  mounted at the top of the workspace's panel stack, collapsed by
  default; expands to a seven-step checklist with safety copy;
  references the demo script;
- a 5-minute and 10-minute demo script, an exact click-path doc,
  and a video shot list under `docs/demo/`;
- this Phase 13 contract document at
  `docs/chartnav-demo-ready-clinical-workflow-package.md`;
- this section.

**Demo data policy.** No backend demo seed is added. The demo
reuses the existing fake seed (`demo-eye-clinic` org, patient
`PT-1001` Morgan Lee, encounter 1) which has been demo-flavored
since Phase 0. No real PHI; no new patient names; no new MRNs;
no new DOBs.

**Safety / claims rules** are documented in the Phase 13 contract
doc. The frontend tests assert them against the demo guide; the
existing Phase 12 backend integration test already enforces them
across service-emitted text. Forbidden phrasing includes "HIPAA
compliant," "certified EHR," "autonomous diagnosis," "guaranteed
accuracy," "automatic orders," "submit referral," "billing
automation," and "send patient message"; allowed phrasing is the
narrow safe-phrase list ("provider-reviewed," "documentation
support," "draft for review," etc.). Negative assertions are
allowed only when they clearly say ChartNav does *not* do the
thing.

**No video files or screenshots are checked into this repo.** The
shot list is editorial only.

See `docs/chartnav-demo-ready-clinical-workflow-package.md` for
the full demo-ready contract, including the documentation map,
audience, demo-data policy, the demo guide's behavior contract,
the safety-language rules, the video clip plan, and the Phase 14
candidate list.
