# Phase 91 — Unified Ophthalmology Workspace Engine

**Date:** 2026-06-11
**Branch:** `feature/phase-91-unified-workspace-engine`
**Base:** `main` after Phase 90 (`1cd6b90`)
**Status:** Workflow orchestration layer — no new clinical intelligence.

## Purpose

Phase 91 unifies four previously-separate orchestration concerns
into one cohesive engine:

1. **Specialty visit-mode routing** — `intake` / `surgical_pre_op`
   / `post_op` / `follow_up` / `lab_review` / `unscheduled`.
2. **Adaptive workspace completion** — emphasis projection layered
   on top of the Phase 86 panel order.
3. **Eye-linked workflow synchronisation** — provider-driven
   active laterality (`OD` / `OS` / `OU` / `NA`).
4. **Live visit state engine v2** — single React context + GET
   endpoint that exposes the unified projection to every panel.

ChartNav does NOT auto-classify the visit mode, does NOT
autonomously select an eye, does NOT add new clinical intelligence,
does NOT generate diagnoses, and does NOT introduce autonomous
behaviour. Visit mode and active laterality are provider-driven.

## Schema

Alembic `h6c7d8e9f0a1` adds two columns to `encounters`:

| Column | Type | Notes |
|---|---|---|
| `visit_mode` | text | CHECK closed allowlist; default `unscheduled` |
| `active_laterality` | text | CHECK closed allowlist (`OD` / `OS` / `OU` / `NA`); default `NA` |

Index on `(visit_mode)` for queue filters in future phases.

## Endpoints

| Method | Path | RBAC |
|---|---|---|
| `GET` | `/api/v1/encounters/{id}/workspace-state` | any caller |
| `PATCH` | `/api/v1/encounters/{id}/workspace-state/visit-mode` | admin / clinician |
| `PATCH` | `/api/v1/encounters/{id}/workspace-state/active-laterality` | admin / clinician |

GET response embeds the unified projection: encounter metadata,
encounter type, visit mode + label, active laterality + label,
Phase 86 profile + panel_order + panel_labels, visit-mode emphasis
(emphasised + secondary panels), laterality-linked panel list,
supported-matrix pickers, disclosure verbatim.

## Visit mode emphasis

| Visit mode | Emphasised panels |
|---|---|
| `intake` | provider_action_queue, note_validation |
| `surgical_pre_op` | cataract_workflow, imaging_metadata, ophthalmic_medication_safety, medication_safety, note_validation, provider_action_queue |
| `post_op` | cataract_workflow, note_validation, provider_action_queue, ophthalmic_medication_safety, medication_safety |
| `follow_up` | retina_visit_summary, anti_vegf_injection, glaucoma_cockpit, disease_staging, note_validation, provider_action_queue |
| `lab_review` | imaging_metadata, retina_visit_summary, quality_intelligence, note_validation, provider_action_queue |
| `unscheduled` | provider_action_queue, note_validation |

Every emphasised panel must also be in the Phase 86 panel_order;
defensively validated at import time. The emphasis is a **UI hint
only** — no panel is ever hidden by visit mode.

## Laterality-linked panels

The engine declares which panels re-filter when active laterality
changes:

```
anti_vegf_injection
glaucoma_cockpit
cataract_workflow
fundus_chart
imaging_metadata
ophthalmic_medication_safety
```

The list is descriptive — panels are already laterality-aware on
the server; the UI uses this list to decide which panels show a
"now filtered to OD/OS" indicator.

## Frontend

New module `apps/web/src/features/workspace-state/`:

- `workspaceStateTypes.ts` — types.
- `workspaceStateApi.ts` — `getWorkspaceState`, `patchVisitMode`,
  `patchActiveLaterality`.
- `WorkspaceStateProvider.tsx` — React context provider + hook
  (`useWorkspaceState`) + helpers (`panelIsEmphasised`,
  `panelIsLateralityLinked`).
- `VisitModeRibbon.tsx` — closed-allowlist visit mode chooser with
  disclosure copy.
- `LateralitySwitcher.tsx` — closed-allowlist OD/OS/OU/NA chooser
  with disclosure copy.

`ClinicalTabbedWorkspace.tsx` Overview tab now wraps the panel
grid in a `WorkspaceStateProvider`. The Visit Mode Ribbon + Eye
Switcher render above the existing Phase 86 EncounterTypeBadge.
Panels can subscribe to `useWorkspaceState()` to react to laterality
or visit-mode changes (the existing Phase 78–90 panels keep their
current behaviour; future phases may add emphasis-driven styling).

## Cross-phase integrations

- **Phase 86 (workspace profile)** — visit-mode emphasis is layered
  on top of Phase 86's panel order; the Phase 86 "never hide data"
  contract is preserved.
- **Phase 78 / 79 / 80 / 84 / 85 / 88 / 89 / 90 panels** — no
  service change required; panels remain laterality-aware via the
  existing per-row laterality column.

## Forbidden behaviours (verified)

- ChartNav does NOT auto-classify the visit mode.
- ChartNav does NOT autonomously select an eye.
- ChartNav does NOT add new clinical intelligence.
- ChartNav does NOT generate diagnoses or treatment recommendations.
- ChartNav does NOT add autonomous behaviour.
- Phase 86 never-hide-data contract is preserved — emphasis is UI hint only.

## Tests

Backend:

- `tests/test_workspace_state.py` — **20 PASS** covering baseline,
  supported matrix, disclosure boundary, emphasis subset, cross-org
  404, visit mode PATCH for all 6 modes + invalid + RBAC + cross-org,
  active laterality PATCH for all 4 values + invalid + RBAC +
  cross-org, profile integration, safety canary.

Web:

- `src/test/WorkspaceStateEngine.test.tsx` — **14 PASS** covering
  helper functions, VisitModeRibbon render + PATCH + canEdit gate +
  disclosure, LateralitySwitcher render + PATCH + canEdit gate +
  disclosure, provider error surface, no-fetch when encounterId
  null, safety canary.

## Smoke

- `pytest tests/test_workspace_state.py` — 20/20.
- `npx vitest run` — 947/947 (up from 933).
- `npx tsc --noEmit` — clean.
- All 5 safety scanners + `git diff --check` — PASS.
- Phase 63C smoke — not run (no local stack).

## Caveats

- The visit-mode emphasis is intentionally minimal. Future phases
  may add per-panel styling (badges, highlighted borders) driven
  by `panelIsEmphasised()`.
- Laterality-linked panels currently react implicitly; future
  phases can opt in via the `useWorkspaceState()` hook to filter
  their data per active eye.
- `unscheduled` is the default for every existing encounter via
  the migration's server_default; no backfill needed.
- The emphasis projection's secondary list always includes the
  remainder of the profile's panel_order; this guarantees emphasis
  + secondary = full panel_order for the resolved profile.

## Readiness for Phase 92

- Phase 90 + Phase 91 are both on `main`.
- Workspace orchestration is now unified; future feature phases
  can subscribe to `useWorkspaceState()` without re-implementing
  visit-mode or laterality plumbing.
- No new clinical surfaces were added; this phase is pure
  orchestration.
- Phase 92 may target any of the previously-recommended candidates
  (FHIR write-back is OUT of scope, real-PHI readiness review,
  pilot rehearsal, Vite 5→8 hardening, IRIS/MIPS verified spec
  library, or Quality Submission Workbench).
