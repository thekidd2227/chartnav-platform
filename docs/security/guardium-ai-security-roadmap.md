# Guardium AI Security — ChartNav Roadmap

**Status:** NOT deployed. Planning document only. **Last updated:** 2026-04-27

---

## What Guardium AI Security Is

IBM Guardium AI Security is a runtime AI threat monitoring platform. It sits between your application and your AI provider and:

- Detects prompt injection attempts in real time
- Classifies jailbreak patterns before they reach the model
- Flags sensitive data leakage in AI outputs
- Enforces configurable security policies per use-case

It is distinct from watsonx.governance (which handles lifecycle/compliance) and [watsonx.ai](http://watsonx.ai) (which handles model inference).

---

## When ChartNav Should Activate Guardium

Guardium is an enterprise product with enterprise pricing. Activate it when:

1. ChartNav is deployed in a health system with &gt;500 active clinicians, OR
2. A security audit or enterprise sales requirement demands runtime AI threat monitoring attestation, OR
3. The internal security event log (`ai_security_events` table) shows a pattern of prompt injection or jailbreak attempts in production.

Do NOT activate Guardium for early-stage or mid-market deployments. The internal security event log (already implemented) is sufficient.

---

## Integration Architecture (When Ready)

```
ChartNav API → ai_governance.export_guardium_ai_security_payload()
             → POST https://<GUARDIUM_AI_SECURITY_BASE_URL>/v1/events
             ← Response: { threat_score, policy_decision, event_id }
```

### Environment variables (already added to [config.py](http://config.py), gated false)

```
GUARDIUM_AI_SECURITY_ENABLED=false     # flip to true when ready
GUARDIUM_AI_SECURITY_BASE_URL=         # Guardium instance endpoint
GUARDIUM_AI_SECURITY_API_KEY=          # IBM API key with Guardium scope
```

### What export_guardium_ai_security_payload() returns

```json
{
  "source": "chartnav",
  "event_type": "prompt_injection_attempt",
  "severity": "high",
  "org_id": "org-uuid",
  "user_id": "user-uuid",
  "use_case": "clinical_note_generation",
  "payload_hash": "sha256:...",
  "detected_at": "2026-04-27T21:00:00Z",
  "details": {
    "pattern_matched": "ignore previous instructions",
    "input_length_tokens": 412
  }
}
```

No raw PHI is included in the payload. Only hashes and metadata.

---

## What Guardium Does NOT Replace

Replaced?Item❌ NoChartNav's internal `ai_security_events` audit log❌ Nowatsonx.governance lifecycle tracking❌ NoHIPAA BAA with IBM (requires separate agreement)❌ NoChartNav's PHI redaction pipeline❌ NoInput validation in the FastAPI layer

---

## Procurement Path

1. Contact IBM via [cloud.ibm.com](http://cloud.ibm.com) → Guardium AI Security
2. Request a Lite or 30-day trial
3. Obtain `GUARDIUM_AI_SECURITY_BASE_URL` and `GUARDIUM_AI_SECURITY_API_KEY`
4. Flip `GUARDIUM_AI_SECURITY_ENABLED=true`
5. Deploy and monitor `ai_security_events` for `detected_by=guardium` rows

---

## Claims This Document Does NOT Make

- Guardium is NOT deployed
- ChartNav does NOT have a Guardium license
- No IBM partnership exists
- No runtime AI threat monitoring is active
- This roadmap does not constitute HIPAA compliance
