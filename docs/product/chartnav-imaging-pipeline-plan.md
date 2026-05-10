# ChartNav Imaging Pipeline — Plan

> **Phase scope target:** Phase 21B (build), Phase 20A (this plan).
> **Type:** Planning only. No tables, no migrations, no code, no
> claimed device integrations.

The current image-handling surface in ChartNav is **the OD/OS
retinal canvas** (`chart_artifacts` + `RetinalDrawingCanvas` +
`EyeDiagramPanel` + retinal proposal engine). That surface is
strong — version chain, immutable signing, AI proposal review
with provenance. But it only covers **clinician-drawn
annotations**. It does not handle the **device-derived imaging
study** layer the practice already runs upstream:

- OCT macula
- OCT RNFL
- Fundus photo (CFP)
- Optos widefield
- HVF 24-2 / HVF 10-2
- IOLMaster / biometry packet
- External PDF reports
- (future) DICOM-based modalities

This plan defines a **metadata + review pipeline** for those
device-derived studies. It is explicit about what's metadata
vs. what's actual ingestion, and it does not claim integrations
that do not exist.

## What this plan is not

- ❌ Not a DICOM PACS replacement
- ❌ Not a Cirrus / Spectralis / Triton / Optos / IOLMaster
  integration claim — every device adapter listed below is
  **future / planned** unless a specific PR ships the adapter
- ❌ Not an automatic image-interpretation system (no auto-
  measurement of cup-to-disc, central macular thickness, RNFL
  thickness, etc.)
- ❌ Not an auto-routing-to-physician system without human
  review
- ✅ A metadata + review-workflow layer that captures imaging
  study existence, links it to encounter + patient + eye, and
  routes it to a human review queue

## Existing surfaces this plan extends

| Existing | This plan adds |
|---|---|
| `chart_artifacts` (retinal canvas; immutable signing chain) | Sits **downstream** of imaging review. Clinician opens a fundus photo from `imaging_files`, annotates findings on the OD/OS canvas, signs the artifact. |
| `EyeDiagramPanel.tsx` (load/list/sign/fork) | New "Open from imaging study" entry point lets the clinician start a canvas session pre-loaded with a study reference. |
| `RetinalProposalReview.tsx` + `services/retinal_proposals.py` | Unchanged. Proposals still derived from clinician-authored findings text, never from raw images. |
| `extracted_findings` | Imaging metadata (study performed, eye, modality, performed_at) becomes a structured field that can flow into `extracted_findings` for the encounter. |
| `note_versions` | A signed retinal artifact can reference its source `imaging_files.id` so the audit trail is complete. |
| `ai_governance_log` (PHI-redacted) | Any AI-derived content from imaging metadata (e.g., a future structured-finding extractor) writes a governance row, never raw image data. |

## Proposed tables

### `imaging_studies`

One row per device-derived imaging study attached to an encounter.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `encounter_id` | int FK | nullable; some studies are pre-visit imports |
| `modality` | string | `oct_macula` \| `oct_rnfl` \| `fundus_photo` \| `optos_widefield` \| `hvf_24_2` \| `hvf_10_2` \| `octopus_vf` \| `iolmaster` \| `biometry_packet` \| `external_pdf` \| `other` |
| `eye` | string | `OD` \| `OS` \| `OU` \| `n/a` |
| `status` | string | `pending_upload` \| `uploaded` \| `awaiting_review` \| `reviewed` \| `archived` |
| `captured_at` | datetime | study acquisition time (from device or manual) |
| `reviewed_by_user_id` | int FK | nullable |
| `reviewed_at` | datetime | nullable |
| `notes` | text | clinician review note (short — full A/P in note_versions) |
| `created_at`, `updated_at` | datetime | |

### `imaging_files`

