"""Phase 25A / GH-002 — STT readiness admin endpoint.

`GET /admin/security/stt-readiness` reports which STT provider the
operator has wired and whether the upload pipeline will accept audio.
It MUST NOT return secrets or API key values. It MUST gate on admin
role.

Tests cover:
- admin sees the payload
- reviewer / clinician → 403
- unauthenticated → 401
- stub provider (default): no egress, accepts audio
- explicit `none`: no egress, rejects audio
- `openai_whisper` with key: requires egress, accepts audio,
  real_phi_ready stays False (operator sign-off only)
- `openai_whisper` without key: boot will fail, real_phi_ready False
- unknown provider key: provider_key_recognized=False
- response never contains the API key value
"""

from __future__ import annotations

import json

from tests.conftest import ADMIN1, CLIN1, REV1


def _get(client, headers=None):
    return client.get("/admin/security/stt-readiness", headers=headers or {})


def test_admin_can_read_stt_readiness(client):
    r = _get(client, ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organization_id"] == 1
    assert "provider_key_raw" in body
    assert "provider_key_recognized" in body
    assert "openai_api_key_present" in body
    assert "upload_behavior" in body
    assert "external_egress" in body
    assert "real_phi_ready" in body
    assert "guidance" in body
    # ChartNav never claims HIPAA compliance via self-introspection.
    assert "HIPAA" in body["guidance"] or "BAA" in body["guidance"]


def test_reviewer_cannot_read_stt_readiness(client):
    r = _get(client, REV1)
    assert r.status_code == 403, r.text


def test_clinician_cannot_read_stt_readiness(client):
    r = _get(client, CLIN1)
    assert r.status_code == 403, r.text


def test_unauthenticated_cannot_read_stt_readiness(client):
    r = _get(client)
    assert r.status_code in (401, 403), r.text


def test_default_provider_is_stub_no_egress(client, monkeypatch):
    monkeypatch.delenv("CHARTNAV_STT_PROVIDER", raising=False)
    r = _get(client, ADMIN1)
    body = r.json()
    assert body["provider_key_raw"] == "stub"
    assert body["provider_key_recognized"] is True
    assert body["upload_behavior"] == "accepts_returns_placeholder_transcript"
    assert body["external_egress"] == "no"
    assert body["real_phi_ready"] is False


def test_none_provider_blocks_uploads(client, monkeypatch):
    monkeypatch.setenv("CHARTNAV_STT_PROVIDER", "none")
    r = _get(client, ADMIN1)
    body = r.json()
    assert body["provider_key_raw"] == "none"
    assert body["upload_behavior"] == "rejects_no_transcriber_installed"
    assert body["external_egress"] == "no"
    assert body["real_phi_ready"] is False


def test_openai_whisper_with_key_reports_external_required(client, monkeypatch):
    monkeypatch.setenv("CHARTNAV_STT_PROVIDER", "openai_whisper")
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-test-fake-key-never-leaves-env")
    r = _get(client, ADMIN1)
    body = r.json()
    assert body["provider_key_raw"] == "openai_whisper"
    assert body["openai_api_key_present"] is True
    assert body["upload_behavior"] == "accepts_calls_openai_whisper"
    assert body["external_egress"] == "required"
    # Operator sign-off is off-runtime; we never auto-flip this.
    assert body["real_phi_ready"] is False
    # PII safety: payload must never echo the key value.
    assert "sk-test-fake-key-never-leaves-env" not in json.dumps(body)


def test_openai_whisper_without_key_reports_boot_will_fail(client, monkeypatch):
    monkeypatch.setenv("CHARTNAV_STT_PROVIDER", "openai_whisper")
    monkeypatch.delenv("CHARTNAV_OPENAI_API_KEY", raising=False)
    r = _get(client, ADMIN1)
    body = r.json()
    assert body["openai_api_key_present"] is False
    assert body["upload_behavior"] == "boot_will_fail"
    assert body["real_phi_ready"] is False


def test_unknown_provider_key_recognized_false(client, monkeypatch):
    monkeypatch.setenv("CHARTNAV_STT_PROVIDER", "vendor_that_does_not_exist")
    r = _get(client, ADMIN1)
    body = r.json()
    assert body["provider_key_recognized"] is False
    assert body["upload_behavior"] == "boot_will_fail"
    assert body["external_egress"] == "unknown"
    assert body["real_phi_ready"] is False


def test_real_phi_ready_is_always_false_even_with_full_openai_config(client, monkeypatch):
    """ChartNav never auto-flips real_phi_ready=True. Operator sign-off
    via the docs/security/chartnav-real-phi-go-live-gate.md is required.
    This guard ensures a future refactor cannot accidentally flip this."""
    monkeypatch.setenv("CHARTNAV_STT_PROVIDER", "openai_whisper")
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-anything")
    r = _get(client, ADMIN1)
    assert r.json()["real_phi_ready"] is False
