#!/usr/bin/env python3
"""Verify high-risk claim policy fragments remain in every scanner."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "docs" / "commercial" / "claims-policy.json"
SCANNERS = [
    REPO_ROOT / "scripts" / "check_commercial_claims.sh",
    REPO_ROOT / "scripts" / "check_website_claims.sh",
    REPO_ROOT / "scripts" / "check_demo_claims.sh",
]


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    scanner_text = {
        scanner: scanner.read_text(encoding="utf-8")
        for scanner in SCANNERS
    }
    failures: list[str] = []
    for entry in policy["entries"]:
        if not entry.get("sync_required", False):
            continue
        for fragment in entry.get("scanner_fragments", []):
            for scanner, text in scanner_text.items():
                if fragment not in text:
                    failures.append(f"{scanner.relative_to(REPO_ROOT)} missing policy fragment: {fragment}")
    if failures:
        print("FAIL - claim policy/scanner sync drift detected.")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS - claim policy sync fragments are present in all required scanners.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
