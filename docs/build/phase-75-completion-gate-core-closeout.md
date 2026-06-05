# Phase 75 — Completion Gate Audit + Remaining Core Feature Closeout

**Date:** 2026-06-05
**Branch:** `feature/phase-75-completion-gate-core-closeout`
**Base:** `main` at `e28e10d` (after Phase 73)

## Purpose

Verify what the buyer-demo / Phase-1-clinical-spine work actually contains in
the repo today, mark each gate complete / partial / missing / unsafe-to-start,
close the small + safe gaps, and identify the precise next phase boundary
before Phase 2 Clinical Intelligence (Anti-VEGF / glaucoma / FHIR / MIPS) can
begin.

This is a completion audit, not a roadmap. Each gate is a verifiable claim
against `main` (or against the open PR queue), not an aspiration.

## Completion matrix

| # | Gate | Status | Evidence in repo |
|---|---|---|---|
| 1 | Laterality / OD-OS support | **Complete** | `Laterality = "OD" \| "OS" \| "OU"` in `apps/web/src/features/fundus/fundusTypes.ts`. `visual_acuity_od/os/ou`, `iop_od/os`, `iop_method`, `dilation_status` on `VitalsWorkup`. Fundus panel renders long-form (`OD · Right Eye`, etc.) since Phase 72. 30+ backend service files reference laterality. |
| 2 | `/api/v1/encounters/{id}/retina-visit-summary` | **Missing — documented** | Endpoint does not exist in `apps/api/app/api/routes.py`. Per-artifact endpoints exist (`/vitals-workups`, `/scribe-sessions`, `/fundus-charts`, `/notes`, `/events`) but no aggregator. Requires a new GET endpoint that joins the three artifact families for the bridged visit row. **Recommended for Phase 76 (retina visit summary endpoint + buyer-credible aggregator) — not started here.** |
| 3 | Retina visit sequence / ribbon state | **Complete** | `apps/web/src/RetinaVisitSequenceRibbon.tsx` (Phase 71) wired into `ClinicalTabbedWorkspace.tsx`. 5-step ribbon: Intake → Fundus Drawing → VisitDraft → Provider Review → Signed Lock. Role-aware. Test file `RetinaVisitSequenceRibbon.test.tsx` covers role variants. |
| 4 | Physician action rail | **Complete** | `apps/web/src/ProviderActionItemsPanel.tsx` + backend `apps/api/app/api/provider_action_items.py` (4 endpoints: generate, list, get, dismiss/complete) + `apps/api/app/services/provider_action_items.py`. Three-tier priority surfaced in UI. |
| 5 | Metadata-only evidence timeline | **Partial** | `workflow_events` table + `security_audit_events` table both back metadata-only timelines. Overview tab surfaces encounter events. Per-artifact signed banners include reviewer/signer/timestamp. **Gap: no consolidated cross-artifact timeline view.** Closing the cross-artifact view requires a frontend aggregator and ideally the retina-visit-summary endpoint from Gate #2. **Deferred to Phase 76.** |
| 6 | Signer/reviewer normalization across Vitals, VisitDraft, Fundus | **Partial — closed in this PR** | After Phase 73, Vitals and Ambient gained a `vitals-audit-note` / `ambient-audit-note` line stating "ChartNav records metadata-only audit events: who created, reviewed, and signed, and when. The audit trail does not store clinical free text." Fundus (upgraded earlier in Phase 72) had `fundus-signed-reviewer` and `fundus-signed-summary` lines but NOT the audit-note line. This PR adds `fundus-audit-note` to bring Fundus to parity. |
| 7 | Demo reset + seeded patient reliability | **Partial — Phase 74 PR #98 open** | On `main`: `scripts/reset_demo_state.sh` + `scripts/demo/phase63c_functional_smoke.sh --reset` exist. PR #98 (not yet merged) adds `scripts/verify_seed_invariants.py` (8-invariant verifier), `scripts/demo/demo_preflight.sh` (read-only readiness gate), and enhances reset/smoke with port guidance + artifact accumulation warnings. **Merge PR #98 before declaring Gate 7 complete.** |
| 8 | Retina visit packet export | **Missing — documented** | No `visit-packet` / `VisitPacket` / `retina_packet` references anywhere in `apps/`. Phase 70 recommended Phase 75 = "Export / Share Packet". This audit reassigns that work to Phase 77 (after the retina-visit-summary aggregator endpoint lands in Phase 76) because the packet builder consumes the aggregator's output. **Recommended for Phase 77 — not started here.** |
| 9 | Phase 63C smoke stability | **Complete** | `scripts/demo/phase63c_functional_smoke.sh` is the 7-section, 20-gate smoke that drives Vitals/VisitDraft/Fundus happy paths and manual_note shape. Supports `--reset`. PR #98 adds `--preflight` + better port-error messaging but doesn't change the underlying gate suite. |
| 10 | No real PHI / no production LLM / no autonomous claims | **Complete** | All 5 claim-safety scripts PASS on every Phase 71–74 PR. `python3 scripts/check_runtime_safety.py` PASS. Per-artifact safety banners present (`vitals-safety-banner`, `ambient-safety-banner`, `fundus-safety-banner`). "What ChartNav did NOT do" cards on every artifact. Vitest regex sweep over rendered DOM catches forbidden phrases. |

