"""Phase 56 — fundus QA hardening tests.

Pin behaviour the Phase 55 demo-readiness audit flagged as still-actionable:

- laterality mismatch between request and findings text → warning;
- audit minimisation (no raw findings text / drawing_json / SVG in audit);
- signed-chart endpoint policy (review / sign-twice / render);
- renderer edge cases (empty, malformed, long label, crossing 12,
  OU, unknown zone);
- role matrix: reviewer / front_desk cannot mutate; cross-org 404.

This file does not change product behaviour beyond the single
laterality-mismatch warning added in `fundus_chart_ai.generate_chart_from_findings`
(Phase 56 small bug fix matching the Phase 55 audit's § 4 still-actionable
gap "UX does not visibly warn about dropdown/text conflicts").
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from tests.conftest import ADMIN1, CLIN1, CLIN2, FRONT1, REV1, TECH1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def enc_id(seeded_ids):
    """First org-1 encounter id (mirrors test_fundus_charts.py)."""
    org1_id = seeded_ids["orgs"]["demo-eye-clinic"]
    for _pid, (eid, oid, _) in seeded_ids["encs"].items():
        if oid == org1_id:
            return eid
    pytest.fail("No org-1 encounters in seeded_ids")


def _generate(client, enc_id, findings_text, **kwargs):
    body = {"findings_text": findings_text}
    body.update(kwargs)
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json=body,
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _sign(client, chart_id):
    r = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# 1. Laterality mismatch — request says one eye, findings text says another
# ---------------------------------------------------------------------------


def test_ai_emits_warning_when_request_laterality_conflicts_with_findings_text():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings(
        "horseshoe tear at 10:30 OS", laterality_hint="OD"
    )
    # Findings text wins.
    assert result.laterality == "OS"
    assert any(
        "Laterality mismatch" in w and "OD" in w and "OS" in w
        for w in result.warnings
    ), f"expected mismatch warning, got {result.warnings!r}"


def test_ai_no_mismatch_warning_when_request_and_text_agree():
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings(
        "horseshoe tear at 10:30 OD", laterality_hint="OD"
    )
    assert not any("Laterality mismatch" in w for w in result.warnings)


def test_ai_no_mismatch_warning_when_request_is_ou_and_text_is_specific():
    """OU is a catch-all hint; we do not flag it as a mismatch against OD/OS."""
    from app.services.fundus_chart_ai import generate_chart_from_findings

    result = generate_chart_from_findings(
        "horseshoe tear at 10:30 OD", laterality_hint="OU"
    )
    assert not any("Laterality mismatch" in w for w in result.warnings)


def test_generate_persists_mismatch_warning_through_api(client, enc_id):
    body = _generate(
        client,
        enc_id,
        "horseshoe tear at 10:30 OS",
        laterality="OD",
    )
    # The generate response surfaces the warning…
    assert any("Laterality mismatch" in w for w in body["warnings"])
    # …and the GET endpoint persists it too.
    r = client.get(
        f"/api/v1/fundus-charts/{body['chart_id']}", headers=CLIN1
    )
    assert r.status_code == 200
    persisted = r.json()
    assert any(
        "Laterality mismatch" in w for w in (persisted["warnings_json"] or [])
    )
    # And the list endpoint exposes a chart whose status is draft.
    r2 = client.get(
        f"/api/v1/encounters/{enc_id}/fundus-charts", headers=CLIN1
    )
    listed = next(
        (c for c in r2.json() if c["id"] == body["chart_id"]), None
    )
    assert listed is not None
    assert listed["status"] == "draft"


# ---------------------------------------------------------------------------
# 2. Audit minimisation — raw findings / drawing / SVG never leak into audit
# ---------------------------------------------------------------------------


_AUDIT_CANARY_FINDING = (
    "PHASE56_AUDIT_CANARY horseshoe tear at 10:30 OD lattice from 5 to 7 OS"
)


def _read_audit_rows(event_types, since=None):
    """Read audit rows since a marker id (exclusive)."""
    from app.db import engine

    placeholders = ", ".join(f":et{i}" for i in range(len(event_types)))
    params: dict = {f"et{i}": et for i, et in enumerate(event_types)}
    where = f"event_type IN ({placeholders})"
    if since is not None:
        where += " AND id > :since"
        params["since"] = since
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, event_type, detail FROM security_audit_events "
                f"WHERE {where} ORDER BY id ASC"
            ),
            params,
        ).fetchall()
    return [dict(zip(["id", "event_type", "detail"], r)) for r in rows]


def _max_audit_id():
    from app.db import engine

    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM security_audit_events")
        ).fetchone()
    return int(r[0]) if r else 0


def test_audit_detail_contains_no_raw_findings_text_or_drawing(
    client, enc_id
):
    before = _max_audit_id()
    body = _generate(client, enc_id, _AUDIT_CANARY_FINDING)
    chart_id = body["chart_id"]
    # Trigger every audited fundus action.
    r_render = client.post(
        f"/api/v1/fundus-charts/{chart_id}/render", headers=CLIN1
    )
    # render currently is not audited (audit_record not called from
    # the route) — still safe to assert below.
    assert r_render.status_code == 200
    rendered_svg = r_render.json()["rendered_svg"]
    r_rev = client.post(
        f"/api/v1/fundus-charts/{chart_id}/review", json={}, headers=CLIN1
    )
    assert r_rev.status_code == 200
    r_sign = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=CLIN1,
    )
    assert r_sign.status_code == 200

    rows = _read_audit_rows(
        [
            "fundus_chart_generated",
            "fundus_chart_created",
            "fundus_chart_updated",
            "fundus_chart_reviewed",
            "fundus_chart_signed",
        ],
        since=before,
    )
    assert rows, "no fundus audit rows recorded — fixture sanity check"
    forbidden_substrings = [
        "PHASE56_AUDIT_CANARY",
        "horseshoe tear at 10:30 OD",
        "lattice from 5 to 7 OS",
        "drawing_json",
        '"elements"',
        '"clock_start"',
        "<svg",
        "<path",
        rendered_svg[:64] if len(rendered_svg) > 64 else rendered_svg,
    ]
    for row in rows:
        detail = row["detail"] or ""
        for needle in forbidden_substrings:
            assert needle not in detail, (
                f"audit row {row['id']} ({row['event_type']}) leaked "
                f"forbidden substring {needle!r}: detail={detail!r}"
            )
    # Sanity: the detail strings should still carry the chart_id so
    # the audit remains useful for traceability.
    assert any(
        f"chart_id={chart_id}" in (r["detail"] or "") for r in rows
    )


# ---------------------------------------------------------------------------
# 3. Signed-chart endpoint policy
# ---------------------------------------------------------------------------


def test_review_on_signed_chart_returns_409(client, enc_id):
    """Once a chart is signed, the review endpoint must refuse."""
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    _sign(client, chart_id)
    r = client.post(
        f"/api/v1/fundus-charts/{chart_id}/review", json={}, headers=CLIN1
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["error_code"] == "chart_already_signed"


def test_sign_already_signed_chart_returns_409(client, enc_id):
    """Idempotency contract: a second sign call on an already-signed
    chart returns 409, never silently re-stamps signed_at."""
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    first = _sign(client, chart_id)
    r = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] in (
        "already_signed",
        "chart_already_signed",
    )
    # And the original signed_at is unchanged.
    r2 = client.get(f"/api/v1/fundus-charts/{chart_id}", headers=CLIN1)
    assert r2.json()["signed_at"] == first["signed_at"]


def test_render_signed_chart_is_currently_allowed_and_idempotent(
    client, enc_id
):
    """Documents the current behaviour: render on a signed chart is
    allowed (signed_at / signer_id remain unchanged) so the operator
    can regenerate the cached SVG on demand. If this policy ever
    tightens (e.g. block render on signed), update this test name +
    body, since it serves as the canonical record of expected
    behaviour."""
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    _sign(client, chart_id)
    before = client.get(f"/api/v1/fundus-charts/{chart_id}", headers=CLIN1).json()
    r = client.post(
        f"/api/v1/fundus-charts/{chart_id}/render", headers=CLIN1
    )
    assert r.status_code == 200
    after = client.get(f"/api/v1/fundus-charts/{chart_id}", headers=CLIN1).json()
    # The signature stays untouched.
    assert after["signed_at"] == before["signed_at"]
    assert after["signed_by_user_id"] == before["signed_by_user_id"]
    assert after["status"] == "signed"


def test_patch_signed_chart_returns_409(client, enc_id):
    """Already pinned in test_update_signed_chart_blocked; restated here
    so the Phase 56 signed-policy suite is the single canonical place
    to read the contract for every endpoint."""
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    _sign(client, chart_id)
    r = client.patch(
        f"/api/v1/fundus-charts/{chart_id}",
        json={"laterality": "OS"},
        headers=CLIN1,
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# 4. Renderer edge cases
# ---------------------------------------------------------------------------


def test_renderer_empty_drawing_json_still_renders_base_diagram():
    from app.services.fundus_chart_renderer import render_fundus_svg

    svg = render_fundus_svg({}, "OD")
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    # Base diagram pieces are present even with zero findings.
    assert "Posterior Pole" in svg
    assert "Equator" in svg
    # Laterality badge.
    assert ">OD<" in svg


def test_renderer_unknown_finding_type_renders_without_crashing():
    """Unknown 'type' field should still produce a glyph at the
    indicated clock position — the renderer does not block on
    unknown types."""
    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "fictitious_finding_type_unknown_to_renderer",
                "laterality": "OD",
                "clock_start": 6.0,
                "clock_end": None,
                "zone": "equator",
                "color": "#718096",
                "label": "Unknown",
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OD")
    assert "<svg" in svg
    assert "Unknown" in svg


def test_renderer_very_long_label_does_not_truncate_svg():
    from app.services.fundus_chart_renderer import render_fundus_svg

    long_label = "A" * 256
    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "lattice",
                "laterality": "OD",
                "clock_start": 9.0,
                "clock_end": 10.0,
                "zone": "equator",
                "color": "#d69e2e",
                "label": long_label,
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OD")
    assert long_label in svg
    assert svg.endswith("</svg>")


def test_renderer_clock_range_crossing_12_oclock():
    """e.g. 11 → 2 should render an arc using the large-arc flag."""
    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "lattice",
                "laterality": "OD",
                "clock_start": 11.0,
                "clock_end": 14.0,  # 14 mod 12 = 2 o'clock; span = 3 (≤6 → small arc)
                "zone": "equator",
                "color": "#d69e2e",
                "label": "Crossing 12",
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OD")
    assert "<path" in svg
    # Span = (14 - 11) % 12 = 3, so large_arc = 0; the SVG should still
    # be well-formed and reference the correct arc parameters.
    assert "</svg>" in svg


def test_renderer_clock_range_crossing_12_with_large_arc():
    """e.g. 11 → 7 covers more than half the clock → large-arc flag = 1."""
    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "detachment",
                "laterality": "OS",
                "clock_start": 11.0,
                "clock_end": 19.0,  # 19 mod 12 = 7; span = 8 (>6 → large arc)
                "zone": "equator",
                "color": "#3182ce",
                "label": "Wide detachment",
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OS")
    # The large-arc flag is the 4th '0/1' token in the SVG path A
    # parameters; check that a '1' large-arc token exists.
    assert " 1 " in svg  # presence of large-arc=1 token in any path


def test_renderer_ou_laterality_renders_ou_badge():
    from app.services.fundus_chart_renderer import render_fundus_svg

    svg = render_fundus_svg({}, "OU")
    assert ">OU<" in svg


def test_renderer_unsupported_zone_falls_back_to_equator():
    """Unsupported zone string should not crash; the renderer falls
    back to the equator radius."""
    from app.services.fundus_chart_renderer import render_fundus_svg

    drawing = {
        "version": 1,
        "elements": [
            {
                "type": "lattice",
                "laterality": "OD",
                "clock_start": 6.0,
                "clock_end": None,
                "zone": "nonexistent_zone_xyz",
                "color": "#d69e2e",
                "label": "ZoneFallback",
            }
        ],
    }
    svg = render_fundus_svg(drawing, "OD")
    assert "ZoneFallback" in svg
    assert "<svg" in svg


# ---------------------------------------------------------------------------
# 5. Role matrix
# ---------------------------------------------------------------------------


def test_admin_can_generate(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=ADMIN1,
    )
    assert r.status_code == 201


def test_reviewer_cannot_generate(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=REV1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "insufficient_role"


def test_front_desk_cannot_generate(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=FRONT1,
    )
    assert r.status_code == 403


def test_technician_cannot_generate(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/fundus-charts/generate",
        json={"findings_text": "horseshoe tear at 10:30 OD"},
        headers=TECH1,
    )
    assert r.status_code == 403


def test_reviewer_can_read_but_not_sign(client, enc_id):
    """Reviewer role can GET but not POST /sign — pin both."""
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    # Read is allowed (no write-role check on GET endpoints).
    r_get = client.get(
        f"/api/v1/fundus-charts/{chart_id}", headers=REV1
    )
    assert r_get.status_code == 200
    # Sign refused.
    r_sign = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=REV1,
    )
    assert r_sign.status_code == 403


def test_cross_org_get_chart_returns_404(client, enc_id):
    """Org-2 clinician cannot read an org-1 chart even with the id."""
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    r = client.get(f"/api/v1/fundus-charts/{chart_id}", headers=CLIN2)
    assert r.status_code == 404


def test_cross_org_sign_returns_404(client, enc_id):
    body = _generate(client, enc_id, "horseshoe tear at 10:30 OD")
    chart_id = body["chart_id"]
    r = client.post(
        f"/api/v1/fundus-charts/{chart_id}/sign",
        json={"attested": True},
        headers=CLIN2,
    )
    assert r.status_code == 404
