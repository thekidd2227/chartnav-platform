<!--
  Product page section — drop-in copy.
  Source of truth: docs/sales/chartnav-product-page-copy.md
  Use: paste into the marketing/website repo's product page section.
  Wrap with whatever component the host page uses for "feature highlight"
  blocks. Do not introduce new H1s; this section is an H2.
-->

<div class="cn-section cn-section--clinical-signal-filtering">

<p class="cn-eyebrow">Clinical Signal Filtering</p>

## Filters conversation. Captures findings. Builds the diagram.

ChartNav's AI scribe is built for real clinical speech — not perfect
dictation scripts. It separates casual phrases like "hold on,"
"next patient," or "let me check" from actual medical findings.
Clinical findings are extracted into structured data, uncertain
phrases are flagged for review, and retinal diagram annotations
are proposed for provider approval. **Nothing is saved to the
chart until the provider approves it.**

- Ignores non-clinical chatter
- Extracts structured retinal findings
- Flags uncertainty before charting
- Proposes retinal diagram annotations
- Saves only provider-approved chart artifacts

<aside class="cn-worked-example">

**Doctor says:**

> "Okay hold on… OD drusen in the macula… maybe OS flame
> hemorrhage inferior."

**ChartNav separates:**

- **Ignored chatter:** "Okay hold on"
- **Clinical finding:** "OD drusen in the macula"
- **Uncertain phrase:** "maybe OS flame hemorrhage inferior"
- **Proposed diagram annotation:** provider review required

</aside>

<p class="cn-trust-strip">Provider stays in control. Nothing reaches the chart without explicit approval.</p>

<!--
  Video placeholder slots. Replace inner content with <video> embeds when files are ready.
  Do not change the surrounding card structure.
-->

<section class="cn-video-grid" aria-label="Product video clips">

<figure class="cn-video-card" data-clip="1">
  <div class="cn-video-placeholder">Video — Clinical Signal Filtering</div>
  <figcaption>25 sec · how chatter, clinical text, and uncertainty separate</figcaption>
  <!-- swap target: clip-1-clinical-signal-filtering.mp4 -->
</figure>

<figure class="cn-video-card" data-clip="2">
  <div class="cn-video-placeholder">Video — AI Proposed Retinal Diagram</div>
  <figcaption>25 sec · proposals appear on OD/OS canvases</figcaption>
  <!-- swap target: clip-2-ai-proposed-retinal-diagram.mp4 -->
</figure>

<figure class="cn-video-card" data-clip="3">
  <div class="cn-video-placeholder">Video — Provider Review and Save</div>
  <figcaption>30 sec · apply, reject, save to the chart</figcaption>
  <!-- swap target: clip-3-provider-review-and-save.mp4 -->
</figure>

</section>

</div>

<!--
  Suggested page-meta updates (host page <head>). Keep canonical URL the same.

  <title>ChartNav — Clinical Signal Filtering for ophthalmology charting</title>
  <meta name="description" content="ChartNav separates clinical findings from conversational chatter, flags uncertainty for provider review, and proposes retinal diagram annotations the provider explicitly approves before they reach the chart." />
-->
