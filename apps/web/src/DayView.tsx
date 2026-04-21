// Phase 38 — B2 — day-view / schedule screen.
//
// Front desk + clinician day rhythm. Buckets encounters by
// workflow status lane so the board reads "what's waiting, what's
// in workup, what's done." Pure client render — backend endpoints
// are the same as the list view.
//
// Rendered inline inside the existing detail section when
// `view === "day"`. Selecting a card defers to the parent `onPick`
// handler (same one the list uses).

import { Encounter } from "./api";

interface Props {
  encounters: Encounter[];
  date: Date;
  onPick: (id: Encounter["id"]) => void;
  onDateChange?: (next: Date) => void;
}

const LANES: { status: string; title: string }[] = [
  { status: "scheduled", title: "Waiting / arrived" },
  { status: "in_progress", title: "In workup" },
  { status: "draft_ready", title: "Draft ready" },
  { status: "review_needed", title: "Review needed" },
  { status: "completed", title: "Completed" },
];

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pickDayCandidate(e: Encounter): Date | null {
  const iso =
    e.scheduled_at ?? e.started_at ?? e.created_at ?? null;
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function DayView({ encounters, date, onPick, onDateChange }: Props) {
  const todays = encounters.filter((e) => {
    const d = pickDayCandidate(e);
    return d ? sameDay(d, date) : false;
  });

  const byLane: Record<string, Encounter[]> = {};
  for (const e of todays) {
    byLane[e.status] ||= [];
    byLane[e.status].push(e);
  }
  // Sort each lane by earliest scheduled/started time so the board
  // reads chronologically.
  for (const k of Object.keys(byLane)) {
    byLane[k].sort((a, b) => {
      const ta = pickDayCandidate(a)?.getTime() ?? 0;
      const tb = pickDayCandidate(b)?.getTime() ?? 0;
      return ta - tb;
    });
  }

  const shiftDay = (delta: number) => {
    if (!onDateChange) return;
    const next = new Date(date);
    next.setDate(next.getDate() + delta);
    onDateChange(next);
  };

  const dateInputValue = date.toISOString().slice(0, 10);

  return (
    <div className="dayview" data-testid="dayview">
      <div className="dayview__head">
        <h2>Day</h2>
        <span className="dayview__date" data-testid="dayview-date">
          {date.toLocaleDateString(undefined, {
            weekday: "short",
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
        {onDateChange && (
          <>
            <button
              className="btn btn--muted"
              onClick={() => shiftDay(-1)}
              data-testid="dayview-prev"
              aria-label="Previous day"
            >
              ←
            </button>
            <input
              type="date"
              value={dateInputValue}
              onChange={(e) => {
                if (!e.target.value) return;
                const [y, m, d] = e.target.value.split("-").map(Number);
                onDateChange(new Date(y, (m || 1) - 1, d || 1));
              }}
              data-testid="dayview-date-input"
              aria-label="Pick date"
            />
            <button
              className="btn btn--muted"
              onClick={() => shiftDay(1)}
              data-testid="dayview-next"
              aria-label="Next day"
            >
              →
            </button>
            <button
              className="btn"
              onClick={() => onDateChange(new Date())}
              data-testid="dayview-today"
            >
              Today
            </button>
          </>
        )}
        <span className="subtle-note">
          {todays.length} encounter{todays.length === 1 ? "" : "s"} on this day
        </span>
      </div>
      <div className="dayview__board">
        {LANES.map((lane) => {
          const rows = byLane[lane.status] || [];
          return (
            <div
              key={lane.status}
              className="dayview__lane"
              data-testid={`dayview-lane-${lane.status}`}
            >
              <h3>
                <span>{lane.title}</span>
                <span className="dayview__count">{rows.length}</span>
              </h3>
              {rows.length === 0 ? (
                <div className="empty" style={{ padding: "20px 12px" }}>
                  —
                </div>
              ) : (
                rows.map((e) => (
                  <button
                    key={String(e.id)}
                    type="button"
                    className="dayview__card"
                    onClick={() => onPick(e.id)}
                    data-testid={`dayview-card-${e.id}`}
                  >
                    <span className="dayview__card__main">
                      <span className="dayview__card__name">
                        {e.patient_name ?? e.patient_identifier}
                      </span>
                      <span className="dayview__card__meta">
                        {e.provider_name}
                      </span>
                    </span>
                    <span className="dayview__card__time">
                      {fmtTime(e.scheduled_at ?? e.started_at ?? e.created_at)}
                    </span>
                  </button>
                ))
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
