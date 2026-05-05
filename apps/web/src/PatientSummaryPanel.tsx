// PatientSummaryPanel — provider-facing patient-friendly summary workspace.
//
// Phase 9. The provider creates a draft (optionally seeded from a
// scribe session), reviews/edits it, marks reviewed, then finalizes.
// Discarded and finalized are immutable. The panel never sends
// anything to a patient — there is no patient-send button. Status
// transitions go through dedicated routes.

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  PatientSummary,
  PatientSummaryStatus,
  createPatientSummary,
  discardPatientSummary,
  finalizePatientSummary,
  getPatientSummary,
  listPatientSummaries,
  reviewPatientSummary,
  updatePatientSummary,
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

const STATUS_LABEL: Record<PatientSummaryStatus, string> = {
  draft: "Draft",
  reviewed: "Reviewed",
  finalized: "Finalized",
  discarded: "Discarded",
};

function friendly(err: unknown): string {
  if (err instanceof ApiError) return `${err.errorCode}: ${err.reason}`;
  return err instanceof Error ? err.message : String(err);
}

function linesToText(lines: string[]): string {
  return lines.join("\n");
}

function textToLines(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function PatientSummaryPanel({ identity, patientId, encounterId }: Props) {
  const [items, setItems] = useState<PatientSummary[]>([]);
  const [active, setActive] = useState<PatientSummary | null>(null);

  // Draft create / edit fields.
  const [scribeSessionId, setScribeSessionId] = useState<string>("");
  const [providerInstructions, setProviderInstructions] = useState<string>("");
  const [plainLanguageSummary, setPlainLanguageSummary] = useState<string>("");
  const [keyFindingsText, setKeyFindingsText] = useState<string>("");
  const [nextStepsText, setNextStepsText] = useState<string>("");
  const [questionsText, setQuestionsText] = useState<string>("");
  const [limitationsNotice, setLimitationsNotice] = useState<string>("");
  const [reviewNotes, setReviewNotes] = useState<string>("");

  const [banner, setBanner] = useState<Banner>(null);
  const [busy, setBusy] = useState(false);

  // --- list / load ---------------------------------------------------

  const refresh = useCallback(async () => {
    try {
      const res = await listPatientSummaries(identity, patientId);
      setItems(res.items);
    } catch (err) {
      setBanner({
        kind: "error",
        msg: `Could not load patient summaries: ${friendly(err)}`,
      });
    }
  }, [identity, patientId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const resetDraft = useCallback(() => {
    setActive(null);
    setScribeSessionId("");
    setProviderInstructions("");
    setPlainLanguageSummary("");
    setKeyFindingsText("");
    setNextStepsText("");
    setQuestionsText("");
    setLimitationsNotice("");
    setReviewNotes("");
    setBanner(null);
  }, []);

  const loadSummary = useCallback(
    async (id: number) => {
      try {
        setBusy(true);
        const s = await getPatientSummary(identity, patientId, id);
        setActive(s);
        setScribeSessionId(s.scribe_session_id?.toString() ?? "");
        setProviderInstructions("");
        setPlainLanguageSummary(s.plain_language_summary);
        setKeyFindingsText(linesToText(s.key_findings));
        setNextStepsText(linesToText(s.next_steps));
        setQuestionsText(linesToText(s.questions));
        setLimitationsNotice(s.limitations_notice);
        setReviewNotes(s.review_notes ?? "");
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
      const parsedScribe = scribeSessionId.trim()
        ? Number(scribeSessionId.trim())
        : undefined;
      const summary = await createPatientSummary(identity, patientId, {
        encounter_id: encounterId ?? undefined,
        scribe_session_id: parsedScribe ?? undefined,
        provider_instructions: providerInstructions || undefined,
      });
      setActive(summary);
      setScribeSessionId(summary.scribe_session_id?.toString() ?? "");
      setProviderInstructions("");
      setPlainLanguageSummary(summary.plain_language_summary);
      setKeyFindingsText(linesToText(summary.key_findings));
      setNextStepsText(linesToText(summary.next_steps));
      setQuestionsText(linesToText(summary.questions));
      setLimitationsNotice(summary.limitations_notice);
      setReviewNotes(summary.review_notes ?? "");
      setBanner({ kind: "ok", msg: `Draft #${summary.id} generated.` });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Create failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [
    encounterId,
    identity,
    patientId,
    providerInstructions,
    refresh,
    scribeSessionId,
  ]);

  const onUpdate = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const summary = await updatePatientSummary(
        identity,
        patientId,
        active.id,
        {
          plain_language_summary: plainLanguageSummary,
          key_findings: textToLines(keyFindingsText),
          next_steps: textToLines(nextStepsText),
          questions: textToLines(questionsText),
          limitations_notice: limitationsNotice,
          review_notes: reviewNotes,
        }
      );
      setActive(summary);
      setBanner({ kind: "ok", msg: "Saved draft." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Update failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [
    active,
    identity,
    keyFindingsText,
    limitationsNotice,
    nextStepsText,
    patientId,
    plainLanguageSummary,
    questionsText,
    refresh,
    reviewNotes,
  ]);

  const onReview = useCallback(async () => {
    if (!active) return;
    try {
      setBusy(true);
      const summary = await reviewPatientSummary(
        identity,
        patientId,
        active.id,
        { review_notes: reviewNotes || undefined }
      );
      setActive(summary);
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
      const summary = await finalizePatientSummary(identity, patientId, active.id);
      setActive(summary);
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
      const summary = await discardPatientSummary(identity, patientId, active.id);
      setActive(summary);
      setBanner({ kind: "ok", msg: "Discarded." });
      await refresh();
    } catch (err) {
      setBanner({ kind: "error", msg: `Discard failed: ${friendly(err)}` });
    } finally {
      setBusy(false);
    }
  }, [active, identity, patientId, refresh]);

  // --- derived display ------------------------------------------------

  const statusBadge = useMemo(
    () => (active ? STATUS_LABEL[active.status] : null),
    [active]
  );

  // --- render ---------------------------------------------------------

  return (
    <div className="patient-summary-panel" data-testid="patient-summary-panel">
      <header className="patient-summary-panel__header">
        <h3>Patient-friendly summary</h3>
        <p
          className="patient-summary-panel__hint"
          data-testid="patient-summary-banner-copy"
        >
          Patient summary draft — provider review required. Do not send
          to patient until finalized by the provider.
        </p>
      </header>

      {banner && (
        <div
          role="status"
          data-testid="patient-summary-banner"
          className={`flash flash--${banner.kind}`}
        >
          {banner.msg}
        </div>
      )}

      <section className="patient-summary-panel__list">
        <div className="patient-summary-panel__list-header">
          <strong>Saved summaries</strong>
          <button
            type="button"
            onClick={resetDraft}
            disabled={busy}
            data-testid="patient-summary-new"
          >
            New
          </button>
        </div>
        {items.length === 0 ? (
          <p className="muted" data-testid="patient-summary-empty">
            No patient summaries yet for this patient.
          </p>
        ) : (
          <ul data-testid="patient-summary-list">
            {items.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  data-testid={`patient-summary-load-${s.id}`}
                  onClick={() => loadSummary(s.id)}
                  disabled={busy}
                >
                  #{s.id} · {STATUS_LABEL[s.status]}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="patient-summary-panel__editor">
        <div className="patient-summary-panel__meta">
          {active ? (
            <>
              <strong>#{active.id}</strong>
              <span
                className={`patient-summary-panel__badge patient-summary-panel__badge--${active.status}`}
                data-testid="patient-summary-status-badge"
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
            <span className="muted">New summary (unsaved)</span>
          )}
        </div>

        {isReadOnly && (
          <div
            className="flash flash--info"
            data-testid="patient-summary-readonly-warning"
          >
            This summary is {active!.status} and cannot be modified.
          </div>
        )}

        {!active && (
          <>
            <label>
              <span>Source scribe session ID (optional)</span>
              <input
                type="text"
                value={scribeSessionId}
                onChange={(e) => setScribeSessionId(e.target.value)}
                disabled={busy}
                data-testid="patient-summary-scribe-id"
                placeholder="e.g. 42"
              />
            </label>
            <label>
              <span>Provider instructions (optional)</span>
              <textarea
                rows={2}
                value={providerInstructions}
                onChange={(e) => setProviderInstructions(e.target.value)}
                disabled={busy}
                data-testid="patient-summary-provider-instructions"
                placeholder={
                  "Optional context the provider wants reflected verbatim. " +
                  "Not a directive to the engine."
                }
              />
            </label>
          </>
        )}

        <label>
          <span>Plain-language summary</span>
          <textarea
            rows={6}
            value={plainLanguageSummary}
            onChange={(e) => setPlainLanguageSummary(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="patient-summary-plain-language"
          />
        </label>

        <label>
          <span>Key findings (one per line)</span>
          <textarea
            rows={4}
            value={keyFindingsText}
            onChange={(e) => setKeyFindingsText(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="patient-summary-key-findings"
          />
        </label>

        <label>
          <span>Next steps (one per line)</span>
          <textarea
            rows={4}
            value={nextStepsText}
            onChange={(e) => setNextStepsText(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="patient-summary-next-steps"
          />
        </label>

        <label>
          <span>Questions to ask (one per line)</span>
          <textarea
            rows={4}
            value={questionsText}
            onChange={(e) => setQuestionsText(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="patient-summary-questions"
          />
        </label>

        <label>
          <span>Limitations notice</span>
          <textarea
            rows={2}
            value={limitationsNotice}
            onChange={(e) => setLimitationsNotice(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="patient-summary-limitations"
          />
        </label>

        <label>
          <span>Review notes</span>
          <textarea
            rows={2}
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            disabled={busy || isReadOnly}
            data-testid="patient-summary-review-notes"
          />
        </label>

        <div className="patient-summary-panel__actions">
          {!active && (
            <button
              type="button"
              onClick={onCreate}
              disabled={busy}
              data-testid="patient-summary-create"
            >
              Generate draft
            </button>
          )}
          {active && active.status === "draft" && (
            <>
              <button
                type="button"
                onClick={onUpdate}
                disabled={busy}
                data-testid="patient-summary-update"
              >
                Save draft
              </button>
              <button
                type="button"
                onClick={onReview}
                disabled={busy}
                data-testid="patient-summary-review"
              >
                Mark reviewed
              </button>
              <button
                type="button"
                onClick={onDiscard}
                disabled={busy}
                data-testid="patient-summary-discard"
              >
                Discard
              </button>
            </>
          )}
          {active && active.status === "reviewed" && (
            <>
              <button
                type="button"
                onClick={onUpdate}
                disabled={busy}
                data-testid="patient-summary-update"
              >
                Save edits
              </button>
              <button
                type="button"
                onClick={onFinalize}
                disabled={busy}
                data-testid="patient-summary-finalize"
              >
                Finalize
              </button>
              <button
                type="button"
                onClick={onDiscard}
                disabled={busy}
                data-testid="patient-summary-discard"
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
