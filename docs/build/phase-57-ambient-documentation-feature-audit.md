# Phase 57 — Provider-Reviewed Ambient Documentation Feature Audit

> Scope: pre-implementation audit of existing audio / transcript / scribe /
> note / LLM-provider infrastructure on `main` at `896352d`. No product
> behaviour changes were made during this audit.
>
> **Headline:** The full lifecycle state machine, RBAC, audit
> minimisation, and storage that Phase 57 needs **already exist** in
> `scribe_sessions` (Phase 8). Phase 57 should reuse that table and
> add only a narrow ambient-draft generation seam plus a thin UI.

## 1. Existing audio / STT / documentation assets found

| Asset | Path | What it is |
|---|---|---|
| Stub audio transcriber | `apps/api/app/services/audio_transcriber.py` | Pluggable transport seam (Phase 33/35). Returns `[stub-transcript]` placeholder unless overridden. No real STT in tree. |
| **Scribe sessions service** | `apps/api/app/services/scribe_sessions.py` | **The core lifecycle table for transcript → draft → reviewed → finalised.** Status: `draft → processing → ready_for_review → reviewed → finalized` (+ `discarded`). Per-session fields: `source_text`, `transcript_text`, `draft_note_text`, `structured_note_json`, `review_notes`, `linked_artifact_id`. Org-scoped, patient-scoped, optional encounter linkage. |
| Scribe sessions routes | `apps/api/app/api/scribe_sessions.py` | Full CRUD + `/process`, `/review`, `/finalize`, `/discard` endpoints. RBAC admin/clinician write, reviewer read-only. Metadata-only audit. |
| Scribe sessions migration | `apps/api/alembic/versions/f1a2b3c4d5e6_scribe_sessions_lifecycle.py` | Defines the `scribe_sessions` table; comment explicitly says body fields are NEVER written to audit logs. |
| Scribe sessions tests | `apps/api/tests/test_scribe_sessions.py` | Full lifecycle, RBAC, org isolation. |
| Audio consent UI | `apps/web/src/AudioConsentPanel.tsx` | Browser recording capture + consent surface. |
| Note generator (deterministic) | `apps/api/app/services/note_generator.py` | `generate_draft(transcript_text, patient_display, provider_display)` → `GenerationResult` (findings dict + note_text + missing_flags). Comment: "Replace `_run_generator` with a real LLM call when you wire one." |
| Note orchestrator | `apps/api/app/services/note_orchestrator.py` | Enforces the pipeline contract (transcript → findings → draft → review-required). |
| Note version snapshot | `apps/api/alembic/versions/e1f2a3041501_note_generated_text_snapshot.py` | Immutable snapshot persistence. |

## 2. Existing LLM provider assets found

| Asset | Path | What it does |
|---|---|---|
| LLM provider scaffold | `apps/api/app/services/llm_provider.py` | Phase 52 scaffold + Phase 52B fake-data adapters. Public exports: `LLMRequest`, `LLMResponse`, `LLMProvider` Protocol, `DeterministicStubProvider`, `OpenAIChatProvider`, `AnthropicMessagesProvider`, `select_default_provider`, `ProviderDisabledError`. |
| Phase 54 public guardrail | `assert_live_provider_safe_to_use(provider_key, request)` | Combines env-state gates (`CHARTNAV_LLM_ENABLED`, `CHARTNAV_LLM_REAL_PHI_APPROVED`, `CHARTNAV_PILOT_ALLOW_LLM_*`, vendor API key presence) and per-request gates (`fake_data_context=True`, `requires_provider_review=True`). Raises `ProviderDisabledError` if any gate fails. |
| Protocol method | `draft_provider_review_note(LLMRequest) -> LLMResponse` | The **only** Protocol method wired beyond the deterministic stub. Returns a draft + structured facts + safety flags; pins `requires_provider_review=True` and `forbidden_actions.{diagnosis,orders,patient_message,billing_or_coding}=false`. |
| Tests | `apps/api/tests/test_llm_provider.py`, `tests/test_fundus_llm_guardrails.py` | Pin every gate-refusal path; verify no vendor SDK is imported; verify API key never appears in logs. |

## 3. Existing note / encounter / draft-note structures

The repo already exposes the entire chain Phase 57 wants:

