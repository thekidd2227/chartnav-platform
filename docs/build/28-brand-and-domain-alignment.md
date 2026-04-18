# Brand & Domain Alignment (phase 17)

This phase does two things: (1) links `chartnav.ai` to the existing
marketing page at `https://arcgsystems.com/chartnav/`, and (2) brings
the product UI into explicit visual alignment with the ChartNav brand
system used by the marketing site. No behavior changes, no endpoint
changes, no new dependencies.

## 1. Domain — `chartnav.ai` → `https://arcgsystems.com/chartnav/`

Primary mechanism: **GoDaddy 301 forwarding** on both the apex and
`www`. GoDaddy does the redirect at its edge (TLS terminated by
GoDaddy) and the visitor lands on the canonical marketing URL.

Secondary safety-net (implemented in-repo, [`~/arcg-live`]):

- `index.html` and `public/404.html` run a host-based redirect
  **before** anything else. If DNS for `chartnav.ai` is ever pointed
  at GitHub Pages (instead of or in addition to GoDaddy forwarding),
  the site itself still bounces visitors to
  `https://arcgsystems.com/chartnav/<path>`.
- The `CNAME` file stays `arcgsystems.com`; we don't rebrand Pages'
  primary domain.

Full operator runbook: `arcg-live/docs/chartnav-ai-domain-runbook.md`.

### Verification

```bash
# Once GoDaddy forwarding is saved:
curl -sI http://chartnav.ai       | grep -i ^location
curl -sI https://chartnav.ai      | grep -i ^location
curl -sI https://www.chartnav.ai  | grep -i ^location
# All three must point at: https://arcgsystems.com/chartnav/
```

### What's external vs in-repo

- **External (GoDaddy UI)**: the actual 301 forwarding rule creation
  on both the apex and the `www` subdomain. This is the primary path
  and is the only work required to flip the domain live. Cannot be
  automated from this repo without registrar API access.
- **In-repo (this commit)**: safety-net redirect + runbook.

## 2. Brand alignment — ChartNav product UI

Before: a clean-but-generic muted-blue shell with ad-hoc tokens.

After: an explicit med-tech light brand system that mirrors the
marketing site's tokens 1:1. The product and the marketing site now
share one visual vocabulary.

### Token alignment

All color, radius, and shadow tokens are lifted from
`arcg-live/src/components/chartnav/chartnav.css`. The same teal
(`#0B6E79`) is primary. Legacy token names (`--fg`, `--muted`,
`--accent`, …) remain as aliases so no component needs to be
rewritten.

| Concern        | Before                      | After (ChartNav brand)     |
|----------------|-----------------------------|-----------------------------|
| Primary        | `#0b6e79` (same teal)       | `#0B6E79` + `hover`/`active`/`tint`/`soft` scale |
| Surface bg     | `#ffffff` / `#f8fafc`       | `#F4F8FA` (page) + `#FFFFFF` (card) + `#F8FBFC` (alt) |
| Muted text     | `#64748B` (borderline on light bg) | `#475569` (AA contrast on `#F4F8FA`) |
| Borders        | `#e5e7eb`                   | `#DCE5EA` + `#C4D2D9` strong |
| Typography     | System default              | **Inter** via Google Fonts + cv02/03/04/11 features |
| Radii          | 6 / 8 / 10                  | 6 (sm) / 10 (md) / 14 (lg) + pill |
| Shadows        | one flat `rgba(15,23,42,0.25)` | sm / md / lg scale, teal-tinted on md |

### Visible changes

- App header shows the real **ChartNav logo SVG** (teal `Chart` +
  `Nav` wordmark with the cross-and-pulse mark) instead of the
  `<span>Chart</span><span>Nav</span>` text approximation.
- "Workflow" label next to the wordmark is now a subtle uppercase
  pill, not an inline span.
- Buttons: larger hit targets, brand-teal primary, focus rings use
  the primary-tint token.
- Tables + cards: proper border + shadow elevation, consistent
  radius rhythm.
- Status pills: tuned to the brand token palette; `in_progress` is
  now primary-tint (teal) instead of amber — it reads as "active",
  not "caution".
- Filters / form inputs: focus ring uses brand teal.
- Modal backdrop gets a subtle blur for visual depth.
- Admin tabs re-styled as an actual underlined tab strip (brand
  teal underline on active), not just contrasting buttons.
- Platform banner (phase 16) now uses the primary-soft background
  with a 3px teal left border — reads as an informational banner.

### Footer — "Powered by ARCG Systems"

A single, subtle attribution line in the app shell footer:

```
ChartNav · Clinical workflow platform        POWERED BY ARCG SYSTEMS
```

- Rendered exactly once per page (inside `<App>` after the main
  layout).
- 11px uppercase, letter-spacing 0.12em, muted color.
- `data-testid="app-footer-arcg"` for test stability.
- Copy is literal: `Powered by ARCG Systems`.
- Vitest assertion in `src/test/App.test.tsx` locks the exact
  copy in.

### A11y

New tokens were chosen specifically to preserve AA contrast:
- `--cn-muted` moved from `#64748B` → `#475569` (6.17:1 on page bg).
- `--cn-dim` moved from `#94A3B8` → `#64748B` (4.54:1 on white).

The existing axe-core baseline (`apps/web/tests/e2e/a11y.spec.ts`)
passes 5/5 after this phase with zero `serious`/`critical`
violations. Visual-regression baselines
(`apps/web/tests/e2e/visual.spec.ts-snapshots/*-darwin.png`) were
intentionally regenerated — the UI *should* look different now.

## 3. Files changed

### `arcg-live` (marketing site)

- `index.html` — host-based `chartnav.ai` safety-net redirect.
- `public/404.html` — same safety-net before SPA redirect.
- `docs/chartnav-ai-domain-runbook.md` — GoDaddy operator runbook.

### `chartnav-platform` (product)

- `apps/web/index.html` — Inter font, theme-color, meta description,
  favicon pointing at the brand SVG.
- `apps/web/public/brand/` — logo (`chartnav-logo.svg`), mark
  (`chartnav-mark.svg`), favicon (`chartnav-favicon.svg`). Copied
  from `arcg-live/public/chartnav/brand/` so the product and site
  share one SVG source.
- `apps/web/src/styles.css` — full rewrite into the ChartNav token
  system. Legacy class names preserved; legacy var names aliased.
- `apps/web/src/App.tsx` — logo swap in header, `<footer>` with
  Powered-by line, `<div>` → fragment wrapper so the footer sits
  outside the layout grid.
- `apps/web/src/InviteAccept.tsx` — inline colors moved to the new
  AA-safe muted token.
- `apps/web/src/test/App.test.tsx` — new test asserting the footer
  line exists and carries the literal "Powered by ARCG Systems".

## 4. What this phase does NOT do

- Does **not** ship a new endpoint, migration, or data-model change.
- Does **not** alter the ChartNav marketing page copy or layout.
- Does **not** add a ChartNav-branded marketing landing page to the
  product repo — the product is still an operator console, not a
  marketing surface.
- Does **not** introduce a component library or design-system
  package. Tokens + plain CSS remain; that's deliberate.
- Does **not** automate GoDaddy — the user completes forwarding via
  the GoDaddy UI using the runbook.
