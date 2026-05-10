# ChartNav Phase 20–23 Implementation Roadmap

> **Type:** Roadmap synthesis. Reads the other 8 Phase 20A
> planning docs and orders them into shippable phases with
> scope, files-touched, tests, risks, and "do not touch" lists.
>
> **Filename retained** as `chartnav-phase-20-22-implementation-roadmap.md`
> to avoid renaming churn. The roadmap content covers
> **Phase 20B → 20C → 21A → 21B → 21C → 22 → 23** (the
> Phase 23 HIPAA-regulated deployment readiness layer was added
> in Phase 20A.1 alongside the rest of this set).

This roadmap covers seven phases (**20B → 20C → 21A → 21B → 21C
→ 22 → 23**). Each phase is sized to ship as one PR (or a small
sequence of subphase PRs in the case of 23), behind one merge,
with one validation pass.

## Phase ordering rationale

```
Phase 20A   ──── plan only (PR #29)
Phase 20A.1 ──── plan only — adds Phase 23 HIPAA readiness (PR #29 amend)
Phase 20B   ──── structured data layer (foundation)
Phase 20C   ──── role-based dashboards (consumes 20B)
Phase 21A   ──── ophthalmology specialty modules (consumes 20B + extends existing)
Phase 21B   ──── imaging pipeline (extends 21A + existing chart_artifacts)
Phase 21C   ──── ophthalmology positioning (consumes evidence from 20B/20C/21A/21B)
Phase 22    ──── multi-clinic scaling (extends 20B + locations)
Phase 23    ──── HIPAA-regulated deployment readiness (legal / technical / audit /
                 backup / incident-response / vendor / operational policy / validation)
```

The order is deliberately **data → dashboards → specialty depth →
imaging → public positioning → multi-clinic operations →
HIPAA-regulated deployment readiness**. Positioning (21C) lands
after the underlying capability ships so every claim is anchored
to merged code, not a planning artifact.

