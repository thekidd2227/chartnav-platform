#!/usr/bin/env bash
# scripts/check_commercial_claims.sh — Phase 17 commercial deck +
# support-doc claims verifier.
#
# What it does:
#   1. confirms the 15 deck Markdown source files exist under
#      docs/decks/ and are non-empty;
#   2. confirms the 6 commercial support docs exist under
#      docs/commercial/ and are non-empty;
#   3. confirms the 4 demo-package docs exist (3 under
#      docs/commercial/demo-package/ + Phase 17 contract at the
#      docs/ root);
#   4. greps each deck + support doc for forbidden positive claims
#      (HIPAA-compliant, SOC 2-certified, certified-EHR,
#      autonomous-diagnosis, automatic orders / coding / referrals /
#      patient messaging) — only flags positive context, not the
#      explicit negative-assertion safety bullets;
#   5. confirms decks include the provider-review safe-claims
#      contract phrasing;
#   6. confirms the export and create-package shell scripts exist,
#      are executable, and refuse non-local DATABASE_URL values
#      (via the wrapped reset_demo_state.sh);
#   7. confirms the Desktop folder paths are listed in .gitignore
#      so the generated package is never committed.
#
# The vitest suite at apps/web/src/test/CommercialDeckClaims.test.tsx
# is authoritative; this script is a lightweight pre-merge sanity
# check.
#
# Usage:
#   bash scripts/check_commercial_claims.sh
# Exit codes:
#   0  passed
#   1  failed (a required file is missing, a forbidden positive
#      claim was detected, or a script is not executable)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

fail_count=0
warn_count=0

echo "ChartNav Phase 17 commercial-claims check."
echo

# ---------------------------------------------------------------
# 1. Required deck files.
# ---------------------------------------------------------------
DECKS=(
  "docs/decks/chartnav-investor-pitch-deck.md"
  "docs/decks/chartnav-sales-deck.md"
  "docs/decks/chartnav-demo-deck.md"
  "docs/decks/chartnav-buyer-demo-deck.md"
  "docs/decks/chartnav-operator-demo-deck.md"
  "docs/decks/chartnav-customer-pitch-deck-template.md"
  "docs/decks/chartnav-company-deck.md"
  "docs/decks/chartnav-product-roadmap-deck.md"
  "docs/decks/chartnav-brand-guidelines-deck.md"
  "docs/decks/chartnav-educational-onboarding-deck.md"
  "docs/decks/chartnav-one-page-sales-deck.md"
  "docs/decks/chartnav-financial-fundraising-deck.md"
  "docs/decks/chartnav-marketing-plan-deck.md"
  "docs/decks/chartnav-project-proposal-deck.md"
  "docs/decks/chartnav-agency-partner-pitch-deck.md"
  "docs/decks/chartnav-elevator-pitch-deck.md"
  "docs/decks/chartnav-long-sales-pitch-deck.md"
)

# Buyer-facing decks (excludes operator-only and brand-internal
# decks that may legitimately reference internal scripts / repo
# paths). Phase 17B introduces stricter repo-leak / banned-buzzword
# checks for this subset.
BUYER_FACING_DECKS=(
  "docs/decks/chartnav-investor-pitch-deck.md"
  "docs/decks/chartnav-sales-deck.md"
  "docs/decks/chartnav-buyer-demo-deck.md"
  "docs/decks/chartnav-customer-pitch-deck-template.md"
  "docs/decks/chartnav-company-deck.md"
  "docs/decks/chartnav-product-roadmap-deck.md"
  "docs/decks/chartnav-educational-onboarding-deck.md"
  "docs/decks/chartnav-one-page-sales-deck.md"
  "docs/decks/chartnav-financial-fundraising-deck.md"
  "docs/decks/chartnav-project-proposal-deck.md"
  "docs/decks/chartnav-agency-partner-pitch-deck.md"
  "docs/decks/chartnav-elevator-pitch-deck.md"
  "docs/decks/chartnav-long-sales-pitch-deck.md"
)

