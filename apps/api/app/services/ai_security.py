"""
ChartNav AI Security Pipeline — v2
Provider: IBM watsonx (primary)

Pipeline order (pre-call):
  1. redact_for_ai(raw_prompt)
  2. detect_prompt_injection(clean_prompt)   → abort if hard-block
  3. detect_sensitive_data(clean_prompt)     → flag / log
  4. hash_prompt(clean_prompt)

Pipeline order (post-call):
  5. hash_output(raw_output)
  6. detect_sensitive_data(raw_output)       → flag / log
  7. require_human_review(record)
  8. record_ai_security_event(record, ...)
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .ai_governance import (
    AIGovernanceRecord,
    HumanReviewStatus,
    PHIRedactionStatus,
    SecurityEventType,
    append_security_event,
)

# ── PHI patterns (HIPAA Safe Harbor — 18 identifiers) ───────────────────────
# Ordering matters: high-specificity patterns run before generic digit sweeps.

_PHI_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Structured identifiers — must precede generic digit patterns
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                     "SSN"),
    (re.compile(r"\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"), "DOB_ISO"),
    (re.compile(r"\b(0[1-9]|1[0-2])[/\-](0[1-9]|[12]\d|3[01])[/\-](19|20)\d{2}\b"), "DOB_US"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),     "EMAIL"),
    # NPI and DEA before PHONE/MRN (avoids 10-digit NPI matching PHONE pattern)
    (re.compile(r"\bNPI[:\s#]*\d{10}\b", re.I),                                 "NPI"),
    (re.compile(r"\b[A-Z]{2}\d{7}\b"),                                          "DEA"),
    # URLs with personal paths (before generic digit sweep)
    (re.compile(r"https?://[^\s]+/(?:patient|user|member)/\d+", re.I),           "PERSONAL_URL"),
    # PHONE: require formatted separators to avoid false-positive on NPI/MRN digits
    (re.compile(r"\b(?:\(?\d{3}\)?[\s.\-])\d{3}[\s.\-]\d{4}\b|\+1[\s.\-]?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"), "PHONE"),
    (re.compile(r"\b\d{5}(?:-\d{4})?\b"),                                      "ZIP"),
    (re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),                            "CC_CANDIDATE"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),                              "IP_ADDRESS"),
    # Generic long-digit catch-all — must be last
    (re.compile(r"\b\d{10,12}\b"),                                              "MRN_CANDIDATE"),
]

# ── Prompt injection signatures ──────────────────────────────────────────────

_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str, bool]] = [
    # (pattern, label, is_hard_block)
    (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),          "instruction_override",      False),
    (re.compile(r"disregard\s+(all|everything|prior)",         re.I),          "instruction_override",      False),
    (re.compile(r"forget\s+(everything|all|your\s+rules)",     re.I),          "instruction_override",      False),
    (re.compile(r"system\s+prompt",                            re.I),          "system_prompt_probe",       False),
    (re.compile(r"you\s+are\s+now\s+",                        re.I),          "persona_hijack",            False),
    (re.compile(r"act\s+as\s+if\s+",                          re.I),          "persona_hijack",            False),
    (re.compile(r"pretend\s+you\s+(are|have)",                re.I),          "persona_hijack",            False),
    (re.compile(r"<\|.*?\|>"),                                                  "token_boundary",            True),
    (re.compile(r"\[INST\]|\[/INST\]|\[SYSTEM\]",             re.I),          "llama_template_injection",  True),
    (re.compile(r"jailbreak|DAN\b|do\s+anything\s+now",       re.I),          "jailbreak_attempt",         True),
    (re.compile(r"repeat\s+(the\s+)?(above|previous|system)", re.I),          "data_exfil_probe",          True),
    (re.compile(r"#{2,}\s*(instruction|system|prompt|role)",   re.I),          "markdown_injection",        False),
    (re.compile(r"export\s+all\s+(records|patient|data)",     re.I),          "bulk_exfil_attempt",        True),
    (re.compile(r"bypass\s+(security|auth|review)",           re.I),          "security_bypass_attempt",   True),
    (re.compile(r"skip\s+(human\s+)?review",                  re.I),          "review_bypass_attempt",     True),
    (re.compile(r"autonomous(ly)?\s+decid|self.approv",       re.I),          "unsupported_automation",    False),
]

# ── Suspicious (non-injection) prompt patterns ───────────────────────────────

_SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\ball\s+patient\s+records\b",               re.I),          "bulk_record_request"),
    (re.compile(r"without\s+review",                          re.I),          "no_review_request"),
    (re.compile(r"automatically\s+sign",                      re.I),          "auto_sign_request"),
    (re.compile(r"delete\s+(all|every|patient)",              re.I),          "mass_delete_request"),
]


# ── Return types ─────────────────────────────────────────────────────────────

@dataclass
class RedactionResult:
    text:         str
    was_redacted: bool
    categories:   list[str]


@dataclass
class InjectionResult:
    detected:      bool
    should_block:  bool
    matched_label: Optional[str] = None
    severity:      str = "medium"


@dataclass
class SensitiveDataResult:
    detected:   bool
    categories: list[str]


@dataclass
class SuspiciousPromptResult:
    detected: bool
    labels:   list[str]


# ── Core functions ────────────────────────────────────────────────────────────

def redact_for_ai(text: str) -> RedactionResult:
    """
    Strip PHI from *text* before any AI provider call.
    Original text is never mutated. Returns scrubbed text + metadata.
    """
    redacted       = text
    found_cats: list[str] = []
    for pattern, label in _PHI_PATTERNS:
        new_text = pattern.sub(f"[REDACTED:{label}]", redacted)
        if new_text != redacted:
            found_cats.append(label)
            redacted = new_text
    return RedactionResult(text=redacted, was_redacted=bool(found_cats), categories=found_cats)


def detect_prompt_injection(text: str) -> InjectionResult:
    """
    Scan *text* for adversarial instruction patterns.
    Hard-block patterns abort the call; soft patterns are logged only.
    """
    for pattern, label, is_hard_block in _INJECTION_PATTERNS:
        if pattern.search(text):
            return InjectionResult(
                detected=True,
                should_block=is_hard_block,
                matched_label=label,
                severity="critical" if is_hard_block else "high",
            )
    return InjectionResult(detected=False, should_block=False, severity="none")


def detect_sensitive_data(text: str) -> SensitiveDataResult:
    """
    Inspect AI output for PHI that should not have been returned.
    Also usable on prompts as a secondary scan.
    """
    categories: list[str] = []
    for pattern, label in _PHI_PATTERNS:
        if pattern.search(text):
            categories.append(label)
    return SensitiveDataResult(detected=bool(categories), categories=categories)


def detect_suspicious_prompt(text: str) -> SuspiciousPromptResult:
    """
    Flag prompts that are not injections but indicate unusual intent.
    """
    labels: list[str] = []
    for pattern, label in _SUSPICIOUS_PATTERNS:
        if pattern.search(text):
            labels.append(label)
    return SuspiciousPromptResult(detected=bool(labels), labels=labels)


def hash_prompt(prompt: str) -> str:
    """SHA-256 hex digest of the (already-redacted) prompt. Never store raw."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def hash_output(output: str) -> str:
    """SHA-256 hex digest of the AI output before any transformation."""
    return hashlib.sha256(output.encode("utf-8")).hexdigest()