**Phase 23 dependency note.** Phase 23 can begin **in parallel**
with product work (20B → 22) — its docs-only subphases (23A–C)
do not conflict with code PRs. The product-code subphases (23D–F)
land last because they need the docs as the source of truth.
**Real PHI cannot begin until Phase 23 gates are completed and
approved** (see Section 9 of the [HIPAA-regulated deployment
readiness plan](./chartnav-hipaa-regulated-deployment-readiness-plan.md#9-exact-safe-readiness-statement)).

## Phase 20B — Structured Data Layer

**Plan doc:** [`chartnav-structured-data-layer-plan.md`](./chartnav-structured-data-layer-plan.md)

### Scope

- 7 new tables: `patient_segments`, `patient_segment_memberships`, `patient_tags`, `patient_problem_list`, `clinic_workflow_templates`, `clinic_workflow_stages`, `work_queue_items`, `role_view_presets`
- 18 new endpoints (segments / tags / problem-list / work-queues / role-views)
- Segment evaluator service (deterministic, scheduled run; can be triggered manually)
- Org isolation + RBAC tests for every endpoint

### Files likely touched

- `apps/api/alembic/versions/<new>_phase_20b_structured_data.py`
- `apps/api/app/models/structured_data.py` (new)
- `apps/api/app/api/segments.py`, `tags.py`, `problem_list.py`, `work_queues.py`, `role_views.py` (new modules)
- `apps/api/app/services/segment_evaluator.py` (new)
- `apps/api/app/api/routes.py` (mount the new modules)
- `apps/api/tests/test_phase_20b_*.py` (new test files per resource)
- `apps/api/scripts_seed.py` (seed a few demo segments + tags + problem-list rows for `?demo=1`)
- `docs/diagrams/er-diagram.md` (add the 7 tables)

### Tests required

- Migration up/down on SQLite + Postgres
- Org isolation on every read/write (cross-org returns 404)
- RBAC: only admin creates segments/templates; only assigned role completes a queue item
- Soft-delete vs hard-delete on memberships
- Audit row written for every write; audit detail metadata-only (no criteria_json content, no work-queue payload contents)
- Segment evaluator deterministic against frozen patient set
- Work-queue read filtered by org + role + (optional) location

### Risks

- **Predicate engine scope creep.** The `criteria_json` predicate language is intentionally narrow (typed structured field comparisons). Risk: someone adds free-text matching against unredacted clinical body. **Mitigation:** explicit allowlist of predicate field names; reviewer-pair on every evaluator change.
- **Work-queue coupling to specialty modules.** Queue types referenced by Phase 21A modules don't exist until Phase 21A. **Mitigation:** Phase 20B ships a generic queue with the operational types; specialty queue types added in 21A migrations.

### Merge criteria

- Migrations apply clean SQLite + Postgres
- All new endpoints have org-isolation + RBAC tests
- vitest 498/498 (existing tests) + new vitest for any frontend stub
- claims-check 0 fail / 0 warn
- All 8 CI checks green
- No frontend product code changes (frontend consumption is Phase 20C)

### Do NOT touch

- ❌ `apps/web/src/` (frontend lands in 20C)
- ❌ `chart_artifacts` / `note_versions` / `scribe_sessions` schema
- ❌ Existing `users.role` CHECK constraint (no `front_desk` / `technician` yet — that's 20C)
- ❌ `clinicalShortcuts.ts` / `quickComments.ts` / `retinalAnnotations.ts`

---

## Phase 20C — Role-Based Dashboards

**Plan doc:** [`chartnav-role-based-clinic-workflows-plan.md`](./chartnav-role-based-clinic-workflows-plan.md)

### Scope

- Add `front_desk` + `technician` to `users.role` CHECK constraint (migration)
- 5 dashboard React components:
  - `FrontDeskDashboard.tsx`
  - `TechnicianDashboard.tsx`
  - `DoctorDashboard.tsx`
  - `ReviewerDashboard.tsx`
  - `AdminDashboard.tsx`
- App-level routing dispatches by `me.role`
- Sidebar **CORE → Dashboard** entry (currently disabled placeholder) wired to the role-dispatched route
- Sidebar OPERATIONS → **Tasks** entry wired to role-filtered work_queue_items view
- Top-bar location + provider selectors (degrade to org-scope until Phase 22 ships)
- Dashboard endpoints: `/dashboards/role` (returns the lane spec for caller's role)

### Files likely touched

- `apps/api/alembic/versions/<new>_phase_20c_extend_user_roles.py` (small migration)
- `apps/api/app/authz.py` (extend `TRANSITION_ROLES` + permission map for new roles)
- `apps/api/app/api/dashboards.py` (new)
- `apps/web/src/dashboards/` (5 new components)
- `apps/web/src/App.tsx` (routing + sidebar wire-up)
- `apps/web/src/test/dashboards/` (new test files)
- `docs/diagrams/er-diagram.md` (note the role enum extension)

### Tests required

- vitest: each dashboard renders the right lanes for the caller's role
- vitest: front-desk role cannot read clinical chart bodies
- vitest: technician role cannot sign note versions
- vitest: doctor role sees only their own MD-ready queue by default
- vitest: reviewer sees full org review queue
- vitest: admin sees cross-location aggregates; drill-downs respect RBAC
- Backend: `front_desk` and `technician` roles reject existing clinician/admin actions
- E2E: each role's dashboard loads + paginates work queue
- Forbidden-phrase scan on every dashboard panel: no autonomous-diagnosis, no auto-order, no auto-message language

### Risks

- **Role enum migration on existing users.** Existing rows must keep current values. **Mitigation:** ADD CHECK enum, do not REWRITE existing rows.
- **Cross-role read leakage.** A front-desk user must not see clinical body fields. **Mitigation:** dashboard-only query layer that selects safe columns; explicit test for every role × resource pair.

### Merge criteria

- Migrations apply clean
- All 8 CI checks green including E2E
- Role-dispatched routing in App.tsx covered by integration test
- claims-check 0 fail / 0 warn

### Do NOT touch

- ❌ `ClinicalTabbedWorkspace.tsx` internal structure
- ❌ `NoteWorkspace` / `EyeDiagramPanel` / `RetinalDrawingCanvas` internals
- ❌ `chart_artifacts` schema
- ❌ specialty module tables (those are Phase 21A)

---

## Phase 21A — Ophthalmology Specialty Modules

**Plan doc:** [`chartnav-ophthalmology-specialty-modules-plan.md`](./chartnav-ophthalmology-specialty-modules-plan.md)

### Scope

- Tables: `retina_tracking`, `retina_injection_events`, `glaucoma_tracking`, `glaucoma_iop_measurements`, `glaucoma_visual_field_tests`, `cornea_tracking`, `cataract_tracking`, `oculoplastics_tracking`, `pediatric_strabismus_tracking`
- Endpoints per module (see specialty-modules plan)
- Specialty cards on patient summary surface
- Specialty chips on Clinical tab (Retina / Glaucoma / Cornea / Cataract / Oculoplastics / Pediatric)
- Work-queue triggers wired (severity escalation; OCT due; IOP > target; VF overdue; injection day chart-closure risk)

### Files likely touched

- `apps/api/alembic/versions/<new>_phase_21a_specialty_modules.py`
- `apps/api/app/models/specialty.py` (new)
- `apps/api/app/api/{retina,glaucoma,cornea,cataract,oculoplastics,pediatric}.py` (new)
- `apps/web/src/specialty/` (new card components)
- `apps/web/src/ClinicalTabbedWorkspace.tsx` (extend Clinical tab pills with specialty chips)
- `apps/web/src/clinicalShortcuts.ts` (add Cataract + Pediatric shortcut groups if appetite to expand from 48 → ~70)
- `apps/api/tests/test_phase_21a_*.py` (new)

### Tests required

- Migration up/down
- Org isolation on every specialty module endpoint
- RBAC: technician records IOP + injection events; clinician edits tracking; reviewer read-only on tracking, signs artifacts
- Cross-module bleed test (glaucoma IOP doesn't leak into retina patients)
- Work-queue integration test (escalation triggers correct queue type)
- Forbidden-phrase scan: every specialty module API + UI string — no "auto-grade" / "auto-dose" / "auto-prescribe" anywhere on shipped surfaces
- Specialty card degrades gracefully when no tracking row exists

### Risks

- **Connecting to existing chart_artifacts.** Retina module reads the most-recent signed artifact for thumbnail rendering. **Mitigation:** read-only join; never modify artifact.drawing_json from specialty module.
- **Cataract IOLMaster packet handling.** Hardware-specific format. **Mitigation:** Phase 21A handles only the metadata + packet upload; PDF parsing is Phase 21B.

### Merge criteria

- All 8 CI checks green
- vitest covers every new card + every new module endpoint
- claims-check 0 fail / 0 warn
- Specialty hard constraints (no auto-dose, no auto-grade, no auto-prescribe, no auto-IOL-power) enforced by tests

### Do NOT touch

- ❌ `RetinalDrawingCanvas.tsx` internal canvas behavior
- ❌ `retinalAnnotations.ts` symbol library
- ❌ `services/retinal_proposals.py` proposal engine
- ❌ Imaging tables (those are Phase 21B)

---

## Phase 21B — Imaging Pipeline

**Plan doc:** [`chartnav-imaging-pipeline-plan.md`](./chartnav-imaging-pipeline-plan.md)

### Scope

- Tables: `imaging_studies`, `imaging_files`, `imaging_measurements`
- Endpoints per imaging plan
- Storage backend abstraction (S3 / local / GCS via env config)
- Upload handler with checksum + size + content-type allowlist
- Imaging review queue integration
- Specialty-module integration (last_oct_at, last_fundus_at, RNFL/VF metadata)
- Imaging tab UI: 6-card grid (Phase 19I shape) wired to real studies; OD/OS workbench remains downstream

### Files likely touched

- `apps/api/alembic/versions/<new>_phase_21b_imaging_pipeline.py`
- `apps/api/app/models/imaging.py` (new)
- `apps/api/app/api/imaging.py` (new)
- `apps/api/app/services/imaging_storage.py` (new — storage backend abstraction)
- `apps/web/src/ClinicalTabbedWorkspace.tsx` (Imaging tab cards consume real data)
- `apps/web/src/imaging/` (viewer components — image, PDF)
- `apps/api/tests/test_phase_21b_*.py`
- `apps/web/tests/e2e/imaging.spec.ts` (new e2e)

### Tests required

- Migration up/down
- Org isolation on study + file reads
- Cross-org file fetch returns 404
- Checksum mismatch returns 422
- Max file size enforced
- Content-type allowlist enforced
- Review state transitions atomic
- `reviewed_at` write triggers work-queue completion
- Audit log row content metadata-only (study_id + action; never file content, never measurement values)
- E2E: upload a test fixture (synthetic, redacted) → review → flow into specialty module
- Forbidden-phrase scan: no "automatic measurement", no "AI-detected", no "auto-graded" anywhere

### Risks

- **PHI controls before real images.** Phase 21B ships the schema + endpoint surface; **real image bytes only flow in production after a separate PHI-readiness gate ships** (audit retention, IAM, encryption). **Mitigation:** ship demo / pilot with synthetic image fixtures only; production rollout is a separate explicit phase.
- **Storage backend coupling.** Don't bake S3 specifics into the API layer. **Mitigation:** `imaging_storage.py` is the only module that knows the backend.
- **Vendor adapter scope creep.** Phase 21B does NOT ship Cirrus / Spectralis / Triton / Optos / IOLMaster adapters. Marketing must not claim them.

### Merge criteria

- All 8 CI checks green
- E2E imaging flow covers upload → review → specialty-module update
- claims-check 0 fail / 0 warn
- No vendor name in shipped marketing without adapter merged

### Do NOT touch

- ❌ Real PHI in any test fixture
- ❌ Production storage backend (Phase 21B uses local fs / synthetic S3 in dev; prod is a separate gate)
- ❌ chart_artifacts internal schema

---

## Phase 21C — Ophthalmology Positioning Upgrade

**Plan doc:** [`chartnav-ophthalmology-positioning-gap-plan.md`](./chartnav-ophthalmology-positioning-gap-plan.md)

### Scope

- Update all decks under `docs/decks/`
- Update website shot list under `docs/website/`
- Add `docs/commercial/one-pagers/chartnav-ophthalmology-artifact-glossary.md`
- Update homepage copy + add static specialty chart fragment (Phase 19I-style screenshot from `?demo=1`)
- Update non-goals language across all decks (add ophthalmology-specific second block)
- Mark every "future" capability explicitly
- (Optionally) extend `clinicalShortcuts.ts` with Cataract + Pediatric shortcut groups

### Files likely touched

- `docs/decks/chartnav-buyer-demo-deck.md`
- `docs/decks/chartnav-customer-pitch-deck-template.md`
- `docs/decks/chartnav-investor-pitch-deck.md`
- `docs/decks/chartnav-elevator-pitch-deck.md`
- `docs/website/chartnav-website-shot-list.md`
- `docs/commercial/one-pagers/chartnav-ophthalmology-artifact-glossary.md` (new)
- `docs/commercial/chartnav-approved-claims-language.md`
- `docs/demo/chartnav-clinical-workflow-demo-script.md`
- `apps/web/src/clinicalShortcuts.ts` (optional Cataract + Pediatric expansion)

### Tests required

- `bash scripts/check_commercial_claims.sh` 0 fail / 0 warn
- `bash scripts/check_website_claims.sh` 0 fail / 0 warn
- Forbidden-phrase grep on docs/website + docs/decks: no HIPAA-compliant / certified-EHR / autonomous-diagnosis / automatic-orders / automatic-patient-messaging / automatic-billing
- Subspecialty stratification present: Retina + Glaucoma + Cornea + Oculoplastics named in any updated buyer-pitch slide
- Eye-clinic operational language present in any "How ChartNav fits" surface
- Every "Planned" / "Future" tag present on unshipped capability
- No vendor name (Cirrus, Spectralis, Triton, Optos, IOLMaster) appears without merged adapter

### Risks

- **Claim-vs-capability drift.** Risk: copy claims a Phase 21B imaging modality before Phase 21B merges. **Mitigation:** Phase 21C strictly follows Phase 21B merge.
- **Cataract / Pediatric shortcut expansion.** Adding shortcut groups requires new clinical content review. **Mitigation:** scope as optional in this phase; can split to Phase 21D if needed.

### Merge criteria

- All claims-check passes
- No production website publish
- No chartnavmd.com update (separate explicit gate)

### Do NOT touch

- ❌ Production website
- ❌ chartnavmd.com
- ❌ Final-delivery folder
- ❌ Real customer / pilot / metric numbers without legal-review approval

---

## Phase 22 — Multi-Clinic Scaling

**Plan doc:** [`chartnav-multi-clinic-scaling-plan.md`](./chartnav-multi-clinic-scaling-plan.md)

### Scope

- Tables: `provider_location_assignments`, `location_rooms`, `provider_schedule_blocks`, `clinic_operating_hours`
- Endpoints per multi-clinic plan (15+ new endpoints)
- Top-bar location + provider selectors wired to real data
- Admin dashboard cross-location summary card
- Location dashboard + provider dashboard endpoints

### Files likely touched

- `apps/api/alembic/versions/<new>_phase_22_multi_clinic.py`
- `apps/api/app/models/multi_clinic.py` (new)
- `apps/api/app/api/{provider_location,rooms,schedule_blocks,operating_hours,location_dashboard,provider_dashboard,multi_clinic_summary}.py` (new modules)
- `apps/web/src/multi_clinic/` (selectors + admin summary card)
- `apps/web/src/AdminPanel.tsx` (extend with cross-location summary)
- `apps/api/tests/test_phase_22_*.py`

### Tests required

- Migration up/down
- Org isolation on every endpoint
- Cross-org returns 404
- Unique constraints enforced (`provider_id, location_id`; `location_id, day_of_week`)
- `is_primary` constraint at most one per provider per org
- Soft-delete preserves historical encounter → location/provider links
- Schedule-block conflict warning at admin write time
- Audit row written for every write
- E2E: location selector switch updates dashboards correctly

### Risks

- **Soft-delete data integrity.** Existing encounters reference location_id and provider_id; soft-deleting an assignment must not break those references. **Mitigation:** assignments are about the (provider, location) **link**, not the entities themselves; encounters don't depend on the assignment row.
- **Schedule complexity.** Risk: feature creeps into a calendar / booking product. **Mitigation:** schedule blocks are coarse availability only; no per-slot booking.

### Merge criteria

- All 8 CI checks green
- E2E location-switching flow covered
- claims-check 0 fail / 0 warn
- Multi-clinic capability claim allowed in marketing only after this phase merges

### Do NOT touch

- ❌ Patient-side booking surfaces
- ❌ Per-slot appointment scheduling
- ❌ Billing-by-location reporting
- ❌ EHR-level scheduling integration

---

---

## Phase 23 — HIPAA-Regulated Deployment Readiness

**Plan doc:** [`chartnav-hipaa-regulated-deployment-readiness-plan.md`](./chartnav-hipaa-regulated-deployment-readiness-plan.md)

> **Phase 23 prepares ChartNav for security review. It does
> not constitute the security review itself or its outcome.
> ChartNav is not HIPAA compliant by default. ChartNav is not
> HIPAA certified.** See Section 9 of the plan for the exact
> approved readiness statement.

### Scope

Six subphases (23A → 23F). Subphases 23A–C are **docs-only**
(legal / contract / policy artifacts). Subphases 23D–F are
**product code** (admin-only, read-only over existing data,
audit-logged) plus operational tooling.

### Subphases (one PR each)

| Subphase | Scope | Type | Deliverables |
|---|---|---|---|
| **23A** | HIPAA Readiness Control Matrix + Customer Responsibility Matrix | docs-only | `docs/compliance/chartnav-hipaa-readiness-control-matrix.md`, `docs/compliance/chartnav-customer-responsibility-matrix.md` |
| **23B** | PHI Data Flow + Subprocessor / Vendor Inventory | docs-only | `docs/security/chartnav-phi-data-flow-map.md`, `docs/compliance/chartnav-subprocessor-inventory.md`, `docs/compliance/chartnav-baa-vendor-readiness-checklist.md` |
| **23C** | Policies + Incident / Breach Runbooks | docs-only | `docs/security/chartnav-access-control-policy.md`, `docs/security/chartnav-backup-disaster-recovery-policy.md`, `docs/security/chartnav-support-phi-handling-policy.md`, `docs/security/chartnav-incident-breach-response-runbook.md`, `docs/security/chartnav-security-risk-analysis-template.md` |
| **23D** | Admin Security Dashboard + Audit Event Export | product code (admin-only) | `apps/api/app/api/admin_security.py`, `apps/api/app/services/audit_export.py`, `apps/web/src/AdminSecurityDashboard.tsx`, tests |
| **23E** | Backup / Restore Evidence + Monitoring Evidence | product code + scripts | `scripts/verify_backup_integrity.sh`, `scripts/restore_test_runner.sh`, `apps/api/app/api/backup_status.py`, `apps/web/src/AdminBackupStatus.tsx` |
| **23F** | Final Controlled-Pilot Real-PHI Gate Review Packet | product code + scripts + docs | `docs/compliance/chartnav-controlled-pilot-real-phi-gate-review-packet.md`, `scripts/generate_pilot_readiness_packet.sh`, `apps/api/app/api/production_readiness.py`, `apps/web/src/AdminProductionReadiness.tsx` |

### Tests required (per subphase)

- claims-check + website-claims-check 0 fail / 0 warn on every subphase
- Forbidden-phrase grep on every new doc — every HIPAA-positive phrase must be in safe negative-assertion context
- For 23D/E/F: RBAC tests (admin-only); org isolation tests; audit row written for every read; PHI-safe payload guard on every export endpoint
- For 23F: production-readiness endpoint covered by known-good / known-bad config fixtures
- No real PHI in any test fixture across all six subphases

### Risks

- **Doc-as-compliance misread.** Risk: the practice reads the policy artifacts and assumes ChartNav is now HIPAA compliant. **Mitigation:** every doc opens with the exact safe readiness statement; every UI score includes the same statement.
- **Vendor egress drift.** Risk: a future PR adds a new vendor surface (e.g., a new STT provider) without updating the subprocessor inventory. **Mitigation:** Phase 23B's inventory is a `docs/compliance/` source-of-truth file; subsequent vendor-adding PRs must update it (enforced by reviewer convention).
- **Admin dashboard PHI leak.** Risk: an export endpoint accidentally surfaces clinical text from `security_audit_events.detail`. **Mitigation:** the existing audit detail contract is metadata-only; Phase 23D adds an explicit test that scans exported payloads for clinical-text shape patterns.
- **Real-PHI go-live without all gates.** Risk: a deploying party skips a gate (e.g., starts real PHI without the BAA). **Mitigation:** the production-readiness endpoint computes the readiness score from existing config; the practice's signed go-live document is required separately and is off-repo.

### Merge criteria (per subphase)

- All 8 CI checks green
- claims-check + website-claims-check 0 fail / 0 warn
- For docs-only subphases: scope confined to `docs/compliance/` + `docs/security/` + the roadmap update
- For product-code subphases: admin-only RBAC enforced; PHI-safe payloads tested; no schema changes (Phase 23 reads existing tables)
- The exact safe readiness statement (Plan doc Section 9) appears verbatim in every new artifact that mentions HIPAA readiness

### Do NOT touch (across all of Phase 23)

- ❌ Real BAAs (signed off-repo by the practice and ChartNav)
- ❌ Real practice-owned production backups
- ❌ Real PHI in any test / fixture / demo / capture
- ❌ Practice security review acceptance (that's the practice's signed acceptance, not a code change)
- ❌ Real-PHI deployment activation (that's gated on the signed go-live document)
- ❌ Clinical workflow tables / endpoints / surfaces (Phase 23 is admin-only, read-only over existing data)

---

## Cross-phase invariants

These rules bind every phase in this roadmap (20B → 23):

- ✅ Every migration is forward + reverse on SQLite + Postgres
- ✅ Every new endpoint has org-isolation + RBAC + audit row
- ✅ Every shipped UI claim is anchored to merged code
- ✅ Every "future" / "planned" capability is tagged as such in copy
- ✅ Every PR is squash-merged with a CI-green precondition
- ✅ Any reference to HIPAA readiness uses the exact safe readiness statement (Plan doc Section 9)
- ❌ No HIPAA-compliant claim
- ❌ No HIPAA-certified claim
- ❌ No "approved for real PHI by default" claim
- ❌ No certified-EHR claim
- ❌ No autonomous-diagnosis claim
- ❌ No automatic orders / referrals / patient messaging / coding / billing claim
- ❌ No vendor-integration claim without the merged adapter
- ❌ No real PHI in any test / demo / capture
- ❌ No production website publish without explicit Jean-Max sign-off

## Suggested sequencing notes

- **20B → 20C is tight coupling.** Phase 20C consumes Phase 20B's work-queue + role-views API directly. Plan to land them in the same week.
- **21A and 21B are independent.** Specialty modules don't depend on imaging; imaging doesn't depend on specialty modules. They can land in parallel if there's reviewer bandwidth.
- **21C waits for 21A + 21B.** Positioning copy must be true at merge time. If 21A merges but 21B is still in flight, Phase 21C can ship a "subspecialty-stratified" cut that excludes imaging claims; full 21C ships after 21B.
- **22 is independent of 21.** Multi-clinic scaling doesn't depend on specialty depth. It depends only on Phase 20B's structured data layer. Can land any time after 20B.
- **23 is independent of 20–22.** Phase 23 can begin in parallel with product work. The docs-only subphases (23A–C) don't conflict with code PRs; the product-code subphases (23D–F) only depend on existing tables (`security_audit_events`, `ai_governance_log`, etc.) so they can land any time. **Real PHI cannot begin until Phase 23 gates are completed and the practice's signed go-live document is on file.**
- **Real PHI is a separate gate** orthogonal to all of the above. Every phase in this roadmap operates on synthetic / redacted demo data only. The Phase 23 plan defines the exact gates that must close before real PHI begins.
