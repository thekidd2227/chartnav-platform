# Adapter-Driven Encounters & Integrated Write Gating (phase 20)

The `/encounters` and `/encounters/{id}` HTTP handlers now dispatch
through the adapter boundary in integrated modes. Standalone behavior
is unchanged — it still routes through the native adapter which wraps
the same SQL path the old direct-DB code used.

This phase also nails down the encounter source-of-truth story end-to-end:

- every encounter row carries a `_source` tag so the frontend can
  render a source-of-truth chip consistently;
- every mutation path returns a clean, stable error code when it is
  unsupported in the current mode, rather than silently falling back
  to the native DB.

## 1. Source-of-truth rules

| Concern | `standalone` | `integrated_readthrough` | `integrated_writethrough` |
|--------|--------------|---------------------------|----------------------------|
| `GET /encounters` | native DB via native adapter (`_source=chartnav`) | adapter dispatch (`_source=stub`/`fhir`/vendor) | adapter dispatch |
| `GET /encounters/{id}` | native adapter (`_source=chartnav`) | adapter dispatch | adapter dispatch |
| `POST /encounters` | allowed | **409 `encounter_write_unsupported`** | **409 `encounter_write_unsupported`** (push-back not implemented) |
| `POST /encounters/{id}/status` | allowed (native state machine) | **409 `encounter_write_unsupported`** | adapter dispatch; `AdapterNotSupported` → **501 `adapter_write_not_supported`** |
| `POST /encounters/{id}/events` | allowed | allowed (ChartNav-native workflow tracking) | allowed |
| `POST /encounters/{id}/inputs` | allowed | allowed | allowed |
| `POST /encounters/{id}/notes/generate` | allowed | allowed (note drafting is ChartNav-native regardless of encounter source) | allowed |

Rule: **anything on `encounters` the external EHR owns** is gated.
**ChartNav-native workflow objects** (`workflow_events`, `encounter_inputs`,
`extracted_findings`, `note_versions`, audit events) stay writable in
every mode, because they exist in ChartNav's own tables and represent
work performed through the ChartNav surface, not modifications to the
external record.

## 2. Adapter contract additions

```python
class EncounterListResult:
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int

class ClinicalSystemAdapter(Protocol):
    def list_encounters(
        self, *, organization_id: int, location_id: int | None = None,
        status: str | None = None, provider_name: str | None = None,
        limit: int = 50, offset: int = 0,
    ) -> EncounterListResult: ...
    def fetch_encounter(self, encounter_id: str) -> dict[str, Any]: ...
```

Every returned encounter row is in ChartNav's internal shape
(`id`, `organization_id`, `location_id`, `patient_identifier`,
`patient_name`, `provider_name`, `status`, `patient_id`,
`provider_id`, `scheduled_at`, `started_at`, `completed_at`,
`created_at`) plus adapter-provided metadata:

- `_source`: `"chartnav"` for native, the vendor key for integrated
  (`"fhir"`, `"stub"`, future `"epic"` etc.).
- `_external_ref`: vendor id (FHIR `Encounter.id`, etc.) when
  applicable.
- `_fhir_status`: raw FHIR status when the adapter normalized the
  ChartNav `status`.

## 3. Adapter implementations

### Native
Uses the existing `encounters` SQL path. `list_encounters` emits
`X-Total-Count`-shaped paging; `fetch_encounter` serves the full
column set plus `_source: "chartnav"`.

### Stub
Returns two deterministic canned external rows (`EXT-1001`,
`EXT-1002`). Filters `status` and `provider_name` locally so
integrated_readthrough can be exercised end-to-end without a real
FHIR server.

### FHIR
`list_encounters` → `GET /Encounter?_count=<limit>&_offset=<offset>
[&status=<mapped>]`. ChartNav statuses are translated back to the
FHIR vocabulary (`scheduled→planned`, `in_progress→in-progress`,
`completed→finished`). `provider_name` is applied as a post-filter
because FHIR doesn't have a universal search parameter for it.

`fetch_encounter` normalizes:
- status mapping + raw `_fhir_status` passthrough;
- `participant[0].individual.display` → `provider_name`;
- `subject.reference` → `patient_identifier`;
- `period.start` → `scheduled_at`/`started_at`;
- `period.end` → `completed_at`.

## 4. HTTP handler changes

### `GET /encounters`
Now calls `resolve_adapter().list_encounters(...)`. Standalone gets
native rows; integrated gets adapter rows. `X-Total-Count`/`X-Limit`/
`X-Offset` headers identical to before.

### `GET /encounters/{id}`
Path param type widened from `int` to `str` so FHIR vendor ids
(non-numeric strings) pass through. Standalone path unchanged. In
integrated modes, the HTTP handler:
- resolves the adapter;
- calls `fetch_encounter(id)`;
- stamps `organization_id` from the caller when the adapter returns
  `None` (FHIR servers are not ChartNav-org-aware; one ChartNav org
  per deployment is the documented convention);
