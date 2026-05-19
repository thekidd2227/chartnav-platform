# Phase 61 — Controlled Buyer Demo Runbook (Master)

> **Fake-data demo only.** No real PHI. **ChartNav is not HIPAA
> compliant by default.** **ChartNav is not a certified EHR and does
> not replace a certified EHR.** Every workflow surface in this demo
> requires explicit clinician review and sign-off. ChartNav does not
> diagnose, does not recommend treatment, does not place orders or
> referrals, does not message patients, does not bill or code, does
> not interpret images, and does not integrate with vital-signs
> devices.

This is the **master operator script** for a buyer-facing controlled
demo of ChartNav's current workflow. It links to the existing
per-feature runbooks for detailed click paths. It does **not** replace
them.

---

## 1. Purpose

Show a buyer how ChartNav captures a visit end-to-end as a
**provider-reviewed workflow layer**:

1. structured intake (vitals + ophthalmology workup),
2. provider-review draft note from a fake encounter transcript,
3. structured retinal-diagram drafting from clinician-entered
   findings,
4. clinician review + attestation + signed/locked artifact,
5. metadata-only audit posture.

Goal: make the **technician-entered / clinician-reviewed / signed**
posture obvious in under 12 minutes. Every claim in the room must be
defensible against the claim-scanner forbidden list.

## 2. Audience

- Clinic owners, retina / glaucoma / general ophthalmology providers,
  practice managers, IT decision makers.
- Internal partners (advisors, prospective pilot sites, security
  reviewers).

This runbook is **not** for the public website. It is **not**
investor pitch material. It is **not** legal / compliance
attestation. It is an **operator artefact** the demo driver and
narrator work from.

## 3. Fake-data-only warning (read aloud at start)

> "Everything you see today is fake demo data. No real patient
> information is in this environment. ChartNav captures
> **provider-reviewed** intake, drafts, and charts — every step
> requires a clinician to review and sign. ChartNav does not
> diagnose, does not recommend treatment, does not place orders or
> referrals, does not message patients, does not bill or code, does
> not interpret images, and does not sync with vital-signs devices.
> ChartNav is **not HIPAA compliant by default** and is **not a
> certified EHR**. It is a workflow layer that drafts artefacts for
> the clinician's review."

## 4. Pre-demo setup checklist

Before opening the screen-share. **Run § 5 environment checks
first** — every gate must PASS before the buyer joins.

- [ ] Latest `main` checked out (`git log --oneline -1` records the
      SHA at the top of this checklist).
- [ ] Demo environment is `local` / `dev` / `demo` / `test` —
      **never** `production` / `staging` / `controlled-pilot`.
- [ ] No real `CHARTNAV_OPENAI_API_KEY` /
      `CHARTNAV_ANTHROPIC_API_KEY` in the demo shell.
- [ ] No real .env file is open in any visible editor.
- [ ] No real patient name / MRN / DOB / phone / address /
      insurance / photo is visible anywhere on screen.
- [ ] Browser zoom is 100%.
- [ ] Demo identities prepared: `clin@chartnav.local` (clinician,
      default driver) and `tech@chartnav.local` (technician, for the
      Vitals workup scene).
- [ ] Side terminal open with `python3 scripts/check_runtime_safety.py`
      ready to demonstrate.
- [ ] Demo reset script identified for the post-demo step:
      `scripts/reset_demo_state.sh` (general) or
      `scripts/reset_phase24b_retina_demo.sh` (retina-only).

## 5. Environment checks (all must PASS)

Run from the repo root in a side terminal. Every command must exit
with `PASS` / `PASSED` / `0` before the buyer joins.

```bash
python3 scripts/check_runtime_safety.py
bash scripts/check_commercial_claims.sh
bash scripts/check_website_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/test_claim_policy_fixtures.sh
bash scripts/check_alembic_safety.sh
```

If any returns `FAIL` / warns / hits, **halt** and resolve before
opening the screen-share. Do not start a buyer demo on a failing
environment.

## 6. Demo patient / fake-data reminder

