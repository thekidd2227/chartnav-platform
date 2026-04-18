# E2E & Release

## E2E harness

### Stack
- **Playwright** (`@playwright/test`) with the `chromium` browser.
- Playwright's `webServer` boots **both** backend and frontend, waits for
  their `/health` / `/` URLs, and tears both down on exit. No bash
  orchestration, no orphan processes.

### Config

`apps/web/playwright.config.ts`:

- **Backend** boots on `127.0.0.1:8001` using an ephemeral SQLite file
  at `apps/api/.e2e.chartnav.db` (the operator's dev DB is never
  touched). The config runs:
  ```
  rm -f .e2e.chartnav.db
  alembic upgrade head
  python scripts_seed.py
  uvicorn app.main:app --port 8001
  ```
- **Frontend** boots on `127.0.0.1:5174` via `npm run dev -- --host 127.0.0.1 --port 5174`, with `VITE_API_URL` pointed at the E2E backend.
- `reuseExistingServer: !CI` — locally, running `make e2e` twice in a
  row reuses the stack; in CI each run is fresh.
- Traces, screenshots, videos retained on failure only.

### Vitest / Playwright isolation
`vite.config.ts` now narrows Vitest `test.include` to `src/**/*.test.{ts,tsx}` and excludes `tests/**`, so Playwright specs and Vitest specs never cross-contaminate.

## E2E coverage

`apps/web/tests/e2e/workflow.spec.ts` (8 tests):

| Scenario                                                           |
|--------------------------------------------------------------------|
| App boots, resolves default seeded identity                        |
| Switching identity (admin1 → admin2) swaps visible encounter scope  |
| Admin opens detail, creates encounter, sees it in the list         |
| Admin appends an event; it appears in the timeline                 |
| Clinician performs operational transitions; reviewer edge not offered |
| Reviewer sees completion/kick-back controls, no create button, no event composer |
| Unknown email surfaces `identity-error` chip with `unknown_user`   |
| Status filter narrows the list                                     |

Tests use resilient selectors: `role`, placeholder text, and `data-testid` for elements without another stable hook.

Local run:
```bash
make e2e          # headless
make e2e-headed   # visible browser
make e2e-ui       # Playwright UI mode
```

Result at time of writing: **8/8 passed in ~14s**.

## CI

New `e2e` job in `.github/workflows/ci.yml`:

1. `backend-sqlite` + `frontend` must pass first.
2. Set up Python 3.11 + Node 20 (both with caches).
3. `pip install -e "apps/api[dev,postgres]"` (system install — verify.sh already tolerates missing `.venv`).
4. `npm ci` in `apps/web`.
5. `npx playwright install --with-deps chromium`.
6. `npx playwright test --reporter=list` (Playwright boots + tears down the stack).
7. On failure, upload `playwright-report/` + `test-results/` as an artifact for debugging.

## Release pipeline

### `scripts/release_build.sh`

One command to produce a releasable bundle under `dist/release/<version>/`:

- `chartnav-api-<version>.tar` — `docker save` of `chartnav-api:<version>` (importable with `docker load`).
- `chartnav-web-<version>.tar.gz` — static bundle from `apps/web/dist` (drop behind any CDN/reverse proxy).
- `MANIFEST.txt` — version, git sha, ref, build time, artifact sizes + sha256s.

Version resolution:
1. Explicit arg (e.g. `bash scripts/release_build.sh v0.1.0`).
2. Exact git tag on `HEAD`.
3. Fallback `dev-<short-sha>`.

Local:
```bash
make release-build VERSION=v0.1.0
```

`dist/release/` is gitignored.

### `.github/workflows/release.yml`

Triggers:
- `push` on tags matching `v*.*.*` (e.g. `v0.1.0`, `v1.2.3-rc1`).
- `workflow_dispatch` with a `version` input (manual).

