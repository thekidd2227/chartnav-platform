# Patient-chart / retina reconciliation matrix

**Date:** 2026-06-25
**Decision:** strict **mainline-wins**. The committed mainline schema and UI are
authoritative:
- migrations `e1f2a3041507` (chart_artifacts, `drawing_json`) + `e1f2a3041508` (fundus_charts)
- UI `EyeDiagramPanel`, `RetinalDrawingCanvas`, `RetinalProposalReview`, `FundusChartPanel`
- api client `listPatientEyeDiagrams` / `getPatientEyeDiagram` / `createPatientEyeDiagram` /
  `updatePatientEyeDiagram` / `signPatientEyeDiagram` + `EyeDiagramArtifact` (`drawing_json`)
- backend contract test `apps/api/tests/test_eye_diagrams.py` (the authoritative API spec)

## Root cause

`stash@{0}` was taken at Alembic `e1f2a3041505`. Mainline then **independently
re-implemented** the patient-chart / retina feature with a different `chart_artifacts`
schema (`drawing_json`, no `rendered_snapshot`) and a new UI. Mainline shipped the
**frontend + contract test** for `/patients/{id}/eye-diagrams` but **not the backend
routes** — that is the real gap. The stash carries a *stale* version of those routes
(`vector_json`/`rendered_snapshot`) plus a duplicate `chart_artifacts` migration, which
produced multiple Alembic heads and a column-name mismatch.

## Matrix

| Stash component | Mainline equivalent | Decision | Reason |
|---|---|---|---|
| migration `f7b9c1d2e301` (patients demographics + dup `chart_artifacts`); down=`e1f2a3041505`; **untracked** | `e1f2a3041507` `chart_artifacts`, `e1f2a3041508` `fundus_charts` | **delete + replace** | Duplicate `chart_artifacts` collides; stale `down_revision` creates a 2nd head. Never committed → safe to delete. Replace with a NEW migration (down=`e1f2a3041508`) adding ONLY the patients-demographics columns mainline lacks. |
| `chart_artifacts` table (`vector_json`, `rendered_snapshot`) | `chart_artifacts` (`drawing_json`) | **delete** | Mainline table is authoritative; never recreate. |
| `routes.py` eye-diagram endpoints (`vector_json`/`rendered_snapshot`) | **`app/api/eye_diagrams.py`** already implements `/patients/{id}/eye-diagrams` on `drawing_json` (+ `app/services/chart_artifacts.py`) and is registered in `main.py` | **drop the stash version; use mainline's** | Correction (post-commit `4be209b`): mainline already owns a complete, service-layer eye-diagram router. The eye-diagram CRUD I initially re-implemented in `routes.py` was a duplicate that *shadowed* `eye_diagrams.py` (routes.py router is included first). Removed it; `eye_diagrams.py` is canonical and passes `test_eye_diagrams.py` (23/23) once the demographics migration lets the seed/patient lookups resolve. routes.py keeps ONLY the genuinely-missing patient detail / encounters / chart-sections. |
| `routes.py` generic `/artifacts*` + `/patients/{id}/artifacts` (`vector_json`) | none | **delete** | No mainline equivalent; superseded by typed eye-diagram routes; avoids a 2nd representation. |
| `routes.py` `propose-from-text` + `services/retinal_scribe.py` + `tests/test_retinal_scribe.py` | none ("no AI proposal pipeline" on mainline) | **delete** | No mainline contract; avoids autonomous interpretation; mainline-wins. |
| `routes.py` `GET/PATCH /patients/{id}`, `/patients/{id}/encounters`, `/patients/{id}/chart-sections` | `/patients` list/create only | **keep (org-scoped)** | PatientChart needs patient detail + chart sections; mainline lacks them; uniquely needed. |
| `app/chart_sections.py` (section registry) | none | **keep** | Backs `/chart-sections` + PatientChart; verify no `vector_json`/autonomous content. |
| `api.ts` `getPatient`/`patchPatient`/`listPatientEncounters`/`listPatientChartSections`/`ChartSection`/`Patient` | mainline eye-diagram client | **keep** | Needed by PatientChart; not in mainline. |
| `api.ts` `ChartArtifact`/`vector_json` fns (`listPatientArtifacts`/`createPatientArtifact`/`getArtifact`/`patchArtifact`/`signArtifact`) | mainline eye-diagram fns | **delete** | Obsolete `vector_json`/`rendered_snapshot` representation. |
| `PatientChart.tsx` (imports `RetinalDiagramWorkspace`) | `EyeDiagramPanel` | **adapt** | Embed mainline `EyeDiagramPanel`; drop `RetinalDiagram` import + stash's own editor. |
| `RetinalDiagram.tsx` + `test/RetinalDiagram.test.tsx` | `EyeDiagramPanel`/`RetinalDrawingCanvas`/`RetinalProposalReview` | **delete** | Superseded parallel UI. |
| `tests/test_patient_chart_foundation.py` | — | **keep if green** | Validates patient detail/demographics/chart-sections against reconciled routes. |
| `App.tsx` import PatientChart + hash routing; `ClinicalTabbedWorkspace` "Open chart" | — | **keep** | Entry-point chain; already conflict-resolved (markers removed). |

## Eye-diagram API contract (from `test_eye_diagrams.py` + `EyeDiagramArtifact`)

- `POST /patients/{id}/eye-diagrams` → 201; `{artifact_type:"retinal_diagram", version_number:1, parent_artifact_id:null, is_signed:false, signed_at:null, title, findings_text, drawing_json:<dict>, ...}`. clinician/admin only (reviewer→403 `role_forbidden`). Unknown `encounter_id`→404 `encounter_not_found`. audit `eye_diagram_created`.
- `GET /patients/{id}/eye-diagrams` → 200 `{items:[...], total:N}`, newest first, `drawing_json` as dict. reviewer may read; unauth→401; other org→404 `patient_not_found`.
- `GET /patients/{id}/eye-diagrams/{aid}` → 200; unknown→404 `artifact_not_found`; other org→404.
- `PATCH /patients/{id}/eye-diagrams/{aid}[?fork=true]` → unsigned in-place (version unchanged); signed+no-fork→409 `artifact_signed_immutable`; signed+fork→200 new version (`parent_artifact_id`=orig, `version_number`=2, unsigned, inherits unspecified fields). reviewer→403. audit `eye_diagram_updated`.
- `POST /patients/{id}/eye-diagrams/{aid}/sign` → 200 `is_signed:true`; re-sign→409 `artifact_already_signed`; reviewer→403; other org→404. audit `eye_diagram_signed`.
- Audit `detail` must never contain `findings_text` or `drawing_json` content.
- `drawing_json` stored as JSON TEXT, returned parsed (dict). `is_signed` derived from `signed_at`.

## Gate before commit (requirement 7)
single Alembic head · blank-DB upgrade · upgrade from `e1f2a3041508` · patient-chart tests ·
eye-diagram API tests · EyeDiagramPanel tests · fundus tests · tenant-isolation tests ·
frontend typecheck · frontend build · backend tests for touched routes · conflict-marker scan ·
`git diff --check`. **stash@{0} untouched.** No audit/CI/screenshot/package.json staging.
