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

## Future phases (deferred from this PR)

These all build on the same `chart_artifacts` table and routes:

1. **Visual drawing canvas** — replace the JSON textarea with a real
   OD/OS retinal canvas widget. Submits the same `drawing_json` shape.
2. **Clinical speech filter** — filter dictated text into clinical
   findings before it reaches the artifact. Independent of this PR.
3. **AI-proposed annotations** — generate diagram annotations from
   `findings_text`. Producer pipeline; does not write to `chart_artifacts`
   directly.
4. **Provider apply/reject workflow** — surface AI proposals as
   reviewable suggestions; only **applied** ones flow into
   `drawing_json` with `source=ai_approved` provenance. Rejected
   proposals never persist.
5. **Findings → diagram proposals** — the bridge that turns approved
   findings into proposed annotations on the diagram.

The persistence shell ships first so each of those follow-ups has a
stable storage contract and audit baseline to plug into.
