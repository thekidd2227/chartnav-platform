// PreVisitBriefPanel — provider-facing pre-visit summary of the
// existing ChartNav chart for one patient.
//
// Phase 10. The panel:
//   - calls POST /pre-visit-briefs/generate (audited) on click
//   - or auto-loads via GET /pre-visit-brief on mount (read-only,
//     no audit)
//   - renders source counts, last-visit recap, active issues,
//     retinal/scribe/summary section blocks, pending items,
//     suggested review items, and explicit data gaps
//   - shows the provider-review notice prominently
//   - does NOT render any patient-send action, order/coding
//     button, or autonomous-diagnosis language

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  PreVisitBrief,
  generatePatientPreVisitBrief,
  getPatientPreVisitBrief,
} from "./api";

interface Props {
  identity: string;
  patientId: number;
  encounterId: number | null;
}

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | null;

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

function CountTable({ counts }: { counts: Record<string, number> }) {
  const keys = Object.keys(counts).sort();
  return (
    <dl
      className="pre-visit-brief-panel__counts"
      data-testid="pre-visit-brief-counts"
    >
      {keys.map((k) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd data-testid={`pre-visit-brief-count-${k}`}>{counts[k]}</dd>
        </div>
      ))}
    </dl>
  );
}

export function PreVisitBriefPanel({ identity, patientId }: Props) {
  const [brief, setBrief] = useState<PreVisitBrief | null>(null);
  const [banner, setBanner] = useState<Banner>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setBusy(true);
      const b = await getPatientPreVisitBrief(identity, patientId);
      setBrief(b);
      setBanner(null);
    } catch (err) {
      setBanner({
        kind: "error",
        msg: `Could not load pre-visit brief: ${friendly(err)}`,
      });
    } finally {
      setBusy(false);
    }
  }, [identity, patientId]);

  useEffect(() => {
    load();
  }, [load]);

  const onGenerate = useCallback(async () => {
    try {
      setBusy(true);
      const b = await generatePatientPreVisitBrief(identity, patientId);
      setBrief(b);
      setBanner({ kind: "ok", msg: "Pre-visit brief regenerated." });
    } catch (err) {
      setBanner({
        kind: "error",
        msg: `Generate failed: ${friendly(err)}`,
      });
    } finally {
      setBusy(false);
    }
  }, [identity, patientId]);

  return (
    <div className="pre-visit-brief-panel" data-testid="pre-visit-brief-panel">
      <header className="pre-visit-brief-panel__header">
        <h3>Pre-visit brief</h3>
        <p
          className="pre-visit-brief-panel__hint"
          data-testid="pre-visit-brief-banner-copy"
        >
          Pre-visit brief — provider review required. This brief
          summarizes available ChartNav records and may be incomplete.
        </p>
      </header>

      {banner && (
        <div
          role="status"
          data-testid="pre-visit-brief-banner"
          className={`flash flash--${banner.kind}`}
        >
          {banner.msg}
        </div>
      )}

      <div className="pre-visit-brief-panel__actions">
        <button
          type="button"
          onClick={onGenerate}
          disabled={busy}
          data-testid="pre-visit-brief-generate"
        >
          Generate pre-visit brief
        </button>
        {brief && (
          <span
            className="muted"
            data-testid="pre-visit-brief-generated-at"
          >
            Generated at {brief.generated_at}
          </span>
        )}
      </div>

      {!brief ? (
        <p className="muted" data-testid="pre-visit-brief-empty">
          No brief loaded yet for this patient.
        </p>
      ) : (
        <div className="pre-visit-brief-panel__body">
          <section className="pre-visit-brief-panel__section">
            <h4>Source counts</h4>
            <CountTable counts={brief.source_counts} />
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Last visit</h4>
            <p data-testid="pre-visit-brief-last-visit">
              {brief.last_visit_summary || "—"}
            </p>
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Active issues from chart</h4>
            {brief.active_issues.length === 0 ? (
              <p
                className="muted"
                data-testid="pre-visit-brief-active-issues-empty"
              >
                No active issues recorded in finalized chart content.
              </p>
            ) : (
              <ul data-testid="pre-visit-brief-active-issues">
                {brief.active_issues.map((it, i) => (
                  <li key={i}>{it}</li>
                ))}
              </ul>
            )}
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Retinal artifacts</h4>
            <dl
              className="pre-visit-brief-panel__retinal"
              data-testid="pre-visit-brief-retinal"
            >
              <div>
                <dt>Total</dt>
                <dd>{brief.retinal_artifact_summary.total}</dd>
              </div>
              <div>
                <dt>Signed</dt>
                <dd>{brief.retinal_artifact_summary.signed_count}</dd>
              </div>
              <div>
                <dt>Unsigned</dt>
                <dd>{brief.retinal_artifact_summary.unsigned_count}</dd>
              </div>
              {brief.retinal_artifact_summary.latest_signed && (
                <div>
                  <dt>Latest signed</dt>
                  <dd
                    data-testid="pre-visit-brief-retinal-latest-signed"
                  >
                    #{brief.retinal_artifact_summary.latest_signed.id}
                    {" · "}
                    {brief.retinal_artifact_summary.latest_signed.title || "(untitled)"}
                  </dd>
                </div>
              )}
            </dl>
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Recent scribe session</h4>
            {brief.recent_scribe_session_summary.session_id === null ? (
              <p
                className="muted"
                data-testid="pre-visit-brief-scribe-none"
              >
                No scribe session on file.
              </p>
            ) : (
              <dl data-testid="pre-visit-brief-scribe">
                <div>
                  <dt>Session</dt>
                  <dd>
                    #{brief.recent_scribe_session_summary.session_id}{" "}
                    ({brief.recent_scribe_session_summary.status})
                  </dd>
                </div>
                {brief.recent_scribe_session_summary.chief_complaint_excerpt && (
                  <div>
                    <dt>Chief complaint excerpt</dt>
                    <dd>
                      {brief.recent_scribe_session_summary.chief_complaint_excerpt}
                    </dd>
                  </div>
                )}
                {brief.recent_scribe_session_summary.plan_excerpt && (
                  <div>
                    <dt>Plan excerpt</dt>
                    <dd>
                      {brief.recent_scribe_session_summary.plan_excerpt}
                    </dd>
                  </div>
                )}
              </dl>
            )}
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Patient summary context</h4>
            {brief.patient_summary_context.summary_id === null ? (
              <p
                className="muted"
                data-testid="pre-visit-brief-summary-none"
              >
                No patient summary on file.
              </p>
            ) : (
              <dl data-testid="pre-visit-brief-summary">
                <div>
                  <dt>Summary</dt>
                  <dd>
                    #{brief.patient_summary_context.summary_id}{" "}
                    ({brief.patient_summary_context.status})
                  </dd>
                </div>
                {brief.patient_summary_context.plain_language_excerpt && (
                  <div>
                    <dt>Excerpt</dt>
                    <dd>
                      {brief.patient_summary_context.plain_language_excerpt}
                    </dd>
                  </div>
                )}
              </dl>
            )}
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Pending items</h4>
            {brief.pending_items.length === 0 ? (
              <p
                className="muted"
                data-testid="pre-visit-brief-pending-empty"
              >
                No pending items.
              </p>
            ) : (
              <ul data-testid="pre-visit-brief-pending">
                {brief.pending_items.map((p, i) => (
                  <li key={i}>
                    {p.kind} #{p.id} ({p.status})
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Suggested review items</h4>
            {brief.suggested_review_items.length === 0 ? (
              <p
                className="muted"
                data-testid="pre-visit-brief-suggested-empty"
              >
                No items awaiting provider review.
              </p>
            ) : (
              <ul data-testid="pre-visit-brief-suggested">
                {brief.suggested_review_items.map((s, i) => (
                  <li key={i}>
                    {s.kind} #{s.id} — {s.reason}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="pre-visit-brief-panel__section">
            <h4>Data gaps</h4>
            {brief.data_gaps.length === 0 ? (
              <p
                className="muted"
                data-testid="pre-visit-brief-gaps-empty"
              >
                No gaps detected in available ChartNav records.
              </p>
            ) : (
              <ul data-testid="pre-visit-brief-gaps">
                {brief.data_gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
