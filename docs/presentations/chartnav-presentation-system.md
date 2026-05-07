# ChartNav Presentation System (Phase 17D)

> How the ChartNav markdown deck library at `docs/decks/` is
> converted into branded PPTX presentations on the operator's
> Desktop. Implementation lives at `tools/presentations/`.

---

## Why

Phase 17 + 17B locked the deck library as **Markdown source**.
The operator (Jean-Max) needs **real, polished presentations**
to walk into investor / buyer / partner meetings without a
manual conversion step. Phase 17D is that bridge — Markdown in,
branded PPTX out.

This phase is **content + tooling only**. No backend changes, no
schema, no website code, no auth. The repo carries the
Markdown source + the generator + the theme; the Desktop folder
carries the consumed PPTX outputs.

---

## What ships

### `tools/presentations/`

| File | Role |
|---|---|
| `package.json` | One direct dep: `pptxgenjs` (pure JS, no native libs). |
| `theme.js` | Palette + typography + slide dimensions. Pulled from `apps/web/src/styles.css`. |
| `brand/chartnavMark.js` | Reproduces the mark + logo as PptxGenJS shapes. No raster art committed. |
| `parseDeck.js` | Markdown → structured slide records. Tolerant of canonical `## Slide N — title` and section-style `##` / `###` decks (for the one-pager + demo-deck index). |
| `slideLayouts.js` | 10 reusable layouts: Cover, Section, Title+Bullets, Feature Cards, Clinical Signal Filtering, Workflow, Pricing, Safety Dual, CTA, Index. |
| `renderDeck.js` | Heuristic per-slide layout picker + PptxGenJS driver. |
| `generateAll.js` | Walks `docs/decks/` and writes every required PPTX into the Desktop folder. |

### `scripts/generate_chartnav_presentations.sh`

Standalone wrapper that ensures `tools/presentations/node_modules`
is installed and runs the JS driver. Override the destination
with `CHARTNAV_DESKTOP_DIR`.

### `scripts/export_chartnav_decks_to_desktop.sh`

Extended in Phase 17D to:

1. Add `01_Decks/Markdown_Source/`, `01_Decks/PPTX/`,
   `01_Decks/PDF/`, `02_One_Pagers/Markdown_Source/`,
   `02_One_Pagers/PPTX/`, and `10_Presentation_Assets/` to the
   subfolder list.
2. Redirect every deck Markdown copy into `Markdown_Source/`.
3. Copy `docs/presentations/*.md` into `10_Presentation_Assets/`.
4. Optionally chain the PPTX generator (skip with
   `CHARTNAV_SKIP_PPTX=1` for fast Markdown-only refreshes).

### `docs/presentations/`

| File | Role |
|---|---|
| `palette.md` | Authoritative palette tokens + use rules. |
| `typography.md` | Type stack, hierarchy, spacing rules. |
| `brand-usage.md` | When/where to use the mark/logo, audience routing, safe-claims rules. |
| `chartnav-presentation-system.md` | This doc. |

---

## How layout selection works

`renderDeck.js → pickLayout` walks each slide and picks a layout
in this order (most specific first):

1. **Demo-deck index** — the routing index slide (`when to use which`).
2. **Clinical Signal Filtering** — title or content matches the prime feature cadence.
3. **Pricing** — title contains `pricing`, `business model`, `cost`, `fee`.
4. **Safety dual** — title contains "what ChartNav is not", "buyer-safe non-goals", "boundaries", etc.
5. **Workflow** — title contains "workflow"/"seven explicit steps" or content has arrow-separated stages.
6. **CTA** — title contains "next step", "talk to us", "single CTA", "what we'd like".
7. **Section divider** — slide has a title but no content body.
8. **Feature cards** — 3–8 bullets where most are headline-and-body pairs (contain `—` or bold prefix).
9. **Title + bullets** — default fallback.

The cover slide always uses `drawCover` for slide 1. Slide
numbering, header strip, and footer strip are added by every
layout via the `drawChrome` helper.

---

## How to regenerate

From the repo root on the operator's Mac:

```
bash scripts/generate_chartnav_presentations.sh
```

Or chain it from the existing Desktop export:

```
bash scripts/export_chartnav_decks_to_desktop.sh
```

The export script will install `tools/presentations` deps on the
first run and skip them on subsequent runs.

To skip PPTX generation when only the Markdown copies need to
refresh:

```
CHARTNAV_SKIP_PPTX=1 bash scripts/export_chartnav_decks_to_desktop.sh
```

---

## What is generated, where

Every required deck → one `.pptx` file at:

| Deck | Output path |
|---|---|
| 16 deck PPTXs (investor, sales, demo index, buyer demo, operator demo, customer pitch, company, roadmap, brand, educational, financial, marketing, project proposal, agency, elevator, long sales) | `01_Decks/PPTX/<deck-id>.pptx` |
| One-page sales | `02_One_Pagers/PPTX/chartnav-one-page-sales-deck.pptx` |

17 PPTX files total (the 15 originals + the buyer-demo and operator-demo decks introduced in Phase 17B).

---

## What is NOT generated

- **PDF output is deferred.** Pure-JS PPTX-to-PDF requires a
  heavy LibreOffice headless dependency. The operator opens the
  PPTX in PowerPoint or Keynote and exports PDFs manually if
  needed. The `01_Decks/PDF/` directory is created empty so PDFs
  exported manually have a stable home.
- **Binary screenshots / video clips** — captured out-of-repo per
  the existing shot lists. Phase 17D does not commit any binary
  media.
- **A separate marketing-site renderer.** The public website is
  the React app at `apps/web/`; Phase 17D doesn't touch it.

---

## Safety contract preservation

The generator reads exactly the same Markdown sources the Phase
17B `CommercialDeckClaims` vitest scans. Any banned phrase that
slips into a source deck is caught by the existing claims
contract before reaching the generator — no separate
sanitization step in `tools/presentations/`.

The generator also preserves:

- The deck's Audience / Purpose / CTA front-matter — surfaced on
  the cover slide.
- Speaker notes — travel as PowerPoint speaker notes per slide.
- The "What ChartNav does NOT do" boundary copy — rendered as a
  full red-trim column on the safety-dual layout.

---

## Known limitations

- **Layout heuristics are not a full markdown renderer.** Long
  paragraphs, nested bullets, and tables may render as flat
  bullet lists. If a slide needs a specific visual treatment that
  the existing layouts can't express, edit the deck source to
  match an existing layout's shape.
- **Inter font not embedded.** PowerPoint will substitute Calibri
  on machines that don't have Inter installed. The visual feel
  is very close.
- **Speaker notes attach per slide**, not per slide-section. If
  a slide has multi-line speaker notes in source, they are
  joined with a single space.

---

## Phase 18 candidate

Phase 18 is **first paid pilot or paid customer** — operations
work, not new product. The Phase 17 + 17B + 17D output (markdown
decks + branded PPTX + Desktop folder + .command launchers) is
the inventory Phase 18 sells from.

A small Phase 17E might add a JSON layout-override file so
specific slides can opt into a non-default layout without changing
the heuristic — deferred until the heuristic actually misroutes
a slide in real use.
