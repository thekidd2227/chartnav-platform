"""Fundus chart routes (encounter-scoped).

GET  /api/v1/encounters/{encounter_id}/fundus-charts
POST /api/v1/encounters/{encounter_id}/fundus-charts/generate
POST /api/v1/encounters/{encounter_id}/fundus-charts
GET  /api/v1/fundus-charts/{chart_id}
PATCH /api/v1/fundus-charts/{chart_id}
POST /api/v1/fundus-charts/{chart_id}/render
POST /api/v1/fundus-charts/{chart_id}/review
POST /api/v1/fundus-charts/{chart_id}/sign
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.auth import require_caller, Caller
from app.audit import record as audit_record
from app.db import engine

router = APIRouter(prefix="/api/v1", tags=["fundus-charts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class FundusChartCreate(BaseModel):
    laterality: str = Field(..., pattern="^(OD|OS|OU)$")
    drawing_json: dict[str, Any] = Field(default_factory=dict)
    findings_json: dict[str, Any] | None = None
    source_type: str = "manual"
    note_version_id: int | None = None


class FundusChartUpdate(BaseModel):
    drawing_json: dict[str, Any] | None = None
    findings_json: dict[str, Any] | None = None
    laterality: str | None = Field(None, pattern="^(OD|OS|OU)$")
    status: str | None = None


class FundusChartGenerateRequest(BaseModel):
    findings_text: str = Field(..., min_length=1)
    laterality: str | None = Field(None, pattern="^(OD|OS|OU)$")
    note_version_id: int | None = None


class FundusChartReviewRequest(BaseModel):
    notes: str | None = None


class FundusChartSignRequest(BaseModel):
    attested: bool


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_encounter(encounter_id: int, org_id: int, conn: Any) -> dict[str, Any]:
    row = conn.execute(
        text(
            "SELECT e.id, e.patient_id FROM encounters e "
            "WHERE e.id = :eid "
            "AND e.location_id IN ("
            "  SELECT id FROM locations WHERE organization_id = :oid"
            ")"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return {"id": row[0], "patient_id": row[1]}


def _get_chart(chart_id: int, org_id: int, conn: Any) -> dict[str, Any]:
    row = conn.execute(
        text(
            "SELECT id, organization_id, encounter_id, patient_id, laterality, "
            "status, source_type, findings_json, drawing_json, rendered_svg, "
            "ai_model_name, ai_confidence_json, warnings_json, "
            "reviewed_by_user_id, reviewed_at, signed_by_user_id, signed_at, "
            "created_by_user_id, created_at, updated_at "
            "FROM fundus_charts WHERE id = :cid AND organization_id = :oid"
        ),
        {"cid": chart_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Fundus chart not found")
    cols = [
        "id", "organization_id", "encounter_id", "patient_id", "laterality",
        "status", "source_type", "findings_json", "drawing_json", "rendered_svg",
        "ai_model_name", "ai_confidence_json", "warnings_json",
        "reviewed_by_user_id", "reviewed_at", "signed_by_user_id", "signed_at",
        "created_by_user_id", "created_at", "updated_at",
    ]
    return dict(zip(cols, row))


def _require_write_role(caller: Caller) -> None:
    if caller.role not in ("admin", "clinician"):
        raise HTTPException(
            status_code=403,
            detail={"error_code": "insufficient_role", "reason": "admin or clinician required"},
        )


def _require_unsigned(chart: dict[str, Any]) -> None:
    if chart["signed_at"] is not None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "chart_already_signed", "reason": "Signed charts cannot be modified"},
        )


def _deserialize(chart: dict[str, Any]) -> dict[str, Any]:
    for key in ("findings_json", "drawing_json", "ai_confidence_json", "warnings_json"):
        val = chart.get(key)
        if isinstance(val, str):
            try:
                chart[key] = json.loads(val)
            except (ValueError, TypeError):
                chart[key] = None
    return chart


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/encounters/{encounter_id}/fundus-charts")
def list_fundus_charts(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> Any:
    with engine.connect() as conn:
        _resolve_encounter(encounter_id, caller.organization_id, conn)
        rows = conn.execute(
            text(
                "SELECT id, laterality, status, source_type, "
                "reviewed_at, signed_at, created_at, updated_at "
                "FROM fundus_charts "
                "WHERE encounter_id = :eid AND organization_id = :oid "
                "ORDER BY created_at DESC"
            ),
            {"eid": encounter_id, "oid": caller.organization_id},
        ).fetchall()
    cols = ["id", "laterality", "status", "source_type",
            "reviewed_at", "signed_at", "created_at", "updated_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("/encounters/{encounter_id}/fundus-charts/generate", status_code=201)
def generate_fundus_chart(
    encounter_id: int,
    body: FundusChartGenerateRequest,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)

    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings(body.findings_text, body.laterality)

    now = _now_utc()
    # findings_json stores only metadata — no PHI
    findings_json_str = json.dumps({"raw_text_length": len(body.findings_text)})
    drawing_json_str = json.dumps(result.drawing_json)
    warnings_json_str = json.dumps(result.warnings)
    confidence_json_str = json.dumps(result.confidence)

    with engine.begin() as conn:
        enc = _resolve_encounter(encounter_id, caller.organization_id, conn)
        row = conn.execute(
            text(
                "INSERT INTO fundus_charts "
                "(created_at, updated_at, organization_id, encounter_id, patient_id, "
                "note_version_id, laterality, status, source_type, findings_json, "
                "drawing_json, ai_model_name, ai_confidence_json, warnings_json, created_by_user_id) "
                "VALUES (:created_at, :updated_at, :org_id, :enc_id, :pat_id, "
                ":nvid, :lat, 'draft', 'ai_generated', :findings_json, "
                ":drawing_json, :model, :confidence, :warnings, :creator) "
                "RETURNING id"
            ),
            {
                "created_at": now,
                "updated_at": now,
                "org_id": caller.organization_id,
                "enc_id": encounter_id,
                "pat_id": enc["patient_id"],
                "nvid": body.note_version_id,
                "lat": result.laterality,
                "findings_json": findings_json_str,
                "drawing_json": drawing_json_str,
                "model": result.ai_model_name,
                "confidence": confidence_json_str,
                "warnings": warnings_json_str,
                "creator": caller.user_id,
            },
        ).fetchone()
        chart_id = row[0]

    audit_record(
        event_type="fundus_chart_generated",
        actor_user_id=caller.user_id,
        actor_email=caller.email,
        organization_id=caller.organization_id,
        metadata={
            "chart_id": chart_id,
            "laterality": result.laterality,
            "warning_count": len(result.warnings),
        },
    )

    return {
        "chart_id": chart_id,
        "laterality": result.laterality,
        "warnings": result.warnings,
        "drawing_json": result.drawing_json,
        "ai_model_name": result.ai_model_name,
        "status": "draft",
    }


@router.post("/encounters/{encounter_id}/fundus-charts", status_code=201)
def create_fundus_chart(
    encounter_id: int,
    body: FundusChartCreate,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    now = _now_utc()
    drawing_json_str = json.dumps(body.drawing_json)
    findings_json_str = json.dumps(body.findings_json) if body.findings_json else None

    with engine.begin() as conn:
        enc = _resolve_encounter(encounter_id, caller.organization_id, conn)
        row = conn.execute(
            text(
                "INSERT INTO fundus_charts "
                "(created_at, updated_at, organization_id, encounter_id, patient_id, "
                "note_version_id, laterality, status, source_type, findings_json, "
                "drawing_json, created_by_user_id) "
                "VALUES (:created_at, :updated_at, :org_id, :enc_id, :pat_id, "
                ":nvid, :lat, 'draft', :src, :findings_json, :drawing_json, :creator) "
                "RETURNING id"
            ),
            {
                "created_at": now,
                "updated_at": now,
                "org_id": caller.organization_id,
                "enc_id": encounter_id,
                "pat_id": enc["patient_id"],
                "nvid": body.note_version_id,
                "lat": body.laterality,
                "src": body.source_type,
                "findings_json": findings_json_str,
                "drawing_json": drawing_json_str,
                "creator": caller.user_id,
            },
        ).fetchone()
        chart_id = row[0]

    audit_record(
        event_type="fundus_chart_created",
        actor_user_id=caller.user_id,
        actor_email=caller.email,
        organization_id=caller.organization_id,
        metadata={"chart_id": chart_id, "laterality": body.laterality},
    )
    return {"chart_id": chart_id, "status": "draft"}


@router.get("/fundus-charts/{chart_id}")
def get_fundus_chart(
    chart_id: int,
    caller: Caller = Depends(require_caller),
) -> Any:
    with engine.connect() as conn:
        chart = _get_chart(chart_id, caller.organization_id, conn)
    return _deserialize(chart)


@router.patch("/fundus-charts/{chart_id}")
def update_fundus_chart(
    chart_id: int,
    body: FundusChartUpdate,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    with engine.begin() as conn:
        chart = _get_chart(chart_id, caller.organization_id, conn)
        _require_unsigned(chart)
        updates: dict[str, Any] = {
            "updated_at": _now_utc(),
            "id": chart_id,
            "org_id": caller.organization_id,
        }
        sets: list[str] = ["updated_at = :updated_at"]
        if body.drawing_json is not None:
            updates["drawing_json"] = json.dumps(body.drawing_json)
            sets.append("drawing_json = :drawing_json")
        if body.findings_json is not None:
            updates["findings_json"] = json.dumps(body.findings_json)
            sets.append("findings_json = :findings_json")
        if body.laterality is not None:
            updates["laterality"] = body.laterality
            sets.append("laterality = :laterality")
        if body.status is not None:
            updates["status"] = body.status
            sets.append("status = :status")
        conn.execute(
            text(
                f"UPDATE fundus_charts SET {', '.join(sets)} "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            updates,
        )
    audit_record(
        event_type="fundus_chart_updated",
        actor_user_id=caller.user_id,
        actor_email=caller.email,
        organization_id=caller.organization_id,
        metadata={"chart_id": chart_id},
    )
    with engine.connect() as conn:
        return _deserialize(_get_chart(chart_id, caller.organization_id, conn))


@router.post("/fundus-charts/{chart_id}/render")
def render_fundus_chart(
    chart_id: int,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    with engine.connect() as conn:
        chart = _deserialize(_get_chart(chart_id, caller.organization_id, conn))

    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = chart.get("drawing_json") or {}
    svg = render_fundus_svg(drawing, laterality=chart["laterality"])

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE fundus_charts SET rendered_svg = :svg, updated_at = :now "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {"svg": svg, "now": _now_utc(), "id": chart_id, "org_id": caller.organization_id},
        )
    return {"chart_id": chart_id, "rendered_svg": svg}


@router.post("/fundus-charts/{chart_id}/review")
def review_fundus_chart(
    chart_id: int,
    body: FundusChartReviewRequest,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    now = _now_utc()
    with engine.begin() as conn:
        chart = _get_chart(chart_id, caller.organization_id, conn)
        _require_unsigned(chart)
        conn.execute(
            text(
                "UPDATE fundus_charts "
                "SET reviewed_by_user_id = :uid, reviewed_at = :now, "
                "status = 'reviewed', updated_at = :now "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {"uid": caller.user_id, "now": now, "id": chart_id, "org_id": caller.organization_id},
        )
    audit_record(
        event_type="fundus_chart_reviewed",
        actor_user_id=caller.user_id,
        actor_email=caller.email,
        organization_id=caller.organization_id,
        metadata={"chart_id": chart_id},
    )
    return {"chart_id": chart_id, "status": "reviewed", "reviewed_at": now}


@router.post("/fundus-charts/{chart_id}/sign")
def sign_fundus_chart(
    chart_id: int,
    body: FundusChartSignRequest,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    if not body.attested:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "attestation_required", "reason": "attested must be true to sign"},
        )
    now = _now_utc()
    with engine.begin() as conn:
        chart = _get_chart(chart_id, caller.organization_id, conn)
        if chart["signed_at"] is not None:
            raise HTTPException(status_code=409, detail={"error_code": "already_signed"})
        conn.execute(
            text(
                "UPDATE fundus_charts "
                "SET signed_by_user_id = :uid, signed_at = :now, "
                "status = 'signed', updated_at = :now "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {"uid": caller.user_id, "now": now, "id": chart_id, "org_id": caller.organization_id},
        )
    audit_record(
        event_type="fundus_chart_signed",
        actor_user_id=caller.user_id,
        actor_email=caller.email,
        organization_id=caller.organization_id,
        metadata={"chart_id": chart_id, "laterality": chart["laterality"]},
    )
    return {"chart_id": chart_id, "status": "signed", "signed_at": now}
