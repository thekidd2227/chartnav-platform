"""Findings → retinal diagram proposal engine (deterministic, rule-based).

Phase 6A. This module is **pure logic** — no DB, no HTTP, no LLM. The
route layer wraps it to authorize the caller and audit metadata only.
Nothing here writes to `chart_artifacts`; the proposal endpoint is
explicitly read-only on the data side, and proposals only ever flow
into a stored artifact after a provider explicitly applies them on the
frontend.

Design constraints (from Phase 6 spec):
  - No LLM in this PR.
  - Stable, deterministic proposal IDs derived from the source phrase
    so the same input produces the same id across requests.
  - Missing laterality => no proposal placed; emit a `missing_flag`
    so the UI can show the provider what to clarify.
  - OU / bilateral => one OD proposal + one OS proposal.
  - Coordinate convention matches `RetinalDrawingCanvas.tsx`:
      OD: nasal is x > 0.5, temporal is x < 0.5
      OS: nasal is x < 0.5, temporal is x > 0.5
      superior is y < 0.5, inferior is y > 0.5
  - Detail strings stored in audit logs are metadata-only — never the
    raw findings_text.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


# --- domain --------------------------------------------------------------


# Eye literal: "OD" (right) or "OS" (left).
Eye = str

# Symbol type keys must match `apps/web/src/retinalAnnotations.ts`
# `SYMBOL_TYPES`. Keep this list synchronized.
KNOWN_FINDINGS: dict[str, str] = {
    "drusen": "drusen",
    "dot blot hemorrhage": "dot_blot_hemorrhage",
    "dot/blot hemorrhage": "dot_blot_hemorrhage",
    "dot hemorrhage": "dot_blot_hemorrhage",
    "blot hemorrhage": "dot_blot_hemorrhage",
    "flame hemorrhage": "flame_hemorrhage",
    "microaneurysm": "microaneurysm",
    "microaneurysms": "microaneurysm",
    "hard exudate": "hard_exudates",
    "hard exudates": "hard_exudates",
    "cotton wool spot": "cotton_wool_spot",
    "cotton-wool spot": "cotton_wool_spot",
    "cotton wool spots": "cotton_wool_spot",
    "cotton-wool spots": "cotton_wool_spot",
    "neovascularization": "neovascularization",
    "retinal tear": "retinal_tear",
    "retinal hole": "retinal_tear",
    "retinal tear/hole": "retinal_tear",
    "retinal detachment": "retinal_detachment",
    "laser scar": "laser_scar",
    "laser/scar": "laser_scar",
    "laser scars": "laser_scar",
    "disc pallor": "disc_pallor",
    "rpe change": "rpe_change",
    "rpe changes": "rpe_change",
    "lattice degeneration": "lattice_degeneration",
}

# Laterality vocabulary. "OU" / bilateral / both eyes => both OD and OS.
LEFT_EYE_TOKENS = {"os", "left eye", "left-eye"}
RIGHT_EYE_TOKENS = {"od", "right eye", "right-eye"}
BOTH_EYE_TOKENS = {"ou", "bilateral", "bilaterally", "both eyes"}

# Zones recognized in the parser. Display zone names are normalized
# back into the proposal output for the UI.
ZONE_TOKENS: dict[str, str] = {
    "macula": "macula",
    "macular": "macula",
    "optic disc": "optic_disc",
    "disc": "optic_disc",
    "superior temporal": "superior_temporal",
    "superotemporal": "superior_temporal",
    "superior nasal": "superior_nasal",
    "superonasal": "superior_nasal",
    "inferior temporal": "inferior_temporal",
    "inferotemporal": "inferior_temporal",
    "inferior nasal": "inferior_nasal",
    "inferonasal": "inferior_nasal",
    "superior": "superior",
    "inferior": "inferior",
    "nasal": "nasal",
    "temporal": "temporal",
    "periphery": "periphery",
    "peripheral": "periphery",
}


# Phrases the parser deliberately ignores (chatter / non-clinical).
CHATTER_PHRASES = (
    "thank you",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "next slide",
    "uh ",
    "um ",
    "okay,",
    "ok,",
    "let me see",
)


# --- output types --------------------------------------------------------


@dataclass(frozen=True)
class ProposedAnnotation:
    proposal_id: str
    kind: str            # "symbol"
    symbol_type: str
    eye: Eye             # "OD" | "OS"
    x: float
    y: float
    zone: Optional[str]
    text: str
    color: str
    confidence: float    # 0.0 .. 1.0
    confidence_band: str # "high" | "medium" | "low"
    source_phrase: str
    source_start: int
    source_end: int
    reason: str
    missing_flags: list[str] = field(default_factory=list)
    source: str = "ai_proposed"


@dataclass
class MissingFlag:
    code: str            # e.g. "missing_laterality"
    detail: str
    source_phrase: str
    source_start: int
    source_end: int


@dataclass
class ProposalResult:
    clinical_text: str
    ignored_chatter: list[str]
    uncertain_phrases: list[str]
    proposed_annotations: list[ProposedAnnotation]
    confidence_summary: dict[str, Any]
    missing_flags: list[MissingFlag]


# --- coordinate mapping --------------------------------------------------


def coords_for(eye: Eye, zone: Optional[str]) -> tuple[float, float]:
    """Map (eye, zone) -> normalized (x, y) coordinates inside the eye pane.

    Convention matches `RetinalDrawingCanvas.tsx`:
      OD pane: optic disc on the RIGHT (x > 0.5), so nasal=right, temporal=left.
      OS pane: optic disc on the LEFT (x < 0.5), so nasal=left, temporal=right.
      Superior is y < 0.5; inferior is y > 0.5; eye-independent.
    """
    # Defaults if zone is unknown — drop near macula center.
    if zone is None:
        return (0.5, 0.5)

    nasal_x_for = {"OD": 0.7, "OS": 0.3}
    temporal_x_for = {"OD": 0.3, "OS": 0.7}

    table: dict[str, tuple[float, float]] = {
        "macula": (0.5, 0.5),
        "optic_disc": (nasal_x_for[eye], 0.5),  # disc sits on the nasal side
        "superior": (0.5, 0.25),
        "inferior": (0.5, 0.75),
        "nasal": (nasal_x_for[eye], 0.5),
        "temporal": (temporal_x_for[eye], 0.5),
        "superior_temporal": (temporal_x_for[eye], 0.25),
        "superior_nasal": (nasal_x_for[eye], 0.25),
        "inferior_temporal": (temporal_x_for[eye], 0.75),
        "inferior_nasal": (nasal_x_for[eye], 0.75),
        "periphery": (0.85, 0.5) if eye == "OD" else (0.15, 0.5),
    }
    return table.get(zone, (0.5, 0.5))


# --- parsing -------------------------------------------------------------


_FINDING_PATTERNS: list[tuple[re.Pattern[str], str]] = sorted(
    (
        (re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE), key)
        for phrase, key in KNOWN_FINDINGS.items()
    ),
    # Match longest phrases first so e.g. "dot/blot hemorrhage" wins over "blot hemorrhage".
    key=lambda pair: -len(pair[0].pattern),
)


def _detect_laterality(text: str) -> set[Eye]:
    low = text.lower()
    eyes: set[Eye] = set()
    for tok in BOTH_EYE_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            return {"OD", "OS"}
    for tok in RIGHT_EYE_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            eyes.add("OD")
            break
    for tok in LEFT_EYE_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            eyes.add("OS")
            break
    return eyes


def _detect_zone(text: str) -> Optional[str]:
    low = text.lower()
    # Prefer compound zones (longest token) first.
    for token in sorted(ZONE_TOKENS, key=lambda s: -len(s)):
        if re.search(rf"\b{re.escape(token)}\b", low):
            return ZONE_TOKENS[token]
    return None


def _split_segments(text: str) -> list[tuple[str, int, int]]:
    """Split findings_text into segments with their original offsets.

    Splits on sentence terminators and newlines. Preserves the segment's
    `start` and `end` offsets within the original text so the UI can
    highlight the source phrase.
    """
    out: list[tuple[str, int, int]] = []
    if not text:
        return out
    pattern = re.compile(r"[^.\n;]+(?:[.\n;]|$)")
    for match in pattern.finditer(text):
        seg_raw = match.group(0)
        start = match.start()
        end = match.end()
        # Trim leading/trailing whitespace but keep accurate offsets.
        leading_ws = len(seg_raw) - len(seg_raw.lstrip())
        trailing_ws = len(seg_raw) - len(seg_raw.rstrip(".;\n "))
        seg = seg_raw.strip(".;\n ")
        if seg:
            out.append((seg, start + leading_ws, end - trailing_ws))
    return out


def _is_chatter(segment: str) -> bool:
    low = segment.lower()
    return any(p in low for p in CHATTER_PHRASES)


def _stable_proposal_id(*parts: str) -> str:
    """SHA-256 of normalized parts, truncated to 16 hex chars."""
    norm = "|".join(p.strip().lower() for p in parts)
    digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return f"p_{digest[:16]}"


def _normalize_phrase(phrase: str) -> str:
    # Collapse internal whitespace; strip surrounding punctuation.
    return re.sub(r"\s+", " ", phrase).strip(" .,;:\n").lower()


def _confidence_for(has_laterality: bool, has_zone: bool) -> tuple[float, str]:
    if has_laterality and has_zone:
        return (0.85, "high")
    if has_laterality and not has_zone:
        return (0.6, "medium")
    return (0.3, "low")


def _zone_display(zone: Optional[str]) -> str:
    if not zone:
        return ""
    pretty = {
        "macula": "macula",
        "optic_disc": "optic disc",
        "superior": "superior",
        "inferior": "inferior",
        "nasal": "nasal",
        "temporal": "temporal",
        "superior_temporal": "superior temporal",
        "superior_nasal": "superior nasal",
        "inferior_temporal": "inferior temporal",
        "inferior_nasal": "inferior nasal",
        "periphery": "periphery",
    }
    return pretty.get(zone, zone)


def _finding_display(symbol_type: str) -> str:
    pretty = {
        "drusen": "drusen",
        "dot_blot_hemorrhage": "dot/blot hemorrhage",
        "flame_hemorrhage": "flame hemorrhage",
        "microaneurysm": "microaneurysm",
        "hard_exudates": "hard exudates",
        "cotton_wool_spot": "cotton-wool spot",
        "neovascularization": "neovascularization",
        "retinal_tear": "retinal tear/hole",
        "retinal_detachment": "retinal detachment",
        "laser_scar": "laser/scar",
        "disc_pallor": "disc pallor",
        "rpe_change": "RPE change",
        "lattice_degeneration": "lattice degeneration",
    }
    return pretty.get(symbol_type, symbol_type)


# --- public entrypoint ---------------------------------------------------


def propose_from_findings(findings_text: str) -> ProposalResult:
    """Run the deterministic findings parser and return proposals.

    Pure function. No DB, no HTTP, no LLM. Stable across calls for the
    same input.
    """
    if findings_text is None:
        findings_text = ""

    ignored: list[str] = []
    uncertain: list[str] = []
    proposals: list[ProposedAnnotation] = []
    missing: list[MissingFlag] = []
    clinical_lines: list[str] = []

    for segment, start, end in _split_segments(findings_text):
        if _is_chatter(segment):
            ignored.append(segment)
            continue

        finding_match = _find_first_finding(segment)
        if not finding_match:
            uncertain.append(segment)
            continue

        symbol_type, finding_phrase, _, _ = finding_match
        clinical_lines.append(segment)

        eyes = _detect_laterality(segment)
        zone = _detect_zone(segment)

        if not eyes:
            missing.append(
                MissingFlag(
                    code="missing_laterality",
                    detail=(
                        f"Found {_finding_display(symbol_type)} but no eye "
                        "(OD/OS/OU/right/left/bilateral) — cannot place on diagram."
                    ),
                    source_phrase=segment,
                    source_start=start,
                    source_end=end,
                )
            )
            continue

        for eye in sorted(eyes):
            x, y = coords_for(eye, zone)
            confidence, band = _confidence_for(
                has_laterality=True, has_zone=zone is not None
            )
            zone_disp = _zone_display(zone)
            label = f"{eye} {_finding_display(symbol_type)}"
            if zone_disp:
                label = f"{label} at {zone_disp}"
            reason_bits = [f"finding={symbol_type}", f"eye={eye}"]
            if zone:
                reason_bits.append(f"zone={zone}")
            else:
                reason_bits.append("zone=missing")
            reason = "matched " + " + ".join(reason_bits)

            pid = _stable_proposal_id(
                _normalize_phrase(segment), symbol_type, eye, zone or ""
            )
            proposals.append(
                ProposedAnnotation(
                    proposal_id=pid,
                    kind="symbol",
                    symbol_type=symbol_type,
                    eye=eye,
                    x=x,
                    y=y,
                    zone=zone,
                    text=label,
                    color="#c1121f",
                    confidence=confidence,
                    confidence_band=band,
                    source_phrase=segment,
                    source_start=start,
                    source_end=end,
                    reason=reason,
                    missing_flags=[] if zone else ["missing_zone"],
                )
            )

    summary = {
        "high": sum(1 for p in proposals if p.confidence_band == "high"),
        "medium": sum(1 for p in proposals if p.confidence_band == "medium"),
        "low": sum(1 for p in proposals if p.confidence_band == "low"),
        "needs_review": True,
    }

    return ProposalResult(
        clinical_text="\n".join(clinical_lines),
        ignored_chatter=ignored,
        uncertain_phrases=uncertain,
        proposed_annotations=proposals,
        confidence_summary=summary,
        missing_flags=missing,
    )


def _find_first_finding(
    segment: str,
) -> Optional[tuple[str, str, int, int]]:
    """Return (symbol_type, phrase, start, end) for the first finding hit."""
    for pattern, symbol_type in _FINDING_PATTERNS:
        m = pattern.search(segment)
        if m:
            return (symbol_type, m.group(0), m.start(), m.end())
    return None


# --- helpers for the route layer ----------------------------------------


def proposal_to_dict(p: ProposedAnnotation) -> dict[str, Any]:
    return {
        "proposal_id": p.proposal_id,
        "kind": p.kind,
        "symbol_type": p.symbol_type,
        "eye": p.eye,
        "x": p.x,
        "y": p.y,
        "zone": p.zone,
        "text": p.text,
        "color": p.color,
        "confidence": p.confidence,
        "confidence_band": p.confidence_band,
        "source_phrase": p.source_phrase,
        "source_start": p.source_start,
        "source_end": p.source_end,
        "reason": p.reason,
        "missing_flags": list(p.missing_flags),
        "source": p.source,
    }


def missing_flag_to_dict(m: MissingFlag) -> dict[str, Any]:
    return {
        "code": m.code,
        "detail": m.detail,
        "source_phrase": m.source_phrase,
        "source_start": m.source_start,
        "source_end": m.source_end,
    }


def result_to_response(result: ProposalResult) -> dict[str, Any]:
    return {
        "clinical_text": result.clinical_text,
        "ignored_chatter": list(result.ignored_chatter),
        "uncertain_phrases": list(result.uncertain_phrases),
        "proposed_annotations": [proposal_to_dict(p) for p in result.proposed_annotations],
        "confidence_summary": dict(result.confidence_summary),
        "missing_flags": [missing_flag_to_dict(m) for m in result.missing_flags],
    }


__all__: Iterable[str] = (
    "propose_from_findings",
    "ProposalResult",
    "ProposedAnnotation",
    "MissingFlag",
    "result_to_response",
    "proposal_to_dict",
    "missing_flag_to_dict",
    "coords_for",
    "KNOWN_FINDINGS",
)
