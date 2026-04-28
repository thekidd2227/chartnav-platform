"""AI Governance service — ChartNav internal scaffold.

Implements the internal AI governance layer:
  register_ai_use_case()        — register/idempotent use-case
  record_ai_output()            — write one AI output audit row
  record_human_review()         — record a reviewer decision
  record_security_event()       — log a security/threat event
  export_watsonx_governance_payload()     — JSON dict for IBM watsonx.governance
  export_guardium_ai_security_payload()   — JSON dict for Guardium AI Security

PHI policy
----------
Raw prompt text and raw AI output are NEVER passed into or stored by this
service. Callers must supply SHA-256 hashes and ≤200-char redacted previews.

No outbound IBM API calls are made here. Export helpers return JSON-ready
dicts only. External calls happen in a future integration layer controlled
by WATSONX_GOVERNANCE_ENABLED / GUARDIUM_AI_SECURITY_ENABLED config flags.

Sync pattern
------------
Follows the existing app.db sync conventions (transaction(), fetch_one(),
insert_returning_id(conn, table, values)). No async here.

See docs/security/ibm-watsonx-governance-plan.md
    docs/security/ai-governance-architecture.md
    docs/security/guardium-ai-security-roadmap.md
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.db import fetch_one, transaction

log = logging.getLogger("chartnav.ai_governance")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# register_ai_use_case
# ---------------------------------------------------------------------------

def register_ai_use_case(
    *,
    name: str,
    description: str,
    model_provider: str,
    model_name: str,
    phi_exposure: bool,
    output_type: str,
    requires_human_review: bool,
    clinical_disclaimer_required: bool,
) -> str:
    """Register an AI use-case (idempotent by name). Returns use_case_id."""
    with transaction() as conn:
        existing = conn.execute(
            text("SELECT use_case_id FROM ai_use_cases WHERE name = :name"),
            {"name": name},
        ).mappings().first()
        if existing:
            log.debug("ai_governance: use_case already registered: %s", name)
            return str(existing["use_case_id"])

        use_case_id = _new_id()
        conn.execute(
            text("""
                INSERT INTO ai_use_cases
                  (use_case_id, name, description, model_provider, model_name,
                   phi_exposure, output_type, requires_human_review,
                   clinical_disclaimer_required, active, created_at)
                VALUES
                  (:use_case_id, :name, :description, :model_provider, :model_name,
                   :phi_exposure, :output_type, :requires_human_review,
                   :clinical_disclaimer_required, 1, :created_at)
            """),
            {
                "use_case_id": use_case_id,
                "name": name,
                "description": description,
                "model_provider": model_provider,
                "model_name": model_name,
                "phi_exposure": int(phi_exposure),
                "output_type": output_type,
                "requires_human_review": int(requires_human_review),
                "clinical_disclaimer_required": int(clinical_disclaimer_required),
                "created_at": _now(),
            },
        )
    log.info("ai_governance: registered use_case '%s' (%s)", name, use_case_id)
    return use_case_id


# ---------------------------------------------------------------------------
# record_ai_output
# ---------------------------------------------------------------------------

def record_ai_output(
    *,
    org_id: str,
    user_id: str,
    use_case_id: str,
    model_provider: str,
    model_name: str,
    input_hash: str,
    output_hash: str,
    output_preview: str,
    phi_redacted: bool,
    clinical_disclaimer_shown: bool,
    latency_ms: int = 0,
    token_count_prompt: int = 0,
    token_count_completion: int = 0,
    encounter_id: str | None = None,
    prompt_template_id: str | None = None,
) -> str:
    """Record one AI output event to the audit trail. Returns audit_id.

    PHI contract: callers MUST NOT pass raw prompt text or raw AI output.
    Only SHA-256 hashes and ≤200-char non-PHI previews are stored.
    """
    audit_id = _new_id()
    with transaction() as conn:
        conn.execute(
            text("""
                INSERT INTO ai_output_audit
                  (audit_id, org_id, user_id, encounter_id, use_case_id,
                   model_provider, model_name, prompt_template_id,
                   input_hash, output_hash, output_preview,
                   phi_redacted, clinical_disclaimer_shown,
                   latency_ms, token_count_prompt, token_count_completion,
                   created_at)
                VALUES
                  (:audit_id, :org_id, :user_id, :encounter_id, :use_case_id,
                   :model_provider, :model_name, :prompt_template_id,
                   :input_hash, :output_hash, :output_preview,
                   :phi_redacted, :clinical_disclaimer_shown,
                   :latency_ms, :token_count_prompt, :token_count_completion,
                   :created_at)
            """),
            {
                "audit_id": audit_id,
                "org_id": org_id,
                "user_id": user_id,
                "encounter_id": encounter_id,
                "use_case_id": use_case_id,
                "model_provider": model_provider,
                "model_name": model_name,
                "prompt_template_id": prompt_template_id,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "output_preview": (output_preview or "")[:200],
                "phi_redacted": int(phi_redacted),
                "clinical_disclaimer_shown": int(clinical_disclaimer_shown),
                "latency_ms": latency_ms,
                "token_count_prompt": token_count_prompt,
                "token_count_completion": token_count_completion,
                "created_at": _now(),
            },
        )
    log.debug("ai_governance: output audit %s (org=%s)", audit_id, org_id)
    return audit_id


# ---------------------------------------------------------------------------
# record_human_review
# ---------------------------------------------------------------------------

def record_human_review(
    *,
    audit_id: str,
    org_id: str,
    reviewer_user_id: str,
    decision: str,
    notes: str | None = None,
) -> str:
    """Record a human review decision. decision: accepted|rejected|modified."""
    if decision not in {"accepted", "rejected", "modified"}:
        raise ValueError(f"decision must be accepted|rejected|modified, got {decision!r}")
    review_id = _new_id()
    with transaction() as conn:
        conn.execute(
            text("""
                INSERT INTO ai_human_reviews
                  (review_id, audit_id, org_id, reviewer_user_id,
                   decision, notes, reviewed_at)
                VALUES
                  (:review_id, :audit_id, :org_id, :reviewer_user_id,
                   :decision, :notes, :reviewed_at)
            """),
            {
                "review_id": review_id,
                "audit_id": audit_id,
                "org_id": org_id,
                "reviewer_user_id": reviewer_user_id,
                "decision": decision,
                "notes": notes,
                "reviewed_at": _now(),
            },
        )
    log.info("ai_governance: review %s → %s (audit=%s)", review_id, decision, audit_id)
    return review_id


# ---------------------------------------------------------------------------
# record_security_event
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = frozenset({
    "prompt_injection_attempt",
    "jailbreak_attempt",
    "phi_leak_risk",
    "excessive_output_length",
    "model_refusal",
    "policy_violation",
    "model_drift_alert",
})

VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


def record_security_event(
    *,
    org_id: str,
    event_type: str,
    severity: str,
    payload_hash: str,
    details: dict[str, Any],
    detected_by: str = "chartnav_internal",
    user_id: str | None = None,
) -> str:
    """Record an AI security event. Returns event_id.

    PHI contract: details dict MUST NOT contain raw PHI.
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"event_type {event_type!r} not in allowed set")
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"severity {severity!r} not in low|medium|high|critical")

    event_id = _new_id()
    with transaction() as conn:
        conn.execute(
            text("""
                INSERT INTO ai_security_events
                  (event_id, org_id, user_id, event_type, severity,
                   payload_hash, details, detected_by, created_at)
                VALUES
                  (:event_id, :org_id, :user_id, :event_type, :severity,
                   :payload_hash, :details, :detected_by, :created_at)
            """),
            {
                "event_id": event_id,
                "org_id": org_id,
                "user_id": user_id,
                "event_type": event_type,
                "severity": severity,
                "payload_hash": payload_hash,
                "details": json.dumps(details),
                "detected_by": detected_by,
                "created_at": _now(),
            },
        )
    log.warning(
        "ai_governance: security_event %s [%s/%s] org=%s",
        event_type, severity, event_id, org_id,
    )
    return event_id


