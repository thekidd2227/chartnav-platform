from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.routes import router
from app.audit import record as audit_record, should_audit
from app.config import settings
from app.logging_config import configure_logging
from app.middleware import (
    AccessLogMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
)
from app.services.stt_provider import install_default as _install_stt_provider

# Phase 33 → Phase 35 — wire the configured STT provider at import
# time. `CHARTNAV_STT_PROVIDER` picks between:
#   "stub"           (default; deterministic placeholder for dev/test)
#   "openai_whisper" (real OpenAI Whisper; requires
#                     CHARTNAV_OPENAI_API_KEY)
#   "none"           (explicitly no STT; audio uploads fail honestly)
# A vendor-specific adapter can still overwrite the registration via
# `app.services.ingestion.set_transcriber(...)` or
# `app.services.stt_provider.install_provider(...)` after this line.
_install_stt_provider()

configure_logging()
log = logging.getLogger("chartnav")

app = FastAPI(title="ChartNav Platform API", version="0.1.0")

# --- CORS ----------------------------------------------------------------
# `allow_origins=["*"]` is intentionally NOT used. CORS is driven by
# `CHARTNAV_CORS_ALLOW_ORIGINS` (see docs/build/12-runtime-config.md).
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-User-Email", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# --- Operational middleware ---------------------------------------------
# Order: rate limit is innermost (shortcut before access log / routing),
# access log wraps the route, request id is outermost so downstream sees
# the id even if something below throws.
app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIdMiddleware)


# --- HTTP exception handler — audits denied/suspicious traffic ----------

@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail: Any = exc.detail
    error_code = None
    reason = None
    if isinstance(detail, dict):
        error_code = detail.get("error_code")
        reason = detail.get("reason")

    if should_audit(exc.status_code, error_code):
        # Observe metric (fails-closed — wrapped in try inside metrics module).
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
