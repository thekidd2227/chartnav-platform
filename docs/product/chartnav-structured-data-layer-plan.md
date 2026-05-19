# ChartNav Structured Data Layer — Plan

> **Phase scope target:** Phase 20B (build), Phase 20A (this plan).
> **Type:** Planning only. No tables, no migrations, no code.

The current data model is **encounter-centric**. Every clinical
artifact in the repo today (extracted findings, note versions,
chart artifacts, scribe sessions, workflow events, encounter
inputs) hangs off a single encounter row. That's the right
foundation for the scribe-tier workflow ChartNav has shipped —
but it does not let an operator answer questions like:

- "Which diabetic-retinopathy patients are due for an OCT?"
- "Which glaucoma suspects are overdue for a visual field?"
- "Which cataract patients need their 1-week post-op recall?"
- "Which encounters are awaiting provider sign-off across all
  three locations?"
- "Which uploaded imaging studies haven't been reviewed yet?"
- "Which injection-day patients have an open chart-closure lag
  risk?"

This plan defines the **structured data layer** that lets a
practice answer those questions without leaving ChartNav, while
preserving the strict org-isolation + RBAC + provider-reviewed
contracts already in place.

## Existing surfaces this layer extends

| Existing | This plan adds |
|---|---|
| `patients` (org-scoped, native + external) | tags, segments (membership), problem-list rows |
| `encounters` (status state machine + workflow events) | work-queue surface that lets staff act on encounters by role / due time / queue type |
| `users` (admin / clinician / reviewer roles) | role-view presets so each role sees a tailored slice |
| `organizations` + `locations` (multi-location supported in data) | role views can already filter by location once tables exist |
| `clinical_shortcut_favorites` + `quick_comment_favorites` (per-clinician personalization) | same per-user / per-org isolation pattern; no new auth model |

## Proposed tables

### `patient_segments`

Org-scoped, named cohort definition. The criteria_json field
holds a typed predicate (parsed by the segment evaluator), not
free-text — so segments are computable, auditable, and
deterministic. Segment membership is materialized into
`patient_segment_memberships` so reads are cheap.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK → organizations | NOT NULL; org-isolation enforced on every read |
| `name` | string | unique within org |
| `description` | text | clinician-facing copy |
| `segment_type` | string | `dynamic` (re-evaluated on schedule) \| `static` (one-time membership snapshot) |
| `criteria_json` | json | typed predicate (e.g., `{"problem.condition_code":"E11.319","problem.status":"active","encounter.last_at_lt":"now-180d"}`) |
| `is_active` | bool | soft-disable |
| `created_by_user_id` | int FK → users | for audit |
| `created_at`, `updated_at` | datetime | |

Read access: any role within org. Write access: `admin`. Audit
metadata-only (segment_id, action). Never logs criteria_json or
membership PHI.

### `patient_segment_memberships`

Materialized membership rows. One row per (segment, patient).

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK → patients | unique (segment_id, patient_id) |
| `segment_id` | int FK → patient_segments | |
| `source` | string | `evaluator` \| `manual` \| `import` |
| `reason` | string | brief evaluator output (e.g., "active E11.319 + last_oct_at > 180d") |
| `created_at` | datetime | |

Soft-delete via DELETE → re-add when the predicate matches again
on the next evaluator run.

### `patient_tags`

Lightweight, free-form tag model (high-priority follow-up,
research-cohort markers, internal flags). Tags are **not**
clinical findings; problem-list captures clinical state.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK → patients | |
| `tag` | string | unique (patient_id, tag) |
| `color` | string | UI hex; defaults to `--cn-muted` |
| `created_by_user_id` | int FK | |
| `created_at` | datetime | |

### `patient_problem_list`

Structured problem list — the foundation that retina_tracking,
glaucoma_tracking, and segment evaluators read from. Each row
captures one problem on one eye (or `bilateral` / `n/a`).

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `patient_id` | int FK | |
| `condition_code` | string | ICD-10 / SNOMED string; **not** mapped automatically — clinician picks |
| `condition_label` | string | human-readable |
| `specialty` | string | `retina` \| `glaucoma` \| `cornea` \| `cataract` \| `oculoplastics` \| `pediatric` \| `general` |
| `eye` | string | `OD` \| `OS` \| `OU` \| `n/a` |
| `status` | string | `active` \| `resolved` \| `inactive` |
| `onset_date` | date | nullable |
| `last_reviewed_at` | datetime | bumped on every clinician review |
| `created_at`, `updated_at` | datetime | |

### `clinic_workflow_templates`

Org-scoped clinic workflow definitions. A template is a named
sequence of stages a patient (or encounter) walks through. The
current encounter status state machine handles **clinical**
status transitions; this is the **operational** layer above it.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `name` | string | "Standard ophthalmology workup" / "Injection day" / "Post-op week 1" |
| `specialty` | string | optional scoping |
| `role_owner` | string | nominal owner (`technician` / `clinician` / `front_desk`) |
| `description` | text | |
| `is_active` | bool | |
| `created_at`, `updated_at` | datetime | |

### `clinic_workflow_stages`

Stage rows attached to a template.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `template_id` | int FK | |
| `name` | string | "VA / IOP / refraction" / "Dilation" / "Ancillary imaging" / "MD encounter" / "Recheck" / "Checkout" / "Sign-off" |
| `stage_order` | int | sortable |
| `role_owner` | string | role responsible (front_desk / technician / clinician / reviewer / admin) |
| `sla_minutes` | int | nullable; informs work-queue aging coloring only |
| `created_at` | datetime | |

### `work_queue_items`

