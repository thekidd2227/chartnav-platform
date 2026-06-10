# Phase 86 — Subspecialty Adaptive Workspace

**Date:** 2026-06-10
**Branch:** `feature/phase-86-subspecialty-adaptive-workspace`
**Base:** `main` after Phase 85 (`1c9d93b`)
**Status:** Ninth Phase 2 Clinical Intelligence surface — provider-driven workspace adaptation layer

## Purpose

Phase 86 transforms the Overview tab from a static
ophthalmology workspace into a subspecialty-adaptive
workspace. The adaptation is **purely a panel-ordering layer
over data already in the workspace** — no panels are hidden,
no clinical content changes, and no subspecialty is inferred
from clinical data.

The provider PATCHes the encounter's `encounter_type`
(`retina` / `glaucoma` / `cataract` / `comprehensive`) and the
WorkspaceProfileResolver maps it to a deterministic panel
order:

- **prioritized_panels** — render expanded at the top.
- **visible_panels** — render expanded mid-grid.
- **collapsed_panels** — render inside a `<details>` so the
  operator can always expand them.

**ChartNav does not classify encounters.** ChartNav does not
infer subspecialty from imaging, vitals, IOP, OCT, or any
clinical artifact. The `encounter_type` column defaults to
`comprehensive` (balanced layout). The resolver mapping is a
fixed closed-allowlist — new profiles require a migration +
service change.

## Schema

Alembic revision `d2f3a4b5c6d7` adds a single column to
`encounters`:

| Column | Type | Notes |
|---|---|---|
| `encounter_type` | text | closed allowlist (CHECK), default `comprehensive` |

