"""
ChartNav AI Governance Layer — v2
Provider: IBM watsonx (primary)
Append-only audit log. No raw PHI stored.
All records are org-scoped to prevent cross-tenant leakage.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ── Enums ─────────────────────────────────────────────────────────────────────

class AIProvider(str, Enum):
    IBM_WATSONX = "ibm_watsonx"
    OPENAI      = "openai"
    ANTHROPIC   = "anthropic"
    INTERNAL    = "internal"


class AIUseCase(str, Enum):
    """Tracks the clinical or administrative purpose of an AI call."""
    CLINICAL_CHARTING        = "clinical_charting"
    CONSULT_LETTER           = "consult_letter"
    INTAKE_PROCESSING        = "intake_processing"
    CODING_SUGGESTION        = "coding_suggestion"
    IMAGING_SUMMARY          = "imaging_summary"
    PATIENT_COMMUNICATION    = "patient_communication"
    ADMINISTRATIVE_SUMMARY   = "administrative_summary"
    SECURITY_ANALYSIS        = "security_analysis"
    OTHER                    = "other"


class PHIRedactionStatus(str, Enum):
    NOT_CHECKED   = "not_checked"
    CLEAN         = "clean"
    REDACTED      = "redacted"       # PHI stripped before send
    BLOCKED       = "blocked"        # Call aborted — unredactable PHI
    PHI_IN_PROMPT = "phi_in_prompt"  # PHI reached model; flagged post-hoc
    PHI_IN_OUTPUT = "phi_in_output"  # Model returned PHI; flagged post-hoc


class HumanReviewStatus(str, Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    ESCALATED = "escalated"
    WAIVED    = "waived"             # Low-risk calls only; must be explicit


class SecurityEventType(str, Enum):
    PROMPT_INJECTION       = "prompt_injection"
    SUSPICIOUS_PROMPT      = "suspicious_prompt"
    DATA_RISK              = "data_risk"
    PHI_DETECTED           = "phi_detected"
    OUTPUT_ANOMALY         = "output_anomaly"
    RATE_ABUSE             = "rate_abuse"
    ROLE_VIOLATION         = "role_violation"
    ORG_SCOPE_VIOLATION    = "org_scope_violation"
    UNSUPPORTED_AUTOMATION = "unsupported_automation"


# ── ORM ──────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class AIGovernanceRecord(Base):
    """
    Immutable audit log row written for every AI call.
    Append-only. Never updated except for human_review fields.
    All records carry org_id for multi-tenant isolation.
    """
    __tablename__ = "ai_governance_log"

    # ── Identity ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # ── Org scoping (required — no cross-org reads permitted) ─────────────
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # ── Provider / model tracking ─────────────────────────────────────────
    provider: Mapped[str] = mapped_column(
        SAEnum(AIProvider), nullable=False, default=AIProvider.IBM_WATSONX
    )
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # e.g. "ibm/granite-13b-chat-v2", "ibm/granite-20b-multilingual"

    # ── Use-case inventory ────────────────────────────────────────────────
    use_case: Mapped[str] = mapped_column(
        SAEnum(AIUseCase), nullable=False, default=AIUseCase.OTHER
    )

    # ── Request fingerprinting (SHA-256, no raw text stored) ─────────────
    prompt_hash:  Mapped[str] = mapped_column(String(64), nullable=False, default="")
    output_hash:  Mapped[str] = mapped_column(String(64), nullable=False, default="")

    # ── PHI protection ────────────────────────────────────────────────────
    phi_redaction_status: Mapped[str] = mapped_column(
        SAEnum(PHIRedactionStatus),
        nullable=False,
        default=PHIRedactionStatus.NOT_CHECKED,
    )

    # ── Human review gate ─────────────────────────────────────────────────
    human_review_required: Mapped[bool]   = mapped_column(Boolean, nullable=False, default=True)
    human_review_status:   Mapped[str]    = mapped_column(
        SAEnum(HumanReviewStatus), nullable=False, default=HumanReviewStatus.PENDING
    )
    human_reviewer_id:        Mapped[Optional[str]]      = mapped_column(String(36),   nullable=True)
    human_review_timestamp:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    human_review_notes:       Mapped[Optional[str]]      = mapped_column(Text, nullable=True)

    # ── Security event log (append-only JSON array) ───────────────────────
    security_events: Mapped[list[dict]] = mapped_column(JSON, default=list)

    # ── Workflow / session context ─────────────────────────────────────────
    workflow_id:  Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    user_id:      Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    session_id:   Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    patient_id:   Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # Note: patient_id is a foreign key reference only — no raw patient data stored here

    # ── Token / latency telemetry ──────────────────────────────────────────
    prompt_tokens:     Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms:        Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AIGovernanceRecord id={self.id[:8]} "
            f"org={self.org_id[:8]} "
            f"use_case={self.use_case} "
            f"review={self.human_review_status}>"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_governance_record(
    *,
    org_id:       str,
    prompt:       str,
    output:       str,
    model_id:     str,
    use_case:     AIUseCase = AIUseCase.OTHER,
    provider:     AIProvider = AIProvider.IBM_WATSONX,
    workflow_id:  Optional[str] = None,
    user_id:      Optional[str] = None,
    session_id:   Optional[str] = None,
    patient_id:   Optional[str] = None,
    prompt_tokens:     Optional[int] = None,
    completion_tokens: Optional[int] = None,
    latency_ms:        Optional[int] = None,
) -> AIGovernanceRecord:
    """
    Construct an unsaved governance record from a completed AI call.
    org_id is required — records without an org cannot be created.
    No raw prompt or output text is stored — only SHA-256 hashes.
    """
    if not org_id:
        raise ValueError("org_id is required for all AI governance records")

    return AIGovernanceRecord(
        org_id=org_id,
        provider=provider,
        model_id=model_id,
        use_case=use_case,
        prompt_hash=_sha256(prompt),
        output_hash=_sha256(output),
        workflow_id=workflow_id,
        user_id=user_id,
        session_id=session_id,
        patient_id=patient_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )


def append_security_event(
    record:     AIGovernanceRecord,
    event_type: SecurityEventType,
    detail:     str,
    severity:   str = "medium",
) -> None:
    """
    Append an event to the record's security_events JSON array.
    detail must not contain raw PHI — callers are responsible.
    """
    events: list[dict[str, Any]] = list(record.security_events or [])
    events.append(
        {
            "event_id":  str(uuid.uuid4()),
            "type":      event_type.value,
            "detail":    detail,
            "severity":  severity,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    record.security_events = events

    if severity in ("high", "critical"):
        record.human_review_required = True
        if record.human_review_status == HumanReviewStatus.WAIVED:
            record.human_review_status = HumanReviewStatus.PENDING
