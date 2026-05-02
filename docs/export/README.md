# `docs/export/` — copy-paste-ready ChartNav assets

Clean, single-purpose files designed to be lifted into other
surfaces (marketing site, PDF builder, slide deck) without any
internal-only commentary.

| File                                     | Purpose                                                         |
| ---------------------------------------- | --------------------------------------------------------------- |
| [`product-page-section.md`](product-page-section.md) | Drop-in section copy for the marketing/product page. |
| [`one-pager-print.md`](one-pager-print.md) | One-pager body, formatted for clean PDF rendering. |
| [`demo-script-presentation.md`](demo-script-presentation.md) | Demo script, formatted as a presentation deck outline. |

These are **derived** from the canonical sources in
`docs/sales/` and `docs/user-guides/`. Edits to the canonical
sources should be propagated here when the wording shifts.
Edits made directly here without updating the source will be
overwritten the next time the docs are regenerated.

**Naming convention** for downstream files:

- `chartnav-product-page-section.html` (when ported to the marketing site)
- `chartnav-clinical-signal-filtering-one-pager.pdf` (when exported to PDF)
- `chartnav-clinical-signal-filtering-demo.{key,pptx,pdf}` (presentation export)

**Hard rules** for any file under this directory:

- No autonomous-diagnosis language.
- No certified-EHR language.
- No "perfect" or "100% accurate" language.
- Provider-in-the-loop language present in every file.
- No internal-only links (no Notion, Slack, internal Jira).
