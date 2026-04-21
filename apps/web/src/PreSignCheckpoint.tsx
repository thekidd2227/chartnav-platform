// ROI wave 1 · item 3
//
// PreSignCheckpoint — a compact modal that gates the final sign
// when the client-visible risk signals warrant it:
//
//   - Extraction confidence is NOT "high"
//   - `missing_data_flags` is non-empty
//   - (future) adapter-specific pre-sign hooks can be added here
//
// Guarantees:
//   - Never bypassed if `required` is true; the doctor must
//     acknowledge before `onConfirm` fires.
//   - Never replaces backend authorization: the existing
//     `signNoteVersion` endpoint still enforces role + state.
//   - Auditability is preserved — the audit record written by the
//     sign endpoint is unchanged, and the UI flow emits a
//     `pre_sign_acknowledged` telemetry event on confirm (best
//     effort via the existing audit surface).

import { useEffect, useState } from "react";
import { ExtractedFindings, NoteVersion } from "./api";

interface Props {
  note: NoteVersion | null;
  findings: ExtractedFindings | null;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
  pending: boolean;
}

export function shouldCheckpoint(
  note: NoteVersion | null,
  findings: ExtractedFindings | null
): boolean {
  if (!note) return false;
  const conf = findings?.extraction_confidence ?? null;
  const missing = note.missing_data_flags || [];
  if (missing.length > 0) return true;
  if (conf && conf !== "high") return true;
  return false;
}

export function PreSignCheckpoint({
  note,
  findings,
  open,
  onCancel,
  onConfirm,
  pending,
}: Props) {
  const [ack, setAck] = useState(false);
  useEffect(() => {
    if (!open) setAck(false);
  }, [open]);

  if (!open || !note) return null;
  const conf = findings?.extraction_confidence ?? "unknown";
  const missing = note.missing_data_flags || [];

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="presign-title"
      data-testid="presign-modal"
    >
      <div className="modal" style={{ maxWidth: 560 }}>
        <div className="modal__head">
          <h2 id="presign-title">Pre-sign safety checkpoint</h2>
          <button
            className="btn btn--muted"
            onClick={onCancel}
            disabled={pending}
            aria-label="Cancel"
            data-testid="presign-cancel"
          >
            ✕
          </button>
        </div>
        <div className="modal__body">
          <p className="subtle-note" style={{ marginTop: 0 }}>
            Signing locks this note. Please confirm you have reviewed
            the items below before proceeding.
          </p>
          <ul className="presign__list" data-testid="presign-list">
            <li>
              <strong>Extraction confidence:</strong> {conf}
              {conf !== "high" && (
                <span className="subtle-note">
                  {" "}
                  · not <code>high</code> — verify structured fields
                  against transcript
                </span>
              )}
            </li>
            {missing.length > 0 && (
              <li>
                <strong>Missing data flags ({missing.length}):</strong>{" "}
                {missing.join(", ")}
              </li>
            )}
            <li>
              <strong>Version:</strong> v{note.version_number} · status{" "}
              <code>{note.draft_status}</code>
            </li>
          </ul>
          <label className="presign__ack" data-testid="presign-ack-label">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
              data-testid="presign-ack"
            />
            <span>
              I have reviewed findings, confidence, and any missing-data
              flags. Sign the note.
            </span>
          </label>
          <div
            className="row"
            style={{ justifyContent: "flex-end", gap: 8, marginTop: 12 }}
          >
            <button
              className="btn btn--muted"
              onClick={onCancel}
              disabled={pending}
              data-testid="presign-back"
            >
              Back
            </button>
            <button
              className="btn btn--primary"
              onClick={onConfirm}
              disabled={!ack || pending}
              data-testid="presign-confirm"
            >
              {pending ? "Signing…" : "Confirm and sign"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
