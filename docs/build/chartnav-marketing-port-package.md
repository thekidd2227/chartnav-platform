# ChartNav — marketing repo port package

**Audience:** the team owning the ChartNav marketing/website
repo. This is the clean handoff for Clinical Signal Filtering +
Retinal Diagram Assist content.

**Source-of-truth files in `chartnav-platform/docs/`:**

- [`sales/chartnav-product-page-copy.md`](../sales/chartnav-product-page-copy.md) — drop-in section copy + video-placeholder spec
- [`sales/chartnav-clinical-signal-filtering-one-pager.md`](../sales/chartnav-clinical-signal-filtering-one-pager.md)
- [`sales/chartnav-clinical-signal-filtering-demo-script.md`](../sales/chartnav-clinical-signal-filtering-demo-script.md)
- [`sales/chartnav-retinal-diagram-video-clips.md`](../sales/chartnav-retinal-diagram-video-clips.md)
- [`user-guides/clinical-signal-filtering.md`](../user-guides/clinical-signal-filtering.md)
- Export-ready (PDF / presentation / paste) versions in [`../export/`](../export/)

If anything below contradicts those docs, those docs win.

---

## 0. Hard rules — do not violate during port

These claims are **not allowed** anywhere on the marketing site,
deck, or video captions. Every doc above explicitly negates
them; please keep them negated when you port.

- Not "the AI diagnoses." → "ChartNav surfaces findings; the
  provider diagnoses, treats, and signs."
- Not "100% accurate" / "perfect transcription." → "The
  product surfaces uncertainty by design."
- Not "certified EHR." → "ChartNav is a clinical workflow
  surface, not a certified Electronic Health Record."
- Not "autonomous charting." → "Every persisted artifact has
  a provider-approval step."
- Not "replaces the scribe." → "Provider-assist."

If a draft, a sales page test, or a CTA experiment drifts
toward any of these, route through clinical review before
shipping.

---

## 1. Section block to port

The full copy block lives in
[`sales/chartnav-product-page-copy.md`](../sales/chartnav-product-page-copy.md).
Port verbatim. The structure:

```
[ Eyebrow ]                Clinical Signal Filtering
[ H2 ]                     Filters conversation. Captures findings.
                           Builds the diagram.
[ Lede paragraph ]         (drop-in copy, ~70 words)
[ Feature bullets ]        5 bullets
[ Worked example block ]   Doctor says: ... ChartNav separates: ...
[ Trust strip ]            Provider stays in control...
```

When porting:

- Use the page's existing H2 component (do not introduce a new
  H1 inside the section).
- Keep the worked-example block visually distinct from the
  lede — a card / quote / inset, not a paragraph blob.
- Mobile: stack the example block; bullets become single-column.
- Do **not** animate any heading, nav, footer, or form input.
  Subtle in-section motion (e.g. an annotation appearing) is
  acceptable only if it ships with the video clips, not as a
  perpetual layout shift.

## 2. Video placeholder specs (3 slots)

Ship these as **stable**, labeled placeholder cards now.
Replace with MP4 / WebM / GIF later without touching layout.

Each placeholder should:

- Render at a 16:9 aspect ratio.
- Use the existing card / button component if available;
  otherwise fall back to a CSS box matching adjacent product
  feature cards (same border, radius, spacing).
- Be a stable, server-rendered element — not lazy-mounted —
  so SEO crawlers see the label text.
- Be replaceable by swapping inner content for a video embed
  with no surrounding-layout changes.

| Slot | Label                                  | Caption                                        | File swap                                     |
| ---- | -------------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| 1    | `Video — Clinical Signal Filtering`    | 25 sec · chatter, clinical text, uncertainty   | `clip-1-clinical-signal-filtering.mp4`        |
| 2    | `Video — AI Proposed Retinal Diagram`  | 25 sec · proposals appear on OD/OS canvases    | `clip-2-ai-proposed-retinal-diagram.mp4`      |
| 3    | `Video — Provider Review and Save`     | 30 sec · apply, reject, save to the chart      | `clip-3-provider-review-and-save.mp4`         |

Poster frames pulled from
`apps/web/tests/marketing-capture.mjs` output in the product
repo (`qa/screenshots/marketing/`). Do not use external stock
footage.

## 3. CTA placement guidance

Treat this as a guide, not a contract. The marketing repo
owns its own conversion patterns; these are recommendations
that match how the section is structured.

