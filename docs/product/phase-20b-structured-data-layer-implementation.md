# Phase 20B — Structured Data Layer Foundation (Implementation)

> **Status:** Implemented (this PR).
> **Type:** Backend tables + endpoints + tests + minimal API
> client typings. **No frontend dashboards.**

This phase ships the durable foundation for the rest of the
Phase 20–22 roadmap (role-based dashboards, specialty modules,
imaging, multi-clinic). Every table is org-scoped, every
endpoint enforces RBAC + the no-existence-leak invariant, and
every write emits a metadata-only audit row.

## Tables added (8)

| # | Table | Purpose |
|---|---|---|
| 1 | `patient_segments` | Org-scoped named patient cohorts (dynamic / static). `criteria_json` holds typed predicates; never indexed for free-text matching. |
| 2 | `patient_segment_memberships` | Materialized memberships keyed on `(org, patient, segment)`. |
| 3 | `patient_tags` | Per-patient operational tags (high-priority, research-cohort, etc.). Idempotent on `(org, patient, tag)`. |
| 4 | `patient_problem_list` | Structured per-patient problem rows with `specialty`, `eye` (OD/OS/OU/null), `status` (active/monitoring/inactive/resolved), and onset/last-reviewed timestamps. CHECK constraints enforce eye + status enums. |
| 5 | `clinic_workflow_templates` | Org-scoped clinic-workflow templates (named, specialty-tagged, role-owned). |
| 6 | `clinic_workflow_stages` | Per-template stage rows with `stage_order` (unique within template) + `role_owner` + `sla_minutes`. |
| 7 | `work_queue_items` | The cross-tab task queue. Org-scoped; nullable FKs to location/patient/encounter/provider/assigned_user; CHECK-constrained `priority` + `status`. JSON `payload_json` for task-level metadata. |
| 8 | `role_view_presets` | Per-(org, role) saved view presets — filters_json + columns_json + is_default. CHECK-constrained `role` enum supports the additive Phase 20C `front_desk` + `technician` roles. |

Migration revision: `c4d5e6f7a8b9` (down from `b3c4d5e6f7a8`).
Forward + reverse roundtrip validated on SQLite.

## Endpoints added (≈25 across 16 paths)

| Resource | Method | Path | Role |
|---|---|---|---|
| Segments | GET | `/segments` | any |
| Segments | POST | `/segments` | admin |
| Segments | PATCH | `/segments/{id}` | admin |
| Segment memberships | GET | `/patients/{id}/segments` | any |
| Segment memberships | POST | `/patients/{id}/segments` | admin / clinician |
| Segment memberships | DELETE | `/patients/{id}/segments/{segment_id}` | admin / clinician |
| Tags | GET | `/patients/{id}/tags` | any |
| Tags | POST | `/patients/{id}/tags` | admin / clinician |
| Tags | DELETE | `/patients/{id}/tags/{tag_id}` | admin / clinician |
| Problem list | GET | `/patients/{id}/problem-list` | any |
| Problem list | POST | `/patients/{id}/problem-list` | admin / clinician |
| Problem list | PATCH | `/patients/{id}/problem-list/{item_id}` | admin / clinician |
| Workflow templates | GET | `/workflow-templates` | any |
| Workflow templates | POST | `/workflow-templates` | admin |
| Workflow templates | PATCH | `/workflow-templates/{id}` | admin |
| Workflow stages | GET | `/workflow-templates/{id}/stages` | any |
| Workflow stages | POST | `/workflow-templates/{id}/stages` | admin |
| Workflow stages | PATCH | `/workflow-stages/{id}` | admin |
| Work queue | GET | `/work-queues` | any |
| Work queue | POST | `/work-queues` | admin / clinician |
| Work queue | PATCH | `/work-queues/{id}` | admin / clinician |
| Role views | GET | `/role-views` | any |
| Role views | POST | `/role-views` | admin |
| Role views | PATCH | `/role-views/{id}` | admin |

All reads scoped to the caller's organization. All endpoints
require an authenticated caller (`X-User-Email` header in dev,
JWT bearer in prod).

## Org-isolation contract (no existence leak)

Every cross-org access returns **`404` not `403`**. This
preserves the existing repo-wide invariant: an attacker can't
distinguish "exists in another org" from "doesn't exist".

| Cross-org access pattern | Response |
|---|---|
| GET segment owned by another org | `404 segment_not_found` |
| PATCH segment owned by another org | `404 segment_not_found` |
| Add membership for cross-org patient | `404 patient_not_found` |
| Tag a cross-org patient | `404 patient_not_found` |
| Read problem list of a cross-org patient | `404 patient_not_found` |
| Read stages of a cross-org template | `404 template_not_found` |
| Update queue item from another org | `404 queue_item_not_found` |
| PATCH preset from another org | `404 preset_not_found` |
| Reference a cross-org `location_id` / `encounter_id` / `provider_id` / `assigned_user_id` in a queue item | `404 location_not_found` / `encounter_not_found` / `provider_not_found` / `user_not_found` |

