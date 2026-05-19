#!/usr/bin/env python3
"""ChartNav runtime safety validator.

This is a fail-closed preflight for local, CI, demo, staging, pilot,
and production environments. It inspects environment shape only; it
does not connect to vendors, databases, or identity providers, and it
never prints secret values.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


TRUTHY = {"1", "true", "yes", "on", "y"}
FAKE_DEMO_ENVS = {"local", "dev", "development", "test", "ci", "demo", "fake", "fake-data"}
LIVE_LLM_PROVIDERS = {"openai", "anthropic", "ibm_watsonx", "watsonx"}
BLOCKED_LLM_PROVIDERS = {"anthropic", "ibm_watsonx", "watsonx"}
DEMO_LLM_PROVIDERS = {"deterministic_stub", "stub"}
LIVE_STT_PROVIDERS = {"openai_whisper"}
SQLITE_RE = re.compile(r"^sqlite(?:\+[^:]*)?://", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    return value.strip()


def _lower(env: Mapping[str, str], name: str, default: str = "") -> str:
    return _clean(env.get(name), default).lower()


def _is_truthy(env: Mapping[str, str], name: str) -> bool:
    return _lower(env, name) in TRUTHY


def _env_name(env: Mapping[str, str]) -> str:
    return _lower(env, "CHARTNAV_ENV", "local")


def _is_fake_demo_mode(env: Mapping[str, str]) -> bool:
    if _is_truthy(env, "CHARTNAV_FAKE_DATA_ONLY"):
        return True
    return _env_name(env) in FAKE_DEMO_ENVS


def _load_env_file(path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            raise ValueError(f"{path}:{lineno}: expected NAME=value")
        name, value = line.split("=", 1)
        name = name.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"{path}:{lineno}: invalid environment variable name")
        value = value.strip().strip("'\"")
        loaded[name] = value
    return loaded


def build_env(base: Mapping[str, str] | None = None, env_file: Path | None = None) -> dict[str, str]:
    env = dict(base if base is not None else os.environ)
    if env_file is not None:
        env.update(_load_env_file(env_file))
    return env


def validate_env(env: Mapping[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    chartnav_env = _env_name(env)
    is_production = chartnav_env == "production"
    is_fake_demo = _is_fake_demo_mode(env)

    llm_provider = _lower(env, "CHARTNAV_LLM_PROVIDER", "deterministic_stub")
    llm_enabled = _is_truthy(env, "CHARTNAV_LLM_ENABLED")
    llm_real_phi = _is_truthy(env, "CHARTNAV_LLM_REAL_PHI_APPROVED")
    pilot_allow_openai = _is_truthy(env, "CHARTNAV_PILOT_ALLOW_LLM_OPENAI")
    fundus_assist = _lower(env, "CHARTNAV_FUNDUS_DRAFTING_ASSIST")
    ambient_assist = _lower(env, "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST")
    real_phi_enabled = _is_truthy(env, "CHARTNAV_REAL_PHI_ENABLED")

    # LLM safety.
    if llm_provider == "openai" and llm_real_phi:
        findings.append(Finding(
            "LLM_OPENAI_REAL_PHI",
            "CHARTNAV_LLM_PROVIDER=openai cannot be combined with CHARTNAV_LLM_REAL_PHI_APPROVED=1.",
        ))
    if llm_provider == "openai" and is_production:
        findings.append(Finding(
            "LLM_OPENAI_PRODUCTION",
            "CHARTNAV_LLM_PROVIDER=openai is fake-data/demo-only and is not approved for CHARTNAV_ENV=production.",
        ))
    if llm_enabled and is_production:
        findings.append(Finding(
            "LLM_ENABLED_PRODUCTION",
            "CHARTNAV_LLM_ENABLED=1 is not allowed in CHARTNAV_ENV=production; no production LLM path is approved.",
        ))
    if fundus_assist == "openai" and not is_fake_demo:
        findings.append(Finding(
            "FUNDUS_OPENAI_NOT_DEMO",
            "CHARTNAV_FUNDUS_DRAFTING_ASSIST=openai is allowed only in fake-data/demo environments.",
        ))
    if ambient_assist == "openai" and is_production:
        findings.append(Finding(
            "AMBIENT_OPENAI_PRODUCTION",
            "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai is fake-data/demo-only and is not approved for CHARTNAV_ENV=production.",
        ))
    if ambient_assist == "openai" and not is_fake_demo:
        findings.append(Finding(
            "AMBIENT_OPENAI_NOT_DEMO",
            "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai is allowed only in fake-data/demo environments.",
        ))
    if ambient_assist == "openai" and llm_real_phi:
        findings.append(Finding(
            "AMBIENT_OPENAI_REAL_PHI_APPROVED",
            "CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai cannot be combined with CHARTNAV_LLM_REAL_PHI_APPROVED=1.",
        ))
    if pilot_allow_openai:
        findings.append(Finding(
            "LLM_OPENAI_PILOT_ALLOW",
            "CHARTNAV_PILOT_ALLOW_LLM_OPENAI=1 is blocked for the fake-data adapter semantics.",
        ))
    if llm_provider in BLOCKED_LLM_PROVIDERS:
        findings.append(Finding(
            "LLM_PROVIDER_BLOCKED",
            "CHARTNAV_LLM_PROVIDER names a blocked provider; Anthropic and IBM watsonx are not approved/wired for production.",
        ))
    if real_phi_enabled and llm_provider in LIVE_LLM_PROVIDERS:
        findings.append(Finding(
            "REAL_PHI_WITH_LIVE_LLM",
            "CHARTNAV_REAL_PHI_ENABLED=1 cannot be combined with demo-only/fake-data-only LLM providers.",
        ))
    if real_phi_enabled and llm_enabled and llm_provider in DEMO_LLM_PROVIDERS:
        findings.append(Finding(
            "REAL_PHI_WITH_STUB_LLM",
            "CHARTNAV_REAL_PHI_ENABLED=1 cannot use deterministic_stub/stub as an active LLM provider.",
        ))
    if real_phi_enabled and fundus_assist == "openai":
        findings.append(Finding(
            "REAL_PHI_WITH_FUNDUS_OPENAI",
            "CHARTNAV_REAL_PHI_ENABLED=1 cannot be combined with CHARTNAV_FUNDUS_DRAFTING_ASSIST=openai.",
        ))
    if real_phi_enabled and ambient_assist == "openai":
        findings.append(Finding(
            "REAL_PHI_WITH_AMBIENT_OPENAI",
            "CHARTNAV_REAL_PHI_ENABLED=1 cannot be combined with CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai.",
        ))

    # STT/audio safety.
    stt_provider = _lower(env, "CHARTNAV_STT_PROVIDER", "stub")
    real_phi_approved = _is_truthy(env, "CHARTNAV_REAL_PHI_APPROVED")
    stt_vendor_approved = _is_truthy(env, "CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER")
    stt_prod_approved = _is_truthy(env, "CHARTNAV_PRODUCTION_ALLOW_STT_OPENAI_WHISPER")
    if stt_provider in LIVE_STT_PROVIDERS and real_phi_approved and not stt_vendor_approved:
        findings.append(Finding(
            "STT_REAL_PHI_WITHOUT_APPROVAL",
            "CHARTNAV_STT_PROVIDER=openai_whisper with CHARTNAV_REAL_PHI_APPROVED=1 requires explicit STT vendor approval.",
        ))
    if stt_provider in LIVE_STT_PROVIDERS and is_production and not stt_prod_approved:
        findings.append(Finding(
            "STT_PRODUCTION_WITHOUT_APPROVAL",
            "CHARTNAV_STT_PROVIDER=openai_whisper is blocked in production without explicit production STT approval.",
        ))
    if stt_provider in LIVE_STT_PROVIDERS and not (stt_vendor_approved or stt_prod_approved):
        findings.append(Finding(
            "STT_VENDOR_WITHOUT_APPROVAL",
            "CHARTNAV_STT_PROVIDER=openai_whisper requires an explicit vendor approval flag.",
        ))
    if real_phi_enabled and stt_provider in {"stub", "deterministic_stub"}:
        findings.append(Finding(
            "REAL_PHI_WITH_STUB_STT",
            "CHARTNAV_REAL_PHI_ENABLED=1 cannot use demo-only/stub STT providers.",
        ))
    integration_adapter = _lower(env, "CHARTNAV_INTEGRATION_ADAPTER")
    if real_phi_enabled and integration_adapter == "stub":
        findings.append(Finding(
            "REAL_PHI_WITH_STUB_INTEGRATION",
            "CHARTNAV_REAL_PHI_ENABLED=1 cannot use the stub integration adapter.",
        ))

    # Demo/real-PHI and production hardening.
    database_url = _clean(env.get("DATABASE_URL"))
    if is_production and (not database_url or SQLITE_RE.match(database_url)):
        findings.append(Finding(
            "PRODUCTION_SQLITE",
            "CHARTNAV_ENV=production requires a non-SQLite DATABASE_URL.",
        ))
    auth_mode = _lower(env, "CHARTNAV_AUTH_MODE", "header")
    if is_production and auth_mode in {"header", "dev", "demo", "mock"}:
        findings.append(Finding(
            "PRODUCTION_DEV_AUTH",
            "CHARTNAV_ENV=production cannot use CHARTNAV_AUTH_MODE=header/dev/demo/mock.",
        ))
    if is_production and fundus_assist == "openai":
        findings.append(Finding(
            "PRODUCTION_FUNDUS_OPENAI",
            "Production cannot enable demo-only OpenAI fundus assist.",
        ))
    if is_production and ambient_assist == "openai":
        findings.append(Finding(
            "PRODUCTION_AMBIENT_OPENAI",
            "Production cannot enable demo-only OpenAI ambient documentation assist.",
        ))

    return findings


def format_report(findings: list[Finding]) -> str:
    lines = ["ChartNav runtime safety validator"]
    if not findings:
        lines.append("PASS - no unsafe runtime combinations detected.")
        return "\n".join(lines)
    lines.append(f"FAIL - {len(findings)} unsafe runtime combination(s) detected.")
    for finding in findings:
        lines.append(f"- {finding.code}: {finding.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check ChartNav runtime safety gates.")
    parser.add_argument("--env-file", type=Path, help="Optional .env-style file to overlay on the shell environment.")
    args = parser.parse_args(argv)
    try:
        env = build_env(env_file=args.env_file)
    except ValueError as exc:
        print(f"FAIL - {exc}", file=sys.stderr)
        return 2
    findings = validate_env(env)
    print(format_report(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
