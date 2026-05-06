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

## Phase 14 — pilot readiness / deployment hardening

Phase 14 is a **pilot-readiness / deployment-hardening phase**.
Its only goal is to prepare ChartNav for safe pilot conversations
and controlled-pilot deployment with ophthalmology offices,
without obvious gaps.

**No new clinical automation. No new schema. No new API surface.
No backend code changes.** The PR's `git diff` against
`apps/api/` (excluding `tests/`) is empty.

Phase 14 ships:

- eight new pilot docs under `docs/pilot/` (readiness checklist,
  deployment guide, admin onboarding, security packet, support
  runbook, demo-to-pilot transition plan, known limitations,
  pilot success metrics);
- this top-level Phase 14 contract at
  `docs/chartnav-pilot-readiness-deployment-hardening.md`;
- this section;
- a vitest readiness suite asserting the docs exist, the required
  headings exist, and forbidden positive claims appear only in
  safe contexts (negative assertions, enumerated forbidden-phrase
  lists, or Q&A question headings whose answers are negatives);
- `scripts/check_pilot_readiness.sh` — a small shell verifier for
  pre-pilot dry-runs.

**Safe pilot language** is enforced by the readiness suite and
documented in the security packet's "BAA / HIPAA language
caution" section. Forbidden positive claims include "HIPAA
compliant," "certified EHR," "autonomous diagnosis," "automatic
orders," "submit referral," "billing automation," "send patient
message," "replaces a doctor," "production-ready for PHI."
Approved phrasing includes "provider-reviewed," "documentation
support," "ophthalmology-specific," "controlled-pilot," "designed
to support."

**Deployment expectations** are now documented for three modes:
`local` (fake-data only), `staging` (fake-data only), and
`controlled-pilot` (real PHI permitted only after BAA + security
review gating items are signed off).

**Security review gating** items are enumerated in one place,
identical across the readiness checklist, the security packet, the
admin onboarding checklist, and the demo-to-pilot transition plan.

