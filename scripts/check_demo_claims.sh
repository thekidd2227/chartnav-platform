#!/usr/bin/env bash
# scripts/check_demo_claims.sh — Phase 24C demo claim-safety check.
#
# Why this exists:
#   Phase 24C packages the Morgan Lee retina follow-up demo for
#   repeatable sales. The Phase 17 `check_commercial_claims.sh`
#   scans buyer decks + commercial docs; the Phase 16
#   `check_website_claims.sh` scans the public landing page; the
#   Phase 24A `check_live_site_claims.sh` scans captured live HTML.
#   None of those cover `docs/demo/` (the runbook + shot list +
#   QA checklist), the Phase 24B narration script, or the
#   `scripts/reset_phase24b_retina_demo.sh` shell script that runs
#   pre-demo.
#
# What this script does:
#   1. Scans the Phase 24B + Phase 24C demo docs and the demo
#      reset script for forbidden positive-claim phrases.
#   2. Applies a permissive negative-context guard:
#      * a forbidden phrase on a line that ALSO contains a
#        negative-context marker (does not / never / banned /
#        forbidden / do not say / etc.) is skipped, AND
#      * a forbidden phrase inside a section whose heading is a
#        clear catalog marker ("What not to say", "Banned",
#        "Forbidden", "Never include", "Editorial guardrails",
#        "Buyer-safety reminders") is skipped until the next
#        markdown heading or blank-line + non-bullet line.
#   3. Exits non-zero on any positive-claim hit so pre-merge
#      gates and pre-demo runs can fail fast.
#
# What this script does NOT do:
#   - does not modify any file;
#   - does not fetch the network;
#   - does not print secrets;
#   - does not replace human review.
#
# This scanner is synchronized with the canonical policy manifest at
# docs/commercial/claims-policy.json. Run
# scripts/check_claim_policy_sync.py when adding high-risk phrases.
#
# Usage:
#   bash scripts/check_demo_claims.sh
# Exit codes:
#   0  pass (no positive-claim hits across the demo surfaces)
#   1  FAIL (at least one positive-claim hit detected)
#   2  invocation error (a required file is missing)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

FILES=(
  # Phase 24C — runbook + shot list + QA checklist.
  "docs/demo/phase-24c-retina-demo-runbook.md"
  "docs/demo/phase-24c-retina-shot-list.md"
  "docs/demo/phase-24c-demo-qa-checklist.md"
  # Phase 24B — narration script + shot list.
  "docs/demo/phase-24b-retina-workflow-demo-script.md"
  "docs/demo/phase-24b-retina-shot-list.md"
  # Phase 24C — demo reset shell script.
  "scripts/reset_phase24b_retina_demo.sh"
  # Phase 24D — pilot selection + outreach + discovery + demo
  # invite + post-demo follow-up + scorecard + objection cheat
  # sheet + tracker template + pilot README index.
  "docs/pilot/phase-24d-pilot-practice-selection-criteria.md"
  "docs/pilot/phase-24d-pilot-outreach-message-bank.md"
  "docs/pilot/phase-24d-pilot-discovery-call-script.md"
  "docs/pilot/phase-24d-demo-invite-and-agenda.md"
  "docs/pilot/phase-24d-post-demo-follow-up-template.md"
  "docs/pilot/phase-24d-pilot-fit-scorecard.md"
  "docs/pilot/phase-24d-pilot-objection-cheat-sheet.md"
  "docs/pilot/phase-24d-pilot-tracker-template.md"
  "docs/pilot/README.md"
  # Phase 57 — ambient documentation assist demo runbook.
  "docs/demo/phase-57-ambient-documentation-demo-runbook.md"
  # Phase 59 — ambient documentation demo QA lockdown checklist.
  "docs/demo/phase-59-ambient-demo-qa-checklist.md"
  # Phase 60 — structured vitals/workup demo runbook.
  "docs/demo/phase-60-vitals-workup-demo-runbook.md"
)

