# Phase 60 — Structured Vitals & Technician Workup Demo Runbook

> **Fake-data demo only.** Do not enter, screenshot, or narrate real
> PHI. ChartNav's vitals workup feature **does not diagnose**, **does
> not recommend treatment**, **does not place orders**, **does not
> send referrals or patient messages**, **does not bill or code**, and
> **does not integrate with vital-signs devices**. Every value is
> manually entered. Every workup requires explicit clinician sign-off.

## 1. Demo purpose

Show a clinic operator how ChartNav captures structured vitals + an
ophthalmology workup row at the start of a visit, surfaces partial /
out-of-range data as **review prompts** (never as diagnosis), and
locks the workup after explicit clinician attestation. Goal: make the
**technician-entered → clinician-reviewed → signed** posture obvious
in under four minutes.

## 2. Fake-data warning (read aloud at start)

> "This is fake demo data. No real patient information is in this
> environment. ChartNav captures structured vitals — blood pressure,
> temperature, pulse, respiratory rate, oxygen saturation, height,
> weight, BMI, pain score, visual acuity, IOP, dilation status — for
> provider review. ChartNav does not diagnose, does not recommend
> treatment, does not place orders, does not refer, does not message
> patients, does not bill, does not code, and does not sync with any
> vital-signs device. Every value I'm about to enter is fake."

## 3. Setup checklist

- [ ] Demo environment is on the latest `main`. Verify the
      **Clinical / Ophthalmology** tab shows a **"Technician Workup &
      Vitals"** wide card at the top.
- [ ] `CHARTNAV_ENV` is `local` / `dev` / `demo` / `test` — **not**
      `production`.
- [ ] You are logged in as a clinician or technician
      (`clin@chartnav.local` or `tech@chartnav.local`). Reviewers and
      front-desk users cannot create workups (403).
- [ ] You know that **technicians cannot sign**. The demo
      reviewer / sign step uses the clinician identity.
- [ ] No real `CHARTNAV_OPENAI_API_KEY` is set — the vitals service
      does not use OpenAI, but the runtime safety validator should
      still PASS before a live demo.
- [ ] `python3 scripts/check_runtime_safety.py` → PASS.

## 4. Exact click path

1. Open the demo encounter.
2. Click the **Clinical / Ophthalmology** tab.
3. The **Technician Workup & Vitals** card is at the top.
4. Click **Load fake demo vitals** — the form fills with synthetic
   values (BP 122/78 sitting left arm, temp 98.6 °F, pulse 72, RR 16,
   SpO2 98, height 70 in, weight 165 lb, BMI 23.7, pain 0, VA OD
   20/20, VA OS 20/25, IOP 14 / 13 applanation, not dilated,
   allergies + meds reviewed, demo notes).
5. **Point out the live BMI** — the "BMI (calculated)" display
   updates as you type height / weight. Narrate: "BMI is
   server-calculated from height and weight. There is no manual BMI
   entry."
6. Click **Save draft** — the workup is created with status `draft`.
   The status timeline pills flip to `DRAFT → entered → reviewed →
   signed` (only Draft highlighted).
7. Click **Save & mark entered** — status advances to `entered`. The
   timeline lights the Entered pill.
8. **Demonstrate the warnings flow:**
   - Clear the systolic field so only diastolic remains. Click **Save**.
   - The warnings panel now shows "Blood pressure diastolic captured
     but systolic missing; please add systolic before signing."
   - Narrate: "ChartNav surfaces partial data as a review prompt. It
     does not say 'hypertensive crisis'. It does not say 'low blood
     pressure'. It says 'please confirm before signing'."
9. Restore the systolic and bump it to 210 + diastolic 125. The
   warnings panel reads "Systolic blood pressure (210) is outside the
   typical range; provider review required." Narrate: "Out-of-range
   values are flagged for **provider review**. ChartNav never names a
   diagnosis like 'hypertensive crisis'."
10. Reset to the demo sample values. Click **Mark Reviewed**
    (clinician identity). Status flips to `reviewed`.
11. The purple **attestation block** appears. Try clicking **Sign &
    Lock Workup** without ticking the checkbox; it stays disabled.
12. Read the attestation aloud: "I attest that I have reviewed this
    technician workup and the vitals values are accurate. Signing
    will lock the workup — signed workups are immutable."