def require_human_review(
    record: AIGovernanceRecord,
    *,
    reason: str = "clinical_ai_output",
) -> AIGovernanceRecord:
    """
    Mark *record* as requiring human review and set status to PENDING.
    Idempotent — calling multiple times is safe.
    """
    record.human_review_required = True
    if record.human_review_status not in (
        HumanReviewStatus.APPROVED,
        HumanReviewStatus.ESCALATED,
    ):
        record.human_review_status = HumanReviewStatus.PENDING
    return record


def record_ai_security_event(
    record: AIGovernanceRecord,
    event_type: SecurityEventType,
    detail: str,
    severity: str = "medium",
) -> AIGovernanceRecord:
    """
    Append a named security event to the governance record's JSON log.
    Escalates human review automatically for high/critical events.
    Does NOT store raw PHI in the detail field — callers must redact first.
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
        if record.human_review_status not in (HumanReviewStatus.ESCALATED,):
            record.human_review_status = HumanReviewStatus.PENDING

    return record


# ── Full enforcement pipeline ─────────────────────────────────────────────────

def enforce_security_pipeline(
    record: AIGovernanceRecord,
    *,
    raw_prompt: str,
    raw_output: str,
) -> AIGovernanceRecord:
    """
    Complete pre/post call security audit.  Mutates *record* in place.
    Caller persists.

    Steps:
      1. PHI scan on prompt
      2. Injection scan on prompt
      3. Suspicious prompt scan
      4. PHI scan on output
      5. Finalise phi_redaction_status
      6. human_review_required = True (always for clinical AI)
    """

    # ── Step 1: PHI in prompt ────────────────────────────────────────────
    prompt_phi = detect_sensitive_data(raw_prompt)
    if prompt_phi.detected:
        record = record_ai_security_event(
            record,
            SecurityEventType.PHI_DETECTED,
            f"PHI categories in prompt (no raw values stored): {prompt_phi.categories}",
            severity="high",
        )
        record.phi_redaction_status = PHIRedactionStatus.PHI_IN_PROMPT

    # ── Step 2: Injection ─────────────────────────────────────────────────
    injection = detect_prompt_injection(raw_prompt)
    if injection.detected:
        record = record_ai_security_event(
            record,
            SecurityEventType.PROMPT_INJECTION,
            f"Pattern: {injection.matched_label}",
            severity=injection.severity,
        )

    # ── Step 3: Suspicious prompt (non-injection) ─────────────────────────
    suspicious = detect_suspicious_prompt(raw_prompt)
    if suspicious.detected:
        record = record_ai_security_event(
            record,
            SecurityEventType.SUSPICIOUS_PROMPT,
            f"Suspicious intents: {suspicious.labels}",
            severity="medium",
        )

    # ── Step 4: PHI in output ─────────────────────────────────────────────
    output_phi = detect_sensitive_data(raw_output)
    if output_phi.detected:
        record = record_ai_security_event(
            record,
            SecurityEventType.DATA_RISK,
            f"PHI categories in AI output (no raw values stored): {output_phi.categories}",
            severity="high",
        )
        if record.phi_redaction_status != PHIRedactionStatus.PHI_IN_PROMPT:
            record.phi_redaction_status = PHIRedactionStatus.PHI_IN_OUTPUT

    # ── Step 5: Set clean if nothing found ───────────────────────────────
    if not prompt_phi.detected and not output_phi.detected:
        record.phi_redaction_status = PHIRedactionStatus.CLEAN

    # ── Step 6: Always require human review for clinical AI ───────────────
    record = require_human_review(record, reason="clinical_ai_output")

    return record
