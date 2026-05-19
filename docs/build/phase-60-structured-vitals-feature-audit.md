# Phase 60 — Structured Vitals & Technician Workup Feature Audit

> Pre-implementation audit on `main` at `0a023eb` (Phase 59 merged).
> No product behaviour was changed during this audit.
>
> **Headline:** Greenfield build. ChartNav currently has **no**
> structured vitals capture, **no** BMI tracking, **no** intake
> checklist booleans, and **no** ophthalmology workup summary row.
> Phase 21A introduced discrete IOP / visual-field measurement
> tables for longitudinal glaucoma tracking; those are not a
> visit-level workup row. Phase 60 must add a new
> `visit_vitals_workups` table.
>
> Reuse, do not rebuild: the technician role + auth pattern (Phase
> 20C), the audit-record signature, the scribe-session-style
> lifecycle (`draft → entered → reviewed → signed`), the Phase 56
> claim-policy + scanner pattern, and the Phase 21A
> "specialty tracking" route shape.

## 1. Existing audio / vitals / workup / intake infrastructure

| Surface | Result | Notes |
|---|---|---|
| Vital signs (BP, temp, pulse, RR, SpO2) | **None** | No table, no model, no service, no UI. Phase 60 builds these new. |
| Biometrics (height, weight, BMI, pain score) | **None** | Same — no existing capture. |
| Visual acuity (VA) | **Partial** | Mentioned in `note_orchestrator.py` for AI extraction from a transcript; no storage row. Ambient documentation feature (Phase 57) extracts VA into `structured_facts` but those are not persisted as workup. |
| IOP — discrete measurements | **Yes (Phase 21A)** | `glaucoma_iop_measurements` table stores per-reading IOP for glaucoma trending. Phase 60's `iop_od` / `iop_os` columns are the **encounter-level workup summary**, not a replacement for the longitudinal trending table. |
| Visual field tests | **Yes (Phase 21A)** | `glaucoma_visual_field_tests` table — same pattern as IOP. Phase 60 does not touch this. |
| Allergies / medications (review booleans) | **None** | Read-only `PatientAllergy` / `PatientMedication` interfaces exist in `chart_context.py` for conflict surfacing, but no "I reviewed this at the visit" boolean. Phase 60 adds `allergies_reviewed` / `medications_reviewed`. |
| Dilation status | **None** | No column, no UI. |
| Technician notes | **None** | Phase 60 adds `technician_notes` as a metadata-only free-text field (never written to audit log). |
| Intake / workup lifecycle | **None** | No "workup ready for review" state on encounters today. Phase 60 introduces a `draft → entered → reviewed → signed` lifecycle on the new row. |

## 2. Surrounding infrastructure to build against

### Encounter / patient model

- `encounters` (Phase 19 + later): `id, organization_id, location_id, patient_identifier, patient_name, provider_name, status, scheduled_at, started_at, completed_at, created_at, patient_id (FK nullable), provider_id (FK nullable)`.
- `patients` (Phase 19 native patients): `id, organization_id, external_ref, patient_identifier, first_name, last_name, date_of_birth, sex_at_birth, is_active, created_at`. Unique `(org_id, patient_identifier)`.
- All clinical features filter by `organization_id`; cross-org access returns 404 (not 403).

### Role enum

`apps/api/app/authz.py` confirms five roles: `admin`, `clinician`, `reviewer`, `front_desk`, **`technician`**.

Phase 20C wrote the technician scope: technicians CAN create discrete measurements (IOP, VF, retina injections); they CANNOT sign longitudinal review rows. Phase 60 applies the same shape:

- **technician** — create + update workup (draft / entered), mark entered, **cannot** sign.
- **clinician** — create + update + review + sign.
- **admin** — full.
- **reviewer** — read-only.
- **front_desk** — read denied on clinical detail; mutation denied.

### Alembic migration convention

Recent migrations use a 12-char hex revision id + kebab-cased descriptor file name. The current head is `e1f2a3041508` (Phase 55 fundus_charts table). Phase 60's revision will hang off `e1f2a3041508`.

`scripts/check_alembic_safety.sh` blocks:

- `AUTOINCREMENT` (SQLite-only);
- `datetime('now')` (SQLite function — use `sa.text("CURRENT_TIMESTAMP")` for portability);
- raw `op.execute(... CREATE TABLE ...)` — must use `op.create_table()`.

### Audit recording

`app/audit.py:record(*, event_type, request_id, actor_email, actor_user_id, organization_id, path, method, error_code, detail, remote_addr)`. The `detail` field is metadata-only by convention; clinical body text never leaks. Phase 56 pinned this with a canary regression test for fundus; Phase 57 extended the canary pattern for ambient; Phase 60 will add a vitals canary in the same shape.

### Frontend tabs

`ClinicalTabbedWorkspace` exposes 9 tabs (Phase 19F): `overview | clinical | documentation | imaging | orders-labs | calendar | communications | documents | chat`. The natural home for Phase 60 is the **Clinical tab** (currently hosts the specialty-tracking panel + shortcut grid). The Phase 60 vitals workup panel slots above or alongside specialty tracking.

### Claim policy

`docs/commercial/claims-policy.json` already covers 15 entries. Phase 60 adds four new critical-severity categories:

- `vitals_diagnosis_overclaims` — "AI vitals diagnosis", "automatic vitals diagnosis", "vital-sign diagnosis".
- `treatment_recommendation_overclaims` — "treatment recommendation", "automatic treatment recommendation", "AI prescribes".
- `device_integration_overclaims` — "device integration", "live device integration", "vital-signs device integration".
- `remote_patient_monitoring_overclaims` — "remote patient monitoring", "RPM-ready", "continuous patient monitoring".

## 3. Implementation decision

**Build a single new table** `visit_vitals_workups` with the Phase 60 brief's column set. Add a single migration. Add a single new service module + a single new routes module. Mount the new frontend feature module in the Clinical tab as a wide card above the existing specialty-tracking panel.

**Do not** reuse `scribe_sessions` — its lifecycle is `draft → ready_for_review → reviewed → finalized` (4 states + `discarded`), and the Phase 60 brief specifies `draft → entered → reviewed → signed` (4 states + `superseded` reserved). Storing vitals fields on a scribe-session row would conflate two clinical surfaces.

**Do not** extend `fundus_charts` either — that table is fundus-specific (drawing_json, rendered_svg, laterality). Vitals is its own surface.

**Do not** auto-promote IOP_od / IOP_os into the `glaucoma_iop_measurements` table. That's a separate longitudinal trending feature. Phase 60's IOP columns are an encounter-level workup snapshot. A future phase may add a "promote to glaucoma tracking" action; that is explicitly out of scope.

## 4. Phase 60 implementation surface

| File | Purpose |
|---|---|
| `apps/api/alembic/versions/b1c2d3e4f5a6_phase_60_visit_vitals_workups.py` | Migration: new table + indexes. |
| `apps/api/app/services/vitals_workup.py` | Service: normalize, BMI calc, warnings, lifecycle transitions, audit metadata helper. |
| `apps/api/app/api/vitals_workup.py` | Routes: GET/POST list+create, GET/PATCH detail, POST review, POST sign. |
| `apps/api/app/main.py` | Mount the new router. |
| `apps/api/tests/test_vitals_workup.py` | ~30 tests. |
| `apps/web/src/features/vitals/vitalsTypes.ts` | TypeScript types matching the API contract. |
| `apps/web/src/features/vitals/vitalsApi.ts` | Fetch wrappers. |
| `apps/web/src/features/vitals/VitalsWorkupPanel.tsx` | List + selection + mount. |
| `apps/web/src/features/vitals/VitalsWorkupForm.tsx` | Editable form (BP, temp, pulse, RR, SpO2, height, weight, BMI live, pain score, VA, IOP, dilation, review checks, notes). |
| `apps/web/src/features/vitals/VitalsWorkupSummary.tsx` | Read-only summary + status timeline + signed-lock banner. |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Mount the new card in the Clinical tab. |
| `apps/web/src/test/VitalsWorkupPanel.test.tsx` | Frontend test suite. |
| `docs/workflow/structured-vitals-workup.md` | Feature contract + safety boundary + API reference. |
| `docs/demo/phase-60-vitals-workup-demo-runbook.md` | Operator runbook in the Phase 56/57/59 template. |
| `docs/build/current-product-truth.md` | New "Technician Workup & Structured Vitals" row + 5 new Hard Safety Statements. |
| `docs/commercial/claims-policy.json` | 4 new categories. |
| `scripts/check_{commercial,website,demo}_claims.sh` | Sync fragments. |

## 5. Non-goals (out of scope for Phase 60)

- **No** device integration. No live BP cuff sync, no thermometer sync, no smart-scale sync, no pulse oximeter sync. Phase 60 is manual entry only.
- **No** remote patient monitoring. RPM is out of scope.
- **No** diagnosis. Out-of-range BP/temp/pulse/SpO2 surfaces as a "review required" warning — never as "hypertensive crisis", "fever", "hypoxia", etc.
- **No** treatment recommendation. The service never returns "give X medication" or "schedule Y procedure".
- **No** orders / referrals / patient messaging / billing / coding. Same posture as Phase 56/57/58/59 — pinned in `forbidden_actions`-style invariants.
- **No** image interpretation. Phase 60 does not parse images.
- **No** EHR replacement. ChartNav remains an intake + draft surface; the certified EHR is the system of record.
- **No** real PHI. Demo + tests use synthetic data; the route is fake-data-safe (no `fake_data_context=false` analogue needed — the route does not auto-process raw text).

## 6. Phase 59 doc nit to fix while in `docs/demo/`

PR #66's audit flagged: `docs/demo/phase-59-ambient-demo-qa-checklist.md` references `scripts/reset_demo.sh` which does not exist. Real reset scripts are `scripts/reset_demo_state.sh` and `scripts/reset_phase24b_retina_demo.sh`. Fix the reference as part of this PR's docs sweep.

## Related documents

- `docs/security/chartnav-openai-fake-data-adapter.md` — Phase 52B contract.
- `docs/workflow/ambient-documentation-assist.md` — Phase 57 sibling.
- `docs/workflow/fundus-charting.md` — Phase 55 sibling.
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/commercial/claims-policy.json` — canonical manifest.
