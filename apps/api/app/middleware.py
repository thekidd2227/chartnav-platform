"""Operational middleware — request IDs, structured access logs,
in-memory rate limiting.

Rate limiting here is **per-process**, in-memory, sliding-window. It is
a real protection against trivial abuse, not a distributed limiter.
Multi-process deploys should sit behind an edge layer that rate limits
globally; this prevents a single uvicorn worker from melting but won't
coordinate across workers. The docs call that out explicitly.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Callable, Deque, Iterable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("chartnav.http")


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a stable request id to every request.

    Honors a caller-provided `X-Request-ID` if it's a reasonable length;
    otherwise generates a fresh UUID4. Always echoed on the response.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        inbound = request.headers.get("x-request-id", "").strip()
        rid = inbound if 0 < len(inbound) <= 64 else uuid.uuid4().hex
        request.state.request_id = rid
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """One structured log line per request with useful fields."""

    async def dispatch(self, request: Request, call_next: Callable):
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            # Let the exception propagate; still emit a failure log.
            log.exception(
                "request failed",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        caller = getattr(request.state, "caller", None)
        # Metrics observation (honest in-process counters)
        from app.metrics import metrics as _metrics
        _metrics.observe_request(
            request.method, request.url.path, response.status_code, duration_ms
        )
        log.info(
            "request",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_email": getattr(caller, "email", None),
                "organization_id": getattr(caller, "organization_id", None),
                "remote_addr": _client_ip(request),
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window limiter.

    Protects the path prefixes in `protected_prefixes` (defaults to all
    paths the rest of the app actually cares about).

    Key = (client_ip, path). Window = 60s. Limit = `per_minute`.
    Returns 429 with a stable `{error_code: "rate_limited"}` envelope.
    """

    def __init__(
        self,
        app,
        per_minute: int,
        protected_prefixes: Iterable[str] = (
            "/me",
            "/encounters",
            "/organizations",
            "/locations",
            "/users",
        ),
    ):
        super().__init__(app)
        self.per_minute = per_minute
        self.protected = tuple(protected_prefixes)
        self._buckets: dict[tuple[str, str], Deque[float]] = defaultdict(deque)

    def _protected(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in self.protected)

    async def dispatch(self, request: Request, call_next: Callable):
        if self.per_minute <= 0 or not self._protected(request.url.path):
            return await call_next(request)

        key = (_client_ip(request), request.url.path)
        now = time.time()
        window = self._buckets[key]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.per_minute:
            # Defer audit import to avoid circular at module load time.
            from app.audit import record as audit_record
            from app.metrics import metrics as _metrics
            _metrics.observe_rate_limited()

            rid = getattr(request.state, "request_id", None)
            audit_record(
                event_type="rate_limited",
                request_id=rid,
                path=request.url.path,
                method=request.method,
                error_code="rate_limited",
                remote_addr=_client_ip(request),
                detail=f"per_minute={self.per_minute}",
            )
            from starlette.responses import JSONResponse

            resp = JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "error_code": "rate_limited",
                        "reason": (
                            f"too many requests (>{self.per_minute}/min "
                            f"for this client+path)"
                        ),
                    }
                },
            )
            if rid:
                resp.headers["X-Request-ID"] = rid
            return resp

        window.append(now)
        return await call_next(request)
