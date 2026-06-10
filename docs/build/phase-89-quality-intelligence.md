# Phase 89 — IRIS / MIPS Quality Intelligence

**Date:** 2026-06-10
**Branch:** `feature/phase-89-iris-mips-quality-intelligence`
**Base:** `main` after Phase 88 release hardening (`12669c1`)
**Status:** Twelfth Phase 2 Clinical Intelligence surface — provider-reviewed quality documentation support.

## Purpose

Phase 89 introduces a **provider-reviewed quality documentation
support** surface for ophthalmology. It surfaces deterministic
"is this measure applicable?", "did the provider record a
response?", and "what structured fields are still missing?"
signals across the encounter and the org. It records provider
responses as structured rows that can be exported later by a
qualified operator into whatever program-specific submission
format is required.

**ChartNav does NOT submit to CMS / IRIS / payers / registries.**
ChartNav does NOT autonomously compute MIPS scoring. ChartNav
does NOT autonomously decide whether a measure is met — the
provider records the response. ChartNav does NOT interpret
images, does NOT diagnose, and does NOT recommend treatment
based on quality state. Every seeded measure spec is marked
**`verified_for_submission = false`** until a qualified operator
explicitly verifies it; this is enforced at the projection
layer.

## Schema

Alembic revision `f4a5b6c7d8e9` adds two tables:

### `quality_measure_specs`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | auto |
| `organization_id` | int FK | nullable (global specs allowed) |
| `measure_id` | string(64) | non-empty (CHECK) |
| `measure_name` | string(255) | non-empty (CHECK) |
| `program_year` | int | 2020..2030 (CHECK) |
| `applicable_icd10_prefixes` | text | JSON array |
| `required_fields` | text | JSON array |
| `exception_codes` | text | JSON array |
| `status` | string(16) | active / inactive (CHECK) |
| `created_at` / `updated_at` | datetime | server-set |

`UNIQUE (organization_id, measure_id, program_year)`.

### `quality_measure_responses`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | auto |
| `organization_id` | int FK | required |
| `patient_id` | int FK | required |
| `encounter_id` | int FK | required |
| `measure_id` | string(64) | non-empty (CHECK) |
| `response_type` | string(24) | met/exception/exclusion/not_applicable/incomplete (CHECK) |
| `exception_code` | string(64) | nullable; validated against spec at service layer |
| `responded_by_user_id` | int FK users | required |
| `responded_at` / `created_at` / `updated_at` | datetime | server-set |

`UNIQUE (organization_id, encounter_id, measure_id)` — each
measure has at most one current response per encounter
(upsert semantics on POST).

### Seeded internal demo specs

Three illustrative specs are seeded as **global** rows
(`organization_id IS NULL`) by `scripts_seed.py`. Each
`measure_name` starts with "(DEMO — internal placeholder, NOT
verified for submission)" and each `measure_id` is in the
`INTERNAL_DEMO_MEASURE_IDS` set so the projection layer
unconditionally flags `verified_for_submission=false`:

| measure_id | measure_name | program_year |
|---|---|---|
| `chartnav_demo_ophth_dr_communication` | DR communication with primary care (DEMO) | 2026 |
| `chartnav_demo_ophth_poag_iop_documentation` | POAG IOP documentation (DEMO) | 2026 |
| `chartnav_demo_ophth_dr_screening` | DR screening within 12 months (DEMO) | 2026 |

These specs are **NOT** intended for real-program use. Any
operator preparing for a real CMS / IRIS / payer cycle must
replace these rows with a verified spec set before any
submission.

## Endpoints

