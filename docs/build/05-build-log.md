# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 9: Playwright E2E + release pipeline

### Step 1 — Baseline
- Head: `f83d748` (create UI + frontend tests + frontend CI).
- Backend untouched; 28/28 pytest, 12/12 vitest, all smoke green.

### Step 2 — Playwright harness
- Installed `@playwright/test`; ran `npx playwright install chromium --with-deps`.
- New `apps/web/playwright.config.ts`:
  - Backend launched on `127.0.0.1:8001` against an ephemeral SQLite file `apps/api/.e2e.chartnav.db` so the operator's dev DB is never touched.
  - Frontend launched on `127.0.0.1:5174` with `VITE_API_URL` pointed at the E2E backend.
  - `webServer: [backend, frontend]` — Playwright waits for health + tears both down on exit.
  - `reuseExistingServer: !CI`, chromium-only project, traces/videos/screenshots on failure.
- `package.json` now carries `test:e2e`, `test:e2e:headed`, `test:e2e:ui`.
- `tsconfig.json` includes `playwright.config.ts` and `tests/`.
- Narrowed Vitest `test.include` to `src/**/*.test.{ts,tsx}` and excluded `tests/**` so Playwright specs aren't pulled into vitest runs.

### Step 3 — E2E test suite
- New `apps/web/tests/e2e/workflow.spec.ts` (8 tests):
  - App boots + default identity resolves
  - Identity switch (admin1 → admin2) changes visible encounter list
  - Admin opens detail, creates a new encounter, sees it appear
  - Admin appends a workflow event; timeline reflects it
  - Clinician drives `scheduled→in_progress→draft_ready`; review edge not offered
  - Reviewer sees completion + kick-back controls, no create button, no event composer
  - Unknown email surfaces the `identity-error` chip with `unknown_user`
  - Status filter narrows the list
- Uses `role` / `placeholder` / `data-testid` selectors. No ad-hoc classnames.
- Bug fixed during first run: a strict-mode selector conflict — the new encounter's PID appeared in both the list row AND the banner. Scoped assertion to `getByTestId("enc-list")`.

### Step 4 — CI wiring
- New `e2e` job in `.github/workflows/ci.yml`: `needs: [backend-sqlite, frontend]`.
  - Install backend + frontend deps.
  - `npx playwright install --with-deps chromium`.
  - `npx playwright test --reporter=list` (Playwright manages servers).
  - Upload `playwright-report/` + `test-results/` on failure for debugging.

### Step 5 — Release artifacts
- New `scripts/release_build.sh`:
  - Resolves version from arg / tag / `dev-<short-sha>` fallback.
  - `docker build` → `docker save` → `chartnav-api-<version>.tar`.
  - `npm ci` + `npm run build` → `chartnav-web-<version>.tar.gz`.
  - `MANIFEST.txt` with git sha / ref / build time / sizes / sha256 sums.
  - Output under `dist/release/<version>/` (gitignored).
- New `.github/workflows/release.yml`:
  - Triggers on `v*.*.*` tag push and `workflow_dispatch` with a version input.
  - Pushes `ghcr.io/<owner>/chartnav-api:<version>` + `:latest` via Buildx.
  - Runs `scripts/release_build.sh` and uploads the full `dist/release/<version>/` as a workflow artifact.
  - On tag pushes only, creates a GitHub Release with auto-generated notes and attaches the tarballs + manifest.

### Step 6 — Makefile
- New targets: `e2e`, `e2e-headed`, `e2e-ui`, `release-build`.
- `make release-build VERSION=v0.1.0` shells to `scripts/release_build.sh`.

### Step 7 — Verification
- Local Playwright run: **8/8 passed in ~14s**.
- Vitest still **12/12**. Backend `make verify` still **28/28 pytest + 9/9 smoke**.
- `apps/api/.venv/bin/python scripts/build_docs.py` regenerates HTML + PDF.
- CI YAML (both `ci.yml` and `release.yml`) parses cleanly via PyYAML.
- Honest limitation: no `act` in shell to execute the workflows locally; parse + structural review.

### Step 8 — Hygiene
- `.gitignore` now excludes `apps/web/playwright-report/`, `apps/web/test-results/`, `apps/web/e2e-results/`, and `dist/release/`.
- Dev DB reset to seeded state before commit.

---

## Prior phases

- **Phase 8 — Create UI + vitest + frontend CI** (`f83d748`)
- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
