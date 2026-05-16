"""Phase 25A / GH-004 — server-side mirror of ``noteQualityChecks.ts``.

Same rules, same severities, same flag codes. The web client already
runs these against the in-progress draft; this module gives the
backend the same view so server-side gates (submit-for-review, sign,
export) can refuse to advance a draft that is empty or carries a
``block`` flag — without trusting the client to have done its
checks.

Design constraints
------------------
- Pure functions. No DOM, no fetch, no AI, no hidden state.
- Never autonomously diagnoses, interprets images, orders, refers,
  codes, or bills. These checks are linters, not clinical decision
  support.
- Severities mirror the TS file exactly: ``block`` / ``warn`` /
  ``info``.
- Flag codes mirror the TS file exactly so logs / metrics line up
  across both layers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------
# Public dataclasses (mirror the TS shapes).
# ---------------------------------------------------------------

QualityFlagSeverity = str  # "block" | "warn" | "info"

QualityFlagCode = str  # see TS file for the closed enum


@dataclass(frozen=True)
class FlagRegion:
    start: int
    end: int


@dataclass(frozen=True)
class QualityFlag:
    code: str
    severity: str
    message: str
    action_label: Optional[str] = None
    region: Optional[FlagRegion] = None


@dataclass(frozen=True)
class QualityCheckContext:
    encounter_laterality: Optional[str] = None  # "OD" / "OS" / "OU" / None
    extracted_findings: Optional[str] = None
    specialty: str = "general"


@dataclass(frozen=True)
class QualityCheckResult:
    flags: tuple[QualityFlag, ...] = field(default_factory=tuple)
    completeness_percent: int = 0
    has_blocking_flags: bool = False

    def to_dict(self) -> dict:
        return {
            "flags": [
                {
                    "code": f.code,
                    "severity": f.severity,
                    "message": f.message,
                    "action_label": f.action_label,
                    "region": (
                        {"start": f.region.start, "end": f.region.end}
                        if f.region is not None
                        else None
                    ),
                }
                for f in self.flags
            ],
            "completeness_percent": self.completeness_percent,
            "has_blocking_flags": self.has_blocking_flags,
        }


# ---------------------------------------------------------------
# Tables (mirror the TS file 1:1).
# ---------------------------------------------------------------

REQUIRED_SECTIONS: dict[str, list[str]] = {
    "retina": [
        "Chief complaint",
        "History",
        "Exam",
        "Imaging review",
        "Assessment",
        "Plan",
    ],
    "glaucoma": [
        "Chief complaint",
        "History",
        "Exam",
        "Imaging / VF review",
        "Assessment",
        "Plan",
    ],
    "cornea": ["Chief complaint", "History", "Exam", "Impression", "Plan"],
    "cataract": ["Chief complaint", "History", "Post-op status", "Plan"],
    "oculoplastics": [
        "Chief complaint",
        "History",
        "Exam",
        "Impression",
        "Plan",
    ],
    "general": [
        "Chief complaint",
        "History",
        "Exam",
        "Assessment",
        "Plan",
    ],
}


BANNED_PHRASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bauto[- ]?graded? DR\b", re.IGNORECASE), "auto-grade DR"),
    (re.compile(r"\bauto[- ]?interpret(s|ed)?\b", re.IGNORECASE), "auto-interpret"),
    (re.compile(r"\bautonomous diagnosis\b", re.IGNORECASE), "autonomous diagnosis"),
    (re.compile(r"\bguaranteed accuracy\b", re.IGNORECASE), "guaranteed accuracy"),
    (re.compile(r"\bautomatic orders?\b", re.IGNORECASE), "automatic orders"),
    (re.compile(r"\bautomatic referrals?\b", re.IGNORECASE), "automatic referrals"),
    (re.compile(r"\bchart fills itself\b", re.IGNORECASE), "chart fills itself"),
    (re.compile(r"\bnote writes itself\b", re.IGNORECASE), "note writes itself"),
]


LATERALITY_TOKENS = {
    "OD": [re.compile(r"\bOD\b"), re.compile(r"\bright eye\b", re.IGNORECASE)],
    "OS": [re.compile(r"\bOS\b"), re.compile(r"\bleft eye\b", re.IGNORECASE)],
    "OU": [
        re.compile(r"\bOU\b"),
        re.compile(r"\bboth eyes\b", re.IGNORECASE),
        re.compile(r"\bbilateral\b", re.IGNORECASE),
    ],
}


# ---------------------------------------------------------------
# Helpers (mirror TS).
# ---------------------------------------------------------------

def _matches_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def _find_first(text: str, pattern: re.Pattern[str]) -> Optional[FlagRegion]:
    m = pattern.search(text)
    if not m:
        return None
    return FlagRegion(start=m.start(), end=m.end())


def _has_section(text: str, section: str) -> bool:
    needle = re.escape(section)
    re_section = re.compile(
        rf"(^|\n)\s*{needle}\b[ \t]*:?", re.IGNORECASE
    )
    return bool(re_section.search(text))


def _section_has_body(text: str, section: str, known_headers: list[str]) -> bool:
    needle = re.escape(section)
    header_re = re.compile(
        rf"(^|\n)\s*{needle}\b[ \t]*:?[ \t]*", re.IGNORECASE
    )
    m = header_re.search(text)
    if not m:
        return False
    match_end = m.end()
    # 1. Inline body.
    nl = text.find("\n", match_end)
    inline_end = nl if nl != -1 else len(text)
    inline = text[match_end:inline_end].strip()
    if inline:
        return True
    # 2. Walk subsequent lines.
    if nl == -1:
        return False
    after = text[nl + 1 :]
    others = [h for h in known_headers if h.lower() != section.lower()]
    for raw in after.split("\n"):
        line = raw.strip()
        if not line:
            continue
        is_next = any(
            re.match(rf"^{re.escape(h)}\b[ \t]*:", line, re.IGNORECASE)
            for h in others
        )
        if is_next:
            return False
        if len(line) <= 60 and line.endswith(":"):
            return False
        return True
    return False


def _completeness_count(text: str, required: list[str]) -> int:
    return sum(
        1
        for s in required
        if _has_section(text, s) and _section_has_body(text, s, required)
    )


def _check_laterality(
    text: str, encounter_lat: Optional[str]
) -> list[QualityFlag]:
    out: list[QualityFlag] = []
    od = _matches_any(text, LATERALITY_TOKENS["OD"])
    os_ = _matches_any(text, LATERALITY_TOKENS["OS"])
    ou = _matches_any(text, LATERALITY_TOKENS["OU"])

    if encounter_lat == "OD" and os_ and not ou:
        out.append(
            QualityFlag(
                code="laterality_conflict",
                severity="block",
                message=(
                    "Encounter laterality is OD, but the draft mentions "
                    "OS / left eye without a bilateral anchor. Confirm "
                    "before sign-off."
                ),
                action_label="Confirm OD/OS",
                region=_find_first(text, LATERALITY_TOKENS["OS"][0]),
            )
        )
    elif encounter_lat == "OS" and od and not ou:
        out.append(
            QualityFlag(
                code="laterality_conflict",
                severity="block",
                message=(
                    "Encounter laterality is OS, but the draft mentions "
                    "OD / right eye without a bilateral anchor. Confirm "
                    "before sign-off."
                ),
                action_label="Confirm OD/OS",
                region=_find_first(text, LATERALITY_TOKENS["OD"][0]),
            )
        )
    elif (
        encounter_lat
        and encounter_lat != "OU"
        and not od
        and not os_
        and not ou
    ):
        out.append(
            QualityFlag(
                code="laterality_mention_no_anchor",
                severity="info",
                message=(
                    f"Encounter laterality is {encounter_lat}, but the "
                    "draft has no OD/OS/OU mention. Add an explicit "
                    "laterality anchor where appropriate."
                ),
                action_label="Add laterality",
            )
        )
    return out


def _check_contradictions(
    text: str, extracted: Optional[str]
) -> list[QualityFlag]:
    if not extracted:
        return []
    out: list[QualityFlag] = []
    probes = [
        "retinal detachment",
        "retinal tear",
        "vitreous hemorrhage",
        "macular hole",
        "neovascularization",
    ]
    for probe in probes:
        probe_word_re = re.compile(
            rf"(?:^|[^a-z]){re.escape(probe)}(?![a-z])", re.IGNORECASE
        )
        neg_re = re.compile(
            rf"(?:no|without|negative for)\s+{re.escape(probe)}",
            re.IGNORECASE,
        )
        draft_asserts = bool(probe_word_re.search(text)) and not bool(
            neg_re.search(text)
        )
        draft_negates = bool(neg_re.search(text))
        extracted_negates = bool(neg_re.search(extracted))
        extracted_asserts = bool(probe_word_re.search(extracted)) and not extracted_negates

        if draft_asserts and extracted_negates:
            out.append(
                QualityFlag(
                    code="contradiction_negation_then_assertion",
                    severity="warn",
                    message=(
                        f'Draft asserts "{probe}" but the upstream '
                        "findings text negates it. Reconcile before "
                        "sign-off."
                    ),
                    action_label=f"Reconcile {probe}",
                    region=_find_first(text, re.compile(re.escape(probe), re.IGNORECASE)),
                )
            )
        elif draft_negates and extracted_asserts:
            out.append(
                QualityFlag(
                    code="contradiction_negation_then_assertion",
                    severity="warn",
                    message=(
                        f'Draft negates "{probe}" but the upstream '
                        "findings text asserts it. Reconcile before "
                        "sign-off."
                    ),
                    action_label=f"Reconcile {probe}",
                    region=_find_first(
                        text,
                        re.compile(rf"no\s+{re.escape(probe)}", re.IGNORECASE),
                    ),
                )
            )
    return out


def _check_banned_phrases(text: str) -> list[QualityFlag]:
    out: list[QualityFlag] = []
    for pattern, label in BANNED_PHRASES:
        region = _find_first(text, pattern)
        if region:
            out.append(
                QualityFlag(
                    code="banned_phrase",
                    severity="warn",
                    message=(
                        f'Draft contains "{label}" — this phrase is on '
                        "the ChartNav safe-claims contract. Rephrase "
                        "before sign-off."
                    ),
                    action_label="Rephrase",
                    region=region,
                )
            )
    return out


def _check_duplicate_sections(
    text: str, required: list[str]
) -> list[QualityFlag]:
    out: list[QualityFlag] = []
    for section in required:
        needle = re.escape(section)
        re_section = re.compile(
            rf"(^|\n)\s*{needle}\b[ \t]*:", re.IGNORECASE
        )
        count = len(re_section.findall(text))
        if count > 1:
            out.append(
                QualityFlag(
                    code="duplicate_critical_section",
                    severity="warn",
                    message=(
                        f'Draft has {count} "{section}" section '
                        "headers. Merge them so there is one canonical "
                        "section per chart record."
                    ),
                    action_label="Merge sections",
                )
            )
    return out


# ---------------------------------------------------------------
# Public entry-point.
# ---------------------------------------------------------------

def run_note_quality_checks(
    draft_text: str,
    context: Optional[QualityCheckContext] = None,
) -> QualityCheckResult:
    ctx = context or QualityCheckContext()
    specialty = ctx.specialty or "general"
    required = REQUIRED_SECTIONS.get(specialty, REQUIRED_SECTIONS["general"])
    flags: list[QualityFlag] = []

    if not draft_text or not draft_text.strip():
        flags.append(
            QualityFlag(
                code="draft_empty",
                severity="info",
                message=(
                    "Draft is empty. Insert a specialty template or "
                    "start typing to begin."
                ),
            )
        )
        return QualityCheckResult(
            flags=tuple(flags),
            completeness_percent=0,
            has_blocking_flags=False,
        )

    # Missing sections.
    for section in required:
        if not _has_section(draft_text, section):
            flags.append(
                QualityFlag(
                    code="missing_critical_element",
                    severity="warn",
                    message=(
                        f'Required section "{section}" is missing. Add '
                        "it before sign-off (the reviewer cannot infer "
                        "it from context)."
                    ),
                    action_label=f"Add {section}",
                )
            )

    # Completeness scoring.
    present = _completeness_count(draft_text, required)
    completeness_percent = round(
        (present / max(1, len(required))) * 100
    )
    if completeness_percent < 60:
        flags.append(
            QualityFlag(
                code="completeness_low",
                severity="warn",
                message=(
                    f"Note is {completeness_percent}% complete "
                    f"({present} of {len(required)} required sections). "
                    "Provider sign-off expected after the missing "
                    "sections are filled."
                ),
            )
        )
    elif completeness_percent < 100:
        flags.append(
            QualityFlag(
                code="completeness_partial",
                severity="info",
                message=(
                    f"Note is {completeness_percent}% complete "
                    f"({present} of {len(required)} required sections)."
                ),
            )
        )

    flags.extend(_check_laterality(draft_text, ctx.encounter_laterality))
    flags.extend(_check_contradictions(draft_text, ctx.extracted_findings))
    flags.extend(_check_banned_phrases(draft_text))
    flags.extend(_check_duplicate_sections(draft_text, required))

    has_blocking = any(f.severity == "block" for f in flags)
    return QualityCheckResult(
        flags=tuple(flags),
        completeness_percent=completeness_percent,
        has_blocking_flags=has_blocking,
    )


def severity_counts(result: QualityCheckResult) -> dict[str, int]:
    counts = {"block": 0, "warn": 0, "info": 0}
    for f in result.flags:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts
