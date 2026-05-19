# ChartNav Ophthalmology Specialty Modules — Plan

> **Phase scope target:** Phase 21A (build), Phase 20A (this plan).
> **Type:** Planning only. No tables, no migrations, no code.

ChartNav already ships **encounter-level** ophthalmology depth.
The repo audit confirms:

- 13 retinal symbol types (drusen, dot/blot, flame hemorrhage,
  microaneurysm, hard exudates, cotton-wool spot,
  neovascularization, retinal tear/hole, retinal detachment,
  laser/scar, disc pallor, RPE change, lattice degeneration)
- 48 clinical shortcuts across 10 subspecialty groups (PVD;
  Retinal detachment; Wet/Dry AMD; Diabetic retinopathy/DME;
  ERM/VMT/macular hole; BRVO/CRVO/retinal vascular;
  Post-injection/post-vitrectomy/post-op; Glaucoma; Cornea/
  anterior segment; Oculoplastics/lids/adnexa)
- 50 quick comments across 5 categories (Symptoms/HPI;
  Visual function/basic exam; External/anterior segment;
  Posterior segment; Assessment/plan/counseling)
- OD/OS retinal canvas with version chain + immutable signing
- Provider-reviewed AI proposal flow (rule-based parser → human
  accept/reject)
- Abbreviation-aware search

What's missing is the **longitudinal layer**: per-patient,
per-eye disease tracking that sits across many encounters and
feeds work queues. This plan defines specialty modules that
**extend** the existing systems — not replace them.

## Connection map: existing → new

| Existing surface | Specialty module connection |
|---|---|
| `clinicalShortcuts.ts` 10 groups | Each module's UI surfaces shortcut chips from the relevant group(s). E.g. the Retina module surfaces PVD / RD / Wet-Dry AMD / DR-DME / ERM-VMT / BRVO-CRVO / post-injection groups. |
| `quickComments.ts` Posterior-segment + Assessment-plan categories | Specialty module note panels suggest the relevant quick-comment chips inline. |
| `retinalAnnotations.ts` symbol library | Retina module problem-list rows can link to the specific signed `chart_artifacts` row that documents the finding. |
| `EyeDiagramPanel.tsx` + `RetinalDrawingCanvas.tsx` | Specialty module Retina cards render a **read-only thumbnail** of the patient's most-recent signed retinal artifact next to the tracking row. Click → opens the existing canvas. |
| `RetinalProposalReview.tsx` + `services/retinal_proposals.py` | Phase 6A proposal engine stays read-only; specialty modules consume the **accepted** outputs by reading signed `chart_artifacts.drawing_json`. |
| `NoteWorkspace.tsx` | Specialty module cards on the patient summary surface link back to the most-recent note version's structured findings. |
| `ScribeSessionPanel.tsx` | Unchanged. Scribe lifecycle is upstream of every specialty tracking row. |
| `extracted_findings` (existing table) | Specialty modules read `eye`, `iop_value`, `va_value` etc. when those structured fields exist; otherwise the clinician enters tracking values manually on the specialty card. |
| `patient_problem_list` (Phase 20B) | Specialty modules **filter to** their `specialty` column; e.g. retina_tracking only renders when `patient_problem_list.specialty = 'retina'` rows exist. |

## Retina module

### `retina_tracking` table

One row per (patient, eye, condition) — captures the longitudinal
state of a retina problem the practice is monitoring.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `encounter_id` | int FK | nullable; the encounter that created or last reviewed this row |
| `eye` | string | `OD` \| `OS` \| `OU` |
| `condition` | string | `wet_amd` \| `dry_amd` \| `dr_npdr` \| `dr_pdr` \| `dme` \| `erm` \| `vmt` \| `macular_hole` \| `brvo` \| `crvo` \| `lattice` \| `pvd` (mirrors existing shortcut groups) |
| `severity` | string | clinician-graded; suggested values per condition; **not** auto-graded |
| `last_oct_at` | datetime | populated from imaging_studies.metadata or manual |
| `last_fundus_at` | datetime | same |
| `injection_history_summary` | string | clinician-authored synopsis (e.g., "5x aflibercept, last 4 weeks ago") — full history in `retina_injection_events` |
| `follow_up_interval` | string | `1w` \| `2w` \| `4w` \| `6w` \| `8w` \| `12w` \| `prn` |
| `provider_assessment` | text | brief clinician note — **not** the full A/P; that lives in `note_versions` |
| `review_status` | string | `active` \| `stable` \| `escalating` \| `resolved` |
| `created_at`, `updated_at` | datetime | |

### `retina_injection_events` table

Append-only log of intravitreal injections. One row per
injection event.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `encounter_id` | int FK | nullable |
| `eye` | string | `OD` \| `OS` |
| `medication` | string | clinician-picked from a defined list (anti-VEGF agents). **ChartNav does not auto-select dosing.** |
| `procedure_date` | date | |
| `laterality` | string | `OD` \| `OS` |
| `notes` | text | clinician notes |
| `created_by_user_id` | int FK | |
| `created_at` | datetime | |

### Required APIs (Retina)

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /patients/{id}/retina` | clinician/reviewer/admin | list tracking rows |
| `POST /patients/{id}/retina` | clinician | create tracking row |
| `PATCH /patients/{id}/retina/{tracking_id}` | clinician | update severity / interval / assessment |
| `GET /patients/{id}/retina/injections` | clinician/reviewer | list injection events |
| `POST /patients/{id}/retina/injections` | clinician | record injection (in-room or scheduled) |

### What lives in shortcuts already (for reference)

The `clinicalShortcuts.ts` file already contains usable bodies
for every retina condition listed above. Examples (from the
shipped shortcut bank):

- `pvd-01` — "Acute PVD noted with vitreous syneresis. Negative Shafer sign. No retinal tear or retinal detachment on scleral depressed exam."
- `rd-01` — "Rhegmatogenous retinal detachment involving ___ quadrants, macula on / macula off."
- Wet/Dry AMD, DR/DME, ERM/VMT/macular hole, BRVO/CRVO,
  post-injection groups all populated.

### What feeds work queues (Retina)

- `retina_tracking.review_status = 'escalating'` → opens an
  `md_ready` queue item
- `retina_tracking.last_oct_at > follow_up_interval` → opens an
  `imaging_review` queue item (recommend OCT at next visit)
- A new injection event creates a `chart_closure_risk` queue
  item if the visit's note is unsigned > 24h post-procedure

### Hard constraints (Retina)

- ❌ **ChartNav does not auto-dose anti-VEGF.** Medication +
  dose are clinician-entered.
- ❌ **ChartNav does not auto-grade DR.** Severity is clinician-
  selected; UI may show a suggested-grade chip from existing
  proposal engine, but never as a final value.
- ❌ **ChartNav does not finalize retinal annotations without
  explicit provider approval.** This already holds in
  `RetinalProposalReview` and remains true.

## Glaucoma module

### `glaucoma_tracking` table

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `encounter_id` | int FK | nullable |
| `eye` | string | `OD` \| `OS` \| `OU` |
| `glaucoma_type` | string | `ocular_hypertension` \| `poag` \| `nag_acute` \| `pxf` \| `pds` \| `secondary` \| `congenital` |
| `target_iop` | int | clinician-set; mmHg |
| `latest_iop` | int | mmHg; populated from `glaucoma_iop_measurements` |
| `cup_to_disc_ratio` | string | clinician-entered as fraction (e.g., "0.7"); **never auto-computed** |
| `rnfl_status` | string | clinician-graded: `wnl` \| `borderline` \| `thinning` |
| `visual_field_status` | string | clinician-graded: `wnl` \| `borderline` \| `progressing` |
| `medication_plan` | text | brief synopsis; full meds in EHR |
| `progression_risk_label` | string | clinician-set: `low` \| `moderate` \| `high` |
| `provider_assessment` | text | |
| `review_status` | string | `active` \| `stable` \| `escalating` |
| `created_at`, `updated_at` | datetime | |

### `glaucoma_iop_measurements` table

Append-only IOP series.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `encounter_id` | int FK | nullable |
| `eye` | string | `OD` \| `OS` |
| `iop_value` | int | mmHg |
| `measured_at` | datetime | |
| `method` | string | `gat` \| `tonopen` \| `icare` \| `ncai` \| `other` |
| `created_at` | datetime | |

### `glaucoma_visual_field_tests` table

Reference rows pointing at HVF / Octopus / other VF tests. The
**file** lives in [imaging_files](./chartnav-imaging-pipeline-plan.md);
this table holds the structured progression metadata.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `encounter_id` | int FK | nullable |
| `eye` | string | `OD` \| `OS` |
| `test_type` | string | `hvf_24-2` \| `hvf_10-2` \| `octopus` \| `other` |
| `performed_at` | datetime | |
| `result_summary` | text | clinician-authored or imported from PDF |
| `reliability` | string | `reliable` \| `borderline` \| `unreliable` |
| `progression_flag` | string | `none` \| `possible` \| `likely` (clinician-set; never auto-flagged) |
| `created_at` | datetime | |

### Required APIs (Glaucoma)

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /patients/{id}/glaucoma` | clinician/reviewer/admin | list tracking rows |
| `POST /patients/{id}/glaucoma` | clinician | create tracking row |
| `PATCH /patients/{id}/glaucoma/{tracking_id}` | clinician | update target IOP / status |
| `GET /patients/{id}/glaucoma/iop` | clinician/reviewer | IOP series |
| `POST /patients/{id}/glaucoma/iop` | clinician/technician | record measurement |
| `GET /patients/{id}/glaucoma/visual-fields` | clinician/reviewer | VF series |
| `POST /patients/{id}/glaucoma/visual-fields` | clinician | record VF metadata |

