#!/usr/bin/env python3
"""Fail if development header-auth could be active in a production posture.

Production must use bearer/JWT auth. Header auth (`X-User-Email`) is dev-only.
Reads the environment (pass a safe example env to dry-run). Stdlib only.

Exit 0 = safe; non-zero = a finding.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def findings(env: dict) -> list[str]:
    out: list[str] = []
    is_prod = (env.get("CHARTNAV_ENV", "dev") or "dev").lower() == "prod"
    mode = (env.get("CHARTNAV_AUTH_MODE", "header") or "header").lower()
    if is_prod and mode != "bearer":
        out.append(
            f"CHARTNAV_AUTH_MODE={mode!r} in production — must be 'bearer'. "
            "X-User-Email header auth is dev-only and must never authenticate "
            "in staging/production."
        )
    if mode == "bearer":
        for var in ("CHARTNAV_JWT_ISSUER", "CHARTNAV_JWT_AUDIENCE",
                    "CHARTNAV_JWT_JWKS_URL"):
            if not env.get(var):
                out.append(f"bearer mode requires {var} (issuer/audience/JWKS "
                           "validation) — missing.")
    # An explicit dev-trust escape hatch must never be on in prod.
    if is_prod and (env.get("CHARTNAV_TRUST_USER_HEADER", "").lower() in {"1", "true", "yes"}):
        out.append("CHARTNAV_TRUST_USER_HEADER is enabled in production — forbidden.")
    return out


def main() -> int:
    f = findings(dict(os.environ))
    if f:
        print("❌ dev-auth verification FAILED:")
        for x in f:
            print(f"  - {x}")
        return 1
    print("✅ no dev (header) auth exposure detected for this configuration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
