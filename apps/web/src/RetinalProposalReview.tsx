// RetinalProposalReview — Phase 6 review surface.
//
// Provider-facing review panel for findings → diagram proposals.
// The endpoint never writes to chart_artifacts. Nothing here writes to
// the persisted drawing either. Applied proposals are handed back via
// `onApply`; the parent panel inserts the annotation into the working
// DrawingDocument and persists later through the normal save flow.
//
// Rejected proposals stay in transient UI state only and never reach
// `onApply`. They are dropped when the panel unmounts or is dismissed.

import { useMemo, useState } from "react";

import {
  RetinalProposal,
  ProposalMissingFlag,
} from "./retinalAnnotations";

interface ProposalSummary {
  high: number;
  medium: number;
  low: number;
  needs_review: boolean;
}

interface Props {
  clinicalText: string;
  ignoredChatter: string[];
  uncertainPhrases: string[];
  proposals: RetinalProposal[];
  missingFlags: ProposalMissingFlag[];
  confidenceSummary: ProposalSummary;
  onApply: (proposal: RetinalProposal) => void;
  onDismiss: () => void;
  /** When true, applying proposals is blocked (e.g. signed artifact). */
  disabled?: boolean;
}

type ProposalState = "pending" | "applied" | "rejected";

export function RetinalProposalReview({
  clinicalText,
  ignoredChatter,
  uncertainPhrases,
  proposals,
  missingFlags,
  confidenceSummary,
  onApply,
  onDismiss,
  disabled = false,
}: Props) {
  // Per-proposal state. Applied proposals stick around in the list with
  // an "applied" indicator so the provider can see what's already been
  // accepted; rejected ones disappear from the actionable area.
  const [state, setState] = useState<Record<string, ProposalState>>(() => {
    const out: Record<string, ProposalState> = {};
    for (const p of proposals) out[p.proposal_id] = "pending";
    return out;
  });

  const counts = useMemo(() => {
    let pending = 0;
    let applied = 0;
    let rejected = 0;
    for (const p of proposals) {
      const s = state[p.proposal_id] ?? "pending";
      if (s === "pending") pending += 1;
      else if (s === "applied") applied += 1;
      else rejected += 1;
    }
    return { pending, applied, rejected };
  }, [proposals, state]);

  const apply = (p: RetinalProposal) => {
    if (disabled) return;
    if (state[p.proposal_id] === "applied") return;
    onApply(p);
    setState((prev) => ({ ...prev, [p.proposal_id]: "applied" }));
  };

  const reject = (p: RetinalProposal) => {
    if (disabled) return;
    setState((prev) => ({ ...prev, [p.proposal_id]: "rejected" }));
  };

  const applyRemaining = () => {
    if (disabled) return;
    const next: Record<string, ProposalState> = { ...state };
    for (const p of proposals) {
      if ((state[p.proposal_id] ?? "pending") === "pending") {
        onApply(p);
        next[p.proposal_id] = "applied";
      }
    }
    setState(next);
  };

  const rejectRemaining = () => {
    if (disabled) return;
    setState((prev) => {
      const next: Record<string, ProposalState> = { ...prev };
      for (const p of proposals) {
        if ((prev[p.proposal_id] ?? "pending") === "pending") {
          next[p.proposal_id] = "rejected";
        }
      }
      return next;
    });
  };

  return (
    <section
      className="proposal-review"
      data-testid="retinal-proposal-review"
      aria-label="Retinal diagram proposal review"
    >
      <header className="proposal-review__header">
        <strong>Proposed by ChartNav — review required</strong>
        <p className="muted">
          Nothing is added to the diagram until you apply it. Rejected
          proposals are not saved.
        </p>
        <button
          type="button"
          data-testid="proposal-review-dismiss"
          onClick={onDismiss}
        >
          Dismiss panel
        </button>
      </header>

      <dl className="proposal-review__summary">
        <div>
          <dt>High confidence</dt>
          <dd data-testid="proposal-summary-high">{confidenceSummary.high}</dd>
        </div>
        <div>
          <dt>Medium confidence</dt>
          <dd data-testid="proposal-summary-medium">{confidenceSummary.medium}</dd>
        </div>
        <div>
          <dt>Low confidence</dt>
          <dd data-testid="proposal-summary-low">{confidenceSummary.low}</dd>
        </div>
        <div>
          <dt>Pending review</dt>
          <dd data-testid="proposal-summary-pending">{counts.pending}</dd>
        </div>
      </dl>

      {missingFlags.length > 0 && (
        <div
          className="proposal-review__missing"
          data-testid="proposal-missing-flags"
        >
          <strong>Needs your input</strong>
          <ul>
            {missingFlags.map((m, i) => (
              <li key={`${m.code}-${i}`}>
                <span className="muted">[{m.code}]</span> {m.detail}
                <div className="muted">“{m.source_phrase}”</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {ignoredChatter.length > 0 && (
        <details data-testid="proposal-chatter">
          <summary>Ignored chatter ({ignoredChatter.length})</summary>
          <ul>
            {ignoredChatter.map((c, i) => (
              <li key={i} className="muted">
                {c}
              </li>
            ))}
          </ul>
        </details>
      )}

      {uncertainPhrases.length > 0 && (
        <details data-testid="proposal-uncertain">
          <summary>Uncertain phrases ({uncertainPhrases.length})</summary>
          <ul>
            {uncertainPhrases.map((u, i) => (
              <li key={i} className="muted">
                {u}
              </li>
            ))}
          </ul>
        </details>
      )}

      {clinicalText && (
        <details data-testid="proposal-clinical-text">
          <summary>Parsed clinical text</summary>
          <pre className="muted">{clinicalText}</pre>
        </details>
      )}

      {proposals.length === 0 ? (
        <p className="muted" data-testid="proposal-empty">
          No proposals were generated for this findings text.
        </p>
      ) : (
        <>
          <div className="proposal-review__bulk">
            <button
              type="button"
              data-testid="proposal-apply-remaining"
              onClick={applyRemaining}
              disabled={disabled || counts.pending === 0}
            >
              Apply remaining ({counts.pending})
            </button>
            <button
              type="button"
              data-testid="proposal-reject-remaining"
              onClick={rejectRemaining}
              disabled={disabled || counts.pending === 0}
            >
              Reject remaining
            </button>
          </div>

          <ul className="proposal-review__list" data-testid="proposal-list">
            {proposals.map((p) => {
              const s = state[p.proposal_id] ?? "pending";
              if (s === "rejected") return null;
              return (
                <li
                  key={p.proposal_id}
                  data-testid={`proposal-item-${p.proposal_id}`}
                  data-state={s}
                >
                  <div className="proposal-item__head">
                    <strong>
                      {p.eye} · {p.text}
                    </strong>
                    <span
                      className="muted"
                      data-testid={`proposal-band-${p.proposal_id}`}
                    >
                      {p.confidence_band} · {Math.round(p.confidence * 100)}%
                    </span>
                  </div>
                  <div className="proposal-item__source muted">
                    “{p.source_phrase}”
                  </div>
                  <div className="proposal-item__reason muted">{p.reason}</div>
                  {p.missing_flags.length > 0 && (
                    <div
                      className="proposal-item__missing muted"
                      data-testid={`proposal-missing-${p.proposal_id}`}
                    >
                      Missing: {p.missing_flags.join(", ")}
                    </div>
                  )}
                  <div className="proposal-item__actions">
                    <button
                      type="button"
                      data-testid={`proposal-apply-${p.proposal_id}`}
                      onClick={() => apply(p)}
                      disabled={disabled || s === "applied"}
                    >
                      {s === "applied" ? "Applied" : "Apply"}
                    </button>
                    <button
                      type="button"
                      data-testid={`proposal-reject-${p.proposal_id}`}
                      onClick={() => reject(p)}
                      disabled={disabled || s === "applied"}
                    >
                      Reject
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
