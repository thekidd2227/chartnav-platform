// GuidedDemoMode — Phase 15.
//
// Sticky sales-demo orchestrator. Renders ONLY when the URL query
// includes `?demo=1` (or when localStorage `chartnav.demoMode === "1"`).
// Default off — normal providers never see this surface.
//
// What it does:
//   - shows a 'DEMO MODE' badge and a deterministic 8-step stepper
//     describing the ChartNav ophthalmology workflow;
//   - lets the presenter advance through the steps with a single
//     button while the rest of the workspace stays put;
//   - exposes a Reset Demo button that clears the demo step
//     pointer back to step 1 and prints a reset reminder.
//
// What it does NOT do:
//   - it does not call any API;
//   - it does not write to any clinical record;
//   - it does not surface order / coding / referral / patient-message
//     buttons;
//   - it does not animate, redesign, or restyle existing panels;
//   - it does not change clinical lifecycle behavior.
//
// All copy is provider-review-safe. The negative-assertion banner
// "ChartNav supports documentation and review workflows. ChartNav
// does not diagnose, order, bill, send referrals, or message
// patients automatically." renders on every step.

import { useCallback, useEffect, useMemo, useState } from "react";

interface Props {
  /**
   * The patient's display name, used in the lead copy so the
   * stepper makes sense in context. Optional — when not provided
   * the stepper falls back to "the demo patient".
   */
  patientDisplay?: string;
}

interface DemoStep {
  id: string;
  shortLabel: string;
  title: string;
  body: string;
  cue: string;
}

export const DEMO_STEPS: DemoStep[] = [
  {
    id: "intake",
    shortLabel: "Intake",
    title: "1. Intake arrives",
    body:
      "The encounter row is open in the workspace. Confirm the " +
      "identity badge and the patient context.",
    cue:
      "Say: \"Every panel below is provider-reviewed. ChartNav " +
      "supports documentation; the provider decides.\"",
  },
  {
    id: "pre-visit-brief",
    shortLabel: "Pre-visit brief",
    title: "2. Pre-visit brief appears",
    body:
      "Open the Pre-visit brief panel and click Generate. Show the " +
      "source counts, the last-visit recap, and any explicit data " +
      "gaps.",
    cue:
      "Say: \"Derived view of available chart records. Data gaps " +
      "are explicit. Not a clinical decision.\"",
  },
  {
    id: "visit-begins",
    shortLabel: "Visit begins",
    title: "3. Visit begins",
    body:
      "Switch focus to the Scribe Session panel. Paste the demo " +
      "source text and create the session.",
    cue:
      "Say: \"Source goes in; the engine drafts a structured note. " +
      "Provider reviews before anything is final.\"",
  },
  {
    id: "scribe",
    shortLabel: "Scribe",
    title: "4. AI scribe session runs",
    body:
      "Click Process, then Mark reviewed, then Finalize. Show that " +
      "Finalize is an explicit click — not automatic.",
    cue:
      "Say: \"Provider review is mandatory. Finalize is an explicit " +
      "click. Finalized sessions are immutable.\"",
  },
  {
    id: "retinal-proposal",
    shortLabel: "Retinal proposal",
    title: "5. Retinal proposal generated",
    body:
      "Open the Eye diagram panel. Generate proposals from " +
      "findings, apply one, save, and sign.",
    cue:
      "Say: \"Proposals are read-only suggestions. Anything that " +
      "lands on the diagram is tagged source=ai_approved.\"",
  },
  {
    id: "action-queue",
    shortLabel: "Action queue",
    title: "6. Provider review queue updates",
    body:
      "Open the Provider action queue panel. Click Generate. Show " +
      "Accept on one, Dismiss on a second, Complete on the " +
      "accepted item.",
    cue:
      "Say: \"Suggested → accepted → completed; dismissed is " +
      "terminal. Every transition is the provider's explicit " +
      "click.\"",
  },
  {
    id: "patient-summary",
    shortLabel: "Patient summary",
    title: "7. Patient-friendly summary generated",
    body:
      "Open the Patient summary panel. Create from the finalized " +
      "scribe, edit if you want, mark reviewed, finalize.",
    cue:
      "Say: \"Provider-facing summary. ChartNav never sends to a " +
      "patient. Finalized summaries are immutable.\"",
  },
  {
    id: "completed",
    shortLabel: "Done",
    title: "8. Workflow completed",
    body:
      "Close the demo on the read-only finalized states. Reset the " +
      "stepper before the next demo.",
    cue:
      "Say: \"Five minutes, seven steps, every step provider-" +
      "reviewed. Questions?\"",
  },
];

const SAFETY_BULLETS: string[] = [
  "ChartNav supports documentation and review workflows.",
  "ChartNav does not diagnose, order, bill, send referrals, or message patients automatically.",
  "Every clinical artifact requires explicit provider review before it is treated as final.",
];

