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

.PHONY: help install migrate seed test boot smoke docs verify clean reset-db

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

clean: ## Remove caches + dev DB
	rm -f $(DEV_DB)
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