The operational queue every role-based dashboard reads from.
Each item is a **task**, not a clinical finding — so PHI never
lives in the work-queue payload (only in the linked rows it
points at). Work queues let the same encounter appear in
multiple lanes simultaneously without copy-pasting state.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `location_id` | int FK | nullable (cross-location items) |
| `patient_id` | int FK | nullable (admin tasks not patient-bound) |
| `encounter_id` | int FK | nullable |
| `provider_id` | int FK | nullable |
| `queue_type` | string | `tech_workup` \| `dilation_recheck` \| `imaging_review` \| `md_ready` \| `note_review` \| `signoff` \| `imaging_upload_pending` \| `injection_day` \| `cataract_postop_followup` \| `chart_closure_risk` |
| `priority` | string | `normal` \| `high` \| `urgent` |
| `status` | string | `open` \| `in_progress` \| `completed` \| `cancelled` |
| `assigned_role` | string | role that owns the queue lane |
| `assigned_user_id` | int FK | nullable |
| `due_at` | datetime | nullable |
| `source` | string | `evaluator` \| `manual` \| `signed_artifact` \| `imaging_upload` \| `encounter_status_change` |
| `payload_json` | json | small task-level metadata; never clinical text |
| `created_at`, `updated_at`, `completed_at` | datetime | |

Read scope: org + location filter + role filter. Write scope:
admin / clinician / reviewer per role permissions.

### `role_view_presets`

Per-org, per-role saved table views (column set + filter set).
Lets each clinic tune what front desk / tech / doctor see on
their dashboard without code changes.

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `organization_id` | int FK | |
| `role` | string | `front_desk` \| `technician` \| `clinician` \| `reviewer` \| `admin` |
| `name` | string | "Today's MD-ready", "Imaging backlog", "Cataract post-op" |
| `filters_json` | json | typed filter spec (queue_type / status / due_window / specialty) |
| `columns_json` | json | column ids in display order |
| `is_default` | bool | one default preset per (org, role) |
| `created_at`, `updated_at` | datetime | |

## How org isolation, RBAC, and audit are preserved

- Every table carries `organization_id NOT NULL`.
- Every read goes through the existing `ensure_same_org(caller, target_org_id)` guard before returning rows.
- Every write requires the existing role permission map; no new role types are introduced.
- Every audit row is metadata-only — `event_type`, `actor`,
  `path`, `error_code`, IDs. Never clinical body, criteria
  predicate text, or work-queue payload contents.

## How this connects to existing models

| Existing | Connection |
|---|---|
| `patients` | `patient_tags`, `patient_problem_list`, `patient_segment_memberships` all FK |
| `encounters` | `work_queue_items.encounter_id` (nullable); workflow_events can emit work-queue creation events |
| `extracted_findings` | downstream of segment evaluators (e.g., a finding for "increased IOP" can be the trigger that opens an `imaging_review` queue item) |
| `note_versions` | `signoff` queue items reference the note version awaiting signature |
| `chart_artifacts` | `imaging_upload_pending` queue items reference an artifact draft awaiting provider signature |
| `users` | `assigned_user_id` + `role_view_presets.role` |
| `locations` | every queue item is location-scoped optionally |

## Required APIs

(Detailed API design lives in
[`chartnav-multi-clinic-scaling-plan.md`](./chartnav-multi-clinic-scaling-plan.md#section-6--api-design)
and the per-module plans. Summary here.)

| Endpoint | Role | Purpose |
|---|---|---|
| `GET /patients/{id}/segments` | any | list segments containing this patient |
| `POST /patients/{id}/segments` | admin | manual add |
| `DELETE /patients/{id}/segments/{segment_id}` | admin | manual remove |
| `GET /segments` | any | list active segments + counts |
| `POST /segments` | admin | create segment definition |
| `PATCH /segments/{id}` | admin | edit / disable |
| `GET /patients/{id}/tags`, `POST`, `DELETE` | clinician | tag CRUD |
| `GET /patients/{id}/problem-list`, `POST`, `PATCH` | clinician | problem-list CRUD |
| `GET /work-queues` | any (filtered by role) | the dashboard endpoint |
| `POST /work-queues` | admin / system | manual queue creation |
| `PATCH /work-queues/{id}` | role with assignment | claim / progress / complete |
| `GET /role-views` | any | resolve presets for the caller's role |

## Required frontend panels

| Panel | Tab | Notes |
|---|---|---|
| Segments + tags chips on patient header | Patient header | Read-only chip strip + "Add tag" admin action |
| Problem List card on Overview | Overview | Per-eye, per-specialty rows with last-reviewed date |
| Work-queue dashboard (per role) | New tab or App-level routing — TBD | Top-level entry into Phase 20C role dashboards |

## Required tests

- Migration up/down on SQLite + Postgres
- Org isolation (cross-org read returns 404 / 403 not 200 with empty list)
- Cross-org existence leak guard (a 404 for a real-other-org row reads identically to a 404 for a non-existent row)
- RBAC: only admin can create segments / templates; only assigned role can complete a queue item
- Soft-delete vs hard-delete semantics on memberships
- Audit-log row written for every write; audit detail contains no clinical body / no criteria_json content
- Segment evaluator deterministic against a frozen patient set
- Work-queue read returns only items in caller's org + (optionally) location

## Hard constraints

- ❌ No automatic order creation from problem-list rows
- ❌ No automatic referral creation
- ❌ No automatic patient messaging from segment evaluation
- ❌ No automatic billing / coding from problem-list condition_code
- ❌ Predicates must not include text-pattern matching against unredacted clinical body — only structured fields
- ✅ Every queue item must point at a clinical row; the queue itself stores no clinical text
- ✅ Every segment evaluator run must be auditable
