"""Phase 84 — Disease Staging Protocol Engine service.

Provider-entered disease staging records keyed to a
``(patient, encounter, diagnosis_code, staging_system)`` quadruple.

Hard rules:

  * ChartNav does NOT autonomously stage disease. The provider must
    POST an explicit ``stage_value``. No interpretation from imaging,
    vitals, IOP, OCT, or VF data.
  * ``progression_detected`` is a deterministic equality between the
    POST's provider-entered ``stage_value`` and the most-recent prior
    row's ``stage_value`` for the same patient + diagnosis. It is
    computed at read time; it is never persisted.
  * ``elapsed_days_since_prior`` is a deterministic delta against the
    most-recent prior row's ``staged_at`` for the same patient +
    diagnosis. Computed at read time.
  * The summary projection never includes free text. The full record
    response includes only the persisted columns and the two derived
    fields above.
  * Only admin / clinician may POST a stage. Reviewer / front_desk
    / technician are denied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine, insert_returning_id


# ---------------------------------------------------------------------------
# Allowed (staging_system, stage_value) pairs — closed allowlist.
# ---------------------------------------------------------------------------

STAGING_SYSTEM_LABELS: dict[str, str] = {
    "amd_areds": "AMD · AREDS",
    "diabetic_etdrs": "Diabetic Retinopathy · ETDRS",
    "glaucoma_poag": "Glaucoma · POAG",
    "keratoconus_amsler_krumeich": "Keratoconus · Amsler-Krumeich",
    "dry_eye_dews": "Dry Eye · DEWS",
}

STAGE_VALUES_BY_SYSTEM: dict[str, tuple[str, ...]] = {
    "amd_areds": (
        "Category 1",
        "Category 2",
        "Category 3",
        "Category 4",
    ),
    "diabetic_etdrs": (
        "Mild NPDR",
        "Moderate NPDR",
        "Severe NPDR",
        "Non-high-risk PDR",
        "High-risk PDR",
        "Advanced",
    ),
    "glaucoma_poag": (
        "Mild",
        "Moderate",
        "Severe",
    ),
    "keratoconus_amsler_krumeich": (
        "Stage I",
        "Stage II",
        "Stage III",
        "Stage IV",
    ),
    "dry_eye_dews": (
        "Severity 1",
        "Severity 2",
        "Severity 3",
        "Severity 4",
    ),
}

VALID_STAGING_SYSTEMS = frozenset(STAGING_SYSTEM_LABELS.keys())


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class StagingError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_text(name: str, value: Any, *, max_len: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StagingError(
            "invalid_text", f"{name} must be a non-empty string", 422
        )
    s = value.strip()
    if len(s) > max_len:
        raise StagingError(
            "invalid_text",
            f"{name} must be at most {max_len} characters",
            422,
        )
    return s


def _validate_staging_system(value: Any) -> str:
    if value not in VALID_STAGING_SYSTEMS:
        raise StagingError(
            "invalid_staging_system",
            f"staging_system must be one of {sorted(VALID_STAGING_SYSTEMS)}; "
            f"got {value!r}",
            422,
        )
    return value


def _validate_stage_value(staging_system: str, value: Any) -> str:
    if not isinstance(value, str):
        raise StagingError(
            "invalid_stage_value",
            "stage_value must be a string",
            422,
        )
    allowed = STAGE_VALUES_BY_SYSTEM[staging_system]
    if value not in allowed:
        raise StagingError(
            "invalid_stage_value",
            (
                f"stage_value {value!r} is not valid for staging_system "
                f"{staging_system!r}; allowed values: {list(allowed)}"
            ),
            422,
        )
    return value


def _validate_prior_stage(staging_system: str, value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise StagingError(
            "invalid_prior_stage",
            "prior_stage must be a string or null",
            422,
        )
    allowed = STAGE_VALUES_BY_SYSTEM[staging_system]
    if value not in allowed:
        raise StagingError(
            "invalid_prior_stage",
            (
                f"prior_stage {value!r} is not valid for staging_system "
                f"{staging_system!r}; allowed values: {list(allowed)}"
            ),
            422,
        )
    return value


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise StagingError(
            "forbidden",
            "only admin or clinician can record a disease stage",
            403,
        )


# ---------------------------------------------------------------------------
# Resolve patient / encounter
# ---------------------------------------------------------------------------


def _resolve_patient_or_404(
    conn, patient_id: int, org_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise StagingError("patient_not_found", "patient not found", 404)
    pid, pident, first, last = row
    name_parts = [p for p in (first, last) if p]
    return {
        "id": int(pid),
        "patient_identifier": pident,
        "patient_name": " ".join(name_parts) if name_parts else None,
    }


def _resolve_encounter_or_404(
    conn, encounter_id: int, org_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise StagingError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    eid, oid, pid = row
    return {
        "id": int(eid),
        "organization_id": int(oid),
        "patient_id": int(pid) if pid is not None else None,
    }


def _actor_display(conn, user_id: int) -> dict[str, str | None]:
    row = conn.execute(
        sa_text("SELECT full_name, email, role FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    if row is None:
        return {"display_name": None, "role": None}
    full_name, email, role = row
    return {"display_name": full_name or email, "role": role}


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------


_ROW_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "diagnosis_code",
    "staging_system",
    "stage_value",
    "prior_stage",
    "staged_at",
    "staged_by_user_id",
    "created_at",
    "updated_at",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            # Tolerate "YYYY-MM-DD HH:MM:SS" (SQLite default).
            s = value.replace(" ", "T")
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def _serialize(
    row: dict[str, Any],
    *,
    actor_display_name: str | None = None,
    actor_role: str | None = None,
    progression_detected: bool | None = None,
    elapsed_days_since_prior: int | None = None,
) -> dict[str, Any]:
    out = {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "encounter_id": int(row["encounter_id"])
        if row.get("encounter_id") is not None
        else None,
        "diagnosis_code": row["diagnosis_code"],
        "staging_system": row["staging_system"],
        "staging_system_label": STAGING_SYSTEM_LABELS.get(
            row["staging_system"], row["staging_system"]
        ),
        "stage_value": row["stage_value"],
        "prior_stage": row.get("prior_stage"),
        "staged_at": _iso(row.get("staged_at")),
        "staged_by_user_id": int(row["staged_by_user_id"])
        if row.get("staged_by_user_id") is not None
        else None,
        "staged_by_display_name": actor_display_name,
        "staged_by_role": actor_role,
        "progression_detected": progression_detected,
        "elapsed_days_since_prior": elapsed_days_since_prior,
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }
    return out


def _compute_derived_fields(
    *,
    current_stage: str,
    prior_stage: str | None,
    current_staged_at: Any,
    prior_staged_at: Any,
) -> tuple[bool | None, int | None]:
    """Deterministic (progression_detected, elapsed_days_since_prior).

    Never autonomous interpretation — pure equality + date subtraction.
    """
    progression: bool | None
    if prior_stage is None:
        progression = None
    else:
        progression = prior_stage != current_stage

    elapsed: int | None = None
    cur_dt = _parse_iso(current_staged_at)
    prior_dt = _parse_iso(prior_staged_at)
    if cur_dt is not None and prior_dt is not None:
        delta = cur_dt - prior_dt
        elapsed = max(0, int(delta.total_seconds() // 86400))

    return progression, elapsed


def _previous_row_for(
    conn, *, patient_id: int, diagnosis_code: str, before_id: int | None = None
) -> dict[str, Any] | None:
    params: dict[str, Any] = {"pid": patient_id, "dx": diagnosis_code}
    where = (
        "WHERE patient_id = :pid AND diagnosis_code = :dx"
    )
    if before_id is not None:
        where += " AND id < :bid"
        params["bid"] = before_id
    row = conn.execute(
        sa_text(
            f"SELECT {', '.join(_ROW_COLS)} FROM disease_stages {where} "
            "ORDER BY staged_at DESC, id DESC LIMIT 1"
        ),
        params,
    ).fetchone()
    if row is None:
        return None
    return dict(zip(_ROW_COLS, row))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_stage(
    encounter_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    _assert_write_role(caller)

    diagnosis_code = _validate_text(
        "diagnosis_code", payload.get("diagnosis_code"), max_len=64
    )
    staging_system = _validate_staging_system(payload.get("staging_system"))
    stage_value = _validate_stage_value(
        staging_system, payload.get("stage_value")
    )
    prior_stage = _validate_prior_stage(
        staging_system, payload.get("prior_stage")
    )

    with engine.begin() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        if encounter["patient_id"] is None:
            raise StagingError(
                "patient_not_found",
                "encounter has no linked patient",
                404,
            )
        patient = _resolve_patient_or_404(
            conn, encounter["patient_id"], caller.organization_id
        )
        actor = _actor_display(conn, caller.user_id)

        prior_row = _previous_row_for(
            conn, patient_id=patient["id"], diagnosis_code=diagnosis_code
        )

        new_id = insert_returning_id(
            conn,
            "disease_stages",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient["id"],
                "encounter_id": encounter["id"],
                "diagnosis_code": diagnosis_code,
                "staging_system": staging_system,
                "stage_value": stage_value,
                "prior_stage": prior_stage,
                "staged_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM disease_stages "
                "WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        record = dict(zip(_ROW_COLS, row))

    progression, elapsed = _compute_derived_fields(
        current_stage=record["stage_value"],
        prior_stage=prior_row["stage_value"] if prior_row else prior_stage,
        current_staged_at=record["staged_at"],
        prior_staged_at=prior_row["staged_at"] if prior_row else None,
    )

    return _serialize(
        record,
        actor_display_name=actor["display_name"],
        actor_role=actor["role"],
        progression_detected=progression,
        elapsed_days_since_prior=elapsed,
    )


def list_for_patient(
    patient_id: int, caller: Caller, *, diagnosis_code: str | None = None
) -> dict[str, Any]:
    with engine.connect() as conn:
        patient = _resolve_patient_or_404(
            conn, patient_id, caller.organization_id
        )
        params: dict[str, Any] = {
            "pid": patient["id"],
            "oid": caller.organization_id,
        }
        where = "WHERE patient_id = :pid AND organization_id = :oid"
        if diagnosis_code:
            where += " AND diagnosis_code = :dx"
            params["dx"] = diagnosis_code
        rows = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM disease_stages {where} "
                "ORDER BY staged_at DESC, id DESC"
            ),
            params,
        ).fetchall()

        actor_cache: dict[int, dict[str, str | None]] = {}
        # Resolve actor display names in one pass.
        user_ids = {
            int(r[_ROW_COLS.index("staged_by_user_id")])
            for r in rows
            if r[_ROW_COLS.index("staged_by_user_id")] is not None
        }
        if user_ids:
            placeholders = ", ".join(f":u{i}" for i in range(len(user_ids)))
            uparams: dict[str, Any] = {}
            for i, uid in enumerate(sorted(user_ids)):
                uparams[f"u{i}"] = uid
            urows = conn.execute(
                sa_text(
                    "SELECT id, full_name, email, role FROM users "
                    f"WHERE id IN ({placeholders})"
                ),
                uparams,
            ).fetchall()
            for uid, full_name, email, role in urows:
                actor_cache[int(uid)] = {
                    "display_name": full_name or email,
                    "role": role,
                }

    serialized: list[dict[str, Any]] = []
    # Walk rows newest-first; the "prior" row for each is the next row in the
    # same diagnosis_code group (already adjacent because we ordered newest
    # first).
    by_dx: dict[str, list[dict[str, Any]]] = {}
    raw_records = [dict(zip(_ROW_COLS, r)) for r in rows]
    for rec in raw_records:
        by_dx.setdefault(rec["diagnosis_code"], []).append(rec)

    for rec in raw_records:
        dx_group = by_dx[rec["diagnosis_code"]]
        # Find the index of this record in the dx group (deterministic).
        idx = next(i for i, r in enumerate(dx_group) if r["id"] == rec["id"])
        prior = dx_group[idx + 1] if idx + 1 < len(dx_group) else None
        progression, elapsed = _compute_derived_fields(
            current_stage=rec["stage_value"],
            prior_stage=prior["stage_value"] if prior else rec.get("prior_stage"),
            current_staged_at=rec["staged_at"],
            prior_staged_at=prior["staged_at"] if prior else None,
        )
        actor = actor_cache.get(
            int(rec["staged_by_user_id"]) if rec.get("staged_by_user_id") else 0,
            {"display_name": None, "role": None},
        )
        serialized.append(
            _serialize(
                rec,
                actor_display_name=actor["display_name"],
                actor_role=actor["role"],
                progression_detected=progression,
                elapsed_days_since_prior=elapsed,
            )
        )

    # Latest per (diagnosis_code, staging_system) map for the summary panel.
    latest_by_diagnosis: dict[str, dict[str, Any]] = {}
    for rec in serialized:
        key = rec["diagnosis_code"]
        if key not in latest_by_diagnosis:
            latest_by_diagnosis[key] = rec

    return {
        "patient_id": patient["id"],
        "patient_identifier": patient["patient_identifier"],
        "patient_name": patient["patient_name"],
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "records": serialized,
        "latest_by_diagnosis": latest_by_diagnosis,
        "supported_systems": [
            {"code": code, "label": label, "stages": list(STAGE_VALUES_BY_SYSTEM[code])}
            for code, label in STAGING_SYSTEM_LABELS.items()
        ],
        "disclosure": (
            "Disease staging records are provider-entered. ChartNav does "
            "not stage disease, does not interpret imaging to derive a "
            "stage, does not infer progression, and does not recommend "
            "treatment or surgery. Progression flags are deterministic "
            "equality checks against the previous provider-entered stage."
        ),
    }


def latest_for_patient(
    patient_id: int, organization_id: int
) -> list[dict[str, Any]]:
    """Latest stage per diagnosis_code for one patient.

    Used by Phase 76 retina visit summary, Phase 77 packet export, Phase
    81 provider action queue, and Phase 82 note validation to surface
    structured stage metadata. Returns lightweight projections.

    ``progression_detected`` is a deterministic equality check against
    the most recent prior provider-entered row in the same diagnosis
    group (falling back to the row's persisted ``prior_stage`` column
    if no earlier row exists).
    """
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text(
                "SELECT diagnosis_code, staging_system, stage_value, "
                "prior_stage, staged_at, id "
                "FROM disease_stages "
                "WHERE patient_id = :pid AND organization_id = :oid "
                "ORDER BY diagnosis_code ASC, staged_at DESC, id DESC"
            ),
            {"pid": patient_id, "oid": organization_id},
        ).fetchall()

    # Bucket by diagnosis_code preserving newest-first order so the
    # "previous" row is index+1 within the same group.
    by_dx: dict[str, list[tuple[Any, ...]]] = {}
    for row in rows:
        by_dx.setdefault(row[0], []).append(row)

    out: list[dict[str, Any]] = []
    for dx, dx_rows in by_dx.items():
        dx_code, system, stage, prior, staged_at, rid = dx_rows[0]
        # Derive prior stage from the next-to-latest row in the group if
        # the persisted prior_stage is NULL.
        derived_prior = prior
        if derived_prior is None and len(dx_rows) > 1:
            derived_prior = dx_rows[1][2]
        progression: bool | None
        if derived_prior is None:
            progression = None
        else:
            progression = derived_prior != stage
        out.append(
            {
                "id": int(rid),
                "diagnosis_code": dx_code,
                "staging_system": system,
                "staging_system_label": STAGING_SYSTEM_LABELS.get(system, system),
                "stage_value": stage,
                "prior_stage": derived_prior,
                "staged_at": _iso(staged_at),
                "progression_detected": progression,
            }
        )
    return out


def patients_missing_recent_stage(
    organization_id: int,
) -> list[dict[str, Any]]:
    """Return patients with at least one Phase 78/79/80 record but no
    disease-staging row on file. Used by Phase 81 provider action queue
    as an informational ('Low' priority) item.

    Cataract surgical workflow is intentionally excluded — cataract
    staging is not part of the Phase 84 allowlist. Only retina (anti-VEGF)
    and glaucoma activity triggers a "missing stage" hint.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text(
                "SELECT DISTINCT p.id, p.patient_identifier, p.first_name, p.last_name "
                "FROM patients p WHERE p.organization_id = :oid AND ("
                "  EXISTS (SELECT 1 FROM anti_vegf_injections a "
                "          WHERE a.patient_id = p.id AND a.organization_id = :oid) "
                "  OR EXISTS (SELECT 1 FROM visit_vitals_workups v "
                "             WHERE v.patient_id = p.id AND v.organization_id = :oid "
                "             AND (v.iop_od IS NOT NULL OR v.iop_os IS NOT NULL)) "
                ") AND NOT EXISTS ("
                "  SELECT 1 FROM disease_stages s WHERE s.patient_id = p.id "
                "  AND s.organization_id = :oid"
                ")"
            ),
            {"oid": organization_id},
        ).fetchall()

    out: list[dict[str, Any]] = []
    for pid, pident, first, last in rows:
        name_parts = [p for p in (first, last) if p]
        out.append(
            {
                "patient_id": int(pid),
                "patient_identifier": pident,
                "patient_name": " ".join(name_parts) if name_parts else None,
            }
        )
    return out


__all__ = [
    "StagingError",
    "STAGING_SYSTEM_LABELS",
    "STAGE_VALUES_BY_SYSTEM",
    "VALID_STAGING_SYSTEMS",
    "create_stage",
    "list_for_patient",
    "latest_for_patient",
    "patients_missing_recent_stage",
]
