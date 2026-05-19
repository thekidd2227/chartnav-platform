#!/usr/bin/env bash
# Alembic safety checks for release evidence.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$REPO_ROOT/apps/api"

if [ -x "$API_DIR/.venv/bin/python" ]; then
  PY_BIN="$API_DIR/.venv/bin/python"
else
  PY_BIN="${PYTHON:-python3}"
fi

echo "ChartNav Alembic safety check."
echo

cd "$API_DIR"

heads_output="$("$PY_BIN" -m alembic heads)"
head_count="$(printf '%s\n' "$heads_output" | awk 'NF { count++ } END { print count + 0 }')"
if [ "$head_count" -ne 1 ]; then
  echo "FAIL - expected exactly one Alembic head, found $head_count"
  printf '%s\n' "$heads_output"
  exit 1
fi
echo "ok - exactly one Alembic head"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
export DATABASE_URL="sqlite:///$tmpdir/alembic-safety.db"

"$PY_BIN" -m alembic current >/dev/null
echo "ok - alembic current visibility works"

"$PY_BIN" -m alembic upgrade head >/dev/null
echo "ok - alembic upgrade head succeeds against local test DB"

bad_patterns=(
  "AUTOINCREMENT"
  "datetime('now')"
  "op.execute(.*CREATE TABLE"
  "op.execute(\\s*[fr]?['\\\"]\\s*CREATE TABLE"
)

for pattern in "${bad_patterns[@]}"; do
  if rg -n "$pattern" "$API_DIR/alembic/versions" >/tmp/chartnav_alembic_pattern_hits.$$ 2>/dev/null; then
    echo "FAIL - migration contains suspicious SQLite/raw-SQL pattern: $pattern"
    cat /tmp/chartnav_alembic_pattern_hits.$$
    rm -f /tmp/chartnav_alembic_pattern_hits.$$
    exit 1
  fi
  rm -f /tmp/chartnav_alembic_pattern_hits.$$
done
echo "ok - no obvious SQLite-only/raw CREATE TABLE migration patterns found"

echo
echo "PASSED - Alembic safety checks completed."
