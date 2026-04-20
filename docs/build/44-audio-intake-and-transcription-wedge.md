# Phase 33 — Audio Intake + Transcription Wedge

> The first real speech-to-chart path through ChartNav: doctor
> uploads an audio file → `encounter_inputs` row lands with full
> metadata → ingestion pipeline runs → deterministic **stub**
> transcript text lands in `transcript_text` → clinician reviews +
> edits before note generation. No fake live vendor integration,
> no ambient listening, no browser mic. File-upload-first, honest
> about where the seam for a real STT vendor plugs in.

## Surface area

| Verb | Path | Purpose |
|---|---|---|
| `POST` | `/encounters/{id}/inputs/audio` | Multipart `audio` upload. Writes to disk, creates an `encounter_inputs` row, runs the ingestion pipeline inline. |
| `PATCH` | `/encounter-inputs/{id}/transcript` | Clinician review/edit of a completed input's transcript before draft generation. |

Both routes:
- Admin + clinician only (reviewer → 403 via
  `require_create_event`).
- Cross-org → 404 via the shared encounter / input load helpers.
- Audit-logged with dedicated event types
  (`encounter_input_audio_uploaded`,
  `encounter_input_transcript_edited`). PHI minimising: the
  transcript body is never duplicated into the audit detail.

## Data flow

```
[doctor] ── multipart audio ──► POST /inputs/audio
                                      │
                                      ├─► write bytes to
                                      │    <audio_upload_dir>/<enc>/<uuid>.<ext>
                                      │
                                      ├─► insert encounter_inputs
                                      │     input_type="audio_upload"
                                      │     processing_status="queued"
                                      │     source_metadata={filename, content_type,
                                      │                       size_bytes, stored_path,
                                      │                       original_filename}
                                      │
                                      └─► run_ingestion_now(new_id) inline
                                             │
                                             ├─► queued → processing
                                             ├─► transcribe_audio(metadata)
                                             │       (stub by default; vendor-swappable)
                                             ├─► completed  or  failed + last_error_code
                                             └─► updated row returned in response body
```

## Audio storage

- Root: `settings.audio_upload_dir`
  (env `CHARTNAV_AUDIO_UPLOAD_DIR`, default `./audio_uploads`,
  relative paths resolved against the API package root so
  different CWDs converge on the same directory).
- Layout: `<dir>/<encounter_id>/<uuid>.<ext>` — UUID-named files
  so the original filename never leaks into the filesystem path.
  The doctor-facing original name is kept in
  `source_metadata.original_filename` for audit legibility.
- Size cap: env `CHARTNAV_AUDIO_UPLOAD_MAX_BYTES`, default 25 MiB.
  Enforced at the HTTP layer → 413 `audio_upload_too_large`.
- Content-type + extension allowlist — WAV / MP3 / MP4 / M4A /
  OGG / WEBM / FLAC / AAC. Rejected uploads → 400
  `audio_format_not_supported`.

## Transcription seam

The phase-22 pipeline already exposed a single pluggable
`transcribe_audio(metadata: dict) -> str` callable. Phase 33:

1. Ships `app/services/audio_transcriber.py` — a deterministic
   **stub** that returns either:
   - `metadata["stub_transcript"]` if set (test-only path;
     populated via an `X-Stub-Transcript` header on the upload
     route so the HTTP layer can drive the pipeline
     deterministically without binary fixtures),
   - `metadata["stub_transcript_error"]` raises a
     `StubTranscriberError` so failed-path tests don't need
     corrupt-audio fixtures,
   - otherwise an **honestly-labelled placeholder** that starts
     with the literal prefix `[stub-transcript]` + names the
     uploaded file + bytes + content-type so the clinician
     knows immediately that this is not live STT output.
2. Installs the stub at `app.main` import time. A vendor adapter
   calls `app.services.ingestion.set_transcriber(real_fn)` to
   overwrite — the last caller wins.
