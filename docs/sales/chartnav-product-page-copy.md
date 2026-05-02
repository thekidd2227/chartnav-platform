# ChartNav — product page copy: Clinical Signal Filtering + retinal diagram

This file is the canonical copy source for the
**"Filters conversation. Captures findings. Builds the diagram."**
section on the ChartNav marketing/product page.

The marketing site lives in a separate repository, not in
`chartnav-platform`. This doc holds:

1. The exact copy to lift into the marketing page.
2. A spec for non-breaking video placeholders so the marketing
   team can stub the section now and swap in MP4/WebM/GIF later
   without re-doing layout, SEO metadata, or routing.

The product itself (in `apps/web`) does not have a public marketing
landing page — `apps/web/index.html` is the SPA shell only. Do
not add marketing content to the SPA shell.

---

## Section block (drop-in copy)

### Section eyebrow

```
Clinical Signal Filtering
```

### Section H2

```
Filters conversation. Captures findings. Builds the diagram.
```

### Lede paragraph

ChartNav's AI scribe is built for real clinical speech — not perfect
dictation scripts. It separates casual phrases like "hold on,"
"next patient," or "let me check" from actual medical findings.
Clinical findings are extracted into structured data, uncertain
phrases are flagged for review, and retinal diagram annotations
are proposed for provider approval. **Nothing is saved to the
chart until the provider approves it.**

### Feature bullets

- Ignores non-clinical chatter
- Extracts structured retinal findings
- Flags uncertainty before charting
- Proposes retinal diagram annotations
- Saves only provider-approved chart artifacts

### Worked example block

> **Doctor says:**
> "Okay hold on… OD drusen in the macula… maybe OS flame
> hemorrhage inferior."
>
> **ChartNav separates:**
>
> - **Ignored chatter:** "Okay hold on"
> - **Clinical finding:** "OD drusen in the macula"
> - **Uncertain phrase:** "maybe OS flame hemorrhage inferior"
> - **Proposed diagram annotation:** provider review required

### Trust strip (one-liner under the example)

```
Provider stays in control. Nothing reaches the chart without explicit approval.
```

---

## What this copy does NOT claim

These claims are intentionally absent. Do not add them in any
later edit pass.

- Not "the AI diagnoses." ChartNav surfaces findings; the
  provider diagnoses.
- Not "100% accurate" / "perfect transcription." The product
  surfaces uncertainty by design.
- Not "certified EHR." ChartNav is a clinical workflow surface,
  not a certified Electronic Health Record.
- Not "autonomous charting." Every persisted artifact has a
  provider-approval step.
- Not "replaces the scribe." Positioning is provider-assist.

If marketing copy starts to drift toward any of these, route it
through clinical for review first.

---

## Voice and visual constraints

- Premium, clinical, calm. No exclamation marks, no emoji except
  the single ✨ already used inside the product UI to mark the
  scribe entry point.
- Tone: tools-for-experts, not consumer SaaS.
- Do NOT animate header, nav, footer, or form input elements.
  Subtle in-section motion (a single annotation appearing on a
  diagram) is OK if it ships *with* the video clips, not as a
  perpetual layout shift.
- Mobile: example block stacks; bullets become single-column;
  worked-example block remains visually distinct from the lede.
- Keep heading hierarchy continuous with the surrounding page —
  do not introduce a stray H1 inside this section.

---

## Video placeholder spec (workstream 7)

Add three placeholder slots in this order, after the worked
example. Each slot must:

- Render as a labeled card-shaped box at a 16:9 aspect ratio.
- Use the existing button/card component if available; otherwise
  fall back to a CSS box with the same border, radius, and spacing
  as adjacent product feature cards.
- Be a stable element (not lazy-mounted) so SEO crawlers see the
  label text.
- Be replaceable later by swapping the inner content for an MP4 /
  WebM / GIF embed without changing the surrounding layout.

### Slot 1

```
Label: Video — Clinical Signal Filtering
Placeholder caption: 25 sec · how chatter, clinical text, and uncertainty separate
File to swap in later: clip-1-clinical-signal-filtering.mp4
```

### Slot 2

```
Label: Video — AI Proposed Retinal Diagram
Placeholder caption: 25 sec · proposals appear on OD/OS canvases
File to swap in later: clip-2-ai-proposed-retinal-diagram.mp4
```

### Slot 3

```
Label: Video — Provider Review and Save
Placeholder caption: 30 sec · apply, reject, save to the chart
File to swap in later: clip-3-provider-review-and-save.mp4
```

When wiring real video, use poster frames pulled from the live
app (the `apps/web/tests/marketing-capture.mjs` Playwright script
already produces marketing-grade stills under
`qa/screenshots/marketing/`). Do not use external stock footage.

---

## SEO + page hygiene checklist (applies whether marketing site lives in next-forge, Astro, plain HTML, etc.)

- [ ] H1 of the page itself is preserved; this section is an H2.
- [ ] Canonical URL unchanged.
- [ ] `<title>` and `<meta description>` updated to mention
      *Clinical Signal Filtering* without overpromising.
- [ ] No new top-level routes added unless intentional.
- [ ] CTAs unchanged or strengthened (do not silently remove
      existing CTAs to make room for video).
- [ ] Mobile: section renders in a single column without the
      example block overflowing.
- [ ] Page does not regress Core Web Vitals — videos lazy-load,
      placeholders use the existing card component, no
      layout-shifting hero animations.

---

## Suggested `<title>` / `<meta description>` (drop-in)

```
<title>ChartNav — Clinical Signal Filtering for ophthalmology charting</title>
<meta name="description" content="ChartNav separates clinical findings from conversational chatter, flags uncertainty for provider review, and proposes retinal diagram annotations the provider explicitly approves before they reach the chart." />
```
