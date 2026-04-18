# Build Log

Reverse-chronological.

---

## 2026-04-17 — Phase 5: CI + runtime hardening + doc pipeline

### Step 1 — Baseline
- Starting head: `c6f29e6` (RBAC + full scoping + pytest suite).
- No migrations touched this phase.
- Tests still green locally (25/25) before any changes.

### Step 2 — Packaging
- `apps/api/pyproject.toml` now declares `[project.optional-dependencies].dev = ["pytest>=8", "httpx>=0.27"]` and `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. CI installs with `pip install -e "apps/api[dev]"`.

### Step 3 — CI workflow
- New `.github/workflows/ci.yml` with two jobs:
  - `backend` — checkout → setup-python 3.11 (pip cache) → `pip install -e ".[dev]"` → `alembic -x sqlalchemy.url=sqlite:///$RUNNER_TEMP/chartnav_ci.db upgrade head` → seed twice (idempotency proof) → `pytest tests/ -v` → boot uvicorn against the CI DB, poll `/health`, run `scripts/smoke.sh`.
  - `docs` (needs: backend) — apt-install Chromium → `python scripts/build_docs.py` with `CHARTNAV_PDF_BROWSER=chromium-browser` → upload the rebuilt HTML + PDF as a `chartnav-docs-final` artifact (`if-no-files-found: error`).
- Triggers: `push` to `main` and every `pull_request`.

### Step 4 — Smoke script
- New `apps/api/scripts/smoke.sh`. Shell-only curl assertions: `/health`, `/me` (401 without auth, 200 role=admin org=1 with admin header), `/encounters` (401/200), cross-org `?organization_id=2` lens → 403, own encounter 200, cross-org encounter 404. Exits non-zero on first failure.
- First draft used a helper function with an unquoted `$@` pass-through; that word-split the `X-User-Email` header and made curl hang on DNS for `admin@chartnav.local`. Rewrote to inline each assertion with proper quoting — no magic, no hangs.

### Step 5 — Reproducible doc build
- New `scripts/build_docs.py` (repo-rooted — paths resolved from `__file__`). Walks `docs/build/01..10` + `docs/diagrams/*`, renders the markdown subset + Mermaid blocks, writes the consolidated HTML, then prints to PDF via headless Chromium. `CHARTNAV_PDF_BROWSER` env var lets CI point at `chromium-browser` without code changes. Reportlab fallback for a plain-text PDF if no browser is present.
- Prior script `/tmp/build_final_docs.py` was a personal scratch file — now superseded by the in-repo version.

### Step 6 — Makefile (canonical local path)
- New root `Makefile` with targets: `install`, `migrate`, `seed`, `test`, `boot`, `smoke`, `docs`, `reset-db`, `clean`, and the composite `verify` (reset-db + test + boot + smoke).

### Step 7 — New docs
- `docs/build/09-ci-and-deploy-hardening.md` — workflow design, local path, dev/CI DB separation, smoke contract.
- `docs/build/10-doc-artifact-pipeline.md` — builder contract, section order, fallback behavior.

### Step 8 — Verification
- `make reset-db && make test` → 25/25 pytest passed (~12s).
- `make verify` → pytest green, uvicorn boot, smoke all 9 assertions green, process torn down cleanly.
- `scripts/build_docs.py` → regenerated `docs/final/chartnav-workflow-state-machine-build.{html,pdf}` deterministically.
- YAML sanity checked by loading with PyYAML; `act` not available in the shell, honest limitation documented in `06-known-gaps.md`.

### Step 9 — Git hygiene
- `.pytest_cache/` and `__pycache__/` still ignored.
- No DB files committed.
- DB reset to clean seeded state before commit.

---

## Prior phases (preserved)

### Phase 4 — RBAC + full scoping + pytest suite
`authz.py`, per-edge transition roles, `/organizations` / `/locations` / `/users` now authed + org-scoped, 25-test pytest suite with per-test temp SQLite.

### Phase 3 — Dev auth + org scoping
`auth.py` with `X-User-Email`, `Caller`, cross-org 404 on reads and 403 on assertions.

### Phase 2 — Strict state machine + filtering
`ALLOWED_TRANSITIONS` map, 400 `invalid_transition` with allowed-next listing, `GET /encounters` filters.

### Phase 1 — Workflow spine
Migration `a1b2c3d4e5f6`, idempotent seed, six encounter endpoints.
