# Phase 76 — Retina Visit Summary Aggregator + Cross-Artifact Timeline

**Date:** 2026-06-09
**Branch:** `feature/phase-76-retina-visit-summary-timeline`
**Base:** `main` at `167fa51` (after Phase 75)
**Closes:** Phase 1 Clinical Spine Gates 2 and 5

## Purpose

Add the missing cross-artifact aggregator endpoint and cross-artifact metadata-only timeline component that Phase 75's completion audit identified as the last two open gates for Phase 1 Clinical Spine. After this PR merges, Phase 1 is formally closed and Phase 2 Clinical Intelligence work can begin in an isolated phase tree.

## What changed

### Backend

- **New `apps/api/app/services/retina_visit_summary.py`** — pure aggregation service. Joins encounter + vitals workups + scribe sessions + fundus charts + users into a single response. Builds the metadata-only chronological timeline.
- **New `apps/api/app/api/retina_visit_summary.py`** — thin FastAPI router exposing `GET /api/v1/encounters/{encounter_id}/retina-visit-summary`.
- **`apps/api/app/main.py`** — registers the new router.
- **New `apps/api/tests/test_retina_visit_summary.py`** — 7 tests covering happy path, cross-org 404, role capability shape, full lifecycle reflection, metadata-only canary (no clinical free text leaks), unauthenticated 401, unknown encounter 404.

### Frontend

- **New `apps/web/src/features/retina-summary/retinaSummaryTypes.ts`** — typed response shape mirroring the backend.
- **New `apps/web/src/features/retina-summary/retinaSummaryApi.ts`** — fetch wrapper following the project's identity-resolution + API_URL pattern.
- **New `apps/web/src/features/retina-summary/RetinaVisitSummaryPanel.tsx`** — read-only panel rendering: encounter meta, three artifact cards (Vitals / VisitDraft / Fundus with status pills), blockers list (or "all signed" empty banner), role-capability hint, metadata-only evidence timeline, and the API's audit-disclosure line verbatim.
- **`apps/web/src/ClinicalTabbedWorkspace.tsx`** — wires the panel into the Overview tab as a wide section, rendered only for native encounters with numeric IDs.
- **New `apps/web/src/test/RetinaVisitSummaryPanel.test.tsx`** — 10 vitest cases covering baseline render, three artifact cards, blockers + empty-blockers states, role explainer, audit disclosure, forbidden-text canary, timeline event rendering, refresh interaction, and error surfacing.

## Response shape

```jsonc
GET /api/v1/encounters/1/retina-visit-summary
{
  "encounter_id": 1,
  "patient_id": 1,
  "organization_id": 1,
  "patient_identifier": "PT-1001",
  "patient_name": "Morgan Lee",
  "encounter_status": "in_progress",
  "encounter_started_at": "2026-...",
  "demo_mode": true,
  "vitals":      { "count": 1, "latest_id": 5, "latest_status": "signed", "latest_signed_at": "...", "latest_warning_count": 0 },
  "visit_draft": { "count": 1, "latest_id": 3, "latest_status": "finalized", "latest_finalized_at": "..." },
  "fundus":      { "count": 1, "latest_id": 7, "latest_status": "signed", "latest_signed_at": "...", "latest_warning_count": 1, "latest_element_count": 3, "latest_laterality": "OD" },
  "blockers": [],
  "role_capabilities": {
    "role": "clinician",
    "can_review": true,
    "can_sign": true,
    "can_create_intake": true,
    "explainer": "Clinician can review and sign clinical artifacts."
  },
  "evidence_timeline": [
    { "artifact_type": "vitals_workup", "event_type": "created", "timestamp": "...", "ref_id": 5, "actor_display_name": "Taylor Technician", "actor_role": "technician", "warning_count": 0 },
    { "artifact_type": "vitals_workup", "event_type": "signed",  "timestamp": "...", "ref_id": 5, "actor_display_name": "Casey Clinician",  "actor_role": "clinician",  "warning_count": 0 },
    { "artifact_type": "fundus_chart",  "event_type": "signed",  "timestamp": "...", "ref_id": 7, "actor_display_name": "Casey Clinician",  "actor_role": "clinician",  "laterality": "OD", "element_count": 3, "warning_count": 1 }
  ],
  "audit_disclosure": "ChartNav records metadata-only audit events: who created, reviewed, and signed each artifact, and when. The audit trail does not store clinical free text (no transcripts, BP/IOP/VA values, chief complaint, HPI, or findings text)."
}
```

