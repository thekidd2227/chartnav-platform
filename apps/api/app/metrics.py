"""Minimal, honest in-process metrics.

Prometheus text exposition format. Single process only — same honesty
caveat as the rate limiter: multi-worker deployments should either
scrape each worker separately or plug in a proper metrics library
backed by a shared store.

Counters are intentionally narrow and audit-aligned so every metric
has a direct operator question it answers:

    requests_total                  — traffic per (method, path, status bucket)
    auth_denied_total               — every 401/403 by error_code
    rate_limited_total              — every 429 rate_limited
    audit_events_total              — cumulative audit row writes
    http_request_duration_ms_sum    — simple latency sum
    http_request_duration_ms_count  — sample count

`/metrics` is not authed. In staging/prod it should be exposed only on
the internal network (see docs/build/20-observability.md). If a caller
must go through the public edge, put the reverse proxy's IP allowlist
or basic auth in front of it.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, Tuple


class _Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total: Dict[Tuple[str, str, str], int] = defaultdict(int)
        self.auth_denied_total: Dict[str, int] = defaultdict(int)
        self.rate_limited_total: int = 0
        self.audit_events_total: Dict[str, int] = defaultdict(int)
        self.duration_sum_ms: float = 0.0
        self.duration_count: int = 0

    def observe_request(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        bucket = f"{status // 100}xx"
        with self._lock:
            self.requests_total[(method, path, bucket)] += 1
            self.duration_sum_ms += duration_ms
            self.duration_count += 1

    def observe_auth_denial(self, error_code: str) -> None:
        with self._lock:
            self.auth_denied_total[error_code or "unknown"] += 1

    def observe_rate_limited(self) -> None:
        with self._lock:
            self.rate_limited_total += 1

    def observe_audit_event(self, event_type: str) -> None:
        with self._lock:
            self.audit_events_total[event_type] += 1

    def render(self) -> str:
        lines: list[str] = []
        lines.append("# HELP chartnav_requests_total Requests by method, path, status bucket.")
        lines.append("# TYPE chartnav_requests_total counter")
        with self._lock:
            for (method, path, bucket), n in sorted(self.requests_total.items()):
                lines.append(
                    'chartnav_requests_total{method="%s",path="%s",status="%s"} %d'
                    % (method, path.replace('"', ""), bucket, n)
                )

            lines.append("# HELP chartnav_auth_denied_total Denied auth attempts by error_code.")
            lines.append("# TYPE chartnav_auth_denied_total counter")
            for code, n in sorted(self.auth_denied_total.items()):
                lines.append(
                    'chartnav_auth_denied_total{error_code="%s"} %d' % (code, n)
                )

            lines.append("# HELP chartnav_rate_limited_total 429 rate_limited responses.")
            lines.append("# TYPE chartnav_rate_limited_total counter")
            lines.append("chartnav_rate_limited_total %d" % self.rate_limited_total)

            lines.append("# HELP chartnav_audit_events_total security_audit_events writes by event_type.")
            lines.append("# TYPE chartnav_audit_events_total counter")
            for t, n in sorted(self.audit_events_total.items()):
                lines.append(
                    'chartnav_audit_events_total{event_type="%s"} %d' % (t, n)
                )

            lines.append("# HELP chartnav_http_request_duration_ms Total + count for latency.")
            lines.append("# TYPE chartnav_http_request_duration_ms_sum counter")
            lines.append("chartnav_http_request_duration_ms_sum %g" % self.duration_sum_ms)
            lines.append("# TYPE chartnav_http_request_duration_ms_count counter")
            lines.append("chartnav_http_request_duration_ms_count %d" % self.duration_count)
        return "\n".join(lines) + "\n"


metrics = _Metrics()
