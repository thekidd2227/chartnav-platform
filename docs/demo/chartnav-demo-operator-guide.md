# ChartNav Demo Operator Guide (Phase 15)

For the presenter running a live or recorded ChartNav ophthalmology
workflow demo against the local seeded stack. Pair with:

- `chartnav-clinical-workflow-demo-script.md` — what to *say*.
- `chartnav-demo-click-path.md` — what to *click*.
- `chartnav-video-clip-shot-list.md` — what to *film*.
- `chartnav-demo-environment.md` — how to *boot* and *reset*.

This guide adds the Phase 15 Guided Demo Mode orchestration on top of
those three. Use it when you want the workspace itself to remind you
where you are in the demo.

---

## Recommended demo flow (with Guided Demo Mode)

1. Boot the local stack — see `chartnav-demo-environment.md`.
2. Open `http://127.0.0.1:5173/?demo=1` in a clean browser window.
   The `?demo=1` query enables Guided Demo Mode for this session.
3. Click `enc-row-1` to open Morgan Lee's encounter.
4. Confirm the **Demo Mode** badge is visible at the top of the
   workspace (under the encounter detail). The 8-step stepper
   should read "Step 1 of 8".
5. For each step:
   - Read the on-screen `Cue:` line aloud as your spoken cue.
   - Perform the click(s) the cue describes (the panel mentioned
     in the body lives further down the workspace).
   - Click **Next step** to advance the stepper.
6. End on Step 8 (Workflow completed) and read the closing cue.
7. Click **Reset demo** before the next presentation. (For a fresh
   DB on top of that, run `bash scripts/reset_demo_state.sh`.)

---

## What to click in sequence

| Step | Stepper label | Click target | Comment |
|------|---------------|--------------|---------|
| 1 | Intake | `enc-row-1` | Confirm identity badge says `admin@chartnav.local · org 1`. |
| 2 | Pre-visit brief | `pre-visit-brief-generate` | Show source counts + data gaps. |
| 3 | Visit begins | `scribe-session-source-text` then `scribe-session-create` | Paste the demo source text from the demo script. |
| 4 | Scribe | `scribe-session-process`, then `scribe-session-review`, then `scribe-session-finalize` | Three explicit clicks — emphasize the sequence. |
| 5 | Retinal proposal | Eye diagram panel `Generate proposals from findings` → apply one → `Save` → `Sign` | Anything applied is tagged `source=ai_approved`. |
| 6 | Action queue | `provider-action-items-generate`, then Accept on one, Dismiss on a second, Complete on the accepted one | Walks the lifecycle in front of the buyer. |
| 7 | Patient summary | `patient-summary-create`, then `patient-summary-review`, then `patient-summary-finalize` | Optional small edit between create and review. |
| 8 | Done | (no click) | Read the closing cue, then click **Reset demo** before the next run. |

The stepper does **not** drive the workspace — it tracks where you
are. The clinical panels are the source of truth for the actual
artifacts.

---

## How to reset

Two levels of reset are available:

- **Demo state only**: click **Reset demo** in the Guided Demo Mode
  controls. The stepper returns to Step 1; no data is touched.
- **Full reset**: run `bash scripts/reset_demo_state.sh` from the
  repo root. The script drops + re-creates the local dev SQLite DB,
  prints a short DevTools snippet for clearing browser-side demo
  state, and warns that this script is for the local dev SQLite
  only — it refuses if `DATABASE_URL` points elsewhere.

After a full reset, hard-refresh the browser to be safe.

---

## Fallback paths if the demo breaks

| Symptom | First thing to try |
|---------|--------------------|
| Workspace empty after `?demo=1` | Confirm an encounter is selected (`enc-row-1`). The stepper still shows; clinical panels mount only when an encounter is open. |
| Stepper missing | Confirm the URL still has `?demo=1` or set `localStorage.chartnav.demoMode` to `"1"` and refresh. |
| Stepper showing wrong step | Click **Reset demo** to return to Step 1. |
| `Generate` fails on a panel | Confirm `make boot` is running and the API answers on `:8000`. Run `bash scripts/reset_demo_state.sh` and re-boot if needed. |
| Buyer asks about real-data path | Switch to the pilot docs — `docs/pilot/chartnav-pilot-readiness-checklist.md` is the answer. **Do not** load real PHI into the demo environment. |
| Browser cache stale | Hard-refresh (Cmd/Ctrl-Shift-R). |
| Demo Mode badge in wrong place | Refresh the page after appending `?demo=1`. The component reads the URL on mount. |

If the demo breaks irrecoverably, fall back to the pre-recorded
clip plan in `chartnav-video-clip-shot-list.md` — the editorial
shot list stays the same.

---

## What NOT to claim

