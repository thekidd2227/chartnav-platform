"""ICD-10-CM order-file parser.

The authoritative CDC/NCHS release ships a fixed-width text file
conventionally named ``icd10cm-order-<year>.txt`` (e.g.
``icd10cm-order-2025.txt``). Each line has five columns:

    +---------+-----------+---------------------------------------+
    | cols    | width     | meaning                               |
    +---------+-----------+---------------------------------------+
    | 1-5     | 5         | sequential order number               |
    | 7-14    | 8         | diagnosis code (no decimal point)     |
    | 16      | 1         | billable flag (0/1)                   |
    | 18-77   | 60        | short description                     |
    | 79-end  | variable  | long description                      |
    +---------+-----------+---------------------------------------+

Column 16 (the '0' / '1') denotes whether the code is billable as-is.
A '0' row is a header (category or subcategory) used to build the
hierarchy; it is NOT a billable terminal code.

ICD-10-CM chapters are a stable mapping from the first character (and
occasionally the first two characters) of the code. We ship the chapter
table as an in-repo constant since it is stable across releases and
doesn't change between yearly updates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


# Chapter ranges per ICD-10-CM (roman numeral chapter, letter-range, title).
# Stable across yearly updates. Built once; see
# https://www.cms.gov/files/document/fy-2025-icd-10-cm-coding-guidelines.pdf
# Appendix A for the same table.
_CHAPTER_TABLE: list[tuple[str, str, str, str]] = [
    # (roman, first_char_start, first_char_end_inclusive, title)
    ("I",    "A00", "B99", "Certain infectious and parasitic diseases"),
    ("II",   "C00", "D49", "Neoplasms"),
    ("III",  "D50", "D89", "Diseases of the blood and blood-forming organs and certain disorders involving the immune mechanism"),
    ("IV",   "E00", "E89", "Endocrine, nutritional and metabolic diseases"),
    ("V",    "F01", "F99", "Mental, behavioral and neurodevelopmental disorders"),
    ("VI",   "G00", "G99", "Diseases of the nervous system"),
    ("VII",  "H00", "H59", "Diseases of the eye and adnexa"),
    ("VIII", "H60", "H95", "Diseases of the ear and mastoid process"),
    ("IX",   "I00", "I99", "Diseases of the circulatory system"),
    ("X",    "J00", "J99", "Diseases of the respiratory system"),
    ("XI",   "K00", "K95", "Diseases of the digestive system"),
    ("XII",  "L00", "L99", "Diseases of the skin and subcutaneous tissue"),
    ("XIII", "M00", "M99", "Diseases of the musculoskeletal system and connective tissue"),
    ("XIV",  "N00", "N99", "Diseases of the genitourinary system"),
    ("XV",   "O00", "O9A", "Pregnancy, childbirth and the puerperium"),
    ("XVI",  "P00", "P96", "Certain conditions originating in the perinatal period"),
    ("XVII", "Q00", "Q99", "Congenital malformations, deformations and chromosomal abnormalities"),
    ("XVIII","R00", "R99", "Symptoms, signs and abnormal clinical and laboratory findings, not elsewhere classified"),
    ("XIX",  "S00", "T88", "Injury, poisoning and certain other consequences of external causes"),
    ("XX",   "V00", "Y99", "External causes of morbidity"),
    ("XXI",  "Z00", "Z99", "Factors influencing health status and contact with health services"),
    ("XXII", "U00", "U85", "Codes for special purposes"),
]


@dataclass(frozen=True)
class CodeRecord:
    """One row parsed from an icd10cm-order file."""
    code: str                 # decimal-pointed, e.g. H40.1211
    normalized_code: str      # dot stripped, e.g. H401211
    is_billable: bool
    short_description: str
    long_description: str
    chapter_code: str | None
    chapter_title: str | None
    category_code: str | None
    parent_code: str | None
    specificity_flags: str | None
    source_file: str
    source_line_no: int


def normalize_code(code: str) -> str:
    """Strip whitespace and the decimal point from a code."""
    return code.strip().replace(".", "").upper()


def to_pointed(raw: str) -> str:
    """Return the decimal-pointed form. CDC releases the bare form
    ``H401211``; humans and every downstream system want ``H40.1211``.

    Rule: insert a dot after the first three characters when the raw
    is longer than three characters. Codes 3 characters long
    (headers / category codes like ``H40``) are unchanged.
    """
    raw = raw.strip().upper()
    if len(raw) <= 3:
        return raw
    return raw[:3] + "." + raw[3:]


def chapter_for_code(code: str) -> tuple[str | None, str | None]:
    """Return (roman numeral chapter, chapter title) for a code. The
    lookup uses the first three characters of the code."""
    head = normalize_code(code)[:3]
    for roman, lo, hi, title in _CHAPTER_TABLE:
        if lo <= head <= hi:
            return roman, title
    return None, None


def category_for_code(code: str) -> str | None:
    """Return the 3-character category code (e.g. ``H40`` for
    ``H40.1211``). Returns None if the input is shorter than 3 chars."""
    head = normalize_code(code)[:3]
    return head if len(head) == 3 else None


def specificity_flags_for_code(code: str) -> str | None:
    """Inferable specificity requirements from the code shape.

    This is a deterministic heuristic — NOT a replacement for the
    Official Guidelines. Treat as advisory UI prompting only.

    Rules (conservative):
      - H00–H59 eye codes with a 7th character commonly require
        laterality (right/left/bilateral) at positions 4–5. If the
        4th character is absent we prompt for specificity.
      - Glaucoma (H40.xx) codes that are 5 chars long prompt for
        stage (mild/moderate/severe/indeterminate) via the 7th char.
      - Diabetes with ophthalmic manifestations (E08.3x–E11.3x)
        prompt for manifestation detail.
    """
    norm = normalize_code(code)
    if not norm:
        return None

    flags: list[str] = []
    head = norm[:3]

    # Laterality: most eye / adnexa codes require it in their terminal
    # billable form.
    if "H00" <= head <= "H59":
        # Glaucoma laterality sits at position 5 (H40.xxxx)
        # Capture if missing at common positions.
        if len(norm) <= 5:
            flags.append("laterality_required")
        elif head.startswith("H40") and len(norm) == 6:
            # H40.121 still needs the stage (7th char)
            flags.append("stage_required")

    # Diabetes with ophthalmic manifestations (E08.3x, E09.3x, E10.3x,
    # E11.3x, E13.3x).
    if head in ("E08", "E09", "E10", "E11", "E13") and len(norm) >= 5 and norm[3] == "3":
        flags.append("manifestation_detail_required")

    return ",".join(flags) if flags else None


def parse_order_file(path: str) -> Iterator[CodeRecord]:
    """Parse an icd10cm-order-<year>.txt fixed-width file.

    Yields one ``CodeRecord`` per line. Header-only rows (billable
    flag = 0) are still yielded; downstream code can filter on the
    ``is_billable`` flag.
    """
    import os
    source_file = os.path.basename(path)
    # Track the most recent 3-char category so we can set a parent
    # reference without walking the whole file twice.
    last_category_seen: str | None = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            # The official files are strictly fixed-width. If the line
            # is shorter than expected, skip rather than guess.
            if len(line) < 77:
                continue
            # CDC/CMS 2025+ layout (verified against icd10cm_order_2026.txt):
            #   [0:5]   order number
            #   [5]     space
            #   [6:14]  code (8 chars, right-padded with spaces)
            #   [14]    billable flag (0/1)
            #   [15]    space
            #   [16:76] short description (60 chars)
            #   [76]    space
            #   [77:]   long description
            raw_code = line[6:14].strip()
            if not raw_code:
                continue
            billable_flag = line[14:15].strip() == "1"
            short_desc = line[16:76].strip()
            long_desc = line[77:].strip()

            pointed = to_pointed(raw_code)
            chapter_code, chapter_title = chapter_for_code(pointed)
            category = category_for_code(pointed)
            # Parent heuristic:
            #   - if this is a 3-char header, parent is None
            #   - otherwise the parent is the prefix with the last
            #     character stripped (keeping the dot if present)
            if len(pointed) <= 3:
                parent = None
                last_category_seen = pointed
            else:
                parent = pointed[:-1].rstrip(".")
            flags = specificity_flags_for_code(pointed)

            yield CodeRecord(
                code=pointed,
                normalized_code=normalize_code(pointed),
                is_billable=billable_flag,
                short_description=short_desc,
                long_description=long_desc,
                chapter_code=chapter_code,
                chapter_title=chapter_title,
                category_code=category,
                parent_code=parent,
                specificity_flags=flags,
                source_file=source_file,
                source_line_no=lineno,
            )
