"""Phase 23 — Security readiness endpoint tests.

Coverage:
  * unauthenticated → 401
  * non-admin → 403
  * admin allowed; returns metadata-only status labels
  * response never contains env values, secrets, or PHI
  * response carries the compliance disclaimer string
  * status labels reflect environment shape, not hard-coded "pass"
"""

from __future__ import annotations

import os

from tests.conftest import ADMIN1, CLIN1, FRONT1, REV1, TECH1


def _ok_labels() -> set:
    return {"configured", "missing", "required", "external_required", "disabled"}


class TestSecurityReadiness:
    def test_unauthenticated_returns_401(self, client):
        r = client.get("/admin/security/readiness")
        assert r.status_code == 401

    def test_non_admin_returns_403(self, client):
        for h in (CLIN1, REV1, TECH1, FRONT1):
            r = client.get("/admin/security/readiness", headers=h)
            assert r.status_code == 403

    def test_admin_returns_metadata_only_summary(self, client):
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert "organization_id" in body
        # Every label-style field must be in the allow-list.
        for key in (
            "auth_mode",
            "database_kind",
            "audit_retention_configured",
            "cors_explicit_configured",
            "jwt_issuer_configured",
            "jwt_audience_configured",
            "jwt_jwks_url_configured",
            "stt_provider",
            "backup_config_documented",
            "logging_config_documented",
            "monitoring_config_documented",
            "incident_contacts_documented",
            "baa_status_configured",
            "vendor_review_status_configured",
            "real_phi_go_live_gate_status",
        ):
            assert key in body, key
            assert body[key] in _ok_labels(), f"{key}={body[key]!r}"

    def test_compliance_disclaimer_present(self, client):
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        disclaimer = body.get("compliance_attestation", "")
        assert "not HIPAA-certified" in disclaimer
        assert "not approved for real PHI" in disclaimer

    def test_no_env_values_leaked(self, client, monkeypatch):
        # Set sentinel env values; verify they do not appear in any
        # field of the response body.
        sentinels = {
            "CHARTNAV_JWT_ISSUER": "SENTINEL-ISSUER",
            "CHARTNAV_JWT_AUDIENCE": "SENTINEL-AUDIENCE",
            "CHARTNAV_JWT_JWKS_URL": "https://example.invalid/SENTINEL-JWKS",
            "CHARTNAV_CORS_ALLOW_ORIGINS": "https://SENTINEL-CORS",
            "CHARTNAV_AUDIT_RETENTION_DAYS": "42",
        }
        for k, v in sentinels.items():
            monkeypatch.setenv(k, v)

        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body_text = r.text
        for v in sentinels.values():
            assert v not in body_text

    def test_dev_header_mode_reports_auth_mode_missing(self, client):
        # The test stack runs in header auth mode by default.
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["auth_mode"] == "missing"

    def test_postgres_url_reports_configured(self, client, monkeypatch):
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://chartnav:test@localhost:5432/chartnav",
        )
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["database_kind"] == "configured"

    def test_sqlite_url_reports_missing(self, client):
        # The fixture sets DATABASE_URL to sqlite:///... so this is
        # the default state.
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["database_kind"] == "missing"

    def test_stt_default_reports_disabled(self, client):
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        # Default STT provider is "stub" or "none" — both are
        # "disabled" per the endpoint contract.
        assert body["stt_provider"] == "disabled"

    def test_stt_openai_reports_external_required(self, client, monkeypatch):
        monkeypatch.setenv("CHARTNAV_STT_PROVIDER", "openai_whisper")
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["stt_provider"] == "external_required"

    def test_response_does_not_claim_compliance(self, client):
        r = client.get("/admin/security/readiness", headers=ADMIN1)
        body = r.json()
        # The compliance_attestation field intentionally contains
        # negative-assertion copy ("not HIPAA-certified", "not
        # approved for real PHI"). Scan every OTHER field for banned
        # positive claims.
        scan_text = ""
        for key, value in body.items():
            if key == "compliance_attestation":
                continue
            scan_text += " " + str(value).lower()
        # Banned positive-claim phrasings (must not appear outside
        # the disclaimer).
        for banned in (
            "hipaa compliant",
            "hipaa-compliant",
            "hipaa certified",
            "soc 2 certified",
            "certified ehr",
            "approved for real phi",
            "production-ready for phi",
            "real phi ready",
            "baa executed",
            "security approved",
        ):
            assert banned not in scan_text, (
                f"banned phrase '{banned}' appeared in non-disclaimer "
                f"field: {scan_text!r}"
            )
        # Disclaimer must be a NEGATIVE assertion — it explicitly
        # says ChartNav is NOT certified and NOT approved by default.
        disclaimer = body["compliance_attestation"].lower()
        assert "not hipaa-certified" in disclaimer
        assert "not approved for real phi" in disclaimer
