# ChartNav Presentation Brand Usage

> Rules for how the ChartNav mark, logo, palette, and tone show
> up in generated presentations. Read alongside the
> brand-guidelines deck (`docs/decks/chartnav-brand-guidelines-deck.md`)
> and the approved-claims language doc.

## Mark + logo

- The full **logo** (mark + wordmark) appears on the cover slide
  only.
- The compact **mark** (two teal pulse ticks flanking a tall red
  bar) appears in the top-left header strip on every non-cover
  slide and again on the section divider layout.
- Both are reproduced as PptxGenJS shapes (no raster art) so the
  decks stay vector-clean at any size.
- The repo's source SVGs are at:
  - `apps/web/public/brand/chartnav-logo.svg`
  - `apps/web/public/brand/chartnav-mark.svg`
  - `apps/web/public/brand/chartnav-favicon.svg`

## Slide-level identity

- Every non-cover slide shows the deck title in the top header
  strip in `Eyebrow` style (12pt Muted) so a presenter can
  identify the source deck mid-presentation.
- Every slide shows the slide number (`N / total`) and the
  contact strip (`ChartNav · jeanmax@arivergroup.com ·
  chartnavmd.com`) at the bottom.
- A 0.08 in teal accent bar runs along the very top of every
  slide. Never break it.

## Color discipline

- **Teal (`#0B6E79`)** carries identity. Headings, accents,
  primary CTAs.
- **Pulse red (`#DC2626`)** is reserved for the boundary
  ("does not do") column and the logo cross. Never use it for
  safe-claims rule text.
- **No gradients. No drop shadows. No 3D effects.** The product
  UI is flat; the decks match.

## CTA discipline

- **One CTA per close slide.** The CTA panel is a full-width
  teal block with white text. Never two competing CTAs on the
  same slide.
- The contact strip below the CTA panel always reads:
  `jeanmax@arivergroup.com  ·  chartnavmd.com`.

## Audience routing

- The **operator demo deck** is internal-only — never present it
  to a buyer. The system warning slide appears at the top of the
  rendered PPTX.
- The **company deck**'s federal credibility slide (slide 8) is
  for federal-healthcare-adjacent audiences. Skip it for
  private-practice ophthalmology buyers.
- The **buyer demo deck** never references terminal commands,
  `?demo=1`, `make dev`, or repo paths. The Phase 17B
  CommercialDeckClaims test enforces this.

## Safe-claims contract

Every layout that touches the safe-claims contract (Safety dual-
column, Clinical Signal Filtering, the cover Audience strip)
preserves the canonical phrasing from
`docs/commercial/chartnav-approved-claims-language.md`.

Forbidden in slide copy — same list as Phase 17B:

- HIPAA-compliant / HIPAA-certified / SOC 2-certified / FDA-cleared / HITRUST-certified
- certified EHR
- autonomous diagnosis / automatic diagnosis
- guaranteed accuracy / guaranteed documentation accuracy
- automatic orders / auto-orders / order OCT
- submit referral / send referral / billing automation / coding automation
- send patient message / auto-message patients
- replaces a doctor / replaces providers
- production-ready for PHI / real patient data ready
- AI draws automatically / AI decides / AI diagnosis / automatic charting / hands-free diagnosis / hands-free charting / hands-off documentation

The generator reads the same markdown decks the Phase 17B claims
test scans, so any banned phrase that lands in the source decks
gets caught before generation.
