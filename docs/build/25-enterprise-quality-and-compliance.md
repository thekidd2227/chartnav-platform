# Enterprise Quality & Compliance

Phase 15 turns ChartNav from "enterprise-shaped" into
"enterprise-credible" by landing five real guarantees: an a11y floor, a
visual-regression baseline, a release SBOM + image digest, an audit
retention helper, and admin-list pagination/search — plus two feature
flags that actually gate UI behavior.

## 1. Accessibility baseline

Stack: `@axe-core/playwright` over Chromium.

Scope: app shell + encounter list + encounter detail + admin panel
(users + audit tabs) + invite accept screen.

Tests: `apps/web/tests/e2e/a11y.spec.ts` (5 scenarios). The floor is
the set of `serious` and `critical` axe findings — minor ones are
logged but not blocking. Local + CI.

Fixes landed while establishing the baseline:
- `aria-label="Event type"` on the event-composer `<select>` in
  encounter detail.
- `aria-label="Role for <email>"` on each inline role `<select>` in
  the admin users table.

Commands:
```bash
make e2e-a11y          # only axe scans
make e2e               # full suite including a11y
```

Gaps intentionally left:
- No color-contrast audit beyond axe's automated rules (manual pass
  not done).
- No keyboard-only walkthrough of every modal (would warrant a
  dedicated QA sweep).

## 2. Visual regression baseline

Stack: Playwright `toHaveScreenshot`.

Scope: `apps/web/tests/e2e/visual.spec.ts` — 4 anchor views
(encounter list, admin users tab, admin audit tab, invite accept).

Setup notes:
- Viewport pinned to 1280×820.
- Animations + transitions disabled via an injected stylesheet.
- Identity seeded to `admin@chartnav.local` before each snapshot.
- `maxDiffPixelRatio: 0.02` — small renderer drift shouldn't break a
  run, but a real layout regression will cross it.

Baselines are **OS-specific** (Chromium renders subtly differently on
macOS vs. Linux). We ship macOS baselines under
`apps/web/tests/e2e/visual.spec.ts-snapshots/*-chromium-darwin.png`
for local dev. CI does **not** run visual regression (it would fail
first-run against mismatched-OS baselines); it is a local-only gate
for now. Documented honestly as a remaining gap.

Commands:
```bash
make e2e-visual          # run against current baselines
make e2e-visual-update   # intentional UI change → refresh baselines
```

## 3. Admin list scaling

Backend: `GET /users` and `GET /locations` now accept
`limit` (1..500, default 100), `offset` (≥ 0), `q` (substring
search), plus `role` on `/users`. They emit `X-Total-Count`,
`X-Limit`, `X-Offset` headers. All filters combine with the existing
`include_inactive` lens.

Frontend: the Users and Locations tabs have a search box + Prev/Next
pager (25/page) + count header. Org scope is preserved — pagination
never leaks cross-org rows.

Tests: `test_enterprise.py` covers pagination headers, offset
movement, `q` substring match, role filter (valid + invalid),
cross-org isolation.

## 4. Feature-flag consumption

`organization.settings.feature_flags` is now consumed by the
frontend. Two flags ship wired:

| flag           | behavior when `false`                           |
|----------------|-------------------------------------------------|
| `audit_export` | Hides the **Export CSV** button on the Audit tab |
| `bulk_import`  | Hides the **Bulk import…** button on Users tab   |

Both default to `true` (absent → on). Admins flip them from the
Organization tab. Server is unchanged — the endpoints still accept
requests from admins regardless of flag state. Flags only affect the
UI surface; a sophisticated attacker with an admin role could still
hit the endpoint directly. That's the point of feature flags as UX
toggles, not security controls, and it's documented that way.

Frontend test coverage (`AdminPanel.test.tsx`):
- `audit_export=false` → `admin-audit-export` absent, `admin-audit-refresh` present.
- `bulk_import=false` → `admin-user-bulk-open` absent.
- Search field dispatches `listUsersPage({ q: ... })`.

## 5. Release compliance signals

