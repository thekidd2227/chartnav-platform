# ChartNav Presentation Typography

> Type stack + size hierarchy for every ChartNav presentation.

## Stack

- **Primary:** Inter (loaded by the product at `apps/web/index.html`).
- **Fallback:** Calibri — the safe Mac/Windows default. PowerPoint
  will substitute Calibri automatically if Inter isn't installed
  on the presenter's machine.

Do not introduce a third typeface. The product UI is Inter; the
decks match.

## Hierarchy

| Role | Size (pt) | Weight | Color (default) |
|---|---|---|---|
| Deck title (cover) | 36 | 700 | `#0F172A` |
| Section divider title | 32 | 700 | `#0B6E79` |
| Slide title | 28 | 700 | `#0F172A` |
| Slide subtitle | 18 | 400 | `#475569` (italic) |
| Body — large | 16 | 400 | `#0F172A` |
| Body — default | 14 | 400 | `#0F172A` |
| Big number (pricing) | 48 | 700 | `#0F172A` (teal panel) / `#FFFFFF` (highlighted tier) |
| Eyebrow / label | 12 | 700 | `#0B6E79` |
| Caption | 11 | 400 | `#64748B` |
| Footer / slide number | 10 | 400 | `#64748B` |

## Spacing

- **Title strip top:** 0.5 in.
- **Title rule:** a 0.04 in teal accent bar 0.05 in below the title.
- **Body region:** starts at 1.4 in (0.55 in below the title rule).
- **Footer strip top:** 7.0 in (slide is 16:9 widescreen, 7.5 in tall).
- **Card corner radius:** 0.08 in.
- **Card-to-card gap:** 0.15–0.25 in.

## Rules

1. **Bold the slide title, never the body.** Body bullets carry weight from layout, not from font weight.
2. **Italic only for two purposes:** the slide subtitle, and direct quotes from a doctor (the Clinical Signal Filtering quote band).
3. **Never use ALL CAPS.** Use case where appropriate; the Inter quotient handles emphasis.
4. **Maximum 7–8 bullets per slide.** Anything more belongs in two slides or in a feature-card layout.
5. **Speaker notes** travel with the PPTX as PowerPoint speaker notes (per slide). They are read by the presenter, not shown on screen.