for f in "${FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: missing required file: $f" >&2
    exit 2
  fi
done

echo "ChartNav Phase 24C demo claim-safety check."
echo "Scanning ${#FILES[@]} demo file(s)."
echo

PY_BIN="${PYTHON:-python3}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  echo "ERROR: python3 not found on PATH" >&2
  exit 2
fi

"$PY_BIN" - "${FILES[@]}" <<'PY'
import re
import sys

# Forbidden positive-claim phrases (case-insensitive). Each entry
# is a regex fragment matched against each rendered line.
FORBIDDEN = [
    # Positioning overclaims
    r"hands[- ]free scribing",
    r"chart fills itself",
    r"chart writes itself",
    r"note fills itself",
    r"note writes itself",
    r"replaces? (your |an? )?(EHR|EMR|electronic health record|electronic medical record)",
    r"EHR replacement",
    r"EMR replacement",
    r"beats Cora",
    r"beat Cora",
    r"Cora[- ]killer",
    r"Cora replacement",
    r"alternative to Cora",
    r"better than Cora",
    r"outperforms Cora",
    r"Cora competitor",
    r"guaranteed ROI",
    r"ROI guarantee",
    r"replaces? (a |the )?doctor",
    r"replaces? (a |the )?provider",
    r"replaces? (your |a |the )?scribe",
    # Vendor / device overclaims
    r"powered by IBM",
    r"powered by watsonx",
    r"watsonx[- ]powered",
    r"IBM[- ]powered",
    # Vendor-readiness guard — IBM / watsonx may only be described
    # as "planned / vendor-dependent evaluation," never as a shipped
    # production capability. Negative phrasings stay exempt via the
    # same negative / catalog context guards used for the rest of
    # the list.
    r"IBM watsonx[- ]powered",
    r"Watson[- ]powered clinical documentation",
    r"Watson[- ]powered scribe",
    r"Watson makes ChartNav HIPAA compliant",
    r"watsonx diagnosis",
    r"watsonx[- ]driven diagnosis",
    r"watsonx image interpretation",
    r"watsonx auto[- ]grades?",
    r"IBM[- ]certified HIPAA",
    r"IBM certifies ChartNav",
    r"watsonx[- ]validated clinical accuracy",
    # LLM-vendor-evaluation guard — OpenAI / Anthropic / watsonx LLM
    # may only be described as candidate vendors under evaluation,
    # never as a shipped capability. Negative phrasings stay exempt
    # via the same negative / catalog context guards used for the
    # rest of the list. Sync phrase: OpenAI-powered clinical documentation.
    r"OpenAI[- ]powered clinical documentation",
    r"OpenAI[- ]powered scribe",
    r"GPT[- ]powered clinical documentation",
    r"GPT[- ]powered scribe",
    r"ChatGPT clinical documentation",
    r"OpenAI makes ChartNav HIPAA compliant",
    r"OpenAI diagnosis",
    r"GPT diagnosis",
    r"Anthropic[- ]powered clinical documentation",
    r"Anthropic[- ]powered scribe",
    r"Claude[- ]powered clinical documentation",
    r"Claude[- ]powered scribe",
    r"Anthropic makes ChartNav HIPAA compliant",
    r"Claude diagnosis",
    r"LLM[- ]powered diagnosis",
    r"LLM[- ]powered clinical documentation",
    r"automatic note writing",
    r"autonomous documentation",
    r"ambient scribe parity",
    r"AI writes the note",
    r"production LLM documentation",
    r"hands[- ]free scribing",
    r"OpenAI[- ]powered clinical documentation",
    r"autonomous clinical reasoning",
    r"vendor[- ]approved for PHI",
    r"BAA[- ]ready by default",
    r"vendor makes ChartNav HIPAA compliant",
    r"real device integration",
    r"DICOM ingestion",
    r"binary image storage",
    # Compliance overclaims
    r"HIPAA[- ]compliant",
    r"HIPAA[- ]certified",
    r"SOC[- ]?2[- ]?certified",
    r"FDA[- ]cleared",
    r"HITRUST[- ]certified",
    r"certified EHR",
    r"production[- ]ready for PHI",
    r"real patient data ready",
    r"real PHI ready",
    # Autonomous / automation overclaims
    r"autonomous diagnosis",
    r"autonomous interpretation",
    r"fundus image interpretation",
    r"fundus photo interpretation",
    r"retinal image interpretation",
    r"AI[- ]interprets? fundus",
    r"autonomous fundus interpretation",
    r"fundus diagnosis",
    r"AI[- ]generated fundus diagnosis",
    r"OpenAI fundus interpretation",
    r"OpenAI[- ]powered fundus charting",
    r"production LLM fundus workflow",
    r"autonomous retinal charting",
    r"AI detects retinal disease",
    r"auto[- ]interprets? OCT",
    r"auto[- ]grades? DR",
    r"auto[- ]determines? cup[- ]to[- ]disc",
    r"auto[- ]selects? IOL",
    r"auto[- ]recommends? anti[- ]VEGF",
    r"anti[- ]VEGF dosing recommendation",
    r"automatic charting",
    r"automatically charts?",
    r"automatic diagnosis",
    r"automatically diagnoses?",
    r"automatic orders",
    r"automatically orders?",
    r"automatic referrals",
    r"automatically refers?",
    r"automatic coding",
    r"automatically codes?",
    r"automatic billing",
    r"automatically bills?",
    r"billing[- ]aware coding",
    r"billing code",
    r"coding recommendations",
    r"AI vitals diagnosis",
    r"automatic vitals diagnosis",
    r"vital-sign diagnosis",
    r"treatment recommendation",
    r"automatic treatment recommendation",
    r"disease grading",
    r"OCT interpretation",
    # Patient-side overclaims
    r"patient messaging",
    r"send patient message",
    r"sends patient message",
    r"send to patient",
    r"device integration",
    r"remote patient monitoring",
    r"submits? (a )?claims?",
    r"claims? submission",
    r"insurance handling",
]

