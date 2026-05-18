# ChartNav LLM Provider Decision Memo

> **Status:** Decision-prep + Phase 52 scaffold status. **No
> vendor is selected for production.** **No LLM is wired into
> ChartNav's production note workflow today.** Note drafting
> remains deterministic at
> `apps/api/app/services/note_generator.py:_run_generator`.
> Nothing in this document approves any vendor for real PHI.
> ChartNav is not HIPAA-certified. No vendor confers HIPAA
> compliance.
>
> **Authority:** Read with
> `chartnav-llm-vendor-evaluation.md`,
> `chartnav-llm-fake-data-evaluation-plan.md`,
> `chartnav-ibm-watsonx-vendor-readiness.md`,
> `chartnav-stt-vendor-readiness.md`, and
> `chartnav-real-phi-go-live-gate.md`.

---

## Executive summary

ChartNav has run fake-data-only F1 fixture evaluations against
three candidate LLM vendors and has begun adding **fake-data-only
adapter scaffolds** to the `LLMProvider` Protocol seam:

- **OpenAI** `gpt-4o-mini`: F1 PASS. Adapter scaffold landed in
  Phase 52 (`OpenAIChatProvider`). Disabled by default; guarded
  by four env flags + a per-request fake-data marker.
- **Anthropic** `claude-haiku-4-5`: F1 PASS. Adapter scaffold
  landed in Phase 52 (`AnthropicMessagesProvider`). Same
  default-OFF, guarded posture.
- **IBM watsonx**: BLOCKED before inference. The watsonx.ai
  project cannot bind a pm-20 / watsonx.ai Runtime instance in
  us-south despite active instances existing in the account.
  `/ml/v1/text/generation` returns
  `no_associated_service_instance_error` /
  `container_not_found`. **IBM Support case is open. Do not
  retry until Support responds.**
