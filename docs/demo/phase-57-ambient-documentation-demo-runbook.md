# Phase 57 — Ambient Documentation Assist Demo Operator Runbook

> **This is a fake-data demo.** Do not paste, screenshot, or narrate
> real PHI. ChartNav is not "OpenAI-powered" and does not autonomously
> document anything. The ambient documentation panel drafts a
> provider-review note from a fake encounter transcript; the provider
> must review and sign.

## 1. Demo purpose

Show a clinician how ChartNav drafts a structured provider-review note
from a typed / pasted encounter transcript, surfaces missing-detail
warnings, lists what ChartNav explicitly did **not** do (diagnose,
order, refer, message, bill, code, auto-sign, interpret images), and
locks the draft after explicit clinician sign-off. The goal is to make
the **provider-reviewed, fake-data-only** posture obvious in under
four minutes.

## 2. Fake-data warning (read aloud at start)

> "Everything you see here is fake demo data. No real patient
> information is in this environment. ChartNav drafts a note from the
> transcript I'm about to paste — it does not record audio in real
> time, does not diagnose, does not place orders, does not refer, does
> not send patient messages, does not bill or code, and does not sign
> anything on its own."

## 3. Setup checklist

Before opening the screen-share:

- [ ] Demo environment is on the latest `main`. Verify the
      **Documentation** tab shows a **"Provider-Reviewed Ambient
      Documentation Assist"** wide card below the
      Transcript → Extracted Facts → AI Draft → Final Note stepper.
- [ ] No real `CHARTNAV_OPENAI_API_KEY` or
      `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` env var is set in the
      demo environment — the deterministic rule-based path is the
      production default and the demo path.
- [ ] You are logged in as a clinician (`clin@chartnav.local` in the
      seeded demo). Reviewers, front-desk, and technicians cannot run
      the draft endpoint — a 403 means you are on the wrong user.
- [ ] Browser zoom is 100%. The two-column layout collapses to a
      single column on narrow viewports — that's intentional, but the
      demo reads better at default zoom.
- [ ] You know the difference between **Mark Reviewed** (status flips
      to `reviewed`) and **Sign & Lock Draft** (status flips to
      `finalized`, draft becomes immutable).

## 4. Exact click path

1. Open the demo encounter.
2. Click the **Documentation** tab.
3. Scroll past the stepper + the standard `NoteWorkspace` workbench.
   The **"Provider-Reviewed Ambient Documentation Assist"** card is
   below.
4. In the left column ("Paste a fake / demo encounter transcript"):
   - Click **Load demo sample (fake data)**. The textarea fills with
     the standard fake transcript.
5. Click **Generate provider-review draft**. The right column updates:
   - **Status timeline** pills lit as `Draft → READY FOR REVIEW →
     reviewed → signed` (only first two highlighted).
   - **Structured facts** card with chief complaint, HPI summary,
     visual acuity, IOP, imaging metadata, assessment context,
     plan-as-stated.
   - **Safety flags** card (empty for the clean sample).
   - **Missing information** card (also empty for the clean sample).
   - **Draft note text** collapsible details — open it to show the
     "DRAFT — provider review required" banner at the top.
   - **What ChartNav did NOT do** card listing each forbidden action
     with `(false)` next to it.
6. Demonstrate the missing-information flow:
   - Edit the textarea: replace the contents with the literal phrase
     *"Demo only. Patient seen for routine visit."* (no CC, no VA,
     no IOP, no plan).
   - Click **Generate provider-review draft** again.
   - The "Missing information" card now lists three items:
     missing chief complaint, missing visual acuity, missing
     intraocular pressure. Narrate: *"ChartNav will not invent
     clinical facts the clinician did not state. It surfaces the gaps
     for the provider to confirm."*
7. Demonstrate the order-language safety flag:
   - Replace the textarea with: *"Demo only. Patient reports floaters
     OD. VA 20/40 OD, 20/20 OS. IOP 14 OD, 13 OS. Provider mentioned
     referral to retina specialist and CPT code 92014."*
   - Generate. The "Safety flags" card now warns the transcript
     referenced orders / referrals / patient messaging / billing /
     coding and that **ChartNav did NOT execute any of these**.
8. Return to the original clean draft. Click **Mark Reviewed**:
   - Status timeline pill row flips to highlight `REVIEWED`.
   - The Review button disables and relabels.
   - The purple **attestation block** appears below the action bar.
