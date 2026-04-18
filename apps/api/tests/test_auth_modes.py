"""Tests for the production-shaped auth seam.

Covers:
- bearer mode refuses to import without JWT env
- header mode still works
- bearer mode: valid token, missing token, invalid token, wrong
  issuer, wrong audience, unknown user, expired token, missing claim
"""

from __future__ import annotations

import base64
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

API_DIR = Path(__file__).resolve().parents[1]


# ---- RSA / JWKS fixture -------------------------------------------------

KID = "test-kid-1"


class _SigningKeyStub:
    """`.key` is all auth.py reads off the returned object."""
    def __init__(self, public_key):
        self.key = public_key


class _TestJWKSClient:
    """Drop-in replacement for `jwt.PyJWKClient` in tests.

    Hands back our locally generated RSA public key directly — skips
    JWKS JSON round-tripping entirely. Production still uses PyJWKClient
    against a real JWKS URL.
    """
    def __init__(self, public_key):
        self._pk = public_key

    def get_signing_key_from_jwt(self, _token):
        return _SigningKeyStub(self._pk)


@pytest.fixture(scope="session")
def rsa_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_priv = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return {"private_pem": pem_priv, "public_key": key.public_key()}


def _make_token(
    private_pem: bytes,
    *,
    iss: str,
    aud: str,
    claim: str = "email",
    claim_value: str = "admin@chartnav.local",
    ttl: int = 300,
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + ttl,
        claim: claim_value,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload, private_pem, algorithm="RS256", headers={"kid": KID}
    )


# ---- App lifecycle helpers ----------------------------------------------

def _reload_app(monkeypatch, tmp_path, *, mode: str, extra_env: dict[str, str]):
    """Spin up a fresh app + DB in the given auth mode."""
    db_path = tmp_path / "chartnav.db"
    url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CHARTNAV_AUTH_MODE", mode)
    for k in list(extra_env):
        monkeypatch.setenv(k, extra_env[k])
    # Ensure prior JWT env doesn't bleed when tests flip modes.
    for k in ("CHARTNAV_JWT_ISSUER", "CHARTNAV_JWT_AUDIENCE", "CHARTNAV_JWT_JWKS_URL"):
        if k not in extra_env:
            monkeypatch.delenv(k, raising=False)

    subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(API_DIR / "alembic.ini"),
            "-x", f"sqlalchemy.url={url}",
            "upgrade", "head",
        ],
        check=True, cwd=API_DIR,
    )

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    import scripts_seed
    importlib.reload(scripts_seed)
    scripts_seed.main()

    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ---- Existing tests (kept) ----------------------------------------------

def test_bearer_mode_requires_jwt_env(monkeypatch, tmp_path):
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")
    monkeypatch.setenv("CHARTNAV_AUTH_MODE", "bearer")
    for k in ("CHARTNAV_JWT_ISSUER", "CHARTNAV_JWT_AUDIENCE", "CHARTNAV_JWT_JWKS_URL"):
        monkeypatch.delenv(k, raising=False)

    with pytest.raises(RuntimeError) as e:
        import app.config  # noqa: F401

    msg = str(e.value)
    assert "CHARTNAV_JWT_ISSUER" in msg
    assert "CHARTNAV_JWT_AUDIENCE" in msg
    assert "CHARTNAV_JWT_JWKS_URL" in msg


def test_header_mode_unchanged_contract(monkeypatch, tmp_path):
    client = _reload_app(monkeypatch, tmp_path, mode="header", extra_env={})
    r = client.get("/me", headers={"X-User-Email": "admin@chartnav.local"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


# ---- Bearer mode real-JWT tests -----------------------------------------

BEARER_ENV = {
    "CHARTNAV_JWT_ISSUER": "https://auth.example.com/",
    "CHARTNAV_JWT_AUDIENCE": "chartnav-api",
    "CHARTNAV_JWT_JWKS_URL": "https://auth.example.com/.well-known/jwks.json",
    "CHARTNAV_JWT_USER_CLAIM": "email",
}


def _bearer_client(monkeypatch, tmp_path, rsa_keys):
    client = _reload_app(monkeypatch, tmp_path, mode="bearer", extra_env=BEARER_ENV)
    # Inject our fake JWKS client into the freshly-loaded auth module
    import app.auth as auth_mod
    auth_mod.set_jwk_client(_TestJWKSClient(rsa_keys["public_key"]))
    return client


def test_bearer_valid_token_resolves_caller(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    tok = _make_token(
        rsa_keys["private_pem"],
        iss=BEARER_ENV["CHARTNAV_JWT_ISSUER"],
        aud=BEARER_ENV["CHARTNAV_JWT_AUDIENCE"],
        claim_value="admin@chartnav.local",
    )
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["email"] == "admin@chartnav.local"
    assert body["role"] == "admin"
    assert body["organization_id"] == 1


def test_bearer_missing_token(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "missing_auth_header"


def test_bearer_malformed_header(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    r = client.get("/me", headers={"Authorization": "NotBearer something"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_authorization_header"


def test_bearer_garbage_token(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    r = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_token"


def test_bearer_wrong_issuer(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    tok = _make_token(
        rsa_keys["private_pem"],
        iss="https://evil.example.com/",
        aud=BEARER_ENV["CHARTNAV_JWT_AUDIENCE"],
    )
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_issuer"


def test_bearer_wrong_audience(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    tok = _make_token(
        rsa_keys["private_pem"],
        iss=BEARER_ENV["CHARTNAV_JWT_ISSUER"],
        aud="wrong-aud",
    )
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_audience"


def test_bearer_expired(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    tok = _make_token(
        rsa_keys["private_pem"],
        iss=BEARER_ENV["CHARTNAV_JWT_ISSUER"],
        aud=BEARER_ENV["CHARTNAV_JWT_AUDIENCE"],
        ttl=-10,
    )
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "token_expired"


def test_bearer_unknown_user(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    tok = _make_token(
        rsa_keys["private_pem"],
        iss=BEARER_ENV["CHARTNAV_JWT_ISSUER"],
        aud=BEARER_ENV["CHARTNAV_JWT_AUDIENCE"],
        claim_value="ghost@nowhere.test",
    )
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "unknown_user"


def test_bearer_missing_user_claim(monkeypatch, tmp_path, rsa_keys):
    client = _bearer_client(monkeypatch, tmp_path, rsa_keys)
    # Strip the email claim entirely by using an unused claim name.
    now = int(time.time())
    tok = jwt.encode(
        {
            "iss": BEARER_ENV["CHARTNAV_JWT_ISSUER"],
            "aud": BEARER_ENV["CHARTNAV_JWT_AUDIENCE"],
            "iat": now,
            "exp": now + 300,
            "sub": "no-mapping",
        },
        rsa_keys["private_pem"],
        algorithm="RS256",
        headers={"kid": KID},
    )
    r = client.get("/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "missing_user_claim"
