# UI Contract

Entry point: the `Coding` tab in the top view-toggle (`list / day /
month / coding`). Internally this renders
`features/clinical-coding/ClinicalCodingPanel.tsx`.

## Layout (desktop, ≥ 1180 px)

```
┌─ safety banner (persistent, yellow) ──────────────────────────────┐
├─ left rail ──────────┬─ center ─────────┬─ right panel ──────────┤
│ specialty quick-picks│ version bar     │ code detail             │
│ favorites            │ search form     │ specificity prompts     │
│ recent searches      │ results list    │ claim-support hints     │
│                      │                 │ child codes             │
│                      │                 │ source / line audit     │
└──────────────────────┴─────────────────┴─────────────────────────┘
┌─ admin audit strip (admin role only) ─────────────────────────────┐
│ version table · source · effective window · checksum · last sync │
└──────────────────────────────────────────────────────────────────┘
```

Below 1180 px the layout stacks to a single column.

## Persistent labels (always visible)

- Version label: e.g. `ICD-10-CM FY2026 (October 2025)` or `ICD-10-CM FY2026 (April 2026 Update)`
- Source authority: `CMS` (or `CMS (local fixture)`)
- Effective window: the resolved release's bounded window, e.g.
  `2025-10-01 → 2026-03-31` for the October release or
  `2026-04-01 → 2026-09-30` for the April update. Windows are never
  "open" once the superseding release is loaded.
- Last sync: local-formatted datetime from `downloaded_at`

Source-attribution also appears at the foot of every code-detail
card, including `source_file` + `source_line_no`.

## `data-testid` anchors

| Area | testid |
|---|---|
| Panel root | `clinical-coding-panel` |
| Safety banner | `cc-safety-banner` |
| Version bar | `cc-version-bar` |
| Search input | `cc-search-input` |
| Billable-only toggle | `cc-search-billable` |
| Search submit | `cc-search-submit` |
| Result count | `cc-result-count` |
| Results list | `cc-results` |
| One result row | `cc-result-<code>` |
| Favorite toggle | `cc-fav-toggle-<code>` |
| Left rail root | `cc-rail` |
| Specialty tab | `cc-specialty-<tag>` |
| Bundle section | `cc-bundle-<tag>` |
| Bundle code button | `cc-bundle-code-<code>` |
| Favorites list | `cc-favorites-list` / `cc-favorites-empty` |
| Recent searches | `cc-recent-searches` |
| Detail panel | `cc-detail` / `cc-detail-empty` |
| Specificity block | `cc-specificity-flags` |
| Support hints | `cc-support-hints` |
| One hint | `cc-hint-<id>` |
| Child codes | `cc-detail-children` |
| Detail audit row | `cc-detail-audit` |
| Admin audit strip | `cc-admin-audit` |
| One version in admin table | `cc-admin-version-<id>` |

## Role gating (frontend hints, server is authoritative)

- Specialty quick-picks, search, code detail, recent searches: all roles.
- Favorites toggle: `admin` and `clinician` only. Reviewer and
  front-desk see the star but pressing it returns `403` from the
  server.
- Admin audit strip: `admin` only; frontend hides the component
  when `role !== "admin"`.

## Accessibility

- Specialty buttons are `role="tab"` with `aria-selected`.
- Search input has `aria-label="ICD-10-CM search"`.
- Search live-region `role="alert"` for errors and `aria-live="polite"`
  for the result count.
- All chips are informational and use non-color signals (text label
  and border).
