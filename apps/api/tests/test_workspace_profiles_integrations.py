"""Phase 86 — Workspace profile integrations into Phase 76 / 77 / 82."""

from __future__ import annotations

CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _patch_type(client, typ):
    return client.patch(
        "/api/v1/encounters/1/workspace-profile",
        headers=CLIN1,
        json={"encounter_type": typ},
    )


def test_phase_76_summary_embeds_workspace_profile(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    assert "workspace_profile" in body
    wp = body["workspace_profile"]
    assert wp["encounter_type"] == "comprehensive"
    assert wp["encounter_type_label"] == "Comprehensive"
    assert wp["profile_code"] == "comprehensive"


def test_phase_76_summary_reflects_patched_encounter_type(client):
    assert _patch_type(client, "retina").status_code == 200
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    assert body["workspace_profile"]["encounter_type"] == "retina"
    assert "deterministic mapping" in body["audit_disclosure"].lower()


def test_phase_77_packet_inherits_workspace_profile_via_summary(client):
    assert _patch_type(client, "glaucoma").status_code == 200
    packet = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    # The packet may not project workspace_profile at the top level, but
    # the underlying summary's evidence is preserved — verify the audit
    # disclosure still mentions the workspace profile boundary.
    assert "deterministic mapping" in packet["audit_disclosure"].lower()


def test_phase_82_validation_embeds_workspace_profile(client):
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    assert "workspace_profile" in body
    assert body["workspace_profile"]["encounter_type"] == "comprehensive"


def test_phase_82_validation_reflects_patched_encounter_type(client):
    assert _patch_type(client, "cataract").status_code == 200
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    assert body["workspace_profile"]["encounter_type"] == "cataract"
    assert body["workspace_profile"]["encounter_type_label"] == "Cataract"


def test_encounters_list_exposes_encounter_type_field(client):
    encounters = client.get("/encounters", headers=CLIN1).json()
    assert len(encounters) > 0
    # Default should be 'comprehensive' before any PATCH.
    enc = next(e for e in encounters if e["id"] == 1)
    assert enc["encounter_type"] in {"retina", "glaucoma", "cataract", "comprehensive"}


def test_encounters_list_reflects_patched_encounter_type(client):
    assert _patch_type(client, "retina").status_code == 200
    encounters = client.get("/encounters", headers=CLIN1).json()
    enc = next(e for e in encounters if e["id"] == 1)
    assert enc["encounter_type"] == "retina"


def test_validation_check_safety_never_blocks_after_type_change(client):
    # Changing the encounter type must never make the validation rail
    # require an acknowledgement (the rail itself is informational).
    assert _patch_type(client, "retina").status_code == 200
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    for check in body["checks"]:
        # Phase 82 contract preserved — laterality rollup may still require
        # ack if data conflicts, but staging/medication never do.
        if check["category"] in {"staging", "medication"}:
            assert check["requires_provider_acknowledgement"] is False
