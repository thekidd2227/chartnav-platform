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

.PHONY: help install migrate seed test boot smoke docs verify clean reset-db pg-verify docker-build docker-up docker-down web-install web-dev web-build web-typecheck web-test web-verify e2e e2e-headed e2e-ui e2e-a11y e2e-visual e2e-visual-update audit-prune sbom release-build staging-up staging-verify staging-rollback staging-down dev

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

e2e: ## Playwright E2E — boots full stack on 8001/5174, tears down cleanly
	cd apps/web && npx playwright test --reporter=list

e2e-headed: ## Playwright E2E in a visible browser
	cd apps/web && npx playwright test --headed --reporter=list

e2e-ui: ## Playwright interactive UI mode
	cd apps/web && npx playwright test --ui

e2e-a11y: ## axe-core accessibility sweep only
	cd apps/web && npx playwright test tests/e2e/a11y.spec.ts --reporter=list

e2e-visual: ## visual regression baseline (local only; baselines are OS-specific)
	cd apps/web && npx playwright test tests/e2e/visual.spec.ts --reporter=list

e2e-visual-update: ## refresh visual baselines after an intentional UI change
	cd apps/web && npx playwright test tests/e2e/visual.spec.ts --update-snapshots --reporter=list

audit-prune: ## Prune security_audit_events older than CHARTNAV_AUDIT_RETENTION_DAYS (override with --days via ARGS=...)
	$(PY) scripts/audit_retention.py $(ARGS)

sbom: ## Generate the release SBOM JSON into dist/release/_sbom.json
	mkdir -p dist/release
	$(PY) scripts/sbom.py --out dist/release/_sbom.json
	@echo "wrote dist/release/_sbom.json"

release-build: ## Build release artifacts into dist/release/<version>/ (usage: make release-build VERSION=v0.1.0)
	bash scripts/release_build.sh $(VERSION)

staging-up: ## Boot the staging stack (requires infra/docker/.env.staging)
	bash scripts/staging_up.sh

staging-verify: ## Run staging smoke + observability checks
	bash scripts/staging_verify.sh

staging-rollback: ## Roll the staging API image back (usage: make staging-rollback TAG=v0.1.0)
	bash scripts/staging_rollback.sh $(TAG)

staging-down: ## Tear down the staging stack
	cd infra/docker && docker compose --env-file .env.staging -f docker-compose.staging.yml down

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
