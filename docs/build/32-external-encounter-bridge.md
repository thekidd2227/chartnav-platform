# External Encounter → Native Workflow Bridge (phase 21)

The ChartNav wedge (transcript → findings → note draft → provider
signoff) now works on externally-sourced encounters. The bridge is
minimal, honest, and idempotent: given an external encounter's
identifier, ChartNav creates (or resolves) a native `encounters` row
that mirrors the shell fields and carries the vendor reference. All
downstream workflow endpoints attach to that native row.

The external EHR continues to own the encounter. ChartNav owns the
workflow overlay.

## 1. Source-of-truth boundary

| Concern | External EHR | ChartNav (bridged native row) |
|---|---|---|
| Encounter id (authoritative) | ✅ (via `external_ref`) | mirrored on native row |
| Encounter status | ✅ | mirrored; ChartNav keeps its own workflow state via `workflow_events` + note draft status |
| Patient / provider display | ✅ | mirrored on bridge create |
| Transcript inputs | — | ✅ |
| Extracted findings | — | ✅ |
| Note versions + signoff | — | ✅ |
| Export/handoff state | — | ✅ |
| `POST /encounters` | ❌ refused (phase 20) | allowed in standalone only |
| `POST /encounters/{id}/status` | ❌ refused in readthrough; adapter-dispatched in writethrough (phase 20) | unchanged after bridge — external still owns |
| `POST /encounters/{id}/events` | — | ✅ (ChartNav-native workflow tracking, every mode) |

The bridge unlocks **ChartNav-native workflow**. It does NOT reopen
encounter-state writes: `POST /encounters/{id}/status` on a bridged
row in integrated_readthrough still returns 409
`encounter_write_unsupported`. That contract is test-asserted.

## 2. Schema change (migration `b8c9d0e1f203`)

Two nullable columns added to `encounters` via batch rewrite:

| column | type | notes |
|---|---|---|
| `external_ref` | `VARCHAR(128)` nullable, indexed | vendor encounter id (FHIR `Encounter.id`, Epic contact id, …) |
| `external_source` | `VARCHAR(64)` nullable | adapter key (`fhir`, `stub`, vendor) |

New unique constraint:
`UNIQUE(organization_id, external_ref, external_source)` — the
database-level guarantee that makes the bridge idempotent and
org-scoped.

Standalone encounters keep both columns NULL. Backward compatible.

## 3. Service seam

`apps/api/app/services/bridge.py::resolve_or_create_bridged_encounter(...)`
is the single entry point. Signature:

```python
def resolve_or_create_bridged_encounter(
    *,
    organization_id: int,
    external_ref: str,
    external_source: str,
    patient_identifier: str | None = None,
    patient_name: str | None = None,
    provider_name: str | None = None,
    status: str | None = None,
    location_id: int | None = None,
) -> dict[str, Any]
```

Behavior:
- Idempotent on `(organization_id, external_ref, external_source)`.
- First creation returns the new row with `_bridged: True`; subsequent
  resolves return the existing row with `_bridged: False`.
- Location: if not supplied, the caller's first active location in
  the org is used. Rationale: `encounters.location_id` is `NOT NULL`
  today, and most external systems don't map cleanly to ChartNav
  location ids out of the gate. Operators can re-assign later.
- Status defaults to `scheduled` when not supplied (so the native
  state machine has a valid starting point ChartNav can drive from
  its own workflow events and note drafting without touching the
  external encounter).

## 4. HTTP surface

### `POST /encounters/bridge`

Idempotent get-or-create. Body:

```json
{
  "external_ref": "ENC-XYZ",
  "external_source": "fhir",
  "patient_identifier": "EXT-1001",
  "patient_name": "Morgan External",
  "provider_name": "Dr. External",
  "status": "in_progress"
}
```

Returns the full native row plus `_bridged: true|false`,
`_source: "chartnav"`, and the `_external_ref`/`_external_source`
mirror tags.

Rules:
- `admin` + `clinician` can bridge; reviewer → 403 `role_forbidden`.
- Standalone mode → 409 `bridge_not_available_in_standalone_mode`
  (there is nothing external to bridge from).
- Both integrated modes are supported.
- Emits a `security_audit_events` row of type `encounter_bridged` on
  first create (no audit event on idempotent re-resolve — intentional).

## 5. Frontend

External encounter detail now renders a **Bridge to ChartNav** action
inside the SoT banner. On click:

1. The frontend calls `POST /encounters/bridge` with the external
   encounter's `external_ref` (from `_external_ref`),
   `external_source` (from `_source`), and the mirror fields it
   already has (patient display, provider display, status).
2. Navigation flips the `?encounter=<native_id>` query param and
   reloads, so the detail pane remounts against the native row.
3. Because the row is now `_source: "chartnav"`, the existing
   detail view automatically shows the full `NoteWorkspace`
   (transcript ingest → findings → draft → sign → export).

Reviewer role sees the external banner but no Bridge button; a
`bridge-disabled-note` subtle-note explains.

## 6. Tests

Backend (`tests/test_encounter_bridge.py`, +11):
- bridge creates native row + carries `external_ref` +
  `external_source` + `_bridged: True`.
- second call with same external ref returns the same `id` with
  `_bridged: False`.
- standalone mode refuses (409 `bridge_not_available_in_standalone_mode`).
- reviewer → 403, admin + clinician allowed.
- writethrough mode allowed.
- invalid status → 400 `invalid_status`.
- **full wedge** runs on bridged row: transcript ingest → generate
  → sign → export → workflow event.
- integrated_readthrough still refuses encounter status writes on the
  bridged row (phase 20 contract preserved).
- org scoping: same `external_ref` in two orgs → two native rows.
- standalone regression: existing encounters keep
  `external_ref=NULL` and `_source="chartnav"`.

Frontend (`src/test/App.test.tsx`, +1 new + 1 updated):
- external encounter shows the `Bridge to ChartNav` button enabled
  for admin/clinician; the subtle-note copy now talks about
  bridging instead of generic native-only.
- clicking the button dispatches `bridgeEncounter` with the external
  ref + source + mirror fields.

Verification:
- `make verify` → **196/196 pytest + 9/9 smoke**.
- `npm run typecheck` clean · `npm test` → **45/45 Vitest**.
- `npm run build` → 209 KB JS / 18.1 KB CSS.
- `npx playwright test workflow.spec.ts a11y.spec.ts` → **17/17**.
- `npx playwright test visual.spec.ts --update-snapshots` → 4/4
  (baselines refreshed).

## 7. What this phase does NOT do

- Does NOT write back to the external EHR. ChartNav never tries to
  push a new encounter into the source system.
- Does NOT sync external status changes onto the bridged row in the
  background. The bridge mirrors the shell at bridge-time; re-fetch
  would need a dedicated sync worker (future phase).
- Does NOT implement `external_ref` for `workflow_events`,
  `encounter_inputs`, `extracted_findings`, or `note_versions`.
  Those stay native-only — their external counterparts live on the
  external side or don't exist at all (notes).
- Does NOT attempt to reconcile multiple external sources pointing at
  the same logical encounter (`external_source` is part of the key;
  two vendor mirrors of one encounter get two native rows by design).
