// Phase 63 · item 2
//
// Calendar — a month-grid view that fuses two data sources:
//   - Encounters with a scheduled_at, by day.
//   - Reminders with a due_at, by day.
//
// Each day cell shows (a) a count badge and (b) a short stack of
// items. Clicking an encounter chip opens that encounter in the
// main workspace (via onSelectEncounter). Clicking a reminder's
// patient tag calls onSelectPatient. Both callbacks are provided
// by App.tsx so the calendar can drive cross-patient navigation.
//
// The month navigation uses the same prev/today/next idiom as
// DayView so the muscle memory carries over.

import { useMemo } from "react";
import { Encounter, Reminder } from "./api";

interface Props {
  monthStart: Date;
  encounters: Encounter[];
  reminders: Reminder[];
  onMonthPrev: () => void;
  onMonthNext: () => void;
  onMonthToday: () => void;
  onSelectEncounter: (encounterId: number) => void;
  onSelectPatient: (patientIdentifier: string) => void;
  onSelectReminder?: (reminderId: number) => void;
}

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1);
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function parseBackendTs(s: string | null | undefined): Date | null {
  if (!s) return null;
  const iso = s.includes("T") ? s : s.replace(" ", "T");
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function buildMonthGrid(monthStart: Date): Date[] {
  // 6 × 7 = 42 cells, starting on Sunday.
  const start = new Date(monthStart);
  start.setDate(1);
  const startDay = start.getDay(); // 0 = Sun
  start.setDate(start.getDate() - startDay);
  const cells: Date[] = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    cells.push(d);
  }
  return cells;
}

export function Calendar({
  monthStart,
  encounters,
  reminders,
  onMonthPrev,
  onMonthNext,
  onMonthToday,
  onSelectEncounter,
  onSelectPatient,
}: Props) {
  const grid = useMemo(() => buildMonthGrid(monthStart), [monthStart]);

  const encByDay = useMemo(() => {
    const m = new Map<string, Encounter[]>();
    for (const e of encounters) {
      const d = parseBackendTs((e as any).scheduled_at);
      if (!d) continue;
      const k = dayKey(d);
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(e);
    }
    return m;
  }, [encounters]);

  const remByDay = useMemo(() => {
    const m = new Map<string, Reminder[]>();
    for (const r of reminders) {
      const d = parseBackendTs(r.due_at);
      if (!d) continue;
      const k = dayKey(d);
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(r);
    }
    return m;
  }, [reminders]);

  const monthLabel = monthStart.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
  });

  const today = new Date();

  return (
    <section className="calendar" data-testid="calendar">
      <header className="calendar__head">
        <button
          className="btn"
          onClick={onMonthPrev}
          data-testid="calendar-prev"
          aria-label="Previous month"
        >
          ‹
        </button>
        <h3 className="calendar__month" data-testid="calendar-month">
          {monthLabel}
        </h3>
        <button
          className="btn"
          onClick={onMonthToday}
          data-testid="calendar-today"
        >
          Today
        </button>
        <button
          className="btn"
          onClick={onMonthNext}
          data-testid="calendar-next"
          aria-label="Next month"
        >
          ›
        </button>
      </header>
      <div className="calendar__grid" data-testid="calendar-grid">
        <div className="calendar__weekday-row">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
            <div key={d} className="calendar__weekday">{d}</div>
          ))}
        </div>
        <div className="calendar__cells">
          {grid.map((d, i) => {
            const key = dayKey(d);
            const inMonth = d.getMonth() === monthStart.getMonth();
            const isToday = sameDay(d, today);
            const encs = encByDay.get(key) || [];
            const rems = remByDay.get(key) || [];
            const totalCount = encs.length + rems.length;
            const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
            return (
              <div
                key={i}
                className={[
                  "calendar__cell",
                  inMonth ? "" : "calendar__cell--other-month",
                  isToday ? "calendar__cell--today" : "",
                ].filter(Boolean).join(" ")}
                data-testid={`calendar-day-${iso}`}
                data-iso={iso}
              >
                <div className="calendar__cell-head">
                  <span className="calendar__cell-date">{d.getDate()}</span>
                  {totalCount > 0 && (
                    <span
                      className="calendar__cell-count"
                      data-testid={`calendar-day-count-${iso}`}
                    >
                      {totalCount}
                    </span>
                  )}
                </div>
                <div className="calendar__cell-items">
                  {encs.slice(0, 2).map((e) => (
                    <button
                      key={`e-${e.id}`}
                      type="button"
                      className="calendar__chip calendar__chip--enc"
                      onClick={() => onSelectEncounter(Number(e.id))}
                      data-testid={`calendar-encounter-${e.id}`}
                      title={`${e.patient_name ?? e.patient_identifier} · ${e.provider_name}`}
                    >
                      📅 {e.patient_name ?? e.patient_identifier}
                    </button>
                  ))}
                  {rems.slice(0, 3).map((r) => (
                    <button
                      key={`r-${r.id}`}
                      type="button"
                      className={`calendar__chip calendar__chip--rem calendar__chip--${r.status}`}
                      onClick={() =>
                        r.patient_identifier
                          ? onSelectPatient(r.patient_identifier)
                          : undefined
                      }
                      data-testid={`calendar-reminder-${r.id}`}
                      title={r.title}
                    >
                      {r.status === "completed" ? "✓" : "⏰"} {r.title}
                    </button>
                  ))}
                  {encs.length + rems.length > 5 && (
                    <span
                      className="calendar__chip-more"
                      data-testid={`calendar-more-${iso}`}
                    >
                      +{encs.length + rems.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export { addMonths, startOfMonth };
