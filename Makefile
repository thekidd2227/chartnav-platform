# ChartNav — canonical local verification path.
#
# Typical workflow for a developer who just pulled main:
#   make install
#   make verify     # migrate + seed + tests + smoke, all against a fresh dev DB
#
# Individual targets are safe to run standalone.

API_DIR := apps/api
VENV    := $(API_DIR)/.venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
DEV_DB  := $(API_DIR)/chartnav.db
PORT    := 8765

.PHONY: help install migrate seed test boot smoke docs verify clean reset-db pg-verify docker-build docker-up docker-down web-install web-dev web-build web-typecheck web-test web-verify dev

help:
	@awk 'BEGIN{FS=":.*?## "} /^[a-zA-Z_-]+:.*?## /{printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create venv + install backend (incl. dev deps)
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "$(API_DIR)[dev]"

migrate: ## Apply Alembic migrations to the dev SQLite DB
	cd $(API_DIR) && .venv/bin/alembic upgrade head

seed: ## Run the idempotent seed against the dev DB
	cd $(API_DIR) && .venv/bin/python scripts_seed.py

test: ## Run the full pytest suite
	cd $(API_DIR) && .venv/bin/pytest tests/ -v

boot: ## Boot the API (foreground). Ctrl-C to stop.
	cd $(API_DIR) && .venv/bin/uvicorn app.main:app --port $(PORT)

smoke: ## Curl-level smoke against a locally-running API (BASE=http://... optional)
	cd $(API_DIR) && bash scripts/smoke.sh $${BASE:-http://127.0.0.1:$(PORT)}

docs: ## Regenerate docs/final HTML + PDF
	$(PY) scripts/build_docs.py

reset-db: ## Drop + recreate the dev DB (migrate + seed)
	rm -f $(DEV_DB)
	$(MAKE) migrate seed

# The canonical single-command verification: wipes dev DB, re-migrates,
# re-seeds, runs tests, boots the API, runs smoke, tears it down.
# Backgrounding/teardown lives in scripts/verify.sh so Make's stdout
# pipe is never entangled with uvicorn.
verify: reset-db test ## Full local gate: reset DB, tests, boot + smoke
	bash scripts/verify.sh

pg-verify: ## Full Postgres parity proof (requires docker)
	bash scripts/pg_verify.sh

web-install: ## Install frontend deps
	cd apps/web && npm install

web-dev: ## Run Vite dev server (expects API on :8000)
	cd apps/web && npm run dev

web-build: ## Production build of the frontend
	cd apps/web && npm run build

web-typecheck: ## tsc --noEmit on the frontend
	cd apps/web && npm run typecheck

web-test: ## Run frontend unit/integration tests (vitest)
	cd apps/web && npm test

web-verify: ## Frontend gate: typecheck + test + build
	cd apps/web && npm run typecheck && npm test && npm run build

dev: ## Boot backend (port 8000) + frontend (port 5173) together
	@bash -c 'set -e; \
	  cd $(API_DIR) && .venv/bin/uvicorn app.main:app --port 8000 --reload & echo $$! > /tmp/chartnav_dev_api.pid; \
	  cd apps/web && npm run dev & echo $$! > /tmp/chartnav_dev_web.pid; \
	  trap "kill \$$(cat /tmp/chartnav_dev_api.pid) \$$(cat /tmp/chartnav_dev_web.pid) 2>/dev/null || true" INT TERM EXIT; \
	  wait'

docker-build: ## Build the production API image
	docker build -t chartnav-api:local apps/api

docker-up: ## Start the production compose stack (API + Postgres)
	cd infra/docker && docker compose -f docker-compose.prod.yml up --build

docker-down: ## Stop the production compose stack
	cd infra/docker && docker compose -f docker-compose.prod.yml down -v

clean: ## Remove caches + dev DB
	rm -f $(DEV_DB)
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
