# Doc Artifact Pipeline

## Purpose

The living docs in `docs/build/*` and `docs/diagrams/*` are the source
of truth. The final consolidated artifacts in `docs/final/` are always
rebuildable from those sources — no hand edits.

## Source / output layout

```
docs/
├── build/        # human-maintained markdown — source of truth
├── diagrams/     # Mermaid sources (fenced in markdown)
└── final/
    ├── chartnav-workflow-state-machine-build.html   # generated
    └── chartnav-workflow-state-machine-build.pdf    # generated
```

## Builder

File: `scripts/build_docs.py`

- Pure Python, no external deps beyond the standard library.
- Resolves paths relative to the script, so the same invocation works
  locally and in CI.
- Parses a small markdown subset (headings, fenced code, tables, bullet
  lists, inline `code`, `**bold**`) directly to HTML.
- Mermaid fences are passed through verbatim into `<div class="mermaid">`
  blocks; the HTML imports Mermaid from a CDN and renders on load.
- Writes `docs/final/chartnav-workflow-state-machine-build.html`.
- Generates the PDF via headless Chromium (`--headless=new --print-to-pdf`).
  Selection order:
  1. `CHARTNAV_PDF_BROWSER` env var if set (used by CI with `chromium-browser`).
  2. macOS Chrome at `/Applications/Google Chrome.app/...`.
  3. Chromium in a standard app bundle.
  4. `chromium-browser`, `chromium`, `google-chrome`, `chrome` on `PATH`.
- If no browser is available, falls back to `reportlab` for a plain-text
  PDF so CI never silently produces a zero-byte artifact.

## Run it

Locally:

```bash
python scripts/build_docs.py          # or:  make docs
```

In CI: the `docs` job in `.github/workflows/ci.yml` installs
`chromium-browser` via apt, runs the builder with
`CHARTNAV_PDF_BROWSER=chromium-browser`, and uploads the resulting
HTML + PDF as a `chartnav-docs-final` artifact. The upload step is
configured with `if-no-files-found: error`, so a silent generation
failure fails the build.

## Sections consumed (in order)

1. Executive summary (inlined in the builder)
2. `docs/build/01-current-state.md`
3. `docs/build/02-workflow-state-machine.md`
4. `docs/build/03-api-endpoints.md`
5. `docs/build/04-data-model.md`
6. `docs/build/05-build-log.md`
7. `docs/build/06-known-gaps.md`
8. `docs/build/07-auth-and-scoping.md`
9. `docs/build/08-test-strategy.md`
10. `docs/build/09-ci-and-deploy-hardening.md`
11. `docs/build/10-doc-artifact-pipeline.md`
12. `docs/diagrams/system-architecture.md`
13. `docs/diagrams/encounter-status-machine.md`
14. `docs/diagrams/er-diagram.md`
15. `docs/diagrams/api-data-flow.md`

If a source file is missing, the builder emits an inline
`*missing: <path>*` marker rather than crashing — a broken diagram or
an undeleted section shows up immediately in the rendered output and in
the CI artifact.

## Why not a heavier stack

- No MkDocs / Docusaurus / Sphinx — those require a theme + build
  config we'd have to maintain. We currently just need the 10-page PDF
  to stay fresh.
- No pandoc dependency — keeps the CI image lean and the local
  experience `python` + a headless browser (which most devs already
  have).
- If we grow beyond a single consolidated artifact (e.g. a hosted docs
  site), this builder is easy to retire because the sources are already
  plain markdown.