- **IBM Cloud Projects Git workflow** (PR #50): PASS. Separate
  IBM service from watsonx.ai inference. Project IDs are not
  interchangeable.

**The deterministic stub remains the default provider** in product
code. Live adapters require every guardrail to be flipped; missing
any guardrail produces a loud `ProviderDisabledError`, never a
silent fallback to the stub. ChartNav remains vendor-flexible.

---

## 1. What Phase 52 ships

| File | Change | Purpose |
|---|---|---|
| `apps/api/app/services/llm_provider.py` | extended | Adds `OpenAIChatProvider`, `AnthropicMessagesProvider`, `ProviderDisabledError`, `_check_fake_data_guardrails()`, `LLMRequest.fake_data_context` field. Moves `ibm_watsonx` from "not yet implemented" to **"blocked pending IBM Support"** with a diagnostic-doc pointer. |
| `apps/api/tests/test_llm_provider.py` | extended | 33 tests (17 existing + 16 new) covering: every guardrail per live vendor, IBM blocked posture, fake-data context refusal, mocked-transport dispatch, key-leak regression, no-vendor-SDK source check. |
| `docs/security/chartnav-llm-provider-decision-memo.md` | new | This document. |
| `docs/security/chartnav-llm-vendor-evaluation.md` | modified | Phase 52 status section. |
| `docs/security/chartnav-llm-fake-data-evaluation-plan.md` | modified | Phase 52 status section. |

**Net product-behavior change for production users: none.** The
default selector still returns `DeterministicStubProvider`. No
deployment that does not deliberately flip the guardrails sees
any new behavior.

---

## 2. F1 fake-data eval results (recap)

Local one-shot runs against the synthetic F1 fixture. No real
PHI. Same fixture + same v2 safety rubric applied to every
vendor. Not in CI.

| Vendor | Model | F1 result | Notes |
|---|---|---|---|
| OpenAI | `gpt-4o-mini` | **PASS** | JSON parsed via native `response_format`; 12 / 12 safety checks passed; lowest setup friction. |
| Anthropic | `claude-haiku-4-5` | **PASS** | JSON parsed via prefill-`{` pattern; 12 / 12 safety checks passed; populated useful `safety_flags` proactively. |
| IBM watsonx | `ibm/granite-3-8b-instruct` (intended) | **BLOCKED BEFORE INFERENCE** | IAM token exchange ✅ → inference call 4xx `container_not_found`. Watsonx.ai project cannot associate a Runtime instance even though active pm-20 / watsonx.ai Runtime instances exist in us-south. |

---

## 3. IBM watsonx blocker — current state

| Aspect | Value |
|---|---|
| Watsonx.ai project exists? | Yes |
| pm-20 / Watson Machine Learning service instance exists in us-south? | Yes |
| watsonx.ai Runtime instance exists in us-south? | Yes |
| Project → Manage → Services & integrations binds either of them? | **No — UI cannot complete the association** |
| `/ml/v1/text/generation` response | 4xx `no_associated_service_instance_error` / `container_not_found` |
| IBM Support case | Open |
| ChartNav action | **Wait for IBM Support. No further inference retries.** |

The block is on IBM's side. ChartNav cannot bind a runtime to the
project from the watsonx.ai console; that's exactly what Support
must resolve. Phase 52 codifies this state in the provider seam:
selecting `ibm_watsonx` now raises a clear `NotImplementedError`
pointing here.

---

## 4. Phase 52 — guardrails (every live adapter)

A live adapter (OpenAI, Anthropic) refuses to start unless **all
of the following** are true. Missing any → `ProviderDisabledError`
with the offending flag named.

| Flag | Required value | Reason |
|---|---|---|
| `CHARTNAV_LLM_PROVIDER` | `openai` or `anthropic` | Selects the live adapter |
| `CHARTNAV_LLM_ENABLED` | `1` | Operator-intent confirmation |
| `CHARTNAV_LLM_REAL_PHI_APPROVED` | `0` (or unset) | **MUST be 0.** Live adapters are fake-data-only. A real-PHI deployment must use a vetted path that does not exist yet. |
| `CHARTNAV_PILOT_ALLOW_LLM_<VENDOR>` | `1` | Per-vendor practice-approval gate |
| `CHARTNAV_<VENDOR>_API_KEY` | present | Vendor credential (presence-only check; value never logged) |

Per-request enforcement:

| Field | Required | Reason |
|---|---|---|
| `LLMRequest.fake_data_context` | `True` (default) | The caller declares the payload is synthetic. Setting it to `False` causes the live adapter to refuse. |

IBM watsonx has no guardrail path today. The key is in
`_BLOCKED_PROVIDERS`; selection raises `NotImplementedError`
unconditionally. `CHARTNAV_PILOT_ALLOW_LLM_WATSONX` is reserved
for future use but is not read.

---

## 5. Phase 52 — adapter shape

Each live adapter implements the `LLMProvider` Protocol. Today
only `draft_provider_review_note` is wired through to a real
vendor call:

| Method | Phase 52 status |
|---|---|
| `summarize_transcript` | NotImplementedError (later phase) |
| `extract_structured_facts` | NotImplementedError (later phase) |
| `draft_provider_review_note` | **wired** (urllib over HTTPS, no vendor SDK) |
| `classify_note_quality_risk` | NotImplementedError (later phase) |
| `detect_prompt_injection` | NotImplementedError (later phase) |
| `normalize_chart_context` | NotImplementedError (later phase) |

The adapters use a pluggable `ChatTransport` callable for tests
to inject fakes — identical pattern to `OpenAIWhisperProvider`
in `stt_provider.py`. CI never calls a real vendor.

Prompt templating:

- The system prompt is identical across vendors (
  `_SHARED_HARD_RULES`) and is **server-side templated**. User
  content is interpolated inside `<transcript>` and
  `<chart_context>` data blocks. The system prompt instructs
  the model to treat those blocks as data, not instructions —
  the first line of defense against prompt injection.
- Output schema is enforced via the system prompt + vendor-
  specific JSON-coercion: OpenAI native `response_format`;
  Anthropic prefill-`{` pattern.

---

## 6. Safety posture (live adapters)

- ✅ **Default off.** With no env config, default selector returns
  the deterministic stub. No external call.
- ✅ **Loud failure on misconfig.** Missing any guardrail →
  `ProviderDisabledError` naming the flag.
- ✅ **No silent fallback.** A live-provider key with missing
  guardrails never degrades to the stub.
- ✅ **Real-PHI gate refuses.** Flipping
  `CHARTNAV_LLM_REAL_PHI_APPROVED=1` makes the live adapters
  REFUSE — they are fake-data-only by design.
- ✅ **Per-request fake-data flag.** `LLMRequest.fake_data_context`
  defaults True; setting False produces refusal.
- ✅ **Key never logged.** Sanitizer scrubs the key from every
  error path. Regression-locked by
  `test_<vendor>_api_key_never_logged_on_failure_path`.
- ✅ **No vendor SDK imported.** Adapters use urllib only.
  Regression-locked by `test_module_source_imports_no_vendor_sdk`.
- ✅ **Output requires review.** Every `LLMResponse` from a live
  adapter sets `requires_review=True` and the structured output
  includes `requires_provider_review=true` +
  `forbidden_actions.{diagnosis, orders, patient_message,
  billing_or_coding}` all `false`.
- ✅ **Anti-injection prompt.** System prompt instructs the model
  to treat transcript / chart_context blocks as data only.
- ✅ **Capability banner unaffected.** Selecting `openai` /
  `anthropic` does NOT clear `demo_mode=true` because the
  capability banner still keys off STT provider, platform mode,
  and `CHARTNAV_REAL_PHI_APPROVED`. The LLM live adapters do not
  flip the banner today.

---

## 7. Required gates before real PHI

Phase 52 introduces **no new** real-PHI capabilities. Real-PHI
flow remains gated by the existing list in
`chartnav-real-phi-go-live-gate.md`:

- [ ] BAA executed (per vendor, per endpoint, per model).
- [ ] Vendor SOC 2 Type II reviewed.
- [ ] Vendor customer-data-not-used-to-train in writing.
- [ ] Zero-retention or short-retention term documented.
- [ ] Region pinned to a healthcare-eligible region.
- [ ] `chartnav-subprocessor-inventory.md` updated.
- [ ] `chartnav-phi-data-flow-map.md` updated.
- [ ] F1–F7 fixtures all PASS for the vendor.
- [ ] `apps/api/tests/evals/test_safety_eval.py` extended for the
      vendor-backed path.
- [ ] Logging redaction reviewed for the new vendor egress path.
- [ ] Incident-response runbook updated to cover vendor outage.
- [ ] Security + legal review signed.
- [ ] Practice signs off in writing.
- [ ] Operator flips `CHARTNAV_REAL_PHI_APPROVED=1` AND the
      per-vendor allow gate AND the (future) production-LLM gate
      that does not exist yet.

The fake-data adapters in Phase 52 are NOT on the real-PHI path.
A future phase will add a separate vetted real-PHI code path
that cannot be reached by flipping these flags alone.

---

## 8. Human-review requirement

Every vendor-generated draft (today and in any future phase):

- Lands in `status=draft`. Never auto-promoted.
- Runs through `note_quality.py` linter before render.
- Runs through `chart_conflicts.py` surfacer before
  finalization.
- Sign-off requires a permitted role (`admin` / `clinician`).
  Reviewer remains read-only.
- Rejection is one click; rejection is logged in
  `security_audit_events`.

No vendor output may flow into automatic orders, referrals,
coding, billing, or patient messaging. Those surfaces do not
exist in ChartNav and remain forbidden by the safe-claims
contract.

---

## 9. No-public-claims policy

Existing claim guards (PR #48, PR #49) block, with negative-
context exemptions, all of:

- "OpenAI-powered clinical documentation"
- "GPT-powered clinical documentation"
- "Claude-powered clinical documentation"
- "Anthropic-powered clinical documentation"
- "watsonx-powered clinical documentation"
- "Watson-powered clinical documentation"
- "LLM-powered diagnosis" / "AI diagnosis"
- "autonomous documentation"
- "autonomous clinical reasoning"
- "vendor-approved for PHI"
- "BAA-ready by default"
- "vendor makes ChartNav HIPAA compliant"
- "production PHI-ready"
- "certified EHR"
- "ambient scribe parity"

Phase 52 introduces no new public-facing claims about any vendor.

---

## 10. Next implementation options

Three viable next phases. None is committed.

### Option A — Run F2–F7 against OpenAI + Anthropic (recommended)

Use the existing dev scripts (out-of-tree) to exercise the
remaining fixtures: laterality mismatch, hallucinated vitals,
unsafe-diagnosis probe, prompt injection, missing disclaimer,
chart-context contradiction. No code change. Modest spend.

**Expected outcome:** either both vendors stay green (then we
have a defensible go/no-go answer per
`chartnav-llm-vendor-evaluation.md` section 15), or a fixture
fires a block criterion and a vendor is rejected.

### Option B — Wire the adapter into a feature-flagged dev surface

Add a developer-only HTTP endpoint that exercises
`OpenAIChatProvider.draft_provider_review_note` against a fake
fixture, gated by the same guardrails. No production user
reaches it. Useful for end-to-end validation of the full path
(network → vendor → parse → audit → render) with synthetic
inputs.

**Code touches:** small admin route, dev-only flag, no
behavior change for production users.

### Option C — Wait on IBM Support, then run watsonx F1

No ChartNav code change. When Support resolves the project-
runtime association, re-run the watsonx F1 eval. If pass, the
existing `_BLOCKED_PROVIDERS["ibm_watsonx"]` entry is removed in
a future PR and a `WatsonxProvider` adapter is added with the
same guardrail shape.

### Recommended sequencing

1. Now: review + approve Phase 52.
2. Next: Option A (F2–F7 against the two passing vendors).
3. In parallel: Option C (wait on IBM Support).
4. Later, on explicit approval: Option B.

No phase forces the next phase. Each is approved on its own.

---

## Related documents

- `docs/security/chartnav-llm-vendor-evaluation.md`
- `docs/security/chartnav-llm-fake-data-evaluation-plan.md`
- `docs/security/chartnav-ibm-watsonx-vendor-readiness.md`
- `docs/security/chartnav-stt-vendor-readiness.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
- `docs/security/chartnav-baa-vendor-readiness-checklist.md`
- `docs/integrations/ibm-cloud-projects-git-integration.md`
