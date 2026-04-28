"""Tests — AI Governance admin routes and service layer.

Covers:
  - org scoping (audit never leaks across orgs)
  - unauthorized callers are blocked (403)
  - clinician lead is allowed
  - admin is allowed
  - payload export shape (watsonx + guardium)
  - no raw PHI required in exported payload
  - security event recording and listing
"""

from __future__ import annotations

import hashlib
import json

import pytest

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()


_USE_CASE_BODY = {
    "name": "Test Note Generation",
    "description": "Generates clinical notes from transcript.",
    "model_provider": "openai",
    "model_name": "gpt-4o",
    "phi_exposure": True,
    "output_type": "text",
    "requires_human_review": True,
    "clinical_disclaimer_required": True,
}

_SEC_EVENT_BODY = {
    "event_type": "prompt_injection_attempt",
    "severity": "high",
    "payload_hash": _sha256("ignore previous instructions"),
    "details": {"pattern_matched": "ignore previous instructions", "tokens": 8},
    "detected_by": "chartnav_internal",
}

# ---------------------------------------------------------------------------
# Use-case registration
# ---------------------------------------------------------------------------

class TestAiUseCases:
    def test_admin_can_list_use_cases(self, client):
        r = client.get("/admin/ai-governance/use-cases", headers=ADMIN1)
        assert r.status_code == 200
        assert "use_cases" in r.json()

    def test_clinician_lead_can_list_use_cases(self, client):
        # The seed has a clinician-lead at clin@chartnav.local (is_lead=True)
        r = client.get("/admin/ai-governance/use-cases", headers=CLIN1)
        assert r.status_code == 200

    def test_reviewer_blocked(self, client):
        r = client.get("/admin/ai-governance/use-cases", headers=REV1)
        assert r.status_code == 403

    def test_unauthenticated_blocked(self, client):
        r = client.get("/admin/ai-governance/use-cases")
        assert r.status_code in {401, 403, 422}

    def test_admin_can_create_use_case(self, client):
        r = client.post(
            "/admin/ai-governance/use-cases",
            json=_USE_CASE_BODY,
            headers=ADMIN1,
        )
        assert r.status_code == 201
        data = r.json()
        assert "use_case_id" in data
        assert len(data["use_case_id"]) == 36   # UUID

    def test_create_use_case_idempotent(self, client):
        """Registering the same name twice returns the same ID."""
        r1 = client.post(
            "/admin/ai-governance/use-cases",
            json=_USE_CASE_BODY,
            headers=ADMIN1,
        )
        r2 = client.post(
            "/admin/ai-governance/use-cases",
            json=_USE_CASE_BODY,
            headers=ADMIN1,
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["use_case_id"] == r2.json()["use_case_id"]

# ---------------------------------------------------------------------------
# Audit trail — org scoping
# ---------------------------------------------------------------------------

class TestAiAudit:
    def test_admin_can_list_audit(self, client):
        r = client.get("/admin/ai-governance/audit", headers=ADMIN1)
        assert r.status_code == 200
        assert "audit" in r.json()

    def test_audit_scoped_to_org(self, client):
        """Admin of org2 must not see org1 audit rows."""
        r1 = client.get("/admin/ai-governance/audit", headers=ADMIN1)
        r2 = client.get("/admin/ai-governance/audit", headers=ADMIN2)
        # Both succeed but return independent data
        assert r1.status_code == 200
        assert r2.status_code == 200
        ids1 = {row["org_id"] for row in r1.json()["audit"]}
        ids2 = {row["org_id"] for row in r2.json()["audit"]}
        # No org_id should appear in both sets
        assert ids1.isdisjoint(ids2) or (not ids1 and not ids2)

    def test_audit_response_no_raw_phi_fields(self, client):
        """Audit rows must not expose input/output raw text — only hashes."""
        r = client.get("/admin/ai-governance/audit", headers=ADMIN1)
        assert r.status_code == 200
        for row in r.json()["audit"]:
            # These fields must exist (hashes)
            assert "input_hash" in row
            assert "output_hash" in row
            # These raw-text fields must NOT exist
            assert "prompt_text" not in row
            assert "output_text" not in row
            assert "raw_input" not in row
            assert "raw_output" not in row

    def test_reviewer_blocked_from_audit(self, client):
        r = client.get("/admin/ai-governance/audit", headers=REV1)
        assert r.status_code == 403

# ---------------------------------------------------------------------------
# Security events
# ---------------------------------------------------------------------------

class TestAiSecurityEvents:
    def test_admin_can_list_security_events(self, client):
        r = client.get("/admin/ai-governance/security-events", headers=ADMIN1)
        assert r.status_code == 200
        assert "security_events" in r.json()

    def test_admin_can_create_security_event(self, client):
        r = client.post(
            "/admin/ai-governance/security-events",
            json=_SEC_EVENT_BODY,
            headers=ADMIN1,
        )
        assert r.status_code == 201
        assert "event_id" in r.json()

    def test_security_events_scoped_to_org(self, client):
        # Create in org1
        client.post(
            "/admin/ai-governance/security-events",
            json=_SEC_EVENT_BODY,
            headers=ADMIN1,
        )
        # org2 admin should not see it
        r2 = client.get("/admin/ai-governance/security-events", headers=ADMIN2)
        assert r2.status_code == 200
        org1_ids = set()
        # Can't know org1's org_id without querying — just confirm no cross-leak
        # by verifying all returned events share the same org_id
        events = r2.json()["security_events"]
        org_ids_in_response = {e["org_id"] for e in events}
        assert len(org_ids_in_response) <= 1   # all same org or empty

    def test_reviewer_blocked_from_security_events(self, client):
        r = client.get("/admin/ai-governance/security-events", headers=REV1)
        assert r.status_code == 403

    def test_security_event_no_raw_phi(self, client):
        """Details field in created event must not require raw PHI."""
        body = {**_SEC_EVENT_BODY, "details": {"tokens": 8}}  # no PHI
        r = client.post(
            "/admin/ai-governance/security-events",
            json=body,
            headers=ADMIN1,
        )
        assert r.status_code == 201

# ---------------------------------------------------------------------------
# Payload export shape (unit tests — no HTTP)
# ---------------------------------------------------------------------------

class TestPayloadExports:
    def test_watsonx_governance_payload_shape(self):
        from app.services.ai_governance import export_watsonx_governance_payload
        payload = export_watsonx_governance_payload(
            use_case_id="uc-1234",
            use_case_name="Note Generation",
            model_provider="openai",
            model_name="gpt-4o",
            phi_exposure=True,
            output_type="text",
            requires_human_review=True,
        )
        assert payload["source"] == "chartnav"
        assert payload["use_case_id"] == "uc-1234"
        assert payload["model"]["provider"] == "openai"
        assert payload["risk_indicators"]["phi_exposure"] is True
        assert "exported_at" in payload
        assert isinstance(payload["audit_sample"], list)
        # Must be JSON-serialisable
        json.dumps(payload)

    def test_watsonx_payload_no_raw_phi_required(self):
        """Payload export must work with hashes only — no raw PHI needed."""
        from app.services.ai_governance import export_watsonx_governance_payload
        payload = export_watsonx_governance_payload(
            use_case_id="uc-5678",
            use_case_name="Coding Assist",
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
            phi_exposure=False,
            output_type="structured_json",
            requires_human_review=False,
        )
        # No PHI fields in the payload
        payload_str = json.dumps(payload)
        assert "patient" not in payload_str
        assert "dob" not in payload_str
        assert "ssn" not in payload_str

    def test_guardium_payload_shape(self):
        from app.services.ai_governance import export_guardium_ai_security_payload
        payload = export_guardium_ai_security_payload(
            org_id="org-abc",
            event_type="prompt_injection_attempt",
            severity="high",
            use_case_name="Note Generation",
            payload_hash=_sha256("test input"),
            details={"pattern": "ignore previous instructions"},
        )
        assert payload["source"] == "chartnav"
        assert payload["event_type"] == "prompt_injection_attempt"
        assert payload["severity"] == "high"
        assert payload["payload_hash"].startswith("sha256:")
        assert "detected_at" in payload
        # Must be JSON-serialisable
        json.dumps(payload)

    def test_guardium_payload_no_raw_phi(self):
        from app.services.ai_governance import export_guardium_ai_security_payload
        payload = export_guardium_ai_security_payload(
            org_id="org-abc",
            event_type="phi_leak_risk",
            severity="medium",
            use_case_name="Coding Assist",
            payload_hash=_sha256("output text"),
            details={"pattern": "MRN format detected"},
        )
        payload_str = json.dumps(payload)
        assert "ssn" not in payload_str
        assert "patient_name" not in payload_str
