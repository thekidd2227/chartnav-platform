# Phase 25 — Signed-Note Artifact and Export Interoperability Groundwork

> The wedge: **make the export shape correct before we wire transport.**
> Not SMART-on-FHIR. Not a vendor write-back. A packaged,
> provenance-bearing document that a human or EHR can consume today
> in plain text, and that a future integrator can route as a FHIR
> `DocumentReference` the moment a transport seam exists.

## What the artifact is

A single **signed note** exports in three variants off one canonical
builder:

| Variant | MIME | When you reach for it |
|---|---|---|
| `chartnav.v1.json` | `application/vnd.chartnav.signed-note+json` | Downstream automation — audit queues, reviewer workflows, compliance tooling. Carries every tier of the pipeline separately (transcript → findings → generated draft → clinician-final) so reviewers can see what the AI produced vs. what the human committed to. |
| `chartnav.v1.text` | `text/plain; charset=utf-8` | A clinician pasting into a freeform EHR note field. Metadata header + body + audit footer. Human-readable on its own. |
| `fhir.DocumentReference.v1` | `application/fhir+json` | Any downstream integrator that speaks FHIR. Minimal R4 DocumentReference, LOINC `11506-3` "Progress note", clinician-final body base64-encoded as `content.attachment.data`, ChartNav URN identifier (`urn:chartnav:note:{id}:v{n}`). Externally-sourced encounters carry the original FHIR Encounter ref as the `context.encounter` identifier. |

## Trust tiers kept distinct

The canonical JSON has four explicit sections because conflating them
is where interop trust breaks:

- `transcript_source` — raw input (type, processing status,
  confidence, an excerpt up to 800 chars, truncation flag,
  total-chars count)
- `extracted_findings` — structured ophthalmology facts the
  generator saw (chief complaint, HPI, OD/OS VA + IOP, diagnoses,
  plan, structured JSON, extraction confidence)
- `note.generated_draft` — the generator's draft at creation time,
  **immutable** after persist
- `note.clinician_final` — the current `note_text`, the thing the
  clinician actually signed

`note.edit_applied` is true iff those last two differ. Legacy rows
that predate phase-25 backfill `generated_draft = note_text`, so
`edit_applied` is honestly false for them — we don't invent a diff
we never recorded.

## Integrity model

```
signature.content_hash_sha256
  = sha256( f"{version_number}|{note_format}|{clinician_final}" )
```

Emitted on every artifact, stable across repeated retrievals. Also
inlined as `content.attachment.hash` inside the FHIR variant so a
consumer only parsing the DocumentReference still has the
tamper-evidence fingerprint.

This is **not a cryptographic signature** — ChartNav does not hold a
signing key today. It is tamper evidence so downstream systems can
detect whether the note body was altered in transit. Add a real X.509
or JWS signing layer when we ship a signer identity.

## Access control

Same contract as every other note read:

- Unsigned notes → 409 `note_not_signed`. An artifact that claims a
  clinician attested when they didn't is worse than no artifact.
- Cross-org → 404 `note_not_found` (not 403 — same mask-the-existence
  rule as the rest of the API).
- Unknown format → 400 `unsupported_artifact_format`.
- Signed and exported notes both produce artifacts; the `POST /export`
  state transition is unchanged and orthogonal to retrieval.

## Audit

Every successful artifact issuance writes a
`note_version_artifact_issued` audit event whose `detail` string
records the canonical variant emitted
(`format=chartnav.v1.json`, `format=chartnav.v1.text`,
`format=fhir.DocumentReference.v1`). So the audit log can answer
"what shape of this note has left ChartNav?" without needing a
separate artifact table.

## Frontend

`apps/web/src/api.ts`:

- `NoteArtifact` — full typed envelope for the canonical JSON.
- `getNoteArtifact(email, id)` — typed JSON retrieval.
- `fetchNoteArtifactRaw(email, id, format)` — raw retrieval; returns
  parsed body + content-type + variant header.
- `downloadNoteArtifact(email, id, format)` — builds a Blob and
  triggers a browser anchor click. Filename pattern:
  `chartnav-note-{id}.{format}.{ext}` (ext = `.txt` for text, `.json`
  for json + fhir). Stable per note-id + format so re-exports land on
  the same name.

`NoteWorkspace.tsx` renders `[Download JSON] [Download TEXT] [Download FHIR]`
next to the existing Copy / Export buttons once the note is signed.
Each button has a `title` tooltip explaining when to pick that format.

## What this phase did NOT do

- No vendor write-back, no FHIR transaction bundle, no SMART-on-FHIR
  launch. The FHIR variant is the **packaging shape**, not a
  transport.
- No change to the existing `POST /note-versions/{id}/export` state
  transition. Artifact retrieval is orthogonal.
- No new feature flags. Artifact endpoint is always on for signed
  notes.
- No public marketing site work. Separate lane.

## Test coverage

- Backend (`apps/api/tests/test_note_artifact.py`) — 9 scenarios.
- Frontend (`apps/web/src/test/NoteWorkspace.test.tsx`) — 3 scenarios.
- Full suites green: backend **240 passed**; frontend **61 passed**.

## Files touched

- `apps/api/alembic/versions/e1f2a3041501_note_generated_text_snapshot.py`
- `apps/api/app/services/note_orchestrator.py`
- `apps/api/app/services/note_artifact.py` (new)
- `apps/api/app/api/routes.py`
- `apps/api/tests/test_note_artifact.py` (new)
- `apps/web/src/api.ts`
- `apps/web/src/NoteWorkspace.tsx`
- `apps/web/src/test/NoteWorkspace.test.tsx`
- `docs/build/05-build-log.md`
- `docs/build/16-frontend-test-strategy.md`

## Follow-on work (not in this phase)

1. **Real signing key** — once ChartNav holds an organization-scoped
   private key, upgrade `content_hash_sha256` to a JWS in the
   `signature` block. Consumers that verify today by hash will
   continue to; consumers that want cryptographic attestation will
   have it.
2. **FHIR Bundle transport** — wrap the existing DocumentReference in
   a `Bundle` of type `transaction` + POST it via the FHIR adapter.
   Adapter write gating already exists (phase 20 / 21); this phase's
   packaging shape is what slots into the bundle entry.
3. **Playwright** — one e2e scenario: sign a note, click **Download
   FHIR**, assert a download event + file contents round-trip
   through the browser's blob handling. Deferred because the unit
   + vitest coverage already covers the contract and the e2e
   download plumbing needs a file-handler harness change.
4. **Bulk export** — the audit CSV export pattern (phase 14) is a
   good template for a future `/note-versions/export` endpoint that
   streams N artifacts as a zip.