13. Tick the checkbox, click **Sign & Lock Workup**. The action bar
    is replaced with the green **"Workup signed · locked"** banner
    with timestamp + signer ID.
14. Point out the **"What ChartNav did NOT do"** card — every
    forbidden action lists `(false)`: diagnosis, treatment
    recommendation, orders, referrals, patient messages, billing or
    coding, device integration, remote patient monitoring, auto-sign.

## 5. Sample demo flows (fake-data only)

| Sample | Demonstrates |
|---|---|
| **Load fake demo vitals** | Clean parse — no warnings, BMI calculated. |
| Systolic only | Partial-BP warning. |
| BP 210 / 125 | Out-of-range warning — review prompt, not diagnosis. |
| SpO2 = 85 | Below-range warning — never "hypoxia". |
| Temp 103.5 °F | Out-of-range warning — never "fever" or "sepsis". |
| IOP OD only | Partial-IOP ophthalmology warning. |
| VA OD only | Partial-VA ophthalmology warning. |
| Height 70 / weight 0 | "Weight present without height" warning + BMI = "—". |

Never enter real names, MRNs, DOBs, real provider names, real-world
clinic identifiers, real audio, real chart text.

## 6. What to say (approved safe phrases)

- "Structured vitals + ophthalmology workup intake."
- "Technician-entered, provider-reviewed, signed."
- "BMI is server-calculated."
- "Out-of-range values surface as review prompts, never as diagnoses."
- "ChartNav does not diagnose, does not recommend treatment, does not
  place orders, does not refer, does not message patients, does not
  bill or code."
- "ChartNav does not sync with any vital-signs device. Every value is
  manually entered."
- "Signed workups are immutable; corrections start a new workup."
- "Technicians can enter, but only clinicians can sign."

## 7. What NOT to say (forbidden — claim scanners block these)

- ❌ "AI vitals diagnosis."
- ❌ "Automatic vitals diagnosis."
- ❌ "Vital-sign diagnosis."
- ❌ "Treatment recommendation."
- ❌ "AI prescribes."
- ❌ "Device integration."
- ❌ "Live device integration."
- ❌ "Vital-signs device integration."
- ❌ "Remote patient monitoring."
- ❌ "Continuous patient monitoring."
- ❌ "EHR replacement."
- ❌ "HIPAA compliant."
- ❌ "Hypertensive crisis."
- ❌ "Hypertension diagnosis."
- ❌ "Fever diagnosis."
- ❌ "Hypoxia diagnosis."
- ❌ "Stroke."

## 8. How to explain warnings

- "Out-of-range" → "ChartNav says **'review required'**. It never
  names a diagnosis. The provider decides what (if anything) the
  number means clinically."
- "Partial BP / IOP / VA" → "ChartNav prompts the technician to add
  the missing value before the clinician signs. It will not assume
  defaults."
- "Pain outside 0–10" → "Out-of-scale entries are flagged as 'please
  re-enter' so the technician can fix the typo before signing."
- "Weight without height" → "BMI requires both. The warning tells the
  technician which field to add."

## 9. How to explain Review vs Sign

| Action | What it does | Locks the workup? |
|---|---|---|
| **Save & mark entered** | Saves the form and flips status to `entered`. Technicians can do this. | No. |
| **Mark Reviewed** | Clinician confirms the values look right. Records reviewer + timestamp. | No. |
| **Sign & Lock Workup** | Clinician attests. Records signer + timestamp. **Requires the attestation checkbox.** | **Yes.** Signed workups are immutable; PATCH / review / sign all return 409. |

Narrate: "Three distinct actions, three distinct meanings. Technician
captures the data. Clinician reviews. Clinician signs and locks."

## 10. How to explain the signed / locked state

- The action bar is gone from the DOM. Nothing to edit. Intentional.
- The green "Workup signed · locked" banner shows timestamp + signer.
  Ends with "Signed workups are immutable."
- If asked: "Can the clinician fix a typo after signing?" → "In V1,
  no. The clinician starts a new workup on the same encounter. A
  future version may add a fork-and-supersede path; until then,
  signed = permanent."

## 11. Q&A — "Does it diagnose?"

> "No. ChartNav captures structured intake values and surfaces
> out-of-range or partial data as review prompts. The clinician
> decides clinical meaning at sign time. The 'What ChartNav did NOT
> do' card in the UI lists every disallowed action explicitly."

