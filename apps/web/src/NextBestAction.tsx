// ROI wave 1 · item 2
//
// NextBestAction — computes the single primary action a doctor
// should take next based on the current encounter / inputs / notes
// state. Secondary options are rendered but visually subordinate.
//
// Decision tree (first match wins):
//
//   [No inputs]               → "Ingest transcript"
//   [Any input queued/proc.]  → "Process transcript"
//   [Input failed]            → "Retry ingestion"
//   [Input completed, no note]→ "Generate draft"
//   [Draft in 'draft']        → "Review findings" (with submit hint)
//   [Draft in 'provider_review' / 'revised'] → "Sign note"
//   [Draft signed, not exported] → "Export note"
//   [Signed + exported + transmit supported] → "Transmit to EHR"
//   [Signed + exported]       → "Done — nothing else to do"
//
// The component does NOT invoke the actions itself; it surfaces
// them through callbacks so NoteWorkspace stays the orchestrator
// of every side-effect.

import { EncounterInput, NoteVersion } from "./api";

export type NextBestKind =
  | "ingest"
  | "process"
  | "retry"
  | "generate"
  | "review"
  | "sign"
  | "export"
  | "transmit"
  | "done";

export interface NextBestHandlers {
  onFocusIngest?: () => void;
  onProcessLatest?: () => void;
  onRetryLatest?: () => void;
  onGenerate?: () => void;
  onFocusReview?: () => void;
  onRequestSign?: () => void;
  onExport?: () => void;
  onTransmit?: () => void;
}

interface Props {
  inputs: EncounterInput[];
  activeNote: NoteVersion | null;
  transmitSupported: boolean;
  canSign: boolean;
  loading: boolean;
  handlers: NextBestHandlers;
}

interface Plan {
  kind: NextBestKind;
  label: string;
  explain: string;
  actionLabel: string;
  run: (() => void) | undefined;
  disabled: boolean;
}

function computePlan(
  inputs: EncounterInput[],
  note: NoteVersion | null,
  transmitSupported: boolean,
  canSign: boolean,
  loading: boolean,
  h: NextBestHandlers
): Plan {
  // No inputs at all — the doctor needs to ingest a transcript /
  // audio / manual entry before anything else becomes meaningful.
  if (!inputs.length) {
    return {
      kind: "ingest",
      label: "Ingest transcript",
      explain:
        "No operator input on this encounter yet. Upload audio, paste a transcript, or record to kick off the pipeline.",
      actionLabel: "Open intake",
      run: h.onFocusIngest,
      disabled: loading || !h.onFocusIngest,
    };
  }

  // Any failed input? Prefer a retry action.
  const failed = inputs.find((i) => i.processing_status === "failed");
  if (failed) {
    return {
      kind: "retry",
      label: "Retry ingestion",
      explain: `Input #${failed.id} failed${failed.last_error_code ? " (" + failed.last_error_code + ")" : ""}. Retry or correct the transcript before drafting.`,
      actionLabel: "Retry latest failed",
      run: h.onRetryLatest,
      disabled: loading || !h.onRetryLatest,
    };
  }

  // Any input sitting in queued / processing — finish ingestion first.
  const stalled = inputs.find(
    (i) =>
      i.processing_status === "queued" ||
      i.processing_status === "processing"
  );
  if (stalled) {
    return {
      kind: "process",
      label: "Process transcript",
      explain: `Input #${stalled.id} is ${stalled.processing_status}. Advance it so findings can be generated.`,
      actionLabel: "Process now",
      run: h.onProcessLatest,
      disabled: loading || !h.onProcessLatest,
    };
  }

  // Inputs are done but no note drafted yet.
  const hasCompletedInput = inputs.some((i) => i.processing_status === "completed");
  if (hasCompletedInput && !note) {
    return {
      kind: "generate",
      label: "Generate draft",
      explain:
        "Transcript + findings are ready. Generate the first draft to surface the structured exam and narrative below.",
      actionLabel: "Generate now",
      run: h.onGenerate,
      disabled: loading || !h.onGenerate,
    };
  }

  if (note) {
    // Draft phase → verify / edit → submit.
    if (note.draft_status === "draft") {
      return {
        kind: "review",
        label: "Review findings",
        explain:
          "Draft is in 'draft'. Verify findings and edit the narrative; when you're satisfied, submit for review.",
        actionLabel: "Jump to draft",
        run: h.onFocusReview,
        disabled: loading || !h.onFocusReview,
      };
    }
    // Awaiting provider or after revise → sign is the next step.
    if (
      note.draft_status === "provider_review" ||
      note.draft_status === "revised"
    ) {
      const needsSafety =
        !note.missing_data_flags ||
        note.missing_data_flags.length > 0;
      return {
        kind: "sign",
        label: "Sign note",
        explain: needsSafety
          ? "Ready to sign. A safety checkpoint will confirm findings confidence and missing-data flags before locking the note."
          : "Ready to sign.",
        actionLabel: "Sign",
        run: h.onRequestSign,
        disabled: loading || !canSign || !h.onRequestSign,
      };
    }
    if (note.draft_status === "signed") {
      return {
        kind: "export",
        label: "Export note",
        explain:
          "Signed and immutable. Export a copy for your records or downstream systems.",
        actionLabel: "Export",
        run: h.onExport,
        disabled: loading || !h.onExport,
      };
    }
    if (note.draft_status === "exported") {
      if (transmitSupported) {
        return {
          kind: "transmit",
          label: "Transmit to external system",
          explain:
            "Exported. This deployment supports outbound transmit — send to the integrated system when ready.",
          actionLabel: "Transmit",
          run: h.onTransmit,
          disabled: loading || !h.onTransmit,
        };
      }
      return {
        kind: "done",
        label: "Done",
        explain:
          "Signed and exported. Nothing else needs to happen on this encounter.",
        actionLabel: "",
        run: undefined,
        disabled: true,
      };
    }
  }

  // Fallback — we got here with inputs but no completed one. Nudge
  // the doctor to process the latest input.
  return {
    kind: "process",
    label: "Process transcript",
    explain:
      "Waiting for an input to reach 'completed'. Process the latest input to move forward.",
    actionLabel: "Process latest",
    run: h.onProcessLatest,
    disabled: loading || !h.onProcessLatest,
  };
}

export function NextBestAction(props: Props) {
  const plan = computePlan(
    props.inputs,
    props.activeNote,
    props.transmitSupported,
    props.canSign,
    props.loading,
    props.handlers
  );

  return (
    <section
      className="nba"
      data-testid="nba"
      data-kind={plan.kind}
      role="region"
      aria-label="Next best action"
    >
      <div className="nba__body">
        <div className="nba__label">
          <span className="nba__eyebrow">Next best action</span>
          <h3 className="nba__title">{plan.label}</h3>
          <p className="nba__explain">{plan.explain}</p>
        </div>
        {plan.actionLabel && plan.run && (
          <button
            type="button"
            className="btn btn--primary nba__cta"
            data-testid="nba-cta"
            disabled={plan.disabled}
            onClick={plan.run}
          >
            {plan.actionLabel}
          </button>
        )}
      </div>
    </section>
  );
}
