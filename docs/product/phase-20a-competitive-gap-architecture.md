# Phase 20A — Competitive Gap Architecture + Ophthalmology Positioning Audit

> **Type:** Planning / architecture / audit only.
> **Branch:** `feature/phase-20a-competitive-gap-architecture`.
> **No code, no schema, no migrations, no media binaries.** All
> changes ship as Markdown under `docs/product/`.

This is the index for the **nine-document** set produced as
Phase 20A (eight original docs plus the Phase 20A.1 HIPAA
readiness layer). It audits the current ChartNav repo and lays
out a precise implementation blueprint for the next competitive
upgrade layer: structured data, ophthalmology specialty
modules, an imaging pipeline, multi-clinic scaling, role-based
clinic workflows, sharper ophthalmology-specific public
positioning, and a HIPAA-regulated deployment readiness layer.

The repo audit confirms a recurring pattern: **ChartNav's clinical
encounter-level workflow is stronger than its market-facing
story.** The work below converts existing, real ophthalmology
depth (OD/OS retinal canvas, 13 symbol types, 48 subspecialty
shortcuts, abbreviation-aware search, provider-reviewed AI
governance, FHIR adapter foundation) into longitudinal disease
tracking, clinic-wide work queues, an imaging review pipeline,
and a multi-location operating model.

## The nine docs

| # | Doc | Scope |
|---|---|---|
| 1 | [`phase-20a-competitive-gap-architecture.md`](./phase-20a-competitive-gap-architecture.md) | This index — repo audit summary, competitive gap map, deliverable index |
| 2 | [`chartnav-structured-data-layer-plan.md`](./chartnav-structured-data-layer-plan.md) | Patient segments, tags, problem list, work queues, role-view presets |
| 3 | [`chartnav-role-based-clinic-workflows-plan.md`](./chartnav-role-based-clinic-workflows-plan.md) | Front Desk / Technician / Doctor / Reviewer / Admin dashboards in real eye-clinic lane language |
| 4 | [`chartnav-ophthalmology-specialty-modules-plan.md`](./chartnav-ophthalmology-specialty-modules-plan.md) | Retina / Glaucoma / Cornea / Cataract / Oculoplastics / Pediatric tracking modules that extend (not replace) existing systems |
| 5 | [`chartnav-imaging-pipeline-plan.md`](./chartnav-imaging-pipeline-plan.md) | OCT / fundus / VF / biometry metadata pipeline with provider-review queue |
| 6 | [`chartnav-multi-clinic-scaling-plan.md`](./chartnav-multi-clinic-scaling-plan.md) | Provider-location assignments, location rooms, schedule blocks, operating hours |
| 7 | [`chartnav-ophthalmology-positioning-gap-plan.md`](./chartnav-ophthalmology-positioning-gap-plan.md) | Website / deck / demo positioning rewrite — eye-clinic lane language + subspecialty stratification + safer non-goals |
| 8 | [`chartnav-phase-20-22-implementation-roadmap.md`](./chartnav-phase-20-22-implementation-roadmap.md) | Recommended phased build order (20B, 20C, 21A, 21B, 21C, 22, **23**) with scope, files-touched, tests, risks, "do not touch" lists. Filename retained from Phase 20A; content extended to include Phase 23 in Phase 20A.1. |
| 9 | [`chartnav-hipaa-regulated-deployment-readiness-plan.md`](./chartnav-hipaa-regulated-deployment-readiness-plan.md) | **Phase 20A.1 addition.** HIPAA-regulated deployment readiness — legal / contract / technical / audit / backup / incident-response / vendor / operational policy / validation layers. Defines what's needed before real PHI; explicitly states ChartNav is **not HIPAA compliant by default** and **not HIPAA certified.** |

## Repo audit — what already exists

### Backend (76 endpoints, 20 tables)

| Surface | State |
|---|---|
| Org / Location / User / Patient / Provider / Encounter foundation | ✅ shipped + audited |
| Workflow event log (`workflow_events`) | ✅ shipped |
| Encounter inputs + extracted findings + note versions (Phase 19) | ✅ shipped |
| Chart artifacts (retinal diagram persistence with version chain + immutable signing) | ✅ shipped |
| Scribe sessions (draft → processing → reviewed → finalized lifecycle) | ✅ shipped |
| AI governance log (hashed prompts/outputs, PHI-redaction status, human review tracking) | ✅ shipped |
| Note transmissions (signed-artifact dispatch + log) | ✅ shipped |
| Security audit events (metadata-only, never logs PHI) | ✅ shipped |
| Quick-comment + clinical-shortcut favorites (per-clinician) | ✅ shipped |
| FHIR adapter (read-through + `transmit_artifact()`); native; stub | ✅ shipped |
| Patient segments / tags / problem list / work queues / role views | ❌ not present |
| Imaging studies / files / measurements | ❌ not present (chart_artifacts is retinal-canvas only) |
| Retina / glaucoma / cornea specialty tracking tables | ❌ not present |
| Provider-location assignments / rooms / schedule blocks / operating hours | ❌ not present |
| Role-based dashboards | ❌ not present |

### Frontend clinical app