Steps:
1. Resolve version from the tag or input.
2. Install `apps/web` deps (Node 20).
3. Login to `ghcr.io`.
4. `docker buildx build + push` of `ghcr.io/<owner>/chartnav-api:<version>` **and** `:latest`.
5. Run `scripts/release_build.sh <version>` to produce the local artifact set.
6. Upload the whole `dist/release/<version>/` as a workflow artifact (always).
7. On tag pushes only, create a **GitHub Release** with:
   - auto-generated notes from the commit log
   - `chartnav-api-<version>.tar`, `chartnav-web-<version>.tar.gz`, `MANIFEST.txt` attached.

Permissions: `contents: write` for the release, `packages: write` for `ghcr.io`.

Release is never auto-triggered from CI commits — only an explicit tag push or manual dispatch cuts one.

## Release flow (operator view)

```bash
# 1. work lands on main, CI green
git checkout main && git pull --ff-only

# 2. tag
git tag -a v0.1.0 -m "ChartNav v0.1.0"
git push origin v0.1.0

# 3. GitHub Actions runs the release workflow, pushes the GHCR image,
#    creates the Release, attaches the tarballs.

# 4. deploy
docker pull ghcr.io/<owner>/chartnav-api:v0.1.0
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

## Staging artifact (phase 11)

`scripts/release_build.sh` now also writes `chartnav-staging-<version>.tar.gz`
containing the staging compose file, its env template, and the runbook
scripts (`staging_up.sh`, `staging_verify.sh`, `staging_rollback.sh`)
plus the three new doc pages (19/20/21). `release.yml` attaches the
tarball to the GitHub Release alongside the API image tar and web
bundle, so a staging operator can `curl` one archive and be ready to
run against the pinned image tag.

## SBOM + image digest (phase 15)

`scripts/release_build.sh` now emits **two additional files** per
release:

- `chartnav-sbom-<version>.json` — produced by `scripts/sbom.py`.
  Captures project + version, git sha/ref/tag/dirty, image owner +
  tag (when `CHARTNAV_IMAGE_TAG` is set), full `pip list --format
  json` (API venv), full `npm list --all --json` tree of `apps/web`
  (falls back to `package-lock.json` summary if `node_modules` isn't
  installed). The `.notes` field is explicit that this is a plain
  JSON inventory — **not** a signed CycloneDX document. Upgrading to
  `cyclonedx-py` + `cyclonedx-npm` is the obvious next step.
- `chartnav-api-<version>.digest.txt` — `docker image inspect
  --format '{{.Id}}'` of the release image. Deployers can diff the
  digest of what they pulled from GHCR against what was released.

Both files are sha256'd in `MANIFEST.txt` (the manifest is still the
integrity anchor) and both are attached to the GitHub Release by
`release.yml`. Full reference in
`25-enterprise-quality-and-compliance.md`.

## E2E coverage (phase 15 addendum)

Playwright now runs 21 tests across 3 spec files:

- `workflow.spec.ts` — 12 (unchanged contract).
- `a11y.spec.ts` — 5 axe-core scans (hard gate — `serious`/`critical`
  findings fail CI).
- `visual.spec.ts` — 4 Playwright screenshots. **Local only**:
  baselines are macOS-specific (`*-chromium-darwin.png`); CI runs on
  Linux and would fail first-run. Documented honestly.

`playwright.config.ts`'s backend webServer sets
`CHARTNAV_RATE_LIMIT_PER_MINUTE=0` so the full suite doesn't trip
the per-IP rate limiter when every request comes from 127.0.0.1.

## What this phase does NOT do

- No staging / production deploy target is connected — the release workflow builds and publishes, operators still run `docker compose` wherever they host it.
- No automated Postgres E2E — Playwright's webServer uses SQLite for speed + isolation. Postgres parity is still proven by `backend-postgres`.
- No rollback automation — rollbacks are `docker pull` of the previous tag.
- No cosign / Sigstore signing, no CycloneDX / SPDX, no SLSA provenance. The SBOM is the input to those next steps.
