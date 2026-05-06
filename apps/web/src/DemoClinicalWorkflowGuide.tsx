// DemoClinicalWorkflowGuide — Phase 13.
//
// A small, collapsible in-app guide that explains the existing
// ChartNav clinical workflow in seven steps. Surfaces the same
// safety contract the panels themselves enforce — never claims
// ChartNav diagnoses, orders, bills, sends referrals, or messages
// patients automatically.
//
// This component is a *guide*, not a feature. It does not call any
// API, does not write to any record, and does not surface any
// actionable order / coding / referral / patient-message control.

import { useState } from "react";

interface Props {
  /**
   * The patient's display name, used in step headers so the guide
   * makes sense in context. Optional — when not provided the guide
   * falls back to a generic phrase.
   */
  patientDisplay?: string;
}

const STEPS: { id: string; title: string; body: string }[] = [
  {
    id: "step-1-scribe",
    title: "1. Review the AI scribe session",
    body:
      "Open the Scribe Session panel. The provider drafts, processes, " +
      "reviews, and finalizes the structured note. Every transition " +
      "is explicit; ChartNav never finalizes on the provider's behalf.",
  },
  {
    id: "step-2-proposals",
    title: "2. Generate retinal diagram proposals",
    body:
      "From the Eye Diagram panel, paste or pick the findings text " +
      "and ask ChartNav to suggest annotations. Proposals are read-" +
      "only: they enter the chart only after the provider explicitly " +
      "applies them.",
  },
  {
    id: "step-3-apply",
    title: "3. Apply approved proposals to the OD/OS diagram",
    body:
      "The provider chooses which proposed annotations to apply. " +
      "Anything that lands on the diagram is tagged " +
      "`source=ai_approved` so it stays auditable.",
  },
  {
    id: "step-4-sign",
    title: "4. Save and sign the retinal diagram",
    body:
      "Save the unsigned artifact, review the drawing, then sign it. " +
      "Signed artifacts are immutable in place; further edits create " +
      "an explicit fork.",
  },
  {
    id: "step-5-summary",
    title: "5. Generate a patient-friendly summary",
    body:
      "From the Patient Summary panel, draft a plain-language recap. " +
      "The provider edits, marks reviewed, and finalizes. ChartNav " +
      "never sends the summary to the patient.",
  },
  {
    id: "step-6-brief",
    title: "6. Generate the pre-visit brief",
    body:
      "Open the Pre-Visit Brief panel and click Generate. It " +
      "summarizes available ChartNav records and lists explicit data " +
      "gaps. It is review context, not a clinical decision.",
  },
  {
    id: "step-7-actions",
    title: "7. Review the provider action queue",
    body:
      "Open the Provider Action Queue panel. ChartNav surfaces " +
      "review tasks (workflow completion, clinical-language flags, " +
      "data-hygiene). The provider Accepts, Dismisses, or Completes " +
      "each one. Nothing is acted on automatically.",
  },
];

const SAFETY_LINES: string[] = [
  "ChartNav supports documentation and review workflows.",
  "ChartNav does not diagnose, order, bill, send referrals, or message patients automatically.",
  "Every artifact requires explicit provider review before it is treated as final.",
];

export function DemoClinicalWorkflowGuide({ patientDisplay }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="demo-clinical-workflow-guide"
      data-testid="demo-clinical-workflow-guide"
    >
      <header className="demo-clinical-workflow-guide__header">
        <h3>Demo workflow guide</h3>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          data-testid="demo-clinical-workflow-guide-toggle"
        >
          {open ? "Hide demo workflow guide" : "Show demo workflow guide"}
        </button>
      </header>

      <p
        className="demo-clinical-workflow-guide__lead"
        data-testid="demo-clinical-workflow-guide-lead"
      >
        Walk a buyer, pilot user, advisor, or investor through the full
        ChartNav ophthalmology workflow{" "}
        {patientDisplay ? `for ${patientDisplay}` : "for the demo patient"} in
        about five minutes. Every step is provider-reviewed.
      </p>

      {open && (
        <div
          className="demo-clinical-workflow-guide__body"
          data-testid="demo-clinical-workflow-guide-body"
        >
          <section
            className="demo-clinical-workflow-guide__safety"
            data-testid="demo-clinical-workflow-guide-safety"
          >
            <h4>What ChartNav is — and is not</h4>
            <ul>
              {SAFETY_LINES.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </section>

          <section className="demo-clinical-workflow-guide__steps">
            <h4>Demo workflow checklist</h4>
            <ol data-testid="demo-clinical-workflow-guide-checklist">
              {STEPS.map((step) => (
                <li
                  key={step.id}
                  data-testid={`demo-clinical-workflow-guide-${step.id}`}
                >
                  <strong>{step.title}</strong>
                  <p>{step.body}</p>
                </li>
              ))}
            </ol>
          </section>

          <p
            className="demo-clinical-workflow-guide__footnote"
            data-testid="demo-clinical-workflow-guide-footnote"
          >
            Provider review required at every step. See{" "}
            <code>docs/demo/chartnav-clinical-workflow-demo-script.md</code>{" "}
            for the full demo script and click path.
          </p>
        </div>
      )}
    </div>
  );
}
