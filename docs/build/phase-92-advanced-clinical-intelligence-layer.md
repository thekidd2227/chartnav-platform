# Phase 92 — Advanced Clinical Intelligence Layer

**Date:** 2026-06-11
**Branch:** `claude/chartnav-security-integration-dC89C`
**Base:** `main` after Phase 91
**Status:** Pure aggregation + projection layer — no new schema, no new clinical intelligence, no new autonomy.

## Purpose

Phase 92 merges the previously-separate workstreams 94–97 into a single
provider-reviewed projection layer. The Advanced Clinical Intelligence
panel renders four longitudinal sections from already-existing
Phase 78–91 structured data:

1. **Retina progression** — per-eye anti-VEGF injection cadence,
   AMD / DME / DR stage history, fundus chart counts, imaging
   metadata projection.
2. **Glaucoma longitudinal** — POAG stage history + adherence
   signals (medication count, refill gaps, active safety events).
3. **Cataract conversion** — per-eye workflow record state +
   five-step metadata-only funnel (any record → planned date →
   biometry review → consent → post-op day 1).
4. **FHIR / export readiness** — metadata-only packet renderability
   chip, extensions present, submission status pinned to
   `not_submitted`, transport pinned to `none`.

ChartNav does NOT diagnose, does NOT interpret images, does NOT
recommend treatment, does NOT submit anything to registries, payers,
CMS endpoints, IRIS feeds, or EHRs. Every section is a metadata
projection. Missing data renders as explicit `insufficient_data`
banners with no synthesized values.

## Hard rules (verbatim from the phase brief)

- Do not create new autonomous clinical decision-making.
- Do not create diagnosis.
- Do not interpret images.
- Do not recommend treatment / surgery / medication changes.
- Do not submit anything to registries, payers, CMS, IRIS, or EHRs.
- Do not process real PHI.
- Do not use production LLM.
- Do not create marketing pages.

## Schema

**No new tables. No new columns. No migration.** Phase 92 is a pure
read-side projection — the service reads from existing Phase 78–91
tables (`anti_vegf_injections`, `disease_staging`, `fundus_charts`,
`imaging_metadata`, `glaucoma_*`, `medications`,
`cataract_workflow_records`, `encounters`) and renders the projection
inline.

## Endpoint

| Method | Path | RBAC |
|---|---|---|
| `GET` | `/api/v1/encounters/{id}/advanced-clinical-intelligence` | any caller in the encounter's org |

Cross-org access returns `404` with `encounter_not_found`.
Unknown encounter returns `404`.

## Response shape

```jsonc
{
  "encounter_id": 1,
  "organization_id": 1,
  "patient_id": 1,
  "patient_identifier": "PT-1001",
  "patient_name": "Morgan Lee",
  "encounter_type": "comprehensive",
  "visit_mode": "follow_up",          // surfaced from Phase 91
  "active_laterality": "OU",          // surfaced from Phase 91
  "retina_summary": {
    "od": { "injection_count": 0, "latest_injection_date": null,
            "latest_interval_weeks": null,
            "latest_authorization_status": null,
            "insufficient_data": true },
    "os": { ... },
    "stage_history": [...],
    "stage_history_count": 0,
    "fundus_chart_count": 0,
    "fundus_chart_latest": null,
    "imaging_metadata_summary": {...},
    "data_limitations": [...],
    "insufficient_data": true
  },
  "glaucoma_summary": {
    "od": {...}, "os": {...},
    "poag_stage_history": [...],
    "poag_stage_history_count": 0,
    "adherence_signals": {
      "active_medication_count": 0,
      "refill_gap_count": 0,
      "active_safety_event_count": 0
    },
    "data_limitations": [...],
    "insufficient_data": true
  },
  "cataract_summary": {
    "od": { "record_count": 0, "insufficient_data": true },
    "os": {...},
    "conversion_funnel": {
      "any_record": false,
      "planned_date_present": false,
      "biometry_review_complete": false,
      "consent_signed": false,
      "post_op_day_1_complete": false
    },
    "data_limitations": [...],
    "insufficient_data": true
  },
  "fhir_export_readiness": {
    "packet_renderable": true,
    "document_reference_id": "retina-visit-packet-1",
    "schema_version": "chartnav.retina_visit_packet/1.0",
    "all_signed": false,
    "extensions_present": [...],
    "submission_status": "not_submitted",
    "transport": "none",
    "boundary": "ChartNav does not submit, transmit, or post this packet ...",
    "insufficient_data": false
  },
  "data_limitations": [...],
  "safety_boundaries": [
    { "key": "no_autonomous_diagnosis", "asserted": true, ... },
    { "key": "no_image_interpretation", "asserted": true, ... },
    { "key": "no_treatment_recommendation", "asserted": true, ... },
    { "key": "no_submission", "asserted": true, ... },
    { "key": "metadata_only", "asserted": true, ... }
  ],
  "generated_at": "2026-06-09T12:00:00Z",
  "demo_mode": true,
  "submission_status": "not_submitted",
  "disclosure": "Advanced Clinical Intelligence ... metadata projection."
}
```

