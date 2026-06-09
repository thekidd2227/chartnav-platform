# Phase 77 — Retina Visit Packet Export

**Date:** 2026-06-09
**Branch:** `feature/phase-77-retina-visit-packet-export`
**Base:** `main` at `8dd8d91` (after Phase 76)
**Closes:** the last Phase-1 polish item (Gate 8 from Phase 75's audit)

## Purpose

Buyer-experience polish: produce a self-describing JSON packet for one
retina visit that the operator can preview, copy to clipboard, or
download as a `.json` file after a demo. Built entirely on top of the
existing Phase 76 aggregator — no new clinical scope, no new artifact
storage, no new lifecycle behavior.

After this PR, the Phase 1 Clinical Spine buyer-demo experience is
complete and Phase 2 Clinical Intelligence (Anti-VEGF, glaucoma
cockpit, FHIR, MIPS) can begin in an isolated phase tree.

## What changed

### Backend

| File | Kind | Description |
|---|---|---|
| `apps/api/app/services/retina_visit_packet.py` | New (~200 lines) | Builds the packet by wrapping `build_summary()` with packet metadata: `schema_version`, `generated_at`, per-section `sha256` integrity hashes, and the 9-item `safety_boundaries` array. Reproducible: same artifact state → same hashes. |
| `apps/api/app/api/retina_visit_packet.py` | New (~34 lines) | Thin FastAPI router exposing `GET /api/v1/encounters/{encounter_id}/retina-visit-packet`. Same auth + cross-org semantics as the rest of the encounter surface (404 on unknown / cross-org). |
| `apps/api/app/main.py` | Modified | Registers the new router. |
| `apps/api/tests/test_retina_visit_packet.py` | New (~200 lines) | 8 pytest cases: baseline, safety-boundary completeness, hash determinism, full-lifecycle reflection, cross-org 404, unknown 404, unauth 401, and a metadata-only canary. |

### Frontend

| File | Kind | Description |
|---|---|---|
| `apps/web/src/features/retina-summary/retinaPacketTypes.ts` | New | Typed packet shape, composed from existing summary types. |
| `apps/web/src/features/retina-summary/retinaSummaryApi.ts` | Modified | Adds `getRetinaVisitPacket()`. Same identity-resolution pattern as the existing summary fetch. |
| `apps/web/src/features/retina-summary/RetinaVisitPacketPanel.tsx` | New (~370 lines) | Build / Copy JSON / Download .json buttons; sealed-state pill; artifact counts + evidence count; integrity-hash list; safety-boundary block; collapsible JSON preview. |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Modified | Wires the packet panel into the Overview tab right after the summary panel — same `nativeEncounter && typeof id === "number"` gate. |
| `apps/web/src/test/RetinaVisitPacketPanel.test.tsx` | New (~260 lines) | 10 vitest cases: pre-build state, build → fetch + render, sealed vs pending state, all 9 safety boundaries, three artifact hashes, preview opens with JSON, clipboard copy with `Copied` flash, download triggers anchor + `URL.createObjectURL`, API error surfaces in banner, forbidden-clinical-text canary. |

## Packet schema (top-level)

```jsonc
{
  "schema_version": "chartnav.retina_visit_packet/1.0",
  "generated_at": "2026-06-09T08:00:00Z",
  "demo_mode": true,
  "encounter": {
    "id": 1, "patient_id": 1, "patient_identifier": "PT-1001",
    "patient_name": "Morgan Lee", "organization_id": 1,
    "status": "in_progress", "started_at": "..."
  },
  "intake":      { "count": 1, "latest_id": 5, "latest_status": "signed", ... },
  "visit_draft": { "count": 1, "latest_id": 3, "latest_status": "finalized", ... },
  "fundus":      { "count": 1, "latest_id": 7, "latest_status": "signed", ... },
  "review_sign_lock": {
    "vitals_signed": true, "visit_draft_signed": true, "fundus_signed": true,
    "all_signed": true, "blockers": []
  },
  "evidence_timeline": [
    { "artifact_type": "vitals_workup", "event_type": "signed", "actor_display_name": "Casey Clinician", "actor_role": "clinician", "ref_id": 5, "timestamp": "..." }
    // ... metadata-only events only
  ],
  "artifact_hashes": [
    { "section": "intake",      "algorithm": "sha256", "hash": "<64-hex>", "hash_short": "<12-hex>" },
    { "section": "visit_draft", "algorithm": "sha256", "hash": "<64-hex>", "hash_short": "<12-hex>" },
    { "section": "fundus",      "algorithm": "sha256", "hash": "<64-hex>", "hash_short": "<12-hex>" }
  ],
  "role_capabilities": { ... },
  "safety_boundaries": [
    { "key": "not_certified_ehr", "asserted": true, "statement": "..." },
    { "key": "not_ehr_replacement", "asserted": true, "statement": "..." },
    { "key": "no_autonomous_diagnosis", "asserted": true, "statement": "..." },
    { "key": "no_autonomous_image_interpretation", "asserted": true, "statement": "..." },
    { "key": "no_autonomous_billing_or_coding", "asserted": true, "statement": "..." },
    { "key": "no_autonomous_signing", "asserted": true, "statement": "..." },
    { "key": "provider_review_required", "asserted": true, "statement": "..." },
    { "key": "no_real_phi", "asserted": true, "statement": "..." },
    { "key": "metadata_only_audit_trail", "asserted": true, "statement": "..." }
  ],
  "audit_disclosure": "ChartNav records metadata-only audit events..."
}
```

## Metadata-only invariant — extended

The packet inherits the Phase 76 aggregator's hard rule: **no clinical
free text in the body**. The aggregator service explicitly never selects
`bp_systolic`, `temperature_value`, `technician_notes`, `transcript_text`,
`draft_note_text`, `findings_json`, `drawing_json`, `rendered_svg`,
`ai_confidence_json`, etc.

The packet adds *one more* layer of integrity: the per-section sha256
content hashes let an external reviewer prove that the artifact metadata
referenced by `latest_id` matches what was issued in the packet. Identical
artifact state → identical hashes; any change to status, signer,
timestamps, warning count, or element count flips the hash.

This is a content-integrity hash, not a security-grade signature.

## Phase 1 Clinical Spine — final matrix

| Gate | Status |
|---|---|
| 1. Laterality / OD-OS support | ✅ Pre-existing |
| 2. `/retina-visit-summary` endpoint | ✅ Phase 76 |
| 3. Retina visit sequence / ribbon | ✅ Phase 71 |
| 4. Physician action rail | ✅ Pre-existing |
| 5. Metadata-only evidence timeline | ✅ Phase 76 |
| 6. Signer/reviewer normalization across V/VD/F | ✅ Phase 75 |
| 7. Demo reset + seeded patient reliability | ✅ Phase 74 |
| 8. Retina visit packet export | ✅ **This PR** |
| 9. Phase 63C smoke stability | ✅ Pre-existing |
| 10. No real PHI / no production LLM / no autonomous claims | ✅ Continuous |

**All 10 Phase 1 gates closed.**

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_retina_visit_packet.py tests/test_retina_visit_summary.py -v` | **15 / 15 PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 793 / 793 tests across 44 files** (was 783; +10 Phase 77) |
| `bash scripts/check_commercial_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/check_demo_claims.sh` | **PASS** — 0 hits |
| `bash scripts/check_website_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/test_claim_policy_fixtures.sh` | **PASS** |
| `python3 scripts/check_runtime_safety.py` | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run in this sandbox (no live API). Behavior
preserved by construction — no API route, schema, service module,
migration, claim policy, demo/capture/smoke script touched.

## Next phase recommendation

**Phase 78 — Anti-VEGF Retina Operating Rail.** First Phase 2 Clinical
Intelligence phase. Now that the Phase 1 buyer-demo experience is
feature-complete, the next phase moves into specialty-specific operating
logic. Anti-VEGF is the highest-leverage retina workflow:

- Interval tracking (last injection → next due window per eye)
- Authorization status (per-payer per-injection prior-auth state)
- Inventory awareness (drug availability heuristics, not pharmacy
  integration)
- Bilateral injection tracking (OD/OS separate intervals)

Per the operator prompt's Phase 2 boundary: still no diagnosis, no
autonomous treatment selection, no autonomous orders, no autonomous
billing, no production LLM. The Anti-VEGF rail is a structured
provider-review surface that mirrors how retina specialists already
track these decisions.