# ---------------------------------------------------------------------------
# export_watsonx_governance_payload
# ---------------------------------------------------------------------------

def export_watsonx_governance_payload(
    *,
    use_case_id: str,
    use_case_name: str,
    model_provider: str,
    model_name: str,
    phi_exposure: bool,
    output_type: str,
    requires_human_review: bool,
    audit_sample: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build JSON-ready dict for IBM watsonx.governance.

    No outbound network call. Caller POSTs this when
    WATSONX_GOVERNANCE_ENABLED=true.
    """
    return {
        "source": "chartnav",
        "use_case_id": use_case_id,
        "use_case_name": use_case_name,
        "model": {"provider": model_provider, "name": model_name},
        "risk_indicators": {
            "phi_exposure": phi_exposure,
            "requires_human_review": requires_human_review,
            "output_type": output_type,
        },
        "audit_sample": audit_sample or [],
        "exported_at": _now(),
        "_note": (
            "Payload only. No IBM API call made. "
            "Set WATSONX_GOVERNANCE_ENABLED=true to activate."
        ),
    }


# ---------------------------------------------------------------------------
# export_guardium_ai_security_payload
# ---------------------------------------------------------------------------

def export_guardium_ai_security_payload(
    *,
    org_id: str,
    event_type: str,
    severity: str,
    use_case_name: str,
    payload_hash: str,
    details: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:
    """Build JSON-ready dict for IBM Guardium AI Security.

    No outbound network call. PHI contract: details MUST NOT contain raw PHI.
    """
    return {
        "source": "chartnav",
        "event_type": event_type,
        "severity": severity,
        "org_id": org_id,
        "user_id": user_id,
        "use_case": use_case_name,
        "payload_hash": payload_hash,
        "detected_at": _now(),
        "details": details,
        "_note": (
            "Payload only. No IBM API call made. "
            "Set GUARDIUM_AI_SECURITY_ENABLED=true to activate."
        ),
    }
