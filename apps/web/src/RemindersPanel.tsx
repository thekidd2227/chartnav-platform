// Phase 63 · item 1
//
// RemindersPanel — a first-class "what still needs attention" feed
// that lives alongside the encounter list. Clinicians + admins can
// create reminders (due date/time, optional patient-identifier tag,
// optional encounter_id), mark them completed, and filter by status.
//
// Design guardrails:
//   - Org-scoped by the backend; nothing to enforce on the client.
//   - Completion is a POST /reminders/{id}/complete (idempotent on
//     the server). We don't optimistic-update the list body so the
//     panel always reflects the backend's authoritative timestamp.
//   - The create form is intentionally minimal: title + due date +
//     optional patient identifier. Body + encounter_id are deferred
//     to PATCH (kept server-side for future expansion).
//
// data-testids are the contract the video-proof recorder drives.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Reminder,
  ReminderFilters,
  ReminderStatus,
  cancelReminder,
  completeReminder,
  createReminder,
  listReminders,
} from "./api";

interface Props {
  identity: string;
  onPatientSelect?: (patientIdentifier: string) => void;
  filters?: ReminderFilters;
  /**
   * Bumped by the panel whenever it creates/completes/cancels a
   * reminder, so the parent (calendar) can refetch its own feed.
   */
  onMutation?: () => void;
}

