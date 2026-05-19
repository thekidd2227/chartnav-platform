# ChartNav Website Proof Upgrade + Conversion Layer (Phase 16)

Phase 16 upgrades the public-facing ChartNav website so it reflects
the actual product built through Phases 6–15. Goal: a buyer should
understand the real ChartNav workflow in under 60 seconds — what it
does, why it is ophthalmology-specific, what the provider controls,
what ChartNav does **not** do, and how to request a demo or start a
pilot conversation.

This is a **website proof / conversion phase**. It is **not** a new
clinical feature, **not** a backend change, **not** orders / coding /
referrals / patient messaging, **not** EHR integration, **not** a
commercial-deck library, **not** desktop demo packaging, and **not**
unsupported compliance marketing.

**No new clinical automation. No backend changes. No new schema. No
external LLM. No real-PHI claim. No unsupported HIPAA / SOC 2 /
certified-EHR claim. No binary media checked into the repo.**

---

## Site path that was upgraded

There is no separate marketing site (no `apps/web/chartnavmd-site`,
no `apps/website`). The public ChartNav website is the React app at
`apps/web/`, which is what Vercel deploys per PR.

A new opt-in route was added rather than redesigning the existing
workspace:

- **`/landing` or `?intro=1`** — renders the new public landing /
  proof page (`LandingPage.tsx`).
- **everything else** — renders the existing authenticated workspace
  (`App.tsx`) unchanged.

The opt-in pattern matches Phase 15's Guided Demo Mode (`?demo=1`).
Buyers visit `https://<deploy>/?intro=1`; existing providers land on
the workspace they already know.

## Pages changed

A single new public route + tests + docs.

| Path | Change | Notes |
|---|---|---|
| `apps/web/src/LandingPage.tsx` | **A** | Hero / workflow / ophthalmology / provider-control / modules / before-after / demo-pilot / non-goals / footer |
| `apps/web/src/main.tsx` | M | +6 lines: import + `/landing` and `?intro=1` route gate |
| `apps/web/src/styles.css` | M | Pure append: `.landing-page__*` CSS classes |
| `apps/web/src/test/WebsiteProofUpgrade.test.tsx` | **A** | 18-test vitest suite (sections, CTAs, SVG diagrams, modules, before/after, non-goals, claims contract) |
| `scripts/check_website_claims.sh` | **A** | Lightweight pre-deploy claims verifier |
| `docs/chartnav-website-proof-upgrade-conversion-layer.md` | **A** | Phase 16 top-level contract (this file) |
| `docs/website/chartnav-website-shot-list.md` | **A** | Future screenshot / video shot list (no media in repo) |
| `docs/chartnav-patient-chart-foundation.md` | M | Pure append: Phase 16 section |

## Messaging strategy

The page leads with positioning, drops a safety line in the hero,
walks through the seven-stage workflow, anchors the
ophthalmology-specific proof, explains the draft / review / finalize
state model with an inline SVG diagram, lists eight built modules,
contrasts before / with-ChartNav, surfaces the demo + pilot CTAs,
and closes with a buyer-safe non-goals list.

The hero positioning sentence:

> ChartNav is an ophthalmology-specific clinical workflow assistant
> — provider-reviewed at every step.

The hero safety line (asserted by the test suite):

> Provider-reviewed workflow support. ChartNav does not diagnose,
> create orders, send referrals, bill, or message patients
> automatically.

Every CTA on the page resolves to the same `contactHref` (default
`mailto:hello@chartnavmd.com`, overridable). No new intake-form
backend was invented.

## Feature proof map (Phases 6–15 → page sections)

| Phase / module | Where on the page |
|---|---|
| Phase 8 — AI scribe session lifecycle | Workflow stage 1, Module card "AI scribe session lifecycle" |
| Phase 6 — findings-to-retinal-diagram proposal review | Workflow stage 2, Module card "Retinal proposal review" |
| Phase 5B — OD/OS retinal drawing canvas | Workflow stage 3, Module card "OD/OS retinal drawing canvas", "Built for ophthalmology" section bullets |
| Phase 9 — provider-reviewed patient-friendly summaries | Workflow stage 4, Module card "Patient-friendly summary" |
| Phase 10 — provider-facing pre-visit brief | Workflow stage 5, Module card "Pre-visit clinical brief" |
| Phase 11 — provider action review queue | Workflow stage 6, Module card "Provider action review queue" |
| Phase 13 — demo-ready clinical workflow package | Module card "Guided demo mode" (Phase 15 superset)+ footer reference |
| Phase 14 — pilot readiness / deployment hardening | "Built for pilot conversations" section, footer reference to `docs/pilot/`, Module card "Pilot-readiness package" |
| Phase 15 — commercial demo delivery system | Workflow stage 7 ("Guided demo"), Module card "Guided demo mode", footer note about `?demo=1` opt-in |
| Phase 12 — end-to-end clinical workflow smoke review | Implicit — the workflow diagram is the same path Phase 12's integration tests exercise |

## Visual asset strategy

**No binary media is committed.** All visuals are inline SVG plus
CSS-styled text panels:

- **Workflow diagram** — inline `<svg>` with seven numbered stage
  nodes connected by a dashed line ending in an arrow. Each stage
  has its own `data-testid` for stable selectors.
- **Provider-control state diagram** — inline `<svg>` with three
  state boxes (Draft → Reviewed → Finalized) plus an immutability
  caption.
- **Module grid** — eight CSS cards.
- **Before / with-ChartNav comparison** — two CSS cards with bullet
  lists.
- **Brand mark** — the existing `apps/web/public/brand/chartnav-logo.svg`
  already in the repo. No new brand assets shipped.

A future screenshot / video plan lives at
`docs/website/chartnav-website-shot-list.md` — editorial only.

