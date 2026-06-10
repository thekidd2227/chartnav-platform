# Phase 88 — Imaging Metadata Review Linkage

**Date:** 2026-06-10
**Branch:** `feature/phase-88-imaging-metadata-review-linkage`
**Base:** `main` after Phase 87 (`24b11e7`)
**Status:** Eleventh Phase 2 Clinical Intelligence surface — imaging metadata visibility + provider-driven review across phases.

## Purpose

Phase 88 makes the **already-existing** imaging study metadata
visible, reviewable, and linked across ChartNav's workflow
surfaces. The Phase 21B `imaging_studies` table already records
modality, eye, captured_at, status, and review actor; Phase 88
adds three optional device-and-source columns
(`device_manufacturer`, `device_model`, `source_system`) and a
new encounter-scoped read + provider-driven review surface, and
folds the metadata signal into Phase 76 summary, Phase 77 packet
export, Phase 79 glaucoma cockpit and Phase 80 cataract workflow
(via the underlying summary), Phase 81 provider action queue,
Phase 86 adaptive workspace, and Phase 87 FHIR DocumentReference.

**This phase is metadata + review linkage only.** ChartNav does
NOT interpret images, does NOT autonomously classify modality or
eye, does NOT infer findings, does NOT diagnose, does NOT
recommend treatment / surgery / injections / medications, and
does NOT bridge DICOM / HL7 / live device streams. The review
state is provider-driven; the deterministic `metadata_hash` on
each row lets downstream consumers (Phase 87 FHIR
DocumentReference) prove the metadata projection has not
shifted.

## Schema

Alembic revision `e3f4a5b6c7d8` extends `imaging_studies` with
three optional, nullable columns:

| Column | Type | Notes |
|---|---|---|
| `device_manufacturer` | string(128) | provider-entered free-form text |
| `device_model` | string(128) | provider-entered free-form text |
| `source_system` | string(128) | provider-entered free-form text |

No new CHECK constraints — manufacturer/model/source_system are
free-form, not closed allowlists. Length is capped at 128 chars
in the application layer.