# Same-line / same-paragraph negative-context regex. Permissive on
# purpose. Matches:
#  - "does not", "do not", "is not", "are not", "must not", "not yet"
#  - "never", "no <thing>", "nor", "neither"
#  - common contractions: don't, doesn't, isn't, aren't, hasn't, etc.
#  - markdown-emphasized "not": **not**, _not_, *not*
#  - catalog markers: "forbidden", "banned", "do not use", "do not say"
#  - response framing: "safe answer", "safe phrasing", "what not to say"
#  - editorial framing: "re-record", "rewrite the draft"
NEG_CTX = re.compile(
    r"("
    r"does not|do not|never|forbidden|banned|nor|neither"
    r"|no autonomous|no automatic"
    r"|\bnot\b|\bno\b"
    r"|do[- ]not[- ]use|do[- ]not[- ]say|do[- ]not[- ]message"
    r"|don.?t\b|doesn.?t\b|didn.?t\b"
    r"|isn.?t\b|aren.?t\b|wasn.?t\b|weren.?t\b"
    r"|hasn.?t\b|haven.?t\b|hadn.?t\b"
    r"|won.?t\b|wouldn.?t\b|shouldn.?t\b|couldn.?t\b|can.?t\b|cannot"
    r"|must not|mustn.?t\b|needn.?t\b"
    r"|not approved|not pursued|not certified|not marketed|not on the roadmap"
    r"|is not|are not|re[- ]?record|rewrite"
    r"|safe answer|safe[- ]claims|safe phrasing"
    r"|narration|catalog|enumerate|enumerates"
    r"|what not to say|never say|never use|never include"
    r"|non[- ]?goal"
    r")",
    re.IGNORECASE,
)

