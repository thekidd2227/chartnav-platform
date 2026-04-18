# Build Log

Reverse-chronological.

---

## 2026-04-18 — Phase 15: enterprise quality + compliance signals

### Step 1 — Baseline
- Head: `3be3933` (invitations + settings schema + audit export + event hardening + bulk users).
- 110 pytest + 25 Vitest + 12 Playwright + 9 smoke green.

### Step 2 — Admin list scaling
- Backend: `GET /users` and `GET /locations` now accept `limit`
  (1..500, default 100), `offset` (≥0), `q` substring search, and
  `role` (users only). Both endpoints emit `X-Total-Count`, `X-Limit`,
  `X-Offset` headers. `include_inactive` continues to work.
- Invalid role filter → 400 `invalid_role`.
- Frontend: `api.ts` gains `listUsersPage` / `listLocationsPage` that
  return `{items, total, limit, offset}` by reading the headers.
- `AdminPanel.tsx`: Users + Locations tabs each get a search input +
  Prev/Next pager (25/page) + count header. Self-search resets offset
  on every change.

### Step 3 — Feature-flag consumption
- New `featureEnabled(org, flag)` helper in `api.ts` — flags default
  to `true` when unset so the UI doesn't silently strip features for
  orgs that haven't touched settings.
- AdminPanel loads `getOrganization(identity)` on mount, holds the
  result in state, and passes it into panes that gate UI.
- `audit_export=false` hides the **Export CSV** button. `bulk_import=false`
  hides the **Bulk import…** button. Both default-on.
- `flash` in AdminPanel is now `useCallback`-stable, avoiding an
  infinite refresh loop that showed up once children started holding
  it in `refresh` dependency arrays.

### Step 4 — Audit retention helper
- New `apps/api/app/retention.py::prune_audit_events(retention_days, dry_run)`.
  App never silently prunes; operators invoke the helper.
- New `CHARTNAV_AUDIT_RETENTION_DAYS` (default 0 = never) in `app/config.py`.
- New `scripts/audit_retention.py` CLI: supports `--days`, `--dry-run`;
  prints a JSON summary.
- New Makefile target `audit-prune ARGS="..."`.

### Step 5 — SBOM + image digest
- New `scripts/sbom.py`: captures project + git sha/tag/dirty + image
  tag (when set) + `pip list --format json` (API venv) + `npm list
  --all --json` (falls back to `package-lock.json` summary). Honest
  `.notes` field calls out that this is not a signed CycloneDX doc.
- `scripts/release_build.sh` now writes `chartnav-sbom-<v>.json` and
  `chartnav-api-<v>.digest.txt` (from `docker image inspect`).
- `MANIFEST.txt` sha256s both. `release.yml` attaches both to tag-based
  GitHub Releases.

### Step 6 — Accessibility baseline
- Installed `@axe-core/playwright`.
- New `apps/web/tests/e2e/a11y.spec.ts`: scans app shell + encounter
  list + encounter detail + admin panel (users, audit) + invite
  accept. `serious`/`critical` axe findings are blocking.
- Fixes landed while running the baseline:
  - `aria-label="Event type"` on the composer `<select>` in App.tsx.
  - `aria-label="Role for <email>"` on each inline role `<select>`
    in the admin Users table.

### Step 7 — Visual regression baseline
- New `apps/web/tests/e2e/visual.spec.ts`: 4 snapshots (encounter list,
  admin Users tab, admin Audit tab, invite accept). 1280×820 viewport,
  animations disabled via injected stylesheet, `maxDiffPixelRatio: 0.02`.
- Baselines committed for macOS only (`*-chromium-darwin.png`). CI
  does NOT run visual — Linux Chromium renders slightly differently.
  Honest limitation: documented in `25-enterprise-quality-and-compliance.md`.
- New `e2e-visual` / `e2e-visual-update` Make targets.

### Step 8 — CI wiring
- Existing `e2e` job now runs `workflow.spec.ts` + `a11y.spec.ts` (hard
  gate). Visual is excluded with a comment explaining why.
- Release workflow picks up SBOM + image digest automatically via the
  updated `scripts/release_build.sh`.

### Step 9 — Playwright rate-limit bugfix
- Running the full E2E suite (workflow + a11y + visual) was hitting
  the rate limiter (`CHARTNAV_RATE_LIMIT_PER_MINUTE=120` default)
  because all requests come from 127.0.0.1. Fix: set the env to `0`
  in `playwright.config.ts`'s backend webServer command, which is
  safe because the E2E DB is always ephemeral.

### Step 10 — Backend tests
- New `apps/api/tests/test_enterprise.py` (8 tests): pagination
  headers + offset + q + role filter + cross-org isolation; role
  filter 400; retention disabled / dry-run / actual delete; feature
  flags JSON round-trip.
- Full suite: **118/118 passed**.

### Step 11 — Frontend tests
- `AdminPanel.test.tsx` mocks extended for `listUsersPage`,
  `listLocationsPage`, `getOrganization` feature-flag variants.
- +3 Vitest tests: `audit_export=false` hides export button;
  `bulk_import=false` hides bulk button; user-search dispatches
  `listUsersPage({q})`.
- Vitest: **28/28 passed**.

### Step 12 — E2E
- a11y: **5/5 passed**.
- Visual: **4/4 passed** against freshly-generated macOS baselines.
- Workflow: **12/12 passed**.
- Total: **21/21 Playwright passed** in ~18s.

### Step 13 — Docs
- New `docs/build/25-enterprise-quality-and-compliance.md`.
- Updated `01-current-state`, `05-build-log`, `06-known-gaps`,
  `03-api-endpoints` (list pagination/search), `04-data-model`
  (feature_flags consumer note), `08-test-strategy`,
  `09-ci-and-deploy-hardening` (a11y lane + visual skipped reason),
  `15-frontend-integration` (search + pager + flag gating),
  `16-frontend-test-strategy` (a11y + visual), `17-e2e-and-release`
  (SBOM + digest bundle), `18-operational-hardening` + `20-observability`
  (retention notes), `21-staging-runbook` (retention runbook).
- `scripts/build_docs.py` picks up section 25.
- Final HTML + PDF regenerated.

### Step 14 — Hygiene
- Dev DB reset to pristine seeded state before commit.
- Visual baselines committed under `apps/web/tests/e2e/visual.spec.ts-snapshots/`.
- `.gitignore` already excludes caches, `.db`, release dist.

---

## Prior phases

- **Phase 14 — Invitations + schema + audit export + bulk** (`3be3933`)
- **Phase 13 — Operator control plane** (`5a5d846`)
- **Phase 12 — Admin governance** (`4ff4e28`)
- **Phase 11 — Staging deployment + observability** (`ee7cf43`)
- **Phase 10 — Real JWT bearer + operational hardening** (`cbc5184`)
- **Phase 9 — Playwright E2E + release pipeline** (`74fe8dd`)
- **Phase 8 — Create UI + vitest + frontend CI** (`f83d748`)
- **Phase 7 — Frontend workflow UI** (`c4f6e4f`)
- **Phase 6 — Prod auth seam + Docker + Postgres parity** (`700bb0b`)
- **Phase 5 — CI + runtime hardening + doc pipeline** (`cfa8ca9`)
- **Phase 4 — RBAC + full scoping + pytest** (`c6f29e6`)
- **Phase 3 — Dev auth + org scoping** (`efb5b56`)
- **Phase 2 — Strict state machine + filtering** (`505f025`)
- **Phase 1 — Workflow spine** (`93fceb4`)