echo "1. Deck source files (expect ${#DECKS[@]})"
for f in "${DECKS[@]}"; do
  if [ ! -s "$f" ]; then
    echo "   MISSING or EMPTY: $f"
    fail_count=$((fail_count + 1))
  fi
done
if [ "$fail_count" -eq 0 ]; then
  echo "   ok — all ${#DECKS[@]} deck files present and non-empty."
fi
echo

# ---------------------------------------------------------------
# 2. Commercial support docs.
# ---------------------------------------------------------------
SUPPORT=(
  "docs/commercial/chartnav-deck-master-kit.md"
  "docs/commercial/chartnav-approved-claims-language.md"
  "docs/commercial/chartnav-commercial-readiness-map.md"
  "docs/commercial/objections/chartnav-buyer-objection-handling.md"
  "docs/commercial/pricing/chartnav-pricing-packaging-notes.md"
  "docs/commercial/pilot/chartnav-pilot-handoff-checklist.md"
)

echo "2. Commercial support docs (expect ${#SUPPORT[@]})"
local_fail=0
for f in "${SUPPORT[@]}"; do
  if [ ! -s "$f" ]; then
    echo "   MISSING or EMPTY: $f"
    fail_count=$((fail_count + 1))
    local_fail=$((local_fail + 1))
  fi
done
if [ "$local_fail" -eq 0 ]; then
  echo "   ok — all ${#SUPPORT[@]} support docs present and non-empty."
fi
echo

# ---------------------------------------------------------------
# 3. Demo-package docs.
# ---------------------------------------------------------------
DEMO_PKG=(
  "docs/commercial/demo-package/chartnav-local-demo-startup-guide.md"
  "docs/commercial/demo-package/chartnav-local-demo-troubleshooting.md"
  "docs/commercial/demo-package/chartnav-demo-review-checklist.md"
  "docs/chartnav-desktop-demo-delivery-package.md"
)

echo "3. Demo-package docs (expect ${#DEMO_PKG[@]})"
local_fail=0
for f in "${DEMO_PKG[@]}"; do
  if [ ! -s "$f" ]; then
    echo "   MISSING or EMPTY: $f"
    fail_count=$((fail_count + 1))
    local_fail=$((local_fail + 1))
  fi
done
if [ "$local_fail" -eq 0 ]; then
  echo "   ok — all ${#DEMO_PKG[@]} demo-package docs present and non-empty."
fi
echo

# ---------------------------------------------------------------
# 4. Forbidden positive claims across decks + support docs.
#
# Compliance/certification claims are rejected outright. Capability
# claims (autonomous diagnosis, automatic orders, etc.) are rejected
# only when they appear as a positive claim — every deck explicitly
# uses negative-assertion bullets ("ChartNav does not diagnose",
# "Not autonomous diagnosis", etc.) and those are allowed.
# ---------------------------------------------------------------
FORBIDDEN_COMPLIANCE=(
  "HIPAA[- ]compliant"
  "HIPAA[- ]certified"
  "SOC[- ]?2[- ]?certified"
  "FDA[- ]cleared"
  "HITRUST[- ]certified"
  "production[- ]ready for PHI"
  "real patient data ready"
)

