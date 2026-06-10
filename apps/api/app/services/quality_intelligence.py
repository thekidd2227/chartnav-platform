"""Phase 89 — IRIS / MIPS Quality Intelligence service.

Provider-reviewed quality documentation support. Surfaces deterministic
"is this measure applicable?", "did the provider record a response?",
and "what structured fields are still missing?" signals across the
encounter and the org. Records provider responses as structured rows
that can be exported later by a qualified operator into whatever
program-specific submission format is required.

HARD RULES — read this before changing the file.

  * ChartNav does NOT submit to CMS / IRIS / payers / registries.
    This service writes structured rows and reads them back. There
    is no transport layer in this file.
  * ChartNav does NOT autonomously compute MIPS scoring. The
    "completion_state" projection is a deterministic count of
    provider-entered responses against the spec, not a scoring
    decision.
  * ChartNav does NOT autonomously decide whether a measure is met.
    The provider records the response_type.
  * ChartNav does NOT interpret images, generate diagnoses, or
    recommend treatment based on quality state.
  * Every seeded measure spec is marked
    ``verified_for_submission = false`` until a qualified operator
    explicitly verifies it. This is enforced at the projection
    layer, not the DB.
  * Only admin / clinician may POST a response. Reviewer /
    technician / front_desk are denied.
  * Cross-org access returns 404 (no existence leak).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine, insert_returning_id


# ---------------------------------------------------------------------------
# Closed allowlists
# ---------------------------------------------------------------------------

VALID_RESPONSE_TYPES = frozenset(
    {"met", "exception", "exclusion", "not_applicable", "incomplete"}
)

VALID_SPEC_STATUSES = frozenset({"active", "inactive"})

# Internal demo / placeholder measure IDs. The projection layer marks
# these as verified_for_submission=false. A qualified operator must
# explicitly verify before any real-program use.
INTERNAL_DEMO_MEASURE_IDS = frozenset(
    {
        "chartnav_demo_ophth_dr_communication",
        "chartnav_demo_ophth_poag_iop_documentation",
        "chartnav_demo_ophth_dr_screening",
    }
)


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class QualityError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _text(name: str, value: Any, *, max_len: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QualityError(
            "invalid_text", f"{name} must be a non-empty string", 422
        )
    s = value.strip()
    if len(s) > max_len:
        raise QualityError(
            "invalid_text",
            f"{name} must be at most {max_len} characters",
            422,
        )
    return s


def _opt_text(value: Any, *, max_len: int) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise QualityError("invalid_text", "value must be string", 422)
    s = value.strip()
    if not s:
        return None
    if len(s) > max_len:
        raise QualityError(
            "invalid_text", f"value must be at most {max_len} characters", 422
        )
    return s


def _enum(name: str, value: Any, allowed: frozenset[str]) -> str:
    if value not in allowed:
        raise QualityError(
            f"invalid_{name}",
            f"{name} must be one of {sorted(allowed)}; got {value!r}",
            422,
        )
    return value


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise QualityError(
            "forbidden",
            "only admin or clinician can record a quality measure response",
            403,
        )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_encounter_or_404(
    conn, encounter_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, patient_identifier, "
            "patient_name, encounter_type FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise QualityError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return {
        "id": int(row[0]),
        "organization_id": int(row[1]),
        "patient_id": int(row[2]) if row[2] is not None else None,
        "patient_identifier": row[3],
        "patient_name": row[4],
        "encounter_type": row[5],
    }


def _actor_cache(
    conn, user_ids: Iterable[int]
) -> dict[int, dict[str, str | None]]:
    ids = sorted({int(u) for u in user_ids if u is not None})
    out: dict[int, dict[str, str | None]] = {}
    if not ids:
        return out
    placeholders = ", ".join(f":u{i}" for i in range(len(ids)))
    params = {f"u{i}": uid for i, uid in enumerate(ids)}
    rows = conn.execute(
        sa_text(
            "SELECT id, full_name, email, role FROM users "
            f"WHERE id IN ({placeholders})"
        ),
        params,
    ).fetchall()
    for uid, full_name, email, role in rows:
        out[int(uid)] = {
            "display_name": full_name or email,
            "role": role,
        }
    return out


# ---------------------------------------------------------------------------
# Row schemas
# ---------------------------------------------------------------------------

_SPEC_COLS = (
    "id",
    "organization_id",
    "measure_id",
    "measure_name",
    "program_year",
    "applicable_icd10_prefixes",
    "required_fields",
    "exception_codes",
    "status",
    "created_at",
    "updated_at",
)

_RESPONSE_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "measure_id",
    "response_type",
    "exception_code",
    "responded_by_user_id",
    "responded_at",
    "created_at",
    "updated_at",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _json_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return parsed
        return []
    return []


def _serialize_spec(record: dict[str, Any]) -> dict[str, Any]:
    measure_id = record["measure_id"]
    verified = measure_id not in INTERNAL_DEMO_MEASURE_IDS
    return {
        "id": int(record["id"]),
        "organization_id": (
            int(record["organization_id"])
            if record.get("organization_id") is not None
            else None
        ),
        "measure_id": measure_id,
        "measure_name": record["measure_name"],
        "program_year": int(record["program_year"]),
        "applicable_icd10_prefixes": _json_list(
            record.get("applicable_icd10_prefixes")
        ),
        "required_fields": _json_list(record.get("required_fields")),
        "exception_codes": _json_list(record.get("exception_codes")),
        "status": record["status"],
        "verified_for_submission": verified,
        "internal_demo_only": not verified,
        "created_at": _iso(record.get("created_at")),
        "updated_at": _iso(record.get("updated_at")),
    }


def _serialize_response(
    record: dict[str, Any],
    *,
    responder_display_name: str | None = None,
    responder_role: str | None = None,
) -> dict[str, Any]:
    return {
        "id": int(record["id"]),
        "organization_id": int(record["organization_id"]),
        "patient_id": int(record["patient_id"]),
        "encounter_id": int(record["encounter_id"]),
        "measure_id": record["measure_id"],
        "response_type": record["response_type"],
        "exception_code": record.get("exception_code"),
        "responded_by_user_id": int(record["responded_by_user_id"]),
        "responded_by_display": responder_display_name,
        "responded_by_role": responder_role,
        "responded_at": _iso(record.get("responded_at")),
        "created_at": _iso(record.get("created_at")),
        "updated_at": _iso(record.get("updated_at")),
    }


_DISCLOSURE = (
    "Provider-reviewed quality documentation support. ChartNav does NOT "
    "submit to CMS, IRIS, payers, or registries; does NOT autonomously "
    "compute MIPS scoring; does NOT autonomously decide whether a measure "
    "is met; does NOT interpret images; does NOT diagnose; does NOT "
    "recommend treatment. Measure specs flagged internal_demo_only must "
    "be verified by a qualified operator before any real-program use."
)


# ---------------------------------------------------------------------------
# Applicability + completion projection
# ---------------------------------------------------------------------------


def _structured_fields_present(
    conn, *, encounter_id: int, patient_id: int, org_id: int
) -> set[str]:
    """Return the set of structured-field codes that have observable
    evidence for the given encounter/patient.

    The field codes are intentionally generic. The spec ``required_fields``
    list references these codes, and the projection layer computes a
    diff between "required" and "present".
    """
    present: set[str] = set()

    # vitals workup row exists for this encounter
    vit = conn.execute(
        sa_text(
            "SELECT id, iop_od, iop_os FROM visit_vitals_workups "
            "WHERE encounter_id = :eid AND organization_id = :oid LIMIT 1"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if vit is not None:
        present.add("vitals_workup_recorded")
        if vit[1] is not None or vit[2] is not None:
            present.add("iop_documented")

    # scribe / visit draft signed
    scribe = conn.execute(
        sa_text(
            "SELECT id, status FROM scribe_sessions "
            "WHERE encounter_id = :eid AND organization_id = :oid LIMIT 1"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if scribe is not None:
        present.add("visit_draft_recorded")
        if scribe[1] in {"finalized", "signed"}:
            present.add("visit_draft_signed")

    # fundus chart signed
    fundus = conn.execute(
        sa_text(
            "SELECT id, status FROM fundus_charts "
            "WHERE encounter_id = :eid AND organization_id = :oid LIMIT 1"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if fundus is not None:
        present.add("fundus_chart_recorded")
        if fundus[1] == "signed":
            present.add("fundus_chart_signed")

    # disease staging row for patient
    staging = conn.execute(
        sa_text(
            "SELECT id FROM disease_stages "
            "WHERE patient_id = :pid AND organization_id = :oid LIMIT 1"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if staging is not None:
        present.add("disease_stage_documented")

    # any imaging study reviewed
    img_reviewed = conn.execute(
        sa_text(
            "SELECT id FROM imaging_studies "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "AND status = 'reviewed' LIMIT 1"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if img_reviewed is not None:
        present.add("imaging_reviewed")

    # any glaucoma-related imaging
    glauc_img = conn.execute(
        sa_text(
            "SELECT id FROM imaging_studies "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "AND modality IN ('visual_field_24_2', 'visual_field_10_2', "
            "'oct_rnfl') LIMIT 1"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if glauc_img is not None:
        present.add("glaucoma_imaging_on_file")

    return present


def _compute_applicable(
    *, spec: dict[str, Any], encounter_type: str | None
) -> bool:
    """Deterministic applicability based on the encounter_type signal.

    The spec exposes ``applicable_icd10_prefixes`` for finer matching
    in a future phase, but at present applicability is keyed off the
    encounter's subspecialty workspace profile. This is the
    conservative default — every spec is at least applicable to the
    ``comprehensive`` workspace.
    """
    measure_id = spec["measure_id"]
    if measure_id == "chartnav_demo_ophth_poag_iop_documentation":
        return encounter_type in {"glaucoma", "comprehensive", None}
    if measure_id == "chartnav_demo_ophth_dr_screening":
        return encounter_type in {"retina", "comprehensive", None}
    if measure_id == "chartnav_demo_ophth_dr_communication":
        return encounter_type in {"retina", "glaucoma", "comprehensive", None}
    # Non-demo specs default applicable to every encounter; the
    # required_fields presence check is what makes them actionable.
    return True


def _projection_for_spec(
    *,
    spec: dict[str, Any],
    response: dict[str, Any] | None,
    encounter_type: str | None,
    fields_present: set[str],
) -> dict[str, Any]:
    applicable = _compute_applicable(
        spec=spec, encounter_type=encounter_type
    )
    required = set(spec["required_fields"])
    missing = sorted(required - fields_present)

    if response is None:
        response_status = "pending" if applicable else "not_applicable"
    else:
        response_status = response["response_type"]

    return {
        "measure_id": spec["measure_id"],
        "measure_name": spec["measure_name"],
        "program_year": spec["program_year"],
        "applicable": applicable,
        "response_status": response_status,
        "response_exception_code": (
            response["exception_code"] if response else None
        ),
        "responded_by_display": (
            response["responded_by_display"] if response else None
        ),
        "responded_by_role": (
            response["responded_by_role"] if response else None
        ),
        "responded_at": response["responded_at"] if response else None,
        "missing_structured_fields": missing,
        "present_structured_fields": sorted(required & fields_present),
        "required_fields": sorted(required),
        "exception_codes": spec["exception_codes"],
        "verified_for_submission": spec["verified_for_submission"],
        "internal_demo_only": spec["internal_demo_only"],
        "submission_status": "not_submitted",
    }


# ---------------------------------------------------------------------------
# Spec lookup
# ---------------------------------------------------------------------------


def _list_active_specs(
    conn, organization_id: int, *, program_year: int | None = None
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"oid": organization_id}
    where = (
        "WHERE status = 'active' AND (organization_id IS NULL "
        "OR organization_id = :oid)"
    )
    if program_year is not None:
        where += " AND program_year = :py"
        params["py"] = int(program_year)
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_SPEC_COLS)} FROM quality_measure_specs "
            f"{where} ORDER BY measure_id, program_year DESC"
        ),
        params,
    ).fetchall()
    return [_serialize_spec(dict(zip(_SPEC_COLS, r))) for r in rows]


def _responses_for_encounter(
    conn, *, encounter_id: int, organization_id: int
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_RESPONSE_COLS)} "
            "FROM quality_measure_responses "
            "WHERE encounter_id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchall()
    raw = [dict(zip(_RESPONSE_COLS, r)) for r in rows]
    user_ids = {
        int(r["responded_by_user_id"]) for r in raw
        if r.get("responded_by_user_id") is not None
    }
    actors = _actor_cache(conn, user_ids)
    out: dict[str, dict[str, Any]] = {}
    for r in raw:
        actor = actors.get(int(r["responded_by_user_id"]))
        out[r["measure_id"]] = _serialize_response(
            r,
            responder_display_name=actor["display_name"] if actor else None,
            responder_role=actor["role"] if actor else None,
        )
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_for_encounter(
    encounter_id: int, caller: Caller, *, program_year: int | None = None
) -> dict[str, Any]:
    with engine.connect() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        if encounter["patient_id"] is None:
            raise QualityError(
                "patient_not_found",
                "encounter has no linked patient",
                404,
            )
        specs = _list_active_specs(
            conn, caller.organization_id, program_year=program_year
        )
        responses = _responses_for_encounter(
            conn,
            encounter_id=encounter["id"],
            organization_id=caller.organization_id,
        )
        fields_present = _structured_fields_present(
            conn,
            encounter_id=encounter["id"],
            patient_id=encounter["patient_id"],
            org_id=caller.organization_id,
        )

    items: list[dict[str, Any]] = []
    for spec in specs:
        projection = _projection_for_spec(
            spec=spec,
            response=responses.get(spec["measure_id"]),
            encounter_type=encounter["encounter_type"],
            fields_present=fields_present,
        )
        items.append(projection)

    applicable = [it for it in items if it["applicable"]]
    incomplete = [
        it for it in applicable
        if it["response_status"] in {"pending", "incomplete"}
    ]
    completed = [
        it for it in applicable
        if it["response_status"] in {"met", "exception", "exclusion"}
    ]
    internal_demo_present = any(it["internal_demo_only"] for it in items)

    return {
        "encounter_id": encounter["id"],
        "patient_id": encounter["patient_id"],
        "patient_identifier": encounter["patient_identifier"],
        "patient_name": encounter["patient_name"],
        "organization_id": caller.organization_id,
        "encounter_type": encounter["encounter_type"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "items": items,
        "counts": {
            "total": len(items),
            "applicable": len(applicable),
            "incomplete": len(incomplete),
            "completed": len(completed),
        },
        "supported_response_types": sorted(VALID_RESPONSE_TYPES),
        "internal_demo_specs_present": internal_demo_present,
        "submission_status": "not_submitted",
        "disclosure": _DISCLOSURE,
    }


def record_response(
    encounter_id: int,
    caller: Caller,
    *,
    measure_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _assert_write_role(caller)
    response_type = _enum(
        "response_type", payload.get("response_type"), VALID_RESPONSE_TYPES
    )
    exception_code = _opt_text(payload.get("exception_code"), max_len=64)

    if response_type != "exception" and exception_code is not None:
        # Exception codes are only meaningful with exception responses.
        raise QualityError(
            "invalid_exception_code",
            "exception_code may only be set when response_type='exception'",
            422,
        )

    with engine.begin() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        if encounter["patient_id"] is None:
            raise QualityError(
                "patient_not_found",
                "encounter has no linked patient",
                404,
            )

        # Resolve the spec — must exist (active) globally or for the org.
        spec_row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_SPEC_COLS)} FROM quality_measure_specs "
                "WHERE measure_id = :mid "
                "AND (organization_id IS NULL OR organization_id = :oid) "
                "AND status = 'active' "
                "ORDER BY program_year DESC LIMIT 1"
            ),
            {"mid": measure_id, "oid": caller.organization_id},
        ).fetchone()
        if spec_row is None:
            raise QualityError(
                "measure_spec_not_found",
                f"no active spec found for measure_id={measure_id!r}",
                404,
            )
        spec = _serialize_spec(dict(zip(_SPEC_COLS, spec_row)))

        # If exception_code is supplied, it must be in the spec's
        # exception_codes list.
        if exception_code is not None:
            allowed_codes = {
                str(c) for c in spec["exception_codes"]
            }
            if allowed_codes and exception_code not in allowed_codes:
                raise QualityError(
                    "invalid_exception_code",
                    (
                        f"exception_code {exception_code!r} not in spec "
                        f"allowlist {sorted(allowed_codes)}"
                    ),
                    422,
                )

        # Upsert by (org, encounter, measure_id).
        existing = conn.execute(
            sa_text(
                "SELECT id FROM quality_measure_responses "
                "WHERE organization_id = :oid AND encounter_id = :eid "
                "AND measure_id = :mid"
            ),
            {
                "oid": caller.organization_id,
                "eid": encounter["id"],
                "mid": measure_id,
            },
        ).fetchone()
        now = datetime.now(timezone.utc)
        if existing is not None:
            conn.execute(
                sa_text(
                    "UPDATE quality_measure_responses SET "
                    "response_type = :rt, exception_code = :ec, "
                    "responded_by_user_id = :uid, responded_at = :ts, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :id"
                ),
                {
                    "rt": response_type,
                    "ec": exception_code,
                    "uid": caller.user_id,
                    "ts": now,
                    "id": int(existing[0]),
                },
            )
            new_id = int(existing[0])
        else:
            new_id = insert_returning_id(
                conn,
                "quality_measure_responses",
                {
                    "organization_id": caller.organization_id,
                    "patient_id": encounter["patient_id"],
                    "encounter_id": encounter["id"],
                    "measure_id": measure_id,
                    "response_type": response_type,
                    "exception_code": exception_code,
                    "responded_by_user_id": caller.user_id,
                    "responded_at": now,
                },
            )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_RESPONSE_COLS)} "
                "FROM quality_measure_responses WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        record = dict(zip(_RESPONSE_COLS, row))
        actors = _actor_cache(conn, [caller.user_id])

    actor = actors.get(caller.user_id)
    return _serialize_response(
        record,
        responder_display_name=actor["display_name"] if actor else None,
        responder_role=actor["role"] if actor else None,
    )


def analytics_summary(
    caller: Caller, *, program_year: int | None = None
) -> dict[str, Any]:
    """Org-wide quality measure completion rollup.

    Deterministic counts only. Does NOT compute MIPS scoring, does NOT
    project submission readiness, does NOT decide whether the org is
    "passing." This is a workflow signal, not a payer report.
    """
    with engine.connect() as conn:
        specs = _list_active_specs(
            conn, caller.organization_id, program_year=program_year
        )

        # Pull all responses scoped to the org (and optionally filtered
        # by spec's program_year via the spec's measure_id list).
        spec_ids = [s["measure_id"] for s in specs]
        responses: list[dict[str, Any]] = []
        if spec_ids:
            placeholders = ", ".join(f":m{i}" for i in range(len(spec_ids)))
            params: dict[str, Any] = {"oid": caller.organization_id}
            for i, mid in enumerate(spec_ids):
                params[f"m{i}"] = mid
            rows = conn.execute(
                sa_text(
                    f"SELECT {', '.join(_RESPONSE_COLS)} "
                    "FROM quality_measure_responses "
                    f"WHERE organization_id = :oid AND measure_id IN ({placeholders})"
                ),
                params,
            ).fetchall()
            responses = [dict(zip(_RESPONSE_COLS, r)) for r in rows]

    per_measure: list[dict[str, Any]] = []
    for spec in specs:
        related = [r for r in responses if r["measure_id"] == spec["measure_id"]]
        bucket = {
            "met": 0,
            "exception": 0,
            "exclusion": 0,
            "not_applicable": 0,
            "incomplete": 0,
        }
        for r in related:
            t = r["response_type"]
            if t in bucket:
                bucket[t] += 1
        per_measure.append(
            {
                "measure_id": spec["measure_id"],
                "measure_name": spec["measure_name"],
                "program_year": spec["program_year"],
                "verified_for_submission": spec["verified_for_submission"],
                "internal_demo_only": spec["internal_demo_only"],
                "response_counts": bucket,
                "total_responses": sum(bucket.values()),
                "submission_status": "not_submitted",
            }
        )

    return {
        "organization_id": caller.organization_id,
        "program_year": program_year,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "measures": per_measure,
        "internal_demo_specs_present": any(
            m["internal_demo_only"] for m in per_measure
        ),
        "submission_status": "not_submitted",
        "disclosure": _DISCLOSURE,
    }


def summary_for_encounter(
    encounter_id: int, organization_id: int
) -> dict[str, Any]:
    """Lightweight metadata-only projection used by Phase 76 summary,
    Phase 77 packet, and Phase 82 note validation.
    """
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT id, patient_id, encounter_type FROM encounters "
                "WHERE id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).fetchone()
        if row is None or row[1] is None:
            return _empty_encounter_summary()
        patient_id = int(row[1])
        encounter_type = row[2]
        specs = _list_active_specs(conn, organization_id)
        responses = _responses_for_encounter(
            conn,
            encounter_id=encounter_id,
            organization_id=organization_id,
        )
        fields_present = _structured_fields_present(
            conn,
            encounter_id=encounter_id,
            patient_id=patient_id,
            org_id=organization_id,
        )

    items = [
        _projection_for_spec(
            spec=spec,
            response=responses.get(spec["measure_id"]),
            encounter_type=encounter_type,
            fields_present=fields_present,
        )
        for spec in specs
    ]
    applicable = [it for it in items if it["applicable"]]
    incomplete = [
        it for it in applicable
        if it["response_status"] in {"pending", "incomplete"}
    ]
    return {
        "total_count": len(items),
        "applicable_count": len(applicable),
        "incomplete_count": len(incomplete),
        "completed_count": len(applicable) - len(incomplete),
        "internal_demo_specs_present": any(
            it["internal_demo_only"] for it in items
        ),
        "submission_status": "not_submitted",
        "insufficient_data": len(specs) == 0,
    }


def _empty_encounter_summary() -> dict[str, Any]:
    return {
        "total_count": 0,
        "applicable_count": 0,
        "incomplete_count": 0,
        "completed_count": 0,
        "internal_demo_specs_present": False,
        "submission_status": "not_submitted",
        "insufficient_data": True,
    }


def encounters_with_incomplete_measures(
    organization_id: int,
) -> list[dict[str, Any]]:
    """Phase 81 hook — encounters with at least one applicable quality
    measure that is pending or incomplete. Informational only; never
    Tier 1.

    Only surfaces encounters where some structured clinical work has
    already started (vitals workup, visit draft, fundus chart,
    disease stage, or imaging review). An empty encounter with zero
    structured data does NOT trigger a quality item — the other
    Phase 81 sources are the surface for "this encounter has no
    work yet."
    """
    with engine.connect() as conn:
        encounters = conn.execute(
            sa_text(
                "SELECT id, patient_id FROM encounters "
                "WHERE organization_id = :oid AND patient_id IS NOT NULL"
            ),
            {"oid": organization_id},
        ).fetchall()

        # Determine which encounters have any structured work attached.
        # An encounter qualifies for quality surfacing if any of:
        # vitals workup, scribe session, fundus chart, disease stage on
        # the patient, OR an imaging study (any status) on the patient.
        encounters_with_work: set[int] = set()
        for eid_row in encounters:
            eid = int(eid_row[0])
            pid = int(eid_row[1])
            present = _structured_fields_present(
                conn,
                encounter_id=eid,
                patient_id=pid,
                org_id=organization_id,
            )
            if present:
                encounters_with_work.add(eid)

    out: list[dict[str, Any]] = []
    for eid_row in encounters:
        eid = int(eid_row[0])
        if eid not in encounters_with_work:
            continue
        pid = int(eid_row[1])
        summary = summary_for_encounter(eid, organization_id)
        if summary["incomplete_count"] > 0:
            out.append(
                {
                    "encounter_id": eid,
                    "patient_id": pid,
                    "incomplete_count": summary["incomplete_count"],
                    "applicable_count": summary["applicable_count"],
                }
            )
    out.sort(
        key=lambda r: (-r["incomplete_count"], r["encounter_id"])
    )
    return out


__all__ = [
    "QualityError",
    "VALID_RESPONSE_TYPES",
    "VALID_SPEC_STATUSES",
    "INTERNAL_DEMO_MEASURE_IDS",
    "list_for_encounter",
    "record_response",
    "analytics_summary",
    "summary_for_encounter",
    "encounters_with_incomplete_measures",
]
