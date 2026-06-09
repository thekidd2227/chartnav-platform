# Phase 81 — Provider Action Item Queue

**Date:** 2026-06-09
**Branch:** `feature/phase-81-provider-action-item-queue`
**Base:** `main` at `f2573ba` (after Phase 80)
**Status:** Fourth Phase 2 Clinical Intelligence surface — the cross-specialty capstone

## Purpose

A single provider-facing triage queue that aggregates deterministic
workflow signals from the three Phase 2 surfaces plus the Phase 1
signed-lock workflow:

| Source | Signals consumed |
|---|---|
| `anti_vegf` (Phase 78) | readiness-queue buckets (due today / overdue / auth expired / due this week / auth pending) |
| `glaucoma` (Phase 79) | VF / OCT studies in `ready_for_review`; IOP-without-imaging completeness gaps |
| `cataract` (Phase 80) | missed post-op checkpoints; planned surgery with incomplete pre-op signals; provider-entered complications flag |
| `visit_summary` / `signed_lock` (Phase 1) | unsigned vitals workups, unfinalized visit drafts, unsigned fundus charts |

**This is NOT autonomous clinical prioritization.** Every bucket
assignment is a documented deterministic rule over provider-entered
structured data (due dates, missing attestations, unsigned
artifacts). ChartNav does not diagnose, does not recommend treatment
or surgery, does not interpret images, and does not decide clinical
urgency.

## Schema

**None.** Pure aggregation over existing tables
(`anti_vegf_injections` via the Phase 78 service, `imaging_studies`,
`visit_vitals_workups`, `cataract_workflow_records`,
`scribe_sessions`, `fundus_charts`, `patients`).

## Endpoint

| Method | Path | Auth |
|---|---|---|
| `GET` | `/api/v1/provider-action-queue` | any authenticated caller; org-scoped |

Caller-org-scoped, matching the Phase 78 readiness-queue convention
(the queue belongs to the authenticated caller's organization, not a
path-specified provider id). Distinct from the older per-patient
`/patients/{id}/provider-action-items` surface, which is untouched.

## Deterministic bucket rules

| Bucket | Rule |
|---|---|
| `same_day` | anti-VEGF due today / overdue / auth expired; cataract post-op checkpoint marked `missed` |
| `this_week` | anti-VEGF due ≤ 7 days / auth pending; glaucoma VF/OCT study `ready_for_review`; cataract planned surgery with incomplete pre-op signals; cataract provider-entered complications flag |
| `routine` | unsigned vitals workup; unfinalized visit draft; unsigned fundus chart |
| `informational` | IOP on file with no VF and no OCT RNFL metadata (`insufficient_data`) |

## Item shape

```jsonc
{
  "item_id": "anti_vegf:injection_due_today:12",   // stable synthetic id
  "patient_id": 1,
  "patient_identifier": "PT-1001",
  "patient_name": "Morgan Lee",
  "encounter_id": 1,
  "laterality": "OD",                               // OD / OS / OU / null
  "specialty_source": "anti_vegf",                  // 5-value enum
  "category": "injection_due_today",
  "label": "Injection due today",
  "detail": "Provider-entered cadence for OD: ...", // templated metadata only
  "status": "due_today",
  "priority_bucket": "same_day",
  "source_artifact_id": 12,
  "created_at": "...",
  "due_at": "2026-06-09",
  "insufficient_data": false,
  "requires_provider_review": true
}
```

Response wrapper carries `buckets` (4 keys), `totals`, `total_items`,
`sources_present`, and the boundary `disclosure` verbatim.

## Free-text invariant

No provider free text is ever aggregated into the queue — labels and
details are templated metadata strings. The backend test
`test_cataract_complications_flag_surfaces_this_week` writes a canary
`complication_note` and asserts it never appears in the queue JSON.

## Files

| File | Kind |
|---|---|
| `apps/api/app/services/provider_action_queue.py` | New service (~480 lines) |
| `apps/api/app/api/provider_action_queue.py` | New router |
| `apps/api/app/main.py` | Registers router |
| `apps/api/tests/test_provider_action_queue.py` | 13 pytest cases |
| `apps/web/src/features/action-queue/actionQueueTypes.ts` | New |
| `apps/web/src/features/action-queue/actionQueueApi.ts` | New |
| `apps/web/src/features/action-queue/ProviderActionItemQueue.tsx` | New panel — 4 grouped sections, laterality / source / status / insufficient-data / provider-review badges |
| `apps/web/src/ClinicalTabbedWorkspace.tsx` | Wires queue at the top of the Phase 2 stack in the Overview tab |
| `apps/web/src/test/ProviderActionItemQueue.test.tsx` | 10 vitest cases |

## Validation

| Check | Result |
|---|---|
| `python3 -m pytest tests/test_provider_action_queue.py -v` | **13 / 13 PASS** |
| Targeted regression (7 suites incl. old provider_action_items) | **107 / 107 PASS** |
| `npx tsc --noEmit` | **PASS** |
| `npx vitest run` | **PASS — 840 / 840 tests across 48 files** (was 830; +10) |
| All 5 claim/safety scripts | **PASS** |
| `git diff --check` | clean |

Phase 63C smoke not run (no live API in sandbox). No demo/smoke
scripts touched; queue is additive.

## Caveats

- Endpoint is caller-org-scoped rather than `providers/{provider_id}`
  path-scoped — consistent with the codebase's `require_caller`
  convention and the Phase 78 readiness queue. The prompt explicitly
  permitted this.
- The queue panel performs a fetch on mount inside the Overview tab;
  existing ClinicalTabbedWorkspace tests tolerate this the same way
  they tolerate the Phase 76–80 panels (error banner on failed fetch).
- Glaucoma "informational" completeness rule keys on IOP rows with
  `patient_id` set; legacy vitals rows without patient linkage are
  skipped rather than guessed.

## Next phase recommendation

**Phase 82 — Note Validation Rail.** Per the master build document's
Layer 2 list ("Note validation — laterality, staging, follow-up —
checked before sign"): deterministic pre-sign checklist that verifies
a visit draft references the same laterality as its fundus chart and
vitals, has a follow-up interval recorded, and has no unsigned
upstream artifacts — surfaced as provider-review checks, never as
autonomous blocking beyond the existing sign-attestation flow.
