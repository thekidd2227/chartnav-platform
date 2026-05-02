# ChartNav — patient chart foundation (Phase 2A + 2B + Phase 5 start)

> **Productized capability — Clinical Signal Filtering.** Phase 5A.1
> ships ChartNav's first user-facing AI feature on top of this
> foundation: a rule-based scribe that separates clinical findings
> from conversational chatter, surfaces uncertainty for explicit
> review, and proposes retinal diagram annotations the provider
> applies or rejects before anything is saved. See:
>
> - Sales one-pager:
>   [`docs/sales/chartnav-clinical-signal-filtering-one-pager.md`](sales/chartnav-clinical-signal-filtering-one-pager.md)
> - Demo script:
>   [`docs/sales/chartnav-clinical-signal-filtering-demo-script.md`](sales/chartnav-clinical-signal-filtering-demo-script.md)
> - Video shot list:
>   [`docs/sales/chartnav-retinal-diagram-video-clips.md`](sales/chartnav-retinal-diagram-video-clips.md)
> - Marketing-page copy + video placeholder spec:
>   [`docs/sales/chartnav-product-page-copy.md`](sales/chartnav-product-page-copy.md)
> - User guide for providers:
>   [`docs/user-guides/clinical-signal-filtering.md`](user-guides/clinical-signal-filtering.md)
>
> **Output contract** of `POST /patients/{id}/eye-diagrams/propose-from-text`
> (see Phase 5A.1 section below for full detail):
>
> - `clinical_text`
> - `ignored_chatter`
> - `uncertain_phrases`
> - `structured_findings_json`
> - `proposed_annotations`
> - `proposed_findings_text`
> - `missing_flags`
> - `confidence_summary`
>
> **Provider approval lifecycle:** generate → review triage →
> apply or reject per proposal → **Save** persists through the
> existing artifact endpoints → optional **Sign** locks the
> diagram, with edits forking new versions server-side. Nothing
> is saved automatically.
>
> **Demo readiness.** The shot list above is the canonical plan
> for recording six 20–30 second video clips of this feature for
> the website, sales deck, follow-up emails, and social posts.
> All clips are recordable from the live app — no mockups, no
> simulated data.



Status: shipped on 2026-04-30. Single migration (`f7b9c1d2e301`) adds
the schema. Single new frontend route (`#/patients/{id}`) renders the
chart shell. Single new artifact surface (`chart_artifacts`) stores
retinal diagrams as the first concrete instance.

## What was added

### Backend
- **Migration `f7b9c1d2e301_patient_chart_foundation`** — extends
  `patients` with EMR-style demographics and adds `chart_artifacts`.
- **`apps/api/app/chart_sections.py`** — in-process registry. Single
  declaration site for the 11 chart sections. Each entry is a
  `ChartSection(key, label, status, description, api_path,
  required_role, future_module)`.
- **New API endpoints** (in `app/api/routes.py`):
  - `GET    /patients/{id}`                — full demographics row.
  - `PATCH  /patients/{id}`                — whitelist edit, audited.
  - `GET    /patients/{id}/encounters`     — patient-scoped list.
  - `GET    /patients/{id}/chart-sections` — registry payload.
  - `GET    /patients/{id}/artifacts`      — list (filter by `artifact_type`).
  - `POST   /patients/{id}/artifacts`      — create retinal diagram.
  - `GET    /artifacts/{id}`               — detail.
  - `PATCH  /artifacts/{id}`               — in-place edit while unsigned;
                                            forks to a new version when
                                            the prior is signed.
  - `POST   /artifacts/{id}/sign`          — single-shot signing.
- **Audit events** written for: `patient_viewed`, `patient_updated`,
  `artifact_created`, `artifact_updated`, `artifact_versioned`,
  `artifact_signed`. Detail rows carry IDs and field names — never
  values — so PHI does not leak into the audit table.
- **Tests**: `apps/api/tests/test_patient_chart_foundation.py` —
  24 tests covering happy paths, RBAC, cross-org 404, audit
  emission, invalid payloads, and the sign-then-edit fork.

### Frontend
- **Hash route**: `#/patients/{id}` renders the patient chart in
  place of the workflow view. No router library added. The encounter
  detail pane gains an inline "Open chart" link when the encounter
  has a native `patient_id`.
