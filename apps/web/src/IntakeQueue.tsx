// Phase 2 item 3 — Staff intake queue (admin / front_desk).
//
// Spec: docs/chartnav/closure/PHASE_B_Digital_Intake.md §5.
//
// Lists pending intakes; allows staff to issue a new token, copy
// the public URL, accept a submission (creates a draft patient +
// draft encounter), or reject one with an optional reason.
import { useEffect, useState } from "react";
import {
  ApiError,
  IntakeSubmission,
  IntakeTokenIssue,
  acceptIntakeSubmission,
  issueIntakeToken,
  listIntakeSubmissions,
  rejectIntakeSubmission,
} from "./api";

export interface IntakeQueueProps {
  identity: string;
  onClose: () => void;
}

export function IntakeQueue({ identity, onClose }: IntakeQueueProps) {
  const [items, setItems] = useState<IntakeSubmission[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [issued, setIssued] = useState<IntakeTokenIssue | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  function refresh() {
    listIntakeSubmissions(identity)
      .then((r) => setItems(r.items))
      .catch((e: unknown) => {
        if (e instanceof ApiError) setError(e.reason);
        else setError("Could not load intake queue.");
      });
  }
  useEffect(refresh, [identity]);

  async function onIssue() {
    setError(null);
    try {
      const out = await issueIntakeToken(identity);
      setIssued(out);
    } catch (e: unknown) {
      if (e instanceof ApiError) setError(e.reason);
      else setError("Could not issue token.");
    }
  }

  async function onAccept(id: number) {
    setBusyId(id);
    setError(null);
    try {
      await acceptIntakeSubmission(identity, id);
      refresh();
    } catch (e: unknown) {
      if (e instanceof ApiError) setError(e.reason);
      else setError("Could not accept submission.");
    } finally {
      setBusyId(null);
    }
  }

  async function onReject(id: number) {
    setBusyId(id);
    setError(null);
    try {
      await rejectIntakeSubmission(identity, id, "");
      refresh();
    } catch (e: unknown) {
      if (e instanceof ApiError) setError(e.reason);
      else setError("Could not reject submission.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div
      className="modal-shade"
      role="dialog"
      aria-modal="true"
      aria-label="Intake queue"
    >
      <div className="modal-card modal-card--wide">
        <header style={{ display: "flex", justifyContent: "space-between" }}>
          <h2>Intake queue</h2>
          <button onClick={onClose} className="btn">Close</button>
        </header>
        <p>
          Issue a token to share with the patient out-of-band (text,
          email, your existing scheduling tool). Token URLs are
          single-use and expire in 72 hours.
        </p>
        <div>
          <button
            className="btn btn--primary"
            onClick={onIssue}
            data-testid="intake-issue-token"
          >
            Issue intake token
          </button>
        </div>
        {issued && (
          <div className="intake-issued" data-testid="intake-issued-block">
            <p>
              Share this URL with the patient. We will not show it again.
            </p>
            <code>{issued.url}</code>
            <p>Expires: {issued.expires_at}</p>
          </div>
        )}
        {error && <div role="alert">{error}</div>}
        <h3>Pending submissions</h3>
        {items === null && <div>Loading…</div>}
        {items && items.length === 0 && (
          <div data-testid="intake-queue-empty">No pending submissions.</div>
        )}
        {items && items.length > 0 && (
          <ul>
            {items.map((s) => (
              <li
                key={s.id}
                data-testid="intake-queue-row"
                className="intake-queue-row"
              >
                <span>Submission #{s.id}</span>
                <span>Submitted: {s.submitted_at}</span>
                <button
                  className="btn"
                  data-testid="intake-accept-btn"
                  disabled={busyId === s.id}
                  onClick={() => onAccept(s.id)}
                >
                  Accept
                </button>
                <button
                  className="btn"
                  data-testid="intake-reject-btn"
                  disabled={busyId === s.id}
                  onClick={() => onReject(s.id)}
                >
                  Reject
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
