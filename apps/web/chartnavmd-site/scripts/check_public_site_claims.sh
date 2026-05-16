#!/usr/bin/env bash
#
# Phase 19K — public-site claims guard.
#
# Scans every static page under apps/web/chartnavmd-site/ for forbidden
# positive claims in English and Spanish. Negative / safety contexts
# (e.g. "ChartNav does not diagnose", "No automatic claims submission")
# are allowed and required — the guard distinguishes them with a
# lookbehind of negation tokens (does not / not / no / never / sin /
# no se / no es).
#
# Usage:
#   bash scripts/check_public_site_claims.sh
# Exit codes:
#   0  no forbidden positive claims found
#   1  one or more forbidden positive claims detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> public-site claims guard"
echo "    site root: $SITE_ROOT"

# Files in scope.
TARGETS=()
while IFS= read -r f; do TARGETS+=("$f"); done < <(find "$SITE_ROOT" -type f -name "*.html" \
  -not -path "*/.vercel/*" -not -path "*/node_modules/*")

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "FAIL — no static .html pages found under $SITE_ROOT"
  exit 1
fi

# English forbidden positive claims (regex, case-insensitive).
EN_FORBIDDEN=(
  "HIPAA compliant"
  "HIPAA certified"
  "HIPAA certification"
  "certified EHR"
  "autonomous diagnosis"
  "autonomous image interpretation"
  "automatic OCT interpretation"
  "auto[- ]grade DR"
  "treatment recommendation"
  "anti-VEGF dosing recommendation"
  "automatic orders"
  "automatic referrals"
  "patient messaging"
  "automatic coding"
  "automatic billing"
  "claims submission"
  "insurance payment handling"
  "EHR replacement"
  "device integration"
  "DICOM ingestion"
)

# Spanish forbidden positive claims.
ES_FORBIDDEN=(
  "cumple con HIPAA"
  "certificado HIPAA"
  "certificación HIPAA"
  "EHR certificado"
  "diagnóstico automático"
  "diagnóstico autónomo"
  "interpretación automática de imágenes"
  "interpretación autónoma de imágenes"
  "interpretación automática de OCT"
  "reemplaza su EHR"
  "reemplaza el EHR"
  "reemplaza su EMR"
  "reemplaza el EMR"
  "facturación automática"
  "codificación automática"
  "envío de reclamaciones"
  "procesamiento de seguros"
  "mensajes automáticos al paciente"
  "la nota se escribe sola"
  "la historia clínica se completa sola"
  "integración con dispositivos"
  "DICOM"
)

# Phrases that, when found within the same line as a forbidden token,
# flip the verdict from FAIL to ALLOWED (negative / safety context).
# English + Spanish negation tokens.
NEGATIONS_REGEX='\b(does not|do not|never|no\b|not\b|never|forbidden|negative|removed|does NOT|do NOT|cannot|no se|no es|no se .*|sin\b|no diagnostica|no interpreta|no coloca|no envía|no presenta|no automatiza|no reemplaza|no procesa|no requiere)\b'

fail_count=0
warn_count=0

scan_one() {
  local label="$1"; shift
  local -a phrases=("$@")
  for phrase in "${phrases[@]}"; do
    # Find any line containing the phrase, then filter out lines that
    # also contain a negation token. A surviving line is a positive
    # claim, which is forbidden.
    matches=$(grep -ErHniI -- "$phrase" "${TARGETS[@]}" 2>/dev/null || true)
    if [ -z "$matches" ]; then continue; fi
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      # Skip if the line carries a negation token.
      if echo "$line" | grep -E -i -q -- "$NEGATIONS_REGEX"; then
        continue
      fi
      # Skip if the line is inside a known safety list (data-i18n key
      # contains "non_goals" / "forbidden" / "non-goals" / "non_goal").
      if echo "$line" | grep -E -q "non_goals|non-goals|FORBIDDEN|forbidden|claim guard|safety"; then
        continue
      fi
      # Otherwise it's a positive claim — flag it.
      echo "FAIL ($label) — positive claim '$phrase':"
      echo "    $line"
      fail_count=$((fail_count+1))
    done <<< "$matches"
  done
}

scan_one "EN" "${EN_FORBIDDEN[@]}"
scan_one "ES" "${ES_FORBIDDEN[@]}"

# DICOM gets a softer treatment because the literal string appears in the
# Spanish forbidden-phrase context comment of the claims script and in
# legitimate ophthalmology-context references. The bare-token scan already
# excluded negation lines; if a positive standalone "DICOM" claim survives
# above, it's flagged.

if [ "$fail_count" -gt 0 ]; then
  echo
  echo "FAIL — $fail_count forbidden positive claim(s) found."
  exit 1
fi

echo "PASS — 0 forbidden positive claims across $(echo "${TARGETS[@]}" | wc -w | tr -d ' ') public pages."
exit 0