### SBOM

`scripts/sbom.py` writes a JSON document with:
- project + version + git sha/ref/tag/dirty-flag,
- image owner + tag (when `CHARTNAV_IMAGE_TAG` is set),
- full `pip list --format json` of the API venv,
- full `npm list --all --json` tree of `apps/web` (falls back to
  `package-lock.json` summary if node_modules isn't installed).

Explicit note on the file itself: this is **not** a signed CycloneDX
document. It's a real inventory, honest about its shape. Sufficient
for audit questions about dep versions + git provenance; upgrading to
signed CycloneDX (`cyclonedx-py` + `cyclonedx-npm`) is the obvious
next step and the `.notes` field in the SBOM says so.

### Image digest capture

`scripts/release_build.sh` writes `chartnav-api-<version>.digest.txt`
via `docker image inspect --format '{{.Id}}'`. The digest is attached
to GitHub Releases alongside the tarballs so deployers can verify the
pulled image id against what was released.

### Release bundle contents (phase 15)

`dist/release/<version>/`:
- `chartnav-api-<version>.tar`           (docker save)
- `chartnav-web-<version>.tar.gz`        (vite build)
- `chartnav-staging-<version>.tar.gz`    (compose + scripts + docs)
- `chartnav-sbom-<version>.json`         **NEW**
- `chartnav-api-<version>.digest.txt`    **NEW**
- `MANIFEST.txt`                         (sha256 of every file)

`MANIFEST.txt` now sha256s every artifact including the SBOM + digest
file, so the manifest itself is the integrity anchor.

## 6. Retention / compliance scaffolding

### Audit retention helper

`apps/api/app/retention.py::prune_audit_events(retention_days, dry_run)`
deletes rows from `security_audit_events` older than `retention_days`.
The app itself **never** silently prunes — the helper runs only when
an operator invokes it. Retention is driven by
`CHARTNAV_AUDIT_RETENTION_DAYS` (default `0` = never prune).

### Operator CLI

```bash
# use env default
python scripts/audit_retention.py
# explicit threshold
python scripts/audit_retention.py --days 90
# report without deleting
python scripts/audit_retention.py --days 90 --dry-run
# via Make
make audit-prune ARGS="--days 90 --dry-run"
```

Output is a JSON summary: `status`, `retention_days`, `cutoff`,
`matched`, `deleted`, `dry_run`. Backend tests (`test_enterprise.py`)
cover disabled (`0`), dry-run, and real deletion paths.

### Runbook notes
See `21-staging-runbook.md` for the cron-friendly invocation and the
compliance-facing retention discussion in `20-observability.md`.

### What this scaffold does NOT do
- No SIEM shipping / archival-to-S3 out of the box.
- No regulated-industry attestation (HIPAA/SOC2/ISO) — documentation
  only. Those belong to a real audit workstream.
- No row-level "legal hold" mechanism.

## 7. Test + CI summary

| Layer             | Count | Notes |
|-------------------|:-----:|-------|
| pytest (backend)  |  118  | +8 `test_enterprise.py` (admin list + retention + feature-flag round-trip) |
| Vitest (frontend) |  28   | +3 AdminPanel (flags, search dispatch) |
| Playwright E2E    |  21   | +5 a11y (axe) + 4 visual regression + 12 workflow |

CI (`.github/workflows/ci.yml`):
- The existing `e2e` job now runs `workflow.spec.ts` **and**
  `a11y.spec.ts` (hard gate).
- Visual regression is local-only (see above).
- Release workflow (`release.yml`) bundles SBOM + image digest;
  operators receive them in every GitHub Release.

## 8. What this phase explicitly does NOT do

- No Sigstore/cosign signing of images or artifacts.
- No CycloneDX / SPDX standardized SBOM.
- No attested provenance (SLSA, in-toto).
- No automated dependency-vulnerability scan (depends on the
  organization's chosen scanner — the SBOM is the input).
- Visual regression does not run in CI.
- Retention helper is not scheduled in the app itself — operator cron
  is expected.