Per-study file rows. Most studies are 1 file; OCT scans can have
2–6 files (OD/OS + report PDF). Files **stored** behind a
practice-controlled storage URI — never embedded in the row.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `study_id` | int FK | |
| `file_kind` | string | `image` \| `report_pdf` \| `raw_export` |
| `storage_uri` | string | opaque URI (s3://, file://, gs://, etc.); ChartNav does not assume a specific backend |
| `file_name` | string | original device filename |
| `content_type` | string | MIME type |
| `size_bytes` | int | |
| `checksum_sha256` | string | for tamper-evidence |
| `created_at` | datetime | |

### `imaging_measurements`

Structured measurement rows extracted from imaging studies.
**Every row carries a `source` column** so the chart of origin
is auditable — `device_export` for raw vendor exports,
`manual_entry` for clinician-typed values, `pdf_extracted` for
parsed PDF text. **Never** `auto_inferred` without explicit
provider acceptance.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `study_id` | int FK | |
| `measurement_type` | string | `central_macular_thickness` \| `rnfl_thickness_avg` \| `rnfl_thickness_quadrant_<n>` \| `cup_to_disc_ratio` \| `axial_length` \| `keratometry_k1` \| `keratometry_k2` \| `pachymetry_central` \| `vf_md` \| `vf_psd` |
| `eye` | string | `OD` \| `OS` |
| `value` | string | stored as string for unit flexibility (e.g., "0.7", "240", "23.45") |
| `unit` | string | `microns` \| `mmHg` \| `mm` \| `D` \| `dB` \| `ratio` |
| `source` | string | `device_export` \| `manual_entry` \| `pdf_extracted` |
| `created_at` | datetime | |

## Modality coverage

| Modality | Covered? | Notes |
|---|---|---|
| OCT macula | ✅ metadata | Provider-uploaded; future: vendor adapter |
| OCT RNFL | ✅ metadata | Provider-uploaded; future: vendor adapter |
| Fundus photo (CFP) | ✅ metadata + image storage | Manual or future device-export |
| Optos widefield | ✅ metadata + image storage | Manual or future Optos adapter |
| HVF 24-2 | ✅ metadata + report PDF | PDF parser is future / planned |
| HVF 10-2 | ✅ metadata + report PDF | Same |
| Octopus VF | ✅ metadata + report PDF | Same |
| IOLMaster / biometry packet | ✅ metadata + packet PDF | Manual or future IOLMaster adapter; **ChartNav does not select IOL power** |
| External PDF report | ✅ generic | For modalities not yet enumerated |
| DICOM-native viewer | ❌ not in scope | Future phase if pursued |

## How OCT / fundus / VF / biometry files become encounter-linked review items

1. **Upload** — `POST /imaging-studies/{id}/files` with the file
   bytes (multipart) + `file_kind`. ChartNav writes the file to
   the practice's configured storage backend, computes
   `checksum_sha256`, sets `study.status = 'uploaded'`.
2. **Surface in queue** — `study.status = 'uploaded'` flips to
   `awaiting_review` once the encounter the study belongs to is
   in MD-ready or in-progress status. A
   `work_queue_items.queue_type = 'imaging_review'` row is
   created, scoped to the encounter's assigned provider.
3. **Review** — clinician opens the study (image viewer for
   fundus/Optos; PDF viewer for VF reports), enters
   `reviewed_at`, optionally records review notes.
4. **Annotate (retina path only)** — for fundus / Optos studies
   the clinician can launch the OD/OS retinal canvas pre-loaded
   with a thumbnail of the study. Annotations land on a new
   `chart_artifacts` row; the artifact stores
   `source_imaging_study_id` so the audit trail links back.
5. **Sign** — when the clinician signs the canvas artifact, the
   imaging study transitions to `reviewed`. Provider review
   complete.
6. **Audit** — every step writes a `security_audit_events` row
   (metadata-only — study_id, action, no clinical body).

## How `reviewed_by_user_id` / `reviewed_at` feed work queues

A study in `awaiting_review` status creates / updates an
`imaging_review` work-queue item. The Reviewer Dashboard and
Doctor Dashboard both surface this lane. Once
`reviewed_at IS NOT NULL` the queue item completes
automatically. SLA aging is computed from `study.captured_at` →
`reviewed_at`.

## How imaging connects to the specialty modules

| Specialty module | Imaging pipeline connection |
|---|---|
| Retina (`retina_tracking`) | `last_oct_at` / `last_fundus_at` are bumped from imaging_studies; an OCT macula upload on a wet-AMD patient triggers an `md_ready` queue item |
| Glaucoma (`glaucoma_tracking` + `glaucoma_visual_field_tests`) | OCT RNFL upload → `glaucoma_tracking.rnfl_status` requires clinician review; HVF upload → `glaucoma_visual_field_tests` row + work-queue item |
| Cataract (`cataract_tracking`) | IOLMaster packet upload → `cataract_tracking.iolmaster_packet_uri` set; `md_ready` queue for IOL selection (clinician-driven) |
| Cornea (`cornea_tracking`) | External topography PDF upload → review queue + manual entry of K-max / pachymetry into `cornea_tracking` |
| Oculoplastics, Pediatric | Lower-volume; same generic pipeline |

## Where the existing retinal canvas sits in this pipeline

The existing `RetinalDrawingCanvas` + `EyeDiagramPanel` sit
**downstream** of imaging review. The flow:

```
imaging_studies (fundus/Optos/OCT) → reviewed by clinician
                                    ↓
                    optional: launch RetinalDrawingCanvas
                                    ↓
                    chart_artifacts row (signed, immutable)
                                    ↓
                    (existing) RetinalProposalReview + auto-summary
                                    ↓
                    note_versions reference the artifact
```

The retinal canvas remains the system of record for **clinician-
drawn annotations**. Imaging studies are the system of record for
**device-derived files**. The two are linked but not merged.

## Required APIs (Imaging)

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /patients/{id}/imaging-studies` | clinician/reviewer/admin | list patient studies |
| `POST /patients/{id}/imaging-studies` | clinician/technician | create study record (often before files arrive) |
| `GET /imaging-studies/{id}` | clinician/reviewer | study detail |
| `PATCH /imaging-studies/{id}` | clinician | update notes / status |
| `POST /imaging-studies/{id}/files` | clinician/technician | upload file (multipart) |
| `PATCH /imaging-studies/{id}/review` | clinician | mark reviewed_at / set notes |

Audit rows on every write. Read endpoints filter by org +
optional location. File uploads enforce a max-size + content-type
allowlist. **Files themselves never appear in audit rows** — only
checksum + size + content-type.

## PHI + storage controls before real image files ship

Before any real image bytes are accepted in production:

1. Storage backend must be PHI-grade (clinic-controlled S3 with
   server-side encryption, access logging, IAM scoping).
2. Audit retention configured (`CHARTNAV_AUDIT_RETENTION_DAYS`).
3. File-size + content-type allowlist enforced at the upload
   handler.
4. Checksum recorded for every file (already in schema).
5. Access logs emitted on every file fetch (signed URL flow if
   applicable).
6. Tenant isolation enforced on storage URI prefix
   (`s3://chartnav-imaging/<organization_id>/...`).
7. No file content ever appears in `security_audit_events.detail`
   or `ai_governance_log.prompt_hash` — those stay metadata.
8. Real-PHI rollout is gated on a separate Phase 22+ legal /
   security review checklist. Demo / pilot mode operates on
   redacted / synthetic image fixtures only.

## Required tests

- Migration up/down on SQLite + Postgres
- Org isolation on study + file reads
- Cross-org file fetch returns 404 (no existence leak)
- RBAC: technician can upload, clinician can review + annotate,
  reviewer is read-only on imaging
- Checksum mismatch on file write returns 422
- Max file size enforced
- Content-type allowlist enforced
- Review state transitions (pending_upload → uploaded →
  awaiting_review → reviewed → archived) atomic
- `reviewed_at` write triggers `work_queue_items` completion
- Imaging metadata flows into specialty tracking (retina /
  glaucoma) only when the relevant tracking row exists
- Audit log row contains study_id + action only — never file
  content, never measurement values, never clinician notes
- Forbidden phrasing scan: every imaging-related UI string —
  no "automatic measurement", no "AI-detected", no
  "auto-graded" labels on shipped surfaces

## Hard constraints

- ❌ ChartNav does not auto-measure central macular thickness,
  RNFL thickness, axial length, or any device-derived metric
- ❌ ChartNav does not auto-detect glaucoma progression from VF
  reports
- ❌ ChartNav does not auto-detect AMD progression from OCT
  series
- ❌ ChartNav does not select IOL power from IOLMaster packets
- ❌ ChartNav does not transmit imaging files to external
  systems without explicit clinician + admin confirmation
- ❌ ChartNav does not claim a real device integration in
  marketing copy until the adapter ships and is in this plan's
  "Modality coverage" table marked ✅ device-export
- ✅ Every measurement row carries a `source` column so the
  chart of origin (manual / device export / PDF extract) is
  auditable
- ✅ Every imaging study review is a single explicit clinician
  action — no auto-mark-reviewed