The seeded demo patient is **Morgan Lee** (fake), MRN `PT-1001`,
encounter `#1`, provider `Dr. Carter` (fake). Every value the operator
enters in any panel must be synthetic. The Phase 60 vitals "Load fake
demo vitals" button populates the form with synthetic values
(BP 122/78, pulse 72, etc.). The Phase 57 ambient panel's "Load demo
sample" button populates a synthetic encounter transcript. The Phase
55 fundus panel exposes four demo-safe sample chips ("Horseshoe tear
10:30 OD", etc.). **Use these built-in samples — never type real
clinical content.**

## 7. Exact demo order

Twelve-minute target. The operator may compress scene 6 if running
short.

| # | Scene | Tab | Timer (rough) | Reference runbook |
|---|---|---|---|---|
| 1 | Clinical workspace orientation | (workspace shell) | 1 min | this file |
| 2 | Technician Workup & Vitals | Clinical / Ophthalmology | 3 min | `docs/demo/phase-60-vitals-workup-demo-runbook.md` |
| 3 | Ambient Documentation Assist | Documentation / EMR/EHR | 3 min | `docs/demo/phase-57-ambient-documentation-demo-runbook.md` |
| 4 | Fundus Charting | Imaging | 2 min | `docs/demo/phase-56-fundus-demo-runbook.md` |
| 5 | Provider review + sign-off | each of the three surfaces | 1.5 min | per-feature runbooks |
| 6 | Audit + release posture | side terminal + release checklist | 1 min | `docs/release/release-evidence-checklist.md` |
| 7 | Closing | (workspace) | 30 sec | this file |

### Scene 1 — Clinical workspace orientation (1 min)

**Operator action:**
1. Open the SPA at the demo encounter URL.
2. Show the **patient header**: name, MRN, encounter id, status,
   provider, location.
3. Point at the **demographic strip**'s explicit empty-state copy:
   "Not available in demo / Not recorded / No allergies recorded /
   No active meds recorded / Not scheduled".
4. Click through the nine tabs without entering any. State the tab
   names.

**Safe narration:**
> "ChartNav opens to a provider-reviewed workspace. Everything you
> see is fake demo data — the 'Not recorded' fields are intentional
> empty states. The workspace has nine tabs: Overview, Clinical /
> Ophthalmology, Documentation / EMR/EHR, Imaging, Labs / Orders
> Review, Calendar, Communications, Documents, Chat. ChartNav is not
> a certified EHR; it's a workflow layer the clinic uses alongside
> their EHR of record."

### Scene 2 — Technician Workup & Vitals (3 min)

Reference: `docs/demo/phase-60-vitals-workup-demo-runbook.md` § 4.

**Operator action:**
1. Click **Clinical / Ophthalmology**.
2. Find the **Technician Workup & Vitals** wide card at the top.
3. Click **Load fake demo vitals**. Point at the live BMI display
   (server-calculated, no manual BMI entry).
4. Click **Save draft**, then **Save & mark entered**. Point at the
   status timeline pills lighting Entered.
5. Demonstrate a warning: clear the systolic field, click **Save**;
   the warnings panel surfaces "Blood pressure diastolic captured
   but systolic missing; please add systolic before signing."
6. Manually re-enter the missing systolic value on the same selected
   workup, then click **Save** again to clear the warning. (Or, if
   the workup has already advanced past `draft`, click "New workup"
   and **Load fake demo vitals** to start a clean workup for the
   review/sign step.) Demonstrate the **"What ChartNav did NOT do"**
   card: read three forbidden actions aloud with their `(false)`
   markers (diagnosis, orders, billing or coding).

**Safe narration:**
> "Vitals are captured by the technician for clinician review. BMI
> is computed server-side from height and weight — there is no
> manual BMI entry, no device sync, no vital-signs integration.
> Out-of-range values surface as **review prompts** — never as a
> diagnosis. The 'What ChartNav did NOT do' panel lists every
> disallowed action with `(false)` next to it."

**Risk to avoid:** never say "ChartNav has detected hypertension /
fever / hypoxia / tachycardia." Never say "ChartNav recommends X."

### Scene 3 — Ambient Documentation Assist (3 min)

Reference: `docs/demo/phase-57-ambient-documentation-demo-runbook.md` § 4.

**Operator action:**
1. Click **Documentation / EMR/EHR**.
2. Scroll past the existing stepper to the **"Provider-Reviewed
   Ambient Documentation Assist"** wide card.
3. Click **Load demo sample (fake data)**. Point at the textarea
   content.
4. Click **Generate provider-review draft**. The status timeline
   pills light Draft → Ready For Review.
5. Point at the **structured-facts card** (CC, HPI summary, VA, IOP,
   imaging metadata, assessment context, plan-as-stated).
6. Point at the **"What ChartNav did NOT do"** card.
7. Open the **Draft note text** details. Read the "DRAFT — provider
   review required" banner aloud.

**Safe narration:**
> "The clinician's transcript is the source of truth. ChartNav drafts
> structured facts and a provider-review note from the transcript —
> it does not record audio, does not autonomously document, does not
> diagnose, does not place orders, and does not bill or code. The
> draft starts with 'DRAFT — provider review required.' The provider
> reviews, edits if needed, and signs."

**Risk to avoid:** never say "hands-free scribing", "ambient scribe
parity", or "OpenAI-powered documentation." The optional Phase 52B
OpenAI fake-data assist is **not** enabled in this demo.

### Scene 4 — Fundus Charting (2 min)

Reference: `docs/demo/phase-56-fundus-demo-runbook.md` § 4.

**Operator action:**
1. Click **Imaging**.
2. Scroll to the **Fundus charts** wide card.
3. Confirm `OD · Right` is the default laterality.
4. Click the **`Horseshoe tear 10:30 OD`** chip; the textarea fills.
5. Click **Generate Chart**. Point at the SVG preview + legend.
6. Briefly load the **`lattice degeneration at 6`** chip to show a
   missing-laterality warning. Restore the original chart.

**Safe narration:**
> "Fundus charting drafts a structured retinal diagram **from
> clinician-entered findings text**. ChartNav does **not** interpret
> fundus photos. ChartNav does **not** generate diagnoses. Warnings
> are review prompts, not findings."

**Risk to avoid:** never say "AI interprets fundus" or "AI-generated
fundus diagnosis." Never imply the SVG is a clinical conclusion.

### Scene 5 — Provider review + sign-off (1.5 min total)

Return to each of the three signed surfaces in order: Vitals →
Ambient → Fundus.

For **each**:
1. Click **Mark Reviewed**. Status pill flips to Reviewed.
2. The purple attestation block appears. Read the attestation aloud:
   - Vitals: "I attest that I have reviewed this technician workup
     and the vitals values are accurate."
   - Ambient: "I attest that I have reviewed this draft note and it
     accurately reflects my clinical findings from the fake / demo
     transcript."
   - Fundus: "I attest that I have reviewed this fundus chart and it
     accurately reflects my clinical findings."
3. Try the Sign button **without** ticking the checkbox; it stays
   disabled.
4. Tick the checkbox. Click **Sign & Lock** (the exact label varies
   per surface). The green **signed-lock banner** appears with
   timestamp + signer id. The edit controls are gone from the DOM.

**Safe narration:**
> "Every artefact gates the sign action on an explicit attestation
> checkbox. There is no auto-sign. Signed artefacts are immutable —
> the API returns 409 on any later mutation attempt. The clinician
> owns the signature."

**Risk to avoid:** never demonstrate signing without the checkbox.
If the UI ever allows sign-without-attestation, halt — that is a UI
regression to escalate, not narrate.

### Scene 6 — Audit + release posture (1 min)

**Operator action:**
1. In the side terminal, run `python3 scripts/check_runtime_safety.py`
   live. Point at `PASS - no unsafe runtime combinations detected.`
2. Open `docs/release/release-evidence-checklist.md` in the editor.
   Point at the Required Results table.
3. Optional: open `docs/build/current-product-truth.md` and point at
   the row for one of the demonstrated features.

**Safe narration:**
> "Every release is gated by a runtime safety validator and a claim
> manifest. Audit rows on every workflow surface are metadata-only —
> raw vitals values, raw transcript text, raw fundus drawings never
> appear in the audit log. The release-evidence checklist is the
> operator artefact that records what was tested and what risks
> remain before each release."

**Risk to avoid:** never reveal real env-var values or API keys in
the side terminal. If `check_runtime_safety.py` prints `FAIL` during
the live run, **halt the demo immediately**.

### Scene 7 — Closing (30 sec)

**Operator action:**
- Return to either the Vitals or Ambient signed artefact (these
  surfaces render the "What ChartNav did NOT do" card; Fundus
  Charting V1 does not — its safety posture is enforced through
  warnings, provider review/sign, signed-lock state, and the claim
  scanners instead).
- Point at the **"What ChartNav did NOT do"** card on the Vitals or
  Ambient artefact.

**Safe narration:**
> "The Vitals and Ambient signed artefacts in ChartNav come with an
> explicit 'What ChartNav did NOT do' panel listing the actions
> ChartNav did **not** perform: diagnosis, treatment recommendation,
> orders, referrals, patient messages, billing, coding, device
> integration, remote patient monitoring, auto-sign. Fundus
> Charting V1 enforces the same posture through warnings, provider
> review/sign, signed-lock state, and the claim scanners — without
> a per-response forbidden-actions object today. Across all three
> surfaces, ChartNav is a provider-reviewed workflow layer — not an
> autonomous agent, not an EHR replacement, not HIPAA-certified,
> not a billing engine. Provider review and sign-off are mandatory
> at every step. Happy to take questions."

## 8. What to say (approved framing)

- "Provider-reviewed workflow layer."
- "Structured intake for provider review."
- "Clinician-entered findings."
- "Fake / demo transcript."
- "Review and sign-off required."
- "Metadata-only audit posture."
- "Not a certified EHR."
- "Does not replace the EHR."
- "Does not diagnose."
- "Does not interpret images."
- "Does not recommend treatment."
- "Does not place orders or send patient messages."
- "Does not bill or code."
- "Does not integrate with vital-signs devices."
- "Is not remote patient monitoring."

## 9. What NOT to say (forbidden — claim scanners block these)

- ❌ HIPAA compliant / HIPAA certified.
- ❌ EHR replacement / "replaces your EHR".
- ❌ Autonomous documentation / autonomous diagnosis / autonomous interpretation.
- ❌ Hands-free scribing / ambient scribe parity / "AI writes the note" / "the note writes itself" / "the chart fills itself".
- ❌ Production LLM documentation / production LLM clinical reasoning.
- ❌ "AI diagnoses retinal disease" / "AI interprets fundus" / "fundus image interpretation" / "OCT interpretation".
- ❌ OpenAI-powered clinical documentation / ChatGPT clinical documentation / GPT-powered / Claude-powered / Anthropic-powered / IBM watsonx-powered.
- ❌ Treatment recommendation / AI prescribes / AI orders labs.
- ❌ Live device integration / vital-signs device integration / BP cuff integration.
- ❌ Remote patient monitoring / RPM-ready / continuous patient monitoring.
- ❌ Real PHI ready / production-ready for PHI / BAA-ready by default / vendor-approved for PHI.
- ❌ Automatic billing / automatic coding / billing-aware coding / coding recommendations.
- ❌ Automatic orders / automatic referrals / send patient message / patient messaging.
- ❌ Guaranteed ROI / ROI guarantee.
- ❌ Better than Cora / Cora replacement / Cora-killer / outperforms Cora.

The three claim scanners block every phrase above in source files. Saying any of them on a customer call is the only way they reach the customer.

## 10. Stop-demo triggers

Halt immediately and reset the screen-share if any of the following are observed:

- Real patient data appears anywhere on screen.
- `CHARTNAV_ENV` is `production` / `staging` / `controlled-pilot` (visible in env dump or runtime banner).
- `python3 scripts/check_runtime_safety.py` returns FAIL at any point.
- A forbidden phrase from § 9 appears in narration **or** in the UI.
- A vendor / network error exposes an API key, full Authorization header, or OpenAI organization id in a visible stack trace, error banner, or browser console.
- A raw transcript / draft body / vitals value appears in an audit log line visible during the demo.
- Sign / finalize succeeds **without** the attestation checkbox having been ticked (UI bug; escalate after halting).
- Any "diagnosis confirmed", "treatment recommended", "order placed", "billing code", "ICD-10", "CPT", "referral submitted", "patient message sent" text appears in the UI.

## 11. Fallback plan if one module fails

| Module | Symptom | Fallback |
|---|---|---|
| Vitals | API 500 / 404 / 403 on the vitals-workups create / update / review / sign endpoints | Skip Scene 2. State: "Vitals capture is a structured intake; the per-feature runbook covers it in detail." Move directly to Scene 3. |
| Ambient | Generate fails / textarea stuck disabled | Skip Scene 3. State: "Ambient documentation is the transcript-to-draft surface; the per-feature runbook walks through it. Today we'll move directly to fundus charting." Move to Scene 4. |
| Fundus | Generate fails | Skip Scene 4. State the same kind of fallback. Move to Scene 5 using the existing vitals + ambient artefacts. |
| Runtime safety validator | `FAIL` mid-demo | **Halt.** Do not continue the demo on a failing safety gate. |

When any module is skipped, do not narrate the missing functionality
beyond pointing at the per-feature runbook URL. Do not improvise the
behaviour from memory — that risks an inadvertent overclaim.

## 12. Post-demo cleanup

- [ ] Stop the screen-share before any post-demo Q&A that could expose internal state.
- [ ] Reset the local demo database via `scripts/reset_demo_state.sh` (or `scripts/reset_phase24b_retina_demo.sh` if the demo touched retina data).
- [ ] Unset any session env vars that were set for fake-data testing (`CHARTNAV_FUNDUS_DRAFTING_ASSIST`, `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST`).
- [ ] Run `python3 scripts/check_runtime_safety.py` once more and verify `PASS`.
- [ ] Capture buyer questions in the follow-up channel; categorise into Product / Security / Commercial.
- [ ] If a near-miss happened (forbidden phrase narrowly avoided, scanner edge case, runtime gate edge case), file the near-miss in the runbook author's queue. Updating the runbook is **not** the same as merging a code change — claim-scanner additions and runbook fixes land via a normal PR.

## 13. Buyer Q&A safe answers

The full Q&A is captured separately in
`docs/demo/phase-61-buyer-qa-safe-answers.md`. The operator should
read that sheet end-to-end before the demo.

## 14. Known limitations

- This is an **operator artefact**, not auto-executed. The operator
  must complete the pre-demo checklist by hand before every demo.
- The Phase 61 runbook does not replace the per-feature runbooks —
  it links to them.
- The demo scanner's FILES list is hand-curated. Phase 61's three
  new docs (this runbook, the checklist, the Q&A safe-answers, the
  storyboard) are added to the FILES list as part of this PR.
- Phase 61 ships **no product code changes**. Any UI gap surfaced
  during the demo is a separate phase.
- Optional OpenAI fake-data assist is intentionally **disabled** for
  this demo by default. If the buyer asks specifically to see the
  fake-data path with OpenAI, refer to
  `docs/security/chartnav-openai-fake-data-adapter.md` § 11
  (operator runbook) and treat it as a separate ad-hoc demo with
  its own pre-demo checklist.

---

## Related documents

- `docs/demo/phase-61-buyer-demo-checklist.md` — the pre/during/post checklist version of this runbook.
- `docs/demo/phase-61-buyer-qa-safe-answers.md` — Q&A safe answers.
- `docs/demo/phase-61-demo-storyboard.md` — scene-by-scene operator storyboard.
- `docs/demo/phase-56-fundus-demo-runbook.md` — Fundus per-feature runbook.
- `docs/demo/phase-57-ambient-documentation-demo-runbook.md` — Ambient per-feature runbook.
- `docs/demo/phase-60-vitals-workup-demo-runbook.md` — Vitals per-feature runbook.
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/release/release-evidence-checklist.md` — release-gate template.
- `docs/commercial/claims-policy.json` — canonical manifest.
- `scripts/check_runtime_safety.py` — runtime gate.