## Workspace integration

Phase 92 registers a new `advanced_clinical_intelligence` panel code
in the Phase 86 workspace profile resolver. Every profile bucket
explicitly includes the panel so the UI never silently drops it:

| Profile | Bucket |
|---|---|
| `retina` | prioritized |
| `glaucoma` | prioritized |
| `cataract` | prioritized |
| `comprehensive` | prioritized |

The `AdvancedClinicalIntelligencePanel` React component mounts inside
the Phase 86 `AdaptiveOverviewPanels` on the Overview tab and
inherits the Phase 91 `WorkspaceStateProvider` context for visit-mode
+ laterality chips.

## Phase 77 packet integration

`build_packet` now embeds a slim
`advanced_clinical_intelligence_summary` block on the retina visit
packet with these keys: `retina_present`, `glaucoma_present`,
`cataract_present`, `fhir_export_renderable`, `submission_status`
(pinned to `not_submitted`), `boundary_note`, `insufficient_data`.

## Test coverage

- **Backend:** `apps/api/tests/test_advanced_clinical_intelligence.py`
  — 19 tests covering baseline insufficient-data, safety boundary
  assertion, disclosure language, data limitations, cross-org 404,
  unknown encounter 404, retina anti-VEGF + stage-history reflection,
  retina forbidden-language canary, glaucoma POAG + adherence signals,
  glaucoma forbidden-language canary, cataract record + conversion
  funnel, cataract forbidden-language canary, FHIR readiness +
  extensions + no-submission canary, Phase 91 visit-mode + laterality
  reflection, Phase 77 packet embedding.
- **Backend:** `apps/api/tests/test_workspace_profiles.py` —
  `_KNOWN_PANELS` invariant expanded to include
  `advanced_clinical_intelligence`; all 13 tests continue to pass.
- **Frontend:** `apps/web/src/test/AdvancedClinicalIntelligencePanel.test.tsx`
  — 12 tests covering header + banner + refresh, context chips,
  five safety boundaries surfaced, disclosure safe-claims language,
  OD/OS insufficient-data banners, anti-VEGF + interval rendering,
  POAG + adherence rendering, conversion funnel chips, FHIR readiness
  chips + extensions + boundary, refresh refetch, error banner,
  forbidden-phrase canary covering autonomy, interpretation,
  treatment, submission language.

Totals: **32 backend tests** in scope green;
**959 frontend tests** (all suites) green; **TypeScript** clean.

## Files

### New
- `apps/api/app/services/advanced_clinical_intelligence.py`
- `apps/api/app/api/advanced_clinical_intelligence.py`
- `apps/api/tests/test_advanced_clinical_intelligence.py`
- `apps/web/src/features/advanced-clinical-intelligence/advancedClinicalIntelligenceTypes.ts`
- `apps/web/src/features/advanced-clinical-intelligence/advancedClinicalIntelligenceApi.ts`
- `apps/web/src/features/advanced-clinical-intelligence/AdvancedClinicalIntelligencePanel.tsx`
- `apps/web/src/test/AdvancedClinicalIntelligencePanel.test.tsx`
- `docs/build/phase-92-advanced-clinical-intelligence-layer.md`

### Modified
- `apps/api/app/main.py` — register the new router.
- `apps/api/app/services/retina_visit_packet.py` — embed the
  `advanced_clinical_intelligence_summary` block.
- `apps/api/app/services/workspace_profiles.py` — add
  `advanced_clinical_intelligence` to `PANEL_CODES`, `PANEL_LABELS`,
  and every profile bucket.
- `apps/api/tests/test_workspace_profiles.py` — expand
  `_KNOWN_PANELS`.
- `apps/web/src/features/workspace-profile/workspaceProfileTypes.ts`
  — extend `PanelCode` union.
- `apps/web/src/ClinicalTabbedWorkspace.tsx` — wire the panel into
  `AdaptiveOverviewPanels`.

## Risks closed

- No new autonomy. The service is pure aggregation over already-
  provider-entered structured data.
- No image interpretation. The retina section embeds the imaging
  metadata projection only — modality, modality group, review state.
- No new submission path. `submission_status` is pinned to
  `not_submitted` and `transport` to `none`; the FHIR readiness
  chip explicitly states the packet is metadata-only.
- No real PHI surfaces touched. The service reuses existing
  org-scoped Phase 78–91 services that already enforce the demo-only
  invariant.