- **Primary CTA — adjacent to the worked example** ("See it
  in a 5-minute demo" or your equivalent calendar link).
  Reason: by the time a buyer has read the worked example
  they understand what ChartNav does and want to see it move.
- **Secondary CTA — under the trust strip** ("Read the
  one-pager" linking to a hosted PDF of
  `chartnav-clinical-signal-filtering-one-pager.pdf` from
  `docs/export/`). Reason: technical / clinical reviewers
  prefer reading first.
- **Tertiary CTA — bottom of the section** ("Talk to our
  team" or contact form). Use the page's existing form
  component. Do **not** animate the form inputs. Do **not**
  add a chat widget that overlays the worked example.

CTAs that already exist on the page **stay**. Do not silently
remove an existing CTA to make room for video.

## 4. Where each section should go

| Asset                                                      | Page                                                                                                            |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Section block (eyebrow → H2 → lede → bullets → example)    | **Homepage** (mid-page, after the hero, before pricing). And **Platform page** as a feature deep-dive section. |
| Video Slot 1 (Clinical Signal Filtering)                   | **Homepage** alongside the section block (above the fold once scrolled to the section).                       |
| Video Slot 2 (AI Proposed Retinal Diagram)                 | **Platform page** — feature deep-dive section.                                                                  |
| Video Slot 3 (Provider Review and Save)                    | **Platform page** under the worked example, paired with the trust strip.                                       |
| One-pager PDF (`docs/export/`)                             | **Demo / assessment page** as a downloadable resource. Optional: gated by email.                                |
| Demo script (`docs/export/`)                               | **Internal sales enablement** only. Do not publish externally.                                                  |
| User guide (`docs/user-guides/clinical-signal-filtering.md`) | **Customer help center** under "Clinical features → Clinical Signal Filtering."                               |

### Page-by-page port checklist

#### Homepage

- [ ] Add the section block after the hero, before the
      pricing/social-proof rail.
- [ ] Place Video Slot 1 next to the section block (right
      column on desktop, below on mobile).
- [ ] Primary CTA points to the demo / assessment page.
- [ ] H1 of the homepage is unchanged.
- [ ] Lighthouse mobile score does not regress > 2 points.

#### Platform page

- [ ] Add the same section block as a feature deep-dive
      anchor (`#clinical-signal-filtering`).
- [ ] Place Video Slot 2 after the lede paragraph.
- [ ] Place Video Slot 3 after the worked example.
- [ ] Add a "What it does NOT do" inset using the bullet list
      from the user guide (4–6 negations). This protects the
      buyer's expectation and the company.
- [ ] Anchor in the page's TOC: "Clinical Signal Filtering."

#### Demo / assessment page

- [ ] Surface the one-pager PDF as a downloadable resource.
- [ ] Pre-fill the calendar booking form's "what would you
      like to see?" field with "Clinical Signal Filtering +
      retinal diagram demo" (string matching the demo script
      title).

## 5. SEO + page hygiene

- [ ] Page H1 of the host page is unchanged. The section is
      an H2.
- [ ] Canonical URL unchanged.
- [ ] `<title>` and `<meta description>` updated to mention
      *Clinical Signal Filtering*. Suggested copy from the
      product-page-copy doc:

      ```
      <title>ChartNav — Clinical Signal Filtering for ophthalmology charting</title>
      <meta name="description" content="ChartNav separates clinical findings from conversational chatter, flags uncertainty for provider review, and proposes retinal diagram annotations the provider explicitly approves before they reach the chart." />
      ```
- [ ] Schema.org `SoftwareApplication` block, if present,
      gets an `applicationSubCategory` of "Clinical Workflow"
      not "Electronic Health Record."
- [ ] No new top-level routes added.
- [ ] All existing CTAs preserved.
- [ ] Mobile: section renders single-column; example block
      doesn't horizontal-scroll.
- [ ] Core Web Vitals: video placeholders ship with width /
      height and `loading="lazy"` on the video swap; do not
      autoplay with sound.

## 6. Validation steps for the marketing repo's CI

When the port lands in the marketing repo:

- [ ] `npm run build` (or framework equivalent) completes.
- [ ] Lighthouse mobile + desktop run on staging. No regression
      > 2 points on Performance / SEO / Accessibility.
- [ ] Visual diff (Percy / Chromatic / equivalent) shows the
      new section appearing without breaking adjacent layout.
- [ ] Crawl the homepage + platform page and confirm:
      `Clinical Signal Filtering` appears in the rendered
      HTML (not only in client-side hydration).
- [ ] Run an overclaim grep on the rendered output:

      ```
      grep -niE "diagnoses|certified ehr|100% accurate|fully autonomous|replaces the (scribe|provider|doctor)|perfect transcription" dist/
      ```
      Expected hit count: only inside negation phrases ("not
      certified EHR", etc.). Any positive hit is a regression.

## 7. Open questions for the marketing team

These are decisions only you can make; flag them to clinical
review before publishing.

1. **Single feature page vs. tab in Platform page?** Recommend
   tab to start; promote to standalone page once we have
   3+ customer videos.
2. **One-pager gating.** Recommend ungated for the first 60
   days to maximize reach, then revisit based on form-fill
   metrics.
3. **Video clip rollout cadence.** Recommend ship Slots 1+3
   first (the highest-converting pairing per the demo
   script), then Slot 2 a week later.
4. **Compliance review sign-off** — name the clinical or
   regulatory reviewer for the published copy. Add their
   approval as a comment on the marketing-repo PR.

## 8. Handoff checklist

- [ ] Marketing-repo owner has read this file end-to-end.
- [ ] Compliance reviewer named.
- [ ] Section block ported to homepage and platform page.
- [ ] Three video placeholders rendered in the right slots.
- [ ] One-pager PDF uploaded to the demo / assessment page.
- [ ] Customer help center has the user guide live.
- [ ] Marketing-repo CI is green (build + Lighthouse + visual
      diff + overclaim grep).
- [ ] Internal sales enablement has the demo script behind
      the auth wall.

When all checkboxes are ticked, the port is complete.
