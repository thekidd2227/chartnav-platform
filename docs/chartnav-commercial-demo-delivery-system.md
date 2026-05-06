# ChartNav Commercial Demo Delivery System (Phase 15)

Phase 15 converts the existing ChartNav clinical workflow foundation
into a polished, controllable, sales-demo-ready system. It is **not**
a new clinical feature, **not** EHR integration, **not** orders /
coding / referrals / patient messaging, **not** real-PHI support,
**not** desktop packaging, and **not** production enterprise
infrastructure.

The goal: ChartNav should feel like a coherent ophthalmology
platform during demos instead of a collection of features.

**No new clinical automation. No new schema. No new API surface.
No backend code changes. No external LLM. Fake demo data only.**

## What Phase 15 added

- **`apps/web/src/GuidedDemoMode.tsx`** — a sticky in-workspace
  orchestrator that renders a deterministic 8-step stepper, a
  prominent **DEMO MODE** badge, on-screen presenter cues, and
  Previous / Next / Reset controls. Gated on the URL query
  `?demo=1` (or `localStorage.chartnav.demoMode = "1"`); default
  off so normal providers never see it.
- **`scripts/reset_demo_state.sh`** — a small shell verifier that
  drops + re-seeds the local dev SQLite DB, prints a DevTools
  snippet for clearing browser-side demo state, and refuses to run
  if `DATABASE_URL` points at anything other than the local
  `sqlite:///<path>` default.
- **`docs/demo/chartnav-demo-operator-guide.md`** — recommended
  demo flow with Guided Demo Mode, click-by-click sequence,
  reset levels, fallback paths, what NOT to claim, provider-
  review talking points, AI governance talking points,
  ophthalmology workflow talking points, demo-timing guidance,
  pilot/security question routing, known weak spots.
- **`docs/demo/chartnav-demo-environment.md`** — local startup,
  reset levels, seeded credentials, fake-data structure,
  deterministic workflow expectations, troubleshooting, browser
  + recording recommendations (OBS / Zoom).
- **`apps/web/src/test/GuidedDemoMode.test.tsx`** — component
  unit tests asserting render gating, stepper behavior, advance /
  back / reset, safety bullets, badge, and absence of
  forbidden language.
- **`apps/web/src/test/DemoCommercialDelivery.test.tsx`** —
  package-level test asserting the new docs exist with required
  headings, the operator guide includes a "what NOT to claim"
  enumeration, and forbidden positive claims appear only in safe
  contexts.
- **`docs/chartnav-commercial-demo-delivery-system.md`** — this
  contract.
- **Foundation doc append** — Phase 15 section in
  `docs/chartnav-patient-chart-foundation.md`.

## Demo orchestration approach

Guided Demo Mode is **opt-in by URL**. A presenter visits
`http://127.0.0.1:5173/?demo=1` and sees the stepper above the
existing clinical panel stack. Normal providers visiting
`http://127.0.0.1:5173/` see exactly what Phase 13 ships — the
collapsed-by-default `DemoClinicalWorkflowGuide` plus the regular
clinical workspace.

Inside the stepper:

1. **Intake arrives** → confirm identity badge + patient context.
2. **Pre-visit brief appears** → click Generate; show source
   counts + data gaps.
3. **Visit begins** → paste source text into the Scribe panel;
   create the session.
4. **AI scribe session runs** → process → review → finalize.
5. **Retinal proposal generated** → generate proposals; apply one;
   save; sign.
6. **Provider review queue updates** → generate; accept / dismiss /
   complete.
7. **Patient-friendly summary generated** → create from finalized
   scribe; review; finalize.
8. **Workflow completed** → close on read-only finalized states.

Each step renders an on-screen `Cue:` line — the spoken cue the
presenter reads aloud. The cue is the same wording used in the
Phase 13 demo script, so the two surfaces stay in lockstep.

## Deterministic workflow philosophy

Phase 15 commits to determinism:

- Step labels and cues are fixed at compile time, in the closed
  `DEMO_STEPS` array.
- Step state lives in browser `localStorage` only. There is no API
  call. The stepper cannot drift between presenter and audience
  because there is no remote state to drift.