- **`apps/web/src/PatientChart.tsx`** — chart shell:
  - Patient header (name, MRN, DOB+age, sex, status pill).
  - Sidebar with 11 tabs; tabs with `status: placeholder` show a
    "soon" badge so the UI is honest.
  - Overview panel — read view + edit modal calling `PATCH`.
  - Encounters panel — table with deep links to the encounter
    workspace (`?encounter=...`).
  - Eye Diagrams panel — list + open + create new.
  - Placeholder panels render a clear "Not implemented yet" message
    with the future-module label.
- **`apps/web/src/RetinalDiagram.tsx`** — Phase 5 minimum:
  - Side-by-side OD / OS SVG canvases (200x200 view box).
  - Tools: select, pen (freehand polyline), text label, clear.
  - Color picker (5 clinical colors) + stroke width slider.
  - Save → `POST /patients/{id}/artifacts` (or `PATCH` on existing).
  - Sign → `POST /artifacts/{id}/sign`. Once signed the canvas is
    read-only; further edits create a new version (server-side fork).
- **API client**: `Patient`, `PatientPatchBody`, `ChartSection`,
  `ChartArtifact`, `ChartArtifactCreateBody`, `ChartArtifactPatchBody`
  types and matching functions in `src/api.ts`.
- **Tests**: `src/test/PatientChart.test.tsx` — 6 tests covering
  default Overview render, tab switching, placeholder honesty,
  retinal save flow with mocked API, RBAC hiding edit/create
  controls for reviewer, and the demographics edit round-trip.

## Patient schema changes (migration `f7b9c1d2e301`)

Additive columns on `patients` (all nullable; existing rows untouched):

| Column                              | Type     | Notes                                             |
| ----------------------------------- | -------- | ------------------------------------------------- |
| `middle_name`                       | varchar  |                                                   |
| `preferred_name`                    | varchar  |                                                   |
| `display_name`                      | varchar  | optional override of "{first} {last}"             |
| `pronouns`                          | varchar  |                                                   |
| `gender_identity`                   | varchar  | separate from `sex_at_birth`                      |
| `preferred_language`                | varchar  | ISO-ish; not enforced                             |
| `race`                              | varchar  | free-form, no imposed vocabulary                  |
| `ethnicity`                         | varchar  | free-form                                         |
| `email`                             | varchar  |                                                   |
| `phone`                             | varchar  |                                                   |
| `address_line1` / `_line2`          | varchar  |                                                   |
| `address_city` / `_state`           | varchar  |                                                   |
| `address_postal_code` / `_country`  | varchar  |                                                   |
| `emergency_contact_name`            | varchar  |                                                   |
| `emergency_contact_phone`           | varchar  |                                                   |
| `emergency_contact_relationship`    | varchar  |                                                   |
| `insurance_metadata`                | text     | JSON-serialized (object or array). See note.      |
| `updated_at`                        | datetime | populated by PATCH                                |

**Insurance** is stored as a JSON blob on purpose. The frontend can
evolve plan/member-id/payer fields without a migration each time.
When the schema settles we will normalize into a real
`patient_insurance` table.

**Identity-bearing fields** (`patient_identifier`, `external_ref`,
`organization_id`) are intentionally NOT in the PATCH whitelist —
the generic edit endpoint cannot change a patient's MRN.

## Chart-section registry

Defined once in `app/chart_sections.py`. Each entry has:

```
{ key, label, status, description, api_path?, required_role?, future_module? }
```

Initial sections:

| Key            | Status      | Notes                                                |
| -------------- | ----------- | ---------------------------------------------------- |
| `overview`     | active      | demographics from `GET /patients/{id}`               |
| `encounters`   | active      | `GET /patients/{id}/encounters`                      |
| `allergies`    | placeholder | future module: `phase-2c-allergies`                  |
| `medications`  | placeholder | future module: `phase-2c-medications`                |
| `labs`         | placeholder | future module: `phase-2c-labs`                       |
| `radiology`    | placeholder | future module: `phase-2c-radiology`                  |
| `orders`       | placeholder | future module: `phase-2c-orders`                     |
| `documents`    | placeholder | future module: `phase-2c-documents`                  |
| `consults`     | placeholder | future module: `phase-2c-consults`                   |
| `isolation`    | placeholder | future module: `phase-2c-isolation`                  |
| `eye_diagrams` | active      | `chart_artifacts` table; retinal diagram surface     |

