# ChartNav — Clinical Signal Filtering & Retinal Diagram demo script

**Run time:** 3–5 minutes.
**Audience:** Ophthalmology buyers (clinic owners, practice
administrators, health-system innovation leaders, enterprise
procurement).
**Goal:** Show the loop *raw dictation → triage → proposed
diagram → provider applies/rejects → saved, signed, version-protected
artifact*. Always reinforce that the provider is in control.

> Use the same sample throughout the demo:
>
> **"Okay hold on… OD drusen in the macula… maybe OS flame
> hemorrhage inferior."**

---

## Pre-demo setup (do this once before going live)

- Boot ChartNav locally: `make dev` (API on :8000, web on :5173).
- Sign in as a clinician or admin identity (the seeded
  `clin@chartnav.local` works).
- Open a seeded patient chart at
  `http://localhost:5173/#/patients/1`.
- Click the **Eye Diagrams** tab and start a **+ New retinal diagram**
  so the canvas is mounted, then click **AI scribe (paste/dictate)**
  to expand the panel.
- Have the sample dictation copied to your clipboard so you can
  paste it without fumbling.

---

## Beat 1 — Frame the problem (≈ 30s)

> "Generic dictation tools transcribe everything the provider
> says — including hallway chatter, asides, and uncertain
> phrasing — and dump it back as a wall of text the provider
> has to clean up after the visit. ChartNav does something
> different. It separates clinical signal from conversational
> noise *before* anything reaches the chart."

Action on screen:

- Show the empty retinal diagram workspace with the AI scribe
  panel already expanded.
- Resist the urge to demo anything yet — the visual frame
  here is "blank canvas + dictation textbox + nothing has been
  written to the chart."

## Beat 2 — Paste the sample dictation (≈ 15s)

> "Here's a realistic snippet of how an ophthalmologist actually
> dictates during a retinal exam. Notice it's not a perfect
> dictation script — there's an aside, a clean finding, and an
> uncertain finding all in one breath."

Action:

- Paste the sample into the **AI scribe** textarea exactly as
  written:
  > Okay hold on… OD drusen in the macula… maybe OS flame
  > hemorrhage inferior.
- Click **Generate proposals**.

## Beat 3 — Walk through the triage (≈ 45s)

> "ChartNav's Clinical Signal Filtering breaks that one
> sentence into three tracks."

Action:

- Open the **Triage details** disclosure inside the scribe
  review.
- Walk the audience through:
  - **Ignored chatter:** "Okay hold on" — the filter recognizes
    this is a conversational marker with no clinical content,
    so it's set aside.
  - **Clinical text:** "OD drusen in the macula" — recognized
    finding, with laterality (OD), zone (macula), and definite
    certainty.
  - **Uncertain phrase:** "maybe OS flame hemorrhage inferior" —
    recognized finding, but the word *maybe* flags it for the
    provider to confirm before it goes anywhere near the chart.

> "Critically: chatter is *separated*, not silently dropped.
> The provider can still see exactly what was filtered and why."

## Beat 4 — Surface the proposed diagram (≈ 30s)

Action:

- Scroll to the **Proposed annotations** list. Two proposals
  are present — OD drusen (definite) and OS flame hemorrhage
  (uncertain).
- Mention what's NOT shown:
  - Nothing has been written to the chart yet.
  - Nothing is on the canvas yet.
- Read the small print under each proposal: laterality, zone,
  severity (when present), the verbatim source phrase, and
  certainty.

> "These are *proposed* annotations. The AI placed them at the
> zone the provider mentioned, color-coded by severity. But
> they're not on the diagram and they're not in the findings
> text — they exist only inside this review panel until the
> provider explicitly applies them."

## Beat 5 — Apply the definite finding, reject the uncertain one (≈ 45s)

Action:

- Click **Apply** on the OD drusen proposal.
- Watch the OD canvas update with a new label. Point out:
  - The label is tagged as `ai_approved` in the saved data.
  - The findings text below the diagram updated to reflect the
    auto-summary.
- Click **Reject** on the OS flame hemorrhage proposal.
- Watch it gray out and strike through.

> "Apply pulls the annotation onto the canvas and into the
> findings summary. Reject means it never reaches the chart —
> not the canvas, not the findings text, not the saved
> artifact. The provider stays in control of every line."