Closed allowlist: `retina`, `glaucoma`, `cataract`,
`comprehensive`. Index on `(encounter_type)` for queue / queue
filter scans.

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/encounters/{encounter_id}/workspace-profile` | required | any caller with encounter access |
| `PATCH` | `/api/v1/encounters/{encounter_id}/workspace-profile` | required | admin / clinician |

Cross-org returns 404 (no existence leak).

GET response shape:

```jsonc
{
  "encounter_id": 1,
  "encounter_type": "retina",
  "encounter_type_label": "Retina",
  "profile": {
    "code": "retina",
    "label": "Retina",
    "prioritized_panels": [{"code": "...", "label": "..."}, ...],
    "visible_panels": [{"code": "...", "label": "..."}, ...],
    "collapsed_panels": [{"code": "...", "label": "..."}, ...],
    "panel_order": ["provider_action_queue", "note_validation", ...]
  },
  "supported_encounter_types": [{"code": "...", "label": "..."}, ...],
  "disclosure": "Workspace profile is a deterministic mapping..."
}
```

## Workspace profiles

Every profile covers every known panel exactly once across
its three buckets — verified by an import-time defensive
check (`_validate_profile_coverage`) and a backend coverage
test.

### Retina

- **Prioritized:** provider_action_queue, note_validation,
  anti_vegf_injection, retina_visit_summary,
  retina_visit_packet
- **Visible:** disease_staging, medication_safety
- **Collapsed:** glaucoma_cockpit, cataract_workflow

### Glaucoma

- **Prioritized:** provider_action_queue, note_validation,
  glaucoma_cockpit, medication_safety
- **Visible:** disease_staging, retina_visit_summary
- **Collapsed:** anti_vegf_injection, cataract_workflow,
  retina_visit_packet

### Cataract

- **Prioritized:** provider_action_queue, note_validation,
  cataract_workflow, medication_safety
- **Visible:** disease_staging, retina_visit_summary
- **Collapsed:** anti_vegf_injection, glaucoma_cockpit,
  retina_visit_packet

### Comprehensive

- **Prioritized:** all nine panels in baseline order.
- **Visible / Collapsed:** empty. Balanced layout — no
  collapsing.

## Cross-phase integrations

### Phase 76 — Retina Visit Summary

`workspace_profile` block embedded in the response (encounter
type + label + profile code). `audit_disclosure` extended
with the workspace-profile boundary statement.

### Phase 77 — Retina Visit Packet Export

Inherits the workspace profile via the underlying summary;
the packet's audit disclosure now mentions the deterministic-
mapping boundary.

### Phase 82 — Note Validation Rail

`workspace_profile` block embedded in the response so the
rail consumer can colocate validation with the adaptive
workspace context.

### Phase 81 — Provider Action Queue

No behavior change; the queue continues to surface every
specialty signal at its existing priority. The UI consumer
(future enhancement) may filter by profile.

### Encounter list

`GET /encounters` projection now includes `encounter_type`
so the encounter sidebar can display the chip per row.

## Forbidden behaviors (verified)

- ChartNav does NOT autonomously classify the encounter.
- ChartNav does NOT infer subspecialty from imaging.
- ChartNav does NOT diagnose.
- ChartNav does NOT recommend treatment, surgery, injections,
  or medications.
- ChartNav does NOT hide data — lower-priority panels are
  always available via the collapsed `<details>` wrapper.
- Sign attestation is unchanged. Workspace profile changes
  never block signing.

## UI

New module `apps/web/src/features/workspace-profile/`:

- `workspaceProfileTypes.ts` — types.
- `workspaceProfileApi.ts` — `getWorkspaceProfile` + `patchWorkspaceProfile`.
- `WorkspaceProfileResolver.ts` — `useWorkspaceProfile` hook,
  `panelDispositionFor`, `panelOrderIndex` helpers.
- `EncounterTypeBadge.tsx` — chip + admin/clinician-gated
  select for changing the encounter type.

`ClinicalTabbedWorkspace.tsx` Overview tab refactored:

- New `AdaptiveOverviewPanels` component renders every Phase
  78–85 surface in the order chosen by the resolver.
- Collapsed panels render inside a `<details>` element so the
  operator can always expand them. `data-panel-disposition`
  attributes (`prioritized` / `visible` / `collapsed`) expose
  the resolver's decision for testing.
- The badge renders at the top of the Overview grid.

WCAG 2.1 AA contrast preserved.

## Tests

Backend:

- `apps/api/tests/test_workspace_profiles.py` — 13 tests
  covering GET default, PATCH for each of the 4 profiles,
  RBAC, cross-org 404, supported-types matrix, coverage
  invariant (every profile covers every panel exactly once).
- `apps/api/tests/test_workspace_profiles_integrations.py` —
  8 tests covering Phase 76 summary embedding, Phase 77
  packet inheritance, Phase 82 validation embedding,
  `/encounters` list reflection, never-blocks-signing
  safety invariant.

Web:

- `apps/web/src/test/EncounterTypeBadge.test.tsx` — 15
  tests covering the resolver helpers (disposition,
  ordering), badge render, edit visibility gating, PATCH
  flow, error banner, disclosure boundary copy, and
  forbidden-phrase canary sweep.

## Smoke

- `npx tsc --noEmit` — clean.
- `npx vitest run` — 896/896 pass (up from 881).
- `pytest tests/test_workspace_profiles.py
  tests/test_workspace_profiles_integrations.py` — 21/21
  pass.
- Cross-phase backend regression (test_medications +
  integrations, test_disease_staging + integrations,
  test_provider_action_queue, test_note_validation,
  test_note_validation_acknowledgements,
  test_retina_visit_summary, test_retina_visit_packet,
  test_cataract_workflow, test_glaucoma_summary,
  test_anti_vegf_injections) — 160/160 pass.
- All five safety scripts pass.
- `git diff --check` — clean.

## Caveats

- The Phase 86 collapse semantics are visual only. Every
  panel still mounts and fetches its data; the UI just
  presents it inside a closed `<details>` element. This
  preserves the "never hide data" contract but does mean
  the network traffic is identical regardless of the
  active profile.
- `encounter_type` defaults to `comprehensive` on every
  existing encounter via the migration's `server_default`.
  No backfill is needed.
- The resolver mapping is fixed in code. Profile tuning is a
  service change (deliberately — the profile contract is
  part of the safety story).
- The Phase 81 provider action queue does NOT filter by
  profile in this phase. The queue continues to surface
  every signal at its existing bucket; a future enhancement
  could add a profile-driven UI filter, but filtering would
  require a "show all" escape hatch to honor the
  never-hide-data contract.

## Recommended next phase

**Phase 87 — FHIR Export Layer.** A read-only FHIR R4
export surface that projects ChartNav's structured
provider-entered artifacts (encounter, vitals, anti-VEGF
injections, fundus charts, disease stages, medications) as
FHIR resources for downstream interoperability. Safe-claims
boundary: ChartNav does not write FHIR back to upstream
systems, does not submit claims, does not generate or
synthesize FHIR content beyond a deterministic projection
of existing structured rows, and never includes clinical
free text in resources whose schemas don't require it.
