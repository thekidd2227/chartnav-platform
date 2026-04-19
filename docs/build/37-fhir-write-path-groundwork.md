# Phase 26 — FHIR Write-Path Groundwork

> Groundwork, not a vendor delivery. The seam is honest: adapters that
> can transmit do, adapters that cannot refuse cleanly, and every
> attempt — success or failure — is persisted into an append-only log
> with provenance intact.

## What was built

1. **Adapter protocol extended.** `ClinicalSystemAdapter` grows a
   typed write seam: `transmit_artifact(artifact, document_reference,
   note_version_id, encounter_external_ref) -> TransmitResult`. The
   existing free-text `write_note(body=...)` is left in place but not
   extended — signed notes now travel as a fully-packaged FHIR
   DocumentReference (from phase 25's `render_fhir_document_reference`),
   never as a bare string. New capability flag:
   `AdapterInfo.supports_document_transmit`.

2. **Three adapters, three honest answers.**
   | Adapter | `supports_document_transmit` | transmit_artifact behaviour |
   |---|---|---|
   | `native` | `False` always | Raises `AdapterNotSupported` — ChartNav is already the system of record in standalone mode; transmission to an external system that doesn't exist is meaningless. |
   | `stub` | mirrors `writes_allowed` | In writethrough: appends a record to `recorded_writes`, returns `TransmitResult(status="succeeded", remote_id="stub-docref-N")`. In readthrough: raises `AdapterNotSupported`. |
   | `fhir` | `True` | POSTs the DocumentReference JSON to `{base_url}/DocumentReference` with `Content-Type: application/fhir+json`, Bearer auth when configured, and two custom provenance headers (`X-ChartNav-Note-Version-Id`, `X-ChartNav-Artifact-Hash`). Parses HTTP 2xx as success + pulls `remote_id` from the `Location:` header or a returned resource `.id`. 4xx/5xx come back as `TransmitResult(status="failed", response_code=..., error_code="fhir_transmit_http_error")` — not exceptions. Transport-level errors (DNS, timeout) still raise `AdapterError`. |

3. **New table `note_transmissions`.** Append-only log of every
   dispatch attempt. One note-version can have N rows (retries,
   force-resends). Columns:
   `note_version_id`, `encounter_id`, `organization_id` (denormalized
   for scoping), `adapter_key`, `target_system`, `transport_status`
   (`queued`|`dispatching`|`succeeded`|`failed`|`unsupported`),
   `request_body_hash` (sha256 of the canonicalized DocumentReference
   JSON), `response_code`, `response_snippet` (≤1024 chars),
   `remote_id`, `last_error_code`, `last_error`, `attempt_number`
   (monotonic per note-version), `attempted_at`, `completed_at`,
   `created_by_user_id`. Unique `(note_version_id, attempt_number)`.

4. **Service `app.services.note_transmit.py`.** End-to-end orchestration.
   Gates (mode → role → artifact → adapter → idempotency),
   persists a `dispatching` row **before** calling the adapter so a
   crash mid-call still leaves a trace, calls
   `adapter.transmit_artifact`, updates the row with the result.
   Every branch persists a row; a remote failure is a normal business
   outcome that the UI renders from the same shape.

5. **HTTP surface.**
   - `POST /note-versions/{id}/transmit` — body `{force?: bool}`.
     Returns the final persisted row. Gating errors → 4xx with the
     standard `{error_code, reason}` envelope.
   - `GET /note-versions/{id}/transmissions` — newest-first list of
     attempts. Cross-org masked via the shared note-load helper
     (cross-org note → 404 `note_not_found`; therefore the
     transmission list is also 404 for non-owners).

6. **Audit event.** Every transmit attempt writes
   `note_version_transmitted` with a detail string carrying
   `note_id`, `transmission_id`, `adapter`, `status`, `attempt`.

7. **Frontend.** `NoteWorkspace` renders a **Transmit to EHR**
   button (becomes **Re-transmit** after a successful attempt) only
   when `GET /platform.adapter.supports.document_transmit === true`.
   A transmission-history pane shows attempts with status chips,
   HTTP code, remote id, and error code if any. `api.ts` gains
   `NoteTransmission` type, `transmitNoteVersion`,
   `listNoteTransmissions`.

## Gating matrix (what refuses + why)

| Condition | HTTP | error_code |
|---|---|---|
| caller role != admin/clinician | 403 | `role_cannot_transmit` |
| `platform_mode != "integrated_writethrough"` | 409 | `transmit_not_available_in_mode` |
| adapter cannot be resolved | 500 | `adapter_resolve_failed` |
| adapter `supports_document_transmit=False` | 409 | `adapter_does_not_support_transmit` |
| note not signed (forwarded from artifact gate) | 409 | `note_not_signed` |
| cross-org | 404 | `note_not_found` |
| prior succeeded transmission exists and `force!=true` | 409 | `already_transmitted` |
| remote HTTP 4xx/5xx | 200 | persisted row with `transport_status="failed"` |
| remote transport error (DNS/timeout) | 200 | persisted row with `transport_status="failed"`, error_code populated |

Key property: the caller's HTTP response never lies about what
happened remotely. A 200 on the endpoint means "ChartNav attempted and
persisted an outcome"; the outcome itself lives in the response body.

## What this phase did NOT do

- **No vendor-specific adapters.** Epic/Cerner/Athena/Nextech specifics
  (auth dance, Encounter linkage rules, status vocab) are out of scope.
  The generic FHIR adapter targets standards-compliant R4 servers
  (HAPI, Aidbox, Medplum, test servers). Vendor adapters should
  `register_vendor_adapter("epic", lambda: EpicAdapter())` and
  override `transmit_artifact` with their own transport.
- **No SMART-on-FHIR OAuth dance.** Generic FHIR adapter uses
  `CHARTNAV_FHIR_AUTH_TYPE=bearer` + `CHARTNAV_FHIR_BEARER_TOKEN`
  only. SMART launch context, scopes, PKCE — vendor-specific.
- **No background worker for retries.** Today's transmit runs in the
  request path. The `note_transmissions` shape is ready for a worker
  (rows start as `dispatching` before the call returns; a worker
  could pick up pending rows, the `attempted_at` / `completed_at`
  pair is already there). Not built because there is no failure-mode
  today that benefits — manual retry via `force=true` covers it.
- **No bulk transmit.** One note per call. Bulk export pattern from
  audit CSV is the template when needed.
- **No Bundle.transaction envelope.** The DocumentReference goes as
  a single resource POST, not wrapped in a FHIR Bundle. HAPI + Aidbox
  accept both; vendor-specific adapters that require Bundle wrap it
  themselves.

## Trust tiers kept visible through the write path

The phase-25 four-tier separation (transcript → findings → generated
draft → clinician final) stays intact all the way to the wire:

- `request_body_hash` matches
  `phase-25 signature.content_hash_sha256` across the FHIR
  DocumentReference's `content.attachment.hash`. A downstream system
  receiving the DocumentReference can verify against the ChartNav
  audit log (same hash, same note).
- `artifact_hash` travels as a custom header
  `X-ChartNav-Artifact-Hash` so a FHIR server that strips the
  resource-level `content.attachment.hash` (some do) still gets the
  correlation.
- The adapter never sees ChartNav's `clinician_final` as a bare
  string — only as the `content.attachment.data` payload inside
  the DocumentReference. The transmit log records the hash, not
  the plaintext.

## Test coverage

- Backend (`apps/api/tests/test_note_transmit.py`) — **11 scenarios**:
  standalone refuses, readthrough stub refuses, writethrough stub
  succeeds + persists row + emits audit, writethrough FHIR via
  injected transport succeeds, FHIR 400 persists failed row, unsigned
  refused, cross-org 404, reviewer role 403, double without force →
  409 already_transmitted, double with force → new attempt row
  (attempt_number increments), GET cross-org masked.
- Frontend (`src/test/NoteWorkspace.test.tsx`) — **+3 scenarios**:
  Transmit hidden when `document_transmit=false`, visible when true,
  click dispatches `transmitNoteVersion` + refreshes history pane.
- Full backend suite: **251 passed**. Frontend suite: **64 passed**.
  Typecheck + Vite build clean.

## Files touched

- `apps/api/alembic/versions/e1f2a3041502_note_transmissions_table.py` (new)
- `apps/api/app/integrations/base.py` — `TransmitResult`,
  `supports_document_transmit`, `transmit_artifact` protocol method
- `apps/api/app/integrations/fhir.py` — write-transport, transmit_artifact
- `apps/api/app/integrations/stub.py` — transmit_artifact
- `apps/api/app/integrations/native.py` — transmit_artifact (raises)
- `apps/api/app/services/note_transmit.py` (new) — orchestrator
- `apps/api/app/api/routes.py` — two new routes, `/platform` response
  grows `document_transmit`
- `apps/api/tests/test_note_transmit.py` (new)
- `apps/web/src/api.ts` — `NoteTransmission`, `transmitNoteVersion`,
  `listNoteTransmissions`, `document_transmit` flag on `PlatformInfo`
- `apps/web/src/NoteWorkspace.tsx` — Transmit button + history pane
- `apps/web/src/test/NoteWorkspace.test.tsx` — 3 new tests
- `docs/build/05-build-log.md`, `16-frontend-test-strategy.md`,
  `37-fhir-write-path-groundwork.md` (new)

## Follow-on work

1. **Background worker.** `dispatching` rows + `attempted_at` /
   `completed_at` already support a `stale-claim recovery` pattern;
   add a worker that retries `failed` rows within a policy window.
2. **Bundle.transaction envelope.** Wrap DocumentReference in a
   transaction bundle for vendors that require it. One extra helper
   in `note_artifact.py` + a thin vendor adapter.
3. **Vendor adapters.** Epic → `EpicAdapter(base_url, client_id, ...)`
   that overrides `transmit_artifact` with SMART-backend auth +
   `ServiceRequest` linkage. Register under `epic` in
   `app/integrations/__init__.py`.
4. **JWS signing.** Phase 25 flagged this; it becomes more valuable
   once transmission is happening — vendor systems can verify the
   signed hash cryptographically rather than just by inspection.
5. **Playwright e2e.** One happy-path scenario through the UI: sign
   → click Transmit → assert a `succeeded` chip + remote id render
   in the history pane. Needs the writethrough stub adapter to be
   active in the e2e backend.