## Code change in this PR

Closing Gate #6 (Fundus signed-lock audit-note parity with Vitals + Ambient).

**Files:**
- `apps/web/src/features/fundus/FundusChartEditor.tsx` — add `fundus-audit-note` paragraph inside the existing signed-lock banner. Same language Phase 73 added to Vitals + Ambient.
- `apps/web/src/test/FundusChartPanel.test.tsx` — add a vitest assertion that the audit-note renders on signed fundus charts and contains the required language.

No backend, no schema, no migration, no new components.

## Out of scope (explicit deferrals)

The following items were considered and explicitly deferred. They are not
small, not safe to start without isolation, or are explicitly forbidden by the
operator prompt:

| Item | Why deferred | Recommended phase |
|---|---|---|
| `/api/v1/encounters/{id}/retina-visit-summary` aggregator endpoint | Backend route + service + schema work — requires phase isolation | Phase 76 |
| Cross-artifact buyer-visible timeline view | Depends on Gate #2's aggregator output | Phase 76 (UI half) |
| Retina visit packet export | Depends on Gate #2's aggregator output | Phase 77 |
| Anti-VEGF interval / auth / inventory operating rail | Phase 2 clinical intelligence territory; explicitly out of scope per operator prompt | Phase 81+ (after Phase 1 closeout) |
| Glaucoma progression cockpit (IOP + VF + OCT synthesis) | Phase 2 clinical intelligence territory; explicitly out of scope | Phase 81+ |
| FHIR integration writethrough | Phase 2 interoperability; backend phase, explicit prohibition | Phase 81+ |
| MIPS / IRIS quality capture | Phase 2 quality reporting; out of scope | Phase 81+ |
| Production LLM enablement | Explicitly forbidden by every phase prompt and runtime safety validator | Not approved |

## Exit criteria for "Phase 1 Clinical Spine is closed"

To declare Phase 1 complete and unblock Phase 2 Clinical Intelligence work,
the following must be true (all dependencies should be merged onto `main`):

1. PR #98 (Phase 74 demo reset reliability) merged → Gate 7 complete
2. This PR (Phase 75 Fundus audit-note parity) merged → Gate 6 complete
3. Phase 76 (retina-visit-summary endpoint + cross-artifact timeline) merged → Gates 2 + 5 complete
4. Phase 77 (visit packet export, optional) merged → Gate 8 complete

After (1), (2), and (3): **Phase 1 is functionally closed**. Phase 8 can begin.
Phase 77 (8) is a buyer-experience polish, not a clinical spine requirement.

## Validation performed

| Check | Result |
|---|---|
| Audit grep for laterality references | ✅ 30+ files |
| Audit grep for retina-visit-summary | ❌ 0 backend files (confirmed missing) |
| Audit grep for RetinaVisitSequenceRibbon | ✅ 3 files (component + wire + test) |
| Audit grep for provider-action rail | ✅ Panel + API + service all present |
| Audit grep for cross-artifact audit-note language | 🟡 Vitals + Ambient have it, Fundus does not (closed by this PR) |
| Audit grep for visit-packet | ❌ 0 references (confirmed missing) |

## Next phase recommendation

**Phase 76 — Retina Visit Summary Aggregator + Cross-Artifact Timeline.**

Scope:
- Backend: new `GET /api/v1/encounters/{encounter_id}/retina-visit-summary` endpoint that joins encounter + bridged patient + vitals workups + scribe sessions + fundus charts + workflow events, returning the chronological metadata-only timeline that already exists across the three artifact tables.
- Frontend: a new read-only `RetinaVisitTimeline` component in `ClinicalTabbedWorkspace` Overview tab that consumes the aggregator and renders the cross-artifact provider-review trail with the metadata-only audit note already standardized across Vitals + Ambient + (after this PR) Fundus.

That single phase closes Gate #2 and the remaining half of Gate #5 in one
backend route + one frontend component. After Phase 76 merges, Phase 1 is
formally closed and Phase 2 Clinical Intelligence work can begin in an
isolated phase tree.