| Surface | State | Specialty depth |
|---|---|---|
| `ClinicalTabbedWorkspace.tsx` | ✅ Phase 19F/19I — 9 tabs, no Billing | High — burgundy sidebar, recipient-selector chat, intentional empty states |
| `NoteWorkspace.tsx` | ✅ Phase 17/18/19 — transcript → findings → AI draft → signed | High |
| `ScribeSessionPanel.tsx` | ✅ status lifecycle | High |
| `EyeDiagramPanel.tsx` + `RetinalDrawingCanvas.tsx` | ✅ shipped | **Crown jewel** — OD/OS canvas, 13 symbol types, freehand, text labels, undo/redo, signed read-only mode |
| `RetinalProposalReview.tsx` | ✅ shipped | Provider-reviewed AI proposals with provenance preserved |
| `retinalAnnotations.ts` | ✅ 13 symbols, OD/OS, zone-aware, AnnotationSource (`manual` / `ai_approved`), auto-summary block | Strong |
| `clinicalShortcuts.ts` | ✅ **48 shortcuts across 10 subspecialty groups** | Retina (heavy) + Glaucoma + Cornea/anterior + Oculoplastics |
| `quickComments.ts` | ✅ **50 comments across 5 categories** | Symptoms/HPI · Visual function · External/anterior · Posterior · Assessment/plan |
| `PatientSummaryPanel.tsx`, `PreVisitBriefPanel.tsx`, `ProviderActionItemsPanel.tsx` | ✅ shipped | Provider-reviewed |
| Phase 19I Chat recipient selector | ✅ shipped | Demo-local, internal only |

### Marketing / decks / demo

| Asset | Strength |
|---|---|
| OD/OS retinal canvas as the "moat" framing | ✅ strong, preserve |
| Clinical Signal Filtering banner narrative (drusen, OD/OS, flame hemorrhage examples) | ✅ strong, preserve |
| Forbidden-claims discipline (no HIPAA / no certified EHR / no autonomous diagnosis / no auto-orders / no auto-message / no auto-bill) | ✅ rigorous |
| Subspecialty pitch coverage | ⚠️ Retina-heavy; Glaucoma + Cornea **exist in product** (12 of 48 shortcuts) but **don't appear in buyer decks** |
| Real ophthalmology artifact mentions in pitch (OCT macula / RNFL, HVF, fundus, IOLMaster, IRIS Registry, MIPS) | ❌ absent from buyer copy despite VA/IOP/refraction in demo |
| Eye-clinic operational language (front desk → tech workup → VA → IOP → refraction → dilation → MD → recheck → injection → ASC → checkout → sign-off → chart-closure lag) | ❌ replaced by generic "clinical workflow" framing |
| Non-goals specificity | ⚠️ correct ("does not bill", "does not message patients") but generic; missing ophthalmology-specific non-goals ("does not autofill IOP", "does not select IOL power", "does not auto-dose anti-VEGF") |

## The competitive gap, stated honestly

The accurate gap is **not** "ChartNav has no clinical workflow."
The accurate gap is:

> ChartNav has strong **encounter-level ophthalmology workflow**, but
> still needs **longitudinal specialty tracking**, an **imaging-study
> pipeline**, **clinic-wide work queues**, **multi-location operations**,
> and **sharper ophthalmology-specific public positioning** that
> matches the depth already in the product.

What's already real:

- A — **Encounter-level clinical workflow** (scribe → findings → draft → signed)
- B — **Patient-level clinical workflow** (summary panel, pre-visit brief, provider action items)
- C — **Retina artifact / diagram workflow** (immutable signing + version chain)
- D — **Provider-reviewed AI workflow** (governance log, hashed prompts, human review)

What's missing:

- E — **Longitudinal disease tracking** (no retina_tracking / glaucoma_tracking; no IOP series; no VF series)
- F — **Imaging-study pipeline** (chart_artifacts only handles retinal canvas; no OCT/HVF/fundus metadata layer)
- G — **Clinic-wide operational work queues** (encounter_inputs.processing_status is a job queue, not a human work queue)
- H — **Multi-location / multi-provider dashboards** (single org, multi-location supported in data but no cross-location dashboards)
- I — **Role-specific dashboards** for front desk / technician / doctor / reviewer / admin (no dashboard endpoints; admin has `/admin/deployment/*` ops-level only)
- J — **Ophthalmology-specific marketing** (positioning is Retina-only despite product depth in Glaucoma + Cornea)
- K — **HIPAA-regulated deployment readiness** (no BAA template / customer responsibility matrix / subprocessor inventory / PHI data-flow map / incident runbook / admin audit dashboard; Phase 23, planned in Phase 20A.1)

## Reading order

1. Read this doc first for the gap map.
2. Then read the **roadmap** (doc 8) for the recommended phased build order.
3. Then drill into individual plans (docs 2–7) as the relevant phase comes up.

## Hard constraints that bind every plan in this set

- ❌ No HIPAA-compliant claim
- ❌ No HIPAA-certified claim
- ❌ No "approved for real PHI by default" claim
- ❌ No certified EHR claim
- ❌ No autonomous-diagnosis claim
- ❌ No automatic orders / referrals / patient messaging / coding / billing
- ❌ No specific device-integration claim (Cirrus / Spectralis / Triton / Optos / IOLMaster) until the actual adapter ships
- ❌ No real PHI in any demo / capture / artifact
- ❌ No backend code, no migrations, no schema changes in this PR
- ❌ No frontend product code in this PR
- ❌ No production-website update
- ✅ Every proposed table / endpoint / UI is described, not built
- ✅ Every proposed claim is paired with the repo evidence that supports it
- ✅ Every "future" mention is explicitly labeled future
- ✅ Any reference to HIPAA readiness uses the exact safe readiness statement from the [HIPAA-regulated deployment readiness plan](./chartnav-hipaa-regulated-deployment-readiness-plan.md#9-exact-safe-readiness-statement)

## Validation

- `bash scripts/check_commercial_claims.sh` — must pass 0 fail / 0 warn
- `git diff --name-only main...HEAD` — must show only `docs/product/*.md`
- No `apps/api/`, `apps/web/src/`, `migrations/`, `package.json`, or media-binary changes
