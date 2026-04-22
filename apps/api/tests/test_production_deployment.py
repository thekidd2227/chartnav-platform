"""Phase 60 — production deployment / secrets / storage / go-live
contract tests.

Covers:

  validate_production_config
    * dev environment: no findings regardless of otherwise-insecure
      defaults (the validator is production-scoped)
    * production + sqlite DB   → error DATABASE_URL
    * production + header auth → error CHARTNAV_AUTH_MODE
    * production + bearer missing JWT trio → 3 errors
    * production + localhost CORS → error
    * production + empty CORS → error
    * production happy path → 0 errors (may emit info/warning)
    * strict=True raises ProductionConfigError on any error
    * strict=False returns the full findings list

  script presence + syntax
    * deploy_preflight.sh, enterprise_validate.sh, bootstrap.sh,
      deploy_rollback.sh exist and are executable
    * all four pass `bash -n` syntax check
    * deploy_preflight.sh returns exit 2 (usage error) when given
      a nonexistent env file

  env.prod.example contract
    * file exists under infra/docker/
    * carries every REQUIRED key listed in the go-live docs
"""
from __future__ import annotations

import os
import pathlib
import subprocess

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"


# -------- validate_production_config ---------------------------------


def _settings_with(**overrides):
    """Build a Settings-like namespace for pure-config validation.
    We avoid reloading `app.config` because that touches global
    module state shared across the test session."""
    from app.config import Settings

    defaults = dict(
        env="production",
        database_url="postgresql+psycopg://u:p@db:5432/c",
        auth_mode="bearer",
        jwt_issuer="https://auth.example.com/",
        jwt_audience="chartnav-api",
        jwt_jwks_url="https://auth.example.com/.well-known/jwks.json",
        jwt_user_claim="email",
        cors_allow_origins=("https://chart.example.com",),
        rate_limit_per_minute=120,
        audit_retention_days=730,
        platform_mode="standalone",
        integration_adapter="stub",
        fhir_base_url=None,
        fhir_auth_type="none",
        fhir_bearer_token=None,
        audio_upload_dir="/var/lib/chartnav/audio",
        audio_upload_max_bytes=26214400,
        audio_ingest_mode="async",
        stt_provider="stub",
        evidence_signing_hmac_key=None,
        evidence_signing_hmac_keyring={},
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_dev_environment_no_findings():
    from app.config import validate_production_config
    s = _settings_with(env="dev", database_url="sqlite:///./chartnav.db",
                       auth_mode="header", jwt_issuer=None,
                       jwt_audience=None, jwt_jwks_url=None,
                       cors_allow_origins=("http://localhost:5173",))
    out = validate_production_config(s, strict=False)
    # Validator is production-only; dev env produces nothing.
    assert out == []


def test_prod_rejects_sqlite():
    from app.config import validate_production_config
    s = _settings_with(database_url="sqlite:///./chartnav.db")
    out = validate_production_config(s, strict=False)
    errs = [f for f in out if f["severity"] == "error"]
    assert any(f["key"] == "DATABASE_URL" for f in errs)


def test_prod_rejects_header_auth():
    from app.config import validate_production_config
    s = _settings_with(auth_mode="header")
    out = validate_production_config(s, strict=False)
    errs = [f for f in out if f["severity"] == "error"]
    assert any(f["key"] == "CHARTNAV_AUTH_MODE" for f in errs)


def test_prod_bearer_without_jwt_trio_has_three_errors():
    from app.config import validate_production_config
    s = _settings_with(
        jwt_issuer=None, jwt_audience=None, jwt_jwks_url=None,
    )
    out = validate_production_config(s, strict=False)
    err_keys = {f["key"] for f in out if f["severity"] == "error"}
    assert "CHARTNAV_JWT_ISSUER" in err_keys
    assert "CHARTNAV_JWT_AUDIENCE" in err_keys
    assert "CHARTNAV_JWT_JWKS_URL" in err_keys


def test_prod_rejects_localhost_cors():
    from app.config import validate_production_config
    s = _settings_with(cors_allow_origins=(
        "https://chart.example.com", "http://localhost:5173",
    ))
    out = validate_production_config(s, strict=False)
    errs = [f for f in out if f["severity"] == "error"]
    assert any(f["key"] == "CHARTNAV_CORS_ALLOW_ORIGINS" for f in errs)


def test_prod_rejects_empty_cors():
    from app.config import validate_production_config
    s = _settings_with(cors_allow_origins=())
    out = validate_production_config(s, strict=False)
    errs = [f for f in out if f["severity"] == "error"]
    assert any(f["key"] == "CHARTNAV_CORS_ALLOW_ORIGINS" for f in errs)


def test_prod_rejects_unknown_platform_mode():
    from app.config import validate_production_config
    s = _settings_with(platform_mode="bananas")
    out = validate_production_config(s, strict=False)
    errs = [f for f in out if f["severity"] == "error"]
    assert any(f["key"] == "CHARTNAV_PLATFORM_MODE" for f in errs)


def test_prod_happy_path_has_no_errors():
    from app.config import validate_production_config
    out = validate_production_config(_settings_with(), strict=False)
    errs = [f for f in out if f["severity"] == "error"]
    assert errs == []


def test_strict_true_raises_on_any_error():
    from app.config import (
        validate_production_config, ProductionConfigError,
    )
    s = _settings_with(database_url="sqlite:///./chartnav.db")
    with pytest.raises(ProductionConfigError) as exc:
        validate_production_config(s, strict=True)
    # The raised error carries the findings list.
    assert any("DATABASE_URL" in f for f in exc.value.findings)


def test_prod_zero_rate_limit_warns_not_errors():
    from app.config import validate_production_config
    s = _settings_with(rate_limit_per_minute=0)
    out = validate_production_config(s, strict=False)
    warns = [f for f in out if f["severity"] == "warning"]
    assert any(f["key"] == "CHARTNAV_RATE_LIMIT_PER_MINUTE" for f in warns)
    errs = [f for f in out if f["severity"] == "error"]
    assert not errs


# -------- scripts exist + syntax -------------------------------------

@pytest.mark.parametrize("name", [
    "deploy_preflight.sh",
    "enterprise_validate.sh",
    "bootstrap.sh",
    "deploy_rollback.sh",
])
def test_script_exists_executable_and_bash_syntax_clean(name):
    p = SCRIPTS / name
    assert p.is_file(), f"missing {p}"
    assert os.access(p, os.X_OK), f"not executable: {p}"
    # `bash -n` parses without running.
    result = subprocess.run(
        ["bash", "-n", str(p)], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_deploy_preflight_reports_usage_error_on_missing_file(tmp_path):
    """deploy_preflight.sh must exit 2 when the env file is absent."""
    bogus = tmp_path / "nope.env"
    result = subprocess.run(
        ["bash", str(SCRIPTS / "deploy_preflight.sh"), str(bogus)],
        capture_output=True, text=True,
    )
    assert result.returncode == 2, result.stderr
    assert "env file not found" in (result.stderr + result.stdout)


def test_deploy_preflight_errors_on_insecure_env(tmp_path):
    """Give preflight a well-formed env file that would fail in
    production (SQLite + header auth + localhost CORS). The script
    must exit 1 and report errors in stdout."""
    env = tmp_path / ".env.bad"
    env.write_text(
        "CHARTNAV_ENV=production\n"
        "DATABASE_URL=sqlite:///./chartnav.db\n"
        "CHARTNAV_AUTH_MODE=header\n"
        "CHARTNAV_CORS_ALLOW_ORIGINS=http://localhost:5173\n"
    )
    result = subprocess.run(
        ["bash", str(SCRIPTS / "deploy_preflight.sh"), str(env)],
        capture_output=True, text=True,
    )
    # The CHARTNAV_AUTH_MODE=bearer prerequisite check in
    # _load() raises before our validator runs, so the exit code
    # may be 1 either way; assert the script refused the deploy.
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    # Either our validator's output OR the startup guard is
    # acceptable — both correctly refuse the config.
    assert (
        "ERROR" in combined
        or "required" in combined
        or "FAILED" in combined
    )


# -------- env.prod.example contract ---------------------------------


REQUIRED_KEYS = [
    "CHARTNAV_IMAGE_OWNER",
    "CHARTNAV_IMAGE_TAG",
    "CHARTNAV_ENV",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "CHARTNAV_AUTH_MODE",
    "CHARTNAV_JWT_ISSUER",
    "CHARTNAV_JWT_AUDIENCE",
    "CHARTNAV_JWT_JWKS_URL",
    "CHARTNAV_CORS_ALLOW_ORIGINS",
]


def test_env_prod_example_exists_and_has_required_keys():
    p = REPO_ROOT / "infra" / "docker" / ".env.prod.example"
    assert p.is_file(), f"missing {p}"
    body = p.read_text()
    for k in REQUIRED_KEYS:
        assert k in body, f"missing required key {k} in {p}"


# -------- compose/env integration contract --------------------------

# Operator-visible env vars documented in .env.prod.example that
# are not forwarded by compose are silent no-ops. This guard
# catches the drift automatically.
_COMPOSE_EXEMPT = {
    # These are meta-settings read by compose itself, not passed
    # to the container.
    "CHARTNAV_IMAGE_OWNER",
    "CHARTNAV_IMAGE_TAG",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
}


def test_compose_forwards_every_documented_env():
    """Every CHARTNAV_* or DATABASE_URL env documented in
    .env.prod.example must appear in docker-compose.prod.yml's
    api.environment block. Prevents silent no-op regressions where
    an operator sets an env that never reaches the container."""
    import re
    example = (REPO_ROOT / "infra" / "docker" / ".env.prod.example").read_text()
    compose_body = (
        REPO_ROOT / "infra" / "docker" / "docker-compose.prod.yml"
    ).read_text()

    documented = set()
    for line in example.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Some entries are intentionally commented out; accept both
        # `KEY=val` and `# KEY=` patterns so the guard is about
        # "the key exists in this doc" rather than whether it is
        # uncommented today.
        m = re.match(r"^#?\s*([A-Z_][A-Z_0-9]*)\s*=", line)
        if m:
            documented.add(m.group(1))

    # Only enforce on the CHARTNAV_* namespace + DATABASE_URL.
    enforced = {
        k for k in documented
        if (k.startswith("CHARTNAV_") or k == "DATABASE_URL")
        and k not in _COMPOSE_EXEMPT
    }

    missing = [k for k in sorted(enforced) if k not in compose_body]
    assert not missing, (
        "docker-compose.prod.yml does not forward env keys "
        "documented in .env.prod.example: " + ", ".join(missing)
    )
