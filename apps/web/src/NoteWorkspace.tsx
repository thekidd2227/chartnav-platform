/**
 * Provider review workspace (phase 19).
 *
 * Renders the encounter's transcript-to-note pipeline in three
 * visibly-distinct tiers so the trust model stays legible:
 *
 *   1. TRANSCRIPT  — raw operator input. Source of record for
 *                    what actually came out of the encounter.
 *   2. FINDINGS    — structured facts the generator extracted.
 *                    Read-only in the UI; surfaces confidence +
 *                    missing-data flags.
 *   3. DRAFT       — provider-editable narrative. `revised`
 *                    state and `generated_by: manual` label
 *                    whenever the provider has touched it.
 *
 * The component is intentionally NOT a generic "notes form." It
 * forces the operator through verify → submit → sign → export and
 * refuses edits once the note is signed.
 */

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  EncounterInput,
  ExtractedFindings,
  Me,
  MISSING_FLAG_LABELS,
  NoteVersion,
  createEncounterInput,
  exportNoteVersion,
  generateNoteVersion,
  getNoteVersion,
  listEncounterInputs,
  listEncounterNotes,
  patchNoteVersion,
  processEncounterInput,
  retryEncounterInput,
  signNoteVersion,
  submitNoteForReview,
} from "./api";

// ---------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------

interface Props {
  identity: string;
  me: Me;
  encounterId: number;
  patientDisplay: string;
  providerDisplay: string;
}

interface Flash {
  kind: "ok" | "error" | "info";
  msg: string;
}

// ---------------------------------------------------------------------
// Workspace
// ---------------------------------------------------------------------

