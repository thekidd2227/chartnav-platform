# Native Clinical Layer & FHIR Adapter (phase 18)

This phase makes ChartNav's dual-mode architecture *real* for the
first time. Standalone mode now owns patients and providers natively.
Integrated modes can target a generic FHIR R4 server via the first
shipped vendor adapter.

## 1. Native clinical ownership (standalone)

Two new org-scoped tables persist the first-class clinical objects
ChartNav now owns in `standalone` mode:

- `patients` — local MRN (`patient_identifier`), name, DOB,
  `sex_at_birth` (free-form), `external_ref` for integration mirroring,
  `is_active` soft-delete.
- `providers` — `display_name`, 10-digit `npi` (API-layer validated,
  DB-unique per org when set), `specialty`, `external_ref`, `is_active`.

Both are unique per org on their natural key. Migration
`f6a7b8c9d0e1` lands the tables plus two nullable FKs on
`encounters`: `patient_id` and `provider_id`. Legacy text fields
(`patient_identifier`, `patient_name`, `provider_name`) remain for
display continuity and legacy integrations — the **preferred source
of truth** in standalone mode is the FK linkage.

Seed populates real patient + provider rows per tenant and backfills
encounter FKs on re-seed without duplicating rows.

## 2. HTTP surface

| Method | Path          | Notes |
|--------|---------------|-------|
| GET    | `/patients`   | `limit`/`offset`/`q`/`include_inactive`; `X-Total-Count` headers |
| POST   | `/patients`   | admin + clinician; mode-gated; dup → 409 `patient_identifier_conflict` |
| GET    | `/providers`  | same pagination surface |
| POST   | `/providers`  | admin only; NPI validated; dup NPI → 409 `npi_conflict` |

`integrated_readthrough` returns 409
`native_write_disabled_in_integrated_mode` on both POST endpoints so
the UI can render a clear banner instead of silently succeeding.

`GET /encounters` responses now include `patient_id` + `provider_id`.

## 3. FHIR R4 adapter — first real external boundary

`app/integrations/fhir.py::FHIRAdapter` implements the
`ClinicalSystemAdapter` protocol against a generic FHIR R4 server.
Vendor-agnostic by design — any FHIR R4 endpoint (HAPI, Aidbox, Epic,
Cerner, Athena, Nextech, …) works with the same adapter.

### Capabilities

| Operation                 | FHIR adapter |
|---------------------------|--------------|
| `fetch_patient(id)`       | ✅ `GET /Patient/<id>` |
| `search_patients(query)`  | ✅ `GET /Patient?name=…&_count=…` |
| `fetch_encounter(id)`     | ✅ `GET /Encounter/<id>` |
| `update_encounter_status` | ❌ `AdapterNotSupported` — vendor-specific |
| `write_note`              | ❌ `AdapterNotSupported` — DocumentReference + Binary work |
| `sync_reference_data`     | returns zeros (vendor-specific) |

### Normalization rules

- **Patient**
  - `external_ref` ← `Patient.id`
  - `patient_identifier` ← first `identifier.value` where
    `type.coding.code == "MR"` or `type.text == "MRN"`; falls back to
    first identifier.
  - `first_name` ← `given[]` joined from `name[use=official|usual]`
  - `last_name` ← `family`
  - `date_of_birth` ← `birthDate`
  - `sex_at_birth` ← `gender`
- **Encounter**
  - `status` ← best-effort ChartNav mapping:
    `planned→scheduled`, `arrived|triaged|in-progress|onleave→in_progress`,
    `finished|cancelled→completed`. `fhir_status` carries the raw.
  - `patient_id` ← `subject.reference` when it starts with `Patient/`.
  - `provider_name` ← first participant `individual.display`.

### Transport & config

- `CHARTNAV_FHIR_BASE_URL` (required when adapter is `fhir`).
- `CHARTNAV_FHIR_AUTH_TYPE` ∈ {`none`, `bearer`} — default `none`.
- `CHARTNAV_FHIR_BEARER_TOKEN` — required when auth type is `bearer`.
- Pluggable `transport` on the adapter class — tests inject a
  fixture transport; default uses `urllib.request` (no new runtime
  deps). All errors funnel through `AdapterError` with a specific
  `error_code`.

### Resolution

`CHARTNAV_PLATFORM_MODE=integrated_readthrough` +
`CHARTNAV_INTEGRATION_ADAPTER=fhir` resolves to the FHIR adapter at
boot. Misconfig (missing base URL, bearer auth without a token,
invalid auth type) raises at resolution time with a clear code
(`fhir_not_configured`, `fhir_missing_bearer`, `fhir_invalid_auth_type`).

## 4. Source-of-truth matrix

| Object         | `standalone` (native) | `integrated_readthrough` (stub / FHIR) | `integrated_writethrough` (stub / FHIR) |
|----------------|-----------------------|-----------------------------------------|------------------------------------------|
| patient        | ChartNav              | external (mirrored via `external_ref`)  | external                                 |
| provider       | ChartNav              | external                                | external                                 |
| encounter      | ChartNav              | external                                | external                                 |
| workflow_event | ChartNav              | ChartNav                                | ChartNav                                 |
| document       | ChartNav (as workflow_events) | external (read-only via FHIR) | vendor-specific write path               |

The admin panel renders this matrix as the platform banner for every
operator — no mode is ever implicit.

## 5. Frontend

Admin panel gains two tabs:

- **Patients** — list, search, create. In `integrated_readthrough`
  mode the create form is hidden and a banner labels patients as
  read-through from the external EHR.
- **Providers** — list, search, create (admin-only). Same mode-aware
  banner + form gating.

## 6. Tests

Backend:
- `tests/test_clinical.py` (13) — migration + seed linkage, CRUD,
  RBAC, NPI format + dup conflicts, cross-org isolation,
  readthrough-blocks-writes.
- `tests/test_fhir_adapter.py` (11) — config validation, fixture
  transport Patient/Encounter normalization, bearer auth threads
  through, write paths raise `AdapterNotSupported`, resolve_adapter
  picks the FHIR adapter under `integrated_readthrough`.

Frontend:
- 3 `AdminPanel.test.tsx` tests — Patients create form,
  readthrough-hides-form + banner, Providers create.

Verification matrix (commands, all green locally):
- `make verify` → 155 pytest + 9 smoke
- `make web-verify` → 34 vitest + typecheck + build
- `npx playwright test workflow.spec.ts a11y.spec.ts` → 17/17
- `npx playwright test visual.spec.ts` → 4/4 (baselines refreshed)

## 7. What this phase does NOT do

- **Does not** ship a vendor-specific adapter (Epic, Cerner, …).
  Each vendor's SMART-on-FHIR auth, status vocabulary, and write
  semantics are their own adapter class layered on top of (or
  beside) `FHIRAdapter`.
- **Does not** implement FHIR `DocumentReference` writes.
  `write_note` is intentionally `AdapterNotSupported` on the
  generic FHIR adapter.
- **Does not** add a patient chart UI, scheduling, billing, or
  dictation — those are separate product surfaces.
- **Does not** reconcile existing `encounters.provider_name` strings
  against the new `providers` table automatically. Operators can
  backfill by creating providers with matching `display_name` and
  re-running the seed, or by issuing targeted UPDATE statements.