No new table is created. The existing modality / eye / status /
captured_at / reviewed_by_user_id / reviewed_at columns from
Phase 21B are reused.

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/encounters/{encounter_id}/imaging-metadata` | required | any caller with encounter access |
| `PATCH` | `/api/v1/imaging-metadata/{metadata_id}/review` | required | admin / clinician |

Cross-org returns 404 (no existence leak). The Phase 88 routes
**deliberately do not add a POST**. Imaging study creation
continues to flow through the existing Phase 21B pipeline
endpoints (`POST /patients/{id}/imaging-studies`).

GET response shape (per item):

```jsonc
{
  "id": 1,
  "encounter_id": 1,
  "patient_id": 1,
  "organization_id": 1,
  "modality": "oct_macula",
  "modality_group": "oct",
  "laterality": "OD",
  "acquisition_date": "2026-06-09T14:00:00Z",
  "device_manufacturer": "Heidelberg",
  "device_model": "Spectralis",
  "source_system": "OCT cart 1",
  "review_status": "uploaded",
  "reviewed_by_display": null,
  "reviewed_by_role": null,
  "reviewed_at": null,
  "metadata_hash": "0123…cdef (64 hex)"
}
```

Aggregates: `counts.{total,reviewed,unreviewed}`,
`modality_groups_present`, `by_modality_group`,
`disclosure` carrying boundary copy.

## Modality groups

A Phase-88 workflow-facing taxonomy maps each Phase 21B modality
code into one of:

- `oct` — `oct_macula`, `oct_rnfl`
- `fundus` — `fundus_photo`, `widefield_fundus`
- `visual_field` — `visual_field_24_2`, `visual_field_10_2`
- `biometry` — `biometry_packet`
- `topography` — (none mapped yet; reserved)
- `external_record` — `external_pdf`
- `other` — `other`

This lets glaucoma / cataract / retina surfaces ask "is OCT
metadata on file?" without hard-coding the underlying enum.

## Cross-phase integrations

### Phase 76 — Retina Visit Summary

Adds `imaging_metadata_summary` to the response (counts +
per-group buckets + deterministic `summary_hash`).
`audit_disclosure` extended with the imaging boundary statement.

### Phase 77 — Retina Visit Packet Export

Embeds the same metadata-only `imaging_metadata_summary` —
counts only, no clinical narrative.

### Phase 79 — Glaucoma Progression Cockpit

No service change required — the cockpit already reads
`imaging_studies` for VF and OCT review state. Phase 88 makes
the metadata explicitly visible in the new panel and lets the
queue surface unreviewed items.

### Phase 80 — Cataract Surgical Workflow

No service change required — cataract already references
`imaging_studies` for biometry validation. Phase 88 surfaces
biometry/topography metadata via the new panel and queue items.

### Phase 81 — Provider Action Queue

Adds a `imaging` source with category
`imaging_metadata_unreviewed` for patients whose imaging rows
have not reached `reviewed` status. **Always informational —
never Tier 1.** The item disappears as soon as every row is
marked reviewed.

### Phase 86 — Subspecialty Adaptive Workspace

Adds `imaging_metadata` to `PANEL_CODES` + `PANEL_LABELS`. Per
profile:

- **Retina:** prioritized alongside anti-VEGF + summary + packet.
- **Glaucoma:** prioritized alongside cockpit + medications.
- **Cataract:** prioritized alongside workflow + medications.
- **Comprehensive:** **collapsed but accessible** — the only
  panel collapsed in the comprehensive profile, per the
  Phase 88 spec ("comprehensive profile: collapsed but
  accessible"). The Phase 86 invariant is preserved: every
  panel still appears in `panel_order`; the operator can always
  expand it.

### Phase 87 — FHIR DocumentReference

The `extension` array now includes
`imaging-metadata-summary` carrying `total-count`,
`reviewed-count`, `unreviewed-count`, and `summary-hash`. The
attachment hash is recomputed by the FHIR consumer; the
summary hash lets the consumer detect changes across packets
without enumerating individual rows.

## Forbidden behaviors (verified)

- ChartNav does NOT interpret images.
- ChartNav does NOT autonomously classify modality or
  laterality.
- ChartNav does NOT infer findings from imaging.
- ChartNav does NOT diagnose.
- ChartNav does NOT recommend treatment, surgery, injections,
  or medications.
- ChartNav does NOT bridge DICOM / HL7 / live device streams.
- ChartNav does NOT add image upload via this phase (the
  existing Phase 21B upload path is unchanged).
- The Phase 81 queue item is informational only — never Tier 1.
- The Phase 82 contract is unchanged — no new
  acknowledgement-requiring check is emitted by Phase 88.
- The Phase 86 "never hide data" contract is preserved —
  collapsed-but-accessible.

## UI

New module `apps/web/src/features/imaging-metadata/`:

- `imagingMetadataTypes.ts` — types.
- `imagingMetadataApi.ts` — `getImagingMetadata` +
  `patchImagingMetadataReview`.
- `ImagingMetadataPanel.tsx` — read + review panel with
  per-row Mark reviewed button (admin / clinician via API
  RBAC), counts strip, status pill (green = reviewed,
  amber = ready_for_review, neutral otherwise), boundary
  banner + disclosure rendered verbatim from the server.

Wired into `ClinicalTabbedWorkspace.tsx` Overview tab via the
existing `AdaptiveOverviewPanels` resolver; the action queue
gets a new `imaging` source label.

WCAG 2.1 AA contrast preserved.

## Tests

Backend:

- `apps/api/tests/test_imaging_metadata.py` — 17 tests
  covering GET shape, modality-group bucketing, ordering,
  cross-org 404, unknown 404, PATCH review actor stamping,
  PATCH RBAC + idempotency, metadata hash determinism +
  change-on-review, forbidden-phrase canary, auth required.
- `apps/api/tests/test_imaging_metadata_integrations.py` — 9
  tests covering Phase 76 baseline + populated + review
  reflection, Phase 77 packet embedding, Phase 81 queue
  surfaces + drops + never-Tier-1, Phase 87 FHIR
  DocumentReference imaging-metadata-summary extension.

Web:

- `apps/web/src/test/ImagingMetadataPanel.test.tsx` — 11
  tests covering render, counts, empty, populated rendering,
  Mark-reviewed button gating, PATCH flow, review error
  banner, refresh, API error banner, disclosure boundary
  copy, forbidden-phrase canary sweep.

Phase 86 workspace tests updated to reflect the new
`imaging_metadata` panel + Phase 88 comprehensive contract
(imaging collapsed-but-accessible).

## Smoke

- `npx tsc --noEmit` — clean.
- `npx vitest run` — 907/907 pass (up from 896).
- `pytest tests/test_imaging_metadata.py
  tests/test_imaging_metadata_integrations.py` — 26/26 pass.
- Cross-phase backend regression (workspace_profiles + integrations,
  medications + integrations, disease_staging + integrations,
  provider_action_queue, note_validation,
  note_validation_acknowledgements, retina_visit_summary,
  retina_visit_packet, cataract_workflow, glaucoma_summary,
  anti_vegf_injections, fhir_export, phase_21b_imaging_pipeline)
  — 237/237 pass.
- All five safety scripts pass.
- `git diff --check` — clean.
- Phase63C functional smoke — **not run**; this phase did
  not boot a local stack. Phase63C surfaces unchanged.

## Caveats

- `modality_group` is a Phase-88 workflow-facing taxonomy.
  The underlying `modality` enum from Phase 21B is unchanged;
  Phase 88 maps it. New modalities require both a Phase 21B
  CHECK update and a Phase 88 mapping update.
- `topography` is a reserved group with no underlying
  modality mapped yet. The Phase 21B enum doesn't currently
  carry a `corneal_topography` code; a future migration could
  add one without breaking the Phase 88 contract.
- `metadata_hash` is computed at read time, not persisted. This
  avoids drift but does re-compute on every GET — cheap for the
  per-row hash, but consumers that want immutable references
  should snapshot the value alongside the FHIR
  DocumentReference.
- Phase 88 does NOT add a "needs upload" item to the Phase 81
  queue. The queue only surfaces patients with imaging rows
  whose status is not `reviewed`. Patients with no imaging at
  all do not trigger an item — the Phase 84 disease staging
  queue is the surface for "missing artifact" prompts.
- Phase 87 FHIR DocumentReference embeds the summary hash, not
  the per-row hashes. Per-row integrity is reachable via the
  GET endpoint; the packet-level envelope keeps the attachment
  small.

## Recommended next phase

**Phase 89 — IRIS / MIPS Quality Intelligence.** A
deterministic metadata projection over ChartNav's structured
artifacts (encounters, vitals, anti-VEGF history, disease
stages, medications, imaging review state) into a
report-friendly shape compatible with the AAO IRIS Registry
and CMS MIPS quality measures. Safe-claims boundary: ChartNav
does not submit to IRIS, does not submit to CMS, does not
calculate MIPS scoring, and does not interpret whether a
measure was met — the export surface is structured metadata
only, with provider review required before any downstream
submission. (Specific IRIS / MIPS measure structure is to be
verified clinically before publishing.)
