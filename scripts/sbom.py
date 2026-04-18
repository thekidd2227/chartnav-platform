"""Generate a minimal, honest SBOM for ChartNav releases.

Captures:
  - backend Python deps (`pip list --format json` against apps/api)
  - frontend Node deps (`npm list --all --json` against apps/web)
  - git sha + git tag (if present)
  - docker image reference (if CHARTNAV_IMAGE_TAG is set)

Output is JSON to stdout (or to `--out <path>`). The format is
intentionally simple (project + deps arrays) rather than full
CycloneDX — honest shape for a project of this size. Teams that need
signed CycloneDX should plug in `cyclonedx-py` + `cyclonedx-npm` later;
the seam is clear.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _py_deps() -> list[dict]:
    """`pip list --format json` using the API's venv if present."""
    venv_pip = REPO_ROOT / "apps/api/.venv/bin/pip"
    pip = str(venv_pip) if venv_pip.exists() else "pip"
    try:
        out = subprocess.check_output(
            [pip, "list", "--format", "json"], cwd=REPO_ROOT / "apps/api"
        )
        return json.loads(out)
    except Exception as e:  # pragma: no cover
        return [{"error": f"pip list failed: {e}"}]


def _npm_deps() -> dict:
    """Parse the top-level node_modules tree via `npm list`.

    Falls back to reading `package-lock.json` when the tree can't be
    enumerated (e.g. in a CI cache without installed deps).
    """
    try:
        out = subprocess.check_output(
            ["npm", "list", "--all", "--json", "--omit=peer"],
            cwd=REPO_ROOT / "apps/web",
        )
        return json.loads(out)
    except Exception:
        lock = REPO_ROOT / "apps/web/package-lock.json"
        if lock.exists():
            data = json.loads(lock.read_text())
            return {
                "source": "package-lock.json",
                "name": data.get("name"),
                "version": data.get("version"),
                "packages_count": len(data.get("packages", {})),
            }
        return {"error": "npm list + package-lock.json both unavailable"}


def build(version: str | None = None) -> dict:
    return {
        "project": "chartnav-platform",
        "version": version or os.environ.get("CHARTNAV_IMAGE_TAG") or _git(
            "describe", "--tags", "--always", "--dirty"
        ) or "dev",
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "git": {
            "sha": _git("rev-parse", "HEAD"),
            "ref": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "tag": _git("describe", "--tags", "--exact-match"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "image": {
            "owner": os.environ.get("CHARTNAV_IMAGE_OWNER"),
            "tag": os.environ.get("CHARTNAV_IMAGE_TAG"),
        },
        "python_deps": _py_deps(),
        "node_deps": _npm_deps(),
        "notes": (
            "Not a signed CycloneDX document. Captures the exact versions of "
            "every backend and frontend dep plus git + image identity at build "
            "time. Sufficient for an inventory audit; a signed SBOM (e.g. via "
            "cyclonedx-py + cosign) is the next honest step."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    sbom = build(args.version)
    payload = json.dumps(sbom, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(payload)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
