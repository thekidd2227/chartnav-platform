"""Phase 21B — Ophthalmology imaging pipeline endpoints.

Read + provider-reviewed write surface for the three tables added by
``f7a8b9c0d1e2_phase_21b_imaging_pipeline``:

  * ``imaging_studies``      — one row per device-derived imaging study
  * ``imaging_files``        — per-study file METADATA (no binaries)
  * ``imaging_measurements`` — structured measurement metadata

Permission model
----------------

  * **admin**       — read / write / mark reviewed
  * **clinician**   — read / write / mark reviewed
  * **technician**  — read; create studies, file metadata, and
                      measurement rows; cannot mark a study reviewed
                      (review is the provider's act)
  * **reviewer**    — read-only across all three resources
  * **front_desk**  — no access (clinical imaging surface)

Audit
-----
Every create / patch / review records a metadata-only audit row.
``detail`` includes only IDs, modality, eye, status, and the action.
The following clinical body fields are NEVER included in audit
detail: ``notes`` (study), ``storage_uri`` / ``file_name`` (file),
``value`` (measurement).

Imaging surface is METADATA ONLY. The route layer never accepts or
stores image binaries — ``storage_uri`` is an opaque reference owned
by the practice's storage backend. The route returns ``400
binary_upload_not_supported`` if a request body looks like base64
file content rather than metadata.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_all, fetch_one, insert_returning_id, transaction


router = APIRouter()


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

_MODALITIES = {
    "oct_macula",
    "oct_rnfl",
    "fundus_photo",
    "widefield_fundus",
    "visual_field_24_2",
    "visual_field_10_2",
    "biometry_packet",
    "external_pdf",
    "other",
}
_EYE_VALUES = {"OD", "OS", "OU", "NA"}
_STUDY_STATUSES = {
    "pending_upload",
    "uploaded",
    "ready_for_review",
    "reviewed",
    "archived",
}
_FILE_KINDS = {"image", "report_pdf", "raw_export"}
_MEASUREMENT_SOURCES = {"manual", "demo", "imported_metadata"}

_ROLE_ADMIN = "admin"
_ROLE_CLINICIAN = "clinician"
_ROLE_REVIEWER = "reviewer"
_ROLE_TECHNICIAN = "technician"
_ROLE_FRONT_DESK = "front_desk"

_READ_ROLES = {
    _ROLE_ADMIN,
    _ROLE_CLINICIAN,
    _ROLE_REVIEWER,
    _ROLE_TECHNICIAN,
}
# Creating studies, files, and measurements is allowed for the people
# upstream of the provider review (clinician/admin/technician). Review
# itself is reserved for the clinical provider (clinician/admin).
_CREATE_ROLES = {_ROLE_ADMIN, _ROLE_CLINICIAN, _ROLE_TECHNICIAN}
_REVIEW_ROLES = {_ROLE_ADMIN, _ROLE_CLINICIAN}
_PATCH_ROLES = {_ROLE_ADMIN, _ROLE_CLINICIAN, _ROLE_TECHNICIAN}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _require_read_access(caller: Caller) -> None:
    if caller.role not in _READ_ROLES:
        raise _err(
            "imaging_role_forbidden",
            f"role {caller.role!r} cannot read imaging studies",
            403,
        )


def _require_create_access(caller: Caller) -> None:
    if caller.role not in _CREATE_ROLES:
        raise _err(
            "imaging_role_forbidden",
            f"role {caller.role!r} cannot create imaging records; "
            "requires admin, clinician, or technician",
            403,
        )


def _require_patch_access(caller: Caller) -> None:
    if caller.role not in _PATCH_ROLES:
        raise _err(
            "imaging_role_forbidden",
            f"role {caller.role!r} cannot update imaging studies; "
            "requires admin, clinician, or technician",
            403,
        )


def _require_review_access(caller: Caller) -> None:
    if caller.role not in _REVIEW_ROLES:
        raise _err(
            "imaging_role_forbidden",
            f"role {caller.role!r} cannot mark studies reviewed; "
            "requires admin or clinician",
            403,
        )


def _resolve_patient_in_org(patient_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM patients WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "patient_not_found",
            "patient not found in your organization",
            404,
        )
    return int(row["id"])


def _resolve_encounter_in_org(
    encounter_id: Optional[int], caller: Caller
) -> Optional[int]:
    if encounter_id is None:
        return None
    row = fetch_one(
        "SELECT id FROM encounters WHERE id = :id AND organization_id = :org",
        {"id": encounter_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return int(row["id"])


def _resolve_study_in_org(study_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM imaging_studies "
        "WHERE id = :id AND organization_id = :org",
        {"id": study_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "imaging_study_not_found",
            "imaging study not found in your organization",
            404,
        )
    return row


def _validate_modality(value: str) -> str:
    if value not in _MODALITIES:
        raise _err(
            "invalid_modality",
            f"modality must be one of {sorted(_MODALITIES)}",
            400,
        )
    return value


def _validate_eye(value: str) -> str:
    if value not in _EYE_VALUES:
        raise _err(
            "invalid_eye",
            f"eye must be one of {sorted(_EYE_VALUES)}",
            400,
        )
    return value


def _validate_status(value: str) -> str:
    if value not in _STUDY_STATUSES:
        raise _err(
            "invalid_status",
            f"status must be one of {sorted(_STUDY_STATUSES)}",
            400,
        )
    return value


def _validate_file_kind(value: str) -> str:
    if value not in _FILE_KINDS:
        raise _err(
            "invalid_file_kind",
            f"file_kind must be one of {sorted(_FILE_KINDS)}",
            400,
        )
    return value


def _validate_source(value: str) -> str:
    if value not in _MEASUREMENT_SOURCES:
        raise _err(
            "invalid_source",
            f"source must be one of {sorted(_MEASUREMENT_SOURCES)}",
            400,
        )
    return value


def _row_to_dict(row: dict) -> dict:
    out: dict[str, Any] = {}
    for k, v in row.items():
        out[k] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    detail: str,
) -> None:
    audit_record(
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


# ---------------------------------------------------------------------
# Pydantic shapes
# ---------------------------------------------------------------------


class ImagingStudyCreate(BaseModel):
    modality: str = Field(..., min_length=1, max_length=64)
    eye: str = Field(..., min_length=2, max_length=2)
    status: str = Field(default="pending_upload", max_length=32)
    captured_at: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=8000)
    encounter_id: Optional[int] = None


class ImagingStudyUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=32)
    captured_at: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=8000)


class ImagingStudyReview(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=8000)


class ImagingFileCreate(BaseModel):
    file_kind: str = Field(..., min_length=1, max_length=32)
    file_name: str = Field(..., min_length=1, max_length=500)
    storage_uri: Optional[str] = Field(default=None, max_length=1024)
    content_type: Optional[str] = Field(default=None, max_length=200)
    size_bytes: Optional[int] = Field(default=None, ge=0)
    checksum_sha256: Optional[str] = Field(default=None, max_length=128)

    @field_validator("storage_uri")
    @classmethod
    def _no_data_url(cls, v: Optional[str]) -> Optional[str]:
        # Belt-and-suspenders: reject base64 data URIs that would
        # smuggle a binary into the metadata field. Practice-owned
        # storage URIs (s3://, gs://, file://, https://) are fine.
        if v is None:
            return v
        s = v.strip()
        if s.lower().startswith("data:"):
            raise ValueError("storage_uri must be a reference URI, not a binary data URL")
        return v


class ImagingMeasurementCreate(BaseModel):
    measurement_type: str = Field(..., min_length=1, max_length=120)
    eye: str = Field(..., min_length=2, max_length=2)
    value: str = Field(..., min_length=1, max_length=64)
    unit: Optional[str] = Field(default=None, max_length=32)
    source: str = Field(default="manual", max_length=32)


# ---------------------------------------------------------------------
# Imaging studies
# ---------------------------------------------------------------------


@router.get("/patients/{patient_id}/imaging-studies")
def list_patient_imaging_studies(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    rows = fetch_all(
        "SELECT * FROM imaging_studies "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY COALESCE(captured_at, created_at) DESC, id DESC",
        {"org": caller.organization_id, "pid": pid},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/patients/{patient_id}/imaging-studies",
    status_code=status.HTTP_201_CREATED,
)
def create_patient_imaging_study(
    patient_id: int,
    payload: ImagingStudyCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_create_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    modality = _validate_modality(payload.modality)
    eye = _validate_eye(payload.eye)
    study_status = _validate_status(payload.status)
    eid = _resolve_encounter_in_org(payload.encounter_id, caller)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "imaging_studies",
            {
                "organization_id": caller.organization_id,
                "patient_id": pid,
                "encounter_id": eid,
                "modality": modality,
                "eye": eye,
                "status": study_status,
                "captured_at": payload.captured_at,
                "notes": payload.notes,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM imaging_studies WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="imaging_study_created",
        detail=(
            f"imaging_study_id={new_id} patient_id={pid} "
            f"modality={modality} eye={eye} status={study_status}"
        ),
    )
    return _row_to_dict(dict(row))


@router.get("/imaging-studies/{study_id}")
def get_imaging_study(
    study_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    row = _resolve_study_in_org(study_id, caller)
    return _row_to_dict(row)


@router.patch("/imaging-studies/{study_id}")
def patch_imaging_study(
    study_id: int,
    payload: ImagingStudyUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_patch_access(caller)
    existing = _resolve_study_in_org(study_id, caller)

    sets: dict[str, Any] = {}
    if payload.status is not None:
        sets["status"] = _validate_status(payload.status)
    if payload.captured_at is not None:
        sets["captured_at"] = payload.captured_at
    if payload.notes is not None:
        sets["notes"] = payload.notes

    if not sets:
        return _row_to_dict(existing)

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": study_id}
    for k, v in sets.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE imaging_studies SET {', '.join(set_clauses)} "
                "WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM imaging_studies WHERE id = :id"),
            {"id": study_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="imaging_study_updated",
        detail=(
            f"imaging_study_id={study_id} fields_changed={sorted(sets.keys())} "
            f"status={row['status']} eye={row['eye']} modality={row['modality']}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/imaging-studies/{study_id}/review")
def review_imaging_study(
    study_id: int,
    payload: ImagingStudyReview,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_review_access(caller)
    _resolve_study_in_org(study_id, caller)

    params: dict[str, Any] = {
        "id": study_id,
        "reviewer": caller.user_id,
    }
    sets = [
        "status = 'reviewed'",
        "reviewed_by_user_id = :reviewer",
        "reviewed_at = CURRENT_TIMESTAMP",
        "updated_at = CURRENT_TIMESTAMP",
    ]
    if payload.notes is not None:
        sets.append("notes = :notes")
        params["notes"] = payload.notes

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE imaging_studies SET {', '.join(sets)} "
                "WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM imaging_studies WHERE id = :id"),
            {"id": study_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="imaging_study_reviewed",
        detail=(
            f"imaging_study_id={study_id} reviewer_user_id={caller.user_id} "
            f"modality={row['modality']} eye={row['eye']}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Imaging files (METADATA ONLY)
# ---------------------------------------------------------------------


@router.get("/imaging-studies/{study_id}/files")
def list_imaging_files(
    study_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    _resolve_study_in_org(study_id, caller)
    rows = fetch_all(
        "SELECT * FROM imaging_files "
        "WHERE organization_id = :org AND study_id = :sid "
        "ORDER BY id DESC",
        {"org": caller.organization_id, "sid": study_id},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/imaging-studies/{study_id}/files",
    status_code=status.HTTP_201_CREATED,
)
def create_imaging_file(
    study_id: int,
    payload: ImagingFileCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_create_access(caller)
    _resolve_study_in_org(study_id, caller)
    file_kind = _validate_file_kind(payload.file_kind)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "imaging_files",
            {
                "organization_id": caller.organization_id,
                "study_id": study_id,
                "file_kind": file_kind,
                "storage_uri": payload.storage_uri,
                "file_name": payload.file_name,
                "content_type": payload.content_type,
                "size_bytes": payload.size_bytes,
                "checksum_sha256": payload.checksum_sha256,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM imaging_files WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="imaging_file_metadata_created",
        detail=(
            f"imaging_file_id={new_id} study_id={study_id} "
            f"file_kind={file_kind} size_bytes={payload.size_bytes or 0}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Imaging measurements
# ---------------------------------------------------------------------


@router.get("/imaging-studies/{study_id}/measurements")
def list_imaging_measurements(
    study_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    _resolve_study_in_org(study_id, caller)
    rows = fetch_all(
        "SELECT * FROM imaging_measurements "
        "WHERE organization_id = :org AND study_id = :sid "
        "ORDER BY id DESC",
        {"org": caller.organization_id, "sid": study_id},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/imaging-studies/{study_id}/measurements",
    status_code=status.HTTP_201_CREATED,
)
def create_imaging_measurement(
    study_id: int,
    payload: ImagingMeasurementCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_create_access(caller)
    _resolve_study_in_org(study_id, caller)
    eye = _validate_eye(payload.eye)
    source = _validate_source(payload.source)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "imaging_measurements",
            {
                "organization_id": caller.organization_id,
                "study_id": study_id,
                "measurement_type": payload.measurement_type,
                "eye": eye,
                "value": payload.value,
                "unit": payload.unit,
                "source": source,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM imaging_measurements WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="imaging_measurement_created",
        detail=(
            f"imaging_measurement_id={new_id} study_id={study_id} "
            f"measurement_type={payload.measurement_type} eye={eye} "
            f"source={source}"
        ),
    )
    return _row_to_dict(dict(row))
