"""ICD-10-CM parsing + ingestion library.

Public names:
    parse_order_file                — fixed-width icd10cm-order file
    chapter_for_code                — return (chapter_code, chapter_title)
    category_for_code               — return 3-char category
    normalize_code                  — strip decimal point
    CDC_NCHS_RELEASE_SOURCES        — list of official release URLs
    fetch_release                   — download one release manifest
    CodeRecord                      — parsed dataclass
"""
from .parser import (
    CodeRecord,
    parse_order_file,
    chapter_for_code,
    category_for_code,
    normalize_code,
    specificity_flags_for_code,
)
from .fetch import (
    CDC_NCHS_RELEASE_SOURCES,
    fetch_release,
    ReleaseManifest,
)

__all__ = [
    "CodeRecord",
    "parse_order_file",
    "chapter_for_code",
    "category_for_code",
    "normalize_code",
    "specificity_flags_for_code",
    "CDC_NCHS_RELEASE_SOURCES",
    "fetch_release",
    "ReleaseManifest",
]