## Beat 6 — Save the artifact (≈ 30s)

Action:

- Click **Save diagram**.
- The artifact returns from the API; the timestamp updates;
  the **unsaved changes** marker disappears.
- Navigate back to the Eye Diagrams list and show the new
  artifact in the list with version 1.

> "The diagram is now persisted as a chart artifact. It carries
> who created it, when, the patient and organization scope,
> and the full drawing JSON — including which annotations came
> from manual placement and which the provider approved from
> the AI scribe."

## Beat 7 — Reload to prove durability (≈ 20s)

Action:

- Click the saved diagram in the list.
- Confirm the canvas comes back with the OD drusen label, and
  the findings text matches what was saved.

> "If a provider reopens the diagram later, the annotations
> and findings come back exactly. There's no AI re-running and
> drifting — the saved diagram is the saved diagram."

## Beat 8 — Sign and demonstrate version protection (≈ 45s)

Action:

- Click **Sign diagram**.
- Show the **signed** badge appear on the artifact.
- Notice the canvas has been locked: no toolbar, no scribe
  panel, no edit affordances.
- Open the **+ New retinal diagram** flow OR explain (depending
  on the deal): "If a provider needs to amend a signed diagram,
  ChartNav doesn't overwrite the signed version — it forks a
  new version, version 2, with `parent_artifact_id` pointing at
  version 1. The signed record is immutable."

> "This is the audit and compliance story. Signed work cannot
> be silently changed. Amendments create a new versioned record.
> The diagnosing provider's signed artifact is preserved
> exactly as they saw it."

## Beat 9 — Wrap (≈ 30s)

> "What you just saw is ChartNav's Clinical Signal Filtering and
> Retinal Diagram Assist working end-to-end:
>
> - The AI separates clinical from conversational.
> - It surfaces uncertainty instead of guessing.
> - It proposes annotations and findings, but it never writes
>   to the chart on its own.
> - The provider applies, rejects, saves, and signs.
> - Signed work is version-protected.
>
> ChartNav doesn't replace the provider — it gives the provider
> a faster, cleaner, audit-friendly path from speech to a signed
> retinal record."

---

## Talking-point cheat sheet (keep nearby during the live demo)

- Provider-in-the-loop is the architecture, not just a marketing
  line. Repeat it each beat.
- The proposal endpoint is **read-only**. No autosave, no
  silent persistence.
- The filter is rule-based v1 — deterministic, reviewable —
  with an LLM-backed v2 path planned.
- Signed = immutable. Amendments fork. Use the word "fork" with
  technical buyers; "creates a new version" with clinical
  buyers.
- Audit captures counts, never source text, never findings text.
  Bring this up before the buyer's compliance person does.

## Things NOT to say during this demo

- "ChartNav diagnoses retinal disease." It does not.
- "ChartNav is a certified EHR." It is not.
- "The AI is 100% accurate." We surface uncertainty by design.
- "It works on any specialty out of the box." Retinal scribe v1
  is ophthalmology-specific by allowlist.
- "Live audio capture is included." STT integration is a
  separate piece of work.

## Recovery moves if something glitches

| Problem                                | Recovery                                                        |
| -------------------------------------- | --------------------------------------------------------------- |
| Proposal returns no annotations        | Re-paste the sample; check that you opened the scribe panel.    |
| Canvas doesn't update on Apply         | Refresh the page, reload the diagram from the list, retry once. |
| Sign returns 409 already-signed        | Open a fresh diagram (it means the demo seed already signed it).|
| API not responding                     | Quick `curl localhost:8000/health`; restart `make dev`.         |
| Audience asks about HIPAA right now    | Refer to the one-pager's *Provider-control safeguards* section. |

---

## Suggested follow-up (within 24 hours of the demo)

Send the buyer:

1. The one-pager:
   `docs/sales/chartnav-clinical-signal-filtering-one-pager.md`.
2. Two video clips from the shot list:
   - Clip 1: Clinical Signal Filtering.
   - Clip 3: Provider Review and Save.
3. A read-only link to the user guide if they have clinical or
   compliance reviewers:
   `docs/user-guides/clinical-signal-filtering.md`.

Do not send the demo recording itself unless cleared with
account ownership — short, polished clips convert better than a
full session capture.