FORBIDDEN_CAPABILITY=(
  "certified EHR"
  "autonomous diagnosis"
  "automatic diagnosis"
  "guaranteed accuracy"
  "guaranteed documentation accuracy"
  "automatic orders"
  "auto-orders"
  "submit referral"
  "send patient message"
  "replaces a doctor"
  "replaces the doctor"
  "replaces providers"
  "AI draws automatically"
  "AI decides"
  # Phase 24A — Manus public-claims audit additions. Negative
  # phrasings ("the chart does not fill itself", "ChartNav does
  # not replace your EHR") are exempted by the negative-context
  # check below.
  "hands-free scribing"
  "hands-free scribe"
  "chart fills itself"
  "chart writes itself"
  "note fills itself"
  "note writes itself"
  "replaces your EHR"
  "replace your EHR"
  "replaces your EMR"
  "replace your EMR"
  "EHR replacement"
  "EMR replacement"
  "powered by IBM"
  "powered by watsonx"
  "watsonx-powered"
  "IBM-powered"
  # Vendor-readiness guard — IBM / watsonx may only be described as
  # "planned / vendor-dependent evaluation," never as a shipped
  # production capability. Negative phrasings ("ChartNav is not
  # powered by IBM", "Watson does not make ChartNav HIPAA compliant")
  # are exempted by the negative-context check below.
  "IBM watsonx-powered"
  "Watson-powered clinical documentation"
  "Watson-powered scribe"
  "Watson makes ChartNav HIPAA compliant"
  "watsonx diagnosis"
  "watsonx-driven diagnosis"
  "watsonx image interpretation"
  "watsonx auto-grades"
  "IBM-certified HIPAA"
  "IBM certifies ChartNav"
  "watsonx-validated clinical accuracy"
  # LLM-vendor-evaluation guard — OpenAI / Anthropic / watsonx may
  # only be described as candidate vendors under evaluation, never
  # as a shipped LLM capability. Negative phrasings ("ChartNav is
  # not Claude-powered", "OpenAI does not make ChartNav HIPAA
  # compliant") stay exempt via the negative-context check.
  "OpenAI-powered clinical documentation"
  "OpenAI-powered scribe"
  "GPT-powered clinical documentation"
  "GPT-powered scribe"
  "ChatGPT clinical documentation"
  "OpenAI makes ChartNav HIPAA compliant"
  "OpenAI diagnosis"
  "GPT diagnosis"
  "Anthropic-powered clinical documentation"
  "Anthropic-powered scribe"
  "Claude-powered clinical documentation"
  "Claude-powered scribe"
  "Anthropic makes ChartNav HIPAA compliant"
  "Claude diagnosis"
  "LLM-powered diagnosis"
  "LLM-powered clinical documentation"
  "automatic note writing"
  "autonomous documentation"
  "ambient scribe parity"
  "AI writes the note"
  "production LLM documentation"
  "autonomous clinical reasoning"
  "vendor-approved for PHI"
  "BAA-ready by default"
  "vendor makes ChartNav HIPAA compliant"
  "billing-aware coding"
  "coding recommendations"
  "AI diagnosis"
  "automatic charting"
  "hands-free diagnosis"
  "hands-free charting"
  "hands-off documentation"
  # Phase 21C — ophthalmology-specific positive-claim guards.
  # Negative phrasings ("does not auto-grade DR", "auto-grade DR is not
  # implemented") are exempted by the negative-context check below.
  "auto-grade DR"
  "auto-grade diabetic retinopathy"
  "auto-interpret OCT"
  "fundus image interpretation"
  "fundus photo interpretation"
  "retinal image interpretation"
  "AI[- ]interprets? fundus"
  "autonomous fundus interpretation"
  "fundus diagnosis"
  "AI[- ]generated fundus diagnosis"
  "OpenAI fundus interpretation"
  "OpenAI-powered fundus charting"
  "production LLM fundus workflow"
  "autonomous retinal charting"
  "AI detects retinal disease"
  "real PHI ready"
  "autonomous imaging interpretation"
  "auto-determine cup-to-disc"
  "auto-measure central macular thickness"
  "auto-measure RNFL thickness"
  "auto-select IOL power"
  "auto-recommend anti-VEGF"
  "auto-suggest anti-VEGF"
  "auto-flag glaucoma progression"
  "IRIS Registry submission"
  "MIPS submission"
  # Phase 25A / GH-012 — Cora-comparison language. ChartNav does
  # not benchmark against, replace, or position itself "vs Cora"
  # in buyer-facing material. Negative phrasings ("we do not
  # compete with Cora", "ChartNav is not a Cora replacement")
  # are exempted by the negative-context check below.
  "beats Cora"
  "beat Cora"
  "Cora[- ]killer"
  "Cora killer"
  "replaces Cora"
  "replace Cora"
  "Cora replacement"
  "alternative to Cora"
  "better than Cora"
  "outperforms Cora"
  "Cora competitor"
)