| Method | Path | Auth | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/encounters/{encounter_id}/quality-measures` | required | any caller with encounter access |
| `POST` | `/api/v1/encounters/{encounter_id}/quality-measures/{measure_id}/response` | required | admin / clinician |
| `GET` | `/api/v1/analytics/quality?program_year=…` | required | any caller |

Cross-org access → 404 (no existence leak).

Query parameter `program_year` is optional and supports
`?program_year=2026`-style filtering on both the encounter and
analytics endpoints. Range 2020..2030.

GET encounter response shape:

```jsonc
{
  "encounter_id": 1,
  "counts": { "total": 3, "applicable": 3, "incomplete": 2, "completed": 1 },
  "items": [{
    "measure_id": "…",
    "measure_name": "…",
    "applicable": true,
    "response_status": "pending" | "met" | "exception" | "exclusion" | "not_applicable" | "incomplete",
    "missing_structured_fields": ["visit_draft_signed"],
    "verified_for_submission": false,
    "internal_demo_only": true,
    "submission_status": "not_submitted",
    "responded_by_display": "…",
    "responded_by_role": "clinician",
    "responded_at": "…"
  }],
  "supported_response_types": ["met", "exception", "exclusion", "not_applicable", "incomplete"],
  "internal_demo_specs_present": true,
  "submission_status": "not_submitted",
  "disclosure": "Provider-reviewed quality documentation support. ChartNav does NOT submit to CMS, IRIS, payers, or registries…"
}
```

## Applicability + completion projection

- **Applicability** is keyed off the encounter's Phase 86
  `encounter_type` (subspecialty workspace profile). The DR
  screening demo spec is applicable when encounter_type ∈
  {retina, comprehensive}; POAG IOP applies to {glaucoma,
  comprehensive}; DR communication applies to {retina, glaucoma,
  comprehensive}. Non-demo specs default to applicable on every
  encounter.
- **Completion state** uses the `quality_measure_responses` row
  per (encounter, measure). When none exists, `response_status`
  is `pending` (or `not_applicable` when the spec isn't
  applicable). When a row exists, the persisted `response_type`
  is surfaced.
- **Missing structured fields** is a deterministic diff between
  the spec's `required_fields` and the set of structured fields
  the patient/encounter already carries. The structured-field
  presence query inspects vitals workup, scribe sessions,
  fundus charts, disease stages, and imaging reviews.

## Cross-phase integrations

### Phase 76 — Retina Visit Summary

Embeds `quality_intelligence_summary` (counts + boolean flags +
`submission_status`). `audit_disclosure` extended with the
quality boundary statement.

### Phase 77 — Retina Visit Packet Export

Inherits the same metadata-only `quality_intelligence_summary`
block. No clinical narrative; no submission claim.

### Phase 81 — Provider Action Queue

New `quality` source with category
`quality_measure_incomplete`. Surfaces encounters that have
**both** open quality items **and** at least one structured
artifact attached (vitals workup, visit draft, fundus chart,
disease stage, or imaging review). Empty encounters do not
pollute the queue.

Always **informational only** — never Tier 1.

### Phase 82 — Note Validation Rail

Adds one informational check per encounter (mutually
exclusive):

| State | check_id | status |
|---|---|---|
| No applicable measures | `quality:not_applicable` | `pass` |
| Some applicable measures still pending | `quality:incomplete` | `warning` |
| All applicable measures have a recorded response | `quality:documented` | `pass` |

`requires_provider_acknowledgement` is always `false`. The
quality check **never blocks signing** and never appears in
`acknowledgements_required`.

### Phase 86 — Subspecialty Adaptive Workspace

Adds `quality_intelligence` to `PANEL_CODES` + `PANEL_LABELS`.
Per profile:

- **Retina / Glaucoma / Cataract:** visible alongside disease
  staging.
- **Comprehensive:** prioritized at the end of the panel
  list. No collapse.

The Phase 86 "never hide data" contract is preserved.

## Forbidden behaviors (verified)

- ChartNav does NOT submit to CMS / IRIS / payers / registries.
- ChartNav does NOT autonomously compute MIPS scoring.
- ChartNav does NOT autonomously decide whether a measure is
  met.
- ChartNav does NOT diagnose.
- ChartNav does NOT interpret images.
- ChartNav does NOT recommend treatment, surgery, injections,
  or medications.
- ChartNav does NOT auto-bill, auto-code, or send claims.
- ChartNav does NOT make payer-readiness or compliance
  guarantees.
- The Phase 81 queue item is informational only — never Tier 1.
- The Phase 82 validation check is informational only — never
  blocks signing.
- The Phase 77 packet projection contains no clinical narrative
  and no submission status beyond `not_submitted`.

## UI

New module `apps/web/src/features/quality-intelligence/`:

- `qualityIntelligenceTypes.ts` — types.
- `qualityIntelligenceApi.ts` — `getQualityMeasures` +
  `postQualityResponse`.
- `QualityIntelligencePanel.tsx` — read + respond panel.

Panel features:

- Internal-demo caution banner (orange) when seeded demo specs
  are present.
- Counters: applicable / documented / awaiting response /
  submission status (always "not submitted").
- Per-measure row with a status pill (green = met / exception /
  exclusion, amber = pending / incomplete, neutral =
  not_applicable), missing-field list, demo-flag callout, and
  responder metadata when on file.
- Response controls per applicable row: `Met`, `Incomplete`,
  `Not applicable`, plus a typed exception-code selector +
  `Record exception` button, plus `Exclusion` button.
- Disclosure banner rendered verbatim from the server.

Wired into the Phase 86 adaptive workspace via the existing
`AdaptiveOverviewPanels` resolver as the new
`quality_intelligence` panel code. Action queue source label
`quality` → "Quality documentation".

WCAG 2.1 AA contrast preserved.

## Tests

Backend:

- `apps/api/tests/test_quality_intelligence.py` — 24 tests
  covering GET shape, internal-demo flag enforcement,
  disclosure language, supported-types allowlist, pending
  status when no response, program-year filter, cross-org 404,
  unknown encounter 404, POST met / exception / invalid type /
  invalid exception-code-without-exception / exception-code-
  not-in-spec / unknown measure 404 / RBAC / cross-org / upsert
  idempotency, analytics baseline + counts + disclosure +
  program-year filter + cross-org scoping, plus a
  forbidden-phrase canary sweep on both endpoints.
- `apps/api/tests/test_quality_intelligence_integrations.py`
  — 10 tests covering Phase 76 summary embedding + reflection,
  Phase 77 packet embedding + reflection, Phase 81 queue
  surfaces + never-Tier-1 + does-not-fire-on-empty + drops on
  full completion, Phase 82 incomplete → documented
  transition.

Web:

- `apps/web/src/test/QualityIntelligencePanel.test.tsx` — 12
  tests covering render, counts, empty, populated rendering,
  internal-demo caution banner, POST met / exception with
  code, submit error banner, refresh, API error banner,
  disclosure verbatim, forbidden-phrase canary sweep.

Phase 86 workspace tests updated to include
`quality_intelligence` in `_KNOWN_PANELS`.

## Smoke

- `npx tsc --noEmit` — clean.
- `npx vitest run` — 908/908 pass (up from 896).
- `pytest tests/test_quality_intelligence.py
  tests/test_quality_intelligence_integrations.py` — 34/34
  pass.
- Cross-phase backend regression (workspace_profiles +
  integrations, medications + integrations, disease_staging +
  integrations, provider_action_queue, note_validation,
  note_validation_acknowledgements, retina_visit_summary,
  retina_visit_packet, cataract_workflow, glaucoma_summary,
  anti_vegf_injections, fhir_export) — verified on this branch
  before commit.
- All five safety scanners pass.
- `git diff --check` clean.
- Phase63C functional smoke — **not run**; no local stack
  booted in this verification. Phase63C surfaces unchanged.

## Caveats

- **The three seeded demo specs are NOT verified for current
  CMS / IRIS / payer program use.** They are illustrative
  placeholders. The service layer unconditionally marks every
  internal-demo measure_id as `verified_for_submission=false`
  and the panel renders an orange caution banner so neither
  the operator nor the buyer can confuse these for real
  measure specs.
- Applicability is keyed off `encounter_type`; future phases
  can layer ICD-10 prefix matching on top of
  `applicable_icd10_prefixes`. That data is already persisted
  on the spec.
- `summary_for_encounter` re-runs the full applicability +
  field-presence projection. For a single-encounter request
  this is fine; an org-wide rollup
  (`encounters_with_incomplete_measures`) walks every encounter
  in the org and runs the per-encounter projection inline.
  This is bounded by org size and is acceptable for the demo
  posture; a real-program cycle would deserve a separate
  materialized rollup table.
- The Phase 89 analytics endpoint is a workflow signal, not a
  payer report. It does not compute scoring, does not estimate
  MIPS performance category, and does not claim submission
  readiness.

## Recommended next phase

The prompt suggested **Phase 90 — Ophthalmic Medication Safety
& Adherence Engine**, but that surface was already delivered
in Phase 85. Reasonable alternatives the operator may pick:

- **Phase 90 — Quality Submission Workbench** — a verified-
  spec-only export tooling that takes an operator's verified
  spec set (replacing the internal demo specs) plus a date
  range and produces a structured CSV / FHIR Bundle for an
  operator to hand-carry into the program-specific
  submission flow. Still no autonomous submission.
- **Phase 90 — Verified IRIS / MIPS spec library** — work
  with a qualified domain expert to encode the actual current
  AAO IRIS / CMS MIPS specs as repo-versioned spec rows
  (replacing the demo seed), with a CHANGELOG, citations, and
  per-row provenance.
- **Phase 90 — Imaging Metadata Review Linkage** — the
  previously-deferred Phase 88 clinical phase from PR #113.
- **Phase 90 — Vite 5 → 8 dependency hardening** — sequenced
  major bump (5→6→7→8) per the Phase 88 release-hardening
  notes.
