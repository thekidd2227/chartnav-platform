"""ChartNav LLM provider seam — scaffolding only.

This module defines the **interface** ChartNav will use for any
future LLM workflow (draft generation, summarization, structured
extraction, prompt-injection classification). It ships with a
single concrete provider — `DeterministicStubProvider` — that
returns hand-written, deterministic output keyed by use case.

What this module is NOT
-----------------------
- It is **not** wired into `note_generator.py` or
  `note_orchestrator.py`. The deterministic note workflow remains
  authoritative. This module is design scaffolding only.
- It does **not** import any vendor SDK (OpenAI / Anthropic /
  IBM watsonx). There is no network call here.
- It does **not** read any vendor credential. The stub provider
  needs no key.
- It is **not** approved for real PHI. The `real_phi_ready` flag
  is hard-pinned False in any future readiness endpoint that
  surfaces this module's selection.

Why ship this now
-----------------
A vendor-flexible interface (mirroring the proven shape of
`stt_provider.py`) lets a future build wire OpenAI / Anthropic /
watsonx behind a single feature flag without touching any
existing code path. The interface is small (5 methods), entirely
typed, and exercised by the test suite against the stub
provider so a regression catches any shape drift before vendor
code is written.

Selection
---------
`select_default_provider(provider_key)` reads
`CHARTNAV_LLM_PROVIDER`:
- unset / `deterministic_stub` → `DeterministicStubProvider`
- `none` → returns `None` (caller wires a no-op)
- `openai`, `anthropic`, `ibm_watsonx` → **NotImplementedError**
  with a clear message that the adapter has not shipped. Failing
  loud here is the design — a future build adds the adapter; we
  refuse to silently downgrade to the stub.
- anything else → `RuntimeError` at boot.

See `docs/security/chartnav-llm-vendor-evaluation.md` for the
full vendor comparison and gating.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


# ---------------------------------------------------------------------------
# Public dataclasses (the contract every provider must honor)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LLMRequest:
    """A single request to the LLM seam.

    `use_case` mirrors `app.services.ai_governance.AIUseCase` so the
    governance audit row carries the same enum the provider was
    invoked under.

    `payload` is a structured dict the provider interprets — never
    raw user input concatenated into a system prompt. The provider
    is responsible for templating with anti-injection markers.

    `org_id` is required so any future audit row can be org-scoped
    without a separate parameter chain.
    """
    use_case: str
    payload: dict[str, Any]
    org_id: int
    request_id: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    """A single response from the LLM seam.

    Every response carries a `source_label` so the renderer can
    show the clinician where the text came from (deterministic
    stub / vendor name). Confidence is optional but encouraged.
    The structured-output dict validates against the use case's
    schema upstream — this module does not enforce that.
    """
    text: str
    structured: dict[str, Any]
    source_label: str
    confidence: Optional[float] = None
    requires_review: bool = True
    safety_flags: tuple[str, ...] = ()


class LLMProvider(Protocol):
    """The contract every provider class must implement.

    Methods are deliberately small and orthogonal. A vendor adapter
    that cannot honor a method MUST raise `NotImplementedError`
    rather than silently degrade.
    """

    name: str

    def summarize_transcript(self, request: LLMRequest) -> LLMResponse: ...

    def extract_structured_facts(self, request: LLMRequest) -> LLMResponse: ...

    def draft_provider_review_note(self, request: LLMRequest) -> LLMResponse: ...

    def classify_note_quality_risk(self, request: LLMRequest) -> LLMResponse: ...

    def detect_prompt_injection(self, request: LLMRequest) -> LLMResponse: ...

    def normalize_chart_context(self, request: LLMRequest) -> LLMResponse: ...


# ---------------------------------------------------------------------------
# Deterministic stub provider
# ---------------------------------------------------------------------------


class DeterministicStubProvider:
    """The default LLM provider — pure, deterministic, no external call.

    Returns predictable, clearly-labelled placeholder outputs for
    each use case. The only "logic" is honouring optional test
    metadata in `request.extra` so the existing test patterns
    (e.g. `X-Stub-Transcript`) can carry over when a future
    workflow wires this provider into a real surface.

    Every response sets `requires_review = True` so a regression
    cannot accidentally promote a stub output to a signed note.
    """

    name = "deterministic_stub"

    def _stub_response(
        self, request: LLMRequest, surface: str
    ) -> LLMResponse:
        # Honour a canned-text test hook (mirrors stt_provider stub).
        canned = request.extra.get("stub_text")
        if isinstance(canned, str) and canned:
            text = canned
        else:
            text = (
                f"[stub-llm:{surface}] use_case={request.use_case} "
                f"org_id={request.org_id} — provider must review."
            )
        return LLMResponse(
            text=text,
            structured={"surface": surface, "use_case": request.use_case},
            source_label="deterministic_stub",
            confidence=None,
            requires_review=True,
            safety_flags=(),
        )

    def summarize_transcript(self, request: LLMRequest) -> LLMResponse:
        return self._stub_response(request, "summarize_transcript")

    def extract_structured_facts(self, request: LLMRequest) -> LLMResponse:
        return self._stub_response(request, "extract_structured_facts")

    def draft_provider_review_note(self, request: LLMRequest) -> LLMResponse:
        return self._stub_response(request, "draft_provider_review_note")

    def classify_note_quality_risk(self, request: LLMRequest) -> LLMResponse:
        return self._stub_response(request, "classify_note_quality_risk")

    def detect_prompt_injection(self, request: LLMRequest) -> LLMResponse:
        # Stub always reports "no injection detected"; the real
        # security pipeline (`ai_security.detect_prompt_injection`)
        # remains authoritative and runs upstream regardless.
        resp = self._stub_response(request, "detect_prompt_injection")
        return LLMResponse(
            text=resp.text,
            structured={**resp.structured, "injection_detected": False},
            source_label=resp.source_label,
            confidence=None,
            requires_review=True,
            safety_flags=(),
        )

    def normalize_chart_context(self, request: LLMRequest) -> LLMResponse:
        return self._stub_response(request, "normalize_chart_context")


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


# Vendor adapters that have NOT yet shipped. Selecting one raises
# loudly so a misconfigured deployment cannot silently downgrade to
# the stub under a vendor key.
_NOT_YET_IMPLEMENTED: frozenset[str] = frozenset({
    "openai",
    "anthropic",
    "ibm_watsonx",
})


# Adapters that HAVE shipped. Add vendor factory entries here when
# a vendor adapter is implemented and approved per
# `docs/security/chartnav-llm-vendor-evaluation.md`.
_PROVIDER_FACTORIES: dict[str, Callable[[], LLMProvider]] = {
    "deterministic_stub": lambda: DeterministicStubProvider(),
}


def select_default_provider(
    provider_key: Optional[str] = None,
) -> Optional[LLMProvider]:
    """Resolve the configured LLM provider.

    Returns:
        - an `LLMProvider` instance, OR
        - `None` when the operator explicitly configured `none`.

    Raises:
        - `NotImplementedError` for a vendor key whose adapter has
          not shipped (`openai`, `anthropic`, `ibm_watsonx`). The
          error message points at the vendor-evaluation doc.
        - `RuntimeError` for an unknown provider key.
    """
    key = (
        provider_key
        or os.environ.get("CHARTNAV_LLM_PROVIDER")
        or "deterministic_stub"
    ).lower()

    if key == "none":
        return None

    if key in _NOT_YET_IMPLEMENTED:
        raise NotImplementedError(
            f"CHARTNAV_LLM_PROVIDER={key!r} is not yet implemented. "
            "See docs/security/chartnav-llm-vendor-evaluation.md "
            "for the gating that must close before any vendor "
            "adapter ships. Set CHARTNAV_LLM_PROVIDER=deterministic_stub "
            "(default) or =none to proceed."
        )

    factory = _PROVIDER_FACTORIES.get(key)
    if factory is None:
        raise RuntimeError(
            f"CHARTNAV_LLM_PROVIDER={key!r} is not a registered "
            f"provider. Known: {sorted(_PROVIDER_FACTORIES)} or 'none'."
        )
    return factory()
