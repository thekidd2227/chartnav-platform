# Phase 88 — Dependency Hardening Notes

**Date:** 2026-06-10
**Branch:** `feature/phase-88-release-hardening-pilot-evidence-gate`
**Trigger:** Independent audit flagged frontend dev dependency posture
(critical / moderate `npm audit` advisories).

## Scope

This phase reduces, but does not eliminate, the frontend `npm audit`
findings. The remaining moderate findings are documented with their
mitigation. Production runtime dependencies (`react`, `react-dom`)
are unchanged.

## Before / after

```
Before: 4 vulnerabilities (2 moderate, 2 critical)
After:  2 vulnerabilities (2 moderate, 0 critical)
```

### Critical advisories — resolved

| Package | Range | Advisory | Fix |
|---|---|---|---|
| `vitest` | <= 3.2.5 | GHSA-5xrq-8626-4rwp — Vitest UI server arbitrary file read/exec | Bumped to `3.2.6` (patch). |
| `@vitest/ui` | <= 3.2.5 | Same chain | Bumped to `3.2.6` (patch). |

Both are dev-only dependencies. The Vitest UI server is not exposed
in CI or production builds; the advisory is most acute when the UI is
opened on an operator workstation. The patch bump retires the
critical advisory without changing the major version of Vitest, so
the existing 896 web tests pass unchanged.

### Patch-bumps applied alongside

| Package | From | To | Reason |
|---|---|---|---|
| `jsdom` | `29.0.2` | `29.1.1` | Transitive bug-fix patches; vitest setup unchanged. |
| `@playwright/test` | `1.59.1` | `1.60.0` (via `npm update`) | Minor patches; e2e behavior unchanged. |
| `@axe-core/playwright` | `4.11.2` | `4.11.3` (via `npm update`) | Patch. |
| `@types/node` | `25.6.0` | `25.9.2` (via `npm update`) | Type-only. |
| `@types/react` | `18.3.28` | `18.3.31` (via `npm update`) | Type-only. |

### Moderate advisories — NOT yet fixed

Both remaining moderate advisories are in the same chain
(`esbuild` ≤ `0.24.2` → `vite` ≤ `6.4.1`). The published fix is to
upgrade `vite` to `8.x`, which is a multi-major bump (5 → 6 → 7 → 8)
and a documented breaking change.

| Package | Range | Advisory | Required upgrade | Reason for deferring |
|---|---|---|---|---|
| `vite` | <= `6.4.1` | GHSA-4w7w-66w2-5vf9 — path traversal in optimized deps `.map` handling | `vite@8.0.16` (semver-major) | Vite 5 → 8 changes module-resolution semantics, `@vitejs/plugin-react` major version, and dev-server defaults. Requires a separate hardening phase with its own regression matrix. |
| `esbuild` | <= `0.24.2` | GHSA-67mh-4wv8-2f99 — dev server can be queried cross-origin | `vite@8.0.16` (transitive) | Same chain. |

### Mitigation for the remaining moderate advisories

Both findings only fire when the **vite dev server** is reachable
from a network the operator does not control. In ChartNav's
deployment posture:

- **Production builds** (`vite build`) do not run a dev server. The
  produced static assets are served by an unrelated runtime. The
  advisory does not apply.
- **CI builds** (`vite build` + `vitest run`) do not start the dev
  server. The advisory does not apply.
- **Local development** (`npm run dev`) binds the dev server with
  Vite's standard config (`server.host: true`). For local-only
  loopback work this is the expected posture. Operators running on
  shared / untrusted networks should bind to `127.0.0.1` or run the
  dev server behind a host firewall until the vite 8 upgrade lands.

A separate phase should sequence the vite 5 → 8 upgrade:

1. Bump `vite` to `^6`, run vitest + tsc + axe.
2. Bump `vite` to `^7`, repeat.
3. Bump `vite` to `^8`, bump `@vitejs/plugin-react` to its v6 line,
   repeat.

Each step is its own PR with its own CI signal.

## Verification

```
$ cd apps/web
$ npm audit
2 moderate severity vulnerabilities

$ npx tsc --noEmit
(clean)

$ npx vitest run
Test Files  52 passed (52)
     Tests  896 passed (896)
```

## Files changed

- `apps/web/package.json` — bumped `vitest`, `@vitest/ui`, `jsdom`
  carets.
- `apps/web/package-lock.json` — npm-managed.

No source code changes. No production runtime upgrade.

## Recommendation for future work

Open a dedicated `feature/dependency-hardening-vite-8` phase to
sequence the `vite` 5 → 8 upgrade. Treat each major bump as its own
PR with full CI evidence. Do NOT bundle Vite 8 with a feature
release — the dev-server / module-resolution risk is large enough to
deserve its own change-control window.
