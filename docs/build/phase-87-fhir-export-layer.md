# Phase 87 — FHIR R4 Export Layer

**Date:** 2026-06-10
**Branch:** `feature/phase-87-fhir-export-layer`
**Base:** `main` after Phase 86 (`283ff02`)
**Status:** Tenth Phase 2 Clinical Intelligence surface — narrow, read-only FHIR R4 export

## Purpose

Phase 87 introduces a narrow, **read-only** FHIR R4 export
projection of ChartNav's structured provider-entered artifacts.
The export surfaces three resources:

- **Patient** — projected from `patients`.
- **Encounter** — projected from `encounters` (+ Phase 86
  workspace-profile + Phase 76 review/sign/lock state).
- **DocumentReference** — the Phase 77 retina visit packet
  delivered as a self-contained base64 inline attachment with
  a SHA-256 integrity envelope.

This is **interoperability, not workflow mutation.** ChartNav
does NOT write to FHIR servers, does NOT sync state, does NOT
push to upstream EHRs, does NOT submit claims, and does NOT
expose a SMART-on-FHIR / OAuth / bulk-export surface. ChartNav
is not a certified EHR.

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/fhir/r4/Patient/{patient_id}` | required | any caller with patient access |
| `GET` | `/api/fhir/r4/Encounter/{encounter_id}` | required | any caller with encounter access |
| `GET` | `/api/fhir/r4/DocumentReference/{encounter_id}` | required | any caller with encounter access |

All responses use `Content-Type: application/fhir+json`.
Cross-org access returns a FHIR `OperationOutcome` 404 (no
existence leak). Auth failures return the same shape ChartNav's
other endpoints return.

## Patient resource

Minimal FHIR R4 Patient projection — no new PHI surface is
opened by this adapter:

- `identifier[0]` — local `patient_identifier`
  (`urn:chartnav:patient-identifier`).
- `identifier[1]` — `external_ref` when present.
- `name[0]` — HumanName with `given`, `family`, `text`.
- `birthDate` — when on file.
- `gender` — normalized to the FHIR `administrative-gender`
  value set (`male` / `female` / `other` / `unknown`).
  Free-form `sex_at_birth` values that don't match fall back
  to `unknown`.
- `active` — boolean.
- `meta.source` — `urn:chartnav:organization:{org_id}`.

## Encounter resource

- `identifier[0]` — encounter id (`urn:chartnav:encounter-id`).
- `identifier[1]` — `external_ref` when present.
- `status` — normalized to the FHIR `encounter-status` value
  set (`planned` / `in-progress` / `finished` / `cancelled` /
  `unknown`).
- `class` — always `AMB` (ambulatory).
- `type[0]` — Coding carrying the Phase 86 subspecialty type
  code (`retina` / `glaucoma` / `cataract` / `comprehensive`).
- `subject` — `Patient/{patient_id}` reference.
- `participant[0]` — provider as `display` with the
  `v3-ParticipationType` ATND code.
- `period.start` / `period.end` — from `started_at` /
  `completed_at`.
- `extension` — Two extensions:
  - `…/StructureDefinition/review-sign-lock` carrying four
    booleans (vitals_signed, visit_draft_signed,
    fundus_signed, all_signed) projected from the Phase 76
    summary.
  - `…/StructureDefinition/workspace-profile` carrying the
    Phase 86 profile code as `valueCode`.

## DocumentReference resource

The Phase 77 retina visit packet projected as a DocumentReference:

- `id` — `retina-visit-packet-{encounter_id}`.
- `meta.versionId` — packet schema version
  (`chartnav.retina_visit_packet/1.0`).
- `status` — `current`.
- `docStatus` — `final` when all artifacts are signed, else
  `preliminary`.
- `identifier[0]` — packet identity (`urn:chartnav:retina-visit-packet`).
- `identifier[1]` — packet hash hex
  (`urn:chartnav:packet-hash:sha256`).
- `type` — LOINC `11506-3` (Progress note) plus a ChartNav
  `retina-visit-packet` coding.
- `subject` — `Patient/{patient_id}` reference.
- `context.encounter[0]` — `Encounter/{encounter_id}` reference.
- `content[0].attachment` — inline base64 of the canonical
  packet JSON, sized correctly, with `hash` set to
  base64-of-sha256-bytes.
- `extension[…/packet-integrity]` — algorithm (`sha256`),
  packet hash hex, byte length, generated_at, and the
  all-signed boolean. A consumer can independently verify the
  attachment matches by recomputing sha256 over the decoded
  bytes.

## Out-of-scope (intentionally NOT implemented)

- HL7 v2 message interfaces.
- Write-back to upstream EHRs (no `POST` / `PUT` / `PATCH` /
  `DELETE` FHIR routes).
- Bidirectional sync.
- SMART-on-FHIR launch / OAuth provider flows
  (`.well-known/smart-configuration` returns 404).
- Bulk export (`$export`, NDJSON) — returns 404.
- New PHI fields beyond what the existing non-FHIR API exposes.

The read-only contract is verified by tests
(`test_no_fhir_post_route_exists_for_patient`,
`test_no_fhir_put_route_exists_for_patient`,
`test_no_fhir_bulk_export_route_exists`,
`test_no_smart_metadata_route_exists`).

## Files added

```
apps/api/app/fhir/__init__.py
apps/api/app/fhir/patient_adapter.py
apps/api/app/fhir/encounter_adapter.py
apps/api/app/fhir/document_reference_adapter.py
apps/api/app/fhir/routes_fhir.py
apps/api/tests/test_fhir_export.py
docs/build/phase-87-fhir-export-layer.md
```

Files modified:

```
apps/api/app/main.py   # register fhir_router
```

## Auth + org isolation

- Reuses `require_caller`. Every authenticated org member
  (admin / clinician / technician / reviewer / front_desk)
  can read.
- Cross-org access returns a FHIR `OperationOutcome` 404 — no
  existence leak between tenants.
- Unauthenticated requests return 401/403 as the rest of the
  API does.

## Tests

`apps/api/tests/test_fhir_export.py` — 28 tests covering:

- Patient resource shape, gender normalization, external_ref
  identifier, unknown-id 404, cross-org 404, auth required.
- Encounter resource shape, workspace-profile extension,
  review/sign/lock extension, Phase 86 type reflection,
  unknown-id 404, cross-org 404, auth required.
- DocumentReference shape, base64 attachment round-trip,
  packet-hash-hex extension consistency, secondary identifier
  with packet hash, unknown-id 404, cross-org 404, auth
  required.
- Read-only contract: no POST/PUT routes, no $export, no
  SMART discovery.
- Every authenticated role can read each resource.

## Smoke

- `pytest tests/test_fhir_export.py` — 28/28 pass.
- Cross-phase backend regression (workspace_profiles,
  medications + integrations, disease_staging + integrations,
  provider_action_queue, note_validation,
  note_validation_acknowledgements, retina_visit_summary,
  retina_visit_packet, cataract_workflow, glaucoma_summary,
  anti_vegf_injections) — 181/181 pass.
- All five safety scripts pass:
  - `check_commercial_claims.sh`
  - `check_demo_claims.sh`
  - `check_website_claims.sh`
  - `test_claim_policy_fixtures.sh`
  - `check_runtime_safety.py`
- `git diff --check` — clean.
- Phase63C functional smoke — **not run**; this phase did
  not boot a local stack. The Phase63C contract is preserved
  by the unchanged Phase63C surfaces.

## Caveats

- The Patient `gender` mapping is conservative. ChartNav's
  underlying `sex_at_birth` column is free-form text; any
  value outside the canonical FHIR
  `administrative-gender` set falls back to `unknown`. This
  preserves resource validity but may hide site-specific
  vocabulary the customer expected to round-trip.
- The DocumentReference attachment is inline base64. For
  very large packets a future enhancement could provide a
  Binary endpoint, but the current packet shape is
  metadata-only and modest in size.
- The packet generation re-runs `build_packet` on every
  DocumentReference request. The Phase 77 packet is
  deterministic over encounter state, so the result is
  reproducible — but this is not cached.
- FHIR R4 is the only version exported. R5 / STU3 are out of
  scope.
- The export adapter intentionally does NOT publish a FHIR
  `CapabilityStatement`. Capability discovery is out of scope
  to keep the surface narrow.

## Recommended next phase

**Phase 88 — Device and Imaging Metadata Linkage.** A
deterministic metadata linkage layer that ties existing
imaging pipeline records (Phase 21B) to provider-entered
device-and-modality metadata (manufacturer, serial number,
acquisition date, study UID echoes — without re-uploading
imagery). Safe-claims boundary: ChartNav does not interpret
imaging, does not auto-classify modality, does not bridge
DICOM stores, and does not infer device identity from
images — every device row is provider-entered structured
metadata that the linkage surface joins by deterministic
key.
