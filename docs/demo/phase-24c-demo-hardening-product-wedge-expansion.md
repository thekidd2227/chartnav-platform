# Phase 24C — Demo Hardening and Product Wedge Expansion

> **Phase:** 24C — controlled post-24B expansion.
> **Audience:** ophthalmology practice owner, clinical champion, advisor, or investor evaluating whether ChartNav is a workflow coordination layer rather than a single-patient retina toy.
> **Companion to:** `phase-24b-retina-workflow-demo-script.md`. Phase 24B remains the core Morgan Lee retina walkthrough. Phase 24C adds a narrow product-wedge proof across Retina Workflow v2, Multi-Specialty Workflow, and Admin/Ops Dashboard visibility.

Phase 24C keeps the same safety posture as Phase 24B: **fake data only, workflow metadata only, provider-reviewed outputs only**. It does not add diagnosis, treatment recommendation, autonomous decisioning, patient messaging, billing, orders, or device interpretation claims.

---

## What Phase 24C adds

| Track | Demo purpose | Safe proof point |
|---|---|---|
| Retina Workflow v2 | Preserve and harden the Morgan Lee role-by-role queue progression after PR #39. | Role dashboards still surface seeded work through deterministic user assignment, including front desk, technician, doctor, reviewer, and admin/operator views. |
| Multi-Specialty Workflow | Prove the same coordination engine can support a second specialty without a new product surface. | Deterministic fake glaucoma rows use the existing specialty-tracking and work-queue architecture. |
| Admin/Ops Dashboard | Give managers a useful operational view across workflow queues. | Queue counts by role/lane, aging/stale work, workload by assigned role/user, and source labels stay metadata-only. |

---

## Demo data contract

| Data element | Contract |
|---|---|
| Primary fake patient | `PT-1001` Morgan Lee remains the Phase 24B/24C retina anchor. |
| Primary demo org | `demo-eye-clinic`. |
| Second-specialty proof | Glaucoma is seeded as the lightweight second specialty because the codebase already has specialty-tracking support for it. |
| Queue ownership | Role-dashboard visibility remains tied to `assigned_user_id` where the dashboard requires user-specific ownership. |
| Aging proof | Seeded queue rows include deterministic due timestamps so admin/operator aging views can be demonstrated consistently. |
| Safety boundary | Imaging remains metadata-only. No binary image upload, device interpretation, autonomous clinical action, billing, orders, or patient communication is introduced. |

---

## Phase 24C walkthrough addendum

Use the Phase 24B Morgan Lee script first. After Stop 9, add this short operator segment.

### Stop 10 — Admin/Ops visibility *(60–90 s)*

**Say:**
> "This is the manager view. It does not make clinical decisions. It shows where work is sitting, who owns it, which lanes are aging, and whether the demo wedge is flowing across roles. The value is operational visibility, not autonomous care."

**Show:**
1. Switch identity to `admin@chartnav.local`.
2. Open the multi-clinic/admin operations dashboard.
3. Point to queue counts by role/lane.
4. Point to aging/stale work indicators.
5. Point to workload by assigned role/user.
6. Point to source labels that distinguish the Phase 24B retina wedge and Phase 24C glaucoma proof.

### Stop 11 — Multi-specialty proof *(45–60 s)*

**Say:**
> "Retina is the main demo path, but the platform is not hard-coded to retina. This second fake glaucoma lane uses the same coordination model: specialty metadata, work queue ownership, and operations visibility. No diagnosis, no treatment recommendation, no autonomous decision."

**Show:**
1. Keep the admin/operator view open.
2. Highlight the glaucoma source/specialty lane in the operational rollup.
3. Confirm the row is deterministic fake demo data.
4. Do not present this as a full glaucoma module; present it as an architectural proof that the same coordination engine can carry another specialty workflow.

---

## Forbidden phrases remain unchanged

| Forbidden | Safe replacement |
|---|---|
| Autonomous diagnosis | Workflow coordination metadata. |
| Treatment recommendation | Provider-reviewed follow-up context. |
| Auto-interpret OCT or device interpretation | Imaging metadata only. |
| Patient messaging | Internal staff coordination only. |
| Billing, orders, or claims automation | Operational queue visibility only. |
| HIPAA-certified or certified EHR | Controlled fake-data demo / pilot-readiness workstream. |

If any forbidden phrasing appears in narration or on screen, stop the recording and correct the source. Do not narrate around unsafe claims.

---

## Validation evidence expected before merge

| Gate | Required result |
|---|---|
| Backend Phase 24B/24C tests | Pass. Confirms Morgan Lee behavior is preserved and Phase 24C seed/admin rollups are covered. |
| Frontend impacted tests | Pass. Confirms admin/operator visibility renders without unsafe copy. |
| Typecheck | Pass. Confirms API contract and UI type alignment. |
| Production build | Pass. Confirms the demo surface is buildable. |
| Playwright Phase 24B/24C E2E | Pass. Confirms Phase 24B remains green and the Phase 24C admin/operator path is visible. |

---

## Merge recommendation language

Phase 24C is demo-ready only when all validation gates above pass and the PR remains a draft until review. It should not be merged if hosted CI fails, if Phase 24B Morgan Lee dashboard visibility regresses, or if any new copy implies diagnosis, treatment recommendation, autonomous clinical decisioning, patient messaging, billing, orders, or device interpretation.
