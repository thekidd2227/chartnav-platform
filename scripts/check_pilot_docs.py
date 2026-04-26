#!/usr/bin/env python3
"""Phase 2 item 7 — pilot-docs lint.

Spec: docs/chartnav/closure/PHASE_B_Onboarding_Training_and_Support.md §4.

Asserts:
  1. Every required pilot doc exists.
  2. Every required section heading is present in each doc.
  3. No `TBD`, `TODO`, or `FIXME` strings appear in any pilot doc.
  4. Every cross-reference between pilot docs resolves to a real file.

Exit 0 on success; exit 1 on any failure with a structured report.

Run from the repo root or via the Makefile target `make pilot-docs`.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = REPO_ROOT / "docs" / "pilot"

# Required docs and their required section headings (any heading
# level — we just check the substring after `# ` / `## `).
REQUIRED_DOCS: dict[str, list[str]] = {
    "scope-template.md": [
        "Parties", "Scope", "Exit criteria",
        "Support", "Data and privacy", "Sign-off",
    ],
    "exit-criteria.md": [
        "Median time from transcript ingest to signed note",
        "Missing-flag resolution rate",
        "Reminder completion rate",
        "What is NOT a Phase B exit criterion",
    ],
    "onboarding-checklist.md": [
        "Day 0 — kickoff call",
        "Day 0 — technical prerequisites",
        "Day 1 — provisioning",
        "First five encounters",
        "Week 2 — review",
    ],
    "training-matrix.md": [
        "Matrix",
        "What each role does NOT need",
        "Walk-through clip pack",
    ],
    "runbook-30-60-90.md": [
        "Day 1", "Day 7", "Day 14", "Day 30", "Day 60", "Day 90",
    ],
    "support-tier.md": [
        "What the pilot tier includes",
        "What the pilot tier does NOT include",
        "Escalation path",
        "Conversion to paid",
    ],
    "escalation-matrix.md": [
        "Severity definitions",
        "Escalation path per severity",
        "Outside business hours",
    ],
}

# Tokens that mean the doc is unfinished.
FORBIDDEN_TOKENS = ("TBD", "TODO", "FIXME")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _heading_matches(text: str, heading: str) -> bool:
    """Match any markdown heading line that contains the substring."""
    for line in text.splitlines():
        if line.startswith("#") and heading in line:
            return True
    return False


def _link_targets(text: str) -> Iterable[str]:
    # Markdown link [label](target) — only relative md targets.
    for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = m.group(1).split("#")[0]
        if target.endswith(".md"):
            yield target


def main() -> int:
    failures: list[str] = []
    for fname, sections in REQUIRED_DOCS.items():
        path = PILOT_DIR / fname
        if not path.is_file():
            failures.append(f"missing pilot doc: {path.relative_to(REPO_ROOT)}")
            continue
        text = _read(path)
        for tok in FORBIDDEN_TOKENS:
            if re.search(rf"\b{tok}\b", text):
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: forbidden token "
                    f"{tok!r} found"
                )
        for heading in sections:
            if not _heading_matches(text, heading):
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: missing required "
                    f"heading containing {heading!r}"
                )
        # Cross-reference check.
        for target in _link_targets(text):
            resolved = (path.parent / target).resolve()
            if not resolved.is_file():
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: broken cross-link "
                    f"{target!r} → {resolved}"
                )

    if failures:
        print("Pilot-docs lint FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("Pilot-docs lint OK — every required section is filled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