**Phase 14 prepares Phase 15** — Phase 15 will package ChartNav as
a runnable desktop demo (one-click run on a buyer's laptop) and
finalize commercial-launch readiness, while continuing to obey the
existing safety contract.

See `docs/chartnav-pilot-readiness-deployment-hardening.md` for
the full Phase 14 contract, the docs map, the readiness-test
description, and the Phase 15 recommendation.

## Phase 15 — commercial demo delivery system

Phase 15 converts the existing ChartNav clinical workflow
foundation into a polished, controllable, sales-demo-ready system.
Goal: ChartNav should feel like a coherent ophthalmology platform
during demos instead of a collection of features.

**No new clinical automation. No new schema. No new API surface.
No backend code changes. Fake demo data only.**

Phase 15 ships:

- a new `GuidedDemoMode` component — a sticky in-workspace
  orchestrator with a deterministic 8-step stepper, a prominent
  **DEMO MODE** badge, on-screen presenter cues, and Previous /
  Next / Reset controls. Gated on the URL query `?demo=1` (or
  `localStorage.chartnav.demoMode = "1"`); default off so normal
  providers never see it;
- `scripts/reset_demo_state.sh` — drops + re-seeds the local dev
  SQLite DB, prints a DevTools snippet for clearing browser-side
  demo state, refuses to run if `DATABASE_URL` is anything other
  than the local `sqlite:///<path>` default;
- two new docs under `docs/demo/` — an operator guide (recommended
  flow with Guided Demo Mode, click-by-click sequence, fallback
  paths, what NOT to claim, talking points) and an environment
  README (local startup, reset levels, seeded credentials,
  fake-data structure, troubleshooting, recording recommendations);
- this top-level Phase 15 contract at
  `docs/chartnav-commercial-demo-delivery-system.md`;
- this section;
- two new test files — a `GuidedDemoMode.test.tsx` component suite
  and a `DemoCommercialDelivery.test.tsx` package suite that
  asserts the new docs exist with required headings and that
  forbidden positive claims appear only in safe contexts.

**Deterministic by design.** Step labels and cues are fixed at
compile time. Step state lives only in browser `localStorage`.
There are no animations, no auto-advance, no hidden timers, no API
calls. The stepper does not click clinical-panel buttons or
generate artifacts — it is a presenter overlay, not a workflow
automation surface.

**Fake-data-only boundary.** The demo environment is fake-data
only by construction. The Phase 15 reset script refuses to run
against a non-local database URL. The Guided Demo Mode badge
prominently labels the experience "DEMO MODE · fake data only" so
it cannot be confused with a real-data session.

**Safety guardrails.** The stepper renders the same
negative-assertion safety bullets the Phase 13 demo guide and the
Phase 11 action queue use. Forbidden marketing claims are rejected
by the Phase 15 docs-claims test unless they appear inside a
negative-assertion line, an enumerated forbidden-phrase list, or
a Q&A question heading whose answer is a negative assertion —
identical heuristic to Phase 13 / 14.

**Phase 15 prepares Phase 16** — desktop demo packaging
(one-click runner for the buyer's laptop), pre-recorded fallback
clips, optional sticky workflow progress in normal mode, an
a11y smoke for the stepper, and a CI summary card. Phase 16 must
continue to obey the existing safety contract.

See `docs/chartnav-commercial-demo-delivery-system.md` for the
full Phase 15 contract.

## Phase 16 — website proof upgrade + conversion layer

Phase 16 upgrades the public-facing ChartNav website so it reflects
the actual product built through Phases 6–15. Goal: a buyer should
understand the real ChartNav workflow in under 60 seconds — what it
does, why it is ophthalmology-specific, what the provider controls,
what ChartNav does *not* do, and how to request a demo or start a
pilot conversation.

**No new clinical automation. No backend changes. No new schema.
No external LLM. No real-PHI claim. No unsupported HIPAA / SOC 2 /
certified-EHR claim. No binary media in the repo.**

There is no separate marketing site (no `apps/web/chartnavmd-site`).
The public website is the React app at `apps/web/`. Phase 16 adds
an opt-in route — `/landing` or `?intro=1` — that renders a new
public landing / proof page (`LandingPage.tsx`); the existing
authenticated workspace UX is unchanged. The opt-in pattern matches
Phase 15's Guided Demo Mode (`?demo=1`).

Phase 16 ships:

- a new `LandingPage.tsx` with hero / workflow / ophthalmology /
  provider-control / modules / before-after / demo-pilot /
  non-goals / footer sections;
- two inline SVG diagrams — a 7-stage workflow path and a Draft →
  Reviewed → Finalized state model. No binary media is committed;
- a 6-line gate in `main.tsx` and a CSS append in `styles.css`;
- an 18-test vitest suite asserting required sections, CTAs, SVG
  diagrams, modules, before/after, non-goals, the safe-claims
  contract, and the absence of order / coding / referral /
  patient-message buttons or autonomous-LLM positive claims;
- `scripts/check_website_claims.sh` — a pre-deploy verifier that
  confirms required files exist, the router gate is wired,
  negative-assertion phrasing is present, no forbidden positive
  claim slips, and no binary media is checked in under
  `apps/web/public`;
- the top-level Phase 16 contract at
  `docs/chartnav-website-proof-upgrade-conversion-layer.md` and an
  editorial shot list at
  `docs/website/chartnav-website-shot-list.md`;
- this section.

**Safe claims** are enforced by the same heuristic Phase 13 / 14 /
15 use: forbidden marketing claims (HIPAA compliant, certified EHR,
autonomous diagnosis, automatic orders, submit referral, billing
automation, send patient message, replaces a doctor,
production-ready for PHI, real patient data ready) appear only
inside negative-assertion lines, enumerated forbidden lists, or
explicit `does not …` statements.

**CTA strategy.** All named CTAs resolve to a single `contactHref`
prop (default `mailto:hello@chartnavmd.com`) so the deploy host can
override the destination without touching component code. Phase 16
does not invent a working intake backend.

**Phase 16 prepares Phase 17** — possible follow-ups include
flipping the unauthenticated default to the landing page, wiring a
real intake form, adding the landing page to the axe-core a11y
sweep, capturing real screenshots into out-of-repo CDN storage, and
the long-deferred commercial deck library (still out-of-repo).

See `docs/chartnav-website-proof-upgrade-conversion-layer.md` for
the full Phase 16 contract, the messaging strategy, the per-phase
proof map, the visual asset strategy, the CTA strategy, the safe
claims rules, the test contract, and the Phase 17 candidate list.

## Phase 17 — commercial launch package + desktop demo delivery

Phase 17 ships the operator-facing commercial surface that Phases
6–16 implied but never built: the deck library, the commercial
support docs, the local demo launcher, and the desktop demo
delivery package. After Phase 17 a presenter on the operator's
Mac can open `/Users/jean-maxcharles/Desktop/chartnav decks/`,
double-click `START_CHARTNAV.command`, run a fake-data demo, and
double-click `STOP_CHARTNAV.command` and `RESET_DEMO_DATA.command`
to tear down — without going hunting in the repo.

**No new clinical automation. No backend changes. No new schema.
No external LLM. No real-PHI claim. No unsupported HIPAA / SOC 2
/ FDA / certified-EHR claim. No binary media in the repo.**

Phase 17 ships:

- 15 deck Markdown source files under `docs/decks/` covering
  every recurring sales / investor / partner / onboarding
  scenario (investor pitch, sales, demo, customer pitch
  template, company, product roadmap, brand guidelines,
  educational onboarding, one-page sales, financial fundraising,
  marketing plan, project proposal, agency partner pitch,
  elevator pitch, long sales pitch);
- 6 commercial support docs under `docs/commercial/` (deck
  master kit, approved-claims language, commercial readiness
  map, buyer objection handling, pricing-packaging notes, pilot
  handoff checklist);
- 4 demo-package docs (local demo startup guide, troubleshooting,
  demo review checklist, plus the top-level desktop demo
  delivery contract at
  `docs/chartnav-desktop-demo-delivery-package.md`);
- 3 shell scripts —
  `scripts/export_chartnav_decks_to_desktop.sh` (idempotent
  exporter that builds the Desktop folder, copies every source
  doc to the right subfolder, generates README + 3 .command
  files, marks them executable),
  `scripts/create_chartnav_desktop_demo_package.sh` (orchestrator
  that runs the export and verifies every expected file landed +
  every .command file is executable), and
  `scripts/check_commercial_claims.sh` (pre-merge sanity check
  that mirrors the vitest claims contract);
- a 45-test vitest suite at
  `apps/web/src/test/CommercialDeckClaims.test.tsx` asserting
  every required file exists, every deck reaches the safe-claims
  contract, no forbidden positive claim slips, no deck invents
  financial numbers, the local-DB safety guard is preserved, no
  binary media is committed under Phase 17 paths, the pricing
  constants ($299 / $499 / $5,000 / $10,000) appear consistently,
  and the Desktop folder is `.gitignore`-d;
- the top-level Phase 17 contract at
  `docs/chartnav-commercial-launch-package.md` and the desktop
  delivery contract at
  `docs/chartnav-desktop-demo-delivery-package.md`;
- this section.

**Pricing contract.** $299–$499/provider/month; $5,000/practice/
month flat; $10,000 pilot fee (firm, not discounted); 2–4
practices = 10% off, 5–9 = 15% off, 10+ = enterprise terms.
Pricing is a hypothesis until paid-pilot data validates it; the
pricing-notes doc enumerates what is firm vs. validation-pending.

**Milestones.** M1 first paid pilot Jul 1 2026; M2 second paid
pilot Oct 1 2026; M3 first paying customer post-pilot Q4 2026;
M4 multi-practice deployment Q4 2026. Targets, not committed
delivery dates.

**SDVOSB / VA past-performance framing** appears on
`chartnav-investor-pitch-deck.md`, `chartnav-company-deck.md`,
`chartnav-agency-partner-pitch-deck.md`, and the internal
marketing plan deck only — the certifications and Mann-Grandstaff
VA past performance attach to the operating entity (ARCG
Systems), not to ChartNav clinically. Private-practice clinical
buyers see the clinical decks without the federal credibility
slide because federal credentials are not the relevant signal
for that audience.

**Safe-claims contract** is enforced by the same heuristic Phase
13 / 14 / 15 / 16 use: forbidden marketing claims (HIPAA-
compliant, certified EHR, autonomous diagnosis, automatic
orders, submit referral, billing automation, send patient
message, replaces a doctor, production-ready for PHI, real
patient data ready) appear only inside negative-assertion lines,
enumerated forbidden lists ("Never use" / "Don't say"), Q&A
question headings whose answers are negative assertions, or
explicit `does not …` statements. The catalog docs whose entire
job is to enumerate banned phrases —
`chartnav-approved-claims-language.md`,
`chartnav-brand-guidelines-deck.md` slide 5,
`chartnav-buyer-objection-handling.md` "Don't say" blocks — are
exempt by path from both the vitest scan and the shell-script
scan.

**Desktop delivery contract.** The Desktop folder at
`/Users/jean-maxcharles/Desktop/chartnav decks/` (override via
`CHARTNAV_DESKTOP_DIR`) is regenerated by the export script,
never committed back to the repo (paths are in `.gitignore`),
contains only Markdown / shell / text copies of repo source (no
binary media), and ships three macOS double-click scripts
(`START_CHARTNAV.command`, `STOP_CHARTNAV.command`,
`RESET_DEMO_DATA.command`). The reset script wraps
`scripts/reset_demo_state.sh`, which refuses to run if
`DATABASE_URL` is anything other than a local
`sqlite:///<path>`.

**Phase 17 prepares Phase 18** — first paid pilot or paid
customer (target M1 = Jul 1 2026). Phase 18 is operations work,
not new product. The Phase 17 commercial launch package is the
inventory Phase 18 sells from.

See `docs/chartnav-commercial-launch-package.md` for the full
Phase 17 contract, the deck audience map, the SDVOSB framing
contract, the pricing contract, the milestone contract, the
safe-claims contract, the desktop-folder source-of-truth
contract, the test contract, and the Phase 18 candidate
description.

## Phase 17B — A+ deck message tightening + Clinical Signal Filtering upgrade

Phase 17B is a **content quality pass** on top of Phase 17.
After Phase 17 the deck library exists; after Phase 17B the
decks are A-level commercial material — clear enough for a real
buyer, investor, advisor, partner, or practice administrator to
understand without needing repo context.

**No new clinical automation. No backend changes. No new schema.
No external LLM. No real-PHI claim. No unsupported HIPAA / SOC 2
/ FDA / certified-EHR claim. No binary media in the repo.**

What changed:

- **Clinical Signal Filtering positioned as the prime feature**
  on every buyer-relevant deck, with a canonical three-line
  cadence ("Filters conversation. Captures findings. Builds the
  diagram.") and a concrete worked example (the doctor saying
  *"Okay hold on… OD drusen in the macula… maybe OS flame
  hemorrhage inferior."* and ChartNav classifying the line into
  ignored chatter, clinical finding, uncertain phrase, and
  proposed diagram annotation).
- **Demo deck split** into two decks. The buyer demo deck
  (`chartnav-buyer-demo-deck.md`) is what a presenter shows
  during a live demo — no terminal commands, no repo paths, no
  `?demo=1` query string, no `make dev` references; only what
  the buyer sees on screen. The operator demo deck
  (`chartnav-operator-demo-deck.md`) is **internal-only** —
  pre-flight checklist, START / STOP / RESET .command files,
  reset commands, fallback plan if the stack breaks mid-demo.
  The original `chartnav-demo-deck.md` is now an index that
  routes the operator to the right deck for the audience.
- **One-page sales deck rewritten** as a single-page leave-
  behind with a Clinical Signal Filtering headline and worked
  example.
- **Buyer-facing decks scrubbed of repo-leak phrases** —
  "production code on main," "operator's note," "this version of
  the deck," `?intro=1`, `?demo=1`, `make dev`, `make reset-db`,
  raw repo paths, and `Phase N smoke` references no longer
  appear in any buyer-facing deck.
- **Audience + Purpose + CTA** declared in the front-matter of
  every deck so an operator (or a future ChartNav employee) can
  pick up any deck cold and know who it's for.
- **Company deck audience-routed.** Slide 8 (federal /
  government-healthcare credibility — SDVOSB, Mann-Grandstaff
  VA past performance) is clearly marked as "for federal /
  government-healthcare conversations" and explicitly skipped
  for private-practice buyers. Private-practice buyers see the
  clinical workflow without federal credentials.
- **Brand guidelines deck** adds a Clinical Signal Filtering
  approved-phrasing slide and extends the banned-phrase
  catalogue with "AI draws automatically," "AI decides," "AI
  diagnosis," "automatic charting," "hands-free diagnosis,"
  "hands-free charting," "guaranteed documentation accuracy."
- **Customer pitch template + project proposal template** add
  practice-specific Clinical Signal Filtering content via
  `{{DICTATION_PAIN}}`, `{{RETINAL_WORKFLOW_PAIN}}`, and
  `{{PRACTICE_EXAMPLE_FINDING}}` placeholders so each pilot
  pitch lands in the practice's own words.
- **Marketing plan deck** adds a concrete 30/60/90-day GTM
  execution plan and frames Clinical Signal Filtering as the
  outreach wedge.
- **Product roadmap deck** translates engineering phases into
  business outcomes ("capabilities already working") and adds
  a 30/60/90-day execution plan.
- **Master kit + approved-claims language + objection-handling
  + commercial readiness map** updated to reference the new
  deck split and the Clinical Signal Filtering language.
- **Export script + create-package wrapper** updated to include
  the two new deck files and verify them in post-export checks.
- **`scripts/check_commercial_claims.sh`** extended with a
  buyer-facing repo-leak scan plus the new Phase 17B
  banned-phrase entries.
- **`apps/web/src/test/CommercialDeckClaims.test.tsx`** grows
  from 45 assertions to 96 assertions covering the Phase 17B
  Clinical Signal Filtering presence requirement, the
  buyer-facing repo-leak scan, the audience / purpose / CTA
  front-matter requirement, and the operator-demo-stays-internal
  contract.

**Test contract.** `npx vitest run
src/test/CommercialDeckClaims.test.tsx` should pass 96/96.
`bash scripts/check_commercial_claims.sh` should pass 0 fail / 0
warn. The export script produces 41 source files copied + README
+ 3 .command files generated.

Phase 17B is a content + tooling pass. The Phase 18 candidate
remains unchanged — first paid pilot or paid customer (target
M1 = Jul 1, 2026). The Phase 17B-tightened decks are the
inventory Phase 18 sells from.

See `docs/chartnav-commercial-launch-package.md` for the updated
deck audience map and the full test contract.