const STORAGE_KEY = "chartnav.demoStep";

function readEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (window.location.search.includes("demo=1")) return true;
    return window.localStorage.getItem("chartnav.demoMode") === "1";
  } catch {
    return false;
  }
}

function readStep(): number {
  if (typeof window === "undefined") return 0;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return 0;
    const n = Number.parseInt(raw, 10);
    if (Number.isNaN(n) || n < 0 || n >= DEMO_STEPS.length) return 0;
    return n;
  } catch {
    return 0;
  }
}

function writeStep(n: number): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, String(n));
  } catch {
    // localStorage may be disabled — surface still works in-memory.
  }
}

export function GuidedDemoMode({ patientDisplay }: Props) {
  const [enabled, setEnabled] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);

  // Read enabled state + stored step on mount. Re-check enabled
  // when navigation happens (URL flips).
  useEffect(() => {
    setEnabled(readEnabled());
    setStepIdx(readStep());
    const onPop = () => setEnabled(readEnabled());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const step = useMemo(() => DEMO_STEPS[stepIdx], [stepIdx]);
  const isFirst = stepIdx === 0;
  const isLast = stepIdx === DEMO_STEPS.length - 1;

  const advance = useCallback(() => {
    setStepIdx((i) => {
      const n = Math.min(i + 1, DEMO_STEPS.length - 1);
      writeStep(n);
      return n;
    });
  }, []);

  const back = useCallback(() => {
    setStepIdx((i) => {
      const n = Math.max(i - 1, 0);
      writeStep(n);
      return n;
    });
  }, []);

  const reset = useCallback(() => {
    setStepIdx(0);
    writeStep(0);
  }, []);

  if (!enabled) return null;

  return (
    <div
      className="guided-demo-mode"
      data-testid="guided-demo-mode"
      role="region"
      aria-label="Guided demo mode"
    >
      <div className="guided-demo-mode__header">
        <span
          className="guided-demo-mode__badge"
          data-testid="guided-demo-mode-badge"
        >
          DEMO MODE · fake data only
        </span>
        <span
          className="muted"
          data-testid="guided-demo-mode-step-counter"
        >
          Step {stepIdx + 1} of {DEMO_STEPS.length}
        </span>
      </div>

      <p
        className="guided-demo-mode__lead"
        data-testid="guided-demo-mode-lead"
      >
        Walk through the existing ChartNav ophthalmology workflow{" "}
        {patientDisplay ? `for ${patientDisplay}` : "for the demo patient"}.
        Every step is provider-reviewed.
      </p>

      <ol
        className="guided-demo-mode__progress"
        data-testid="guided-demo-mode-progress"
        aria-label="Demo workflow progress"
      >
        {DEMO_STEPS.map((s, i) => {
          const status =
            i < stepIdx
              ? "complete"
              : i === stepIdx
              ? "current"
              : "upcoming";
          return (
            <li
              key={s.id}
              data-testid={`guided-demo-mode-step-${s.id}`}
              data-step-status={status}
              className={`guided-demo-mode__progress-item guided-demo-mode__progress-item--${status}`}
              aria-current={status === "current" ? "step" : undefined}
            >
              <span className="guided-demo-mode__progress-num">
                {i + 1}
              </span>
              <span className="guided-demo-mode__progress-label">
                {s.shortLabel}
              </span>
            </li>
          );
        })}
      </ol>

      <section
        className="guided-demo-mode__current"
        data-testid="guided-demo-mode-current-step"
      >
        <h4 data-testid="guided-demo-mode-current-title">{step.title}</h4>
        <p data-testid="guided-demo-mode-current-body">{step.body}</p>
        <p
          className="guided-demo-mode__cue"
          data-testid="guided-demo-mode-current-cue"
        >
          <strong>Cue: </strong>
          {step.cue}
        </p>
      </section>

      <section
        className="guided-demo-mode__safety"
        data-testid="guided-demo-mode-safety"
      >
        <h5>What ChartNav is — and is not</h5>
        <ul>
          {SAFETY_BULLETS.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      </section>

      <div
        className="guided-demo-mode__controls"
        data-testid="guided-demo-mode-controls"
      >
        <button
          type="button"
          onClick={back}
          disabled={isFirst}
          data-testid="guided-demo-mode-back"
        >
          Previous step
        </button>
        <button
          type="button"
          onClick={advance}
          disabled={isLast}
          data-testid="guided-demo-mode-next"
        >
          Next step
        </button>
        <button
          type="button"
          onClick={reset}
          data-testid="guided-demo-mode-reset"
        >
          Reset demo
        </button>
        <span
          className="muted"
          data-testid="guided-demo-mode-footer-note"
        >
          Demo state lives in browser localStorage; no API calls are
          made.
        </span>
      </div>
    </div>
  );
}
