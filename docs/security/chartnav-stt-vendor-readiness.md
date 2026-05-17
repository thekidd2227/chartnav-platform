# ChartNav STT (Speech-to-Text) Vendor-Readiness

> **Status:** Vendor-readiness reference for operators evaluating
> ChartNav's external STT provider path against **fake / demo
> audio only**. Nothing in this document approves real-PHI use of
> any STT vendor.
>
> **ChartNav is not HIPAA-certified. ChartNav is not "Whisper-
> powered." OpenAI does not make ChartNav HIPAA compliant.**
>
> **Authority:** Read with
> `chartnav-real-phi-go-live-gate.md`,
> `chartnav-baa-vendor-readiness-checklist.md`, and
> `chartnav-ibm-watsonx-vendor-readiness.md` (same shape; same
> gates).

ChartNav ships a configurable STT provider path so the operator
can swap between a deterministic stub (default) and a real
external vendor (OpenAI Whisper today; others can register the
same `STTProvider` Protocol). This doc is the single artifact a
practice security owner walks before enabling any external STT
vendor.

---

## 1. Current STT state

Implementation lives in `apps/api/app/services/stt_provider.py`.
The provider seam is selected by `CHARTNAV_STT_PROVIDER`.

| Provider key | Class | Network call? | Default? |
|---|---|---|---|
| `stub` (or unset) | `StubSTTProvider` | No | ✅ |
| `openai_whisper` | `OpenAIWhisperProvider` | Yes — `POST https://api.openai.com/v1/audio/transcriptions` | No |
| `none` | (installs `_not_implemented_transcriber`) | No; uploads fail with `audio_transcription_not_implemented` | No |
| anything else | (boot raises `RuntimeError`) | n/a — never silently downgrades | No |

`OpenAIWhisperProvider` **fails loud at construction** if
`CHARTNAV_OPENAI_API_KEY` is missing. There is no silent fallback
to the stub — that's an explicit design rule so a misconfigured
production deployment can never ship `[stub-transcript]`
placeholders under a clinician's signature.

The admin endpoint `GET /admin/security/stt-readiness` returns a
metadata-only snapshot (provider key, key-presence flag, upload
behavior, egress posture, hard-pinned `real_phi_ready=false`).
The API key value is **never** returned.

---

## 2. What OpenAI STT can be used for today

- ✅ **Fake / demo audio** — short, synthetic dictations with no
  PHI content. Used to verify the provider plumbing end-to-end
  before any BAA conversation begins.
