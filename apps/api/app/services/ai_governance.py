"""ChartNav AI Governance Layer.

In-memory record + helpers. No DB dependency lives here — persistence is
in `ai_governance_store`. This split keeps the security pipeline pure
(easy to unit-test) and keeps SQL concerns out of the security logic.

No raw PHI is ever stored. Only SHA-256 hashes of prompt/output and
event metadata that the caller has already scrubbed.

All records carry `organization_id` to prevent cross-tenant leakage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# --- Enums ---------------------------------------------------------------


class AIProvider(str, Enum):
    IBM_WATSONX = "ibm_watsonx"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    INTERNAL = "internal"


class AIUseCase(str, Enum):
    """Tracks the clinical or administrative purpose of an AI call."""
    CLINICAL_CHARTING = "clinical_charting"
    CONSULT_LETTER = "consult_letter"
    INTAKE_PROCESSING = "intake_processing"
    CODING_SUGGESTION = "coding_suggestion"
    IMAGING_SUMMARY = "imaging_summary"
    PATIENT_COMMUNICATION = "patient_communication"
    ADMINISTRATIVE_SUMMARY = "administrative_summary"
    SECURITY_ANALYSIS = "security_analysis"
    OTHER = "other"


class PHIRedactionStatus(str, Enum):
    NOT_CHECKED = "not_checked"
    CLEAN = "clean"
    REDACTED = "redacted"          # PHI stripped before send
    BLOCKED = "blocked"            # call aborted — unredactable PHI
    PHI_IN_PROMPT = "phi_in_prompt"  # PHI reached model; flagged post-hoc
    PHI_IN_OUTPUT = "phi_in_output"  # model returned PHI; flagged post-hoc


class HumanReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    WAIVED = "waived"              # low-risk only; must be explicit


class SecurityEventType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SUSPICIOUS_PROMPT = "suspicious_prompt"
    DATA_RISK = "data_risk"
    PHI_DETECTED = "phi_detected"
    OUTPUT_ANOMALY = "output_anomaly"
    RATE_ABUSE = "rate_abuse"
    ROLE_VIOLATION = "role_violation"
    ORG_SCOPE_VIOLATION = "org_scope_violation"
    UNSUPPORTED_AUTOMATION = "unsupported_automation"


# --- Record --------------------------------------------------------------


@dataclass
class AIGovernanceRecord:
    """In-memory representation of one AI-call audit row.

    Persistence is handled separately in `ai_governance_store`. The DB
    primary key is assigned on insert; until then `id` stays None.
    """

    organization_id: int
    model_id: str
    use_case: str = AIUseCase.OTHER.value
    provider: str = AIProvider.IBM_WATSONX.value
    prompt_hash: str = ""
    output_hash: str = ""
    phi_redaction_status: str = PHIRedactionStatus.NOT_CHECKED.value
    human_review_required: bool = True
    human_review_status: str = HumanReviewStatus.PENDING.value
    human_reviewer_id: Optional[int] = None
    human_review_timestamp: Optional[datetime] = None
    human_review_notes: Optional[str] = None
    security_events: list[dict[str, Any]] = field(default_factory=list)
    workflow_id: Optional[int] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    patient_identifier: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None


def _sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_governance_record(
    *,
    organization_id: int,
    prompt: str,
    output: str,
    model_id: str,
    use_case: AIUseCase = AIUseCase.OTHER,
    provider: AIProvider = AIProvider.IBM_WATSONX,
    workflow_id: Optional[int] = None,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    patient_identifier: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
) -> AIGovernanceRecord:
    """Construct an unsaved governance record from a completed AI call.

    organization_id is required — records without an org cannot exist.
    No raw prompt or output text is stored — only SHA-256 hashes.
    """
    if not organization_id:
        raise ValueError("organization_id is required for all AI governance records")

    return AIGovernanceRecord(
        organization_id=organization_id,
        provider=provider.value,
        model_id=model_id,
        use_case=use_case.value,
        prompt_hash=_sha256(prompt),
        output_hash=_sha256(output),
        workflow_id=workflow_id,
        user_id=user_id,
        session_id=session_id,
        patient_identifier=patient_identifier,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )


def append_security_event(
    record: AIGovernanceRecord,
    event_type: SecurityEventType,
    detail: str,
    severity: str = "medium",
) -> None:
    """Append an event to the record's security_events list.

    detail must not contain raw PHI — callers are responsible for
    sanitizing. High/critical events flip the record into a
    review-required state and unwaive a previously waived review.
    """
    record.security_events.append(
        {
            "event_id": str(uuid.uuid4()),
            "type": event_type.value,
            "detail": detail,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    if severity in ("high", "critical"):
        record.human_review_required = True
        if record.human_review_status == HumanReviewStatus.WAIVED.value:
            record.human_review_status = HumanReviewStatus.PENDING.value
