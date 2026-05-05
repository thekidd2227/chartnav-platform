// ScribeSessionPanel — provider-facing AI scribe session workspace.
//
// Phase 8. One row per session = one unit of work between provider
// source/transcript text and a finalized clinical artifact. The panel
// surfaces the lifecycle state machine; nothing here finalizes a note
// without an explicit provider review + finalize action.
//
// Banner copy is provider-control language only: "Draft — provider
// review required" / "Nothing is finalized until the provider reviews
// and finalizes." No autonomous diagnosis claims. No external LLM
// language.

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  ScribeSession,
  ScribeSessionInputMode,
  ScribeSessionStatus,
  createPatientScribeSession,
  discardPatientScribeSession,
  finalizePatientScribeSession,
  getPatientScribeSession,
  listPatientScribeSessions,
  processPatientScribeSession,
  reviewPatientScribeSession,
  updatePatientScribeSession,
} from "./api";

interface Props {
  identity: string;
  patientId: number;
  encounterId: number | null;
}

type Banner =
  | { kind: "ok"; msg: string }
  | { kind: "error"; msg: string }
  | { kind: "info"; msg: string }
  | null;

const STATUS_LABEL: Record<ScribeSessionStatus, string> = {
  draft: "Draft",
  processing: "Processing",
  ready_for_review: "Ready for review",
  reviewed: "Reviewed",
  finalized: "Finalized",
  discarded: "Discarded",
};

const SECTION_ORDER: Array<{ key: string; label: string }> = [
  { key: "chief_complaint", label: "Chief complaint" },
  { key: "hpi", label: "HPI" },
  { key: "exam", label: "Exam" },
  { key: "assessment", label: "Assessment" },
  { key: "plan", label: "Plan" },
  { key: "unassigned_text", label: "Unassigned" },
];

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

