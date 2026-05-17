"""LLM provider seam — scaffolding tests.

The module under test ships no vendor SDK and no external call.
These tests pin the interface shape, the selector defaults, and
the "vendor adapter not yet shipped" guard rails. A future PR
that adds a real vendor adapter must extend this file with the
vendor-specific tests.

Hard rules locked here:
- Default provider is the deterministic stub.
- `none` returns None (caller wires a no-op).
- Each vendor key (`openai`, `anthropic`, `ibm_watsonx`) raises
  a loud `NotImplementedError` pointing at the evaluation doc.
- Unknown keys raise `RuntimeError`.
- The stub's responses always carry `requires_review=True` and
  `source_label="deterministic_stub"` so a regression cannot
  promote a stub output to a signed note.
"""

from __future__ import annotations

import pytest

from app.services.llm_provider import (
    DeterministicStubProvider,
    LLMRequest,
    LLMResponse,
    select_default_provider,
)


REQUEST = LLMRequest(
    use_case="clinical_charting",
    payload={"transcript": "Fake demo dictation. No real PHI."},
    org_id=1,
    request_id="req-test",
)


# ---------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------


def test_select_default_provider_is_deterministic_stub(monkeypatch):
    monkeypatch.delenv("CHARTNAV_LLM_PROVIDER", raising=False)
    p = select_default_provider()
    assert isinstance(p, DeterministicStubProvider)
    assert p.name == "deterministic_stub"


def test_select_default_provider_none_returns_none(monkeypatch):
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "none")
    assert select_default_provider() is None


@pytest.mark.parametrize("key", ["openai", "anthropic", "ibm_watsonx"])
def test_vendor_keys_raise_not_implemented_until_adapter_ships(
    monkeypatch, key
):
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", key)
    with pytest.raises(NotImplementedError) as exc:
        select_default_provider()
    msg = str(exc.value)
    assert key in msg
    # Operator must be told WHERE the gating lives, not just that
    # the adapter is missing.
    assert "chartnav-llm-vendor-evaluation.md" in msg
    assert "deterministic_stub" in msg


def test_unknown_provider_key_raises_runtime_error(monkeypatch):
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "vendor_that_does_not_exist")
    with pytest.raises(RuntimeError) as exc:
        select_default_provider()
    assert "vendor_that_does_not_exist" in str(exc.value)


def test_explicit_provider_key_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("CHARTNAV_LLM_PROVIDER", "openai")
    p = select_default_provider(provider_key="deterministic_stub")
    assert isinstance(p, DeterministicStubProvider)


# ---------------------------------------------------------------------
# Deterministic stub behaviour
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "method_name",
    [
        "summarize_transcript",
        "extract_structured_facts",
        "draft_provider_review_note",
        "classify_note_quality_risk",
        "detect_prompt_injection",
        "normalize_chart_context",
    ],
)
def test_stub_every_method_returns_review_required_response(method_name):
    p = DeterministicStubProvider()
    method = getattr(p, method_name)
    resp = method(REQUEST)
    assert isinstance(resp, LLMResponse)
    # Every stub response MUST require provider review. A regression
    # that flips this to False would let a stub output pose as a
    # signed clinical note.
    assert resp.requires_review is True
    assert resp.source_label == "deterministic_stub"
    # No safety flags from the stub — the real ai_security pipeline
    # runs upstream and is authoritative.
    assert resp.safety_flags == ()


def test_stub_honours_canned_text_hook():
    p = DeterministicStubProvider()
    canned = "Fake demo patient reports blurry vision. Not real PHI."
    req = LLMRequest(
        use_case="clinical_charting",
        payload={},
        org_id=1,
        extra={"stub_text": canned},
    )
    assert p.summarize_transcript(req).text == canned


def test_stub_text_includes_surface_label_and_use_case():
    p = DeterministicStubProvider()
    resp = p.draft_provider_review_note(REQUEST)
    assert "[stub-llm:draft_provider_review_note]" in resp.text
    assert "use_case=clinical_charting" in resp.text
    assert "org_id=1" in resp.text


def test_stub_detect_prompt_injection_always_reports_no_injection():
    """The stub's injection classifier is intentionally trivial —
    the authoritative regex pipeline in ai_security.py runs
    upstream and is what we trust. Locking the stub's behaviour
    here prevents accidental drift that would mask a real
    classifier swap."""
    p = DeterministicStubProvider()
    resp = p.detect_prompt_injection(REQUEST)
    assert resp.structured["injection_detected"] is False
    assert resp.requires_review is True


# ---------------------------------------------------------------------
# Module-level invariants
# ---------------------------------------------------------------------


def test_module_source_imports_no_vendor_sdk():
    """Hard rule: the scaffolding module must not import any vendor
    SDK. Importing `openai`, `anthropic`, or
    `ibm_watson_machine_learning` at module level would couple the
    scaffolding to a vendor and defeat the point of a vendor-
    flexible seam. Source-level check is the simplest regression
    lock; a future PR that adds a real adapter will register it via
    `_PROVIDER_FACTORIES` in a separate module."""
    from pathlib import Path
    src = Path(
        __file__
    ).resolve().parent.parent / "app" / "services" / "llm_provider.py"
    text = src.read_text()
    for forbidden in (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "import ibm_watson",
        "from ibm_watson",
        "import ibm_cloud",
        "from ibm_cloud",
    ):
        assert forbidden not in text, (
            f"llm_provider scaffolding must not contain {forbidden!r}"
        )