export function NoteWorkspace({
  identity,
  me,
  encounterId,
  patientDisplay,
  providerDisplay,
}: Props) {
  const [inputs, setInputs] = useState<EncounterInput[]>([]);
  const [notes, setNotes] = useState<NoteVersion[]>([]);
  const [activeNoteId, setActiveNoteId] = useState<number | null>(null);
  const [activeNote, setActiveNote] = useState<NoteVersion | null>(null);
  const [activeFindings, setActiveFindings] =
    useState<ExtractedFindings | null>(null);
  const [loading, setLoading] = useState(false);
  const [flash, setFlash] = useState<Flash | null>(null);
  const [editBody, setEditBody] = useState<string | null>(null);
  const [newTranscript, setNewTranscript] = useState("");

  const canSign = me.role === "admin" || me.role === "clinician";
  const canEdit = canSign; // same set today
  const noteSigned =
    activeNote?.draft_status === "signed" ||
    activeNote?.draft_status === "exported";
  const noteExported = activeNote?.draft_status === "exported";
  const providerEdited =
    activeNote?.generated_by === "manual" ||
    activeNote?.draft_status === "revised";

  const showFlash = useCallback(
    (kind: Flash["kind"], msg: string) => setFlash({ kind, msg }),
    []
  );

  // ---- loaders ----------------------------------------------------
  const loadInputs = useCallback(async () => {
    try {
      setInputs(await listEncounterInputs(identity, encounterId));
    } catch (e) {
      showFlash("error", friendly(e));
    }
  }, [identity, encounterId, showFlash]);

  const loadNotes = useCallback(async () => {
    try {
      const list = await listEncounterNotes(identity, encounterId);
      setNotes(list);
      if (list.length && activeNoteId === null) {
        setActiveNoteId(list[0].id);
      }
    } catch (e) {
      showFlash("error", friendly(e));
    }
  }, [identity, encounterId, activeNoteId, showFlash]);

  const loadActive = useCallback(async () => {
    if (activeNoteId === null) {
      setActiveNote(null);
      setActiveFindings(null);
      setEditBody(null);
      return;
    }
    try {
      const data = await getNoteVersion(identity, activeNoteId);
      setActiveNote(data.note);
      setActiveFindings(data.findings);
      setEditBody(data.note.note_text);
    } catch (e) {
      showFlash("error", friendly(e));
    }
  }, [identity, activeNoteId, showFlash]);

  useEffect(() => {
    loadInputs();
    loadNotes();
  }, [loadInputs, loadNotes]);

  useEffect(() => {
    loadActive();
  }, [loadActive]);

  // ---- actions ----------------------------------------------------

  const onIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTranscript.trim()) {
      showFlash("error", "paste or type a transcript first");
      return;
    }
    setLoading(true);
    try {
      await createEncounterInput(identity, encounterId, {
        input_type: "text_paste",
        transcript_text: newTranscript.trim(),
      });
      showFlash("ok", "Transcript ingested.");
      setNewTranscript("");
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onRetry = async (inputId: number) => {
    setLoading(true);
    try {
      await retryEncounterInput(identity, inputId);
      // After retry flips the row to `queued`, re-run the pipeline.
      await processEncounterInput(identity, inputId);
      showFlash("ok", "Retry complete. Check the updated status.");
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onProcess = async (inputId: number) => {
    setLoading(true);
    try {
      const res = await processEncounterInput(identity, inputId);
      if (res.ingestion_error) {
        showFlash(
          "error",
          `${res.ingestion_error.error_code}: ${res.ingestion_error.reason}`
        );
      } else {
        showFlash("ok", "Input processed.");
      }
      await loadInputs();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateNoteVersion(identity, encounterId, {});
      showFlash(
        "ok",
        `Draft v${data.note.version_number} generated. ${data.note.missing_data_flags.length} items for provider to verify.`
      );
      await loadNotes();
      setActiveNoteId(data.note.id);
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onSaveEdit = async () => {
    if (activeNote === null || editBody === null) return;
    setLoading(true);
    try {
      const updated = await patchNoteVersion(identity, activeNote.id, {
        note_text: editBody,
      });
      setActiveNote(updated);
      showFlash("ok", "Provider edit saved.");
      await loadNotes();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onSubmitReview = async () => {
    if (!activeNote) return;
    setLoading(true);
    try {
      const updated = await submitNoteForReview(identity, activeNote.id);
      setActiveNote(updated);
      showFlash("ok", "Submitted for provider review.");
      await loadNotes();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onSign = async () => {
    if (!activeNote) return;
    if (!canSign) {
      showFlash("error", "your role cannot sign notes");
      return;
    }
    setLoading(true);
    try {
      const updated = await signNoteVersion(identity, activeNote.id);
      setActiveNote(updated);
      showFlash("ok", "Note signed.");
      await loadNotes();
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onExport = async () => {
    if (!activeNote) return;
    setLoading(true);
    try {
      const updated = await exportNoteVersion(identity, activeNote.id);
      setActiveNote(updated);
      await loadNotes();
      downloadTextFile(
        `chartnav-note-${activeNote.encounter_id}-v${activeNote.version_number}.txt`,
        activeNote.note_text
      );
      showFlash("ok", "Note marked exported and downloaded.");
    } catch (err) {
      showFlash("error", friendly(err));
    } finally {
      setLoading(false);
    }
  };

  const onCopy = async () => {
    if (!activeNote) return;
    try {
      await navigator.clipboard?.writeText(activeNote.note_text);
      showFlash("ok", "Note copied to clipboard.");
    } catch {
      showFlash("info", "clipboard unavailable; use the download button");
    }
  };

  // ---- render -----------------------------------------------------

  return (
    <div className="workspace" data-testid="note-workspace">
      <div className="workspace__header">
        <h3>Encounter workspace</h3>
        <div className="workspace__meta subtle-note">
          Patient: <strong>{patientDisplay}</strong> · Provider:{" "}
          <strong>{providerDisplay}</strong>
        </div>
        <p className="workspace__trust subtle-note">
          <strong>Trust model:</strong>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--transcript">
            transcript
          </span>{" "}
          <span className="workspace__trust-arrow">→</span>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--findings">
            extracted facts
          </span>{" "}
          <span className="workspace__trust-arrow">→</span>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--draft">
            AI draft
          </span>{" "}
          <span className="workspace__trust-arrow">→</span>{" "}
          <span className="workspace__trust-pill workspace__trust-pill--signed">
            provider signed
          </span>
        </p>
      </div>

      {flash && (
        <div
          className={`banner banner--${flash.kind === "info" ? "info" : flash.kind === "ok" ? "ok" : "error"}`}
          role={flash.kind === "error" ? "alert" : "status"}
          data-testid="workspace-banner"
        >
          {flash.msg}
        </div>
      )}

      {/* Tier 1 — transcripts */}
      <section
        className="workspace__tier workspace__tier--transcript"
        data-testid="workspace-tier-transcript"
      >
        <div className="workspace__tier-head">
          <h4>1. Transcript input</h4>
          {inputs.length > 0 && (
            <button
              type="button"
              className="btn btn--muted"
              onClick={loadInputs}
              disabled={loading}
              data-testid="transcript-refresh"
              title="Re-fetch input list from the server"
            >
              ↻ Refresh
            </button>
          )}
        </div>
        <p className="subtle-note">
          Raw operator input. Source of record for what was said.
        </p>
        {inputs.some(
          (i) =>
            i.processing_status === "queued" ||
            i.processing_status === "processing"
        ) && (
          <div
            className="banner banner--info"
            role="note"
            data-testid="workspace-queue-banner"
          >
            {inputs.some((i) => i.processing_status === "processing") ? (
              <>
                <strong>Transcript is processing in the background.</strong>{" "}
                A worker picked up the input and is extracting text. Draft
                generation will unlock automatically once processing
                finishes — click <strong>Refresh</strong> to pull the
                latest status, or step away and come back.
              </>
            ) : (
              <>
                <strong>Transcript is queued in the background.</strong>{" "}
                It's waiting for a worker to pick it up. Click{" "}
                <strong>Process now</strong> on the queued row to run it
                immediately, or wait for the next worker tick.
              </>
            )}
          </div>
        )}
        {inputs.length === 0 && (
          <p className="empty">No transcript ingested yet.</p>
        )}
        {inputs.map((inp) => (
          <div
            key={inp.id}
            className="event-item"
            data-testid={`transcript-${inp.id}`}
          >
            <div className="event-item__head">
              <span className="event-item__type">{inp.input_type}</span>
              <span
                className="status-pill"
                data-status={inp.processing_status}
                data-testid={`transcript-status-${inp.id}`}
              >
                {inp.processing_status.replace(/_/g, " ")}
                {typeof inp.retry_count === "number" && inp.retry_count > 0 && (
                  <span
                    className="workspace__retry-count"
                    aria-label="retry count"
                    data-testid={`transcript-retry-count-${inp.id}`}
                  >
                    · retries {inp.retry_count}
                  </span>
                )}
              </span>
            </div>
            {(inp.processing_status === "failed" ||
              inp.processing_status === "needs_review") && inp.last_error && (
              <div
                className="banner banner--error"
                data-testid={`transcript-error-${inp.id}`}
                role="alert"
              >
                <strong>{inp.last_error_code ?? "ingestion_failed"}:</strong>{" "}
                {inp.last_error}
              </div>
            )}
            {inp.transcript_text && (
              <pre className="workspace__transcript">{inp.transcript_text}</pre>
            )}
            {canEdit &&
              (inp.processing_status === "failed" ||
                inp.processing_status === "needs_review" ||
                inp.processing_status === "queued") && (
                <div className="actions" style={{ marginTop: 6 }}>
                  {(inp.processing_status === "failed" ||
                    inp.processing_status === "needs_review") && (
                    <button
                      type="button"
                      className="btn"
                      disabled={loading}
                      onClick={() => onRetry(inp.id)}
                      data-testid={`transcript-retry-${inp.id}`}
                    >
                      Retry
                    </button>
                  )}
                  {inp.processing_status === "queued" && (
                    <button
                      type="button"
                      className="btn"
                      disabled={loading}
                      onClick={() => onProcess(inp.id)}
                      data-testid={`transcript-process-${inp.id}`}
                    >
                      Process now
                    </button>
                  )}
                </div>
              )}
          </div>
        ))}
        {canEdit && (
          <form
            className="event-form"
            onSubmit={onIngest}
            data-testid="transcript-ingest-form"
          >
            <label>
              Paste or type a new transcript
              <textarea
                value={newTranscript}
                onChange={(e) => setNewTranscript(e.target.value)}
                data-testid="transcript-ingest-textarea"
                placeholder="Chief complaint: …&#10;OD 20/40, OS 20/20.&#10;IOP 15/17.&#10;Plan: YAG capsulotomy.&#10;Follow-up in 4 weeks."
              />
            </label>
            <div className="row">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={loading}
                data-testid="transcript-ingest-submit"
              >
                Ingest transcript
              </button>
              <button
                type="button"
                className="btn"
                disabled={
                  loading ||
                  !inputs.some((i) => i.processing_status === "completed")
                }
                onClick={onGenerate}
                data-testid="generate-draft"
                title={
                  inputs.some((i) => i.processing_status === "completed")
                    ? "Generate a draft from the most recent completed input"
                    : "Waiting for a completed input — process or retry one first"
                }
              >
                Generate draft
              </button>
            </div>
            {/* Honest "why is Generate disabled" hint. Appears only
                when no completed input exists; differentiates the
                "still processing" case from the "nothing ingested
                yet" case so operators know whether to wait, retry,
                or paste something fresh. */}
            {!inputs.some((i) => i.processing_status === "completed") && (
              <p
                className="subtle-note workspace__generate-blocked"
                data-testid="generate-blocked-note"
              >
                {inputs.length === 0
                  ? "Generation unlocks once a transcript has been ingested and finished processing."
                  : inputs.some(
                      (i) =>
                        i.processing_status === "queued" ||
                        i.processing_status === "processing"
                    )
                  ? "Generation is waiting on transcript processing. Background work continues — use Refresh to pull the latest status."
                  : inputs.some(
                      (i) =>
                        i.processing_status === "failed" ||
                        i.processing_status === "needs_review"
                    )
                  ? "The most recent input failed or needs review. Retry it, or ingest a fresh transcript before generating."
                  : "No completed input is available yet."}
              </p>
            )}
          </form>
        )}
      </section>

      {/* Tier 2 — findings */}
      <section
        className="workspace__tier workspace__tier--findings"
        data-testid="workspace-tier-findings"
      >
        <h4>2. Extracted findings</h4>
        <p className="subtle-note">
          Structured facts the generator saw. Read-only — provider verifies.
        </p>
        {activeFindings ? (
          <FindingsBlock findings={activeFindings} />
        ) : (
          <p className="empty">
            No findings yet. Generate a draft from a transcript.
          </p>
        )}
        {activeNote && activeNote.missing_data_flags.length > 0 && (
          <div
            className="banner banner--info"
            data-testid="missing-flags-banner"
          >
            <strong>Items for provider to verify:</strong>
            <ul>
              {activeNote.missing_data_flags.map((f) => (
                <li key={f}>{MISSING_FLAG_LABELS[f] ?? f}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Tier 3 — draft / signoff */}
      <section
        className="workspace__tier workspace__tier--draft"
        data-testid="workspace-tier-draft"
      >
        <div className="workspace__tier-head">
          <h4>3. Note draft</h4>
          {activeNote && (
            <span
              className={`status-pill`}
              data-status={mapNoteStatus(activeNote.draft_status)}
              data-testid="note-draft-status"
            >
              {activeNote.draft_status} · v{activeNote.version_number}
            </span>
          )}
        </div>
        {activeNote ? (
          <>
            <div className="workspace__meta subtle-note">
              Generated by:{" "}
              <strong data-testid="note-generated-by">
                {providerEdited ? "provider (edited)" : activeNote.generated_by}
              </strong>
              {activeNote.signed_at && (
                <>
                  {" · Signed at "}
                  <strong>{activeNote.signed_at}</strong>
                </>
              )}
              {noteExported && (
                <>
                  {" · Exported at "}
                  <strong>{activeNote.exported_at}</strong>
                </>
              )}
            </div>
            {canEdit && !noteSigned ? (
              <textarea
                className="workspace__draft"
                value={editBody ?? ""}
                onChange={(e) => setEditBody(e.target.value)}
                data-testid="note-draft-textarea"
                rows={18}
              />
            ) : (
              <pre
                className="workspace__draft workspace__draft--readonly"
                data-testid="note-draft-readonly"
              >
                {activeNote.note_text}
              </pre>
            )}
            <div className="actions">
              {canEdit && !noteSigned && (
                <>
                  <button
                    className="btn"
                    onClick={onSaveEdit}
                    disabled={loading || editBody === activeNote.note_text}
                    data-testid="note-save-edit"
                  >
                    Save provider edit
                  </button>
                  <button
                    className="btn"
                    onClick={onSubmitReview}
                    disabled={
                      loading ||
                      activeNote.draft_status === "provider_review"
                    }
                    data-testid="note-submit-review"
                  >
                    Submit for review
                  </button>
                </>
              )}
              {canSign && !noteSigned && (
                <button
                  className="btn btn--primary"
                  onClick={onSign}
                  disabled={loading}
                  data-testid="note-sign"
                >
                  Sign note
                </button>
              )}
              {noteSigned && !noteExported && (
                <button
                  className="btn btn--primary"
                  onClick={onExport}
                  disabled={loading}
                  data-testid="note-export"
                >
                  Export note
                </button>
              )}
              {noteSigned && (
                <button
                  className="btn"
                  onClick={onCopy}
                  data-testid="note-copy"
                >
                  Copy to clipboard
                </button>
              )}
            </div>
            {!canSign && (
              <p
                className="subtle-note"
                data-testid="note-sign-disabled-note"
              >
                Reviewer role cannot sign. Clinician or admin attestation
                is required.
              </p>
            )}
          </>
        ) : (
          <p className="empty">
            No note yet. Generate a draft to start the review workflow.
          </p>
        )}
        {notes.length > 1 && (
          <div
            className="workspace__versions subtle-note"
            data-testid="note-version-list"
          >
            <strong>Versions:</strong>{" "}
            {notes.map((n) => (
              <button
                key={n.id}
                className={
                  "btn " +
                  (activeNoteId === n.id ? "btn--primary" : "btn--muted")
                }
                onClick={() => setActiveNoteId(n.id)}
                data-testid={`note-version-${n.version_number}`}
              >
                v{n.version_number} · {n.draft_status}
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

function FindingsBlock({ findings }: { findings: ExtractedFindings }) {
  const s = findings.structured_json || {};
  const confidence = findings.extraction_confidence ?? "unknown";
  return (
    <dl className="detail__facts" data-testid="findings-block">
      <div>
        <dt>Chief complaint</dt>
        <dd data-testid="findings-cc">{findings.chief_complaint || "—"}</dd>
      </div>
      <div>
        <dt>HPI</dt>
        <dd>{findings.hpi_summary || "—"}</dd>
      </div>
      <div>
        <dt>Visual acuity OD / OS</dt>
        <dd data-testid="findings-va">
          {findings.visual_acuity_od || "—"} / {findings.visual_acuity_os || "—"}
        </dd>
      </div>
      <div>
        <dt>IOP OD / OS</dt>
        <dd data-testid="findings-iop">
          {findings.iop_od || "—"} / {findings.iop_os || "—"}
        </dd>
      </div>
      <div>
        <dt>Diagnoses</dt>
        <dd>{(s.diagnoses ?? []).join("; ") || "—"}</dd>
      </div>
      <div>
        <dt>Plan</dt>
        <dd>{s.plan || "—"}</dd>
      </div>
      <div>
        <dt>Follow-up</dt>
        <dd>{s.follow_up_interval || "—"}</dd>
      </div>
      <div>
        <dt>Extraction confidence</dt>
        <dd
          data-testid="findings-confidence"
          data-confidence={confidence}
        >
          {confidence}
        </dd>
      </div>
    </dl>
  );
}

function mapNoteStatus(s: string): string {
  // Reuse encounter status-pill palette for draft-status coloring.
  switch (s) {
    case "draft":
      return "in_progress";
    case "provider_review":
      return "review_needed";
    case "revised":
      return "draft_ready";
    case "signed":
    case "exported":
      return "completed";
    default:
      return "scheduled";
  }
}

function downloadTextFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}
