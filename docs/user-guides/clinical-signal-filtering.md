# Clinical Signal Filtering & Retinal Diagram Assist — user guide

For ophthalmology providers (and the people training them) using
ChartNav's AI scribe and retinal diagram workspace.

This is a clinical-workflow surface. It is **not** a certified
electronic health record, and it does **not** diagnose. The AI
proposes; you decide.

---

## What Clinical Signal Filtering does

When you paste or dictate exam phrasing into the **AI scribe**
panel inside the retinal diagram workspace, ChartNav reads it
and splits it into three tracks:

1. **Clinical text** — phrases that contain a recognized
   retinal finding, with laterality, zone, severity, and
   certainty extracted.
2. **Ignored chatter** — conversational phrases ("hold on,"
   "next patient," "thank you") that do not contain a clinical
   finding.
3. **Uncertain phrases** — anything the filter could not
   confidently classify, or any phrase with explicit
   uncertainty language ("possible," "rule out," "?"). These
   are **not** dropped — they are surfaced for you to review.

Recognized findings are then turned into **proposed diagram
annotations** — small markers on the OD or OS canvas that you
can apply or reject one at a time.

## What Retinal Diagram Assist does

When you click **Apply** on a proposed annotation, ChartNav:

- places the annotation on the matching eye's canvas at the
  correct anatomical zone,
- tags the annotation as `ai_approved` in the saved drawing
  data so audit can distinguish AI-assisted vs manual
  annotations later,
- merges the AI-generated findings summary into your
  **Findings** text below the canvas.

When you click **Reject**, ChartNav does **nothing**. The
proposal is grayed out in the panel and never reaches the
canvas, the findings text, or the saved chart.

## What it does NOT do

- It does **not** diagnose retinal disease. It surfaces
  findings; the clinician interprets and signs.
- It does **not** save anything to the chart automatically.
  Generating a proposal is read-only — only your **Save**
  click writes to the chart.
- It does **not** guess at missing information. If your
  dictation skips laterality (no OD / OS / OU), no annotation
  is auto-placed. You'll see a warning flag instead.
- It does **not** transcribe ambient room audio. The scribe
  reads what you paste or type into the textarea. Live
  microphone capture is not part of v1.
- It does **not** replace the manual diagram tools. Pen,
  text labels, delete, undo / redo, and clear remain
  first-class.
- It is **not** multilingual in v1. English only.

## Quick reference — what the filter recognizes

### Findings allowlist (v1)

drusen · microaneurysm · dot/blot hemorrhage · flame
hemorrhage · hard exudates · cotton-wool spot ·
neovascularization (incl. NVD/NVE) · IRMA · lattice
degeneration · retinal tear or hole · retinal detachment ·
laser scar / PRP / pan-retinal photocoagulation · disc pallor
(or pale disc / optic atrophy) · RPE changes (incl.
"pigmentary changes," "retinal pigment epithelium changes").

If your finding isn't on this list, the filter will surface
the phrase as **uncertain** rather than guess. Place it
manually with the labeled-symbol tool.

### Laterality

`OD` · `OS` · `OU` · "right eye" · "left eye" · "both eyes"
· "bilateral."

### Zone

macula · optic disc · superior · inferior · nasal · temporal
· periphery.

### Severity

mild · moderate · severe.

### Uncertainty markers

possible · possibly · maybe · questionable · likely · rule
out · uncertain · suspicious for · cannot rule out · `?`.

### Chatter markers

okay · hold on · let me see · can you hear me · next patient
· front desk · we'll come back to that · thank you · one
moment · scheduling and appointment phrasing.

## Worked examples

### Example 1 — clean dictation

> "OD severe drusen in the macula."

| Track             | Result                                                       |
| ----------------- | ------------------------------------------------------------ |
| clinical text     | `OD severe drusen in the macula`                             |
| ignored chatter   | —                                                            |
| uncertain phrases | —                                                            |
| structured        | drusen / OD / macula / severe / definite                     |
| proposed          | one OD label at the macula zone, severity color "severe"     |

### Example 2 — chatter mixed in

> "Okay hold on. OD drusen in the macula. Next patient."

| Track             | Result                                                       |
| ----------------- | ------------------------------------------------------------ |
| clinical text     | `OD drusen in the macula`                                    |
| ignored chatter   | "Okay hold on" / "Next patient"                              |
| uncertain phrases | —                                                            |
| structured        | drusen / OD / macula / no severity / definite                |
| proposed          | one OD label at the macula zone                              |

### Example 3 — uncertainty preserved

> "Maybe OS flame hemorrhage inferior."

| Track             | Result                                                              |
| ----------------- | ------------------------------------------------------------------- |
| clinical text     | `Maybe OS flame hemorrhage inferior`                                |
| ignored chatter   | —                                                                   |
| uncertain phrases | "Maybe OS flame hemorrhage inferior" (uncertainty marker present)   |
| structured        | flame_hemorrhage / OS / inferior / no severity / **uncertain**      |
| proposed          | one OS label at the inferior zone, marked uncertain in the panel    |

