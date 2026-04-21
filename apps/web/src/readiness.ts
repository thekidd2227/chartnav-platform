// ROI wave 1 · items 5 + 6
//
// Shared derivation utilities for:
//   - Queue presets (5)
//   - Readiness / exception indicators on encounter rows (6)
//
// All logic is pure; callers pass in the current encounter list +
// "now" and get back classified rows or filtered subsets. Using
// current encounter data only — no extra API calls. Indicators are
// deliberately conservative: when we don't know, we return
// "unknown" rather than inventing a status.

import { Encounter } from "./api";

export type ReadinessKind =
  | "arriving_soon"      // scheduled, scheduled_at within +/- 30min
  | "checked_in"         // in_progress, started_at set
  | "ready_for_tech"     // scheduled + already past scheduled_at
  | "waiting_provider"   // in_progress but no draft ready yet
  | "draft_ready"        // draft_ready
  | "review_needed"      // review_needed (exception)
  | "completed"          // completed
  | "blocked"            // heuristic: review_needed older than 48h
  | "transmit_issue"     // hook for adapter-level failures (bridged)
  | "unknown";

export interface Readiness {
  kind: ReadinessKind;
  /** UI severity bucket — drives the pill color. */
  severity: "ok" | "info" | "warn" | "error" | "muted";
  /** Short, action-oriented label shown on the badge. */
  label: string;
  /** Optional longer tooltip hint. */
  tooltip?: string;
}

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

function parseIso(s: string | null | undefined): number | null {
  if (!s) return null;
  const d = new Date(s.replace(" ", "T"));
  return Number.isNaN(d.getTime()) ? null : d.getTime();
}

export function deriveReadiness(enc: Encounter, now: number = Date.now()): Readiness {
  const status = enc.status;
  const scheduled = parseIso(enc.scheduled_at);
  const started = parseIso(enc.started_at);
  const completedAt = parseIso(enc.completed_at);

  // Explicit status-driven classifications.
  if (status === "completed") {
    return { kind: "completed", severity: "ok", label: "Completed" };
  }
  if (status === "review_needed") {
    // Stale review? Escalate to "blocked".
    const created = parseIso(enc.created_at);
    const age = created ? now - created : 0;
    if (age > 48 * HOUR) {
      return {
        kind: "blocked",
        severity: "error",
        label: "Blocked",
        tooltip: "Review needed > 48h — escalate",
      };
    }
    return {
      kind: "review_needed",
      severity: "warn",
      label: "Review",
      tooltip: "Provider review required before completion",
    };
  }
  if (status === "draft_ready") {
    return {
      kind: "draft_ready",
      severity: "info",
      label: "Draft ready",
      tooltip: "Draft generated, awaiting provider review",
    };
  }
  if (status === "in_progress") {
    return {
      kind: "waiting_provider",
      severity: "info",
      label: "In workup",
      tooltip: "Encounter started — awaiting transcript/draft",
    };
  }
  if (status === "scheduled") {
    if (scheduled == null) {
      return { kind: "unknown", severity: "muted", label: "Scheduled" };
    }
    const delta = scheduled - now;
    if (delta < -HOUR) {
      return {
        kind: "ready_for_tech",
        severity: "warn",
        label: "Late",
        tooltip: "Past scheduled time and not checked in",
      };
    }
    if (delta <= 30 * MINUTE) {
      return {
        kind: "arriving_soon",
        severity: "info",
        label: "Arriving",
        tooltip: "Scheduled within the next 30 minutes",
      };
    }
    return { kind: "unknown", severity: "muted", label: "Scheduled" };
  }
  return { kind: "unknown", severity: "muted", label: status.replace(/_/g, " ") };
}

// --- Queue presets ------------------------------------------------------
//
// Each preset is a deterministic predicate over an encounter list. The
// caller applies the predicate locally to the already-loaded list so
// switching presets is free.
//
// Role-neutral labels with hints that surface when a role has
// stronger or different semantics (front desk vs clinical).

export type QueuePreset =
  | "all"
  | "arriving_soon"
  | "checked_in"
  | "ready_for_tech"
  | "waiting_provider"
  | "transcript_pending"
  | "draft_ready"
  | "review_needed"
  | "blocked"
  | "transmit_issue";

export interface QueuePresetDescriptor {
  key: QueuePreset;
  label: string;
  tooltip: string;
  match: (enc: Encounter, now: number) => boolean;
  audience: "all" | "front_desk" | "clinical";
}

export const QUEUE_PRESETS: QueuePresetDescriptor[] = [
  {
    key: "all",
    label: "All",
    tooltip: "Show everything on this list",
    audience: "all",
    match: () => true,
  },
  {
    key: "arriving_soon",
    label: "Arriving",
    tooltip: "Scheduled within the next 30 minutes",
    audience: "front_desk",
    match: (e, now) => deriveReadiness(e, now).kind === "arriving_soon",
  },
  {
    key: "checked_in",
    label: "Checked in",
    tooltip: "in_progress, started",
    audience: "front_desk",
    match: (e) => e.status === "in_progress" && !!e.started_at,
  },
  {
    key: "ready_for_tech",
    label: "Ready for tech",
    tooltip: "Past scheduled time and not yet checked in",
    audience: "clinical",
    match: (e, now) => deriveReadiness(e, now).kind === "ready_for_tech",
  },
  {
    key: "waiting_provider",
    label: "Waiting provider",
    tooltip: "In workup, awaiting draft",
    audience: "clinical",
    match: (e) => e.status === "in_progress",
  },
  {
    key: "transcript_pending",
    label: "Transcript pending",
    tooltip: "In workup or scheduled — transcript not yet drafted",
    audience: "clinical",
    match: (e) => e.status === "in_progress" || e.status === "scheduled",
  },
  {
    key: "draft_ready",
    label: "Draft ready",
    tooltip: "Draft awaiting provider review",
    audience: "clinical",
    match: (e) => e.status === "draft_ready",
  },
  {
    key: "review_needed",
    label: "Review needed",
    tooltip: "Provider review required",
    audience: "clinical",
    match: (e) => e.status === "review_needed",
  },
  {
    key: "blocked",
    label: "Blocked",
    tooltip: "Review needed > 48h — escalate",
    audience: "clinical",
    match: (e, now) => deriveReadiness(e, now).kind === "blocked",
  },
  {
    key: "transmit_issue",
    label: "Transmit issue",
    tooltip:
      "Externally-sourced encounters with a source-of-truth mismatch or transmit failure",
    audience: "clinical",
    match: (e) => {
      // Heuristic — bridged encounters with a _source other than
      // chartnav where we'd expect stabilized mirror. When adapter
      // telemetry lands per-row, this should read a real flag.
      return (
        !!e._external_ref &&
        typeof e._source === "string" &&
        e._source !== "chartnav" &&
        e.status === "review_needed"
      );
    },
  },
];

export function presetsForAudience(
  audience: "all" | "front_desk" | "clinical"
): QueuePresetDescriptor[] {
  if (audience === "all") return QUEUE_PRESETS;
  return QUEUE_PRESETS.filter(
    (p) => p.audience === "all" || p.audience === audience
  );
}