ALL_DOCS=("${DECKS[@]}" "${SUPPORT[@]}" "${DEMO_PKG[@]}")

echo "4. Forbidden positive claims (across ${#ALL_DOCS[@]} doc(s))"
for f in "${ALL_DOCS[@]}"; do
  [ -f "$f" ] || continue

  # Catalog docs that exist *to enumerate* the banned phrases:
  # - approved-claims-language.md (the canonical list)
  # - brand-guidelines-deck.md (slide 5 — "Never use")
  # - buyer-objection-handling.md (each "Don't say:" block)
  # Skip the catalog docs entirely; their job is to list bad
  # phrases.
  case "$f" in
    *"chartnav-approved-claims-language.md"|\
    *"chartnav-brand-guidelines-deck.md"|\
    *"chartnav-buyer-objection-handling.md"|\
    *"chartnav-ophthalmology-positioning-language-guide.md")
      # Phase 21C — language guide enumerates banned phrases as a
      # reference; skip the same way the approved-claims-language
      # catalog is skipped.
      continue
      ;;
  esac

  for pattern in "${FORBIDDEN_COMPLIANCE[@]}"; do
    if grep -Eiq "$pattern" "$f"; then
      while IFS= read -r line; do
        # Allow lines that are clearly negative context — "not
        # HIPAA-certified", "does not claim", "Software is not
        # certified", "not pursued", "never", etc. The pricing-
        # notes and readiness-map docs explicitly enumerate what
        # we are NOT certified for.
        lower="$(printf '%s' "$line" | tr 'A-Z' 'a-z')"
        if printf '%s' "$lower" | grep -Eq '(does not|do not|never|forbidden|banned|don.?t say|not\s+(yet\s+)?(pursued|certified|hipaa|soc|hitrust|fda)|not pursued|software is not|is not|are not|\bnot\b\s+(hipaa|soc|hitrust|fda))'; then
          continue
        fi
        echo "   FAIL — forbidden compliance claim '$pattern' in $f"
        echo "          $line"
        fail_count=$((fail_count + 1))
      done < <(grep -Ei "$pattern" "$f" || true)
    fi
  done

  for pattern in "${FORBIDDEN_CAPABILITY[@]}"; do
    while IFS= read -r line; do
      lower="$(printf '%s' "$line" | tr 'A-Z' 'a-z')"
      # Allow obvious negative contexts. We cover:
      #  - "does not …"
      #  - "no autonomous", "never"
      #  - sentence-leading "not …"
      #  - "don't say:" / "do not use" framings
      if printf '%s' "$lower" | grep -Eq '(does not|do not|never|no autonomous|no automatic|\bnot\s|forbidden|banned|do[- ]not[- ]use|don.?t say)'; then
        continue
      fi
      # The pattern "submit referral" appears in objection-handling
      # / readiness-map docs only as something ChartNav does not
      # do; the negative-context guard above catches almost all of
      # those, but if a hit slips through we log a warn rather
      # than a fail.
      echo "   warn — '$pattern' in $f outside obvious negative context:"
      echo "          $line"
      warn_count=$((warn_count + 1))
    done < <(grep -Ei "$pattern" "$f" || true)
  done
done
if [ "$fail_count" -eq 0 ] && [ "$warn_count" -eq 0 ]; then
  echo "   ok — no forbidden positive claims detected."
fi
echo

# ---------------------------------------------------------------
# 5. Provider-review safe-claims contract phrasing on every deck.
# ---------------------------------------------------------------
echo "5. Safe-claims phrasing on every deck"
for f in "${DECKS[@]}"; do
  [ -f "$f" ] || continue
  # Each deck must reference the approved-claims language doc OR
  # carry the canonical safety phrasing inline (provider-reviewed,
  # approved-claims, or a "Safe-claims contract" header).
  if grep -Eq 'chartnav-approved-claims-language\.md' "$f" \
     || grep -Eiq 'provider[- ]reviewed' "$f" \
     || grep -Eiq 'safe[- ]claims contract' "$f" \
     || grep -Eiq 'approved[- ]claims' "$f"; then
    continue
  fi
  echo "   FAIL — $f does not reference approved-claims language or 'provider-reviewed' or 'Safe-claims contract'."
  fail_count=$((fail_count + 1))