## RBAC summary

| Role | Read | Write |
|---|---|---|
| `admin` | all resources | every endpoint |
| `clinician` | all resources | segment memberships · tags · problem list · queue items |
| `reviewer` | all resources (read-only) | none in Phase 20B |
| `front_desk` (Phase 20C additive) | role-view presets recognize the role | (no write yet) |
| `technician` (Phase 20C additive) | role-view presets recognize the role | (no write yet) |

The `front_desk` and `technician` enums in
`role_view_presets.role` and `clinic_workflow_*.role_owner` are
ready for Phase 20C without further migration. Phase 20B itself
does not extend the `users.role` CHECK constraint (that's
Phase 20C scope).

## Audit metadata-only contract

Every Phase 20B write emits a `security_audit_events` row
whose `detail` is **metadata-only**. The contract is enforced
by tests: a sentinel value placed in the JSON body of
`criteria_json` / `payload_json` / `filters_json` /
`columns_json` / `condition_label` must NOT appear in any
audit row.

| Event type | Detail format |
|---|---|
| `segment_created` | `segment_id={N} segment_type={type}` |
| `segment_updated` | `segment_id={N} fields=[…]` |
| `segment_membership_added` | `membership_id={N} segment_id={N} patient_id={N} source={src}` |
| `segment_membership_removed` | `membership_id={N} segment_id={N} patient_id={N}` |
| `patient_tag_added` | `tag_id={N} patient_id={N}` |
| `patient_tag_removed` | `tag_id={N} patient_id={N}` |
| `problem_item_added` | `item_id={N} patient_id={N} specialty={s} eye={OD/OS/OU} status={status}` |
| `problem_item_updated` | `item_id={N} patient_id={N} fields=[…]` |
| `workflow_template_created` | `template_id={N} role_owner={r} specialty={s}` |
| `workflow_template_updated` | `template_id={N} fields=[…]` |
| `workflow_stage_created` | `stage_id={N} template_id={N} order={N} role_owner={r}` |
| `workflow_stage_updated` | `stage_id={N} fields=[…]` |
| `queue_item_created` | `item_id={N} queue_type={t} priority={p} status={s}` |
| `queue_item_updated` | `item_id={N} old_status={s} new_status={s} fields=[…]` |
| `role_view_created` | `preset_id={N} role={r} is_default={bool}` |
| `role_view_updated` | `preset_id={N} fields=[…]` |

**Never** logged:
- Raw `criteria_json`, `payload_json`, `filters_json`,
  `columns_json` body
- `condition_label` text (clinician-authored — may shadow PHI)
- Tag string body
- Segment / template descriptions
- Anything from related encounters / notes / artifacts

## Tests added

`apps/api/tests/test_phase_20b_structured_data.py` — **42 tests
across 9 test classes**:

| Class | Coverage |
|---|---|
| `TestSegments` | admin create / clinician forbidden / reviewer forbidden / org-scoped list / duplicate name 409 / update / cross-org 404 / membership lifecycle (add / list / idempotent re-add / remove) / cross-org patient resolves 404 |
| `TestPatientTags` | add / list / delete / idempotent / reviewer forbidden / cross-org 404 |
| `TestProblemList` | create + list + update / specialty filter / status filter / invalid eye 400 / invalid status 400 / reviewer can read / cross-org 404 |
| `TestWorkflowTemplates` | admin create + stages / clinician forbidden / invalid role_owner 400 / duplicate stage_order 409 / cross-org 404 |
| `TestWorkQueue` | create + list + filter combos / invalid priority 400 / invalid status 400 / completion auto-stamps `completed_at` / cross-org referenced patient 404 / reviewer write forbidden / reviewer can read |
| `TestRoleViews` | admin create / clinician forbidden / invalid role 400 / `is_default=true` unsets siblings / cross-org 404 / role filter |
| `TestAuditMetadataOnly` | sentinel JSON values in `criteria_json` / `payload_json` / `filters_json` / `columns_json` / `condition_label` must NOT appear in audit rows; metadata IS recorded |
| `TestAuthRequired` | unauthenticated GET/POST returns 401 |

Local result: **42 passed** in 95s. Migration roundtrip validated.

## API client typings (`apps/web/src/api.ts`)

Appended TypeScript types + thin wrapper functions for every
Phase 20B endpoint. **Zero UI components ship in Phase 20B** —
these typings are for downstream phases (20C dashboards, 21A
specialty modules) to consume the API contract:

- Types: `PatientSegment`, `PatientSegmentMembership`,
  `PatientTag`, `PatientProblemItem`, `ClinicWorkflowTemplate`,
  `ClinicWorkflowStage`, `WorkQueueItem`, `RoleViewPreset` +
  enum unions for eye / status / priority / role
