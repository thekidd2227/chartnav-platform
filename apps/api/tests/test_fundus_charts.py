"""Tests for AI-assisted fundus charting."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Unit — AI service
# ---------------------------------------------------------------------------

def test_ai_generates_horseshoe_tear():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings("horseshoe tear at 10:30 OD")
    assert result.laterality == "OD"
    assert len(result.elements) == 1
    assert result.elements[0].finding_type == "horseshoe_tear"
    assert result.elements[0].clock_start == pytest.approx(10.5)


def test_ai_warns_missing_laterality():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings("lattice degeneration at 6")
    assert any("laterality" in w.lower() for w in result.warnings)


def test_ai_warns_missing_clock_hour():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings("lattice OD near ora")
    assert any("clock hour" in w.lower() for w in result.warnings)


def test_ai_lattice_clock_range():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings("lattice from 5 to 7 OS near ora")
    assert result.laterality == "OS"
    assert result.elements[0].clock_start == pytest.approx(5.0)
    assert result.elements[0].clock_end == pytest.approx(7.0)


def test_ai_no_findings_produces_warning():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings("vision is 20/20")
    assert any("no recognisable" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Unit — SVG renderer
# ---------------------------------------------------------------------------

def test_renderer_produces_valid_svg():
    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "horseshoe_tear",
                "laterality": "OD",
                "clock_start": 10.5,
                "clock_end": None,
                "zone": "ora_serrata",
                "color": "#e53e3e",
                "label": "Horseshoe Tear",
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OD")
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert "OD" in svg
    assert "</svg>" in svg


def test_renderer_arc_finding():
    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "lattice",
                "laterality": "OD",
                "clock_start": 5.0,
                "clock_end": 7.0,
                "zone": "equator",
                "color": "#d69e2e",
                "label": "Lattice",
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OD")
    assert "<path" in svg


# ---------------------------------------------------------------------------
# Integration — API
# ---------------------------------------------------------------------------

@pytest.fixture()
def enc_id(seeded_ids):
    return next(iter(seeded_ids["encs"].values()))


def test_list_fundus_charts_empty(client, enc_id, CLIN1):
    r = client.get(f"/api/v1/encounters/{enc_id}/fundus-charts", headers=CLIN1)
    assert r.status_code == 200
    assert r.json() == []


def test_generate_fundus_chart(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=CLIN1,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["laterality"] == "OD"
    assert "chart_id" in body
    assert body["status"] == "draft"


def test_generate_then_retrieve(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "lattice from 5 to 7 OS near ora"},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    r2 = client.get(f"/api/v1/fundus-charts/{chart_id}", headers=CLIN1)
    assert r2.status_code == 200
    assert r2.json()["laterality"] == "OS"


def test_create_manual_chart(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts",
        json={"laterality": "OD", "drawing_json": {}, "source_type": "manual"},
        headers=CLIN1,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "draft"


def test_update_chart(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts",
        json={"laterality": "OD", "drawing_json": {}},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    r2 = client.patch(
        f"/api/v1/fundus-charts/{chart_id}",
        json={"laterality": "OS"},
        headers=CLIN1,
    )
    assert r2.status_code == 200
    assert r2.json()["laterality"] == "OS"


def test_render_chart(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    r2 = client.post(f"/api/v1/fundus-charts/{chart_id}/render", headers=CLIN1)
    assert r2.status_code == 200
    assert "<svg" in r2.json()["rendered_svg"]


def test_review_chart(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    r2 = client.post(f"/api/v1/fundus-charts/{chart_id}/review", json={}, headers=CLIN1)
    assert r2.status_code == 200
    assert r2.json()["status"] == "reviewed"


def test_sign_chart_requires_attestation(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    r2 = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": False},
        headers=CLIN1,
    )
    assert r2.status_code == 422


def test_sign_chart(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    r2 = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=CLIN1,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "signed"


def test_update_signed_chart_blocked(client, enc_id, CLIN1):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=CLIN1,
    )
    chart_id = r.json()["chart_id"]
    client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=CLIN1,
    )
    r2 = client.patch(
        f"/api/v1/fundus-charts/{chart_id}",
        json={"laterality": "OS"},
        headers=CLIN1,
    )
    assert r2.status_code == 409


def test_cross_org_encounter_blocked(client, enc_id, CLIN2):
    """Org-2 clinician cannot access org-1 encounters."""
    r = client.get(f"/api/v1/encounters/{enc_id}/fundus-charts", headers=CLIN2)
    assert r.status_code == 404
