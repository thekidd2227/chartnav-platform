"""Observability surface tests: /ready, /metrics, and metric counters
updating on real request paths."""

from __future__ import annotations

from tests.conftest import ADMIN1


def test_ready_returns_ok(client):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"


def test_metrics_prometheus_text(client):
    # Drive a couple of requests so we have something to count.
    client.get("/health")
    client.get("/me")  # 401
    client.get("/me", headers=ADMIN1)  # 200

    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")

    body = r.text
    assert "chartnav_requests_total" in body
    assert "chartnav_auth_denied_total" in body
    assert "chartnav_audit_events_total" in body
    assert "chartnav_http_request_duration_ms_sum" in body
    # We hit /me without auth above — that should have incremented an
    # auth denial metric.
    assert 'error_code="missing_auth_header"' in body


def test_metrics_counts_rate_limited(monkeypatch, tmp_path):
    # Reuse the operational fixture so we get a tight rate limit.
    from tests.test_operational import _fresh_client_with_env

    client = _fresh_client_with_env(
        monkeypatch, tmp_path, CHARTNAV_RATE_LIMIT_PER_MINUTE="2"
    )
    client.get("/me", headers=ADMIN1)
    client.get("/me", headers=ADMIN1)
    r = client.get("/me", headers=ADMIN1)
    assert r.status_code == 429

    metrics_text = client.get("/metrics").text
    # The rate-limited counter should be at least 1
    import re
    m = re.search(r"^chartnav_rate_limited_total (\d+)", metrics_text, re.MULTILINE)
    assert m and int(m.group(1)) >= 1, metrics_text
