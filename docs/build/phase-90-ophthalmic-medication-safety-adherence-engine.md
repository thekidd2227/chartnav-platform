# Phase 90 — Ophthalmic Medication Safety & Adherence Engine

**Date:** 2026-06-11
**Branch:** `feature/phase-90-ophthalmic-medication-safety-adherence`
**Base:** `main` after Phase 88 Imaging Metadata Review Linkage (`1ef3ca3`)
**Status:** Twelfth Phase 2 Clinical Intelligence surface — provider-reviewed medication safety + adherence support, building on Phase 85.

## Purpose

Phase 90 extends the Phase 85 `medications` table with adherence +
review columns and adds a deterministic rule engine that surfaces
provider-reviewable safety events into the cross-phase aggregator
surfaces (Phase 76 summary, Phase 77 packet, Phase 81 queue, Phase
82 validation, Phase 86 adaptive workspace).

This phase is **workflow safety support**, not medication
recommendation, not prescribing, and not autonomous clinical
decision-making. ChartNav does NOT prescribe, does NOT recommend a
medication change, does NOT recommend stopping a medication, does
NOT diagnose, does NOT recommend treatment or surgery, does NOT
place orders, does NOT send prescriptions or referrals, does NOT
bill or code, and does NOT submit to pharmacies, payers, or EHRs.

Severity values `hard_stop` and `alert` are **reserved** for a
future qualified-operator extension. The Phase 90 seeded rules use
`advisory` only.

## Schema

Alembic revision `g5b6c7d8e9f0`:

### Extension to `medications` (Phase 85)

| Column | Type | Notes |
|---|---|---|
| `preservative_type` | text | CHECK closed allowlist (BAK / preservative_free / other / unknown); default `unknown` |
| `last_fill_date` | date | nullable |
| `days_supply` | int | nullable; CHECK 1-365 when present |
| `reviewed_by_user_id` | int FK users | nullable |
| `reviewed_at` | datetime | nullable |

### New: `medication_safety_rules`

Closed-allowlist rule registry. Phase 90 seeds 5 global DEMO rules
(organization_id IS NULL). The application layer marks every
seeded rule_key as `internal_demo_only=True` + `verified_for_clinical_use=False`.

| Column | Type | Notes |
|---|---|---|
| `id` / `organization_id` | int | scope |
| `rule_key` | text | non-empty CHECK |
| `rule_name` | text | non-empty CHECK |
| `medication_class` | text | nullable |
| `trigger_context` | text | preservative_burden / refill_gap / cataract_alpha_blocker / duplicate_class / review_missing |
| `severity` | text | CHECK hard_stop / alert / advisory |
| `message` | text | template |
| `requires_acknowledgement` | bool | default false |
| `status` | text | CHECK active / inactive |
| `created_at` / `updated_at` | datetime | server-set |

UNIQUE on `(organization_id, rule_key)`.

### New: `medication_safety_events`

Materialized event rows reconciled deterministically from rules +
medications on every read.

| Column | Type | Notes |
|---|---|---|
| `id` / `organization_id` / `patient_id` | int | scope |
| `encounter_id` / `medication_id` | int | nullable |
| `rule_key` | text | non-empty CHECK |
| `severity` | text | CHECK |
| `laterality` | text | CHECK OD/OS/OU/none |
| `status` | text | CHECK active/acknowledged/resolved |
| `message` | text | template populated from rule + current state |
| `acknowledged_by_user_id` / `acknowledged_at` | int / datetime | actor metadata |
| `created_at` / `updated_at` | datetime | server-set |

Indexes: `(organization_id, patient_id)`, `(organization_id, encounter_id)`, `(status, severity)`.

## Seeded rules (DEMO only)

| Rule key | Trigger | Severity |
|---|---|---|
| `ophth_preservative_burden_advisory` | ≥ 3 active BAK-preserved drops | advisory |
| `ophth_refill_gap_advisory` | (last_fill_date + days_supply) past today by > 7 days | advisory |
| `ophth_cataract_alpha_blocker_review` | cataract workflow record + active alpha-blocker | advisory |
| `ophth_duplicate_class_advisory` | 2+ active drops in the same medication_class | advisory |
| `ophth_medication_review_missing_advisory` | active medication(s) with no review or recording within 365 days | advisory |

