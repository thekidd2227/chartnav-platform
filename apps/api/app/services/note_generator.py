"""Note-drafting pipeline — the ChartNav wedge seam.

This module is the **one place** a real LLM plugs in. Today it ships a
deterministic fixture generator so the full encounter-to-signoff
workflow can be exercised end-to-end without an inference service:

    generate_draft_from_input(input_row, encounter_row)
      → (findings_dict, note_text, missing_flags)

Contract:
- Input: a raw `encounter_inputs` row (with `transcript_text`) plus
  the owning `encounters` row for context (patient id, provider name).
- Output:
    findings_dict  — JSON-serializable extraction dict whose top-level
                     shape matches `extracted_findings` columns + a
                     nested `structured_json` payload.
    note_text      — the narrative draft (SOAP format by default).
    missing_flags  — ordered list of string codes the provider must
                     verify before signing (e.g. ``"iop_missing"``).

The fake is intentionally transparent:
- regex-extracts obvious ophthalmology vocabulary (acuity, IOP, CC).
- never fabricates concrete values that weren't in the transcript.
- emits honest ``<missing>`` placeholders + a missing-data flag when
  a field was not mentioned, so the provider signoff UI can require
  review before sign.
- deterministic → safe for tests, no flake.

Replace `_run_generator` with a real LLM call when you wire one.
Keep the output contract identical.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Patterns for cheap, honest extraction from a transcript.
# ---------------------------------------------------------------------------

# Visual acuity: "OD 20/20", "OS 20/40 +2", "visual acuity right 20/30"
_VA_OD = re.compile(
    r"\b(?:OD|right(?:\s+eye)?|VA\s*OD|acuity\s+(?:od|right))\s*[:\-]?\s*"
    r"(20/\d{2,3}(?:\s*[+\-]\d+)?)",
    re.IGNORECASE,
)
_VA_OS = re.compile(
    r"\b(?:OS|left(?:\s+eye)?|VA\s*OS|acuity\s+(?:os|left))\s*[:\-]?\s*"
    r"(20/\d{2,3}(?:\s*[+\-]\d+)?)",
    re.IGNORECASE,
)

# Intraocular pressure: "IOP 15/17", "IOP OD 14 mmHg", "pressure 18 left"
_IOP_OD = re.compile(
    r"\bIOP\s*(?:OD|right)?\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)\s*(?:mm\s*Hg|mmHg)?",
    re.IGNORECASE,
)
_IOP_OS = re.compile(
    r"\bIOP\s*(?:OS|left)?\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)\s*(?:mm\s*Hg|mmHg)?",
    re.IGNORECASE,
)
# "IOP 15/17" — slash shorthand for OD/OS
_IOP_SLASH = re.compile(r"\bIOP\s*[:\-]?\s*(\d{1,2})\s*/\s*(\d{1,2})\b", re.IGNORECASE)

# Chief complaint
_CC = re.compile(
    r"\b(?:chief\s+complaint|cc)\s*[:\-]\s*([^\n.]+)", re.IGNORECASE
)

# Diagnoses — we don't invent ICD codes. Flag whatever the transcript
# literally says after "diagnosis" / "impression" / "assessment".
_DX_LINE = re.compile(
    r"\b(?:diagnos[ie]s?|impression|assessment)\s*[:\-]\s*([^\n]+)",
    re.IGNORECASE,
)

_MEDS_LINE = re.compile(
    r"\b(?:medication[s]?|rx|drops)\s*[:\-]\s*([^\n]+)",
    re.IGNORECASE,
)

_PLAN_LINE = re.compile(r"\bplan\s*[:\-]\s*([^\n]+)", re.IGNORECASE)

_FOLLOW_UP = re.compile(
    r"\b(?:follow[\s-]*up|rto|return)\s*(?:in\s+)?"
    r"(\d+\s*(?:day|week|month|year)s?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenerationResult:
    findings: dict[str, Any]     # matches extracted_findings shape + structured_json
    note_text: str               # narrative draft
    missing_flags: list[str]     # provider-must-verify codes


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def _split_list(raw: str) -> list[str]:
    parts = re.split(r"[;,]| and ", raw)
    return [p.strip() for p in parts if p.strip()]


def _extract(transcript: str) -> dict[str, Any]:
    t = transcript or ""

    va_od = _VA_OD.search(t)
    va_os = _VA_OS.search(t)
    iop_od = _IOP_OD.search(t)
    iop_os = _IOP_OS.search(t)
    iop_slash = _IOP_SLASH.search(t)
    cc = _CC.search(t)
    dx = _DX_LINE.search(t)
    meds = _MEDS_LINE.search(t)
    plan = _PLAN_LINE.search(t)
    follow = _FOLLOW_UP.search(t)

    out: dict[str, Any] = {
        "chief_complaint": cc.group(1).strip() if cc else None,
        "visual_acuity_od": va_od.group(1) if va_od else None,
        "visual_acuity_os": va_os.group(1) if va_os else None,
        "iop_od": iop_od.group(1) if iop_od else None,
        "iop_os": iop_os.group(1) if iop_os else None,
    }
    # IOP slash shorthand overrides per-eye regex if the per-eye ones
    # accidentally matched the slash form.
    if iop_slash:
        out["iop_od"] = iop_slash.group(1)
        out["iop_os"] = iop_slash.group(2)

    # HPI — first sentence after "history" or the first 2 sentences of
    # the transcript, whichever is cleaner. Honest placeholder if we
    # can't find a clear HPI.
    m = re.search(r"\b(?:history|hpi)\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m:
        out["hpi_summary"] = m.group(1).strip()
    else:
        sentences = re.split(r"(?<=[.!?])\s+", t.strip())
        head = " ".join(sentences[:2]).strip()
        out["hpi_summary"] = head if head else None

    diagnoses = _split_list(dx.group(1)) if dx else []
    medications = _split_list(meds.group(1)) if meds else []
    plan_text = plan.group(1).strip() if plan else None
    follow_up = follow.group(1).strip() if follow else None

    structured = {
        "diagnoses": diagnoses,
        "medications": medications,
        "imaging": [],  # not yet extracted
        "assessment": diagnoses[0] if diagnoses else None,
        "plan": plan_text,
        "follow_up_interval": follow_up,
    }
    out["structured_json"] = structured
    return out


def _missing_flags(f: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if not f.get("chief_complaint"):
        flags.append("chief_complaint_missing")
    if not f.get("visual_acuity_od") or not f.get("visual_acuity_os"):
        flags.append("visual_acuity_missing")
    if not f.get("iop_od") or not f.get("iop_os"):
        flags.append("iop_missing")
    if not f.get("structured_json", {}).get("diagnoses"):
        flags.append("diagnosis_missing")
    if not f.get("structured_json", {}).get("plan"):
        flags.append("plan_missing")
    if not f.get("structured_json", {}).get("follow_up_interval"):
        flags.append("follow_up_interval_missing")
    return flags


def _confidence(f: dict[str, Any], flags: list[str]) -> str:
    # Transparent heuristic: ratio of populated critical fields.
    critical = [
        f.get("chief_complaint"),
        f.get("visual_acuity_od"),
        f.get("visual_acuity_os"),
        f.get("iop_od"),
        f.get("iop_os"),
        (f.get("structured_json") or {}).get("diagnoses"),
        (f.get("structured_json") or {}).get("plan"),
    ]
    filled = sum(1 for c in critical if c)
    if filled >= 6:
        return "high"
    if filled >= 3:
        return "medium"
    return "low"


def _render_soap(
    f: dict[str, Any],
    patient_display: str,
    provider_display: str,
) -> str:
    s = f.get("structured_json") or {}
    missing = "<missing — provider to verify>"

    cc = f.get("chief_complaint") or missing
    hpi = f.get("hpi_summary") or missing
    va = f"OD {f.get('visual_acuity_od') or missing}, OS {f.get('visual_acuity_os') or missing}"
    iop = f"OD {f.get('iop_od') or missing}, OS {f.get('iop_os') or missing}"
    dx = ", ".join(s.get("diagnoses") or []) or missing
    meds = ", ".join(s.get("medications") or []) or missing
    plan = s.get("plan") or missing
    follow = s.get("follow_up_interval") or missing

    return (
        f"SUBJECTIVE\n"
        f"Patient: {patient_display}\n"
        f"Provider: {provider_display}\n"
        f"Chief complaint: {cc}\n"
        f"HPI: {hpi}\n"
        f"\n"
        f"OBJECTIVE\n"
        f"Visual acuity: {va}\n"
        f"IOP: {iop}\n"
        f"Current medications: {meds}\n"
        f"\n"
        f"ASSESSMENT\n"
        f"{dx}\n"
        f"\n"
        f"PLAN\n"
        f"{plan}\n"
        f"Follow-up: {follow}\n"
        f"\n"
        f"—\n"
        f"DRAFT generated by ChartNav. Provider must review and sign.\n"
    )


def _run_generator(
    transcript_text: str,
    patient_display: str,
    provider_display: str,
) -> GenerationResult:
    """The seam — swap this body for a real LLM call.

    Today: deterministic regex extraction + SOAP template. The output
    contract (findings dict + narrative + missing-flags list) is what
    matters. A future LLM implementation can produce richer prose
    while preserving the same shape.
    """
    findings = _extract(transcript_text or "")
    flags = _missing_flags(findings)
    findings["extraction_confidence"] = _confidence(findings, flags)
    note_text = _render_soap(findings, patient_display, provider_display)
    return GenerationResult(
        findings=findings,
        note_text=note_text,
        missing_flags=flags,
    )


def generate_draft(
    *,
    transcript_text: str,
    patient_display: str,
    provider_display: str,
) -> GenerationResult:
    """Public entry point used by the HTTP handler.

    Thin wrapper around `_run_generator` so callers don't import the
    private name and tests can monkey-patch this one symbol.
    """
    return _run_generator(transcript_text, patient_display, provider_display)
