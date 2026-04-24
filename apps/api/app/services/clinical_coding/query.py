"""Query-side helpers for the Clinical Coding Intelligence feature."""
from __future__ import annotations

from datetime import date
from typing import Optional

from app.db import fetch_one, fetch_all


def active_version() -> dict | None:
    """Return the currently-preferred version row (is_active = 1)."""
    return fetch_one(
        "SELECT id, version_label, source_authority, source_url, release_date, "
        "effective_start_date, effective_end_date, is_active, parse_status, "
        "checksum_sha256, downloaded_at, parsed_at, activated_at "
        "FROM icd10cm_versions WHERE is_active = 1 LIMIT 1"
    )


def resolve_version_for_date(date_of_service: date | str | None) -> dict | None:
    """Return the version that applies to a given DOS. If no date
    is provided, fall back to active_version().

    An ICD-10-CM release's window is
    [effective_start_date, effective_end_date] inclusive. When the
    end is NULL the release is treated as open-ended."""
    if not date_of_service:
        return active_version()
    if isinstance(date_of_service, date):
        dos = date_of_service.isoformat()
    else:
        dos = str(date_of_service)
    row = fetch_one(
        "SELECT id, version_label, source_authority, source_url, release_date, "
        "effective_start_date, effective_end_date, is_active, parse_status, "
        "checksum_sha256, downloaded_at, parsed_at, activated_at "
        "FROM icd10cm_versions "
        "WHERE parse_status = 'ready' "
        "AND effective_start_date <= :dos "
        "AND (effective_end_date IS NULL OR effective_end_date >= :dos) "
        "ORDER BY effective_start_date DESC LIMIT 1",
        {"dos": dos},
    )
    return row or active_version()


def search_codes(
    q: str,
    *,
    version_id: int,
    limit: int = 25,
    specialty_tag: Optional[str] = None,
    billable_only: bool = False,
) -> list[dict]:
    """Search by code prefix OR descriptive text."""
    q = (q or "").strip()
    if not q:
        return []
    # If the user types "H40" we search by code prefix; otherwise
    # by descriptive text. A leading letter + digit is treated as
    # a code.
    is_codey = len(q) >= 2 and q[0].isalpha() and q[1].isdigit()
    clauses = ["version_id = :v"]
    params: dict = {"v": version_id, "lim": int(limit)}
    if is_codey:
        clauses.append("normalized_code LIKE :code_prefix")
        params["code_prefix"] = q.replace(".", "").upper() + "%"
    else:
        clauses.append("(long_description LIKE :qq OR short_description LIKE :qq)")
        params["qq"] = f"%{q}%"
    if billable_only:
        clauses.append("is_billable = 1")
    where = " AND ".join(clauses)
    return fetch_all(
        f"SELECT id, code, normalized_code, is_billable, short_description, "
        f"long_description, chapter_code, chapter_title, category_code, "
        f"parent_code, specificity_flags "
        f"FROM icd10cm_codes WHERE {where} "
        f"ORDER BY is_billable DESC, code ASC LIMIT :lim",
        params,
    )


def get_code_detail(code: str, *, version_id: int) -> dict | None:
    """Return one code row + its children and parent."""
    from .specialty import hints_for_code
    norm = code.replace(".", "").upper()
    row = fetch_one(
        "SELECT id, code, normalized_code, is_billable, short_description, "
        "long_description, chapter_code, chapter_title, category_code, "
        "parent_code, specificity_flags, source_file, source_line_no "
        "FROM icd10cm_codes WHERE version_id = :v AND normalized_code = :n",
        {"v": version_id, "n": norm},
    )
    if not row:
        return None
    children = fetch_all(
        "SELECT code, short_description, is_billable "
        "FROM icd10cm_codes WHERE version_id = :v AND parent_code = :p "
        "ORDER BY code LIMIT 50",
        {"v": version_id, "p": row["code"]},
    )
    from app.db import transaction
    with transaction() as conn:
        hints = hints_for_code(conn, row["code"], version_id=version_id)
    return {**row, "children": children, "support_hints": hints}
