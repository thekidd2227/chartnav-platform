"""Phase 2 item 4 — provider seam contract tests.

Spec: docs/chartnav/closure/PHASE_B_Reminders_and_Patient_Communication_Hardening.md §4.

The Phase B implementation MUST:
  - have a StubProvider that returns a synthetic provider_message_id
    (clearly marked synthetic);
  - have a TwilioProviderSkeleton that raises NotImplementedError
    on send (the wiring is Phase C and intentionally NOT done now).
"""
from __future__ import annotations

import pytest


def test_stub_provider_returns_synthetic_message_id(client):
    from app.services.messaging import (
        CHANNEL_SMS_STUB, StubProvider,
    )
    sp = StubProvider()
    out = sp.send(channel=CHANNEL_SMS_STUB, to="PT-1", body="hello")
    assert out["delivered_synthetically"] is True
    assert out["provider_message_id"].startswith("stub-")
    # The advisory must call out that nothing real happened.
    assert "no real" in out["advisory"].lower()


def test_twilio_skeleton_raises_not_implemented(client):
    from app.services.messaging import TwilioProviderSkeleton
    with pytest.raises(NotImplementedError) as exc:
        TwilioProviderSkeleton().send(channel="sms_stub", to="PT-1", body="x")
    assert "Phase B" in str(exc.value) or "Phase C" in str(exc.value)
