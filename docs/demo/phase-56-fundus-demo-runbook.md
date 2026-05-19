# Phase 56 — Fundus Charting Demo Operator Runbook

> **This is a fake-data demo.** Do not enter, screenshot, or narrate real
> PHI. ChartNav is not "OpenAI-powered" and does not interpret retinal
> images. The fundus chart panel drafts a structured retinal diagram
> from clinician-entered findings; the provider must review and sign.

## 1. Demo purpose

Show a retina clinician how ChartNav drafts a structured fundus chart
from typed clinical findings, surfaces missing-detail warnings, and
locks the chart after explicit clinician sign-off. The goal is to
make the **provider-reviewed, doctor-entered-findings-are-source-of-truth**
posture obvious in under three minutes.

## 2. Fake-data warning (read aloud at start)

> "Everything you see here is fake demo data. No real patient
> information is in this environment. ChartNav drafts a fundus chart
> from what the clinician types — it does not read fundus photos,
> does not diagnose, and does not sign anything on its own."

## 3. Setup checklist

Before opening the screen-share:

- [ ] Demo environment is on the latest `main`. Verify the Imaging tab
      shows a **Fundus charts** wide card below "OD/OS retinal
      workbench".
- [ ] No real `CHARTNAV_OPENAI_API_KEY` or `CHARTNAV_FUNDUS_DRAFTING_ASSIST`
      env var is set. The fundus charting default is deterministic
      `rule_based_v1`; the optional OpenAI assist is a fake-data
      experimental opt-in and not part of this demo.
- [ ] You are logged in as a clinician (`clin@chartnav.local` in the
      seeded demo). Reviewers and front-desk roles cannot sign — if you
      see a 403, you are on the wrong user.
- [ ] Browser zoom is 100%. The two-column layout collapses to a single
      column at narrow viewports — that's intentional, but the demo
      reads better at default zoom.
- [ ] You know the difference between **Mark Reviewed** (status flips to
      `reviewed`, chart still editable) and **Sign & Lock** (status
      flips to `signed`, chart becomes immutable).

## 4. Exact click path

1. Open the demo encounter (any encounter; the workspace mounts the
   panel scoped to the current encounter).
2. Click the **Imaging** tab.
3. Scroll past the upper imaging-pipeline cards and the OD/OS retinal
   workbench. The **Fundus charts** wide card is below.
4. In the left column ("Enter clinician findings"):
   - Confirm `OD · Right` is selected by default in the laterality
     radio group.
   - Click the **`Horseshoe tear 10:30 OD`** sample chip. The textarea
     fills in and the laterality stays on OD.
5. Click **Generate Chart**. A draft fundus chart appears in the right
   column with:
   - the status timeline pills lit up as `DRAFT → reviewed → signed`
     (only DRAFT highlighted);
   - the SVG preview with the horseshoe-tear glyph at the 10:30
     position;
   - the legend below the SVG;
   - an empty warnings panel (no missing-detail warnings for this
     example).
6. Demonstrate the warnings flow:
   - Clear the textarea.
   - Click the **`Lattice 5 to 7 OS`** chip → laterality flips to OS.
   - Click **Generate Chart**. Pop one item: replace the text with
     `lattice degeneration at 6` (no laterality, no eye) and click
     **Generate Chart** again. The warnings panel now shows the
     missing-laterality warning. Narrate: "ChartNav will not invent
     findings the clinician didn't dictate. It asks the clinician to
     clarify."
7. Select the original horseshoe-tear chart from the saved-charts
   list. Click **Mark Reviewed** — the status pill row updates to
   `DRAFT → REVIEWED → signed` and the Reviewed button disables and
   relabels.
8. Demonstrate the attestation gate:
   - Try clicking **Sign & Lock Chart** without ticking the
     attestation checkbox — it stays disabled.
   - Read the attestation copy aloud: *"I attest that I have reviewed
     this fundus chart and it accurately reflects my clinical findings.
     Signing will lock the chart — signed charts are immutable."*
   - Tick the checkbox, click **Sign & Lock Chart**.
