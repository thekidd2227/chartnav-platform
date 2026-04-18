#!/usr/bin/env bash
# Container entrypoint.
#
# Responsibilities:
#   1. Validate required env is present.
#   2. Apply Alembic migrations against DATABASE_URL.
#   3. Optionally seed (CHARTNAV_RUN_SEED=1) — safe because seed is
#      idempotent. Default off in production.
#   4. exec the CMD (uvicorn).

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required (sqlite:/// or postgresql+psycopg://)}"
: "${CHARTNAV_AUTH_MODE:=header}"

echo "==> entrypoint: DATABASE_URL=${DATABASE_URL%%@*}@(redacted)  auth_mode=${CHARTNAV_AUTH_MODE}"

echo "==> alembic upgrade head"
alembic upgrade head

if [ "${CHARTNAV_RUN_SEED:-0}" = "1" ]; then
    echo "==> seed (idempotent)"
    python scripts_seed.py
fi

echo "==> exec $*"
exec "$@"