9. Demonstrate the attestation gate:
   - Try clicking **Sign & Lock Draft** without ticking the checkbox
     — it stays disabled.
   - Read the attestation copy aloud: *"I attest that I have reviewed
     this draft note and it accurately reflects my clinical findings
     from the fake / demo transcript. Signing will lock the draft —
     signed drafts are immutable."*
   - Tick the checkbox. Click **Sign & Lock Draft**.
10. Show the signed state:
    - The action bar and attestation block are replaced with a green
      **"Draft signed · locked"** banner with timestamp.
    - All edit controls are gone from the DOM. The session is now
      immutable; the backend returns 409 on any further mutation
      attempt.

## 5. Sample transcripts (demo-safe, fake-data only)

| Sample | Demonstrates |
|---|---|
| Default loaded by **Load demo sample** | Clean parse — every section extracted, no warnings. |
| `Demo only. Patient seen for routine visit.` | Missing-information flow (CC / VA / IOP all missing). |
| `Demo only. Patient reports floaters OD. VA 20/40 OD, 20/20 OS. IOP 14 OD, 13 OS. Provider mentioned referral to retina specialist and CPT code 92014.` | Order-language safety flag. |
| `Demo only. Patient reports possible exudative AMD OS. VA 20/200 OS. IOP 17 OS. Plan: ophthalmology follow-up in two weeks.` | "Provider to confirm" prefix on assessment_context. |

Never paste real names, MRNs, DOBs, real provider names, real-world
clinic identifiers, transcripts from real encounters, or real audio.

## 6. What to say (approved safe phrases)

- "Provider-Reviewed Ambient Documentation Assist."
- "From clinician-entered transcript."
- "Structured fundus-equivalent draft support — but for notes."
- "Warnings surface when clinical detail is missing."
- "This is a draft — the provider reviews and signs."
- "Signed drafts are immutable; corrections start a new session, not
  an in-place edit."
- "Default ambient documentation uses a deterministic rule-based
  path. No production LLM."
- "ChartNav does not diagnose. ChartNav does not place orders."
- "ChartNav does not refer or message patients. ChartNav does not
  bill or code. ChartNav does not auto-sign. ChartNav does not
  interpret images."

## 7. What NOT to say (forbidden phrases)

Never say or imply any of the following — the claim scanners block
these in source files; saying them on a customer call is the only way
they reach the customer:

- ❌ "Hands-free scribing."
- ❌ "Automatic charting."
- ❌ "The note writes itself."
- ❌ "The chart fills itself."
- ❌ "Autonomous documentation."
- ❌ "Ambient scribe parity."
- ❌ "AI writes the note."
- ❌ "OpenAI-powered clinical documentation."
- ❌ "Production LLM documentation."
- ❌ "Real PHI ready."
- ❌ "ChartNav is HIPAA compliant."
- ❌ "EHR replacement."
- ❌ "Coding recommendations." / "Billing-aware coding."
- ❌ "Patient messaging." / "Automatic referrals."

If a prospect asks one of these directly, redirect using the Q&A
scripts below — do not concede the framing.

## 8. How to explain warnings

When a "Missing information" item appears:

- "The transcript did not include this clinical fact. ChartNav left
  the structured field with the placeholder `<missing - provider to
  verify>` and flagged the gap. ChartNav will never invent a value to
  fill it in."

When a "Safety flag" appears (order / referral / message / billing /
coding language detected):

- "The transcript referenced an order or referral or message. ChartNav
  flagged it — but it did **not** execute it. Orders, referrals, and
  patient messages go through the EHR or the practice's existing
  workflows. ChartNav drafts the note; the provider handles the
  downstream actions through the appropriate clinical pathway."

## 9. How to explain Review vs Sign

| Action | What it does | Locks the draft? |
|---|---|---|
| **Mark Reviewed** | Sets `status=reviewed`, records reviewer + timestamp. Exposes the attestation block. | No. The draft is still editable. |
| **Sign & Lock Draft** | Sets `status=finalized`, records signer + timestamp. **Requires the attestation checkbox.** | **Yes.** Finalized sessions are immutable; backend returns 409 on any mutation attempt. |

Narrate it as: *"Reviewed is the workflow checkpoint. Signed is the
permanent attestation. Two different actions because they mean two
different things."*

## 10. How to explain the signed / locked state

- The action bar is gone from the DOM. There is nothing to edit —
  that's intentional.
- The green "Draft signed · locked" banner names the timestamp and
  ends with "Signed drafts are immutable."
- If asked "Can the clinician fix a typo after signing?" → say:
  *"In V1, no — signing creates a permanent record. To correct, the
  clinician starts a new session with a corrected transcript and
  drafts again. A future version may add a fork-and-supersede path.
  Today's behaviour matches how signed notes work in mainstream EHRs."*

