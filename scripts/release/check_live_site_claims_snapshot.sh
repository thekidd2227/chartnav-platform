#!/usr/bin/env bash
# scripts/release/check_live_site_claims_snapshot.sh — Phase 88
# operator-driven live-site claims snapshot scanner.
#
# WHY THIS EXISTS
#   The independent Manus audit observed that ChartNav's repo passes
#   every claims-check while the live `chartnavmd.com` deployment is
#   not directly governed by repo CI. The existing
#   `scripts/check_live_site_claims.sh` requires the operator to
#   pre-capture the HTML out-of-band. This wrapper captures the HTML
#   safely (in a temp dir, no secrets, no auth), records the SHA-256
#   of the capture into a dated artifact, and runs the existing
#   scanner against it.
#
# WHAT IT DOES
#   1. Fetches the supplied URL(s) with `curl -sL` into a dated
#      snapshot directory under `artifacts/live-site-snapshots/`.
#   2. Records SHA-256 + Content-Length for each captured page.
#   3. Runs `scripts/check_live_site_claims.sh` against the snapshot
#      directory.
#   4. Writes a summary file with PASS/FAIL + the next recovery step.
#
# WHAT IT DOES NOT DO
#   - It does NOT modify the live site.
#   - It does NOT use credentials.
#   - It does NOT post anywhere.
#   - It does NOT publish.
#   - It does NOT bypass the claim scanner — it only feeds it.
#   - It does NOT make CI flaky; it is operator-run by default.
#
# USAGE
#   bash scripts/release/check_live_site_claims_snapshot.sh
#       (defaults to https://chartnavmd.com/)
#   bash scripts/release/check_live_site_claims_snapshot.sh \
#       https://chartnavmd.com/ https://chartnavmd.com/clinical
#
# OUTPUT
#   artifacts/live-site-snapshots/YYYYMMDD-HHMMSS/
#     ├── manifest.txt        sha256 + size + url per page
#     ├── summary.txt         scanner PASS/FAIL summary
#     ├── *.html              captured pages
#
# OPTIONAL ENV
#   CHARTNAV_LIVE_USER_AGENT  curl User-Agent override.
#                              Defaults to a chartnav-audit string.
#   CHARTNAV_LIVE_TIMEOUT     curl --max-time (seconds). Default 30.
#
# Recommended operator cadence: pre-publish + weekly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if ! command -v curl >/dev/null 2>&1; then
  echo "[live-site-snapshot] curl not found; install curl and retry." >&2
  exit 64
fi

DEFAULT_URLS=(
  "https://chartnavmd.com/"
)

URLS=("$@")
if [[ "${#URLS[@]}" -eq 0 ]]; then
  URLS=("${DEFAULT_URLS[@]}")
fi

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT_DIR="$REPO_ROOT/artifacts/live-site-snapshots/$TIMESTAMP"
mkdir -p "$OUT_DIR"

USER_AGENT="${CHARTNAV_LIVE_USER_AGENT:-chartnav-live-site-audit/1.0 (+repo)}"
TIMEOUT_SECONDS="${CHARTNAV_LIVE_TIMEOUT:-30}"

MANIFEST="$OUT_DIR/manifest.txt"
{
  echo "ChartNav live-site claims snapshot"
  echo "captured_at: ${TIMESTAMP}"
  echo "host: $(hostname)"
  echo "operator: ${USER:-unknown}"
  echo "user_agent: ${USER_AGENT}"
  echo "timeout_seconds: ${TIMEOUT_SECONDS}"
  echo "urls:"
  for u in "${URLS[@]}"; do
    echo "  - $u"
  done
  echo
  echo "files:"
} > "$MANIFEST"

idx=0
for url in "${URLS[@]}"; do
  idx=$((idx + 1))
  # Build a safe filename from the URL.
  slug="$(echo "$url" | tr '/:?&=' '_____' | tr -cd 'A-Za-z0-9_.-' | head -c 100)"
  outfile="$OUT_DIR/page${idx}-${slug}.html"

  echo "[live-site-snapshot] GET  $url"
  if ! curl -sSL \
      --max-time "$TIMEOUT_SECONDS" \
      --user-agent "$USER_AGENT" \
      --fail \
      -o "$outfile" \
      "$url"; then
    echo "[live-site-snapshot] FAIL fetch: $url" >&2
    echo "  - $(basename "$outfile")  FETCH_FAILED  $url" >> "$MANIFEST"
    rm -f "$outfile"
    {
      echo "STATUS: FAIL"
      echo "REASON: fetch_failed for $url"
      echo "RECOVERY: re-run script after network connectivity is restored,"
      echo "          or capture the page manually and place it under $OUT_DIR/"
    } > "$OUT_DIR/summary.txt"
    exit 65
  fi

  sha="$(sha256sum "$outfile" | awk '{print $1}')"
  size="$(stat -c '%s' "$outfile" 2>/dev/null || wc -c <"$outfile")"
  echo "  - $(basename "$outfile")  sha256:${sha}  size:${size}  url:${url}" >> "$MANIFEST"
done

echo
echo "[live-site-snapshot] snapshot: $OUT_DIR"
echo "[live-site-snapshot] running claim scanner..."
echo

scanner_status=0
if ! bash "$REPO_ROOT/scripts/check_live_site_claims.sh" "$OUT_DIR" \
    > "$OUT_DIR/scanner.log" 2>&1; then
  scanner_status=$?
fi

cat "$OUT_DIR/scanner.log"

{
  echo "captured_at: ${TIMESTAMP}"
  echo "snapshot_dir: ${OUT_DIR}"
  if [[ $scanner_status -eq 0 ]]; then
    echo "STATUS: PASS"
    echo "RESULT: no forbidden positive claims found across ${#URLS[@]} captured page(s)."
  else
    echo "STATUS: FAIL"
    echo "RESULT: scanner exited ${scanner_status}; see scanner.log."
    echo "RECOVERY: open the captured HTML, locate the flagged phrase, request a copy edit on the"
    echo "          live site, re-capture, and re-run this script. Do NOT publish until PASS."
  fi
} > "$OUT_DIR/summary.txt"

if [[ $scanner_status -ne 0 ]]; then
  echo
  echo "[live-site-snapshot] FAIL  see $OUT_DIR/summary.txt" >&2
  exit "$scanner_status"
fi

echo
echo "[live-site-snapshot] PASS  see $OUT_DIR/summary.txt"
