# ChartNav Brand Guidelines Deck

> Brand standards for any deck, doc, page, or pitch. 9 slides.
> Authoritative for tone and approved language. **Internal-only**
> — pairs with `chartnav-approved-claims-language.md` (forbidden
> phrase catalog) and the deck master kit.

**Audience:** internal — operators, future ChartNav employees,
partner agencies producing co-branded ChartNav material.
**Purpose:** lock the canonical phrasing so every deck, page,
caption, and voice-over carries the same provider-control safety
contract.
**CTA / next step:** read this before producing any ChartNav copy.

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

## Slide 4.5 — Clinical Signal Filtering language

- **Title:** Talk about Clinical Signal Filtering this way.
- **Content (approved phrasing):**
  - "Clinical Signal Filtering"
  - "Filters conversation. Captures findings. Builds the diagram."
  - "separates casual speech from clinical findings"
  - "flags uncertainty for provider review"
  - "proposes retinal diagram annotations the provider applies,
    edits, or rejects"
  - "ignored chatter / clinical finding / uncertain phrase /
    proposed diagram annotation"
  - "the provider applies, edits, or rejects every proposal
    before anything is saved or finalized"
- **Speaker notes:** Clinical Signal Filtering is the prime
  buyer-facing differentiator. Use the headline three-line cadence
  whenever space allows.
- **Visual:** four-row card showing the four classifications
  (ignored chatter / clinical finding / uncertain phrase /
  proposed annotation).

## Slide 5 — Banned claims

- **Title:** Never use.
- **Content:**
  - HIPAA compliant
  - HIPAA certified
  - SOC 2 certified
  - FDA cleared
  - HITRUST certified
  - certified EHR
  - autonomous diagnosis
  - automatic diagnosis
  - guaranteed accuracy
  - guaranteed documentation accuracy
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
  - AI draws automatically
  - AI decides
  - AI diagnosis
  - automatic charting
  - hands-free diagnosis
  - hands-free charting
- **Speaker notes:** Every banned phrase has an approved
  replacement in the substitution table inside
  `chartnav-approved-claims-language.md`.
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
