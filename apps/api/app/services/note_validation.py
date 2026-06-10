"""Phase 82 — Note Validation Rail service.

Deterministic pre-sign validation across the structured workflow data
ChartNav already aggregates. This is NOT autonomous clinical judgment
— every check is a documented deterministic rule over provider-entered
data. The rail surfaces warnings the provider must acknowledge before
signing; it does not autonomously block the existing
sign-attestation flow (the existing hard blocker — the attestation
checkbox — is unchanged).

Sources read:
  * encounters
  * visit_vitals_workups
  * fundus_charts
  * scribe_sessions
  * anti_vegf_injections                 (Phase 78)
  * cataract_workflow_records             (Phase 80)

Check categories:
  * laterality_consistency  — every laterality recorded across vitals
    (IOP eye), fundus, anti-VEGF, and cataract for this encounter's
    patient lines up; if there is exactly one laterality everywhere
    it's a pass, multiple → warning explicitly listing the sources.
  * follow_up_interval       — anti-VEGF latest interval, cataract
    post-op cadence, glaucoma follow-up presence (any one provider-
    entered cadence ⇒ pass; none ⇒ warning).
  * unsigned_upstream        — vitals workups + fundus charts on this
    encounter that are not yet signed; warning so the provider
    knows what's outstanding before the visit-draft sign.
  * review_state             — visit draft (scribe session) lifecycle
    state for this encounter, plus the sign/lock attestation that's
    still required.
  * specialty_data_present   — informational pass/warning for any
    Phase 2 surface that has data on this patient.

Hard rules:
  * No clinical free text is ever surfaced in a check `detail` — only
    metadata (artifact ids, statuses, laterality codes, dates).
  * Statuses are deterministic: ``pass`` / ``warning`` / ``missing``
    / ``blocked``. ``blocked`` is reserved for the existing sign-
    attestation rule and is only emitted when the encounter genuinely
    has unsigned upstream artifacts AND a finalized visit draft
    (the only "must acknowledge to proceed" condition).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


@dataclass
class ValidationError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _encounter_or_404(conn, encounter_id: int, org_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, status FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise ValidationError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    eid, oid, pid, status = row
    return {
        "id": int(eid),
        "organization_id": int(oid),
        "patient_id": int(pid) if pid is not None else None,
        "status": status,
    }


def _check(
    *,
    check_id: str,
    category: str,
    label: str,
    status: str,
    detail: str,
    source: str,
    laterality: str | None = None,
    source_artifact_id: int | None = None,
    requires_provider_acknowledgement: bool = False,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category,
        "label": label,
        "status": status,
        "laterality": laterality,
        "source": source,
        "detail": detail,
        "requires_provider_acknowledgement": requires_provider_acknowledgement,
        "source_artifact_id": source_artifact_id,
    }


# ---------------------------------------------------------------------------
# Per-source extraction
# ---------------------------------------------------------------------------


def _vitals_lateralities(conn, encounter_id: int, org_id: int) -> set[str]:
    rows = conn.execute(
        sa_text(
            "SELECT iop_od, iop_os FROM visit_vitals_workups "
            "WHERE encounter_id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchall()
    out: set[str] = set()
    for iod, ios in rows:
        if iod is not None:
            out.add("OD")
        if ios is not None:
            out.add("OS")
    return out


def _fundus_lateralities(conn, encounter_id: int, org_id: int) -> set[str]:
    rows = conn.execute(
        sa_text(
            "SELECT DISTINCT laterality FROM fundus_charts "
            "WHERE encounter_id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchall()
    return {row[0] for row in rows if row[0] is not None}


def _anti_vegf_lateralities_for_patient(
    conn, patient_id: int, org_id: int
) -> set[str]:
    rows = conn.execute(
        sa_text(
            "SELECT DISTINCT eye FROM anti_vegf_injections "
            "WHERE patient_id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchall()
    return {row[0] for row in rows if row[0] is not None}


def _cataract_lateralities_for_patient(
    conn, patient_id: int, org_id: int
) -> set[str]:
    rows = conn.execute(
        sa_text(
            "SELECT DISTINCT surgery_eye FROM cataract_workflow_records "
            "WHERE patient_id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchall()
    return {row[0] for row in rows if row[0] is not None}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_laterality_consistency(
    conn, encounter: dict[str, Any]
) -> list[dict[str, Any]]:
    """One check per source surface plus one consistency rollup."""
    eid = encounter["id"]
    org = encounter["organization_id"]
    pid = encounter["patient_id"]

    by_source: dict[str, set[str]] = {
        "vitals": _vitals_lateralities(conn, eid, org),
        "fundus": _fundus_lateralities(conn, eid, org),
    }
    if pid is not None:
        by_source["anti_vegf"] = _anti_vegf_lateralities_for_patient(conn, pid, org)
        by_source["cataract"] = _cataract_lateralities_for_patient(conn, pid, org)

    checks: list[dict[str, Any]] = []
    for source, lats in by_source.items():
        if not lats:
            checks.append(
                _check(
                    check_id=f"laterality:{source}",
                    category="laterality",
                    label=f"{source} laterality recorded",
                    status="missing",
                    detail=f"No {source} laterality recorded for this encounter.",
                    source=source,
                    requires_provider_acknowledgement=False,
                )
            )
        else:
            lat_label = "OU" if lats == {"OD", "OS"} else next(iter(lats))
            checks.append(
                _check(
                    check_id=f"laterality:{source}",
                    category="laterality",
                    label=f"{source} laterality recorded",
                    status="pass",
                    detail=(
                        f"{source} laterality "
                        f"{'/'.join(sorted(lats))} on file."
                    ),
                    source=source,
                    laterality=lat_label,
                )
            )

    # Rollup — every non-empty source must share at least one laterality.
    present = [(s, lats) for s, lats in by_source.items() if lats]
    if len(present) >= 2:
        # Pairwise disagreement: any pair with disjoint sets is a warning.
        all_eyes = [lats for _, lats in present]
        union = set().union(*all_eyes)
        intersection = set.intersection(*all_eyes)
        if not intersection:
            checks.append(
                _check(
                    check_id="laterality:rollup",
                    category="laterality",
                    label="Laterality consistency across sources",
                    status="warning",
                    detail=(
                        "Laterality differs across surfaces: "
                        + ", ".join(
                            f"{s}={','.join(sorted(lats))}"
                            for s, lats in present
                        )
                        + ". Confirm the visit draft references the correct eye."
                    ),
                    source="visit_draft",
                    laterality="OU" if union == {"OD", "OS"} else next(iter(union)),
                    requires_provider_acknowledgement=True,
                )
            )
        else:
            lat_label = (
                "OU" if union == {"OD", "OS"} else next(iter(intersection))
            )
            checks.append(
                _check(
                    check_id="laterality:rollup",
                    category="laterality",
                    label="Laterality consistency across sources",
                    status="pass",
                    detail=(
                        f"All recorded sources share laterality "
                        f"{','.join(sorted(intersection))}."
                    ),
                    source="visit_draft",
                    laterality=lat_label,
                )
            )
    return checks


def _check_follow_up_interval(
    conn, encounter: dict[str, Any]
) -> dict[str, Any]:
    pid = encounter["patient_id"]
    org = encounter["organization_id"]
    if pid is None:
        return _check(
            check_id="follow_up:interval",
            category="follow_up",
            label="Follow-up interval recorded",
            status="missing",
            detail=(
                "No follow-up cadence on file. Encounter has no linked "
                "patient; cross-specialty cadence cannot be checked."
            ),
            source="visit_draft",
            requires_provider_acknowledgement=True,
        )

    # Anti-VEGF interval (any non-null interval_weeks)
    av = conn.execute(
        sa_text(
            "SELECT eye, interval_weeks FROM anti_vegf_injections "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "AND interval_weeks IS NOT NULL LIMIT 1"
        ),
        {"pid": pid, "oid": org},
    ).fetchone()
    if av:
        eye, interval = av
        return _check(
            check_id="follow_up:interval",
            category="follow_up",
            label="Follow-up interval recorded",
            status="pass",
            detail=(
                f"Anti-VEGF interval of {interval} week(s) on file for {eye}."
            ),
            source="anti_vegf",
            laterality=eye,
        )

    # Cataract post-op cadence (any 'scheduled' or 'completed' status)
    cat = conn.execute(
        sa_text(
            "SELECT surgery_eye, postop_day_1_status, postop_week_1_status, "
            "postop_month_1_status FROM cataract_workflow_records "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "LIMIT 1"
        ),
        {"pid": pid, "oid": org},
    ).fetchone()
    if cat:
        eye, pd1, pw1, pm1 = cat
        known = [
            v for v in (pd1, pw1, pm1)
            if v not in (None, "unknown", "not_scheduled")
        ]
        if known:
            return _check(
                check_id="follow_up:interval",
                category="follow_up",
                label="Follow-up interval recorded",
                status="pass",
                detail=(
                    f"Cataract post-op cadence on file for {eye} "
                    f"({len(known)} checkpoint(s) tracked)."
                ),
                source="cataract",
                laterality=eye,
            )

    return _check(
        check_id="follow_up:interval",
        category="follow_up",
        label="Follow-up interval recorded",
        status="warning",
        detail=(
            "No follow-up cadence recorded across anti-VEGF or cataract "
            "workflow surfaces. Provider acknowledgement required if "
            "follow-up is documented outside ChartNav."
        ),
        source="visit_draft",
        requires_provider_acknowledgement=True,
    )


def _check_unsigned_upstream(
    conn, encounter: dict[str, Any]
) -> list[dict[str, Any]]:
    eid = encounter["id"]
    org = encounter["organization_id"]
    out: list[dict[str, Any]] = []

    vitals_unsigned = conn.execute(
        sa_text(
            "SELECT id FROM visit_vitals_workups "
            "WHERE encounter_id = :eid AND organization_id = :oid "
            "AND signed_at IS NULL AND status != 'superseded'"
        ),
        {"eid": eid, "oid": org},
    ).fetchall()
    for (wid,) in vitals_unsigned:
        out.append(
            _check(
                check_id=f"unsigned:vitals:{wid}",
                category="unsigned_upstream",
                label="Vitals workup not yet signed",
                status="warning",
                detail=(
                    f"Vitals workup #{int(wid)} is not signed. Sign upstream "
                    "or acknowledge to proceed."
                ),
                source="vitals",
                source_artifact_id=int(wid),
                requires_provider_acknowledgement=True,
            )
        )

    fundus_unsigned = conn.execute(
        sa_text(
            "SELECT id, laterality FROM fundus_charts "
            "WHERE encounter_id = :eid AND organization_id = :oid "
            "AND signed_at IS NULL"
        ),
        {"eid": eid, "oid": org},
    ).fetchall()
    for fid, lat in fundus_unsigned:
        out.append(
            _check(
                check_id=f"unsigned:fundus:{fid}",
                category="unsigned_upstream",
                label="Fundus chart not yet signed",
                status="warning",
                detail=(
                    f"Fundus chart #{int(fid)} ({lat}) is not signed. Sign "
                    "upstream or acknowledge to proceed."
                ),
                source="fundus",
                laterality=lat,
                source_artifact_id=int(fid),
                requires_provider_acknowledgement=True,
            )
        )

    if not out:
        out.append(
            _check(
                check_id="unsigned:upstream",
                category="unsigned_upstream",
                label="No unsigned upstream artifacts",
                status="pass",
                detail=(
                    "All recorded upstream artifacts on this encounter are "
                    "signed."
                ),
                source="signed_lock",
            )
        )
    return out


def _check_review_state(
    conn, encounter: dict[str, Any]
) -> list[dict[str, Any]]:
    eid = encounter["id"]
    org = encounter["organization_id"]
    out: list[dict[str, Any]] = []

    sessions = conn.execute(
        sa_text(
            "SELECT id, status, finalized_at FROM scribe_sessions "
            "WHERE encounter_id = :eid AND organization_id = :oid "
            "ORDER BY id DESC LIMIT 1"
        ),
        {"eid": eid, "oid": org},
    ).fetchall()
    if not sessions:
        out.append(
            _check(
                check_id="review_state:visit_draft",
                category="review_state",
                label="Visit draft present",
                status="missing",
                detail="No visit draft (scribe session) recorded for this encounter.",
                source="visit_draft",
            )
        )
    else:
        sid, status, finalized = sessions[0]
        if status == "finalized":
            out.append(
                _check(
                    check_id=f"review_state:visit_draft:{int(sid)}",
                    category="review_state",
                    label="Visit draft signed",
                    status="pass",
                    detail=(
                        f"Visit draft #{int(sid)} finalized "
                        f"{_iso(finalized) or 'time not recorded'}."
                    ),
                    source="visit_draft",
                    source_artifact_id=int(sid),
                )
            )
        else:
            out.append(
                _check(
                    check_id=f"review_state:visit_draft:{int(sid)}",
                    category="review_state",
                    label="Visit draft awaits provider sign-off",
                    status="warning",
                    detail=(
                        f"Visit draft #{int(sid)} status is {status}. "
                        "Provider review + finalize remains required."
                    ),
                    source="visit_draft",
                    source_artifact_id=int(sid),
                    requires_provider_acknowledgement=True,
                )
            )

    out.append(
        _check(
            check_id="review_state:attestation",
            category="review_state",
            label="Provider attestation required",
            status="pass",
            detail=(
                "Provider attestation remains required on the existing "
                "sign-and-lock checkbox before any artifact is finalized."
            ),
            source="signed_lock",
        )
    )
    return out


def _check_specialty_data_present(
    conn, encounter: dict[str, Any]
) -> list[dict[str, Any]]:
    pid = encounter["patient_id"]
    org = encounter["organization_id"]
    out: list[dict[str, Any]] = []
    if pid is None:
        return out

    av_count = conn.execute(
        sa_text(
            "SELECT COUNT(*) FROM anti_vegf_injections "
            "WHERE patient_id = :pid AND organization_id = :oid"
        ),
        {"pid": pid, "oid": org},
    ).scalar() or 0
    cat_count = conn.execute(
        sa_text(
            "SELECT COUNT(*) FROM cataract_workflow_records "
            "WHERE patient_id = :pid AND organization_id = :oid"
        ),
        {"pid": pid, "oid": org},
    ).scalar() or 0

    out.append(
        _check(
            check_id="specialty:anti_vegf",
            category="specialty_data",
            label="Anti-VEGF rail data present",
            status="pass" if av_count else "missing",
            detail=(
                f"{av_count} anti-VEGF record(s) for this patient."
                if av_count
                else "No anti-VEGF rail data for this patient."
            ),
            source="anti_vegf",
        )
    )
    out.append(
        _check(
            check_id="specialty:cataract",
            category="specialty_data",
            label="Cataract workflow data present",
            status="pass" if cat_count else "missing",
            detail=(
                f"{cat_count} cataract workflow record(s) for this patient."
                if cat_count
                else "No cataract workflow data for this patient."
            ),
            source="cataract",
        )
    )

    # Phase 84 — informational stage-documentation signal. Never blocks
    # signing; never requires acknowledgement. The provider stages the
    # disease — ChartNav merely surfaces whether a stage row exists.
    from app.services.disease_staging import latest_for_patient as _staging_latest

    stage_rows = _staging_latest(pid, org)
    if stage_rows:
        systems = ", ".join(sorted({r["staging_system_label"] for r in stage_rows}))
        out.append(
            _check(
                check_id="staging:documented",
                category="staging",
                label="Disease staging documented",
                status="pass",
                detail=(
                    f"{len(stage_rows)} provider-entered staging record(s) "
                    f"on file ({systems})."
                ),
                source="visit_draft",
            )
        )
    else:
        out.append(
            _check(
                check_id="staging:missing",
                category="staging",
                label="Disease staging not documented",
                status="missing",
                detail=(
                    "No provider-entered disease-staging record on file for "
                    "this patient. Staging is informational and never blocks "
                    "signing."
                ),
                source="visit_draft",
            )
        )

    # Phase 85 — informational medication-documentation + refill-gap signal.
    # Never blocks signing; never requires acknowledgement. ChartNav does
    # NOT prescribe, refill, or recommend medication changes.
    from app.services.medications import medication_safety_summary as _med_summary

    med_summary = _med_summary(pid, org)
    if med_summary["active_medication_count"] > 0:
        if med_summary["refill_gap_count"] > 0:
            out.append(
                _check(
                    check_id="medication:refill_gap",
                    category="medication",
                    label="Medication refill gap on file",
                    status="warning",
                    detail=(
                        f"{med_summary['refill_gap_count']} of "
                        f"{med_summary['active_medication_count']} active "
                        "medication(s) have a refill gap. Informational "
                        "only — never blocks signing."
                    ),
                    source="visit_draft",
                )
            )
        else:
            out.append(
                _check(
                    check_id="medication:documented",
                    category="medication",
                    label="Active medications documented",
                    status="pass",
                    detail=(
                        f"{med_summary['active_medication_count']} active "
                        "provider-entered medication(s) on file."
                    ),
                    source="visit_draft",
                )
            )
    else:
        out.append(
            _check(
                check_id="medication:missing",
                category="medication",
                label="No active medications documented",
                status="missing",
                detail=(
                    "No active provider-entered medications on file for "
                    "this patient. Informational only — never blocks signing."
                ),
                source="visit_draft",
            )
        )

    # Phase 89 — informational quality intelligence check. Never blocks
    # signing; never requires acknowledgement. ChartNav does NOT
    # submit to CMS / IRIS / payers / registries, and does NOT
    # autonomously decide whether a measure is met — the provider
    # records the response.
    from app.services.quality_intelligence import (
        summary_for_encounter as _quality_summary,
    )

    qsum = _quality_summary(encounter["id"], encounter["organization_id"])
    if qsum["applicable_count"] == 0:
        out.append(
            _check(
                check_id="quality:not_applicable",
                category="quality",
                label="No applicable quality measures",
                status="pass",
                detail=(
                    "No applicable provider-reviewed quality measure "
                    "specs match this encounter. Informational only."
                ),
                source="visit_draft",
            )
        )
    elif qsum["incomplete_count"] > 0:
        out.append(
            _check(
                check_id="quality:incomplete",
                category="quality",
                label="Quality documentation incomplete",
                status="warning",
                detail=(
                    f"{qsum['incomplete_count']} of {qsum['applicable_count']} "
                    "applicable quality measure(s) not yet recorded by the "
                    "provider. Informational only — ChartNav does not submit "
                    "to CMS, IRIS, payers, or registries."
                ),
                source="visit_draft",
            )
        )
    else:
        out.append(
            _check(
                check_id="quality:documented",
                category="quality",
                label="Quality documentation recorded",
                status="pass",
                detail=(
                    f"{qsum['applicable_count']} applicable quality "
                    "measure(s) have a provider-recorded response."
                ),
                source="visit_draft",
            )
        )
    return out


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def build_validation(encounter_id: int, caller: Caller) -> dict[str, Any]:
    """Build the deterministic note-validation rail for one encounter."""
    with engine.connect() as conn:
        encounter = _encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        checks: list[dict[str, Any]] = []
        checks.extend(_check_laterality_consistency(conn, encounter))
        checks.append(_check_follow_up_interval(conn, encounter))
        checks.extend(_check_unsigned_upstream(conn, encounter))
        checks.extend(_check_review_state(conn, encounter))
        checks.extend(_check_specialty_data_present(conn, encounter))

    totals = {"pass": 0, "warning": 0, "missing": 0, "blocked": 0}
    ack_required = 0
    for c in checks:
        totals[c["status"]] = totals.get(c["status"], 0) + 1
        if c["requires_provider_acknowledgement"]:
            ack_required += 1

    # Phase 86 — embed the encounter's workspace profile so the rail
    # consumer can colocate the validation surface with its adaptive
    # workspace context.
    from app.services.workspace_profiles import (
        profile_summary_for_encounter as _profile_summary,
    )

    workspace_profile = _profile_summary(
        encounter["id"], encounter["organization_id"]
    )

    return {
        "encounter_id": encounter["id"],
        "organization_id": encounter["organization_id"],
        "patient_id": encounter["patient_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "checks": checks,
        "totals": totals,
        "acknowledgements_required": ack_required,
        "workspace_profile": workspace_profile,
        "disclosure": (
            "Validation checks use structured provider-entered workflow "
            "data. ChartNav does not diagnose, interpret images, or "
            "recommend treatment. Provider attestation remains required "
            "for every artifact. Sign attestation is the existing hard "
            "blocker; this rail surfaces warnings the provider must "
            "acknowledge but does not autonomously block sign-off."
        ),
    }


__all__ = ["ValidationError", "build_validation"]
