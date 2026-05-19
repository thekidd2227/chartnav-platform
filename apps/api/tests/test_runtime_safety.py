"""Runtime safety validator tests.

These tests exercise the standalone CI/local guard script without
requiring real vendor keys, real PHI, or network access.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_runtime_safety.py"
SPEC = importlib.util.spec_from_file_location("check_runtime_safety", SCRIPT)
runtime_safety = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules["check_runtime_safety"] = runtime_safety
SPEC.loader.exec_module(runtime_safety)


def codes_for(env: dict[str, str]) -> set[str]:
    return {finding.code for finding in runtime_safety.validate_env(env)}


def report_for(env: dict[str, str]) -> str:
    return runtime_safety.format_report(runtime_safety.validate_env(env))


def test_default_local_safe_env_passes():
    assert codes_for({"CHARTNAV_ENV": "local"}) == set()


def test_production_with_llm_enabled_fails():
    codes = codes_for({"CHARTNAV_ENV": "production", "CHARTNAV_LLM_ENABLED": "1"})
    assert "LLM_ENABLED_PRODUCTION" in codes


def test_openai_with_real_phi_approved_fails():
    codes = codes_for({
        "CHARTNAV_ENV": "demo",
        "CHARTNAV_LLM_PROVIDER": "openai",
        "CHARTNAV_LLM_REAL_PHI_APPROVED": "1",
    })
    assert "LLM_OPENAI_REAL_PHI" in codes


def test_openai_fundus_assist_outside_demo_fails():
    codes = codes_for({
        "CHARTNAV_ENV": "controlled-pilot",
        "CHARTNAV_FUNDUS_DRAFTING_ASSIST": "openai",
    })
    assert "FUNDUS_OPENAI_NOT_DEMO" in codes


def test_openai_ambient_assist_in_production_fails():
    """Phase 57 — production must never enable demo-only ambient assist."""
    codes = codes_for({
        "CHARTNAV_ENV": "production",
        "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST": "openai",
    })
    assert "AMBIENT_OPENAI_PRODUCTION" in codes
    assert "AMBIENT_OPENAI_NOT_DEMO" in codes
    assert "PRODUCTION_AMBIENT_OPENAI" in codes


def test_openai_ambient_assist_outside_demo_fails():
    """Phase 57 — opting into the ambient OpenAI assist in a
    controlled-pilot environment (non fake/demo) fails."""
    codes = codes_for({
        "CHARTNAV_ENV": "controlled-pilot",
        "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST": "openai",
    })
    assert "AMBIENT_OPENAI_NOT_DEMO" in codes


def test_openai_ambient_assist_in_local_demo_passes_ambient_gates():
    """Phase 57 — demo / local with no other unsafe combinations is
    the only environment where the ambient OpenAI assist is allowed.
    AMBIENT_OPENAI_* codes must not fire here."""
    codes = codes_for({
        "CHARTNAV_ENV": "demo",
        "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST": "openai",
    })
    assert "AMBIENT_OPENAI_NOT_DEMO" not in codes
    assert "AMBIENT_OPENAI_PRODUCTION" not in codes
    assert "AMBIENT_OPENAI_REAL_PHI_APPROVED" not in codes
    assert "REAL_PHI_WITH_AMBIENT_OPENAI" not in codes
    assert "PRODUCTION_AMBIENT_OPENAI" not in codes


def test_openai_ambient_assist_with_real_phi_approved_fails():
    """Phase 57 — flipping the LLM real-PHI gate while the ambient
    assist is opted in must fail."""
    codes = codes_for({
        "CHARTNAV_ENV": "demo",
        "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST": "openai",
        "CHARTNAV_LLM_REAL_PHI_APPROVED": "1",
    })
    assert "AMBIENT_OPENAI_REAL_PHI_APPROVED" in codes


def test_real_phi_enabled_with_ambient_openai_fails():
    """Phase 57 — operator-side real-PHI flag combined with the
    ambient OpenAI assist must fail."""
    codes = codes_for({
        "CHARTNAV_ENV": "controlled-pilot",
        "CHARTNAV_REAL_PHI_ENABLED": "1",
        "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST": "openai",
    })
    assert "REAL_PHI_WITH_AMBIENT_OPENAI" in codes


def test_ambient_assist_unset_is_safe():
    """Phase 57 — the deterministic ambient path is the production
    default. With no env var set, no AMBIENT_* finding fires."""
    codes = codes_for({"CHARTNAV_ENV": "local"})
    assert not any(c.startswith("AMBIENT_") for c in codes)
    assert "PRODUCTION_AMBIENT_OPENAI" not in codes
    assert "REAL_PHI_WITH_AMBIENT_OPENAI" not in codes


def test_ambient_assist_literal_non_openai_is_ignored():
    """Phase 57 — only the literal value `openai` triggers the
    ambient checks; `1`/`true`/`anthropic`/etc. are ignored at the
    runtime-safety layer (mirroring the service's behaviour)."""
    for val in ("1", "true", "yes", "on", "anthropic", "ibm"):
        codes = codes_for({
            "CHARTNAV_ENV": "production",
            "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST": val,
        })
        assert "AMBIENT_OPENAI_PRODUCTION" not in codes, (
            f"value {val!r} should not trigger AMBIENT_OPENAI_PRODUCTION"
        )
        assert "AMBIENT_OPENAI_NOT_DEMO" not in codes


def test_anthropic_provider_fails_as_blocked():
    codes = codes_for({"CHARTNAV_ENV": "local", "CHARTNAV_LLM_PROVIDER": "anthropic"})
    assert "LLM_PROVIDER_BLOCKED" in codes


def test_ibm_watsonx_provider_fails_as_blocked():
    codes = codes_for({"CHARTNAV_ENV": "local", "CHARTNAV_LLM_PROVIDER": "ibm_watsonx"})
    assert "LLM_PROVIDER_BLOCKED" in codes


def test_stt_live_vendor_without_approval_fails():
    codes = codes_for({"CHARTNAV_ENV": "local", "CHARTNAV_STT_PROVIDER": "openai_whisper"})
    assert "STT_VENDOR_WITHOUT_APPROVAL" in codes


def test_real_phi_enabled_with_demo_provider_fails():
    codes = codes_for({
        "CHARTNAV_ENV": "controlled-pilot",
        "CHARTNAV_REAL_PHI_ENABLED": "1",
        "CHARTNAV_LLM_PROVIDER": "openai",
    })
    assert "REAL_PHI_WITH_LIVE_LLM" in codes


def test_real_phi_enabled_with_active_stub_provider_fails():
    codes = codes_for({
        "CHARTNAV_ENV": "controlled-pilot",
        "CHARTNAV_REAL_PHI_ENABLED": "1",
        "CHARTNAV_LLM_ENABLED": "1",
        "CHARTNAV_LLM_PROVIDER": "deterministic_stub",
        "CHARTNAV_INTEGRATION_ADAPTER": "stub",
    })
    assert "REAL_PHI_WITH_STUB_LLM" in codes
    assert "REAL_PHI_WITH_STUB_INTEGRATION" in codes


def test_production_sqlite_and_dev_auth_fail():
    codes = codes_for({
        "CHARTNAV_ENV": "production",
        "DATABASE_URL": "sqlite:///tmp/chartnav.db",
        "CHARTNAV_AUTH_MODE": "header",
    })
    assert "PRODUCTION_SQLITE" in codes
    assert "PRODUCTION_DEV_AUTH" in codes


def test_secrets_are_not_printed_in_error_output():
    env = {
        "CHARTNAV_ENV": "production",
        "CHARTNAV_LLM_ENABLED": "1",
        "CHARTNAV_OPENAI_API_KEY": "sk-secret-should-not-print",
        "DATABASE_URL": "sqlite:///tmp/chartnav.db",
    }
    report = report_for(env)
    assert "sk-secret-should-not-print" not in report
    assert "sqlite:///tmp/chartnav.db" not in report
    assert "CHARTNAV_LLM_ENABLED" in report
    assert "DATABASE_URL" in report
