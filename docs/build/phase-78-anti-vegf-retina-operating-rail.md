# Phase 78 — Anti-VEGF Retina Operating Rail

**Date:** 2026-06-09
**Branch:** `feature/phase-78-anti-vegf-retina-operating-rail`
**Base:** `main` at `ab3b9c5` (after Phase 77)
**Status:** First Phase 2 Clinical Intelligence phase

## Purpose

ChartNav's first Phase-2 surface. Records structured retina anti-VEGF
injection workflow metadata (eye, drug class, date, interval, next-due,
authorization status, lot number) and computes a deterministic
readiness queue (due today / due this week / overdue / auth pending /
auth expired / bilateral asymmetric).

This is **workflow intelligence**. It is not:

- diagnosis
- treatment recommendation
- image interpretation
- drug selection
- autonomous orders
- autonomous prior-auth submission
- autonomous billing or coding
- patient messaging

Every value displayed is what the provider entered. ChartNav records
the cadence the provider chose; it does not propose one.

## What changed

### Backend

| File | Kind | Description |
|---|---|---|
| `apps/api/alembic/versions/f8b9c0d1e2f3_phase_78_anti_vegf_injections.py` | New migration | Adds `anti_vegf_injections` table with `id`, `organization_id`, `patient_id`, `encounter_id`, `eye` (CHECK OD/OS), `drug_label` (CHECK 4-value allowlist), `injection_date`, `interval_weeks` (CHECK 1–52), `next_due_date`, `authorization_status` (CHECK 6-value allowlist), `authorization_expires_on`, `lot_number`, `notes`, `created_by_user_id`, audit timestamps. Three indexes for the org/patient/eye/due-date access patterns. |
| `apps/api/app/services/anti_vegf_injections.py` | New service | Pure service: `create_injection()`, `list_history()` (split by eye + bilateral flag), `build_readiness_queue()` (org-scoped, deterministic, latest-per-eye projection). |
| `apps/api/app/api/anti_vegf_injections.py` | New router | `GET /api/v1/patients/{id}/anti-vegf-injections` (with optional `?eye=OD\|OS`), `POST` to the same path, and `GET /api/v1/anti-vegf/readiness-queue`. |
| `apps/api/app/main.py` | Modified | Registers the new router. |
| `apps/api/tests/test_anti_vegf_injections.py` | New | 16 pytest cases covering RBAC, enum validation (eye, drug, auth), interval bounds, auto-computed next-due, history split + bilateral flag, eye-filter, cross-org 404, auth-pending/expired bucket surfacing, bilateral-asymmetric flag, no-clinical-text canary in queue projection. |

### Frontend

