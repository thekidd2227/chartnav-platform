"""Phase 54 — fundus charting + Phase 52B OpenAI guardrail hardening tests.

Proves that the optional LLM-assist seam introduced in Phase 54:

- is OFF by default (no env config -> rule_based_v1 is used);
- never reaches OpenAI without the explicit fundus opt-in env var;
- refuses LOUDLY (via ProviderDisabledError) when the operator
  opts in but any Phase 52B gate is not in the SAFE state — there
  is no silent fallback under opt-in;
- still requires the doctor's review / sign-off downstream;
- never sets `signed_at` / `reviewed_at` from the AI path;
- never invokes a real OpenAI endpoint in CI — all tests inject
  a fake transport;
- never logs the API key.

The fundus API surface (`apps/api/app/api/fundus_charts.py`) is
NOT modified by Phase 54; the dispatcher `generate_chart` is a
forward-looking entry point that fundus_charts.py can adopt in a
future phase. Tests here cover the dispatcher + the assist
function directly.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest


def _envelope(content_obj: dict) -> bytes:
    """Build a fake OpenAI chat-completions response envelope whose
    `choices[0].message.content` is the JSON-stringified content_obj.
    Using json.dumps avoids fragile escape-sequence handling in raw
    string literals."""
    return json.dumps(
        {
            "choices": [
                {"message": {"content": json.dumps(content_obj)}}
            ]
        }
    ).encode("utf-8")

from app.services.fundus_chart_ai import (
    FundusChartGenerationResult,
    _fundus_assist_requested,
    generate_chart,
    generate_chart_from_findings,
    generate_chart_via_llm_assist,
)
from app.services.llm_provider import (
    LLMRequest,
    ProviderDisabledError,
    assert_live_provider_safe_to_use,
)


# A canned OpenAI chat-completions envelope with a fundus-shaped
# JSON payload that the assist path would receive on the happy
# path. No real network call ever runs.
_OPENAI_OK_FUNDUS_RESPONSE = _envelope(
    {
        "laterality": "OD",
        "elements": [
            {
                "finding_type": "horseshoe_tear",
                "laterality": "OD",
                "clock_start": 11,
                "clock_end": 11,
                "zone": "equator",
                "color": "#e53e3e",
                "label": "horseshoe tear at 11 o'clock OD",
            }
        ],
        "warnings": [],
        "requires_provider_review": True,
    }
)


@pytest.fixture
def safe_env(monkeypatch):
    """Phase 52B + Phase 54 SAFE state.

    With this fixture applied the operator has opted into the
    fundus drafting assist (`CHARTNAV_FUNDUS_DRAFTING_ASSIST=openai`)
    and every Phase 52B env guardrail is in the SAFE state.
    """
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.delenv("CHARTNAV_LLM_REAL_PHI_APPROVED", raising=False)
    monkeypatch.delenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", raising=False)
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake-test-openai")


# ---------------------------------------------------------------------
# Default behaviour — rule_based_v1 is unchanged
# ---------------------------------------------------------------------


def test_default_dispatcher_returns_rule_based_v1_with_no_env(monkeypatch):
    """No env config -> rule_based_v1. Production default unchanged."""
    monkeypatch.delenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", raising=False)
    monkeypatch.delenv("CHARTNAV_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("CHARTNAV_OPENAI_API_KEY", raising=False)
    r = generate_chart(
        "Horseshoe tear at 11 o'clock OD, demo data."
    )
    assert isinstance(r, FundusChartGenerationResult)
    assert r.ai_model_name == "rule_based_v1"
    assert r.drawing_json["version"] == 1


def test_default_dispatcher_returns_rule_based_v1_even_when_phase_52b_is_active(
    monkeypatch,
):
    """Even with the Phase 52B OpenAI adapter usable system-wide,
    fundus charting still uses rule_based_v1 unless the operator
    *also* sets the fundus opt-in env var. The fundus seam is
    independent of the system-wide LLM selector."""
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake")
    monkeypatch.delenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", raising=False)
    r = generate_chart("Lattice from 9 to 10 o'clock OS, demo.")
    assert r.ai_model_name == "rule_based_v1"


def test_fundus_assist_requested_returns_false_by_default(monkeypatch):
    monkeypatch.delenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", raising=False)
    assert _fundus_assist_requested() is False


@pytest.mark.parametrize("val", ["1", "true", "yes", "on", "anthropic"])
def test_fundus_assist_requested_only_activates_for_literal_openai(
    monkeypatch, val
):
    """Anthropic and IBM watsonx remain unwired for fundus.
    `=1`/`=true` etc. are ignored — only the literal string
    'openai' opts in."""
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", val)
    assert _fundus_assist_requested() is False


def test_fundus_assist_requested_activates_for_openai(monkeypatch):
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", "openai")
    assert _fundus_assist_requested() is True


def test_existing_rule_based_path_unchanged():
    """Spot-check the rule_based_v1 path still parses a clear
    horseshoe-tear fixture into a structured drawing element."""
    r = generate_chart_from_findings(
        "Horseshoe tear at 11 o'clock OD, demo data."
    )
    assert r.ai_model_name == "rule_based_v1"
    assert any(
        el.finding_type for el in r.elements
    ), "rule_based_v1 should produce at least one element"


# ---------------------------------------------------------------------
# Opt-in refusal cases — LOUD, no silent fallback
# ---------------------------------------------------------------------


def test_assist_refuses_without_llm_enabled(monkeypatch):
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.delenv("CHARTNAV_LLM_ENABLED", raising=False)
    monkeypatch.delenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", raising=False)
    monkeypatch.delenv("CHARTNAV_LLM_REAL_PHI_APPROVED", raising=False)
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake")
    with pytest.raises(ProviderDisabledError) as exc:
        generate_chart("Anything, demo.")
    assert "CHARTNAV_LLM_ENABLED" in str(exc.value)


def test_assist_refuses_when_real_phi_approved_is_one(monkeypatch):
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.setenv("CHARTNAV_LLM_REAL_PHI_APPROVED", "1")
    monkeypatch.delenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", raising=False)
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake")
    with pytest.raises(ProviderDisabledError) as exc:
        generate_chart("Anything, demo.")
    # Live adapter must refuse on real-PHI; fundus assist must
    # not be the path that bypasses that contract.
    assert "FAKE-DATA-ONLY" in str(exc.value)


def test_assist_refuses_when_pilot_allow_is_one(monkeypatch):
    """Phase 52B semantic flip: setting pilot-allow=1 refuses."""
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.delenv("CHARTNAV_LLM_REAL_PHI_APPROVED", raising=False)
    monkeypatch.setenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", "1")
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake")
    with pytest.raises(ProviderDisabledError) as exc:
        generate_chart("Anything, demo.")
    assert "CHARTNAV_PILOT_ALLOW_LLM_OPENAI" in str(exc.value)


def test_assist_refuses_without_api_key(monkeypatch):
    monkeypatch.setenv("CHARTNAV_FUNDUS_DRAFTING_ASSIST", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.delenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", raising=False)
    monkeypatch.delenv("CHARTNAV_OPENAI_API_KEY", raising=False)
    # The Phase 52B env-gate also enforces presence of the API key
    # via the adapter constructor — but assist_live_provider_safe_to_use
    # currently checks env gates first; missing key is detected when
    # we attempt the actual call in generate_chart_via_llm_assist
    # (the request build sources api_key from env and will be empty).
    with pytest.raises((ProviderDisabledError, RuntimeError)):
        generate_chart("Anything, demo.")


def test_assist_refuses_when_fake_data_context_false(monkeypatch):
    """Caller-side opt-out: even with the env gates SAFE, if the
    request explicitly opts out of fake_data_context, the
    underlying guardrail wrapper refuses."""
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.delenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", raising=False)
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake")
    bad = LLMRequest(
        use_case="x",
        payload={},
        org_id=1,
        fake_data_context=False,  # explicit opt-out
    )
    with pytest.raises(ProviderDisabledError) as exc:
        assert_live_provider_safe_to_use("openai", bad)
    assert "fake_data_context=True" in str(exc.value)


def test_assist_refuses_when_requires_provider_review_false(monkeypatch):
    """Caller-side opt-out of provider-review is refused. This
    mirrors the Phase 52B requirement for every live adapter."""
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CHARTNAV_LLM_ENABLED", "1")
    monkeypatch.delenv("CHARTNAV_PILOT_ALLOW_LLM_OPENAI", raising=False)
    monkeypatch.setenv("CHARTNAV_OPENAI_API_KEY", "sk-fake")
    bad = LLMRequest(
        use_case="x",
        payload={},
        org_id=1,
        fake_data_context=True,
        requires_provider_review=False,
    )
    with pytest.raises(ProviderDisabledError) as exc:
        assert_live_provider_safe_to_use("openai", bad)
    assert "requires_provider_review" in str(exc.value)


# ---------------------------------------------------------------------
# Opt-in happy path — mocked transport, no network
# ---------------------------------------------------------------------


def test_assist_happy_path_uses_injected_transport_no_network(safe_env):
    captured: dict[str, Any] = {}

    def fake_transport(url, body, headers, timeout):
        captured["url"] = url
        captured["body_len"] = len(body)
        captured["header_keys"] = sorted(headers.keys())
        return 200, _OPENAI_OK_FUNDUS_RESPONSE

    r = generate_chart_via_llm_assist(
        "Horseshoe tear at 11 o'clock OD, fake demo data.",
        transport=fake_transport,
    )

    assert isinstance(r, FundusChartGenerationResult)
    assert r.ai_model_name == "openai_fundus_assist_v1"
    assert r.confidence["requires_provider_review"] is True
    assert r.confidence["vendor_model_id"] == "gpt-4o-mini"
    assert r.drawing_json["version"] == 1
    assert len(r.elements) == 1
    el = r.elements[0]
    assert el.finding_type == "horseshoe_tear"
    assert el.laterality == "OD"
    assert el.clock_start == 11.0
    # The endpoint + auth header were observed without ever
    # touching the real network.
    assert captured["url"].endswith("/chat/completions")
    assert "Authorization" in captured["header_keys"]


def test_assist_dispatcher_routes_to_assist_when_opted_in(safe_env):
    """`generate_chart` dispatcher routes to the assist path when
    the opt-in env var is set + the transport is injected.
    Confirms the dispatcher's branch logic, not just the assist
    function in isolation."""
    def fake_transport(url, body, headers, timeout):
        return 200, _OPENAI_OK_FUNDUS_RESPONSE

    r = generate_chart(
        "Horseshoe tear at 11 o'clock OD, demo.",
        transport=fake_transport,
    )
    assert r.ai_model_name == "openai_fundus_assist_v1"


def test_assist_output_requires_provider_review(safe_env):
    def fake_transport(url, body, headers, timeout):
        return 200, _OPENAI_OK_FUNDUS_RESPONSE

    r = generate_chart_via_llm_assist(
        "Lattice 9 to 10 OS, demo.", transport=fake_transport
    )
    assert r.confidence["requires_provider_review"] is True


def test_assist_output_carries_no_sign_or_review_fields(safe_env):
    """Defense-in-depth: the assist result MUST NOT include any
    keys that the chart row would interpret as 'already signed'
    or 'already reviewed'. The fundus API surface uses the row's
    own columns for those; the AI result feeds drawing_json and
    warnings only.

    This test pins that the assist result shape doesn't sneak in
    `signed_at`, `signed_by_user_id`, `reviewed_at`, or
    `reviewed_by_user_id` (which would be a programming error
    even if the API surface ignored them)."""
    def fake_transport(url, body, headers, timeout):
        return 200, _OPENAI_OK_FUNDUS_RESPONSE

    r = generate_chart_via_llm_assist(
        "Demo only.", transport=fake_transport
    )
    forbidden_keys = {
        "signed_at",
        "signed_by_user_id",
        "reviewed_at",
        "reviewed_by_user_id",
        "status",
    }
    # The dataclass instance must not carry any of these as
    # attributes, and the drawing_json must not contain them as
    # element-level keys either.
    for k in forbidden_keys:
        assert not hasattr(r, k), (
            f"Assist result must not expose '{k}' field"
        )
    for el in r.drawing_json.get("elements", []):
        for k in forbidden_keys:
            assert k not in el, (
                f"Assist drawing element must not contain '{k}'"
            )


def test_assist_translates_warnings_through_unchanged(safe_env):
    """If the model emits warnings (e.g., 'laterality not stated'),
    the assist function surfaces them verbatim in the result —
    NEVER invents findings to cover for missing dictation."""
    body_with_warnings = _envelope(
        {
            "laterality": "unspecified",
            "elements": [],
            "warnings": [
                "Laterality not stated in dictation; please confirm.",
                "No clock-hour specified for the lesion; please clarify.",
            ],
            "requires_provider_review": True,
        }
    )

    def fake_transport(url, body, headers, timeout):
        return 200, body_with_warnings

    r = generate_chart_via_llm_assist(
        "Something vague, demo.", transport=fake_transport
    )
    assert len(r.elements) == 0
    assert len(r.warnings) == 2
    assert any("Laterality" in w for w in r.warnings)


def test_assist_discards_malformed_elements_rather_than_fabricate(safe_env):
    """The schema-validation defense: if the model emits an
    element whose fields are unparseable (e.g., clock_start is a
    string the float() coercion can't handle), the assist
    function DISCARDS that element rather than fabricating a
    fallback. Never invent."""
    malformed = _envelope(
        {
            "laterality": "OD",
            "elements": [
                {
                    "finding_type": "horseshoe_tear",
                    "laterality": "OD",
                    "clock_start": "oops_not_a_number",
                    "clock_end": None,
                    "zone": "equator",
                    "color": "#e53e3e",
                    "label": "demo",
                },
                {
                    "finding_type": "lattice",
                    "laterality": "OS",
                    "clock_start": 9,
                    "clock_end": 10,
                    "zone": "equator",
                    "color": "#3182ce",
                    "label": "demo",
                },
            ],
            "warnings": [],
            "requires_provider_review": True,
        }
    )

    def fake_transport(url, body, headers, timeout):
        return 200, malformed

    r = generate_chart_via_llm_assist(
        "Demo with one good, one bad.", transport=fake_transport
    )
    # The malformed element is dropped; the valid one survives.
    assert len(r.elements) == 1
    assert r.elements[0].finding_type == "lattice"


def test_assist_api_key_never_logged_on_failure_path(safe_env, caplog):
    """Regression lock — the OpenAI API key value must not appear
    in any log line on any failure path inside the fundus assist
    function."""
    canary = "sk-CANARY-DO-NOT-LOG-fundus-12345"
    # Re-set the API key to the canary value so we can scan logs
    # for it deterministically.
    import os as _os
    _os.environ["CHARTNAV_OPENAI_API_KEY"] = canary

    def err_transport(url, body, headers, timeout):
        return 500, b'{"error":{"message":"upstream blew up"}}'

    caplog.set_level(logging.DEBUG, logger="chartnav.fundus.ai")
    with pytest.raises(RuntimeError):
        generate_chart_via_llm_assist(
            "Demo only.", transport=err_transport
        )
    for record in caplog.records:
        msg = record.getMessage()
        assert canary not in msg, (
            f"fundus assist leaked the API key into log: {msg!r}"
        )


# ---------------------------------------------------------------------
# Source-level safety — Anthropic and IBM watsonx remain unwired
# ---------------------------------------------------------------------


def test_fundus_chart_ai_source_does_not_wire_anthropic_or_watsonx():
    """Hard rule: Phase 54 ONLY wires OpenAI for the fundus assist
    seam. Anthropic and IBM watsonx must remain unwired in the
    fundus path. A source-level check pins this."""
    from pathlib import Path

    src_path = (
        Path(__file__).resolve().parent.parent
        / "app"
        / "services"
        / "fundus_chart_ai.py"
    )
    src = src_path.read_text()
    for forbidden in (
        "api.anthropic.com",
        "x-api-key",
        "anthropic-version",
        "AnthropicMessagesProvider",
        "ml.cloud.ibm.com",
        "iam.cloud.ibm.com",
        "ibm/granite",
    ):
        assert forbidden not in src, (
            "Phase 54 fundus seam must NOT wire "
            f"'{forbidden}' — only OpenAI is in scope."
        )