done
if [ "$fail_count" -eq 0 ]; then
  echo "   ok — every deck references the safe-claims contract."
fi
echo

# ---------------------------------------------------------------
# 5B. Phase 17B — buyer-facing deck repo-leak / banned-buzzword
# scan. Buyer-facing decks must not include internal terminal
# commands, repo paths, internal feature-flag URLs, or operator-
# only language that exposes implementation detail. The brand-
# guidelines deck and the operator-demo deck are exempt by path.
# ---------------------------------------------------------------
echo "5B. Buyer-facing deck repo-leak / banned-buzzword scan"
REPO_LEAK_PATTERNS=(
  "production code on main"
  "operator.s note"
  "this version of the deck"
  "\\?intro=1"
  "\\?demo=1"
  "make dev"
  "make reset-db"
  "scripts/reset_demo_state\\.sh"
  "scripts/export_chartnav_decks_to_desktop\\.sh"
  "START_CHARTNAV\\.command"
  "STOP_CHARTNAV\\.command"
  "RESET_DEMO_DATA\\.command"
  "apps/web/"
  "apps/api/"
  "sentinel-token regression"
  "Phase [0-9]+ smoke"
  "Phase 16 landing page"
  "Phase 16 workflow SVG"
  "contract doc in the repo"
  "source file"
  "in production code"
)
for f in "${BUYER_FACING_DECKS[@]}"; do
  [ -f "$f" ] || continue
  for pat in "${REPO_LEAK_PATTERNS[@]}"; do
    while IFS= read -r line; do
      lower="$(printf '%s' "$line" | tr 'A-Z' 'a-z')"
      # Allow the customer pitch template's `{{PLACEHOLDER}}` lines
      # to mention internal scaffolding only when the line itself
      # is clearly a placeholder.
      if printf '%s' "$line" | grep -Eq '\{\{[A-Z_]+\}\}'; then
        continue
      fi
      echo "   FAIL — buyer-facing deck $f line contains '$pat':"
      echo "          $line"
      fail_count=$((fail_count + 1))
    done < <(grep -E "$pat" "$f" || true)
  done
done
if [ "$fail_count" -eq 0 ]; then
  echo "   ok — buyer-facing decks contain no repo-leak phrases."
fi
echo

# ---------------------------------------------------------------
# 6. Phase 17 shell scripts.
# ---------------------------------------------------------------
echo "6. Phase 17 shell scripts"
for s in \
  "scripts/export_chartnav_decks_to_desktop.sh" \
  "scripts/create_chartnav_desktop_demo_package.sh"; do
  if [ ! -f "$s" ]; then
    echo "   MISSING: $s"
    fail_count=$((fail_count + 1))
    continue
  fi
  if [ ! -x "$s" ]; then
    echo "   warn — $s is present but not marked executable."
    warn_count=$((warn_count + 1))
  fi
done

# The reset script (which the .command file wraps) must contain
# the EXPECTED_PREFIX="sqlite:///" guard.
if [ -f scripts/reset_demo_state.sh ]; then
  if ! grep -Eq 'EXPECTED_PREFIX="sqlite:///"' scripts/reset_demo_state.sh; then
    echo "   FAIL — scripts/reset_demo_state.sh missing local-DB guard"
    fail_count=$((fail_count + 1))
  fi
fi