| Table | Purpose |
|---|---|
| `scribe_sessions` | The ambient-documentation lifecycle row. Phase 57 uses this verbatim. |
| `encounter_notes` | Phase 19 encounter-scoped notes (different lifecycle — kept separate). |
| `extracted_findings` | Structured fact extraction snapshot. |
| `note_*_snapshot` | Immutable note-text versioning. |

## 4. Existing safety gates found

- Phase 52B env + per-request gates (above).
- `app/audit.py` records `event_type`, `actor_user_id`, `org_id`, `path`, `method`, `error_code`, `detail`. Audit failures never mask the original error. The `detail` field is metadata-only by convention; Phase 56 added a regression test that scans audit rows for forbidden substrings (raw findings text, drawing_json, rendered_svg).
- Three claim scanners (`scripts/check_{commercial,website,demo}_claims.sh`) block phrases like "autonomous documentation", "OpenAI-powered clinical documentation", "real PHI ready", "HIPAA compliant", "automatic note writing", etc.

## 5. Missing pieces

The infrastructure is mostly already there. Phase 57 must add:

1. A new service `apps/api/app/services/ambient_documentation.py` that:
   - takes a scribe-session row (or its `transcript_text`),
   - runs a deterministic draft pipeline by default (using the existing `note_generator._run_generator` seam, or a tighter ambient-specific variant),
   - optionally dispatches to OpenAI via the Phase 52B fake-data adapter when the operator opts in via `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai` AND every Phase 52B gate is SAFE,
   - never invents diagnoses, orders, referrals, patient messages, billing, or coding,
   - never calls a real OpenAI endpoint in CI (pluggable transport),
   - never logs the API key.
2. **One** new HTTP endpoint that runs the ambient pipeline against an existing scribe-session row. Patient-scoped to match the existing scribe-sessions router. No new table. No new migration.
3. A new frontend feature module at `apps/web/src/features/ambient/` mounted in the **Documentation tab** of `ClinicalTabbedWorkspace`. The tab already exposes a Transcript → Facts → AI Draft → Final stepper; the ambient panel slots naturally beside it.
4. Tests pinning: deterministic default, all gate-refusal cases (no silent fallback under opt-in), audit minimisation, role matrix (via existing scribe-session RBAC), cross-org 404, signed-draft immutability (via existing scribe-session terminal-state contract), no forbidden phrasings in rendered UI.
5. Docs:
   - `docs/workflow/ambient-documentation-assist.md` — feature contract + safety boundary;
   - `docs/demo/phase-57-ambient-documentation-demo-runbook.md` — Phase 56-style operator runbook.
6. Claim-scanner phrases for ambient-specific overclaims (`hands-free scribing`, `ambient scribe parity`, `note writes itself`, `chart fills itself`, etc.) if absent.

## 6. Implementation decision

**Reuse > rebuild.**

- **Do not add** `ambient_note_drafts` table. `scribe_sessions` already has every column needed (`source_text`, `transcript_text`, `draft_note_text`, `structured_note_json`, `review_notes`, lifecycle status, optional encounter linkage). Adding a parallel table would split state across two surfaces.
- **Do not duplicate** the lifecycle state machine. Reuse `scribe_sessions`'s `draft → processing → ready_for_review → reviewed → finalized` machine. The Phase 57 endpoint transitions a row from `draft` to `ready_for_review` after generating the ambient draft.
- **Do not add** parallel encounter-scoped routes. The existing patient-scoped `/api/v1/patients/{patient_id}/scribe-sessions/...` routes are tenant-safe and already in tests. Phase 57 adds **one** new endpoint (`POST .../scribe-sessions/{session_id}/draft-ambient`) that drives ambient generation against an existing row.
- **Do not call** OpenAI from CI. Inject `transport: AmbientAssistTransport` callable (same pattern as Phase 54 fundus assist).
- **Do not** ever set the draft from raw model output without provider-review-required pinning. The new service always returns `requires_provider_review=True`.

The Phase 56-era audit-minimisation + Phase 52B gate-refusal patterns transfer verbatim. The ambient-specific UI is the only new surface that needs serious design work.

## Related documents

- `docs/security/chartnav-openai-fake-data-adapter.md`
- `docs/workflow/fundus-charting.md`
- `docs/demo/phase-56-fundus-demo-runbook.md` — template for Phase 57's demo runbook.
- `docs/build/phase-55-fundus-demo-readiness-audit.md` — template for this audit's structure.