### What feeds work queues (Glaucoma)

- IOP measurement above target → opens `md_ready` queue item
- `visual_field_status = 'progressing'` → opens `md_ready` for
  next visit
- VF test > follow-up-interval old → opens `imaging_review`
  queue item (recommend repeat VF)
- Cup-to-disc ratio clinician-update → no automatic queue
  action (provider-driven only)

### Hard constraints (Glaucoma)

- ❌ **ChartNav does not autofill IOP.** Tonometry values are
  technician/clinician entered.
- ❌ **ChartNav does not auto-determine cup-to-disc ratio.**
  C/D is clinician-entered; the OD/OS canvas can render a
  cup-marker symbol when added by the clinician.
- ❌ **ChartNav does not auto-grade visual fields.** Progression
  flag is clinician-set; an imported HVF PDF surfaces as a
  reviewable artifact.
- ❌ **ChartNav does not auto-prescribe glaucoma medication.**
  Plan field is free-text clinician-authored.

## Cornea / Anterior Segment module

Smaller initial scope — most of the clinical content already
lives in shortcuts (DED, MGD, keratoconus, RCE, Fuchs, post-DSEK)
and quick comments (anterior segment category).

### Proposed tracking surface

A lightweight `cornea_tracking` table with:
- `keratoconus_status` (`stable` / `progressing` / `s/p_cxl`)
- `k_max` (clinician-entered; from external Pentacam/topography PDF)
- `thinnest_pachymetry` (clinician-entered)
- `cxl_status` (`not_indicated` / `indicated` / `s/p_cxl_<date>`)
- `corneal_abrasion_followup_interval` (`24h` / `48h` / `1w`)
- `ulcer_followup_interval`
- `dry_eye_protocol_status` (`tier_1_artificial_tears` /
  `tier_2_punctal_plugs` / `tier_3_immunomodulator` / etc.)

### What feeds work queues (Cornea)

- Corneal abrasion → opens recall queue item at the configured
  interval
- Ulcer → opens recall queue item daily until resolved
- Dry-eye protocol step-up → opens `md_ready` for next visit

### Hard constraints (Cornea)

- ❌ No auto-staging of keratoconus
- ❌ No auto-prescription of dry-eye therapy

## Cataract / Refractive module

### Proposed tracking surface

A `cataract_tracking` table with:
- `cataract_evaluation_status` (`not_evaluated` / `appropriate` /
  `not_appropriate` / `deferred`)
- `lens_status` (`phakic` / `nuclear_sclerotic_<grade>` / `cortical` /
  `psc` / `mixed` / `iol_in_place`)
