// apps/web/src/NoteQualityFlagsPanel.tsx
//
// Renders the rules-based quality-check output from
// `noteQualityChecks.ts` as a compact, clinician-friendly panel.
// Block-severity flags surface first (the UI consumer is expected
// to gate the "Ready for sign-off" affordance on these being
// acknowledged or resolved). Warns and infos follow in priority
// order.
//
// The panel is deliberately not chatty. It does not invent
// guidance, does not paraphrase clinical content, and does not
// suggest treatments. Each flag is a one-line message + an
// optional action chip the caller wires up.
//
// Caller contract:
//   <NoteQualityFlagsPanel
//     draftText={draft}
//     context={{ encounterLaterality: "OD", specialty: "retina" }}
//     onAcknowledge={(code) => ...}
//   />
//
// `onAcknowledge` is optional — when not provided, the action chip
// is omitted. Acknowledgement is operator-side state; ChartNav
// does not silently downgrade a flag for the provider.

import { useMemo } from "react";
import {
  runNoteQualityChecks,
  severityCounts,
  type QualityCheckContext,
  type QualityFlag,
  type QualityFlagCode,
  type QualityFlagSeverity,
} from "./noteQualityChecks";

interface Props {
  draftText: string;
  context?: QualityCheckContext;
  /** Set of flag codes the operator has already acknowledged. The
   *  panel still renders them but tags them as acknowledged so the
   *  contract trail is preserved. */
  acknowledgedCodes?: Set<QualityFlagCode>;
  /** Called when the operator clicks the action chip on a
   *  not-yet-acknowledged flag. */
  onAcknowledge?: (code: QualityFlagCode) => void;
}

const SEVERITY_ORDER: QualityFlagSeverity[] = ["block", "warn", "info"];

function severityLabel(s: QualityFlagSeverity): string {
  if (s === "block") return "Blocking";
  if (s === "warn") return "Warning";
  return "Info";
}

export function NoteQualityFlagsPanel({
  draftText,
  context,
  acknowledgedCodes,
  onAcknowledge,
}: Props) {
  const result = useMemo(
    () => runNoteQualityChecks(draftText, context),
    [draftText, context],
  );
  const counts = useMemo(() => severityCounts(result), [result]);

  // Group flags by severity, preserving order within each group.
  const grouped = useMemo(() => {
    const map: Record<QualityFlagSeverity, QualityFlag[]> = {
      block: [],
      warn: [],
      info: [],
    };
    for (const f of result.flags) map[f.severity].push(f);
    return map;
  }, [result]);

  return (
    <section
      className="note-quality-panel"
      data-testid="note-quality-panel"
      aria-label="Note quality flags"
    >
      <header className="note-quality-panel__header">
        <div>
          <h4
            className="note-quality-panel__title"
            data-testid="note-quality-panel-title"
          >
            Note quality checks
          </h4>
          <p className="note-quality-panel__subtitle subtle-note">
            Rules-based linter. Provider review remains the source of
            truth — ChartNav does not auto-correct, auto-grade, or
            replace clinical judgement.
          </p>
        </div>
        <dl
          className="note-quality-panel__counts"
          data-testid="note-quality-panel-counts"
        >
          <div>
            <dt>Completeness</dt>
            <dd data-testid="note-quality-panel-completeness">
              {result.completenessPercent}%
            </dd>
          </div>
          <div>
            <dt>Block</dt>
            <dd
              data-testid="note-quality-panel-count-block"
              className={
                counts.block > 0
                  ? "note-quality-panel__count note-quality-panel__count--block"
                  : "note-quality-panel__count"
              }
            >
              {counts.block}
            </dd>
          </div>
          <div>
            <dt>Warn</dt>
            <dd data-testid="note-quality-panel-count-warn">
              {counts.warn}
            </dd>
          </div>
          <div>
            <dt>Info</dt>
            <dd data-testid="note-quality-panel-count-info">
              {counts.info}
            </dd>
          </div>
        </dl>
      </header>

      {result.flags.length === 0 ? (
        <p
          className="note-quality-panel__empty"
          data-testid="note-quality-panel-empty"
        >
          No flags raised on the current draft.
        </p>
      ) : (
        <ul
          className="note-quality-panel__flags"
          data-testid="note-quality-panel-flags"
        >
          {SEVERITY_ORDER.flatMap((sev) =>
            grouped[sev].map((flag, idx) => {
              const acked =
                acknowledgedCodes?.has(flag.code) ?? false;
              return (
                <li
                  key={`${flag.code}-${sev}-${idx}`}
                  className={
                    "note-quality-panel__flag "
                    + `note-quality-panel__flag--${sev}`
                    + (acked ? " note-quality-panel__flag--acked" : "")
                  }
                  data-testid={`note-quality-panel-flag-${flag.code}`}
                  data-severity={sev}
                  data-acknowledged={acked ? "true" : "false"}
                >
                  <span
                    className={
                      "note-quality-panel__pill "
                      + `note-quality-panel__pill--${sev}`
                    }
                  >
                    {severityLabel(sev)}
                  </span>
                  <p className="note-quality-panel__message">
                    {flag.message}
                  </p>
                  {flag.actionLabel && onAcknowledge && !acked && (
                    <button
                      type="button"
                      className="btn btn--secondary note-quality-panel__action"
                      data-testid={`note-quality-panel-ack-${flag.code}`}
                      onClick={() => onAcknowledge(flag.code)}
                    >
                      {flag.actionLabel}
                    </button>
                  )}
                  {acked && (
                    <span
                      className="note-quality-panel__acked-mark"
                      data-testid={`note-quality-panel-acked-${flag.code}`}
                    >
                      Acknowledged
                    </span>
                  )}
                </li>
              );
            }),
          )}
        </ul>
      )}
      {result.hasBlockingFlags && (
        <p
          className="note-quality-panel__block-hint"
          data-testid="note-quality-panel-block-hint"
        >
          Blocking flags must be acknowledged or resolved before this
          draft is treated as ready for provider sign-off.
        </p>
      )}
    </section>
  );
}