A freshly-recorded medication counts as an implicit review
(recording IS review).

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/medication-safety` | required | any caller with patient access |
| `POST` | `/api/v1/encounters/{encounter_id}/ophthalmic-medications` | required | admin / clinician |
| `POST` | `/api/v1/medication-safety-events/{event_id}/acknowledge` | required | admin / clinician |
| `GET` | `/api/v1/analytics/medication-safety` | required | any caller |

Cross-org → 404 (no existence leak). GET refreshes the deterministic
projection before returning so events always reflect current state.

## Cross-phase integrations

### Phase 76 — Retina Visit Summary

Adds `ophthalmic_medication_safety_summary` (counts + boundary_note;
no clinical free text). Audit disclosure extended with the Phase 90
boundary statement.

### Phase 77 — Retina Visit Packet Export

Embeds the same metadata-only summary block with an empty fallback.

### Phase 79 — Glaucoma Progression Cockpit / Phase 80 — Cataract Surgical Workflow

No service change required — the action queue + note validation
surfaces are the primary integration. The Phase 86 adaptive
workspace places the panel adjacent to the glaucoma cockpit and
cataract workflow.

### Phase 81 — Provider Action Item Queue

New `medication_safety` source with category
`medication_safety_event_active`. **Always informational priority —
never tier 1.** Item disappears as soon as every active event is
acknowledged or auto-resolved.

### Phase 82 — Note Validation Rail

| State | check_id | status |
|---|---|---|
| Active events present | `medication_safety:active` | warning |
| Active medications + no active events | `medication_safety:clear` | pass |
| No active medications | `medication_safety:no_medications` | pass |

`requires_provider_acknowledgement` is always `false`. **Never
blocks signing.**

### Phase 86 — Subspecialty Adaptive Workspace

`ophthalmic_medication_safety` added to `PANEL_CODES` + `PANEL_LABELS`.

- **Retina:** visible.
- **Glaucoma / Cataract:** prioritized.
- **Comprehensive:** prioritized.

## Forbidden behaviors (verified)

- ChartNav does NOT prescribe.
- ChartNav does NOT recommend a medication, recommend stopping, or
  recommend changing a medication.
- ChartNav does NOT diagnose, interpret images, or recommend
  treatment / surgery.
- ChartNav does NOT place orders, send prescriptions, or send
  referrals.
- ChartNav does NOT bill or code.
- ChartNav does NOT submit to pharmacies, payers, or EHRs.
- Phase 90 queue items are informational only — never tier 1.
- Phase 82 medication safety checks never require acknowledgement
  and never block signing.

## UI

New module `apps/web/src/features/medication-safety/`:

- `medicationSafetyTypes.ts` — types.
- `medicationSafetyApi.ts` — `getMedicationSafety`,
  `postOphthalmicMedication`, `postAcknowledgeEvent`.
- `MedicationSafetyPanel.tsx` — provider-reviewed panel with:
  - Signal counters (active meds, preservative burden, refill gaps,
    active advisories).
  - Internal-demo caution banner when DEMO rules are present.
  - Event list with severity badge + acknowledge button.
  - Active medication list with last-fill / days-supply / refill-gap.
  - Add-medication form (provider-entered).
  - Disclosure rendered verbatim from server.

Wired into Phase 86 adaptive workspace as `ophthalmic_medication_safety`.
Imported as `OphthalmicMedicationSafetyPanel` (a re-aliased
import of the new Phase 90 component) so it coexists cleanly with
the Phase 85 `MedicationSafetyPanel` under `features/medications/`.

WCAG 2.1 AA contrast preserved.

## Tests

Backend:

- `tests/test_medication_safety.py` — 23 tests covering POST + GET +
  RBAC + rule engine fires/clears + ack flow + analytics + safety
  canary.
- `tests/test_medication_safety_integrations.py` — 9 tests covering
  Phase 76 summary + Phase 77 packet + Phase 81 queue (never tier 1,
  drops on ack) + Phase 82 validation states.

Web:

- `src/test/MedicationSafetyPhase90Panel.test.tsx` — 14 tests
  covering render, signals, demo-caution, empty, populated, ack
  flow, ack error, form POST, form error, refresh, disclosure
  verbatim, forbidden-phrase canary sweep.

## Smoke

- Backend Phase 90 + integrations + workspace coverage: **46/46 PASS**.
- Web vitest: **933/933 PASS** (up from 919).
- `npx tsc --noEmit` — clean.
- All five safety scanners pass.
- `git diff --check` — clean.
- Phase 63C functional smoke — NOT run; no local stack booted in
  this verification.

## Caveats

- The rule engine reconciles events on every read of
  `/medication-safety`. This is O(active_medications) per request;
  the projection is intentionally cheap.
- `hard_stop` and `alert` severities are reserved. The seeded rules
  ship `advisory` only.
- Phase 90's `ophthalmic_medication_safety_summary` field name in
  the summary/packet is intentionally distinct from Phase 85's
  pre-existing `medication_safety_summary` field.
- The Phase 90 frontend panel is imported with an alias
  (`OphthalmicMedicationSafetyPanel`) so it does not collide with
  the Phase 85 `MedicationSafetyPanel`. Both coexist; both have
  unique `data-testid` prefixes (Phase 85 = `medication-`,
  Phase 90 = `medication-safety-`).
- The cataract alpha-blocker rule matches both Phase 85's
  `alpha_agonist` medication_class AND a substring sweep over
  common tamsulosin / doxazosin / silodosin / terazosin / Flomax
  brand names in `medication_name`. The substring sweep is
  case-insensitive and deterministic.
- Newly-recorded medications count as implicit reviews so the
  review-missing advisory does not fire instantly on every add.

## Recommended next phase

**Phase 91 — Subspecialty Adaptive Workspace Completion +
Specialty Visit Mode Routing.** Adds a deterministic
visit-mode router (intake / surgical pre-op / post-op /
follow-up / lab review) that further refines the Phase 86
adaptive workspace per visit context. Boundary: ChartNav does
not auto-classify the encounter purpose; the visit mode is
provider-driven.
