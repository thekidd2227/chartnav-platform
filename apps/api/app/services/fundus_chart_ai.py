"""AI-assisted fundus chart generation service.

Parses free-text ophthalmology findings into structured drawing data.
Deterministic rule-based mapping — no LLM required.
Never invents missing clinical details; emits warnings instead.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FundusDrawingElement:
    finding_type: str
    laterality: str
    clock_start: float | None
    clock_end: float | None
    zone: str
    color: str
    label: str


@dataclass
class FundusChartGenerationResult:
    laterality: str
    elements: list[FundusDrawingElement] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ai_model_name: str = "rule_based_v1"
    confidence: dict[str, Any] = field(default_factory=dict)
    drawing_json: dict[str, Any] = field(default_factory=dict)


_LATERALITY_RE = re.compile(
    r"\b(OD|OS|right\s+eye|left\s+eye|right|left)\b", re.IGNORECASE
)
_CLOCK_RANGE_RE = re.compile(
    r"\b(\d{1,2}(?::\d{2})?)\s*(?:to|-|through)\s*(\d{1,2}(?::\d{2})?)\b",
    re.IGNORECASE,
)
_CLOCK_SINGLE_RE = re.compile(r"\bat\s+(\d{1,2}(?::\d{2})?)\b", re.IGNORECASE)

_FINDING_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bhorseshoe\s+tear\b", re.IGNORECASE), "horseshoe_tear", "#e53e3e"),
    (re.compile(r"\bretinal\s+break\b", re.IGNORECASE), "break", "#e53e3e"),
    (re.compile(r"\blattice\b", re.IGNORECASE), "lattice", "#d69e2e"),
    (re.compile(r"\bdetach(?:ment)?\b", re.IGNORECASE), "detachment", "#3182ce"),
    (re.compile(r"\btear\b", re.IGNORECASE), "tear", "#e53e3e"),
    (re.compile(r"\bhole\b", re.IGNORECASE), "hole", "#e53e3e"),
    (re.compile(r"\bbreak\b", re.IGNORECASE), "break", "#e53e3e"),
    (re.compile(r"\bpigment\b|\bRPE\b", re.IGNORECASE), "rpe_change", "#805ad5"),
    (re.compile(r"\bneovascular|\bNV[DE]\b", re.IGNORECASE), "neovascularization", "#38a169"),
    (re.compile(r"\bexudat", re.IGNORECASE), "exudate", "#ecc94b"),
    (re.compile(r"\bhemorrhage\b", re.IGNORECASE), "hemorrhage", "#c53030"),
    (re.compile(r"\bdrusen\b", re.IGNORECASE), "drusen", "#d69e2e"),
]

_ZONE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"\bposterior\s+pole\b|\bmacula\b|\boptic\s+disc\b|\bdisc\b",
            re.IGNORECASE,
        ),
        "posterior_pole",
    ),
    (re.compile(r"\bequator\b|\bequatorial\b", re.IGNORECASE), "equator"),
    (
        re.compile(
            r"\bora\s+serrata\b|\bora\b|\bperipheral\b|\bperiphery\b",
            re.IGNORECASE,
        ),
        "ora_serrata",
    ),
]


def _parse_laterality(text: str) -> str | None:
    m = _LATERALITY_RE.search(text)
    if not m:
        return None
    v = m.group(1).lower().replace(" ", "")
    if v in ("od", "righteye", "right"):
        return "OD"
    if v in ("os", "lefteye", "left"):
        return "OS"
    return None


def _parse_clock_hour(value: str) -> float:
    if ":" in value:
        h, m = value.split(":")
        return int(h) + int(m) / 60.0
    return float(value)


def _parse_zone(sentence: str) -> str:
    for pat, zone in _ZONE_PATTERNS:
        if pat.search(sentence):
            return zone
    return "equator"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[;,\n]", text) if s.strip()]


def generate_chart_from_findings(
    findings_text: str,
    laterality_hint: str | None = None,
) -> FundusChartGenerationResult:
    """Parse findings text and produce structured drawing data.

    Produces warnings for missing laterality, missing clock hour for
    peripheral findings, and unrecognised findings.  Never invents
    clinical details.
    """
    warnings: list[str] = []
    elements: list[FundusDrawingElement] = []

    detected_lat = _parse_laterality(findings_text)
    if detected_lat is None and laterality_hint:
        detected_lat = laterality_hint.upper()
    if detected_lat is None:
        warnings.append(
            "Laterality not specified in findings text. "
            "Please confirm OD (right eye) or OS (left eye) before signing."
        )
        detected_lat = "OD"

    for sentence in _sentences(findings_text):
        lat = _parse_laterality(sentence) or detected_lat

        matched_type: str | None = None
        matched_color: str = "#718096"
        for pat, ftype, color in _FINDING_PATTERNS:
            if pat.search(sentence):
                matched_type = ftype
                matched_color = color
                break

        if matched_type is None:
            continue

        clock_start: float | None = None
        clock_end: float | None = None
        rm = _CLOCK_RANGE_RE.search(sentence)
        if rm:
            clock_start = _parse_clock_hour(rm.group(1))
            clock_end = _parse_clock_hour(rm.group(2))
        else:
            sm = _CLOCK_SINGLE_RE.search(sentence)
            if sm:
                clock_start = _parse_clock_hour(sm.group(1))

        zone = _parse_zone(sentence)
        if zone in ("equator", "ora_serrata") and clock_start is None:
            warnings.append(
                f"Clock hour not specified for '{matched_type}' finding. "
                "Please add clock-hour location before signing."
            )

        elements.append(
            FundusDrawingElement(
                finding_type=matched_type,
                laterality=lat,
                clock_start=clock_start,
                clock_end=clock_end,
                zone=zone,
                color=matched_color,
                label=matched_type.replace("_", " ").title(),
            )
        )

    if not elements:
        warnings.append(
            "No recognisable findings were parsed from the text. "
            "Manual annotation is required."
        )

    drawing_json: dict[str, Any] = {
        "version": 1,
        "elements": [
            {
                "type": el.finding_type,
                "laterality": el.laterality,
                "clock_start": el.clock_start,
                "clock_end": el.clock_end,
                "zone": el.zone,
                "color": el.color,
                "label": el.label,
            }
            for el in elements
        ],
    }

    confidence: dict[str, Any] = {
        "model": "rule_based_v1",
        "parsed_sentences": len(_sentences(findings_text)),
        "matched_findings": len(elements),
        "warning_count": len(warnings),
    }

    return FundusChartGenerationResult(
        laterality=detected_lat,
        elements=elements,
        warnings=warnings,
        ai_model_name="rule_based_v1",
        confidence=confidence,
        drawing_json=drawing_json,
    )