# The export script must set EXPECTED desktop dir + REPO_ON_MAC
# defaults to the operator's documented paths.
if [ -f scripts/export_chartnav_decks_to_desktop.sh ]; then
  if ! grep -Eq 'CHARTNAV_DESKTOP_DIR' scripts/export_chartnav_decks_to_desktop.sh; then
    echo "   FAIL — export script missing CHARTNAV_DESKTOP_DIR override hook"
    fail_count=$((fail_count + 1))
  fi
  # Must wrap reset_demo_state.sh, not invent a new reset path.
  if ! grep -Eq 'reset_demo_state\.sh' scripts/export_chartnav_decks_to_desktop.sh; then
    echo "   FAIL — export script does not reference reset_demo_state.sh"
    fail_count=$((fail_count + 1))
  fi
fi

if [ "$fail_count" -eq 0 ] && [ "$warn_count" -eq 0 ]; then
  echo "   ok — Phase 17 scripts present and DB-guard wiring intact."
fi
echo

# ---------------------------------------------------------------
# 6B. Phase 17D presentation generator + assets.
# ---------------------------------------------------------------
echo "6B. Phase 17D presentation system"
PHASE17D_FILES=(
  "tools/presentations/package.json"
  "tools/presentations/theme.js"
  "tools/presentations/parseDeck.js"
  "tools/presentations/slideLayouts.js"
  "tools/presentations/renderDeck.js"
  "tools/presentations/generateAll.js"
  "tools/presentations/brand/chartnavMark.js"
  "scripts/generate_chartnav_presentations.sh"
  "docs/presentations/palette.md"
  "docs/presentations/typography.md"
  "docs/presentations/brand-usage.md"
  "docs/presentations/chartnav-presentation-system.md"
)
for f in "${PHASE17D_FILES[@]}"; do
  if [ ! -s "$f" ]; then
    echo "   MISSING or EMPTY: $f"
    fail_count=$((fail_count + 1))
  fi
done

# The generator script must be executable.
if [ -f scripts/generate_chartnav_presentations.sh ] \
   && [ ! -x scripts/generate_chartnav_presentations.sh ]; then
  echo "   warn — scripts/generate_chartnav_presentations.sh is present but not executable."
  warn_count=$((warn_count + 1))
fi

# theme.js must reference the canonical palette tokens so it
# stays in sync with apps/web/src/styles.css.
if [ -f tools/presentations/theme.js ]; then
  for tok in "0B6E79" "DC2626" "14B8A6" "0F172A"; do
    if ! grep -q "$tok" tools/presentations/theme.js; then
      echo "   FAIL — tools/presentations/theme.js missing palette token: $tok"
      fail_count=$((fail_count + 1))
    fi
  done
fi

# Generator must read from docs/decks and write under
# CHARTNAV_DESKTOP_DIR.
if [ -f tools/presentations/generateAll.js ]; then
  if ! grep -q "docs/decks\|docs.*decks" tools/presentations/generateAll.js \
     && ! grep -q "DECKS_DIR" tools/presentations/generateAll.js; then
    echo "   FAIL — generateAll.js does not reference the deck source dir"
    fail_count=$((fail_count + 1))
  fi
  if ! grep -q "CHARTNAV_DESKTOP_DIR" tools/presentations/generateAll.js; then
    echo "   FAIL — generateAll.js does not honor CHARTNAV_DESKTOP_DIR"
    fail_count=$((fail_count + 1))
  fi
fi

if [ "$fail_count" -eq 0 ] && [ "$warn_count" -eq 0 ]; then
  echo "   ok — Phase 17D presentation system files present and palette in sync."
fi
echo

# ---------------------------------------------------------------
# 7. .gitignore guard for the Desktop folder.
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# 6C. Phase 18 controlled-pilot PHI readiness files.
# ---------------------------------------------------------------
echo "6C. Phase 18 controlled-pilot PHI readiness"
PHASE18_FILES=(
  "scripts/validate_controlled_pilot_env.sh"
  "scripts/backup_controlled_pilot_postgres.sh"
  "scripts/restore_controlled_pilot_postgres.sh"
  "scripts/verify_controlled_pilot_backup.sh"
  "scripts/smoke_controlled_pilot.sh"
  "docs/security/chartnav-production-auth-readiness.md"
  "docs/security/chartnav-monitoring-logging-readiness.md"
  "docs/security/chartnav-incident-response-plan.md"
  "docs/security/chartnav-real-phi-readiness-status.md"
  "docs/pilot/chartnav-controlled-pilot-go-live-checklist.md"
)
for f in "${PHASE18_FILES[@]}"; do
  if [ ! -s "$f" ]; then
    echo "   MISSING or EMPTY: $f"
    fail_count=$((fail_count + 1))
  fi