3. **Does not pretend STT is live.** Every placeholder transcript
   carries the `[stub-transcript]` marker; a doctor who tries to
   sign a draft generated from one will see the marker in the
   findings tier + generated draft tier + signed artifact, and
   can edit it out via the new transcript-review PATCH surface
   before draft generation.

## Transcript review / edit flow

`PATCH /encounter-inputs/{id}/transcript` with
`{transcript_text}`:

- Only allowed when the input is `completed` (409
  `encounter_input_not_editable` otherwise — races with the
  pipeline's own writes are impossible by construction).
- Minimum 10 chars after trim (400 `transcript_too_short`).
- Overwrites `transcript_text` in place + bumps `updated_at`.
- Preserves provenance: the source audio row (`input_type`,
  `source_metadata`, `stored_path`, creation timestamps, worker
  id) is unchanged — only the text body moves.
- Audit detail: `input_id`, `encounter_id`, `chars`. Never the
  body. A backend test seeds a transcript containing PII-looking
  text and asserts none of it appears in any audit row.

## Generation readiness

`POST /encounters/{id}/notes/generate` already gated on
"at least one `completed` input exists" via
`no_completed_input` (409). No code change needed here — the
new audio path joins the same gate. Frontend behaviour:

- `Generate draft` button stays disabled until a
  `completed` input exists, regardless of whether it came from
  audio upload or text paste.
- The existing blocked-hint (`generate-blocked-note`) copy
  already covers processing / failed / needs_review states;
  audio uploads flow through the same hint text so the doctor
  sees the same messaging whether STT is pending or paste
  ingest failed.

## Frontend changes

- `api.ts`:
  - `uploadEncounterAudio(email, encId, File, {stubTranscript?,
    stubTranscriptError?})` — multipart POST via `FormData`;
    threads stub headers for test / dogfood paths; converts
    non-2xx into the shared `ApiError` shape.
  - `patchEncounterInputTranscript(email, inputId, text)` — JSON
    PATCH.
- `NoteWorkspace.tsx`:
  - New **Upload a dictation audio file** form above the
    existing paste textarea. Accepts `audio/*` + the known
    extensions; disables the submit button until a file is
    chosen; shows filename + KB size; a clearly-labelled
    "stub transcriber" note lives under it until a production
    STT lands.
  - Completed inputs (audio OR text) grow an **Edit transcript**
    button that opens a modal-ish review surface
    (`transcript-edit-modal`).
  - Modal guards: Save disabled under 10 chars; modal closes on
    save + refreshes the inputs list.
  - Reviewer role never sees the audio upload form or the Edit
    transcript button — gated on the existing `canEdit` flag.

## Provenance invariants preserved

- **Transcript audit** (`encounter_input_transcript_edited`)
  records `input_id`, `encounter_id`, `chars`. Backend test
  seeds a transcript containing `PATIENT NAME: JANE DOE,
  MRN 123-45-6789` and asserts none of that text appears in
  any audit event's detail.
- **Surface isolation test** — writes both a Clinical Shortcut
  usage event (`pvd-01`) and a Quick-Comment usage event
  (`sx-01`), edits a transcript, then asserts neither ref (nor
  the keys `shortcut_id` / `preloaded_ref`) appears in the
  transcript-edit audit detail. Transcript provenance stays
  orthogonal to the phase-27/29 clinician-clipboard surfaces.
- Generation consumes `transcript_text` directly, so an edited
  transcript — not the stub placeholder — flows into the next
  draft's extracted findings. Verified by a regression test
  that seeds a stub placeholder, edits to a full clinical
  transcript, then asserts the generated findings reflect the
  edit (visual acuity `20/40`, plan `YAG capsulotomy`).

## Test coverage

- **Backend** — `tests/test_audio_intake.py`, **18 scenarios**:
  - Intake: row creation + metadata shape; empty body; unknown
    format; over-size via env override; reviewer 403; cross-org
    404.
  - Pipeline: default placeholder, canned transcript via header,
    stub forced-error lands as failed, retry path still fails
    with persisted error metadata.
  - Transcript review: completed-only gate, cross-org 404,
    reviewer 403, edit replaces text, PHI-safe audit detail.
  - Generation readiness: blocked until completed audio exists;
    edit flows into next generation (not the placeholder).
  - Provenance isolation: shortcut + quick-comment refs never
    leak into transcript-edit audit.
- **Frontend** — 7 new scenarios in `NoteWorkspace.test.tsx`:
  - Audio upload form renders for clinicians.
  - Audio upload form hidden for reviewers.
  - Upload dispatches `uploadEncounterAudio` + refreshes inputs.
  - Completed audio input renders the **Edit transcript** button.
  - Non-completed audio input does NOT render Edit transcript
    (Retry surfaces instead).
  - Edit modal dispatches `patchEncounterInputTranscript` on
    Save; modal closes after.
  - Save disabled under 10 chars.
  - Generate stays blocked with honest hint when no completed
    input exists (audio-aware path).
- Typecheck clean. Vite build 257.19 kB JS / 21.26 kB CSS
  (gzip 75.78 / 4.41 kB).
- Full backend suite: **327 passed** (309 + 18).
- Full vitest suite: **122 passed** (19 App + 20 AdminPanel +
  83 NoteWorkspace).
- Two pre-existing phase-22 regression tests tightened to
  explicitly uninstall the transcriber before asserting the
  `audio_transcription_not_implemented` failure path — the
  default is now the stub, so the legacy contract needs an
  explicit opt-out.

## Files touched

- `apps/api/app/services/audio_transcriber.py` (new)
- `apps/api/app/main.py` — bootstrap `install_default()`
- `apps/api/app/config.py` — `audio_upload_dir`,
  `audio_upload_max_bytes`
- `apps/api/app/api/routes.py` — two new endpoints; `Request`
  import for multipart parsing
- `apps/api/pyproject.toml` — `python-multipart>=0.0.20`
- `apps/api/tests/test_audio_intake.py` (new)
- `apps/api/tests/test_ingestion_lifecycle.py` — transcriber
  opt-out scope
- `apps/api/tests/test_worker.py` — transcriber opt-out scope
- `apps/web/src/api.ts` — `uploadEncounterAudio`,
  `patchEncounterInputTranscript`
- `apps/web/src/NoteWorkspace.tsx` — audio upload form, edit
  button, review modal, state + handlers
- `apps/web/src/test/NoteWorkspace.test.tsx` — +7 tests + mocks
- `docs/build/05-build-log.md`,
  `16-frontend-test-strategy.md`,
  `44-audio-intake-and-transcription-wedge.md` (new)

## Deliberately NOT done

- No live vendor STT integration (Deepgram / Whisper / vendor).
- No browser-mic recording / ambient listening / real-time WAV
  streaming.
- No mobile recorder UX, no chunked upload, no resume.
- No object-storage adapter (S3/GCS/Azure Blob) — local-disk
  only for now; `stored_path` is a string, so a vendor adapter
  slots into `audio_transcriber` without schema changes.
- No background worker change — the phase-22/23 worker loop
  already picks up `queued` `encounter_inputs`; the stub
  transcriber processes them inline in the request path today
  and the worker path exercises the same seam.

## Follow-on work

1. **First real STT adapter.** Start with Deepgram or OpenAI
   Whisper; implement `transcribe_audio(metadata)` by reading
   `stored_path`, calling the vendor, returning the text.
   `app.services.audio_transcriber.install_default()` becomes
   "only if no vendor adapter was registered"; vendor adapters
   register themselves the same way `app.integrations` does.
2. **Object storage.** Swap local-disk writes for an uploader
   that hands back an opaque URI; adapter reads from URI. No
   schema change.
3. **Chunked / resumable upload.** Tus or multipart-split for
   long dictations over flaky networks.
4. **Browser mic capture.** Once a vendor adapter streams, add
   `MediaRecorder` → Blob → same upload route.
5. **Async pipeline.** If STT latency grows, keep the HTTP
   upload synchronous but move transcription to the phase-22
   worker. The row-state machine already supports it.
