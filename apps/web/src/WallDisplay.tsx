// Phase 38 — B5 — wall display (rooms / waiting).
//
// A read-only full-screen surface that buckets today's encounters
// by location and by workflow status. Consumes the same encounter
// list payload the left rail uses.

import { useMemo, useEffect } from "react";
import { Encounter, Location } from "./api";

interface Props {
  encounters: Encounter[];
  locations: Location[];
  onClose: () => void;
}

function bucket(e: Encounter): string {
  if (e.status === "scheduled") return "Waiting";
  if (e.status === "in_progress") return "In room";
  if (e.status === "draft_ready" || e.status === "review_needed") return "Charting";
  if (e.status === "completed") return "Done";
  return "Other";
}

export function WallDisplay({ encounters, locations, onClose }: Props) {
  // Auto-refresh cadence — the parent keeps refreshing the
  // encounter list on its normal cadence, so here we only need to
  // re-render on window focus to re-evaluate "today".
  useEffect(() => {
    const onFocus = () => {
      // Force a render by touching the document title; the parent
      // owns the data source.
      document.title = document.title;
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const locById = useMemo(() => {
    const m = new Map<number, Location>();
    for (const l of locations) m.set(l.id, l);
    return m;
  }, [locations]);

  // Group by location, then count buckets.
  const board = useMemo(() => {
    const byLoc: Record<string, { loc: Location | null; counts: Record<string, number>; total: number }> = {};
    for (const e of encounters) {
      const key = e.location_id ? `loc-${e.location_id}` : "loc-none";
      if (!byLoc[key]) {
        byLoc[key] = {
          loc: e.location_id ? (locById.get(e.location_id) ?? null) : null,
          counts: {},
          total: 0,
        };
      }
      const b = bucket(e);
      byLoc[key].counts[b] = (byLoc[key].counts[b] || 0) + 1;
      byLoc[key].total += 1;
    }
    return byLoc;
  }, [encounters, locById]);

  const entries = Object.values(board).sort((a, b) => b.total - a.total);

  return (
    <div className="wall" role="dialog" aria-label="Wall display" data-testid="wall">
      <div className="wall__head">
        <h2>Clinic board · {new Date().toLocaleString()}</h2>
        <button
          className="btn wall__close"
          onClick={onClose}
          data-testid="wall-close"
        >
          Close (Esc)
        </button>
      </div>
      <div className="wall__grid">
        {entries.length === 0 && (
          <div className="empty">No activity today.</div>
        )}
        {entries.map((g, i) => (
          <div key={i} className="wall__tile" data-testid={`wall-tile-${i}`}>
            <h3>{g.loc ? g.loc.name : "No location"}</h3>
            <div className="row">
              <span>Waiting</span>
              <strong>{g.counts["Waiting"] || 0}</strong>
            </div>
            <div className="row">
              <span>In room</span>
              <strong>{g.counts["In room"] || 0}</strong>
            </div>
            <div className="row">
              <span>Charting</span>
              <strong>{g.counts["Charting"] || 0}</strong>
            </div>
            <div className="row">
              <span>Done</span>
              <strong>{g.counts["Done"] || 0}</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
