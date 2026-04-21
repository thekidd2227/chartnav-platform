// Phase 38 — C4 — real timeline component.
//
// Replaces the existing stacked event-card list with a grouped,
// lane-based render. The payload is the same `WorkflowEvent[]` —
// no backend change. Lanes bucket the event types so a doctor can
// read "what happened here" instead of scrolling a log.

import { WorkflowEvent } from "./api";

/**
 * Classify an event_type string into:
 *   - a display lane ("Patient" / "Provider" / "Notes" / "System" / "Other")
 *   - a severity hint ("ok" / "warn" / "error" / undefined)
 *
 * The classifier is pure and defensive — any unknown event still
 * renders; it just lands in the generic lane.
 */
export function classifyEvent(t: string): {
  lane: string;
  severity?: "ok" | "warn" | "error";
  display: string;
} {
  const lower = (t || "").toLowerCase();
  // Severity hints.
  let severity: "ok" | "warn" | "error" | undefined;
  if (/fail|error|denied|conflict|mismatch/.test(lower)) severity = "error";
  else if (/retry|stale|requeue|warning|needs_review/.test(lower)) severity = "warn";
  else if (/sign|complete|export|created|succeeded|ok/.test(lower)) severity = "ok";

  // Lane routing.
  let lane = "Other";
  if (/patient|check_in|registration|reschedul/.test(lower)) lane = "Patient";
  else if (/provider|assign|provider_changed|transcrib/.test(lower)) lane = "Provider";
  else if (/note|findings|draft|transcript|sign|export|artifact/.test(lower))
    lane = "Notes";
  else if (
    /worker|queue|ingest|bridge|fhir|adapter|status|request|rate|audit/.test(
      lower
    )
  )
    lane = "System";
  else if (/status\s*changed|encounter\.status/.test(lower)) lane = "Patient";

  // Display label — preserve the raw event_type so the audit /
  // engineer surface remains recognizable, but keep the classified
  // lane so the visual grouping stays doctor-friendly.
  const display = t;

  return { lane, severity, display };
}

function fmt(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso ?? "";
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

const LANE_ORDER = ["Patient", "Provider", "Notes", "System", "Other"];

export function Timeline({
  events,
}: {
  events: WorkflowEvent[];
}) {
  const byLane: Record<string, { ev: WorkflowEvent; cls: ReturnType<typeof classifyEvent> }[]> = {};
  for (const ev of events) {
    const cls = classifyEvent(ev.event_type);
    byLane[cls.lane] ||= [];
    byLane[cls.lane].push({ ev, cls });
  }
  const activeLanes = LANE_ORDER.filter((l) => byLane[l]?.length);

  if (!events.length) {
    return (
      <div className="subtle-note" data-testid="timeline-empty">
        No events on this encounter yet.
      </div>
    );
  }

  return (
    <div className="timeline" data-testid="timeline">
      {activeLanes.map((lane) => (
        <TimelineLane key={lane} name={lane} entries={byLane[lane]} />
      ))}
    </div>
  );
}

function TimelineLane({
  name,
  entries,
}: {
  name: string;
  entries: { ev: WorkflowEvent; cls: ReturnType<typeof classifyEvent> }[];
}) {
  // Cluster consecutive same-type events ("status_changed status_changed
  // status_changed" → one chip + "×3").
  const clusters: { key: string; first: WorkflowEvent; cls: ReturnType<typeof classifyEvent>; count: number }[] = [];
  for (const e of entries) {
    const last = clusters[clusters.length - 1];
    if (last && last.first.event_type === e.ev.event_type) {
      last.count += 1;
    } else {
      clusters.push({
        key: String(e.ev.id),
        first: e.ev,
        cls: e.cls,
        count: 1,
      });
    }
  }

  return (
    <>
      <div className="timeline__lane" data-testid={`timeline-lane-${name}`}>
        {name}
      </div>
      <div className="timeline__row">
        {clusters.map((c) => (
          <span
            key={c.key}
            className="timeline__chip"
            data-severity={c.cls.severity ?? ""}
            data-testid={`timeline-chip-${c.first.id}`}
            title={`${c.first.event_type} · ${fmt(c.first.created_at)}`}
          >
            <span>{c.cls.display}</span>
            {c.count > 1 && (
              <span className="timeline__chip__cluster">×{c.count}</span>
            )}
            <time>{fmt(c.first.created_at)}</time>
          </span>
        ))}
      </div>
    </>
  );
}
