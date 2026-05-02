# ChartNav — Clinical Signal Filtering & Retinal Diagram Assist

**One-page sales brief** · For ophthalmology clinic owners,
practice administrators, health-system innovation leaders,
enterprise procurement, and government buyers.

> Most dictation tools capture everything. ChartNav is designed to
> separate the clinical signal from conversational noise, propose
> retinal annotations, and keep the provider in control.

---

## The problem

Ophthalmology providers dictate during exams. Real clinical speech
is messy:

- Casual asides ("hold on," "let me check," "next patient").
- Mixed laterality and finding density inside one sentence.
- Confidence varies — sometimes the finding is definite, often
  it is "possible," "questionable," or "rule out."

Generic dictation and ambient-scribe tools transcribe everything
and push the burden of editing onto the provider after the visit.
The result: longer documentation, more after-hours work, and an
AI surface that providers don't trust to chart on their behalf.

## The ChartNav approach

ChartNav is a clinical workflow surface for ophthalmology that
treats provider speech as a stream to be **triaged**, not just
transcribed:

1. **Clinical Signal Filtering** separates dictation into
   *clinical text*, *ignored chatter*, and *uncertain phrases*.
2. **Retinal Diagram Assist** turns recognized findings into
   *proposed* annotations on the OD/OS retinal canvas.
3. **Provider review** is the only path to the chart — applied
   proposals persist; rejected proposals never reach the
   diagram or the findings text.

## Why it matters

- **Less friction in the room.** Providers can speak naturally;
  the scribe only surfaces clinically-relevant content.
- **Trust by construction.** Uncertain phrases are flagged
  for review, not silently chosen one way or the other.
- **Audit-ready persistence.** Every chart artifact carries
  version, signed status, and an audit trail with no PHI in
  the audit body.
- **Conservative by design.** Rule-based v1 means deterministic,
  reviewable behavior — not an opaque LLM at the chart edge.

## Retinal Diagram Assist

- OD/OS dual-canvas with manual pen + label tools.
- AI-proposed annotations placed by zone (macula, optic disc,
  superior, inferior, nasal, temporal, periphery), color-coded
  by severity, tagged with certainty.
- Apply / reject controls per proposal; *Apply remaining* and
  *Reject remaining* batch actions.
- Saved diagrams reload with annotations and findings intact.
- Sign locks the diagram. Edits after signing fork into a new
  version — the signed record is immutable.

## Clinical Signal Filtering — what it sees

- **Findings allowlist** (v1): drusen, microaneurysm, dot/blot
  hemorrhage, flame hemorrhage, hard exudates, cotton-wool spot,
  neovascularization (NVD/NVE), IRMA, lattice degeneration,
  retinal tear or hole, retinal detachment, laser scar / PRP,
  disc pallor, RPE changes.
- **Laterality:** OD / OS / OU and natural-language equivalents
  ("right eye," "left eye," "both eyes," "bilateral").
- **Zones:** macula, optic disc, superior, inferior, nasal,
  temporal, periphery.
- **Severity:** mild, moderate, severe.
- **Uncertainty markers:** possible, possibly, maybe,
  questionable, likely, rule out, uncertain, suspicious for,
  cannot rule out, "?".
- **Chatter:** "okay," "hold on," "let me see," "can you hear
  me," "next patient," "front desk," scheduling and rapport
  phrases.

A phrase that contains both a recognized finding *and* an
uncertainty marker is kept as clinical **and** also surfaced as
an uncertain phrase for explicit confirmation.

## Provider-control safeguards

- The proposal endpoint is **read-only** — calling the AI scribe
  never writes to a chart.
- Persistence happens only when the provider clicks *Save* in
  the diagram workspace.
- Applied proposals carry a `source: "ai_approved"` tag in the
  saved drawing JSON so downstream review can distinguish
  manual annotations from AI-assisted ones.
- Rejected proposals never enter `vector_json` or `findings_text`.
- Signed artifacts cannot be silently overwritten — edits
  fork into a new version row, and the signed version is
  preserved unchanged.
- Audit captures **counts only** ("findings=N, chatter=N,
  uncertain=N, annotations=N"); the verbatim source text and
  proposed annotation contents are never written to audit.

## Buyer benefits

| Audience                              | Benefit                                                                                  |
| ------------------------------------- | ---------------------------------------------------------------------------------------- |
| Clinic owners                         | Faster post-visit close-out; less after-hours documentation.                             |
| Practice administrators               | Consistent retinal documentation; cleaner audit story per provider.                      |
| Health-system innovation leaders      | A scribe surface they can defend in front of clinical and compliance reviewers.          |
| Enterprise procurement                | Conservative AI claim surface; deterministic v1 with an explicit upgrade path.           |
| Government / public-sector buyers     | Provider-in-the-loop architecture; PHI-safe audit; honest about what is and isn't certified. |

## Compliance-safe limitations (read this before you pitch)

- **Not a certified EHR.** ChartNav is a clinical workflow and
  charting surface; it does not claim ONC certification.
- **Not autonomous diagnosis.** The AI surfaces findings; the
  provider diagnoses, treats, and signs.
- **Not perfect transcription.** Phrases the filter does not
  recognize are surfaced as *uncertain* rather than guessed.
- **English-only v1.** Multilingual recognition is not in scope
  for v1.
- **Allowlist-bound.** Findings outside the v1 allowlist are not
  auto-recognized; the provider can place them manually with
  the labeled-symbol tool.

## What's next

- LLM-backed v2 of the filter (same `analyze()` contract;
  v1 remains as fallback and regression baseline).
- Symbol palette expansion (per-finding glyphs, eraser, drag /
  move, anterior-segment template).
- STT pipeline integration so the scribe can run on real-time
  encounter audio rather than typed paste.
- Rendered PNG/PDF snapshot generation for export and
  print-to-chart workflows.

---

**Contact:** Your ChartNav account contact. Pricing, deployment
options, and pilot terms available on request. ChartNav is built
by ARCG Systems.