The frontend renders straight from the registry — adding a new
section is a single source change in `chart_sections.py` plus a
panel component for the `key`. Section status (`active` /
`placeholder` / `unavailable`) is the contract; the UI never shows
fake data for placeholder modules.

## Patient chart UI behavior

- Route is `#/patients/{id}` and is deep-linkable. Clearing the hash
  returns the user to the workflow view.
- Identity picker, top-level header, and footer behavior are
  preserved across both views.
- **Edit demographics** is gated to `admin` and `clinician`.
  Reviewers see the read-only Overview without the edit button.
- **Encounters tab** uses the existing encounter-detail
  query-string deep link (`?encounter={id}`) to keep the URL
  contract consistent with the rest of the app.
- **Placeholder panels** show a `data-section-status="placeholder"`
  attribute and a "Not implemented yet" line — operators are not
  asked to interpret an empty surface as "no data."
- **Eye Diagrams** is its own list + editor. Diagrams are sorted
  newest-first. Signed diagrams render with a "signed" badge in
  the list and at the top of the editor.

## Retinal diagram foundation (Phase 5 start)

- One row per *version* in `chart_artifacts`. `parent_artifact_id`
  links a new version to its predecessor; `version_number` is the
  display ordinal.
- **Editing rules**:
  - While `signed_at` is null, `PATCH /artifacts/{id}` updates the
    same row in place.
  - Once `signed_at` is set, `PATCH /artifacts/{id}` is a fork:
    the response is a new row with the prior id as
    `parent_artifact_id` and `version_number` bumped. The signed
    row is never mutated.
  - `POST /artifacts/{id}/sign` is one-shot and idempotent (409
    `artifact_already_signed`).
- **Drawing payload** is JSON in `vector_json`:

  ```ts
  {
    od: { kind: 'pen', color, width, points: [[x, y], ...] }[],
    os: same shape,
    labels: { eye: 'od' | 'os', x, y, text, color }[]
  }
  ```

  Coordinates are in the SVG's 200x200 view-box so they round-trip
  cleanly across renderings and DPI.
- `rendered_snapshot` is a placeholder text column for a future
  PNG/PDF reference. We do not generate a server-rendered snapshot
  in this phase.

## What remains for full EMR-style clinical modules (Phase 2C)

Each placeholder section needs:

- a real schema (one or more tables)
- API endpoints that respect the same auth / RBAC / org-isolation /
  audit conventions
- a panel component
- promotion to `status: 'active'` in the registry

Initial priorities (ordered roughly by clinical leverage):

1. **Allergies** — substance + reaction + severity + onset.
2. **Medications** — active list, sig, prescriber, history.
3. **Labs** — observation + reference range + trend view.
4. **Orders** — order set, status (pending → resulted → cancelled).
5. **Documents** — uploaded blobs + metadata + retention.
6. **Consults / H&P** — narrative templates, signoff parity with notes.
7. **Radiology** — order + study + report; image rendering deferred.
8. **Isolation** — precaution flags + revisit policy.

These are all independent and can be parallelized once the
`chart_section` shape is stable.

## Phase 5A.1 — eye-diagram alias surface + AI retinal scribe (rule-based v1)

Persistence still happens through `chart_artifacts` exactly as
described above. Phase 5A.1 added a friendlier surface and a
non-persistent AI proposal layer on top.

### Friendly aliases

The five canonical eye-diagram operations are now also exposed
under `/patients/{id}/eye-diagrams*`. These do **not** duplicate
persistence — each handler is a thin facade that validates the
(patient ↔ artifact ↔ retinal_diagram) axes then delegates to the
canonical `chart_artifacts` handlers:

- `GET    /patients/{id}/eye-diagrams`                      → list
- `GET    /patients/{id}/eye-diagrams/{aid}`                → detail
- `POST   /patients/{id}/eye-diagrams`                      → create (forces `artifact_type=retinal_diagram`)
- `PATCH  /patients/{id}/eye-diagrams/{aid}`                → in-place when unsigned, fork-on-edit-after-sign
- `POST   /patients/{id}/eye-diagrams/{aid}/sign`           → sign (idempotent → 409 once signed)