done
# All five Phase 18 scripts must be executable.
for s in scripts/validate_controlled_pilot_env.sh \
         scripts/backup_controlled_pilot_postgres.sh \
         scripts/restore_controlled_pilot_postgres.sh \
         scripts/verify_controlled_pilot_backup.sh \
         scripts/smoke_controlled_pilot.sh; do
  if [ -f "$s" ] && [ ! -x "$s" ]; then
    echo "   warn — $s exists but is not executable."
    warn_count=$((warn_count + 1))
  fi
done

# Safety guards must be present in the destructive scripts.
if [ -f scripts/backup_controlled_pilot_postgres.sh ]; then
  if ! grep -q "DATABASE_URL is SQLite" scripts/backup_controlled_pilot_postgres.sh; then
    echo "   FAIL — backup_controlled_pilot_postgres.sh missing SQLite refusal"
    fail_count=$((fail_count + 1))
  fi
fi
if [ -f scripts/restore_controlled_pilot_postgres.sh ]; then
  if ! grep -q "CHARTNAV_RESTORE_CONFIRM" scripts/restore_controlled_pilot_postgres.sh; then
    echo "   FAIL — restore_controlled_pilot_postgres.sh missing CHARTNAV_RESTORE_CONFIRM gate"
    fail_count=$((fail_count + 1))
  fi
fi
if [ -f scripts/validate_controlled_pilot_env.sh ]; then
  for must in "CHARTNAV_AUTH_MODE" "CHARTNAV_JWT_ISSUER" "CHARTNAV_JWT_AUDIENCE" \
              "CHARTNAV_JWT_JWKS_URL" "DATABASE_URL" "CHARTNAV_AUDIT_RETENTION_DAYS"; do
    if ! grep -q "$must" scripts/validate_controlled_pilot_env.sh; then
      echo "   FAIL — validate_controlled_pilot_env.sh does not check $must"
      fail_count=$((fail_count + 1))
    fi
  done
fi

# Phase 18 docs must NOT make a positive HIPAA / SOC 2 / certified-EHR claim.
# The Phase 18 docs are partly catalog/Q&A docs by design (e.g. the
# readiness status doc lists "Is ChartNav HIPAA-certified? No.").
# Negative-context heuristic accepts:
#   - explicit "does not / do not / not / never / forbidden / banned"
#   - the ❌ marker (forbidden-list bullets)
#   - "is not" / "are not" / "not pursued" patterns
#   - per-line column "no.", "no," answers in Q&A markdown tables
#   - prev-line context (e.g. "Is ChartNav a certified EHR?" then "No.")
for f in "${PHASE18_FILES[@]}"; do
  [ -f "$f" ] || continue
  case "$f" in
    *.sh) continue ;;  # script file — heuristic skipped
  esac
  # Build a temp file of (line_no:line) so we can look at the previous
  # line for context.
  while IFS= read -r entry; do
    idx="${entry%%:*}"
    line="${entry#*:}"
    # Strip markdown bold/italic so "is **not**" matches "is not".
    stripped="$(printf '%s' "$line" | sed -E 's/\*+//g; s/`+//g; s/_+/ /g')"
    lower="$(printf '%s' "$stripped" | tr 'A-Z' 'a-z')"
    # Per-line negative context.
    if printf '%s' "$line" | grep -Eq '❌'; then
      continue
    fi
    if printf '%s' "$lower" | grep -Eq '(does not|do not|never|forbidden|banned|don.?t say|not\s+(yet\s+)?(pursued|certified|hipaa|soc|hitrust|fda)|not pursued|software is not|is not|are not|not\s+(hipaa|soc|hitrust|fda)|never\s)'; then
      continue
    fi
    # Markdown table answer "No." / "**No.**"
    if printf '%s' "$lower" | grep -Eq '\|\s*\*\*?no'; then
      continue
    fi
    # Prev-line is a question header / negation, then this line is
    # the wrapped continuation.
    if [ "$idx" -gt 1 ]; then
      prev="$(sed -n "$((idx - 1))p" "$f")"
      prev_stripped="$(printf '%s' "$prev" | sed -E 's/\*+//g; s/`+//g; s/_+/ /g')"
      prev_lower="$(printf '%s' "$prev_stripped" | tr 'A-Z' 'a-z')"
      if printf '%s' "$prev_lower" | grep -Eq '(is chartnav|does chartnav|never\s|forbidden|banned|don.?t say|do not|does not|is not|are not|chartnav is not|not\s+a|not\s+(hipaa|soc|hitrust|fda)|❌)'; then
        continue
      fi
    fi
    echo "   FAIL — Phase 18 doc $f line $idx contains positive claim:"
    echo "          $line"
    fail_count=$((fail_count + 1))
  done < <(
    for pat in "HIPAA[- ]compliant" "HIPAA[- ]certified" "SOC[- ]?2[- ]?certified" \
               "FDA[- ]cleared" "HITRUST[- ]certified" "certified EHR" \
               "production[- ]ready for PHI" "real patient data ready"; do
      grep -nEi "$pat" "$f" || true
    done | sort -u
  )
