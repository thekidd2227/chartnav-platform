#!/usr/bin/env bash
# Container entrypoint with explicit subcommands so DB migration is a SEPARATE
# step from steady-state serving (the production deploy pipeline runs a one-off
# `migrate` task, then rolls the `serve` service — migrations never run on every
# API task start).
#
#   entrypoint.sh migrate    — apply Alembic migrations, then exit.
#   entrypoint.sh serve      — run the API (uvicorn, no reload). No migrations.
#   entrypoint.sh seed       — idempotent demo seed (non-production only).
#   entrypoint.sh <other...> — exec it (back-compat / debugging).
#
# Back-compat: with NO subcommand, behaves like the old image (migrate + seed
# if CHARTNAV_RUN_SEED=1 + uvicorn) so existing dev/compose keep working.

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required (sqlite:/// or postgresql+psycopg://)}"
: "${CHARTNAV_ENV:=dev}"
: "${CHARTNAV_AUTH_MODE:=header}"
: "${API_HOST:=0.0.0.0}"
: "${API_PORT:=8000}"
: "${WEB_CONCURRENCY:=2}"

redacted_db="${DATABASE_URL%%@*}@(redacted)"

run_migrate() {
  echo "==> alembic upgrade head  (db=${redacted_db})"
  alembic upgrade head
}

run_seed() {
  if [ "${CHARTNAV_ENV}" = "prod" ]; then
    echo "==> refusing to seed in production"; exit 1
  fi
  echo "==> seed (idempotent)"
  python scripts_seed.py
}

run_serve() {
  echo "==> serve  env=${CHARTNAV_ENV} auth=${CHARTNAV_AUTH_MODE} workers=${WEB_CONCURRENCY}"
  # No --reload in any container. Graceful shutdown via uvicorn's SIGTERM handling.
  exec uvicorn app.main:app \
    --host "${API_HOST}" --port "${API_PORT}" \
    --workers "${WEB_CONCURRENCY}" \
    --timeout-graceful-shutdown 25 \
    --no-server-header
}

cmd="${1:-}"
case "${cmd}" in
  migrate) run_migrate ;;
  seed)    run_seed ;;
  serve)   run_serve ;;
  "")
    # Legacy default path (dev/compose).
    run_migrate
    [ "${CHARTNAV_RUN_SEED:-0}" = "1" ] && run_seed || true
    run_serve
    ;;
  *)
    echo "==> exec $*"
    exec "$@"
    ;;
esac