Cross-axis mismatches (artifact belongs to another patient, or
artifact is not a retinal_diagram) return **404** to avoid leaking
existence across boundaries. Auth/RBAC/audit/org-isolation rules
are unchanged — all of that lives one level down in the canonical
artifact handlers.

### AI retinal scribe (rule-based v1)

```
POST /patients/{id}/eye-diagrams/propose-from-text
body: { "source_text": "...", "encounter_id": null }
```

This endpoint is **read-only**. It runs the deterministic filter
in `app/services/retinal_scribe.py` over the input text and
returns a triage with proposed annotations. **Nothing is written
to the database.** Persistence happens only when the provider
clicks Apply on individual proposals and saves through the
existing alias endpoint.

#### Filter v1 rules

The filter is conservative and allowlist-only:

- **Findings allowlist** (canonical key + synonym patterns):
  drusen, microaneurysm, dot/blot hemorrhage, flame hemorrhage,
  hard exudates, cotton-wool spot, neovascularization (incl.
  NVD/NVE), IRMA, lattice degeneration, retinal tear/hole,
  retinal detachment, laser scar / PRP, disc pallor, RPE changes.
- **Laterality**: `OD` / right eye, `OS` / left eye, `OU` / both
  eyes / bilateral.
- **Zones**: macula, optic disc, superior, inferior, nasal,
  temporal, periphery.
- **Severity**: mild / moderate / severe.
- **Uncertainty markers**: `possible`, `possibly`, `maybe`,
  `questionable`, `likely`, `rule out`, `uncertain`,
  `suspicious for`, `cannot rule out`, `?`.
- **Chatter markers**: `okay`, `hold on`, `let me see`,
  `can you hear me`, `next patient`, `front desk`,
  `we'll come back to that`, `thank you`, `one moment`,
  scheduling/appointment phrases.

Decision rules per phrase (sentence-level + clause-level split on
`.?!` and `;` / connector-comma):

| Phrase contains                       | Triage                                                               |
| ------------------------------------- | -------------------------------------------------------------------- |
| Recognized finding                    | **clinical**. Build a structured finding + (per-eye) annotation. If uncertainty marker present, also add to `uncertain_phrases`. |
| Chatter marker AND no finding         | **ignored_chatter** (with reason).                                   |
| No finding AND no chatter marker      | **uncertain_phrases** (reason: `no_recognized_finding`) — never silently dropped. |

If a finding has no laterality, the structured finding is still
emitted but **no annotation is auto-placed** (we won't guess OD
vs. OS). The response includes a `missing_flags` entry so the UI
can prompt the provider.

#### Response shape

```json
{
  "clinical_text": "OD severe drusen ...",
  "ignored_chatter":   [{ "phrase": "Hold on",     "reason": "chatter_marker_no_finding" }],
  "uncertain_phrases": [{ "phrase": "Possible NV", "reason": "uncertainty_marker_present" }],
  "structured_findings_json": [{
    "finding": "drusen", "label": "drusen",
    "laterality": "OD", "zone": "macula",
    "severity": "severe", "certainty": "definite",
    "source_phrase": "OD severe drusen in the macula"
  }],
  "proposed_annotations": [{
    "proposal_id": "...", "finding": "drusen", "label": "drusen",
    "eye": "od", "x": 100, "y": 110, "color": "#DC2626",
    "text": "drusen", "source": "ai_proposed",
    "source_phrase": "OD severe drusen in the macula",
    "severity": "severe", "certainty": "definite", "zone": "macula"
  }],
  "proposed_findings_text": "OD drusen (macula) [severe]",
  "missing_flags": [],
  "confidence_summary": { "findings": 1, "chatter": 0, "uncertain": 0, "annotations": 1 }
}
```

### Provider review lifecycle

In the UI:

1. Provider opens the **AI scribe** panel inside the retinal
   diagram workspace and pastes/dictates the exam phrasing.
2. UI calls `POST /eye-diagrams/propose-from-text`. The
   triage and proposed annotations are rendered with apply/reject
   controls per row, plus *Apply remaining* and *Reject remaining*.