### Example 4 — finding without laterality

> "Drusen in the macula."

| Track             | Result                                                              |
| ----------------- | ------------------------------------------------------------------- |
| clinical text     | `Drusen in the macula`                                              |
| missing flag      | `no_laterality_specified`                                           |
| structured        | drusen / — / macula / — / definite                                  |
| proposed          | **none** — laterality required for auto-placement                   |

The provider should either re-dictate with OD / OS, or place
the annotation manually using the canvas tools.

## How provider approval works

1. Open the retinal diagram workspace for a patient (Eye
   Diagrams tab → New retinal diagram, or open an existing
   diagram).
2. Click **AI scribe (paste/dictate)** to expand the panel.
3. Paste or type your exam phrasing.
4. Click **Generate proposals**.
5. Review the **Triage details** disclosure — verify the
   filter agreed with you on what's clinical, what's chatter,
   and what's uncertain. If the filter sorted something into
   the wrong bucket, **trust your read**.
6. For each **Proposed annotation**:
   - **Apply** if you agree — the annotation appears on the
     matching canvas and the findings text auto-summary
     updates.
   - **Reject** if you don't — the annotation is grayed out
     and is **never** persisted.
7. Use **Apply remaining** or **Reject remaining** to batch
   the rest if you've decided in bulk.
8. Edit the canvas or findings text further if needed.
9. Click **Save diagram** to persist. Until you click Save,
   nothing has been written to the chart.

## How saved diagram artifacts work

- Saved diagrams live in `chart_artifacts` and reload exactly:
  same annotations, same findings text, same metadata.
- Each row carries: organization, patient, optional encounter,
  who created it, artifact_type, title, findings text, the
  drawing JSON, version number, and timestamps.
- **Version protection on signing.** Once you click **Sign
  diagram**, the artifact is locked. If you need to amend it
  later, ChartNav does not overwrite the signed record — it
  forks a **new version** that points back at the signed one
  via `parent_artifact_id`. The signed v1 is preserved exactly
  as you saw it when you signed.
- **Audit.** Viewing, updating, creating, signing, and
  versioning all write an audit row. The audit detail captures
  IDs and counts only — never the verbatim source text, the
  findings text, or the drawing payload.

## Best dictation habits

The filter is conservative. You'll get the most out of it by
matching how it reads:

- **State laterality first.** "OD severe drusen" reads cleanly.
  "There's some drusen on the right" works less consistently.
- **Use the canonical finding name.** "Drusen" not "yellow
  spots." "Cotton wool spot" not "cotton wool."
- **Anchor severity once per finding.** "Mild drusen" places
  cleanly; "kind of mild but not really" forces uncertainty.
- **Be explicit about uncertainty.** Saying "possible" or
  "rule out" tells the filter to flag the finding for your
  review instead of charting it as definite.
- **Move chatter into chatter words.** "Hold on" and "next
  patient" are recognized as conversational. Mid-finding
  asides like "let me look at this from above" are not — the
  filter will treat them as uncertain. Pause, then continue.
- **One finding per breath.** "OD drusen, OS lattice" works,
  but separating into two short sentences is cleaner: "OD
  drusen in the macula. OS lattice in the periphery."
- **Don't dictate a full chart note here.** This is the
  retinal diagram surface. Long narrative paragraphs belong in
  the encounter note workspace, not the scribe textarea.

## Troubleshooting

| Symptom                                              | What to check                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------ |
| No proposals appeared                                | Did the filter recognize a finding from the allowlist? Try a canonical name.   |
| Proposal placed on the wrong eye                     | Did you say "OD"/"OS"/"OU"? Re-dictate with explicit laterality.               |
| Proposal placed at the center instead of a zone      | The phrase didn't include a zone word. Add macula / superior / temporal etc.  |
| Filter flagged a definite finding as uncertain       | An uncertainty word was in the phrase. Re-dictate without the hedge.           |
| Save fails with `409 already signed`                 | The artifact is signed. Editing forks a new version automatically — try again. |
| Save fails with `403 role_forbidden`                 | Reviewers are read-only. Sign in as admin or clinician to edit.               |
| Save fails with `404 patient_not_found`              | Cross-org access; you're signed in to a different organization.               |

If something behaves unexpectedly, take a screenshot of the
scribe panel + a copy of the source text you pasted, and send
it to product. Do **not** include any real patient data.

## Where to learn more

- Architecture, persistence, and audit details:
  [`docs/chartnav-patient-chart-foundation.md`](../chartnav-patient-chart-foundation.md).
- Sales and demo materials:
  [`docs/sales/chartnav-clinical-signal-filtering-one-pager.md`](../sales/chartnav-clinical-signal-filtering-one-pager.md).
- Demo script:
  [`docs/sales/chartnav-clinical-signal-filtering-demo-script.md`](../sales/chartnav-clinical-signal-filtering-demo-script.md).
