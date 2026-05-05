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

## Future phases (still deferred)

These all build on the same `chart_artifacts` table and routes:

1. **Clinical speech filter** — filter dictated text into clinical
   findings before it reaches the artifact. Independent of this PR.
2. **AI-proposed annotations** — generate diagram annotations from
   `findings_text`. Producer pipeline; does not write to `chart_artifacts`
   directly.
3. **Provider apply/reject workflow** — surface AI proposals as
   reviewable suggestions; only **applied** ones flow into
   `drawing_json` with `source=ai_approved` provenance. Rejected
   proposals never persist.
4. **Findings → diagram proposals** — the bridge that turns approved
   findings into proposed annotations on the diagram.

The persistence shell + Phase 5B canvas ship first so each of those
follow-ups has a stable storage contract, schema version, and audit
baseline to plug into.

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