- ✅ **Controlled-pilot evaluation** — only after the practice
  has executed a BAA with OpenAI (or accepted OpenAI as a
  ChartNav subprocessor under ChartNav's BAA chain) **and** the
  controlled-pilot allow-gate (`CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1`)
  has been flipped per practice approval.
- ✅ **Internal regression / safety eval** against synthetic
  fixtures (already covered by `tests/test_audio_pipeline_phase35.py`
  using the injected transport seam — no real network).

## 3. What OpenAI STT may **not** be used for

- ❌ **Real PHI** — until every box in
  `chartnav-real-phi-go-live-gate.md` is closed.
- ❌ **Production deployment** — the runtime never auto-flips
  `real_phi_ready=true`. The capability banner remains
  `demo_mode=true` until the operator explicitly sets
  `CHARTNAV_REAL_PHI_APPROVED=1`.
- ❌ **Public claim that ChartNav is "Whisper-powered" or
  "powered by OpenAI."** See section 11 below.
- ❌ **Ambient / always-on listening.** ChartNav's microphone
  capture is explicit-click only (Phase 36); enabling Whisper
  does not change that.

---

## 4. Local test workflow with fake audio

ChartNav already ships a comprehensive mocked test for the
OpenAI Whisper path. The injected `WhisperTransport` seam lets
the full provider be exercised **without any real network
call**, against synthetic audio bytes. Operators evaluating
ChartNav for STT readiness should run these first.

### Step-by-step

1. Set the environment to fake-data mode (no real PHI, no
   production approval). Use placeholder values only:

   ```env
   # Local-only — never commit this file.
   CHARTNAV_STT_PROVIDER=openai_whisper
   CHARTNAV_OPENAI_API_KEY=sk-...your-local-key...
   CHARTNAV_REAL_PHI_APPROVED=0
   CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=0
   ```

2. Run the mocked STT suite (no network required):

   ```bash
   cd apps/api
   python3 -m pytest \
     tests/test_audio_pipeline_phase35.py \
     tests/test_stt_readiness.py \
     tests/test_audio_intake.py \
     tests/test_audio_capture_source_phase36.py
   ```

   These cover the OpenAI Whisper success path, 4xx / 5xx
   failures, missing-text response, oversize audio, async retry,
   and the api-key-never-logged regression lock.

3. (Optional, **local only**) Run a one-off live call against
   OpenAI with a tiny synthetic WAV containing fake-content
   text. Do **not** commit any audio file containing real
   patient identifiers, real DOBs, real MRNs, or real phone
   numbers. Suggested fake-content narration:

   > "Fake demo patient reports blurry vision. This is not
   > real patient information."

4. Confirm `/admin/security/stt-readiness` reports
   `real_phi_ready=false` and `external_egress=required`. The
   payload must never contain the API key value.

### What to verify

- Request reaches OpenAI only when `CHARTNAV_STT_PROVIDER=openai_whisper`.
- Stub mode returns `[stub-transcript]` and no network call is
  made.
- Provider errors come back as a clean `IngestionError` with a
  stable `error_code` (`openai_whisper_http_error`,
  `openai_whisper_transport_error`, `openai_whisper_missing_text`,
  `openai_whisper_empty_audio`, `openai_whisper_audio_too_large`).
- The API key value never appears in stdout, logs, audit rows,
  or `/admin/security/stt-readiness` responses.

---

## 5. How to disable STT

Three independent ways, all safe:

- **Pin to stub:** `CHARTNAV_STT_PROVIDER=stub` (or unset).
  ChartNav stays on the deterministic placeholder; no external
  call.
- **Hard disable:** `CHARTNAV_STT_PROVIDER=none`. Audio uploads
  return `audio_transcription_not_implemented`. Use this for
  staging environments that explicitly forbid STT.
- **Drop credentials:** unset `CHARTNAV_OPENAI_API_KEY`.
  Boot fails loud if `CHARTNAV_STT_PROVIDER=openai_whisper`.

---

## 6. Readiness status reporting

`GET /admin/security/stt-readiness` (admin role only) returns a
JSON metadata snapshot:

```json
{
  "provider_key_raw": "openai_whisper",
  "provider_key_recognized": true,
  "openai_api_key_present": true,
  "upload_behavior": "accepts_calls_openai_whisper",
  "external_egress": "required",
  "real_phi_ready": false,
  "guidance": "STT provider is metadata-only. Real-PHI use requires a BAA, completed vendor review, and operator sign-off per docs/security/chartnav-real-phi-go-live-gate.md. This endpoint never reports HIPAA-compliance.",
  "organization_id": 1
}
```

Notes:

- `openai_api_key_present` is a presence-only boolean. The key
  value itself is never returned.
- `real_phi_ready` is hard-pinned `false` in
  `apps/api/app/api/admin_security.py`. The runtime never auto-
  flips it. Operator sign-off is off-runtime.
- The capability banner `/platform.capability_banner` continues
  to show `demo_mode=true` until **every** reason clears
  (`stt_stub`, `stt_none`, `standalone_mode`, `real_phi_gate_off`).

---

## 7. Required environment variables

ChartNav reads the following names today. Do not commit values.

| Variable | Read by | Purpose |
|---|---|---|
| `CHARTNAV_STT_PROVIDER` | `stt_provider.py:347`, `admin_security.py:416` | Selects provider. `stub` / `openai_whisper` / `none`. |
| `CHARTNAV_OPENAI_API_KEY` | `stt_provider.py:175`, `admin_security.py:423` | OpenAI credential. Presence-only checks anywhere user-visible. |
| `CHARTNAV_STT_MODEL` | `stt_provider.py:176` | Optional model override; default `whisper-1`. |
| `CHARTNAV_STT_TIMEOUT_S` | `stt_provider.py:181` | Optional transport timeout (seconds); default `120`. |
| `CHARTNAV_OPENAI_API_BASE` | `stt_provider.py:190` | Optional vendor-base override; default `https://api.openai.com/v1`. |
| `CHARTNAV_REAL_PHI_APPROVED` | `routes.py:347`, `test_capability_banner.py` | Operator-flipped real-PHI gate. Clears the `demo_mode` banner only when combined with non-stub STT and non-standalone mode. |
| `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER` | `scripts/validate_controlled_pilot_env.sh:210` | Practice-approval gate enforced by the controlled-pilot env validator. Without `=1`, the validator fails when provider is `openai_whisper`. |

Notes on names from operator briefs that do **not** map to code:

- `OPENAI_API_KEY` (no `CHARTNAV_` prefix) is **not** read by
  ChartNav. Use `CHARTNAV_OPENAI_API_KEY`.
- `CHARTNAV_STT_PHI_APPROVED`, `CHARTNAV_STT_VENDOR_APPROVED`,
  `CHARTNAV_REAL_PHI_ENABLED` are not read by ChartNav code. The
  corresponding intent is covered by
  `CHARTNAV_REAL_PHI_APPROVED` and the controlled-pilot allow
  gate above.

---

## 8. Operator readiness checklist

Each item must be closed before flipping ChartNav off the stub
in any environment that may carry real PHI. Fake-audio testing
on a developer machine does not require these — but the moment
real PHI enters the picture, every box must be filled.

- [ ] **BAA with OpenAI** executed (or OpenAI accepted as a
      ChartNav subprocessor under ChartNav's BAA chain). Filed
      in the practice's records. Date: `__________`.
- [ ] **Vendor review** of OpenAI's published security posture
      complete. Reviewer initials + date: `__________`.
- [ ] **PHI egress approved** in writing by the practice for
      the watsonx/Whisper endpoint(s) in scope.
- [ ] **Subprocessor inventory** updated
      (`chartnav-subprocessor-inventory.md`) to include OpenAI.
- [ ] **PHI data-flow map** updated
      (`chartnav-phi-data-flow-map.md`) with the OpenAI egress
      arrow and 🔴 ↗ 🔒 markers.
- [ ] **Audio retention policy** in effect; pruner cron wired
      (`scripts/prune_audio_retention.py`).
- [ ] **Audio consent gate** captured per encounter
      (Phase 25A / GH-001) before any audio upload.
- [ ] **`CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1`** flipped by
      operator with practice sign-off on file.
- [ ] **`CHARTNAV_REAL_PHI_APPROVED=1`** flipped (global gate).
- [ ] **`scripts/validate_controlled_pilot_env.sh`** passes.
- [ ] **Mocked STT regression suite** green
      (`tests/test_audio_pipeline_phase35.py`,
      `tests/test_stt_readiness.py`).

---

## 9. Secret-handling rules

- `CHARTNAV_OPENAI_API_KEY` **must never** be committed. Use
  local-only env files (e.g., `.env` covered by `.gitignore`)
  or your secret manager.
- The API key value is never printed by ChartNav: the provider
  reads it once at construction, sends it as the `Authorization:
  Bearer ...` header, and never logs it. The
  `test_openai_whisper_api_key_never_appears_in_logs`
  regression test locks this in.
- The `/admin/security/stt-readiness` endpoint reports
  **presence only** (`openai_api_key_present: true | false`).
- `security_audit_events` and `ai_governance_log` are metadata-
  only; transcripts or response bodies are not persisted under
  the audit surface.

If you suspect a key has leaked, rotate it in the OpenAI
dashboard, update `CHARTNAV_OPENAI_API_KEY` in your local env,
and restart the application.

---

## 10. Failure-handling guarantees

The audio ingestion workflow must not crash on STT failure. The
provider raises a typed `IngestionError`; the worker pipeline
catches it and persists `processing_status=failed` with a stable
`last_error_code` and a `retry_count`. Tests covering this
contract:

- `test_openai_whisper_4xx_raises_clean_error_code`
- `test_openai_whisper_missing_text_field_raises`
- `test_openai_whisper_oversize_audio_fails_before_post`
- `test_async_mode_failed_then_retry_completes`
- `test_stub_transcriber_failure_lands_as_failed_with_error_code`

Operator-initiated retry via `POST /encounter-inputs/{id}/retry`
re-runs the pipeline without crashing the FastAPI process.

---

## 11. Prohibited public claims

The following are **forbidden** in every customer-facing
artifact (decks, website, demo runbook, pilot outreach, docs,
press, social, status pages). Claim scanners
(`scripts/check_commercial_claims.sh`,
`scripts/check_website_claims.sh`,
`scripts/check_demo_claims.sh`) enforce this list.

- ❌ "Whisper-powered"
- ❌ "powered by OpenAI"
- ❌ "OpenAI-powered clinical documentation"
- ❌ "OpenAI makes ChartNav HIPAA compliant"
- ❌ "Whisper diagnosis"
- ❌ "automatic clinical documentation"
- ❌ "ambient scribe parity"
- ❌ "production STT"
- ❌ "Cora replacement"

These phrases may appear only inside an explicit negative-
context line ("ChartNav is **not** powered by OpenAI," etc.)
and inside catalog documents like this one whose purpose is to
enumerate forbidden claims.

---

## 12. Safe public wording

Use one of these phrasings when a buyer asks about ChartNav's
STT capability.

- ✅ "ChartNav supports a configurable STT provider path for
  fake-data testing and controlled readiness review."
- ✅ "ChartNav's STT seam currently supports a deterministic
  stub (default) and a real OpenAI Whisper adapter. The real
  adapter is disabled by default."
- ✅ "Enabling Whisper for real PHI requires a BAA, a security
  review, practice approval, and the ChartNav real-PHI go-live
  gate to close."
- ✅ "ChartNav remains the data controller and the audit
  authority. Adding an STT vendor does not change the human-
  review requirement or the safe-claims contract."

---

## 13. Go / no-go decision table

| Question | Required answer | If not |
|---|---|---|
| Is fake-data evaluation the only goal of this session? | Yes (fake) — or **all** below items are closed (real PHI) | Stay on stub. |
| Has the practice security owner approved enabling Whisper, in writing? | Yes | **No-go.** |
| Is the BAA between ChartNav and OpenAI executed for the Whisper service? | Yes | **No-go** — fake audio only. |
| Is OpenAI listed in `chartnav-subprocessor-inventory.md`? | Yes | **No-go** — update inventory first. |
| Has `chartnav-phi-data-flow-map.md` been updated with the OpenAI egress arrow? | Yes | **No-go.** |
| Is `CHARTNAV_REAL_PHI_APPROVED=1` for this deployment? | Yes | **No-go** — fake data only. |
| Is `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER=1`? | Yes | **No-go.** |
| Is `CHARTNAV_OPENAI_API_KEY` set in env (presence-only) and **never** committed? | Yes / No | **No-go** if committed. |
| Does the mocked STT regression suite pass? | Yes | **No-go.** |
| Will every Whisper-generated transcript pass through clinician review before sign-off? | Yes | **No-go** — autonomous use is forbidden. |
| Will the product remain free of "Whisper-powered," "OpenAI-powered HIPAA," and equivalent public claims? | Yes | **No-go** — claim scanners will fail the build. |

A single **No-go** answer blocks enablement for real PHI.

---

## Related documents

- `chartnav-real-phi-go-live-gate.md`
- `chartnav-baa-vendor-readiness-checklist.md`
- `chartnav-subprocessor-inventory.md`
- `chartnav-phi-data-flow-map.md`
- `chartnav-ibm-watsonx-vendor-readiness.md`
- `chartnav-customer-responsibility-matrix.md`
- `docs/commercial/chartnav-approved-claims-language.md`
