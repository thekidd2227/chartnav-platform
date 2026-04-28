# IBM watsonx Governance — ChartNav Integration Plan

**Status:** Pre-integration planning (no paid IBM calls active) **Last updated:** 2026-04-27 **Author:** ChartNav Platform Team / ARCG Systems

---

## Executive Summary

ChartNav uses AI at multiple points in the clinical workflow: note generation, clinical coding assistance, intake summarisation, and post-visit summaries. Each of these touches PHI-adjacent context and produces output that clinicians rely on. This document defines which IBM products to use, when, and in what order.

**No IBM production integration is live yet.** All scaffolding is configuration-flag gated (`WATSONX_GOVERNANCE_ENABLED=false`).

---

## Product Comparison

ProductWhat It DoesChartNav Fit**watsonx.governance**AI lifecycle governance: model registry, risk scoring, bias detection, audit trails, regulatory fact-sheets✅ **Primary target** — governs third-party models (OpenAI, Anthropic) ChartNav already calls[**watsonx.ai**](http://watsonx.ai)IBM-hosted model inference (Granite, Llama, etc.)⏸ Defer — ChartNav uses OpenAI/Anthropic; switch only if IBM inference is required**watsonx.data**Governed data lakehouse❌ Not relevant — ChartNav is a transactional clinical app, not a data warehouse**Guardium AI Security**Runtime AI security: prompt injection detection, jailbreak monitoring, data-leakage policy enforcement⏸ Later — enterprise layer once governance baseline is established

---

## Recommended Plan

### Phase 1 — NOW (free, no IBM account required)

Build the internal governance architecture ChartNav needs regardless of vendor:

- AI use-case inventory
- Model/provider registry
- Prompt/template registry
- Output audit trail
- Human review tracking
- PHI redaction status
- Security event log (prompt injection, jailbreak attempts)

All of this is implemented in `apps/api/app/services/ai_governance.py`and the corresponding DB tables. It is vendor-neutral and works today.

### Phase 2 — watsonx.governance Lite/Essentials

**Trigger:** When ChartNav has a compliance conversation with a health system customer that requires third-party AI governance attestation.

**IBM plan:** Start with **Lite** (free tier) or **Essentials**. Do NOT start with Standard or Premium.

**What it adds over Phase 1:**

- IBM-issued model fact-sheets (regulators recognise IBM branding)
- Automated bias/drift alerts from IBM's evaluation engine
- A compliance dashboard that non-technical compliance officers can read

**Integration path:**

1. Set `WATSONX_GOVERNANCE_ENABLED=true`
2. Set `WATSONX_GOVERNANCE_BASE_URL` and `WATSONX_GOVERNANCE_API_KEY`
3. Call `export_watsonx_governance_payload()` from `ai_governance.py`and POST to IBM's `/v1/use_cases` endpoint

### Phase 3 — Guardium AI Security

**Trigger:** ChartNav is deployed in a health system with &gt;500 clinicians OR a security audit requires runtime AI threat monitoring.

**What it adds:**

- Real-time prompt injection detection with policy enforcement
- Jailbreak attempt classification
- Sensitive data leakage alerts before responses leave the API

**Integration path:**

1. Set `GUARDIUM_AI_SECURITY_ENABLED=true`
2. Route AI output through Guardium's inspection proxy or API
3. Call `export_guardium_ai_security_payload()` from `ai_governance.py`

---

## What NOT to Buy

ProductReason to skip now[watsonx.ai](http://watsonx.ai) inferenceChartNav uses OpenAI/Anthropic — no reason to migrate model hostingwatsonx.dataIrrelevant to a transactional clinical appGuardium for databasesChartNav's PHI is in SQLite/Postgres — standard DB encryption handles thisIBM Security VerifyAuth is handled by ChartNav's own JWT/header systemFull watsonx.governance Standard/PremiumPriced for enterprise; Essentials is sufficient for early compliance conversations

---

## Claims This Document Does NOT Make

- ChartNav is NOT HIPAA certified by IBM
- ChartNav does NOT have a partnership with IBM
- No watsonx production monitoring is active
- No Guardium instance is deployed
- No ONC certification is implied by this plan
