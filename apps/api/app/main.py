from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.admin_security import router as admin_security_router
from app.api.anti_vegf_injections import router as anti_vegf_injections_router
from app.api.cataract_workflow import router as cataract_workflow_router
from app.api.consent import router as consent_router
from app.api.eye_diagrams import router as eye_diagrams_router
from app.api.fundus_charts import router as fundus_charts_router
from app.api.glaucoma_summary import router as glaucoma_summary_router
from app.api.imaging_pipeline import router as imaging_pipeline_router
from app.api.multi_clinic import router as multi_clinic_router
from app.api.note_validation import router as note_validation_router
from app.api.patient_summaries import router as patient_summaries_router
from app.api.pre_visit_briefs import router as pre_visit_briefs_router
from app.api.provider_action_items import router as provider_action_items_router
from app.api.provider_action_queue import router as provider_action_queue_router
from app.api.retina_visit_packet import router as retina_visit_packet_router
from app.api.retina_visit_summary import router as retina_visit_summary_router
from app.api.role_dashboards import router as role_dashboards_router
from app.api.routes import router
from app.api.scribe_sessions import router as scribe_sessions_router
from app.api.specialty_tracking import router as specialty_tracking_router
from app.api.structured_data import router as structured_data_router
from app.api.vitals_workup import router as vitals_workup_router
from app.audit import record as audit_record, should_audit
from app.config import settings
from app.logging_config import configure_logging
from app.middleware import (
    AccessLogMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
)
from app.services.stt_provider import install_default as _install_stt_provider

_install_stt_provider()

configure_logging()
log = logging.getLogger("chartnav")

app = FastAPI(title="ChartNav Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-User-Email", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail: Any = exc.detail
    error_code = None
    reason = None
    if isinstance(detail, dict):
        error_code = detail.get("error_code")
        reason = detail.get("reason")

    if should_audit(exc.status_code, error_code):
        try:
            from app.metrics import metrics as _metrics
            _metrics.observe_auth_denial(error_code or f"http_{exc.status_code}")
        except Exception:  # pragma: no cover
            pass
        caller = getattr(request.state, "caller", None)
        audit_record(
            event_type=error_code or f"http_{exc.status_code}",
            request_id=getattr(request.state, "request_id", None),
            actor_email=getattr(caller, "email", None),
            actor_user_id=getattr(caller, "user_id", None),
            organization_id=getattr(caller, "organization_id", None),
            path=request.url.path,
            method=request.method,
            error_code=error_code,
            detail=str(reason) if reason else None,
            remote_addr=(request.client.host if request.client else None),
        )
        log.warning(
            "auth_denied",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
                "status": exc.status_code,
                "error_code": error_code,
                "user_email": getattr(caller, "email", None),
                "organization_id": getattr(caller, "organization_id", None),
            },
        )

    headers = dict(exc.headers or {})
    rid = getattr(request.state, "request_id", None)
    if rid:
        headers.setdefault("X-Request-ID", rid)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=headers,
    )


app.include_router(router)
app.include_router(admin_security_router)
app.include_router(anti_vegf_injections_router)
app.include_router(cataract_workflow_router)
app.include_router(consent_router)
app.include_router(eye_diagrams_router)
app.include_router(fundus_charts_router)
app.include_router(glaucoma_summary_router)
app.include_router(scribe_sessions_router)
app.include_router(patient_summaries_router)
app.include_router(pre_visit_briefs_router)
app.include_router(provider_action_items_router)
app.include_router(provider_action_queue_router)
app.include_router(retina_visit_packet_router)
app.include_router(retina_visit_summary_router)
app.include_router(structured_data_router)
app.include_router(role_dashboards_router)
app.include_router(specialty_tracking_router)
app.include_router(imaging_pipeline_router)
app.include_router(multi_clinic_router)
app.include_router(note_validation_router)
app.include_router(vitals_workup_router)
