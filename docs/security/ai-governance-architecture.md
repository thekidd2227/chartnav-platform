# ChartNav AI Governance Architecture

**Status:** Internal scaffold only — no external IBM calls active
**Last updated:** 2026-04-27

---

## AI Use-Case Inventory

Every AI capability ChartNav exposes is registered as a named use-case.
Registration happens at startup or via admin API.

| Field | Description |
|---|---|
| `use_case_id` | UUID, stable across deploys |
| `name` | Human-readable: "Clinical Note Generation", "ICD-10 Coding Assist" |
| `description` | What the AI does and when it is invoked |
| `model_provider` | "openai", "anthropic", "stub" |
| `model_name` | "gpt-4o", "claude-sonnet-4-20250514", etc. |
| `phi_exposure` | Whether PHI appears in prompt context |
| `output_type` | "text", "code", "structured_json", "classification" |
| `requires_human_review` | Boolean — whether output must be reviewed before use |
| `clinical_disclaimer_required` | Boolean |
| `active` | Whether this use-case is currently enabled |

---

## Model/Provider Registry

Tracks every model version ChartNav has ever used.

| Field | Description |
|---|---|
| `model_id` | UUID |
| `provider` | "openai", "anthropic", "ibm_watsonx" |
| `model_name` | Versioned model string |
| `version_tag` | Optional: "2025-05-14", "v1.0" |
| `registered_at` | Timestamp |
| `deprecated_at` | Null if active |
| `notes` | Drift notes, evaluation summary |

---

## Prompt/Template Registry

Every prompt template ChartNav sends to an AI model is versioned.

| Field | Description |
|---|---|
| `template_id` | UUID |
| `use_case_id` | FK → ai_use_cases |
| `template_hash` | SHA-256 of template content (no raw PHI stored) |
| `template_preview` | First 200 chars of template (no PHI) |
| `version` | Monotonic integer |
| `active` | Boolean |

---

## AI Output Audit Trail

One row per AI output produced in production.

| Field | Description |
|---|---|
| `audit_id` | UUID |
| `org_id` | FK — org-scoped, never cross-org |
| `user_id` | Who triggered the generation |
| `encounter_id` | Optional — which encounter this relates to |
| `use_case_id` | FK → ai_use_cases |
| `model_id` | FK → ai_model_registry |
| `prompt_template_id` | FK → ai_prompt_templates |
| `input_hash` | SHA-256 of prompt+context (no raw PHI) |
| `output_hash` | SHA-256 of AI response |
| `output_preview` | First 200 chars (no PHI) |
| `phi_redacted` | Boolean — was PHI stripped before storage |
| `clinical_disclaimer_shown` | Boolean |
| `latency_ms` | Response time |
| `token_count_prompt` | Prompt tokens |
| `token_count_completion` | Completion tokens |
| `created_at` | Timestamp |

**PHI policy:** Raw prompt text and raw AI output are NEVER stored in
the audit trail. Only hashes and non-PHI previews.

---

## Human Review Status

| Field | Description |
|---|---|
| `review_id` | UUID |
| `audit_id` | FK → ai_output_audit |
| `reviewer_user_id` | Who reviewed |
| `org_id` | Org-scoped |
| `decision` | "accepted", "rejected", "modified" |
| `notes` | Optional reviewer notes |
| `reviewed_at` | Timestamp |

---

## PHI Redaction Status

Tracked inline in `ai_output_audit.phi_redacted`. When `true`, the
ingestion pipeline confirmed PHI was stripped before context was sent to
the AI model OR before the output was stored.

Redaction is handled by `app/services/ai_governance.py:record_ai_output()`
— callers must pass `phi_redacted=True` explicitly if they ran redaction.

---

## Clinical Disclaimer Status

Tracked inline in `ai_output_audit.clinical_disclaimer_shown`.
The frontend is responsible for rendering the disclaimer; the API records
whether it was triggered.

---

## Security Event Log

| Field | Description |
|---|---|
| `event_id` | UUID |
| `org_id` | Org-scoped |
| `user_id` | Optional — may be null for unauthenticated events |
| `event_type` | See event type taxonomy below |
| `severity` | "low", "medium", "high", "critical" |
| `payload_hash` | SHA-256 of the triggering input |
| `details` | JSON blob — structured event metadata (no raw PHI) |
| `detected_by` | "chartnav_internal", "watsonx_governance", "guardium" |
| `created_at` | Timestamp |

### Event Type Taxonomy

| Event Type | Description |
|---|---|
| `prompt_injection_attempt` | Input contained instruction override patterns |
| `jailbreak_attempt` | Input attempted to bypass safety or role constraints |
| `phi_leak_risk` | Output contained patterns matching PHI (SSN, DOB, MRN format) |
| `excessive_output_length` | Response exceeded expected bounds |
| `model_refusal` | Model refused to complete — logged for review |
| `policy_violation` | Output violated a configured ChartNav policy |
| `model_drift_alert` | Evaluation score dropped below threshold (placeholder) |

---

## Model Drift / Evaluation Placeholder

The `ai_model_registry` table includes a `notes` field for evaluation
summaries. A future `ai_model_evaluations` table (not yet built) will
hold structured RAGAS/ROUGE/embedding-similarity scores.

This is a **placeholder** — model drift detection is deferred to
Phase 2 (watsonx.governance integration).
