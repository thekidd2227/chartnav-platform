#!/usr/bin/env python3
"""ChartNav production-readiness gate.

Fails (non-zero) when any production blocker is present:
  - header authentication enabled            - object storage encryption missing
  - SQLite configured                        - database TLS not required
  - default / demo secrets present           - backup configuration absent
  - debug mode enabled                       - required audit logging disabled
  - demo seed enabled                        - unresolved (multi-head) migrations
  - unrestricted CORS wildcard               - marketing asset governance fails
  - required HTTPS hostnames missing

Reads the environment; pass `--env-file <path>` to dry-run against a safe
example configuration (no live secrets). Stdlib only.

NOTE: this checks declared *configuration*. It does not, and cannot, prove a
live deployment is HIPAA-compliant, BAA-covered, or security-approved.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))

DEV_SECRET_VALUES = {"", "dev", "devsecret", "changeme", "change-me", "secret",
                     "password", "test", "example", "placeholder", "todo"}


def load_env_file(path: str) -> dict:
    env = dict(os.environ)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def truthy(v) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def check(env: dict) -> list[str]:
    f: list[str] = []
    is_prod = (env.get("CHARTNAV_ENV", "dev") or "dev").lower() == "prod"
    if not is_prod:
        f.append("CHARTNAV_ENV is not 'prod' — this configuration is not a "
                 "production posture.")

    # auth
    if (env.get("CHARTNAV_AUTH_MODE", "header") or "header").lower() != "bearer":
        f.append("header auth enabled — production requires CHARTNAV_AUTH_MODE=bearer.")

    # database
    db = (env.get("DATABASE_URL", "") or "").lower()
    if db.startswith("sqlite") or not db:
        f.append("SQLite/empty DATABASE_URL — production requires managed PostgreSQL.")
    elif not re.search(r"sslmode=require|ssl=true|sslmode=verify", db):
        f.append("DATABASE_URL does not require TLS (expect sslmode=require).")

    # secrets
    for var in ("CHARTNAV_SECRET_KEY", "CHARTNAV_SESSION_SECRET"):
        val = env.get(var)
        if val is None:
            f.append(f"{var} is unset.")
        elif val.strip().lower() in DEV_SECRET_VALUES or len(val) < 16:
            f.append(f"{var} looks like a default/weak secret.")

    # debug / demo seed
    if truthy(env.get("CHARTNAV_DEBUG")) or truthy(env.get("DEBUG")):
        f.append("debug mode enabled — must be off in production.")
    if truthy(env.get("CHARTNAV_SEED_DEMO")) or truthy(env.get("CHARTNAV_DEMO_SEED")):
        f.append("demo seed enabled — must be off in production.")

    # CORS
    cors = env.get("CHARTNAV_CORS_ALLOW_ORIGINS", "")
    if any(o.strip() == "*" for o in cors.split(",")):
        f.append("CORS allows '*' — must be an explicit HTTPS allowlist.")

    # HTTPS hostnames
    for var in ("CHARTNAV_APP_URL", "CHARTNAV_API_URL"):
        val = env.get(var, "")
        if not val:
            f.append(f"{var} is missing (required HTTPS hostname).")
        elif not val.startswith("https://"):
            f.append(f"{var} must be https://.")

    # object storage encryption
    if (env.get("CHARTNAV_STORAGE_BACKEND", "local") or "local").lower() != "s3":
        f.append("CHARTNAV_STORAGE_BACKEND must be 's3' in production (local FS is dev-only).")
    elif not env.get("CHARTNAV_S3_KMS_KEY_ID"):
        f.append("object storage encryption not configured (CHARTNAV_S3_KMS_KEY_ID unset).")

    # backups
    if not truthy(env.get("CHARTNAV_BACKUPS_CONFIGURED")):
        f.append("backup configuration absent (CHARTNAV_BACKUPS_CONFIGURED not set) — "
                 "RDS automated backups + AWS Backup must be provisioned via IaC.")

    # audit logging
    try:
        if int(env.get("CHARTNAV_AUDIT_RETENTION_DAYS", "0") or "0") <= 0:
            f.append("audit logging retention disabled (CHARTNAV_AUDIT_RETENTION_DAYS<=0).")
    except ValueError:
        f.append("CHARTNAV_AUDIT_RETENTION_DAYS is not an integer.")

    # migrations: single Alembic head (no unresolved divergence)
    heads = _alembic_heads()
    if heads is None:
        f.append("could not determine Alembic heads (alembic unavailable).")
    elif len(heads) != 1:
        f.append(f"unresolved migrations: {len(heads)} Alembic heads {heads}.")

    return f


def _alembic_heads():
    api = os.path.join(ROOT, "apps", "api")
    venv_alembic = os.path.join(api, ".venv", "bin", "alembic")
    exe = venv_alembic if os.path.exists(venv_alembic) else "alembic"
    try:
        out = subprocess.run([exe, "heads"], cwd=api, capture_output=True,
                             text=True, timeout=60)
        if out.returncode != 0:
            return None
        return [ln.split()[0] for ln in out.stdout.splitlines() if ln.strip()]
    except (OSError, subprocess.SubprocessError):
        return None


def _run(script: str, env: dict) -> int:
    return subprocess.run([sys.executable, os.path.join(HERE, script)],
                          env=env).returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=None)
    args = ap.parse_args()
    env = load_env_file(args.env_file) if args.env_file else dict(os.environ)

    print("── ChartNav production readiness ──")
    blockers = check(env)

    sub_rc = 0
    for script in ("verify_no_dev_auth.py", "verify_tenant_isolation.py",
                   "verify_marketing_asset_governance.py"):
        rc = _run(script, env)
        sub_rc = sub_rc or rc

    if blockers:
        print(f"\n❌ NOT production-ready — {len(blockers)} blocker(s):")
        for b in blockers:
            print(f"  - {b}")
    if sub_rc:
        print("\n❌ a sub-verifier reported a finding (see above).")
    if blockers or sub_rc:
        print("\nThis gate checks declared configuration only — it does not "
              "assert HIPAA/BAA/security approval.")
        return 1
    print("\n✅ configuration passes the production-readiness gate "
          "(declared config only — not a compliance attestation).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
