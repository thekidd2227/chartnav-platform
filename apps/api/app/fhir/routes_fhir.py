"""Phase 87 — FHIR R4 read-only export routes.

GET /api/fhir/r4/Patient/{patient_id}
GET /api/fhir/r4/Encounter/{encounter_id}
GET /api/fhir/r4/DocumentReference/{encounter_id}

All responses use Content-Type ``application/fhir+json``. Auth is
the existing ChartNav caller authentication; cross-org access
returns 404 (no existence leak). There are no write routes — this
is a read-only export surface, not an EHR write-back layer.

Out-of-scope for Phase 87 (intentionally NOT implemented):

  * HL7 v2 message interfaces
  * Write-back to upstream EHRs
  * Bidirectional sync
  * SMART-on-FHIR / OAuth provider flows
  * Bulk export ($export, NDJSON)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse

from app.auth import Caller, require_caller
from app.fhir.document_reference_adapter import (
    build_document_reference_resource,
)
from app.fhir.encounter_adapter import build_encounter_resource
from app.fhir.patient_adapter import (
    FhirExportError,
    build_patient_resource,
)

router = APIRouter(prefix="/api/fhir/r4", tags=["fhir-export"])

FHIR_JSON_MEDIA_TYPE = "application/fhir+json"


def _operation_outcome(
    severity: str, code: str, diagnostics: str
) -> dict[str, Any]:
    return {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": severity,
                "code": code,
                "diagnostics": diagnostics,
            }
        ],
    }


def _fhir_response(payload: dict[str, Any], *, status_code: int = 200):
    return JSONResponse(
        content=payload,
        status_code=status_code,
        media_type=FHIR_JSON_MEDIA_TYPE,
    )


def _translate(exc: FhirExportError) -> JSONResponse:
    severity = "error" if exc.status_code >= 400 else "information"
    code = "not-found" if exc.status_code == 404 else "exception"
    return _fhir_response(
        _operation_outcome(severity, code, exc.reason),
        status_code=exc.status_code,
    )


@router.get("/Patient/{patient_id}")
def get_patient(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> Response:
    try:
        return _fhir_response(build_patient_resource(patient_id, caller))
    except FhirExportError as exc:
        return _translate(exc)


@router.get("/Encounter/{encounter_id}")
def get_encounter(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> Response:
    try:
        return _fhir_response(build_encounter_resource(encounter_id, caller))
    except FhirExportError as exc:
        return _translate(exc)


@router.get("/DocumentReference/{encounter_id}")
def get_document_reference(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> Response:
    try:
        return _fhir_response(
            build_document_reference_resource(encounter_id, caller)
        )
    except FhirExportError as exc:
        return _translate(exc)


__all__ = ["router", "FHIR_JSON_MEDIA_TYPE"]


# A defensive HTTPException placeholder; FastAPI requires the
# import for some lint configs even when not directly used.
_ = HTTPException