- There are no animations, hidden timers, or auto-advance
  behaviors. The presenter explicitly clicks **Next step**.
- The stepper does **not** click clinical-panel buttons, generate
  artifacts, or modify seeded data. It is a presenter overlay,
  not a workflow automation surface.
- A clean reset returns the stepper to Step 1 without touching
  clinical state. A full reset (`bash scripts/reset_demo_state.sh`)
  drops + re-seeds the local DB and prints a browser-side cleanup
  snippet.

## No real-PHI / demo boundary

The demo environment is **fake-data only**:

- All seeded names, MRNs, DOBs, NPIs are fake by construction
  (`scripts_seed.py`).
- The reset script refuses to run if `DATABASE_URL` is anything
  other than `sqlite:///<path>` — the script is dev-only.
- Local dev mode uses `CHARTNAV_AUTH_MODE=header`, which is
  trivially spoofable and **not safe** for any environment that
  may hold PHI. The pilot deployment guide
  (`docs/pilot/chartnav-pilot-deployment-guide.md`) gates real
  PHI on `bearer` auth + BAA + security review.
- The Guided Demo Mode badge prominently labels the experience
  "DEMO MODE · fake data only" so it cannot be confused with a
  real-data session.

## Safety guardrails

The stepper renders the same three negative-assertion safety
bullets that the Phase 13 demo guide and the Phase 11 action
queue surface:

- "ChartNav supports documentation and review workflows."
- "ChartNav does not diagnose, order, bill, send referrals, or
  message patients automatically."
- "Every clinical artifact requires explicit provider review
  before it is treated as final."

Forbidden marketing claims include each of the following:

- "HIPAA compliant"
- "certified EHR"
- "autonomous diagnosis"
- "automatic orders"
- "submit referral"
- "billing automation"
- "send patient message"
- "replaces a doctor"
- "external LLM certainty"

These are rejected by the Phase 15 docs-claims test unless they
appear inside a negative-assertion line, an enumerated
forbidden-phrase list, or a Q&A question heading whose answer is a
negative assertion. This is the same heuristic Phase 13 / 14 use;
Phase 15 does not weaken the contract.

## Remaining gaps before commercial pilots

Documented in the operator guide under "Known weak spots":

- The local stack must be running before the meeting.
- Browser cache can hide a fresh demo update — hard-refresh once.
- The action queue is empty on a clean reset until the scribe
  lifecycle has been run; the pre-visit brief shows zero source
  counts on a clean reset for the same reason.
- Guided Demo Mode is opt-in via `?demo=1`. A presenter who
  forgets the query string sees the regular workspace; the Phase
  13 collapsed demo guide is still there as a fallback.
- Reset between back-to-back demos with `bash scripts/reset_demo_state.sh`.
- No production / staging hosting story is shipped here. Buyer
  meetings against staging are still possible; the click path in
  `docs/pilot/chartnav-pilot-deployment-guide.md` covers the
  staging case.
- No commercial deck is shipped. Decks live out-of-repo.

## Phase 16 recommendation

Phase 16 candidates (NOT part of Phase 15):

1. **Desktop demo packaging** — a one-click runner (Mac / Windows /
   Linux) that boots the local stack and opens the workspace in
   the default browser without `make boot` / `make web-dev`
   expertise. Goal: a buyer can play with ChartNav on the plane.
2. **Pre-recorded fallback clip** — produce the seven-clip set
   from `chartnav-video-clip-shot-list.md` (out-of-repo) so a
   demo that breaks live can fall back to the recorded version.
3. **Sticky workflow progress in normal (non-demo) mode** — a
   smaller visual cue that helps a real provider see where they
   are in the encounter without the full Guided Demo Mode
   stepper. Optional; only ship if it earns its keep.
4. **A11y smoke for the stepper** — add Guided Demo Mode to the
   existing axe-core sweep in `apps/web/tests/e2e/a11y.spec.ts`.
5. **CI summary card** — print phase-level test counts in PR
   comments so slow drift is obvious.

Phase 16 must continue to obey the existing safety contract — no
new clinical features pulled forward, no autonomous diagnosis, no
orders / coding / referral / patient-messaging.
