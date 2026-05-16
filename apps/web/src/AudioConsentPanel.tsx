/**
 * Phase 25A — GH-001 audio consent panel.
 *
 * Renders the encounter's current audio-consent state and lets
 * permitted roles (admin / clinician / front_desk / technician)
 * capture, revoke, or change consent. Reviewer is read-only.
 *
 * The panel owns the consent fetch and PUT lifecycle locally and
 * notifies the parent via `onConsentChange` so the parent can
 * disable the Record button until `recording_permitted` flips
 * true. This keeps the consent contract authoritative on the
 * server — the parent never decides for itself whether recording
 * is allowed, it just mirrors what the server returns.
 *
 * UX rules:
 *  - Microphone permission is NOT patient consent. The panel
 *    must be checked off before the Record button is enabled,
 *    no matter what the OS-level mic permission says.
 *  - Note text is operator-facing only ("verbal consent at
 *    intake"); no PHI. The server audits status + method, not
 *    the note body.
 *  - On read-only role (reviewer) the controls hide; only the
 *    status badge is shown.
 */

import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
} from "react";
import {
  fetchAudioConsent,
  setAudioConsent as putAudioConsent,
  type AudioConsent,
  type AudioConsentMethod,
  type AudioConsentStatus,
} from "./api";

const WRITE_ROLES: ReadonlySet<string> = new Set([
  "admin",
  "clinician",
  "front_desk",
  "technician",
]);

const STATUS_LABEL: Record<AudioConsentStatus, string> = {
  granted: "Consent on file",
  declined: "Patient declined",
  revoked: "Consent revoked",
  not_recorded: "Consent not captured",
};

const METHOD_LABEL: Record<AudioConsentMethod, string> = {
  verbal: "Verbal",
  written: "Written",
  demo_fake: "Demo (no PHI)",
  unknown: "Unknown",
};

interface AudioConsentPanelProps {
  identity: string;
  encounterId: number;
  role: string;
  onConsentChange?: (consent: AudioConsent | null) => void;
}

export function AudioConsentPanel({
  identity,
  encounterId,
  role,
  onConsentChange,
}: AudioConsentPanelProps): JSX.Element {
  const [consent, setConsent] = useState<AudioConsent | null>(null);
  const [status, setStatus] = useState<AudioConsentStatus>("granted");
  const [method, setMethod] = useState<AudioConsentMethod>("verbal");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canWrite = WRITE_ROLES.has(role);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const c = await fetchAudioConsent(identity, encounterId);
      setConsent(c);
      onConsentChange?.(c);
      // Pre-populate the editor with the current state so a
      // "change method" edit is one click.
      if (c.status !== "not_recorded") {
        setStatus(c.status);
        setMethod(c.method);
        setNote(c.note ?? "");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      onConsentChange?.(null);
    }
  }, [identity, encounterId, onConsentChange]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canWrite || busy) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await putAudioConsent(identity, encounterId, {
        status,
        method,
        note: note.trim() ? note.trim() : null,
      });
      setConsent(updated);
      onConsentChange?.(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const permitted = consent?.recording_permitted === true;
  const statusKey: AudioConsentStatus =
    consent?.status ?? "not_recorded";

  return (
    <div
      className="event-form workspace__audio-consent"
      data-testid="audio-consent-panel"
    >
      <div className="workspace__audio-consent-head">
        <strong>Patient audio consent</strong>
        <span
          className={`badge badge--${permitted ? "ok" : "warn"}`}
          data-testid="audio-consent-status-badge"
          data-status={statusKey}
        >
          {STATUS_LABEL[statusKey]}
        </span>
      </div>

      {consent && consent.status !== "not_recorded" && (
        <p className="subtle-note" data-testid="audio-consent-current">
          Current: {STATUS_LABEL[consent.status]} ·{" "}
          {METHOD_LABEL[consent.method]}
          {consent.note ? ` · ${consent.note}` : ""}
        </p>
      )}

      {!permitted && (
        <p
          className="subtle-note workspace__audio-consent-warn"
          data-testid="audio-consent-blocked"
          role="status"
        >
          Recording is blocked until consent is captured.
          Microphone permission alone is <em>not</em> patient
          consent.
        </p>
      )}

      {canWrite ? (
        <form
          onSubmit={onSubmit}
          data-testid="audio-consent-form"
          className="row workspace__audio-consent-form"
        >
          <label>
            Status
            <select
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as AudioConsentStatus)
              }
              data-testid="audio-consent-status-select"
              disabled={busy}
            >
              <option value="granted">Granted</option>
              <option value="declined">Declined</option>
              <option value="revoked">Revoked</option>
              <option value="not_recorded">Not recorded</option>
            </select>
          </label>
          <label>
            Method
            <select
              value={method}
              onChange={(e) =>
                setMethod(e.target.value as AudioConsentMethod)
              }
              data-testid="audio-consent-method-select"
              disabled={busy}
            >
              <option value="verbal">Verbal</option>
              <option value="written">Written</option>
              <option value="unknown">Unknown</option>
              <option value="demo_fake">Demo (no PHI)</option>
            </select>
          </label>
          <label className="workspace__audio-consent-note">
            Note (operator-facing, no PHI)
            <input
              type="text"
              maxLength={500}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. verbal consent at intake"
              data-testid="audio-consent-note-input"
              disabled={busy}
            />
          </label>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={busy}
            data-testid="audio-consent-submit"
          >
            {busy ? "Saving…" : "Save consent"}
          </button>
        </form>
      ) : (
        <p
          className="subtle-note"
          data-testid="audio-consent-readonly-note"
        >
          Read-only — only clinic staff can capture or revoke consent.
        </p>
      )}

      {error && (
        <p
          className="subtle-note workspace__audio-consent-error"
          data-testid="audio-consent-error"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
}