export function ScribeSessionPanel({ identity, patientId, encounterId }: Props) {
  const [items, setItems] = useState<ScribeSession[]>([]);
  const [active, setActive] = useState<ScribeSession | null>(null);

  // Draft / draft-edit fields (only meaningful before review).
  const [inputMode, setInputMode] = useState<ScribeSessionInputMode>("pasted_text");
  const [sourceText, setSourceText] = useState<string>("");
  const [transcriptText, setTranscriptText] = useState<string>("");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [banner, setBanner] = useState<Banner>(null);
  const [busy, setBusy] = useState(false);

  // --- list + load helpers -------------------------------------------

  const refresh = useCallback(async () => {
    try {
      const res = await listPatientScribeSessions(identity, patientId);
      setItems(res.items);
    } catch (err) {
      setBanner({ kind: "error", msg: `Could not load scribe sessions: ${friendly(err)}` });
    }
  }, [identity, patientId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const resetDraft = useCallback(() => {
    setActive(null);
    setInputMode("pasted_text");
    setSourceText("");
    setTranscriptText("");
    setReviewNotes("");
    setBanner(null);
  }, []);

  const loadSession = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        const sess = await getPatientScribeSession(identity, patientId, id);
        setActive(sess);
        setInputMode(sess.input_mode);
        setSourceText(sess.source_text ?? "");
        setTranscriptText(sess.transcript_text ?? "");
        setReviewNotes(sess.review_notes ?? "");
        setBanner(null);
      } catch (err) {
        setBanner({ kind: "error", msg: `Load failed: ${friendly(err)}` });
      } finally {
        setBusy(false);
      }
    },
    [identity, patientId]
  );

  const isReadOnly = active?.is_terminal === true;

  // --- write helpers --------------------------------------------------

  const onCreate = useCallback(async () => {
    try {
      setBusy(true);
      const sess = await createPatientScribeSession(identity, patientId, {
        input_mode: inputMode,
        source_text: sourceText || undefined,
        transcript_text: transcriptText || undefined,
        encounter_id: encounterId ?? undefined,
      });
      setActive(sess);
      setBanner({ kind: "ok", msg: `Session #${sess.id} created (draft).` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Create failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [encounterId, identity, inputMode, patientId, refresh, sourceText, transcriptText]);

  const onUpdate = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const sess = await updatePatientScribeSession(
        identity,
        patientId,
        active.id,
        {
          input_mode: inputMode,
          source_text: sourceText,
          transcript_text: transcriptText,
          review_notes: reviewNotes,
        }
      );
      setActive(sess);
      setBanner({ kind: "ok", msg: "Saved draft." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Update failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, inputMode, patientId, refresh, reviewNotes, sourceText, transcriptText]);

  const onProcess = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const sess = await processPatientScribeSession(identity, patientId, active.id);
      setActive(sess);
      setBanner({
        kind: "info",
        msg: "Processed — review required before finalize.",
      });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Process failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh]);

  const onReview = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const sess = await reviewPatientScribeSession(
        identity,
        patientId,
        active.id,
        { review_notes: reviewNotes || undefined }
      );
      setActive(sess);
      setBanner({ kind: "ok", msg: "Marked reviewed." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Review failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh, reviewNotes]);

  const onFinalize = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const sess = await finalizePatientScribeSession(identity, patientId, active.id);
      setActive(sess);
      setBanner({ kind: "ok", msg: "Finalized." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Finalize failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh]);

  const onDiscard = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const sess = await discardPatientScribeSession(identity, patientId, active.id);
      setActive(sess);
      setBanner({ kind: "ok", msg: "Discarded." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Discard failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh]);

  // --- derived display ------------------------------------------------

  const structuredEntries = useMemo(() => {
    if (!active) return [] as Array<{ key: string; label: string; value: string }>;
    const note = active.structured_note_json || {};
    return SECTION_ORDER.filter((s) => (note as Record<string, string>)[s.key]).map((s) => ({
      key: s.key,
      label: s.label,
      value: (note as Record<string, string>)[s.key],
    }));
  }, [active]);

  const statusBadge = active ? STATUS_LABEL[active.status] : null;

  // --- render ---------------------------------------------------------

  return (
    <div className="scribe-session-panel" data-testid="scribe-session-panel">
      <header className="scribe-session-panel__header">
        <h3>AI scribe sessions</h3>
        <p className="scribe-session-panel__hint" data-testid="scribe-session-banner-copy">
          Draft — provider review required. Nothing is finalized until the
          provider reviews and finalizes.
        </p>
      </header>

      {banner && (
        <div
          role="status"
          data-testid="scribe-session-banner"
          className={`flash flash--${banner.kind}`}
        >
          {banner.msg}
        </div>
      )}

      <section className="scribe-session-panel__list">
        <div className="scribe-session-panel__list-header">
          <strong>Sessions</strong>
          <button type="button" onClick={resetDraft} disabled={busy} data-testid="scribe-session-new">
            New
          </button>
        </div>
        {items.length === 0 ? (
          <p className="muted" data-testid="scribe-session-empty">
            No sessions yet for this patient.
          </p>
        ) : (
          <ul data-testid="scribe-session-list">
            {items.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  data-testid={`scribe-session-load-${s.id}`}
                  onClick={() => loadSession(s.id)}
                  disabled={busy}
                >
                  #{s.id} · {STATUS_LABEL[s.status]}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="scribe-session-panel__editor">
        <div className="scribe-session-panel__meta">
          {active ? (
            <>
              <strong>#{active.id}</strong>
              <span
                className={`scribe-session-panel__badge scribe-session-panel__badge--${active.status}`}
                data-testid="scribe-session-status-badge"
              >
                {statusBadge}
              </span>
              <span className="muted">
                {" · "}created {active.created_at}
                {active.updated_at !== active.created_at && (
                  <> · updated {active.updated_at}</>
                )}
              </span>
            </>
          ) : (
            <span className="muted">New session (unsaved)</span>
          )}
        </div>

        {isReadOnly && (
          <div
            className="flash flash--info"
            data-testid="scribe-session-readonly-warning"
          >
            This session is {active!.status} and cannot be modified.
          </div>
        )}

        <label>
          <span>Input mode</span>
          <select
            value={inputMode}
            onChange={(e) => setInputMode(e.target.value as ScribeSessionInputMode)}
            disabled={busy || isReadOnly}
            data-testid="scribe-session-input-mode"
          >
            <option value="pasted_text">Pasted text</option>
            <option value="transcript">Transcript</option>
            <option value="audio_placeholder">Audio (placeholder)</option>
          </select>
        </label>

        <label>
          <span>Source text</span>
          <textarea
            rows={6}
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="scribe-session-source-text"
            placeholder={
              "Use headings to help the parser:\n" +
              "Chief complaint: ...\nHPI: ...\nExam: ...\nAssessment: ...\nPlan: ..."
            }
          />
        </label>

        <label>
          <span>Transcript text (optional)</span>
          <textarea
            rows={4}
            value={transcriptText}
            onChange={(e) => setTranscriptText(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="scribe-session-transcript-text"
          />
        </label>

        {active && active.draft_note_text && (
          <section
            className="scribe-session-panel__draft"
            data-testid="scribe-session-draft-note"
          >
            <strong>Draft note</strong>
            <pre>{active.draft_note_text}</pre>
          </section>
        )}

        {structuredEntries.length > 0 && (
          <section
            className="scribe-session-panel__structured"
            data-testid="scribe-session-structured-note"
          >
            <strong>Structured sections</strong>
            <dl>
              {structuredEntries.map((s) => (
                <div key={s.key} data-testid={`scribe-session-section-${s.key}`}>
                  <dt>{s.label}</dt>
                  <dd>{s.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        <label>
          <span>Review notes</span>
          <textarea
            rows={3}
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="scribe-session-review-notes"
          />
        </label>

        <div className="scribe-session-panel__actions">
          {!active && (
            <button
              type="button"
              onClick={onCreate}
              disabled={busy}
              data-testid="scribe-session-create"
            >
              Create draft
            </button>
          )}
          {active && active.status === "draft" && (
            <>
              <button
                type="button"
                onClick={onUpdate}
                disabled={busy}
                data-testid="scribe-session-update"
              >
                Save draft
              </button>
              <button
                type="button"
                onClick={onProcess}
                disabled={busy}
                data-testid="scribe-session-process"
              >
                Process
              </button>
              <button
                type="button"
                onClick={onDiscard}
                disabled={busy}
                data-testid="scribe-session-discard"
              >
                Discard
              </button>
            </>
          )}
          {active && active.status === "ready_for_review" && (
            <>
              <button
                type="button"
                onClick={onUpdate}
                disabled={busy}
                data-testid="scribe-session-update"
              >
                Save review notes
              </button>
              <button
                type="button"
                onClick={onReview}
                disabled={busy}
                data-testid="scribe-session-review"
              >
                Mark reviewed
              </button>
              <button
                type="button"
                onClick={onDiscard}
                disabled={busy}
                data-testid="scribe-session-discard"
              >
                Discard
              </button>
            </>
          )}
          {active && active.status === "reviewed" && (
            <>
              <button
                type="button"
                onClick={onFinalize}
                disabled={busy}
                data-testid="scribe-session-finalize"
              >
                Finalize
              </button>
              <button
                type="button"
                onClick={onDiscard}
                disabled={busy}
                data-testid="scribe-session-discard"
              >
                Discard
              </button>
            </>
          )}
          {/* finalized / discarded → no actions */}
        </div>
      </section>
    </div>
  );
}
