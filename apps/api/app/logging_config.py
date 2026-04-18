"""Structured JSON logging for ChartNav.

One stream, line-delimited JSON, keyed fields stable across modules so
logs are easy to grep and ship.

Every request-scoped log carries `request_id`. Route handlers and
middleware inject caller context (`user_email`, `organization_id`,
`error_code`) when available.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


_STATIC_FIELDS = ("timestamp", "level", "logger", "message")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any `extra={}` fields the caller passed.
        for k, v in record.__dict__.items():
            if k in payload or k.startswith("_"):
                continue
            if k in {
                "args", "msg", "levelno", "pathname", "filename", "module",
                "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "name",
            }:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except (TypeError, ValueError):
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    root = logging.getLogger()
    root.setLevel(level)
    # Remove prior handlers so re-imports (tests) don't duplicate output.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    # Quiet uvicorn access duplication — we already log request start/end.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