## 12. Q&A — "Does it sync with my BP cuff / pulse oximeter / scale?"

> "No. ChartNav has no device integration. Every value in the
> workup is manually entered by the technician or clinician. The
> `forbidden_actions.device_integration` field is always `false` in
> every response. A future phase may add device integration; it is
> explicitly out of scope today."

## 13. Q&A — "Is this remote patient monitoring?"

> "No. ChartNav captures at-visit intake only. There is no continuous
> monitoring, no streaming data, no patient-side wearable hookup. The
> `forbidden_actions.remote_patient_monitoring` field is always
> `false`."

## 14. Q&A — "Is OpenAI used?"

> "No. The vitals workup service is pure-Python regex + arithmetic.
> No OpenAI call, no LLM, no production AI. The Phase 52B OpenAI
> fake-data adapter exists for other features (fundus, ambient
> documentation) behind separate opt-in env gates; it is not wired
> into the vitals workup path."

## 15. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `HTTP 403 role_forbidden` on create | Logged in as reviewer / front_desk. | Switch to admin / clinician / technician. |
| `HTTP 403 role_forbidden` on sign | Logged in as technician. | Switch to admin / clinician. Technicians cannot sign. |
| `HTTP 404 encounter_not_found` | Wrong encounter id / cross-org. | Verify the encounter belongs to the caller's org. |
| `HTTP 422 invalid_enum` | Sent an enum value the API doesn't recognise. | Use the documented enum values (see `docs/workflow/structured-vitals-workup.md`). |
| `HTTP 422 attestation_required` | Sign called without `attested: true`. | Tick the attestation checkbox in the UI. |
| `HTTP 409 invalid_transition` | Tried review before entered, or sign before reviewed. | Follow the lifecycle: draft → entered → reviewed → signed. |
| `HTTP 409 workup_immutable` | Tried to mutate a signed workup. | Expected. Start a new workup on the same encounter. |
| BMI shows "—" | Either height or weight missing. | Add the missing value. |
| Out-of-range warning persists after correction | The workup is in entered / reviewed state and the value is still typed out-of-range. | Save the corrected value via PATCH; the server recomputes warnings on every update. |
| Demo reset needed | Test workups accumulated. | Run `scripts/reset_demo_state.sh` (or the Phase 24B retina reset if applicable). |

## 16. Stop-demo triggers (any one → halt + reset)

- Real patient data appears anywhere on screen.
- `CHARTNAV_ENV` is `production` / `staging` / `controlled-pilot`.
- `python3 scripts/check_runtime_safety.py` returns FAIL during the demo.
- A forbidden phrase appears in UI or narration (see § 7).
- A vendor / network error exposes a secret in a visible stack trace.
- A workup is signed without the attestation checkbox having been
  ticked (UI bug — escalate after halting).
- Any "diagnosis confirmed", "treatment recommended", "order placed",
  "billing code", "ICD-10", "CPT", "referral sent", or "patient message
  sent" text appears in the UI.

## 17. Approved phrases (cheat sheet)

- structured vitals + ophthalmology workup intake
- technician-entered, provider-reviewed, signed
- BMI is server-calculated
- review prompts, not diagnoses
- no device integration
- no remote patient monitoring
- signed workups are immutable

## 18. Forbidden phrases (cheat sheet)

- AI vitals diagnosis / automatic vitals diagnosis / vital-sign diagnosis
- treatment recommendation / AI prescribes
- device integration / live device integration / vital-signs device integration
- remote patient monitoring / continuous patient monitoring / RPM-ready
- EHR replacement
- HIPAA compliant
- hypertensive crisis / fever / hypoxia / stroke (clinical conclusions ChartNav never makes)

The three claim scanners (`scripts/check_commercial_claims.sh`,
`check_website_claims.sh`, `check_demo_claims.sh`) block these phrases
in source.

---

## Related documents

- `docs/workflow/structured-vitals-workup.md` — feature contract + API reference.
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/commercial/claims-policy.json` — canonical manifest.
- `docs/demo/phase-56-fundus-demo-runbook.md` — sibling provider-reviewed demo.
- `docs/demo/phase-57-ambient-documentation-demo-runbook.md` — sibling demo template.