## 11. Q&A — "Is this AI?"

> "ChartNav drafts the note with a deterministic rule-based parser by
> default — no LLM call in production. There's an optional fake-data
> OpenAI assist that's gated behind multiple environment variables and
> is **not** enabled in this demo or in production. The clinician's
> typed transcript is the source of truth, and the provider review +
> sign workflow is required either way."

Do not say "AI did it" without immediately adding "with mandatory
provider review and sign-off."

## 12. Q&A — "Does it diagnose?"

> "No. ChartNav drafts a structured note from what the clinician typed
> or pasted. It does not generate diagnoses, orders, referrals, patient
> messages, billing, or coding. The provider attests to clinical
> accuracy at sign time. The 'What ChartNav did NOT do' panel in the UI
> spells out each disallowed action explicitly."

## 13. Q&A — "Does it read fundus photos / OCT / images?"

> "No. ChartNav's ambient documentation path is not an
> image-interpretation product. It parses clinician-entered text from a
> fake / demo transcript. No computer vision, no auto-detection of
> pathology in photos, no OCT auto-interpretation. The
> `forbidden_actions.image_interpretation` field is always `false` in
> every response."

## 14. Q&A — "Is OpenAI used?"

> "Production ambient documentation uses the deterministic rule-based
> path — no OpenAI calls, no production LLM activation. There's an
> experimental fake-data OpenAI assist seam that's gated behind several
> environment variables (`CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST=openai`
> plus the Phase 52B SAFE-state gates: `CHARTNAV_LLM_ENABLED=1`,
> `CHARTNAV_LLM_REAL_PHI_APPROVED=0`,
> `CHARTNAV_PILOT_ALLOW_LLM_OPENAI=0`, and `CHARTNAV_OPENAI_API_KEY`
> present). It is **not** enabled in this demo, it is **not**
> authorised for real PHI, and turning it on without all gates in SAFE
> state causes the adapter to refuse loudly. ChartNav is not
> 'OpenAI-powered'."

## 15. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Generate button stays disabled. | Textarea is empty. | Type or paste a fake transcript, or click **Load demo sample**. |
| Error banner: `HTTP 403 role_forbidden`. | You're logged in as a reviewer / front-desk / technician. | Switch to a clinician identity. |
| Error banner: `HTTP 404`. | Wrong patient_id / cross-org. | Verify you're on the right patient + org. |
| Error banner mentioning `fake_data_context_required`. | Someone tampered with the client and set `fake_data_context=false`. | The route refuses on purpose — fix the client. |
| Sign button stays disabled after ticking checkbox. | A previous request is still in flight. | Wait for the loading state to clear, then re-check the checkbox. |
| Status timeline does not advance to `READY FOR REVIEW`. | Generate request failed. | Look at the error banner; verify the transcript is non-empty. |
| 409 on second Generate. | The session is already past `draft`. | Start a new session — the demo flow is one draft per session. |
| 409 after Sign. | Session is finalized. | Expected — finalized sessions are immutable. Start a new session. |

## 16. Approved phrases (cheat sheet)

- Provider-Reviewed Ambient Documentation Assist
- from clinician-entered transcript
- structured note draft support
- warnings for missing clinical detail
- not diagnosis
- not orders / referrals / messages / billing / coding
- not image interpretation
- not auto-sign
- deterministic rule-based path
- fake-data / demo only

## 17. Forbidden phrases (cheat sheet)

- hands-free scribing
- automatic charting
- chart fills itself
- note writes itself
- autonomous documentation
- ambient scribe parity
- AI writes the note
- OpenAI-powered clinical documentation
- production LLM documentation
- real PHI ready
- HIPAA compliant
- EHR replacement
- coding recommendations
- billing-aware coding
- patient messaging
- automatic orders / referrals

The three claim scanners (`scripts/check_commercial_claims.sh`,
`check_website_claims.sh`, `check_demo_claims.sh`) block these phrases
in source. Say them on a customer call and you have shipped a claim
ChartNav does not stand behind.

---

## Related documents

- `docs/workflow/ambient-documentation-assist.md` — feature contract +
  safety boundary + API reference.
- `docs/security/chartnav-openai-fake-data-adapter.md` — Phase 52B
  OpenAI fake-data adapter (the gate this feature opts into; not
  enabled in this demo).
- `docs/build/phase-57-ambient-documentation-feature-audit.md` —
  pre-implementation audit justifying the reuse of `scribe_sessions`.
- `docs/demo/phase-56-fundus-demo-runbook.md` — sibling provider-
  reviewed demo with the same template.
