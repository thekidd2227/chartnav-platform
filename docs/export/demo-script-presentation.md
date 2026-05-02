<!--
  Presentation-formatted demo script (~10 slides).
  Source of truth: docs/sales/chartnav-clinical-signal-filtering-demo-script.md
  Use: paste into Keynote / PowerPoint / Google Slides; one slide per ---
  separator. Speaker notes are in the > blockquotes.
-->

# ChartNav demo — Clinical Signal Filtering & Retinal Diagram Assist

3 to 5 minutes · live product · no mockups

> This deck is the speaker outline. Use the live ChartNav app
> (`make dev`, `localhost:5173`) for the actual demo. Slides are
> here so you can pause and frame each beat without staring at
> the URL bar.

---

## The problem (≈ 30s)

Generic dictation tools transcribe everything. Hallway chatter,
asides, uncertain phrasing — it all lands as a wall of text the
provider has to clean up after the visit.

ChartNav does something different.

> Speaker note: keep this beat short. The audience already knows
> the problem; this is just framing. Do not dwell on competitor
> shortcomings — focus on what ChartNav *does*.

---

## The sample dictation (≈ 15s)

> "Okay hold on… OD drusen in the macula… maybe OS flame
> hemorrhage inferior."

One sentence. One aside. One clean finding. One uncertain
finding. This is what real provider speech looks like.

> Speaker note: paste this exact sample into the app's AI scribe
> textarea now. Don't type it live — click Generate proposals as
> soon as it's pasted.

---

## Three tracks (≈ 45s)

ChartNav splits that one sentence into three:

- **Ignored chatter** — *Okay hold on*. No clinical content;
  the filter sets it aside.
- **Clinical text** — *OD drusen in the macula*. Recognized
  finding, with laterality, zone, and definite certainty.
- **Uncertain phrase** — *maybe OS flame hemorrhage inferior*.
  Recognized finding, but the word *maybe* flags it for the
  provider to confirm.

> Speaker note: open the Triage details disclosure inside the
> scribe panel. Walk one beat per track. Critically: chatter is
> *separated*, not silently dropped — the provider can see what
> was filtered and why.

---

## Proposed, not applied (≈ 30s)

Two proposed annotations now exist in the review panel:

- OD drusen, severity *severe*, definite, macula
- OS flame hemorrhage, uncertain, superior

But the OD/OS canvases are still **blank**. Nothing has been
written to the chart. Nothing has been written to the diagram.
Nothing has been written to the findings text.

> Speaker note: linger on the contrast — proposal panel
> populated, canvases empty. This is the trust moment.

---

## Apply and reject (≈ 45s)

Click **Apply** on OD drusen. The OD canvas updates with a new
label. The findings text auto-summary updates.

Click **Reject** on OS flame hemorrhage. The proposal grays out.
The OS canvas stays clean. The findings text doesn't change.

Provider stays in control of every line.

> Speaker note: this beat is the demo's emotional center. Slow
> the cursor down. Let each click breathe.

---

## Save the artifact (≈ 30s)

Click **Save diagram**. The artifact persists as a chart
artifact: organization, patient, optional encounter, who created
it, the full drawing JSON — including which annotations came
from manual placement and which came from approved AI scribe
output (`source: "ai_approved"`).

> Speaker note: navigate back to the Eye Diagrams list to show
> the new artifact in version 1.

---

## Reload to prove durability (≈ 20s)

Click the saved diagram in the list. The canvas comes back with
the OD drusen label intact. The findings text matches what was
saved. No AI re-running. No drift. The saved diagram is the
saved diagram.

> Speaker note: this beat addresses a buyer concern they often
> don't articulate — "will the AI change my charts overnight?"
> Answer: no. The artifact is fixed.

---

## Sign and version protection (≈ 45s)

Click **Sign diagram**. The signed badge appears. The toolbar
disappears. The canvas is read-only.

If the provider needs to amend a signed diagram, ChartNav
**doesn't overwrite the signed version**. It forks a new version
— version 2 — with `parent_artifact_id` pointing back at version
1. The signed record is immutable.

> Speaker note: the technical word is *fork*. With clinical
> buyers, prefer "creates a new version" or "amendment." With
> compliance buyers, "immutable" plays well.

---

## Wrap (≈ 30s)

What you saw, end to end:

- The AI separates clinical from conversational.
- It surfaces uncertainty instead of guessing.
- It proposes annotations and findings, but it never writes
  to the chart on its own.
- The provider applies, rejects, saves, and signs.
- Signed work is version-protected.

ChartNav doesn't replace the provider — it gives the provider a
faster, cleaner, audit-friendly path from speech to a signed
retinal record.

> Speaker note: drop straight into next steps — calendar link,
> one-pager, or the "what would it take to pilot this" question.

---

## Q&A guard rails

If the audience asks any of these, do **not** answer in the
affirmative:

- *"Does ChartNav diagnose retinal disease?"* — No. ChartNav
  surfaces findings; the provider diagnoses.
- *"Is ChartNav a certified EHR?"* — No. It is a clinical
  workflow and charting surface.
- *"Is the AI 100% accurate?"* — No. We surface uncertainty by
  design.
- *"Does this work on any specialty?"* — Retinal scribe v1 is
  ophthalmology-specific by allowlist. Other specialties are on
  the roadmap.
- *"Can it run on live encounter audio?"* — Not in v1. STT
  pipeline integration is a separate piece of work.

---

## Follow-up materials

- One-pager (PDF): `docs/export/one-pager-print.md`
- User guide: `docs/user-guides/clinical-signal-filtering.md`
- Two short clips for the email follow-up: Clip 1 (Clinical
  Signal Filtering) and Clip 3 (Provider Review and Save) from
  `docs/sales/chartnav-retinal-diagram-video-clips.md`.