9. Show the signed state:
   - The action bar is replaced with a green "Chart signed · locked"
     banner with timestamp + signer ID.
   - All edit controls are gone from the DOM. The chart is now
     immutable; backend PATCH returns 409 too.

## 5. Sample findings (demo-safe, fake-data only)

| Sample | Demonstrates |
|---|---|
| `horseshoe tear at 10:30 OD` | clean parse, single-glyph render, no warnings |
| `lattice from 5 to 7 OS near ora` | arc-style finding crossing two clock hours |
| `superotemporal detachment OD` | descriptive zone, no clock-hour detail |
| `laser scars temporal OS` | post-treatment finding (the chip set in the UI) |
| `lattice degeneration at 6` | missing-laterality warning |
| `lattice OD near ora` | missing-clock-hour warning |
| `vision is 20/20` | no-recognisable-findings warning |

Never enter real names, MRNs, DOBs, real provider names, real-world
clinic identifiers, screenshots from real charts, or real fundus
photos.

## 6. What to say (approved safe phrases)

- "Provider-reviewed retinal diagram drafting from clinician-entered findings."
- "ChartNav offers structured fundus chart support."
- "Warnings surface when laterality or clock-hour detail is missing."
- "This is a draft — the provider reviews and signs."
- "Signed charts are immutable; corrections start a new chart, not an in-place edit."
- "Default fundus charting uses a deterministic rule-based path. No production LLM."
- "ChartNav does not diagnose. ChartNav does not interpret fundus photos."

## 7. What NOT to say (forbidden phrases)

Never say or imply any of the following — the claim scanners block
these in source files; saying them on a customer call is the only way
they reach the customer:

- ❌ "Fundus image interpretation."
- ❌ "AI diagnoses retinal disease."
- ❌ "AI-generated fundus diagnosis."
- ❌ "OpenAI fundus interpretation."
- ❌ "OpenAI-powered fundus charting."
- ❌ "Autonomous retinal charting."
- ❌ "Production LLM fundus workflow."
- ❌ "Real PHI ready."
- ❌ "AI detects retinal disease."
- ❌ "ChartNav is HIPAA compliant."
- ❌ "ChartNav is OpenAI-powered."

If a prospect asks one of these things directly, redirect with the
Q&A in § 11–14 below — do not concede the framing.

## 8. How to explain warnings

When a warning appears, narrate it in one of these patterns:

- **Missing laterality**: "The clinician didn't say which eye. ChartNav
  drew this on the default eye but flagged it for the clinician to
  confirm before signing. ChartNav will never invent which eye."
- **Missing clock hour**: "The finding doesn't have a clock-hour
  location. ChartNav drew it at a default position with reduced
  opacity and flagged it. The clinician confirms the position before
  signing."
- **Vague location**: same script as missing clock hour.
- **Unsupported finding type**: "ChartNav's parser didn't recognise
  this finding. It surfaced a warning so the clinician can clarify or
  draw it manually. Nothing was invented."
- **Laterality mismatch (Phase 56)**: "The clinician typed one eye in
  the findings text but selected a different eye in the request. The
  findings text wins, and ChartNav surfaces a warning so the clinician
  confirms before signing."

## 9. How to explain review vs sign

| Action | What it does | Is the chart still editable? |
|---|---|---|
| **Mark Reviewed** | Records reviewer + timestamp; status flips to `reviewed`. | Yes. |
| **Sign & Lock Chart** | Requires an explicit attestation checkbox. Records signer + timestamp; status flips to `signed`. | **No.** Signed charts are immutable; the backend returns 409 on PATCH. |

Narrate it as: "Reviewed is the workflow checkpoint. Sign is the
permanent attestation. They look like two different actions because
they are two different actions."

## 10. How to explain the signed / locked state

After signing:

- The action bar is gone from the DOM. There is no edit button to
  show off — that's intentional.
- The green "Chart signed · locked" banner names the signer and the
  timestamp, and ends with "Signed charts are immutable."
- If asked "Can the clinician fix a typo after signing?" → say:
  *"In V1, no — signing creates a permanent artefact. A future version
  may add a fork/new-version path. The current behaviour matches how
  signed clinical notes work in mainstream EHRs."*

