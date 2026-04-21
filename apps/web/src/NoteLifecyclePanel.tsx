// Phase 49 — clinical governance wave 3: NoteWorkspace lifecycle panel.
//
// Drops into NoteWorkspace as a self-contained surface that shows:
//   - current lifecycle status (chip)
//   - reviewer attribution (who, when)
//   - signer attribution (who, when)
//   - attestation text (frozen at sign time)
//   - content fingerprint drift warning
//   - live release blockers against the next logical target
//   - review action (reviewer only, when valid edge)
//   - amend action (admin/clinician, when signed/exported/amended)
//
// Never mutates the note directly — triggers the appropriate server
// action and calls `onChanged()` so NoteWorkspace reloads its
// source of truth.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  Me,
  NoteVersion,
  NoteReleaseBlocker,
  amendNoteVersion,
  finalApproveNoteVersion,
  getNoteReleaseBlockers,
  reviewNoteVersion,
} from "./api";

interface Props {
  identity: string;
  me: Me;
  note: NoteVersion | null;
  onChanged: () => void | Promise<void>;
}

// Legible label for every lifecycle state. Keeps the chip copy
// consistent across the admin + provider views.
const STATE_LABEL: Record<string, string> = {
  draft: "Draft",
  provider_review: "In review",
  reviewed: "Reviewed",
  revised: "Revised",
  signed: "Signed",
  exported: "Exported",
  amended: "Amended",
};

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function friendly(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} ${e.errorCode} — ${e.reason}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