- `iolmaster_packet_uri` (FK to `imaging_files`; **never** the
  device-derived IOL power calculation by itself)
- `surgery_planning_status` (`pending_consult` / `consented` /
  `scheduled_<date>` / `s/p_<date>`)
- `post_op_drop_schedule_id` (FK to a future drop-schedule
  template; **never** auto-prescribed)

### What feeds work queues (Cataract)

- `lens_status = 'iol_in_place'` + age > 1w + no post-op note →
  opens `cataract_postop_followup` queue item
- IOLMaster packet uploaded → opens `md_ready` for next pre-op
  evaluation

### Hard constraints (Cataract)

- ❌ **ChartNav does not select IOL power.** The IOLMaster packet
  is surfaced as a reviewable artifact; the clinician selects
  the IOL.
- ❌ **ChartNav does not write an IOL prescription.**
- ❌ **ChartNav does not interface with ASC scheduling
  systems.** The surgery_planning_status is a tracking field
  only.

## Oculoplastics module

### Proposed tracking surface

A lightweight `oculoplastics_tracking` table with:
- `mrd1` (clinician-entered)
- `levator_function` (clinician-entered)
- `lid_findings` (free-text or shortcut-fed)
- `surgery_planning_status` (`pending_consult` / `scheduled` /
  `s/p`)

Most of the clinical content already lives in
`Oculoplastics / lids / adnexa` shortcut group + quick comments.

### Hard constraints (Oculoplastics)

- ❌ No auto-recommendation of surgical intervention
- ❌ No auto-staging of ptosis severity

## Pediatric / Strabismus module

### Proposed tracking surface

A `pediatric_strabismus_tracking` table with:
- `alignment_at_distance` (clinician-entered, e.g., "EOT 15 PD")
- `alignment_at_near` (clinician-entered)
- `amblyopia_status` (`none` / `treating` / `resolved`)
- `patching_plan` (clinician-authored — **never** auto-prescribed)
- `atropine_plan` (clinician-authored — **never** auto-prescribed)
- `next_followup_interval`

### Hard constraints (Pediatric)

- ❌ No auto-prescription of patching schedules
- ❌ No auto-prescription of atropine
- ❌ No auto-staging of amblyopia

## Per-module summary table

| Module | New tables | Existing shortcut groups it consumes | UI surface | Work-queue triggers |
|---|---|---|---|---|
| Retina | `retina_tracking`, `retina_injection_events` | PVD, RD, Wet/Dry AMD, DR/DME, ERM/VMT/macular hole, BRVO/CRVO, Post-injection | Retina card on patient summary; Retina chip on Clinical tab | severity escalation; OCT due; chart closure lag post-injection |
| Glaucoma | `glaucoma_tracking`, `glaucoma_iop_measurements`, `glaucoma_visual_field_tests` | Glaucoma | Glaucoma card; IOP series chart; VF history list | IOP > target; VF progressing; VF overdue |
| Cornea | `cornea_tracking` | Cornea / anterior segment | Cornea card | abrasion / ulcer recall; dry-eye step-up |
| Cataract | `cataract_tracking` | (none today; future shortcut group) | Cataract card; IOLMaster packet viewer | post-op followup; pre-op evaluation ready |
| Oculoplastics | `oculoplastics_tracking` | Oculoplastics / lids / adnexa | Oculoplastics card | (lower-volume; manual queue) |
| Pediatric | `pediatric_strabismus_tracking` | (none today; future shortcut group) | Pediatric card | follow-up interval expiry |

## Required tests (per module)

- Migration up/down on SQLite + Postgres
- Org isolation on every read/write
- RBAC: technician can record IOP measurements + injection events; clinician can edit tracking rows; reviewer is read-only on tracking, can sign artifacts
- Audit row written for every write (metadata-only)
- Cross-module: a Glaucoma IOP measurement on a patient who also has Retina tracking does not bleed across modules
- Forbidden phrasing: every API response, every UI string, scanned for "auto-dose", "auto-prescribe", "auto-grade" — must be absent on interactive surfaces
- Specialty card on patient summary degrades gracefully if no tracking row exists ("No retina tracking yet for this patient.")