## 11. Q&A — "Is this AI?"

> "ChartNav drafts the chart with a deterministic rule-based parser by
> default. There's an optional fake-data OpenAI assist that's gated
> behind multiple environment variables and is not enabled in this
> demo or in production. The clinician's typed findings are the source
> of truth, and the provider review + sign workflow is required either
> way."

Do not say "AI did it" without immediately adding "with mandatory
provider review and sign-off."

## 12. Q&A — "Does it diagnose?"

> "No. ChartNav drafts a structured chart from what the clinician
> typed. It does not generate diagnoses, orders, referrals, patient
> messages, billing, or coding. The provider attests to clinical
> accuracy at sign time."

## 13. Q&A — "Does it read fundus photos?"

> "No. ChartNav is not an image-interpretation product. The fundus
> chart panel parses clinician-entered text findings and draws them on
> a standardised retinal diagram. No computer vision, no auto-detection
> of pathology in photos, no OCT auto-interpretation."

## 14. Q&A — "Is OpenAI used?"

> "Production fundus charting uses the deterministic rule-based path —
> no OpenAI calls, no production LLM activation. There's an
> experimental fake-data OpenAI assist seam that's gated behind several
> environment variables (`CHARTNAV_FUNDUS_DRAFTING_ASSIST=openai` plus
> the Phase 52B SAFE-state gates). It is not enabled in this demo, it
> is not authorised for real PHI, and turning it on without all gates
> in SAFE state causes the adapter to refuse loudly. ChartNav is not
> 'OpenAI-powered'."

## 15. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Generate button stays disabled. | The textarea is empty. | Type a finding or click a sample chip. |
| Error banner: `HTTP 403 insufficient_role`. | You're logged in as a reviewer / front-desk / technician. | Switch to a clinician identity. |
| Error banner: `HTTP 404`. | The encounter is in a different org. | Verify you're on the right org (admin/clinician identity must match the encounter's organization_id). |
| Sign button stays disabled even with checkbox ticked. | A previous render/review call is still in flight. | Wait for the loading state to clear, then tick the checkbox again. |
| Warnings panel is empty when you expected a warning. | The text matched a clean pattern. | Switch to one of the explicit warning examples in § 5 (e.g. `lattice degeneration at 6`). |
| Signed chart still shows the action buttons. | Stale tab — the chart object was loaded before signing. | Click another saved chart and back; the warnings + lock state refresh on chart change (Phase 55 bug fix). |
| Backend 409 on a follow-up sign. | The chart is already signed. | Expected — signed charts are immutable. Start a new chart. |

## 16. Approved safe phrases (cheat sheet)

- provider-reviewed retinal diagram drafting
- from clinician-entered findings
- structured fundus chart support
- warnings for missing laterality or clock-hour detail
- not diagnosis
- not image interpretation
- deterministic rule-based path
- fake-data / demo only

## 17. Forbidden phrases (cheat sheet)

- fundus image interpretation
- fundus photo interpretation
- retinal image interpretation
- AI interprets fundus
- autonomous fundus interpretation
- fundus diagnosis
- AI-generated fundus diagnosis
- OpenAI fundus interpretation
- OpenAI-powered fundus charting
- autonomous retinal charting
- production LLM fundus workflow
- real PHI ready
- AI detects retinal disease
- HIPAA compliant
- ChartNav is OpenAI-powered
- automatic OCT interpretation
- automatic orders / referrals / patient messaging / billing / coding / claims

The three claim scanners (`scripts/check_commercial_claims.sh`,
`check_website_claims.sh`, `check_demo_claims.sh`) block these phrases
in source. Say them on a customer call and you have shipped a claim
ChartNav does not stand behind.

---

## Related documents

- `docs/workflow/fundus-charting.md` — feature workflow + UI + safety boundary.
- `docs/security/chartnav-openai-fake-data-adapter.md` — the Phase 52B OpenAI fake-data adapter contract (not enabled in this demo).
- `docs/build/phase-55-fundus-demo-readiness-audit.md` — audit history and reconciliation with Phase 55 UX polish.