## Metadata-only invariant

Hard rule enforced at both the aggregator service and the test layer: **no clinical free text** ever appears in the response. The aggregator service explicitly never selects:

- vitals body fields (`bp_systolic`, `bp_diastolic`, `temperature_value`, `pulse`, etc., `technician_notes`)
- scribe body fields (`source_text`, `transcript_text`, `draft_note_text`, `structured_note_json`, `review_notes`)
- fundus body fields (`findings_json`, `drawing_json`, `rendered_svg`, `ai_confidence_json`)

The backend test `test_timeline_contains_no_clinical_free_text` writes a canary `technician_notes` value plus BP/temp values, fetches the aggregator, and asserts none of them appear in the JSON response. The frontend test `does NOT render any forbidden clinical free-text fragments` does the same DOM sweep on the rendered panel.

## Phase 1 Clinical Spine — closeout

Per `docs/build/phase-75-completion-gate-core-closeout.md`:

| Gate | Status |
|---|---|
| 1. Laterality / OD-OS support | ✅ Pre-existing |
| 2. `/retina-visit-summary` endpoint | ✅ **Closed by this PR** |
| 3. Retina visit sequence / ribbon | ✅ Phase 71 |
| 4. Physician action rail | ✅ Pre-existing |
| 5. Metadata-only evidence timeline | ✅ **Closed by this PR** (cross-artifact view) |
| 6. Signer/reviewer normalization across V/VD/F | ✅ Phase 75 |
| 7. Demo reset + seeded patient reliability | ✅ Phase 74 |
| 8. Retina visit packet export | ❌ Deferred to **Phase 77** (now a polish phase, not a spine requirement) |
| 9. Phase 63C smoke stability | ✅ Pre-existing |
| 10. No real PHI / no production LLM / no autonomous claims | ✅ Continuous |

**Phase 1 Clinical Spine is functionally closed after this PR merges.** Gate 8 (visit packet export) is a buyer-experience polish that depends on this aggregator's output and can be addressed in a follow-up phase without blocking Phase 2 work.

## Out of scope (explicit)

- Anti-VEGF interval / auth / inventory rail (Phase 2 — Clinical Intelligence)
- Glaucoma progression cockpit (Phase 2)
- FHIR writethrough (Phase 2 — Interoperability)
- MIPS / IRIS quality capture (Phase 2 — Quality reporting)
- Production LLM (explicitly forbidden by every phase prompt and runtime safety validator)
- Cataract surgical workflow (Phase 2)

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_retina_visit_summary.py -v` | **7 / 7 PASS** |
| `python3 -m pytest tests/test_vitals_workup.py tests/test_fundus_charts.py tests/test_ambient_documentation.py tests/test_clinical.py` | **122 / 122 PASS** (regression check on directly-related suites) |
| `cd apps/web && npx tsc --noEmit` | **PASS** |
| `cd apps/web && npx vitest run` | **PASS — 783 / 783 tests** (was 773; +10 Phase 76) |
| `bash scripts/check_commercial_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/check_demo_claims.sh` | **PASS** — 0 hits |
| `bash scripts/check_website_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/test_claim_policy_fixtures.sh` | **PASS** |
| `python3 scripts/check_runtime_safety.py` | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox).

## Next phase recommendation

**Phase 77 — Retina Visit Packet Export.** Frontend-driven (with optional backend convenience endpoint) packet builder that consumes the Phase 76 aggregator's output and produces a printable/shareable visit summary the buyer can circulate after a demo. Per Phase 70 §3 and Phase 75 deferral matrix.

After Phase 77, the entire Phase 1 buyer-demo experience is feature-complete and Phase 2 Clinical Intelligence work can begin.
