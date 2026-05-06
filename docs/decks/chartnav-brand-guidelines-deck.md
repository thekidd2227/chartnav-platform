# ChartNav Brand Guidelines Deck

> Brand standards for any deck, doc, page, or pitch. 8 slides.
> Authoritative for tone and approved language.

---

## Slide 1 — Cover

- **Title:** ChartNav brand guidelines.
- **Visual:** logo + word-mark.

## Slide 2 — Positioning

- **Title:** What ChartNav is.
- **Content:**
  - "ChartNav is an ophthalmology-specific clinical workflow
    assistant — provider-reviewed at every step."
- **Speaker notes:** Use this exact line. Don't paraphrase.
- **Visual:** big-text card.

## Slide 3 — Tone

- **Title:** How ChartNav talks.
- **Content:**
  - Conservative. Precise. Provider-respecting.
  - Active voice over passive.
  - Negative-assertion safety bullets allowed.
  - Marketing superlatives forbidden.
- **Visual:** 4-bullet card.

## Slide 4 — Approved language

- **Title:** Use these.
- **Content:**
  - "provider-reviewed"
  - "documentation support"
  - "ophthalmology-specific"
  - "controlled pilot"
  - "fake patient demo"
  - "draft / review / finalize"
  - "explicit provider review"
  - "Business Associate Agreement"
  - "security review"
  - "does not diagnose"
  - "does not create orders"
  - "does not send referrals"
  - "does not message patients automatically"
- **Visual:** two-column list.

## Slide 5 — Banned claims

- **Title:** Never use.
- **Content:**
  - HIPAA compliant
  - HIPAA certified
  - SOC 2 certified
  - certified EHR
  - autonomous diagnosis
  - automatic diagnosis
  - guaranteed accuracy
  - automatic orders
  - order OCT
  - submit referral
  - send referral
  - billing automation
  - coding automation
  - send patient message
  - replaces a doctor
  - production-ready for PHI
  - real patient data ready
- **Visual:** plain bullets.

## Slide 6 — Visual style direction

- **Title:** Visual rules.
- **Content:**
  - Brand color: #0B6E79 (teal).
  - Accent color: rgba(11,110,121,0.12).
  - Logo asset: `apps/web/public/brand/chartnav-logo.svg`.
  - Word-mark + tagline only on covers.
  - Inline SVG diagrams preferred over raster screenshots.
  - **No raster screenshots in the repo.**
- **Visual:** color swatch + logo.

## Slide 7 — Logo / color / font

- **Title:** Brand assets.
- **Content:**
  - Logo: `apps/web/public/brand/chartnav-logo.svg`.
  - Mark: `apps/web/public/brand/chartnav-mark.svg`.
  - Favicon: `apps/web/public/brand/chartnav-favicon.svg`.
  - Font: Inter (already loaded by `apps/web/index.html`).
- **Visual:** brand mark gallery.

## Slide 8 — Screenshot / video usage rules

- **Title:** When to capture, when not to.
- **Content:**
  - **Capture against fake demo data only.**
  - Reset between captures with
    `bash scripts/reset_demo_state.sh`.
  - Voice-over and captions must use approved-language list.
  - Forbidden phrasing on screen → re-record; do not edit around
    it.
  - **Captured media is NOT committed to the repo.** Lives in
    out-of-repo storage.
- **Speaker notes:** See
  `docs/website/chartnav-website-shot-list.md` and
  `docs/demo/chartnav-video-clip-shot-list.md`.
- **Visual:** plain bullets.