# Markdown headings that put us in catalog mode — every forbidden
# phrase inside is treated as enumeration, not as a claim.
CATALOG_HEADING = re.compile(
    r"^#{1,6}\s+.*("
    r"what not to say"
    r"|banned"
    r"|forbidden"
    r"|never (include|use|say|claim)"
    r"|editorial guardrails"
    r"|buyer[- ]safety reminders"
    r"|claim[- ]safety"
    r"|safety sweep"
    r"|don.?t show"
    r"|do not show"
    r")",
    re.IGNORECASE,
)
# Any new heading resets catalog mode (the catalog section is
# implicitly closed by the next heading).
ANY_HEADING = re.compile(r"^#{1,6}\s+")

# Shell-script comment-block triggers: lines that are clear
# enumeration introducers carry the catalog mode into the
# following echoed lines. Used for the reset script's reminder
# block (which prints a "Forbidden: …" intro then continues).
SHELL_CATALOG_TRIGGER = re.compile(
    r"(forbidden|banned|never|do not say|don.?t say|never (include|use|claim)"
    r"|safety reminders|reminders for the presenter|safe phrasing"
    r"|safe[- ]claims|safety sweep|narration|enumerate|claim[- ]safety)",
    re.IGNORECASE,
)

FORBIDDEN_REGEX = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN]

fail_count = 0
for path in sys.argv[1:]:
    is_shell = path.endswith(".sh")
    is_markdown = path.endswith(".md")
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    # Group markdown lines into paragraphs (blocks separated by
    # blank lines) so a "does not …" on the first line covers
    # soft-wrapped continuation lines. Shell scripts are scanned
    # by groups of consecutive non-blank lines too — close enough.
    paragraphs = []  # list of (start_line_index, [lines])
    current = []
    start_idx = None
    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if line.strip() == "":
            if current:
                paragraphs.append((start_idx, current))
                current = []
                start_idx = None
            continue
        if start_idx is None:
            start_idx = idx
        current.append(line)
    if current:
        paragraphs.append((start_idx, current))

    in_catalog = False
    for start_idx, para in paragraphs:
        para_text = "\n".join(para)

        # Update catalog mode using markdown heading triggers, but
        # only based on the first line of this paragraph if it's a
        # heading (single-line paragraph).
        if is_markdown and len(para) == 1:
            first = para[0]
            if CATALOG_HEADING.search(first):
                in_catalog = True
                continue
            if ANY_HEADING.match(first):
                in_catalog = False
                continue

        # Shell catalog: any paragraph whose text mentions a clear
        # "Forbidden:" / "Banned:" / "Reminders" trigger is treated
        # as catalog-only and skipped.
        is_catalog_paragraph = (
            in_catalog
            or NEG_CTX.search(para_text) is not None
            or (is_shell and SHELL_CATALOG_TRIGGER.search(para_text) is not None)
        )

        if is_catalog_paragraph:
            continue

        for line_offset, line in enumerate(para):
            line_idx = start_idx + line_offset
            for pat in FORBIDDEN_REGEX:
                if pat.search(line):
                    snippet = line[:220]
                    print(
                        f"FAIL ({path}:{line_idx}): positive-claim pattern "
                        f"'{pat.pattern}'"
                    )
                    print(f"          {snippet}")
                    fail_count += 1

sys.exit(1 if fail_count else 0)
PY
RC=$?

echo
echo "Repo state"
echo "   sha:    $(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')"
echo "   branch: $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
echo

if [ "$RC" -ne 0 ]; then
  echo "FAILED — positive-claim hit(s) detected in demo surfaces."
  echo "Fix the offending line(s) or add an explicit negative-context"
  echo "marker (e.g. 'Banned: ' / 'Never say: ' / place under a"
  echo "catalog heading like '## What not to say')."
  exit 1
fi

echo "PASSED — 0 positive-claim hits across ${#FILES[@]} demo file(s)."
echo "Note: this script is a regex safety net, not a substitute for"
echo "human review of the demo narration before every customer call."
exit 0