3. **Apply** writes the annotation into the local canvas state as
   a label tagged `source: 'ai_approved'` and merges the
   `proposed_findings_text` into the findings textarea.
4. **Reject** sets the row to a rejected state and the annotation
   is **never** written into `vector_json` or `findings_text`.
5. Provider clicks **Save**. Persistence flows through the
   existing alias endpoint:
   `POST /patients/{id}/eye-diagrams` (create) or
   `PATCH /patients/{id}/eye-diagrams/{aid}` (update / fork).

The proposal endpoint is not on the persistence path. The same
diagram can be re-saved any number of times, and each save uses
the existing version-fork-on-edit-after-sign rule.

### Audit safety for the scribe

Every call to the proposal endpoint writes one
`scribe_proposal_generated` audit row. The detail string includes
**only counts**:

```
patient_id={id} input_chars=N findings=N chatter=N uncertain=N annotations=N
```

The verbatim `source_text`, the `proposed_findings_text`, and the
proposed annotation contents are **never** written to the audit
detail. The `test_propose_endpoint_audit_excludes_phi` test pins
this contract — a phrase with PHI-like content (e.g. an SSN)
in the input is verified to never appear in any audit row.

### Limitations of v1

- **Deterministic only**: regex- and keyword-based, no LLM. Phrases
  outside the allowlist surface as uncertain rather than getting
  recognized.
- **No symbol drag/move**: AI annotations are placed at the zone
  centroid; provider can use the delete tool + redraw, but cannot
  move yet.
- **No transcript dictation pipeline integration**: scribe takes a
  paste/typed text block. STT integration with the existing
  encounter input pipeline is a separate piece of work.
- **No provenance per stroke** in the UI yet beyond
  `source: 'manual' | 'ai_approved'` on labels. Audit captures
  counts, not per-annotation lineage.

### Future LLM-backed path (v2)

The `analyze()` function is the contract boundary. A future
LLM-backed implementation (call out, get back a structured JSON,
post-process through the same dataclasses) slots in here without
changing the endpoint shape, the UI, or the persistence layer.
The deterministic v1 stays as a fallback and a regression baseline.

## What remains for full Phase 5 retinal tooling (Phase 5B)

The current canvas is intentionally minimal. Future work:

- Structured **symbol palette**: hemorrhage, drusen, laser scars,
  cotton-wool spots, exudates, RPE changes, etc. Each symbol carries
  its own SVG glyph and metadata.
- **Per-symbol layers** with toggleable visibility so providers
  can compare visits side by side while reviewing care.
- **Eraser** + per-stroke select + delete. Currently `clear` is
  whole-eye only.
- **Undo / redo** stack, scoped per editing session.
- **Anterior-segment** template (cornea/iris view) with its own
  symbol set.
- **`rendered_snapshot`** generation: server-side rasterization
  to PNG/PDF for export, transmission, and printing.
- **Encounter linkage**: when an encounter is open, default the new
  diagram's `encounter_id` to the active encounter so audit trails
  tie back to the visit.
- **Symbol provenance** in the audit row (which symbol, where,
  by whom, at what version).

## Security / compliance posture

- Auth/RBAC: existing `require_caller` + role checks; reviewers are
  read-only on patient writes and artifact writes.
- **Org isolation**: every endpoint that loads a `patient` or
  `artifact` validates `organization_id` matches the caller's org and
  returns 404 on mismatch (no existence leak across orgs).
- **Audit**: every read of a patient and every mutation of a patient
  or artifact writes a row. Detail strings carry IDs and field
  names, not values.
- **PHI**: never written to standard logs by the new code; not
  written to audit detail strings.
- **Not certified**: this is a foundation layer, not a certified
  EHR. ChartNav makes no certification claim today and the UI does
  not present this surface as one.
- **Versioning**: signed artifacts cannot be silently overwritten —
  edits fork. This is structural, not a UI choice.

## How to run

```
make migrate          # applies f7b9c1d2e301 forward
make seed             # idempotent
make test             # full pytest suite — 346 passing
make web-test         # vitest — 149 passing
make verify           # full backend gate
make web-verify       # full frontend gate (typecheck + vitest + build)
```

Open the chart shell in dev:

```
make dev              # boots api on :8000 and web on :5173
# then visit http://localhost:5173/#/patients/1
```