export function NoteLifecyclePanel({ identity, me, note, onChanged }: Props) {
  const [blockers, setBlockers] = useState<NoteReleaseBlocker[] | null>(null);
  const [fingerprintOk, setFingerprintOk] = useState<boolean | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [amendOpen, setAmendOpen] = useState(false);
  const [banner, setBanner] = useState<
    { kind: "ok" | "error" | "info"; msg: string } | null
  >(null);

  // Phase 52 — Wave 7 final approval state.
  const [approvalSignature, setApprovalSignature] = useState("");
  const [approvalPending, setApprovalPending] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // Decide the next meaningful transition target for blocker display.
  const target = useMemo(() => {
    if (!note) return "signed";
    switch (note.draft_status) {
      case "draft":
      case "provider_review":
      case "revised":
      case "reviewed":
        return "signed";
      case "signed":
      case "amended":
        return "exported";
      default:
        return "signed";
    }
  }, [note]);

  const loadBlockers = useCallback(async () => {
    if (!note) return;
    try {
      const r = await getNoteReleaseBlockers(identity, note.id, target as any);
      setBlockers(r.blockers);
      setFingerprintOk(r.fingerprint_ok);
    } catch (e) {
      setBlockers(null);
      setFingerprintOk(null);
      // A blocker-fetch failure is not fatal — the pane still renders.
    }
  }, [identity, note, target]);

  useEffect(() => {
    loadBlockers();
  }, [loadBlockers]);

  if (!note) return null;

  const status = note.draft_status;
  const canReview = me.role === "admin" || me.role === "reviewer";
  const canAmend = me.role === "admin" || me.role === "clinician";
  const showReview =
    canReview && (status === "provider_review" || status === "revised");
  const showAmend =
    canAmend &&
    (status === "signed" || status === "exported" || status === "amended") &&
    !note.superseded_at;

  const hardBlockers = (blockers ?? []).filter(
    (b) => (b.severity ?? "error") === "error"
  );
  const warnBlockers = (blockers ?? []).filter((b) => b.severity === "warn");

  const onReview = async () => {
    if (!note) return;
    setReviewing(true);
    setBanner(null);
    try {
      await reviewNoteVersion(identity, note.id);
      setBanner({ kind: "ok", msg: "Marked as reviewed." });
      await onChanged();
    } catch (e) {
      setBanner({ kind: "error", msg: friendly(e) });
    } finally {
      setReviewing(false);
    }
  };

  // Phase 52 — Wave 7 typed-signature final approval.
  //
  // Validation is server-authoritative. Client-side we only do two
  // cheap things: disable the submit button on empty input, and map
  // the structured server error_code back to a human-friendly line.
  // The comparison itself — case-sensitive, exact equality — lives
  // on the API and cannot be bypassed.
  const onFinalApprove = async () => {
    if (!note) return;
    setApprovalPending(true);
    setApprovalError(null);
    try {
      await finalApproveNoteVersion(identity, note.id, {
        signature_text: approvalSignature,
      });
      setApprovalSignature("");
      setBanner({
        kind: "ok",
        msg: "Final physician approval recorded.",
      });
      await onChanged();
    } catch (e) {
      if (e instanceof ApiError) {
        // Map well-known structured codes to clinical-grade copy.
        if (e.errorCode === "signature_mismatch") {
          setApprovalError(
            "Typed name does not match your stored full name exactly. " +
              "Capitalization and spelling must match."
          );
        } else if (e.errorCode === "signature_required") {
          setApprovalError("Type your full name to approve.");
        } else if (e.errorCode === "signer_has_no_stored_name") {
          setApprovalError(
            "Your account has no stored full name. Contact an admin " +
              "to set it before performing final approval."
          );
        } else if (e.errorCode === "role_cannot_final_approve") {
          setApprovalError(
            "This account is not an authorized final signer."
          );
        } else if (e.errorCode === "already_approved") {
          setApprovalError("This note is already final-approved.");
        } else if (e.errorCode === "not_signable_state") {
          setApprovalError(
            "Final approval requires a signed note. Sign it first."
          );
        } else if (e.errorCode === "note_superseded") {
          setApprovalError(
            "This note has been amended; approve the amendment row."
          );
        } else {
          setApprovalError(friendly(e));
        }
      } else {
        setApprovalError(friendly(e));
      }
    } finally {
      setApprovalPending(false);
    }
  };

  return (
    <section
      className="lifecycle-panel"
      data-testid="lifecycle-panel"
      aria-label="Lifecycle governance"
    >
      <div className="lifecycle-panel__head">
        <span
          className="lifecycle-chip"
          data-status={status}
          data-testid="lifecycle-status"
        >
          {STATE_LABEL[status] ?? status}
        </span>
        <span className="subtle-note">
          v{note.version_number}
          {note.amended_from_note_id ? (
            <>
              {" · amendment of "}
              <code data-testid="lifecycle-amended-from">
                #{note.amended_from_note_id}
              </code>
            </>
          ) : null}
          {note.superseded_at ? " · superseded" : null}
        </span>
      </div>

      {banner && (
        <div
          className={`banner banner--${banner.kind}`}
          role={banner.kind === "error" ? "alert" : "status"}
          data-testid="lifecycle-banner"
        >
          {banner.msg}
        </div>
      )}

      {/* Attribution block — reviewer / signer / amender visible whenever
          the underlying stamp is populated. */}
      <dl
        className="lifecycle-panel__attr"
        data-testid="lifecycle-attribution"
      >
        {note.reviewed_at && (
          <div>
            <dt>Reviewed</dt>
            <dd data-testid="lifecycle-reviewed">
              by user #{note.reviewed_by_user_id ?? "—"} · {fmtTime(note.reviewed_at)}
            </dd>
          </div>
        )}
        {note.signed_at && (
          <div>
            <dt>Signed</dt>
            <dd data-testid="lifecycle-signed">
              by user #{note.signed_by_user_id ?? "—"} · {fmtTime(note.signed_at)}
            </dd>
          </div>
        )}
        {note.amended_at && (
          <div>
            <dt>Amended</dt>
            <dd data-testid="lifecycle-amended">
              by user #{note.amended_by_user_id ?? "—"} · {fmtTime(note.amended_at)}
            </dd>
          </div>
        )}
        {note.exported_at && (
          <div>
            <dt>Exported</dt>
            <dd data-testid="lifecycle-exported">
              {fmtTime(note.exported_at)}
            </dd>
          </div>
        )}
        {note.attestation_text && (
          <div className="lifecycle-panel__attr-wide">
            <dt>Attestation</dt>
            <dd data-testid="lifecycle-attestation">{note.attestation_text}</dd>
          </div>
        )}
        {note.amendment_reason && (
          <div className="lifecycle-panel__attr-wide">
            <dt>Amendment reason</dt>
            <dd data-testid="lifecycle-amendment-reason">
              {note.amendment_reason}
            </dd>
          </div>
        )}
      </dl>

      {/* Wave 7 — final physician approval section. Rendered whenever
          the server has stamped a final_approval_status on this row
          (i.e. it has been signed under the Wave 7 flow). Legacy
          signed rows predating Wave 7 carry a null status and are
          intentionally not surfaced here. */}
      {note.final_approval_status ? (
        <section
          className="lifecycle-approval"
          data-testid="lifecycle-final-approval"
          data-status={note.final_approval_status}
          aria-label="Final physician approval"
        >
          <header className="lifecycle-approval__head">
            <h3 className="lifecycle-approval__title">
              Final physician approval
            </h3>
            <span
              className="lifecycle-approval__chip"
              data-status={note.final_approval_status}
              data-testid="lifecycle-final-approval-status"
            >
              {note.final_approval_status === "approved"
                ? "Approved"
                : note.final_approval_status === "invalidated"
                ? "Invalidated"
                : "Pending"}
            </span>
          </header>

          {note.final_approval_status === "approved" && (
            <dl
              className="lifecycle-approval__meta"
              data-testid="lifecycle-final-approval-meta"
            >
              <div>
                <dt>Approved by</dt>
                <dd data-testid="lifecycle-final-approved-by">
                  user #{note.final_approved_by_user_id ?? "—"}
                  {note.final_approval_signature_text ? (
                    <>
                      {" · "}
                      <code
                        className="lifecycle-approval__sig"
                        data-testid="lifecycle-final-approval-signature"
                      >
                        {note.final_approval_signature_text}
                      </code>
                    </>
                  ) : null}
                </dd>
              </div>
              <div>
                <dt>Approved at</dt>
                <dd data-testid="lifecycle-final-approved-at">
                  {fmtTime(note.final_approved_at)}
                </dd>
              </div>
            </dl>
          )}

          {note.final_approval_status === "invalidated" && (
            <div
              className="lifecycle-approval__invalidated"
              role="alert"
              data-testid="lifecycle-final-approval-invalidated"
            >
              <strong>Prior approval invalidated.</strong>{" "}
              {note.final_approval_invalidated_reason ||
                "An amendment or governed action invalidated the prior approval."}{" "}
              Invalidated {fmtTime(note.final_approval_invalidated_at)}.
            </div>
          )}

          {note.final_approval_status === "pending" && (
            <>
              <p
                className="subtle-note lifecycle-approval__prompt"
                data-testid="lifecycle-final-approval-prompt"
              >
                This signed record is awaiting final physician approval.
                Export is blocked until an authorized doctor types
                their exact stored name to approve.
              </p>

              {me.is_authorized_final_signer && !note.superseded_at ? (
                <form
                  className="lifecycle-approval__form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!approvalPending) onFinalApprove();
                  }}
                  data-testid="lifecycle-final-approval-form"
                >
                  <label className="lifecycle-approval__label">
                    Type your exact stored name to approve
                    <input
                      type="text"
                      value={approvalSignature}
                      onChange={(e) => {
                        setApprovalSignature(e.target.value);
                        if (approvalError) setApprovalError(null);
                      }}
                      placeholder={me.full_name || "Your full name"}
                      autoComplete="off"
                      spellCheck={false}
                      maxLength={255}
                      data-testid="lifecycle-final-approval-input"
                      disabled={approvalPending}
                    />
                  </label>
                  <p className="subtle-note lifecycle-approval__policy">
                    Comparison is case-sensitive. Typing is
                    attestation; no UI shortcut bypasses the match.
                  </p>
                  {approvalError && (
                    <div
                      className="banner banner--error lifecycle-approval__error"
                      role="alert"
                      data-testid="lifecycle-final-approval-error"
                    >
                      {approvalError}
                    </div>
                  )}
                  <div className="lifecycle-approval__actions">
                    <button
                      type="submit"
                      className="btn btn--primary"
                      data-testid="lifecycle-final-approve-submit"
                      disabled={
                        approvalPending || approvalSignature.trim().length === 0
                      }
                    >
                      {approvalPending ? "Approving…" : "Record final approval"}
                    </button>
                  </div>
                </form>
              ) : me.is_authorized_final_signer && note.superseded_at ? (
                <p
                  className="subtle-note"
                  data-testid="lifecycle-final-approval-superseded-note"
                >
                  This row has been superseded by an amendment. Approve
                  the amendment row instead.
                </p>
              ) : (
                <p
                  className="subtle-note"
                  data-testid="lifecycle-final-approval-restricted"
                >
                  Only users explicitly designated as authorized final
                  signers in this organization may perform final
                  approval.
                </p>
              )}
            </>
          )}
        </section>
      ) : null}

      {/* Fingerprint drift — hard alert when the signed row has been
          mutated silently in the DB. */}
      {fingerprintOk === false && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="lifecycle-fingerprint-drift"
        >
          <strong>Content-fingerprint drift detected.</strong> The signed
          note_text no longer matches the fingerprint captured at sign time.
          Treat this row as suspect and investigate before releasing.
        </div>
      )}

      {/* Release blockers */}
      {hardBlockers.length > 0 && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="lifecycle-blockers-error"
        >
          <strong>Blocking release to {target}:</strong>
          <ul>
            {hardBlockers.map((b) => (
              <li key={b.code} data-testid={`lifecycle-blocker-${b.code}`}>
                {b.message}
                {b.field ? <> <code>({b.field})</code></> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      {hardBlockers.length === 0 && warnBlockers.length > 0 && (
        <div
          className="banner banner--info"
          data-testid="lifecycle-blockers-warn"
        >
          <strong>Advisory before release:</strong>
          <ul>
            {warnBlockers.map((b) => (
              <li key={b.code} data-testid={`lifecycle-blocker-${b.code}`}>
                {b.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      {blockers !== null && hardBlockers.length === 0 && warnBlockers.length === 0 && (
        <p className="subtle-note" data-testid="lifecycle-blockers-clear">
          No release blockers for the next step ({target}).
        </p>
      )}

      {/* Actions */}
      <div className="lifecycle-panel__actions">
        {showReview && (
          <button
            type="button"
            className="btn"
            onClick={onReview}
            disabled={reviewing}
            data-testid="lifecycle-mark-reviewed"
          >
            {reviewing ? "Marking…" : "Mark reviewed"}
          </button>
        )}
        {showAmend && (
          <button
            type="button"
            className="btn"
            onClick={() => setAmendOpen(true)}
            data-testid="lifecycle-open-amend"
          >
            Amend note
          </button>
        )}
        <button
          type="button"
          className="btn btn--muted"
          onClick={loadBlockers}
          data-testid="lifecycle-refresh-blockers"
          title="Re-check release blockers"
        >
          ↻ Re-check
        </button>
      </div>

      {amendOpen && (
        <AmendModal
          identity={identity}
          note={note}
          onClose={() => setAmendOpen(false)}
          onSuccess={async () => {
            setAmendOpen(false);
            setBanner({
              kind: "ok",
              msg: "Amendment created. Original note is now superseded.",
            });
            await onChanged();
          }}
        />
      )}
    </section>
  );
}

// ---------------------------------------------------------------------
// Amend modal
// ---------------------------------------------------------------------

function AmendModal({
  identity,
  note,
  onClose,
  onSuccess,
}: {
  identity: string;
  note: NoteVersion;
  onClose: () => void;
  onSuccess: () => void | Promise<void>;
}) {
  const [noteText, setNoteText] = useState<string>(note.note_text || "");
  const [reason, setReason] = useState<string>("");
  const [pending, setPending] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canSubmit =
    !pending && noteText.trim().length >= 10 && reason.trim().length >= 4;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setPending(true);
    setErr(null);
    try {
      await amendNoteVersion(identity, note.id, {
        note_text: noteText,
        reason,
      });
      await onSuccess();
    } catch (e) {
      setErr(friendly(e));
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Amend note"
      data-testid="amend-modal"
      onClick={(e) => {
        if (e.target === e.currentTarget && !pending) onClose();
      }}
    >
      <div className="modal" style={{ maxWidth: 680 }}>
        <div className="modal__head">
          <h2>Amend note (v{note.version_number})</h2>
          <button
            type="button"
            className="btn btn--muted"
            onClick={onClose}
            disabled={pending}
            aria-label="Close"
            data-testid="amend-close"
          >
            ✕
          </button>
        </div>
        <form className="modal__body event-form" onSubmit={submit}>
          <p className="subtle-note" style={{ marginTop: 0 }}>
            Creates a NEW signed note version linked to this one. The
            original remains in the audit trail; it is marked
            superseded but not deleted.
          </p>
          <label>
            Amendment reason *
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              minLength={4}
              maxLength={500}
              placeholder="e.g. corrected IOP OD transcription"
              data-testid="amend-reason"
            />
          </label>
          <label>
            New note text *
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              required
              rows={14}
              data-testid="amend-text"
            />
          </label>
          {err && (
            <div
              className="banner banner--error"
              role="alert"
              data-testid="amend-error"
            >
              {err}
            </div>
          )}
          <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
            <button
              type="button"
              className="btn btn--muted"
              onClick={onClose}
              disabled={pending}
              data-testid="amend-cancel"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={!canSubmit}
              data-testid="amend-submit"
            >
              {pending ? "Amending…" : "Create amendment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
