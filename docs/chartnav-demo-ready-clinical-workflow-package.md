# ChartNav Demo-Ready Clinical Workflow Package (Phase 13)

Phase 13 is a **demo-packaging phase**. It is not a new clinical
feature, not new medical reasoning, not orders / coding / referral
work, not patient messaging, not EHR integration, and not
marketing-site work. Its only goal is to make the existing
ChartNav clinical workflow understandable in five minutes by a
buyer, pilot user, advisor, or investor — without misrepresenting
what the product does.

**No new clinical automation. No new schema. No new API surface.**

## Audience

- **Pilot ophthalmologists** evaluating ChartNav for documentation
  support.
- **Practice administrators** evaluating workflow fit.
- **Advisors / investors** evaluating product positioning.
- **Internal team** running pre-pilot rehearsals.

This package is **not** intended for patient-facing demos.

## Demo workflow overview

Five minutes, seven steps, every step provider-reviewed:

```
1. Review scribe session       (Phase 8)
2. Generate diagram proposals  (Phase 6)
3. Apply to OD/OS diagram      (Phase 5B + 6)
4. Save and sign the diagram   (Phase 5B)
5. Generate patient summary    (Phase 9)
6. Generate pre-visit brief    (Phase 10)
7. Review provider action queue (Phase 11)
```

Phase 12 already proved this end-to-end path is integrated; Phase
13 packages it for a buyer to see.

## Demo data policy

**No backend changes. No new demo seed.** The demo uses the
existing fake seed data:

- Org: `demo-eye-clinic`
- Patient: `PT-1001` (Morgan Lee — fake)
- Encounter: 1 (Retina follow-up — fake)
- Provider: Dr. Carter (fake, seeded in `scripts_seed.py`)
- Source text for the scribe paste: ad-hoc, in the demo script,
  obviously fake ("OD drusen at macula. Possible retinal tear
  superior temporal OS.").

The seed has been "demo-flavored" by construction since Phase 0 —
fake names, fake MRNs, fake DOBs, fake NPIs. Phase 13 reuses that
data rather than introducing a new demo seed because:

- Adding a parallel demo seed would duplicate behavior already in
  `scripts_seed.py`.
- A demo-only endpoint or table would expand surface area for no
  clinical benefit.
- The existing seed is already documented and exercised by every
  test in the repo.

If a future phase needs a richer demo dataset (e.g. multiple
encounters, multiple signed retinal artifacts), it can extend
`scripts_seed.py` directly. Phase 13 does not.

## Demo route / guide behavior

A new collapsible component, `DemoClinicalWorkflowGuide`, mounts at
the top of the workspace's panel stack (just above
`eye-diagram-section`) when a numeric `patientId` is resolved.

- **Collapsed by default.** A *Show demo workflow guide* button
  expands the seven-step checklist; *Hide* collapses it again.
  Normal provider workflow is unaffected.
- **No API calls.** The guide is pure presentation. It does not
  read or write any record.
- **No actionable buttons.** No order, coding, referral,
  patient-message, or "automatically resolve" control. Just a
  step-by-step explanation with safety copy.
- **Safety copy on every render.** Three negative-assertion lines
  appear in the expanded body:
  - "ChartNav supports documentation and review workflows."
  - "ChartNav does not diagnose, order, bill, send referrals, or
    message patients automatically."
  - "Every artifact requires explicit provider review before it is
    treated as final."
- **References the demo script.** The footnote points to
  `docs/demo/chartnav-clinical-workflow-demo-script.md` so a buyer
  can keep reading.

The guide's seven checklist items each describe **what the panel
does**, not what ChartNav decides. None mention orders, coding,
referrals, or patient messaging.

## Documentation map

```
docs/
├── chartnav-demo-ready-clinical-workflow-package.md   ← this file
├── chartnav-patient-chart-foundation.md               ← Phase 13 section appended
└── demo/
    ├── chartnav-clinical-workflow-demo-script.md      ← what to say
    ├── chartnav-demo-click-path.md                    ← what to click
    └── chartnav-video-clip-shot-list.md               ← what to film (no media in repo)
```

- The demo script carries 5-minute and 10-minute scripts, the
  buyer Q&A, the safety guardrails, and the ophthalmology-specific
  positioning.
- The click path is the exact step-by-step click sequence against
  the local seeded stack.
- The video shot list plans short clips against the local seeded
  stack. **No video files or screenshots are checked into the
  repo.**

## Safety / claims rules

The packaged demo must use only safe phrasing.

**Safe phrasing (use freely):**
- "provider-reviewed"
- "documentation support"
- "clinical workflow support"
- "ophthalmology-specific charting assistant"
- "draft for review"
- "review required"
- "does not create orders"
- "does not message patients automatically"

**Forbidden phrasing (never use, even in marketing):**
- "HIPAA compliant" (use *HIPAA-aware data-handling practices*)
- "certified EHR"
- "autonomous diagnosis" / "automatic diagnosis"
- "guaranteed accuracy"
- "automatic orders" / "order OCT"
- "submit referral" / "send referral"
- "billing automation" / "coding automation"
- "send patient message"
- "replaces a doctor"
- "external LLM certainty"

Negative statements are allowed only when they clearly say ChartNav
does **not** do the thing, e.g. "ChartNav does not message
patients automatically."

The Phase 13 frontend tests assert these rules against the demo
guide rendering. The Phase 12 backend integration test
`TestEndToEndSafetyLanguage` already enforces them across the
service-emitted text fields; Phase 13 adds the demo-specific
assertion on the new component.

## Video clip plan

Six panel-specific clips plus one master montage, all captured
against the local seeded stack. See
`docs/demo/chartnav-video-clip-shot-list.md` for the editorial
plan, capture order, and voice-over guardrails.

**No video files are checked into this repo.** They live in a
separate marketing or shared storage location.

## Known limitations

- **The demo guide is collapsible, not gated.** It appears for
  every authenticated user who opens an encounter for a
  patient-id-resolved workspace. A future phase could gate it on a
  query param or a "demo mode" flag if it ever becomes clutter for
  real providers; today the collapsed-by-default UX is enough.
- **Demo data is the existing seed.** A buyer who explores beyond
  the click path will see only the seeded encounter; there is no
  fresh data per demo. Reset between demos with `make reset-db`.
- **Click path assumes local stack.** The demo runs against
  `make boot` + `make web-dev`, not against staging. If you need a
  staging demo, run `make staging-up` first; the click path is the
  same.
- **No animated walkthrough is shipped.** The video shot list is
  editorial only. Producing actual video is out of repo scope.
- **No new safety net.** The package surfaces existing safety
  contracts without strengthening them. If a future phase wants to
  raise the bar (e.g. a stronger clinical-language scan), that's a
  new phase.

## Next recommended phase

Phase 14 candidates (NOT part of Phase 13):

1. **Buyer pilot pre-flight.** Light-touch operator UX for a
   designated pilot — better identity onboarding, a dedicated demo
   patient with a richer encounter history (still fake).
2. **Live consent / disclosure surface.** A small first-run banner
   that records the buyer's acknowledgment of the safety contract
   before they explore the workspace.
3. **Audit-volume budget snapshot.** A short report job that prints
   per-event-type audit row counts so the team can spot drift.
4. **A11y smoke for the action queue.** Add the queue to the
   existing axe-core sweep.
5. **CI summary card.** Print phase-level test counts in PR
   comments so slow drift is obvious.

None of these block Phase 13 from merging.