function toLocalIso(dt: Date): string {
  // Strip the seconds + TZ so the input type="datetime-local" value
  // round-trips. The API accepts bare ISO w/o TZ.
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}` +
    `T${pad(dt.getHours())}:${pad(dt.getMinutes())}`
  );
}

function fmtDue(iso: string): string {
  // Backend returns "YYYY-MM-DD HH:MM:SS" (no TZ). Render as a
  // short local-friendly string.
  const safe = iso.replace(" ", "T");
  const d = new Date(safe);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function RemindersPanel({ identity, onPatientSelect, filters, onMutation }: Props) {
  const [rows, setRows] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusTab, setStatusTab] = useState<ReminderStatus>("pending");

  const [title, setTitle] = useState("");
  const [pid, setPid] = useState("");
  const [dueAt, setDueAt] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1); // default: tomorrow, now
    d.setSeconds(0, 0);
    return toLocalIso(d);
  });
  const [creating, setCreating] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const merged: ReminderFilters = { ...filters, status: statusTab };
      const data = await listReminders(identity, merged);
      setRows(data);
    } catch (e: any) {
      setError(e?.message || "failed to load reminders");
    } finally {
      setLoading(false);
    }
  }, [identity, statusTab, filters]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      // Convert local datetime-local value to a plain ISO-ish string
      // the API accepts.
      await createReminder(identity, {
        title: title.trim(),
        due_at: dueAt, // e.g. 2026-05-01T10:00
        patient_identifier: pid.trim() || undefined,
      });
      setTitle("");
      setPid("");
      await reload();
      onMutation?.();
    } catch (e: any) {
      setError(e?.message || "failed to create reminder");
    } finally {
      setCreating(false);
    }
  };

  const onComplete = async (id: number) => {
    setError(null);
    try {
      await completeReminder(identity, id);
      await reload();
      onMutation?.();
    } catch (e: any) {
      setError(e?.message || "failed to complete reminder");
    }
  };

  const onCancel = async (id: number) => {
    setError(null);
    try {
      await cancelReminder(identity, id);
      await reload();
      onMutation?.();
    } catch (e: any) {
      setError(e?.message || "failed to cancel reminder");
    }
  };

  const counts = useMemo(() => {
    const c: Record<ReminderStatus, number> = {
      pending: 0, completed: 0, cancelled: 0,
    };
    for (const r of rows) c[r.status] = (c[r.status] || 0) + 1;
    return c;
  }, [rows]);

  return (
    <section
      className="reminders-panel"
      data-testid="reminders-panel"
      aria-label="Reminders"
    >
      <header className="reminders-panel__head">
        <h3>Reminders</h3>
        <p className="subtle-note">
          Follow-ups, recalls, and operational nudges that live on
          the calendar alongside encounters.
        </p>
      </header>

      <div className="reminders-panel__tabs" role="tablist" data-testid="reminders-tabs">
        {(["pending", "completed", "cancelled"] as ReminderStatus[]).map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={statusTab === s}
            className={`tab${statusTab === s ? " tab--active" : ""}`}
            onClick={() => setStatusTab(s)}
            data-testid={`reminders-tab-${s}`}
          >
            {s} ({counts[s] ?? 0})
          </button>
        ))}
      </div>

      <form
        className="reminders-panel__create"
        onSubmit={onCreate}
        data-testid="reminders-create-form"
      >
        <label>
          Title *
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-testid="reminders-create-title"
            placeholder="e.g. Call patient about IOP recheck"
            maxLength={256}
            required
          />
        </label>
        <label>
          Due
          <input
            type="datetime-local"
            value={dueAt}
            onChange={(e) => setDueAt(e.target.value)}
            data-testid="reminders-create-due"
            required
          />
        </label>
        <label>
          Patient ID (optional)
          <input
            value={pid}
            onChange={(e) => setPid(e.target.value)}
            data-testid="reminders-create-pid"
            placeholder="e.g. PT-1001"
            maxLength={64}
          />
        </label>
        <button
          type="submit"
          className="btn btn--primary"
          disabled={creating || !title.trim()}
          data-testid="reminders-create-submit"
        >
          {creating ? "Creating…" : "Create reminder"}
        </button>
      </form>

      {error && (
        <div
          className="banner banner--error"
          role="alert"
          data-testid="reminders-error"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="empty" data-testid="reminders-loading">Loading…</div>
      ) : rows.length === 0 ? (
        <div className="empty" data-testid="reminders-empty">
          No {statusTab} reminders.
        </div>
      ) : (
        <ul className="reminders-list" data-testid="reminders-list">
          {rows.map((r) => (
            <li
              key={r.id}
              className={`reminder reminder--${r.status}`}
              data-testid={`reminder-row-${r.id}`}
            >
              <div className="reminder__body">
                <div className="reminder__title" data-testid={`reminder-title-${r.id}`}>
                  {r.title}
                </div>
                <div className="reminder__meta subtle-note">
                  <span data-testid={`reminder-due-${r.id}`}>
                    Due {fmtDue(r.due_at)}
                  </span>
                  {r.patient_identifier ? (
                    <>
                      {" · "}
                      <button
                        className="link"
                        type="button"
                        onClick={() => onPatientSelect?.(r.patient_identifier!)}
                        data-testid={`reminder-patient-${r.id}`}
                        title="Jump to patient"
                      >
                        Patient {r.patient_identifier}
                      </button>
                    </>
                  ) : null}
                  {r.encounter_id ? (
                    <>
                      {" · "}
                      <span data-testid={`reminder-encounter-${r.id}`}>
                        Encounter #{r.encounter_id}
                      </span>
                    </>
                  ) : null}
                </div>
              </div>
              <div className="reminder__actions">
                {r.status === "pending" && (
                  <>
                    <button
                      className="btn btn--primary"
                      onClick={() => onComplete(r.id)}
                      data-testid={`reminder-complete-${r.id}`}
                    >
                      Complete
                    </button>
                    <button
                      className="btn"
                      onClick={() => onCancel(r.id)}
                      data-testid={`reminder-cancel-${r.id}`}
                    >
                      Cancel
                    </button>
                  </>
                )}
                {r.status === "completed" && (
                  <span
                    className="chip chip--ok"
                    data-testid={`reminder-completed-${r.id}`}
                  >
                    ✓ completed
                  </span>
                )}
                {r.status === "cancelled" && (
                  <span
                    className="chip"
                    data-testid={`reminder-cancelled-${r.id}`}
                  >
                    cancelled
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