- Functions: `listSegments`, `createSegment`, `updateSegment`,
  `listPatientSegments`, `addPatientSegment`,
  `removePatientSegment`, `listPatientTags`, `addPatientTag`,
  `deletePatientTag`, `listProblemList`, `addProblem`,
  `updateProblem`, `listWorkflowTemplates`,
  `createWorkflowTemplate`, `updateWorkflowTemplate`,
  `listWorkflowStages`, `createWorkflowStage`,
  `updateWorkflowStage`, `listWorkQueue`, `createWorkQueueItem`,
  `updateWorkQueueItem`, `listRoleViews`, `createRoleView`,
  `updateRoleView`

`apps/web/src/api.ts` grew from 2,281 → 2,843 lines.
`tsc --noEmit` clean. `vitest 498/498` unchanged. `vite build`
clean.

## Limitations

1. **No segment evaluator yet.** `criteria_json` is stored as
   typed JSON but Phase 20B does **not** ship a deterministic
   evaluator that auto-populates `patient_segment_memberships`.
   Memberships are manual-only this phase. The evaluator is a
   Phase 20C-or-later add.
2. **No specialty-module work-queue triggers.** Queue items
   are manually created. Phase 21A's specialty-tracking
   modules will emit work-queue items automatically (e.g.,
   "OCT due" / "VF overdue").
3. **No imaging integration on queue payloads.** Phase 21B
   will start writing `queue_type='imaging_review'` rows from
   the imaging upload pipeline.
4. **No multi-location filtering yet.** Phase 22 will add
   `provider_location_assignments` and wire the
   `location_id` filter to the operator's location selector.
5. **No reviewer-only RBAC for queue items.** Reviewer is
   currently read-only on the work queue. Phase 20C may add
   reviewer-write paths for `note_review` queue items if
   needed.

## Explicit non-goals (Phase 20B does not):

- ❌ ship any role-based dashboard UI
- ❌ ship retina / glaucoma / cornea specialty tracking tables
- ❌ ship imaging study / file / measurement tables
- ❌ ship provider-location assignments / rooms / schedule blocks / operating hours
- ❌ extend `users.role` CHECK constraint (front_desk / technician role enums live in `role_view_presets.role` + `clinic_workflow_*.role_owner` only this phase)
- ❌ add chartnavmd.com / website / deck positioning changes
- ❌ ship HIPAA Phase 23 controls
- ❌ make any HIPAA-compliant / certified-EHR / autonomous-diagnosis / automatic-orders / automatic-billing / automatic-messaging claim
- ❌ run any segment evaluator on real data
- ❌ touch existing `chart_artifacts` / `note_versions` / `scribe_sessions` / `clinical_shortcuts` / `quick_comments` schema

## Next phases enabled

| Phase | What 20B unlocks |
|---|---|
| 20C — Role-based dashboards | Reads `work_queue_items` per role + `role_view_presets` per saved view + `front_desk` / `technician` role enums |
| 21A — Specialty modules | Emits `work_queue_items` (severity escalation / OCT due / IOP > target); reads `patient_problem_list` for specialty filters |
| 21B — Imaging pipeline | Emits `queue_type='imaging_review'` items; reads `patient_problem_list` to bind imaging to the active problem |
| 22 — Multi-clinic scaling | Wires `location_id` filter on `work_queue_items`; reads `provider_location_assignments` for the location selector |

## Validation summary

| Check | Result |
|---|---|
| Alembic upgrade head (SQLite) | ✅ clean |
| Alembic downgrade -1 + re-upgrade head | ✅ roundtrip clean |
| API loads (`from app.main import app`) | ✅ all 16 Phase 20B paths registered |
| `pytest tests/test_phase_20b_structured_data.py` | ✅ **42 passed** |
| `tsc --noEmit` (frontend) | ✅ clean |
| `vitest run` | ✅ **498 / 498 pass** (unchanged) |
| `vite build` | ✅ clean |
| `bash scripts/check_commercial_claims.sh` | (run at PR time) |
| `bash scripts/check_website_claims.sh` | (run at PR time) |
| Git scope: backend code + tests + 1 frontend api.ts edit + 2 docs | ✅ within Phase 20B scope |

## Hard guardrails preserved

- ❌ No HIPAA-compliant / HIPAA-certified / certified-EHR claim
- ❌ No autonomous diagnosis / automatic orders / automatic referrals / automatic patient messaging / automatic coding / automatic billing
- ❌ No real PHI in seed / fixtures / tests
- ❌ No frontend dashboard UI
- ❌ No retina / glaucoma / cornea / cataract / oculoplastics / pediatric tracking tables
- ❌ No imaging studies / files / measurements
- ❌ No provider-location assignments / rooms / schedule blocks / operating hours
- ❌ No chartnavmd.com / website / deck changes
- ✅ Every audit detail is metadata-only (sentinel test confirms)
- ✅ Every cross-org access returns 404 (no existence leak)
- ✅ Every write requires the documented role