Repeats from `docs/demo/chartnav-clinical-workflow-demo-script.md`
"What not to claim, ever" section — keep this list visible during
demos:

- "HIPAA compliant" (use *HIPAA-aware data-handling practices*)
- "Certified EHR"
- "Autonomous diagnosis" / "automatic diagnosis"
- "Guaranteed accuracy"
- "Automatic orders" / "Order OCT"
- "Submit referral" / "Send referral"
- "Billing automation" / "Coding automation"
- "Send patient message" / "auto-message patients"
- "Replaces a doctor"
- "External LLM certainty"

If you catch yourself saying any of these on a demo, stop and
correct: "I want to be careful — ChartNav doesn't do that. What it
does is …".

---

## Provider-review talking points

These are the *positive* things you can say. Use them freely:

- "ChartNav supports documentation and review workflows."
- "Every clinical artifact requires explicit provider review before
  it is treated as final."
- "Provider review is mandatory — finalize is an explicit click."
- "Anything that lands on the diagram is tagged
  `source=ai_approved` and stays auditable."
- "Signed retinal artifacts are immutable in place; edits create an
  explicit fork."
- "The patient-summary panel renders no patient-send action."
- "Suggested → accepted → completed; dismissed and completed are
  immutable."
- "The action queue is review prompts only — no orders, no
  referrals, no patient messages."

---

## AI governance talking points

When the buyer asks about the AI side specifically:

- "Today's generators are deterministic — regex / aggregation over
  already-stored chart text. No external LLM is enabled."
- "The architecture leaves room for an LLM source under the same
  provider-review contract — that is documented as deferred and is
  not enabled in this demo."
- "Audit `detail` is metadata-only by code-and-test contract.
  Sentinel-token regression tests assert this on every PR."
- "Cross-organization access returns `404 patient_not_found` — no
  existence leak. Every per-source SELECT re-asserts the org
  filter for defense in depth."

---

## Ophthalmology workflow talking points

When the buyer asks "what's so ophthalmology-specific?":

- "OD/OS retinal diagram is the headline surface. We're not a
  primary-care SOAP note generator."
- "The structured note vocabulary is closed and ophthalmology-
  flavored — chief complaint, HPI, exam, assessment, plan."
- "The action queue's clinical-language scan targets a narrow
  ophthalmology vocabulary — retinal tear, retinal detachment,
  neovascularization, severe hemorrhage. False positives are
  tolerable; false negatives are expected because the queue is
  documented as not a primary safety net."
- "The patient-friendly summary template composes plain-language
  text from already-stored ophthalmic source content — visual
  acuity, IOP, plan, follow-up — rather than free-form clinical
  reasoning."

---

## Demo timing guidance

| Format | Length | Outline |
|--------|--------|---------|
| Hallway | 2 minutes | Skip Guided Demo Mode. Open the workspace, hit Generate on the pre-visit brief, hit Generate on the action queue, narrate. |
| Standard | 5 minutes | Use Guided Demo Mode. One click per step, one cue per step. |
| Deep | 10 minutes | 5-minute version + the three deeper dives (audit metadata-only, org isolation, clinical-language scans) from the demo script. |
| Recording | 7 – 9 minutes | Use Guided Demo Mode. Add an extra beat between Steps 5 and 6 for a calm pan across the OD/OS diagram. |

---

## How to handle pilot / security questions

When a buyer asks about pilot-readiness or security:

- Pilot questions → `docs/pilot/chartnav-pilot-readiness-checklist.md`
  and `docs/pilot/chartnav-demo-to-pilot-transition-plan.md`.
- Security questions → `docs/pilot/chartnav-security-review-packet.md`.
- "Do you have a deck?" → "We have a clinical workflow demo" and
  the buyer-Q&A from `chartnav-clinical-workflow-demo-script.md`.

If the practice asks for a written commitment, hand them
`docs/pilot/chartnav-known-limitations-and-non-goals.md` and the
readiness checklist together. Both are buyer-safe.

---

## Known weak spots

- **The local stack must already be running.** Boot it before the
  meeting, not during.
- **Browser cache can hide a demo update.** Hard-refresh once at
  the start of every meeting.
- **The action queue can be empty on a clean reset.** Run the
  scribe lifecycle first so finalized text exists for the queue's
  language scan to fire.
- **The pre-visit brief shows zero source counts on a clean reset.**
  Run the scribe + diagram + summary lifecycles first to populate
  meaningful counts.
- **Guided Demo Mode is opt-in (`?demo=1`).** A presenter who
  forgets the query string will see the regular workspace. The
  Phase 13 collapsed demo guide is still there as a fallback.
- **Reset between back-to-back demos.** A previous run's signed
  artifact / finalized summary can confuse the next demo.