## CTA strategy

Every conversion path resolves to the same `contactHref`. The page
exposes three named primary CTAs and one secondary CTA:

| CTA | Test ID | Default destination |
|---|---|---|
| "Request a fake-patient demo" (hero) | `landing-cta-request-demo` | `mailto:hello@chartnavmd.com` |
| "See how the workflow works" (hero secondary) | `landing-cta-see-workflow` | in-page anchor `#workflow` |
| "Discuss a controlled ophthalmology pilot" (demo/pilot section) | `landing-cta-pilot-conversation` | `mailto:hello@chartnavmd.com` |
| "Review the provider-in-control workflow" (demo/pilot section) | `landing-cta-review-workflow` | `mailto:hello@chartnavmd.com` |

The destination is a prop (`contactHref`) so the deploy host can
override it to a real intake form without touching component code.
A claims test asserts that all named CTAs resolve to the same
configured destination.

## Safe claims rules

The Phase 16 contract reuses the heuristic from Phases 13 / 14 / 15:
forbidden positive claims (HIPAA compliant, certified EHR,
autonomous diagnosis, automatic orders, submit referral, billing
automation, send patient message, replaces a doctor, production-ready
for PHI, real patient data ready) are rejected unless they appear in
a clearly negative-assertion line ("does not …", "Not …",
"never …").

Approved phrasing on the page:

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

Forbidden phrasing on the page (asserted by tests):

- "HIPAA compliant" / "HIPAA certified"
- "SOC 2 certified"
- "certified EHR" (except inside the explicit "Not a certified EHR
  replacement" negative assertion)
- "autonomous diagnosis" / "automatic diagnosis" (except inside
  "Not autonomous diagnosis" negative assertion)
- "guaranteed accuracy"
- "automatic orders" / "order OCT"
- "submit referral" / "send referral" (except as a "does not"
  negation)
- "billing automation" / "coding automation"
- "send patient message" (except as a "does not" negation)
- "replaces a doctor"
- "production-ready for PHI"
- "real patient data ready"
- bare "OpenAI" / "Anthropic" / "GPT-N" / "external LLM certainty"

## Tests / scans

`apps/web/src/test/WebsiteProofUpgrade.test.tsx` — 18 specs:

- All 10 page sections render (page root, hero, workflow,
  ophthalmology, provider-control, modules, before/after,
  demo-pilot, non-goals, footer).
- Hero positioning + safety line + two CTAs + `contactHref` prop
  is honored across all primary CTAs.
- Inline workflow SVG renders with seven labeled stage nodes;
  the parallel ordered list mirrors them.
- Provider-control SVG renders Draft / Reviewed / Finalized state
  boxes with an immutability note.
- Safety-model `dl` lists the six rows
  (draft / review / finalize / audit / org-isolation / rbac).
- Eight module cards covering the Phase 6 / 8 / 9 / 10 / 11 / 13 /
  14 / 15 surfaces.
- Before / with-ChartNav comparison renders.
- Four "What ChartNav is not" bullet items render.
- Demo + pilot CTA row exposes both buttons.
- Forbidden positive marketing claims appear only in safe contexts
  (negative-assertion lines).
- No order / coding / referral / patient-message buttons.
- No autonomous-diagnosis or external-LLM positive claims.
- No `<img src>` points at a binary media file.
- Provider-review language is present and consistent across sections.
- Every link `href` is either an in-page anchor, the configured
  `contactHref`, the app link `/`, or a `tel:` / `mailto:`.
- The demo-pilot section explicitly states real PHI requires a BAA
  and a security review, and refers to the pilot readiness packet.

`scripts/check_website_claims.sh` — pre-deploy verifier that
confirms required files exist, the router gate is wired,
negative-assertion phrasing is present, no forbidden positive
claim slips outside a negative context, and no binary media is
checked in under `apps/web/public`. Verified locally to pass with
0 fail / 0 warn.

## Known limitations

- **Opt-in only.** A buyer must visit `?intro=1` (or `/landing`)
  to see the proof page. The default workspace URL still goes to
  the product app. A future phase could swap the default if the
  marketing path becomes primary.
- **One contact destination.** All named CTAs use the same
  `contactHref`. If the practice prefers different destinations
  per CTA (calendar booking vs. email), wire that in a follow-up
  by extending the prop into a CTA-keyed map.
- **No real screenshots.** The shot list at
  `docs/website/chartnav-website-shot-list.md` is editorial only.
  Producing actual media is out of scope for Phase 16.
- **No automated lighthouse / a11y sweep on the new page yet.**
  The existing `apps/web/tests/e2e/a11y.spec.ts` could add the
  landing page to its sweep in a follow-up phase.
- **No new client-side i18n.** The page is English-only.

## Phase 17 recommendation

Phase 17 candidates (NOT part of Phase 16):

1. **Default landing for unauthenticated users.** Decide whether
   the unauthenticated default should be the landing page or the
   identity selector. Today `?intro=1` is opt-in.
2. **Real intake form** — replace the `mailto:` CTA with a
   submit-handler hooked to the existing API or an external form
   service. Scope must include rate limiting + spam filtering.
3. **Lighthouse / a11y CI gate** — add the landing page to the
   axe-core Playwright sweep.
4. **Screenshot-based proof** — capture clean shots from the local
   demo (against fake data) and serve them from a CDN; do not
   commit binaries to the repo.
5. **Out-of-repo deck library** — the commercial deck explicitly
   listed as out of scope for Phase 13 + 14 + 15 + 16 still
   belongs out of repo.

Phase 17 must continue to obey the existing safety contract — no
new clinical features pulled forward, no autonomous diagnosis, no
orders / coding / referral / patient-messaging.