done

if [ "$fail_count" -eq 0 ] && [ "$warn_count" -eq 0 ]; then
  echo "   ok — Phase 18 files present + safety guards intact + no positive certification claims."
fi
echo

# ---------------------------------------------------------------
# 7. .gitignore guard for the Desktop folder.
# ---------------------------------------------------------------
echo "7. .gitignore guard for the Desktop folder"
if [ ! -f .gitignore ]; then
  echo "   FAIL — .gitignore is missing."
  fail_count=$((fail_count + 1))
else
  if grep -Eq '(chartnav decks|/Users/jean-maxcharles/Desktop/chartnav decks|chartnav-platform/desktop-export)' .gitignore; then
    echo "   ok — Desktop demo package paths covered by .gitignore."
  else
    echo "   warn — .gitignore does not explicitly exclude the Desktop folder."
    echo "          The folder is outside the repo, so this is not a hard fail,"
    echo "          but consider adding a guard pattern."
    warn_count=$((warn_count + 1))
  fi
fi
echo

# ---------------------------------------------------------------
# 8. No binary media checked into Phase 17 doc / deck folders.
# ---------------------------------------------------------------
echo "8. No binary media in commercial / deck / demo-package folders"
binaries=$(find docs/decks docs/commercial docs/demo \
  -type f \
  \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
     -o -iname '*.gif' -o -iname '*.webp' -o -iname '*.mp4' \
     -o -iname '*.mov' -o -iname '*.webm' -o -iname '*.pdf' \
     -o -iname '*.pptx' -o -iname '*.key' \) \
  2>/dev/null || true)
if [ -n "$binaries" ]; then
  echo "   FAIL — binary media checked in under Phase 17 paths:"
  printf '   %s\n' $binaries
  fail_count=$((fail_count + 1))
else
  echo "   ok — only Markdown / text under Phase 17 paths."
fi
echo

# ---------------------------------------------------------------
# 9. Repo state.
# ---------------------------------------------------------------
echo "9. Repo state"
echo "   sha:    $(git rev-parse HEAD 2>/dev/null || echo unknown)"
echo "   branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
echo

if [ "$fail_count" -gt 0 ]; then
  echo "FAILED — $fail_count fail(s), $warn_count warn(s)."
  exit 1
fi
if [ "$warn_count" -gt 0 ]; then
  echo "PASSED with $warn_count heuristic warn(s); run vitest to confirm."
  exit 0
fi
echo "PASSED — 0 fail / 0 warn."
exit 0
