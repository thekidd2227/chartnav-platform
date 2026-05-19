#!/usr/bin/env bash
# Run canonical claim-policy fixture checks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PY_BIN="${PYTHON:-python3}"

"$PY_BIN" scripts/check_claim_policy_sync.py

"$PY_BIN" - <<'PY'
import json
import re
from pathlib import Path

root = Path.cwd()
policy = json.loads((root / "docs/commercial/claims-policy.json").read_text(encoding="utf-8"))
fixtures = root / "tests/claim_fixtures"

positive_files = [
    fixtures / "positive_overclaims_should_fail.txt",
    fixtures / "spanish_overclaims_should_fail.txt",
]
negative_files = [
    fixtures / "negative_assertions_should_pass.txt",
    fixtures / "forbidden_catalog_context_should_pass.txt",
]

patterns = [
    re.compile(entry["phrase_or_regex"], re.IGNORECASE)
    for entry in policy["entries"]
]

NEG_CTX = re.compile(
    r"(does not|do not|not |not\.|never|forbidden|banned|is not|are not|no |sin |no es|no cuenta|no realiza|no interpreta|no reemplaza|catalog)",
    re.IGNORECASE,
)
CATALOG_CTX = re.compile(r"(forbidden phrase catalog|banned|do not say|never say)", re.IGNORECASE)


def hits(path: Path) -> list[tuple[int, str]]:
    results = []
    in_catalog = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            in_catalog = bool(CATALOG_CTX.search(stripped))
            continue
        matched = any(pattern.search(line) for pattern in patterns)
        if not matched:
            continue
        if in_catalog or NEG_CTX.search(line):
            continue
        results.append((lineno, line))
    return results


def positive_misses(path: Path) -> list[tuple[int, str]]:
    misses = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not any(pattern.search(line) for pattern in patterns):
            misses.append((lineno, line))
    return misses


failures = []
for path in positive_files:
    misses = positive_misses(path)
    if misses:
        formatted = ", ".join(f"line {lineno}: {line}" for lineno, line in misses)
        failures.append(f"{path.relative_to(root)} contains overclaims that did not match policy: {formatted}")

for path in negative_files:
    file_hits = hits(path)
    if file_hits:
        formatted = ", ".join(f"line {lineno}: {line}" for lineno, line in file_hits)
        failures.append(f"{path.relative_to(root)} should pass but hit {formatted}")

if failures:
    print("FAIL - claim policy fixture checks failed.")
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(1)

print("PASS - claim policy fixtures behave as expected.")
PY
