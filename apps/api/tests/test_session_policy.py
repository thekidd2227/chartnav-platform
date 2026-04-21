"""Phase 47 — session policy seam.

Validates:
  - `IdPClaims.from_jwt_payload` maps `mfa`, `amr`, `acr`, `groups`.
  - `_amr_looks_mfa` recognizes the expected token family.
  - `resolve_session_policy` defaults to OFF for every org.
  - `require_mfa` is a no-op when the org has not opted in.
  - `require_mfa` in header-auth mode is always permissive (dev).
"""
from __future__ import annotations

from tests.conftest import ADMIN1


def test_idp_claims_from_payload_flags_mfa():
    from app.session_policy import IdPClaims
    c = IdPClaims.from_jwt_payload({
        "sub": "user-1",
        "email": "x@y.z",
        "mfa": True,
    })
    assert c.subject == "user-1"
    assert c.email == "x@y.z"
    assert c.mfa_authenticated is True


def test_idp_claims_amr_detects_mfa_tokens():
    from app.session_policy import IdPClaims
    c = IdPClaims.from_jwt_payload({"amr": ["pwd", "otp"]})
    assert c.amr == ["pwd", "otp"]
    assert c.mfa_authenticated is True


def test_idp_claims_without_mfa_claims_is_false():
    from app.session_policy import IdPClaims
    c = IdPClaims.from_jwt_payload({"amr": ["pwd"]})
    assert c.mfa_authenticated is False


def test_idp_claims_groups_string_coerced_to_list():
    from app.session_policy import IdPClaims
    c = IdPClaims.from_jwt_payload({"groups": "ophthalmology-admins"})
    assert c.groups == ["ophthalmology-admins"]


def test_session_policy_defaults_off_for_seeded_orgs(client):
    # Seeded orgs have no session policy flags set — default is OFF.
    r = client.get("/me", headers=ADMIN1)
    assert r.status_code == 200
    org_id = r.json()["organization_id"]

    from app.session_policy import resolve_session_policy
    policy = resolve_session_policy(org_id)
    assert policy.require_mfa is False
    assert policy.idle_timeout_minutes is None
    assert policy.absolute_timeout_minutes is None


def test_require_mfa_is_noop_when_org_has_not_opted_in(client):
    """`require_mfa` is a FastAPI dependency; calling it against a
    seeded org with no `require_mfa` flag set must return the caller
    unchanged (no 403)."""
    # Sanity: existing admin route still works without any MFA claim
    # because the seeded orgs have `require_mfa = False`.
    r = client.get("/admin/kpi/overview", headers=ADMIN1)
    assert r.status_code == 200


def test_require_mfa_permissive_in_header_mode_with_flag_on(
    client, test_db, monkeypatch
):
    """When header-auth mode is on (dev), `require_mfa` does not
    block callers even if the org's policy has `require_mfa=True`.
    That matches the seam doc: header mode is assumed MFA-present
    so developer loops don't have to forge claims."""
    import sqlite3
    import json

    # Flip the seeded org1's policy ON.
    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT id, settings FROM organizations WHERE slug = 'demo-eye-clinic'"
        ).fetchone()
        assert row is not None
        org_id, settings_raw = row
        settings_blob = json.loads(settings_raw) if settings_raw else {}
        settings_blob.setdefault("feature_flags", {})["require_mfa"] = True
        conn.execute(
            "UPDATE organizations SET settings = :s WHERE id = :id",
            {"s": json.dumps(settings_blob), "id": org_id},
        )
        conn.commit()
    finally:
        conn.close()

    from app.session_policy import resolve_session_policy
    assert resolve_session_policy(org_id).require_mfa is True

    # Header-auth callers still succeed (dev-mode permissive).
    r = client.get("/admin/kpi/overview", headers=ADMIN1)
    assert r.status_code == 200