- translates `AdapterError("encounter_not_found", ...)` → 404;
- translates any other `AdapterError` → 502 so the operator sees the
  transport failure cleanly.

### `POST /encounters`
Gated via `_assert_encounter_write_allowed()` — refuses in BOTH
integrated modes with 409 `encounter_write_unsupported`.

### `POST /encounters/{id}/status`
Mode-split:
- `integrated_readthrough` → 409 `encounter_write_unsupported`.
- `integrated_writethrough` → adapter dispatch;
  `AdapterNotSupported` bubbles as **501 `adapter_write_not_supported`**
  so the operator can tell vendor non-support from generic mutation
  refusal.
- standalone → native state machine (unchanged).

## 5. Frontend — mode-aware encounter UX

- `Encounter` type widens `id` to `number | string` and adds optional
  `_source`, `_external_ref`, `_fhir_status`. Existing helpers
  `encounterIsNative(enc)` and `encounterSourceLabel(enc)` surface the
  tag to components.
- Encounter detail header renders a **source chip** (`ChartNav
  (native)` vs `External (FHIR)` vs `External (stub)` vs vendor key).
  Teal soft background on native, blue info background on external.
- When the encounter is external:
  - A yellow-no-red **SoT banner** explains that the EHR owns the
    row. Status transitions are not rendered. `NoteWorkspace` is
    replaced with an honest subtle-note explaining note drafting is
    ChartNav-native today.
  - Add-event composer remains (events are ChartNav-native).
- `getEncounter`, `getEncounterEvents`, `updateEncounterStatus`,
  `createEncounterEvent` accept `number | string` so FHIR vendor ids
  work end-to-end.

## 6. Error codes & status semantics

| Code | HTTP | When |
|------|------|------|
| `encounter_write_unsupported` | 409 | `POST /encounters`, `POST /encounters/{id}/status` in integrated_readthrough; `POST /encounters` in integrated_writethrough |
| `adapter_write_not_supported` | 501 | `POST /encounters/{id}/status` in integrated_writethrough when the adapter raises `AdapterNotSupported` (e.g. generic FHIR) |
| `encounter_not_found` | 404 | cross-org read OR adapter-reported not-found |
| (adapter `error_code`) | 502 | any other `AdapterError` from list/fetch |

501 is the right status for "the adapter understood you but refuses
to perform the action" — a transport difference from 409 "mode
blocks this entirely."

## 7. Verification matrix

| Command | Result |
|---------|--------|
| `make verify` (SQLite) | ✅ **185/185 pytest + 9/9 smoke** |
| New `test_integrated_encounters.py` | ✅ 11/11 |
| `npm run typecheck` | ✅ clean |
| `npm test` | ✅ **44/44 Vitest** (+2 source-of-truth UI) |
| `npm run build` | ✅ 208 KB JS / 18.1 KB CSS |
| `npx playwright test workflow + a11y` | ✅ 17/17 |
| `npx playwright test visual --update-snapshots` | ✅ 4/4 (baselines refreshed) |

Honest limitations:
- FHIR `list_encounters` is tested with fixture transport (no live
  network in CI). The HTTP path on a real FHIR server is exercisable
  locally by setting `CHARTNAV_FHIR_BASE_URL` to e.g. `https://hapi.fhir.org/baseR4`.
- FHIR status writes remain **unsupported by design** — vendor
  adapters layer the real push.

## 8. What this phase does NOT do

- Does not ship a FHIR writer. Generic `FHIRAdapter.update_encounter_status`
  still raises `AdapterNotSupported`; that's honest.
- Does not add SMART-on-FHIR auth — that's a vendor-specific concern.
- Does not reconcile integrated encounter rows into the native
  `encounters` table. `external_ref` is available on `patients`/
  `providers`; encounter-level mirroring is future work.
- Does not change standalone behavior for existing encounter routes.

## Addendum — hardening wave (2026-04-20)

- **External banner machine-readable disabled reason**: the shipped
  `external-encounter-banner` now carries three stable data
  attributes — `data-source`, `data-external-ref`, and
  `data-disabled-reason="encounter_owned_by_external_ehr"`. This
  lets observability + e2e tests assert on the canonical reason
  string instead of scraping visible copy. Adapter contract and
  bridge semantics are unchanged.
- **Source-chip label contract** (for tests + telemetry):
  - `_source=chartnav` or undefined → "ChartNav (native)"
  - `_source=fhir` → "External (FHIR)"
  - `_source=stub` → "External (stub)"
  - any other string → "External (<string>)"
- Coverage added in `apps/web/src/test/wedge-hardening.test.tsx`
  (`encounterSourceLabel + encounterIsNative` describe block).