| File | Kind | Description |
|---|---|---|
| `apps/web/src/features/anti-vegf/antiVegfTypes.ts` | New | Typed shape. `AntiVegfEye = "OD" \| "OS"`, drug label / auth-status enums, history + queue types. |
| `apps/web/src/features/anti-vegf/antiVegfApi.ts` | New | Fetch wrapper following the identity-resolution pattern. |
| `apps/web/src/features/anti-vegf/InjectionCommandPanel.tsx` | New | Bilateral OD/OS columns with long-form eye labels, latest-injection card per eye (date, drug class, interval, next due, auth badge with expiry, lot number), earlier-injections list per eye, readiness chip per eye (auth-expired / auth-pending / overdue / due-today / due-this-week / future), explicit boundary note. |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Modified | Wires the panel into the Overview tab right after the visit-packet panel, gated on `nativeEncounter && typeof patient_id === "number"`. |
| `apps/web/src/test/InjectionCommandPanel.test.tsx` | New | 12 vitest cases: patient header + bilateral flag, OD/OS columns with long-form labels, per-eye empty state, auth-pending / auth-expired readiness chips, auth badge label, lot + interval + next-due render, earlier-injections list, refresh button refetches, error banner, boundary-note copy assertions, no-forbidden-phrasings canary. |

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/anti-vegf-injections` | required | any role with patient access |
| `GET` | `/api/v1/patients/{patient_id}/anti-vegf-injections?eye=OD\|OS` | required | any role |
| `POST` | `/api/v1/patients/{patient_id}/anti-vegf-injections` | required | admin / clinician / technician |
| `GET` | `/api/v1/anti-vegf/readiness-queue` | required | any role |

Cross-org access returns 404 (no existence leak), matching the rest of the encounter surface.

## Readiness queue buckets

| Bucket | Definition |
|---|---|
| `due_today` | latest `next_due_date == today` for that (patient, eye) |
| `due_this_week` | `today < next_due_date <= today + 7d` |
| `overdue` | `next_due_date < today` |
| `authorization_pending` | latest auth status is `pending` |
| `authorization_expired` | auth is `expired` OR `authorization_expires_on < today` |

`bilateral_asymmetric` lists every patient whose OD and OS landed in different buckets — an operator signal, not a clinical recommendation.

## Metadata-only invariant (extended)

The readiness-queue projection deliberately omits `notes` (the only free-text column). The single-record response includes `notes` because the provider authored it, but it is never aggregated into the queue. The backend test `test_response_omits_forbidden_clinical_phrasings` writes a canary note and asserts it never appears in the queue's serialized JSON.

## Phase 1 → Phase 2 boundary

Phase 1 Clinical Spine (all 10 gates closed in Phases 71–77) provided:
- Encounter workflow
- Vitals / VisitDraft / Fundus capture + sign-lock
- Cross-artifact summary aggregator + timeline (Phase 76)
- Visit packet export (Phase 77)

Phase 2 Clinical Intelligence starts here with workflow surfaces that mirror real specialty operations without taking clinical decisions. Future phases would extend the same pattern:
- Glaucoma progression cockpit (IOP / VF / OCT cadence aggregation — still no interpretation)
- Cataract surgical workflow (pre-op intervals + checklist — still no surgical decision)
- FHIR writethrough (interop, gated)
- MIPS quality capture (reporting, gated)

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_anti_vegf_injections.py -q` | **16 / 16 PASS** |
| Targeted regression (`test_anti_vegf_injections.py` + retina-summary + retina-packet + clinical + vitals) | **84 / 84 PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 805 / 805 tests across 45 files** (was 793; +12 Phase 78) |
| `bash scripts/check_commercial_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/check_demo_claims.sh` | **PASS** — 0 hits |
| `bash scripts/check_website_claims.sh` | **PASS** — 0 fail / 0 warn |
| `bash scripts/test_claim_policy_fixtures.sh` | **PASS** |
| `python3 scripts/check_runtime_safety.py` | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox).

## Caveats

- The migration moved the alembic head from `b1c2d3e4f5a6` (Phase 60 vitals) → `f8b9c0d1e2f3` (Phase 78). Initial commit had `down_revision = "f7a8b9c0d1e2"` (mid-chain) which created multi-head error; corrected to `b1c2d3e4f5a6`.
- `InjectionError` is a non-frozen dataclass (Phase 76 used `frozen=True` for `SummaryError`, but Phase 78 needs mutability because `engine.begin()`'s context manager sets `__traceback__` on the exception during rollback).
- One pre-existing test (`Phase 19F billing-surface absence`) hit my initial banner text containing "insurance claims". Reworded to "does not submit prior-auth" — the same boundary expressed without triggering the regex sentinel.

## Next phase recommendation

**Phase 79 — Glaucoma Progression Cockpit.** Second Phase 2 surface. Aggregate IOP measurements (already on `visit_vitals_workups`), visual-field metadata (already in `imaging_studies` modality `visual_field_*`), and OCT metadata (modality `oct_rnfl`) into a per-eye trend view. Same boundary as Phase 78: ChartNav does not interpret the trend, does not propose a treatment escalation, does not autonomously order tests. The cockpit surfaces what the provider's measurements show — the provider draws the conclusion.
