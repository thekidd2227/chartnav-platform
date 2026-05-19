"""ChartNav AI Security Pipeline.

Pure-logic module: PHI redaction, prompt-injection detection,
sensitive-data detection, hashing, and pre/post-call audit helpers.
No DB or HTTP concerns here.

Pre-call (callers MUST honor):
    result = preflight_ai_prompt(raw_prompt)
    if result.should_block:
        # do not call the model; record the blocked attempt
        ...
    redacted_prompt = result.redacted_prompt   # send this to the model

Post-call:
    audit_security_pipeline(record, redacted_prompt=..., raw_output=...)

`audit_security_pipeline` only audits — it does not block. Pre-call
blocking decisions are made by `preflight_ai_prompt` and must be
enforced by the caller before any provider request.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.ai_governance import (
    AIGovernanceRecord,
    HumanReviewStatus,
    PHIRedactionStatus,
    SecurityEventType,
    append_security_event,
)


# --- PHI patterns (HIPAA Safe Harbor) ----------------------------------
# Order matters: high-specificity patterns run before generic digit sweeps.

_PHI_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Structured identifiers — must precede generic digit patterns
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN"),
    (re.compile(r"\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"), "DOB_ISO"),
    (re.compile(r"\b(0[1-9]|1[0-2])[/\-](0[1-9]|[12]\d|3[01])[/\-](19|20)\d{2}\b"), "DOB_US"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "EMAIL"),
    # NPI before PHONE/MRN (avoids 10-digit NPI matching PHONE pattern)
    (re.compile(r"\bNPI[:\s#]*\d{10}\b", re.I), "NPI"),
    (re.compile(r"\b[A-Z]{2}\d{7}\b"), "DEA"),
    # URLs with personal paths (before generic digit sweep)
    (re.compile(r"https?://[^\s]+/(?:patient|user|member)/\d+", re.I), "PERSONAL_URL"),
    # PHONE: require formatted separators to avoid false-positives on long digit runs
    (
        re.compile(
            r"\b(?:\(?\d{3}\)?[\s.\-])\d{3}[\s.\-]\d{4}\b"
            r"|\+1[\s.\-]?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"
        ),
        "PHONE",
    ),
    (re.compile(r"\b\d{5}(?:-\d{4})?\b"), "ZIP"),
    (re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"), "CC_CANDIDATE"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "IP_ADDRESS"),
    # MRN — REQUIRES context. We deliberately do NOT flag bare 10–12 digit
    # numbers because clinical workflows are full of order numbers,
    # accession numbers, study IDs and timestamps that look identical.
    # Matched contexts: MRN | medical record [number] | chart number |
    # patient id[entifier].
    (
        re.compile(
            r"\b(?:MRN|medical\s+record(?:\s+(?:number|no\.?|#))?"
            r"|chart\s+(?:number|no\.?|#)"
            r"|patient\s+id(?:entifier)?)"
            r"[:\s#]*\d{6,12}\b",
            re.I,
        ),
        "MRN",
    ),
]

# --- Prompt injection signatures -----------------------------------------
#
# Order in this list controls which label is reported when only one
# pattern matches. When BOTH soft and hard patterns match the same input,
# `detect_prompt_injection` reports the first hard-block label so callers
# never see "should_block=False" because a soft pattern matched first.

# (pattern, label, is_hard_block)
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str, bool]] = [
    (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I), "instruction_override", False),
    (re.compile(r"disregard\s+(all|everything|prior)", re.I), "instruction_override", False),
    (re.compile(r"forget\s+(everything|all|your\s+rules)", re.I), "instruction_override", False),
    (re.compile(r"system\s+prompt", re.I), "system_prompt_probe", False),
    (re.compile(r"you\s+are\s+now\s+", re.I), "persona_hijack", False),
    (re.compile(r"act\s+as\s+if\s+", re.I), "persona_hijack", False),
    (re.compile(r"pretend\s+you\s+(are|have)", re.I), "persona_hijack", False),
    (re.compile(r"<\|.*?\|>"), "token_boundary", True),
    (re.compile(r"\[INST\]|\[/INST\]|\[SYSTEM\]", re.I), "llama_template_injection", True),
    (re.compile(r"jailbreak|\bDAN\b|do\s+anything\s+now", re.I), "jailbreak_attempt", True),
    (re.compile(r"repeat\s+(the\s+)?(above|previous|system)", re.I), "data_exfil_probe", True),
    (re.compile(r"#{2,}\s*(instruction|system|prompt|role)", re.I), "markdown_injection", False),
    (re.compile(r"export\s+all\s+(records|patient|data)", re.I), "bulk_exfil_attempt", True),
    (re.compile(r"bypass\s+(security|auth|review)", re.I), "security_bypass_attempt", True),
    (re.compile(r"skip\s+(human\s+)?review", re.I), "review_bypass_attempt", True),
    (re.compile(r"autonomous(ly)?\s+decid|self.approv", re.I), "unsupported_automation", False),
]

# --- Suspicious (non-injection) prompt patterns --------------------------

_SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\ball\s+patient\s+records\b", re.I), "bulk_record_request"),
    (re.compile(r"without\s+review", re.I), "no_review_request"),
    (re.compile(r"automatically\s+sign", re.I), "auto_sign_request"),
    (re.compile(r"delete\s+(all|every|patient)", re.I), "mass_delete_request"),
]


# --- Return types --------------------------------------------------------


@dataclass
class RedactionResult:
    text: str
    was_redacted: bool
    categories: list[str]


@dataclass
class InjectionResult:
    detected: bool
    should_block: bool
    matched_label: Optional[str] = None
    matched_labels: list[str] = field(default_factory=list)
    severity: str = "medium"


@dataclass
class SensitiveDataResult:
    detected: bool
    categories: list[str]


@dataclass
class SuspiciousPromptResult:
    detected: bool
    labels: list[str]


@dataclass
class PreflightResult:
    """Pre-call security verdict. Callers MUST honor `should_block`."""
    redacted_prompt: str
    should_block: bool
    blocked_reason: Optional[str]
    phi_categories: list[str]
    injection_label: Optional[str]
    suspicious_labels: list[str]


# --- Core detection functions -------------------------------------------


def redact_for_ai(text: str) -> RedactionResult:
    """Strip PHI from `text` before any AI provider call.

    Original text is never mutated. Returns scrubbed text + metadata.
    """
    redacted = text
    found_cats: list[str] = []
    for pattern, label in _PHI_PATTERNS:
        new_text = pattern.sub(f"[REDACTED:{label}]", redacted)
        if new_text != redacted:
            found_cats.append(label)
            redacted = new_text
    return RedactionResult(
        text=redacted,
        was_redacted=bool(found_cats),
        categories=found_cats,
    )


def detect_prompt_injection(text: str) -> InjectionResult:
    """Scan `text` for adversarial instruction patterns.

    Walks every pattern. If ANY hard-block pattern matches, the result is
    blocking — even if a soft pattern also matched. `matched_label` is
    the first hard-block label when present, otherwise the first soft.
    """
    soft_labels: list[str] = []
    hard_labels: list[str] = []
    for pattern, label, is_hard_block in _INJECTION_PATTERNS:
        if pattern.search(text):
            (hard_labels if is_hard_block else soft_labels).append(label)

    if not (soft_labels or hard_labels):
        return InjectionResult(detected=False, should_block=False, severity="none")

    all_labels = hard_labels + soft_labels
    primary = hard_labels[0] if hard_labels else soft_labels[0]
    return InjectionResult(
        detected=True,
        should_block=bool(hard_labels),
        matched_label=primary,
        matched_labels=all_labels,
        severity="critical" if hard_labels else "high",
    )


def detect_sensitive_data(text: str) -> SensitiveDataResult:
    """Inspect text for PHI categories. Used on prompts and outputs."""
    categories: list[str] = []
    for pattern, label in _PHI_PATTERNS:
        if pattern.search(text):
            categories.append(label)
    return SensitiveDataResult(detected=bool(categories), categories=categories)


def detect_suspicious_prompt(text: str) -> SuspiciousPromptResult:
    """Flag prompts that are not injections but indicate unusual intent."""
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


def sanitize_for_audit_detail(text: str, *, max_len: int = 500) -> str:
    """Scrub a free-text string before storing it in a security event detail.

    Used by every code path that accepts user-supplied detail strings.
    Returns the redacted text with a category-suffix marker when PHI was
    found. Truncates to `max_len` to bound storage. Raw PHI never persists.
    """
    if text is None:
        return ""
    cleaned = redact_for_ai(text)
    out = cleaned.text
    if cleaned.was_redacted:
        out = f"{out} [phi_categories={','.join(cleaned.categories)}]"
    if len(out) > max_len:
        out = out[:max_len] + "..."
    return out


# --- Pre-call gate -------------------------------------------------------


def preflight_ai_prompt(raw_prompt: str) -> PreflightResult:
    """Pre-call security gate. Callers MUST honor `should_block`.

    Returns:
      - redacted_prompt: the version safe to send to a model. PHI is
        replaced with [REDACTED:<category>] markers.
      - should_block: True if the call must be aborted.
      - blocked_reason: short reason string when blocked (label/category).
      - phi_categories, injection_label, suspicious_labels: metadata for
        audit events. Detail strings never include raw PHI.
    """
    redaction = redact_for_ai(raw_prompt)
    injection = detect_prompt_injection(raw_prompt)
    suspicious = detect_suspicious_prompt(raw_prompt)

    should_block = injection.should_block
    blocked_reason: Optional[str] = None
    if should_block:
        blocked_reason = f"injection:{injection.matched_label}"

    return PreflightResult(
        redacted_prompt=redaction.text,
        should_block=should_block,
        blocked_reason=blocked_reason,
        phi_categories=redaction.categories,
        injection_label=injection.matched_label,
        suspicious_labels=suspicious.labels,
    )


def record_blocked_call(
    record: AIGovernanceRecord,
    *,
    preflight: PreflightResult,
) -> AIGovernanceRecord:
    """Record that a pre-call check blocked an AI request.

    The model is never called, so output_hash stays empty. The record's
    review status is escalated and the matched injection label is stored
    as the blocking event detail (label only — never raw prompt text).
    """
    record.phi_redaction_status = (
        PHIRedactionStatus.REDACTED.value
        if preflight.phi_categories
        else PHIRedactionStatus.CLEAN.value
    )
    record.output_hash = ""
    append_security_event(
        record,
        SecurityEventType.PROMPT_INJECTION,
        f"Blocked at preflight: {preflight.blocked_reason or preflight.injection_label}",
        severity="critical",
    )
    record.human_review_required = True
    if record.human_review_status not in (
        HumanReviewStatus.APPROVED.value,
        HumanReviewStatus.ESCALATED.value,
    ):
        record.human_review_status = HumanReviewStatus.ESCALATED.value
    return record


# --- Post-call audit ----------------------------------------------------


def require_human_review(
    record: AIGovernanceRecord,
    *,
    reason: str = "clinical_ai_output",
) -> AIGovernanceRecord:
    """Mark `record` as requiring human review and set status to PENDING.

    Idempotent. Does not override APPROVED or ESCALATED statuses.
    """
    record.human_review_required = True
    if record.human_review_status not in (
        HumanReviewStatus.APPROVED.value,
        HumanReviewStatus.ESCALATED.value,
    ):
        record.human_review_status = HumanReviewStatus.PENDING.value
    return record


def record_ai_security_event(
    record: AIGovernanceRecord,
    event_type: SecurityEventType,
    detail: str,
    severity: str = "medium",
) -> AIGovernanceRecord:
    """Append a named security event to the record's JSON event log.

    Detail is auto-scrubbed via `sanitize_for_audit_detail` so caller
    bugs cannot leak raw PHI into the event log. High/critical events
    escalate the human-review status.
    """
    append_security_event(record, event_type, sanitize_for_audit_detail(detail), severity)
    return record


def audit_security_pipeline(
    record: AIGovernanceRecord,
    *,
    raw_prompt: str,
    raw_output: str,
    redacted_prompt: Optional[str] = None,
) -> AIGovernanceRecord:
    """Post-call audit. Mutates `record` in place. Does NOT block.

    Pre-call blocking is the responsibility of `preflight_ai_prompt` and
    its callers. This function records what happened around a completed
    AI call:
      - if `redacted_prompt` is provided AND differs from `raw_prompt`,
        status is REDACTED (PHI was scrubbed before send).
      - if PHI is detected in raw_prompt anyway (e.g. caller forgot to
        send the redacted version), status is PHI_IN_PROMPT.
      - if PHI is detected in raw_output, status is PHI_IN_OUTPUT.
      - clean both ways: CLEAN.
      - human_review_required = True (always for clinical AI).
    """

    prompt_phi = detect_sensitive_data(raw_prompt)
    if prompt_phi.detected:
        record_ai_security_event(
            record,
            SecurityEventType.PHI_DETECTED,
            f"PHI categories in prompt: {prompt_phi.categories}",
            severity="high",
        )
        record.phi_redaction_status = PHIRedactionStatus.PHI_IN_PROMPT.value

    injection = detect_prompt_injection(raw_prompt)
    if injection.detected:
        record_ai_security_event(
            record,
            SecurityEventType.PROMPT_INJECTION,
            f"Pattern: {injection.matched_label}",
            severity=injection.severity,
        )

    suspicious = detect_suspicious_prompt(raw_prompt)
    if suspicious.detected:
        record_ai_security_event(
            record,
            SecurityEventType.SUSPICIOUS_PROMPT,
            f"Suspicious intents: {suspicious.labels}",
            severity="medium",
        )

    output_phi = detect_sensitive_data(raw_output)
    if output_phi.detected:
        record_ai_security_event(
            record,
            SecurityEventType.DATA_RISK,
            f"PHI categories in AI output: {output_phi.categories}",
            severity="high",
        )
        if record.phi_redaction_status != PHIRedactionStatus.PHI_IN_PROMPT.value:
            record.phi_redaction_status = PHIRedactionStatus.PHI_IN_OUTPUT.value

    if not prompt_phi.detected and not output_phi.detected:
        # Nothing made it past the redaction layer. If the caller
        # explicitly redacted before send, mark REDACTED to credit the
        # mitigation; otherwise CLEAN.
        if redacted_prompt is not None and redacted_prompt != raw_prompt:
            record.phi_redaction_status = PHIRedactionStatus.REDACTED.value
        else:
            record.phi_redaction_status = PHIRedactionStatus.CLEAN.value

    require_human_review(record, reason="clinical_ai_output")
    return record
