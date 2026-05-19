// apps/web/src/EncounterWorkflowStatusBar.tsx
//
// Compact, explicit 6-lane workflow visualization for a single
// encounter. The 6 lanes are the operator-facing names ChartNav
// uses to describe the journey from intake to export-ready:
//
//   1. Intake pending
//   2. Transcript queued
//   3. Transcript ready
//   4. Physician review in progress
//   5. Note approved
//   6. Export / billing ready
//
// The component is **derivation-only**: it maps the live encounter
// status (5 values) + optional scribe-session status (6 values)
// into the 6 explicit lanes. No new API, no backend change.
//
// The mapping is documented inline. When a lane is blocked
// upstream (e.g., transcript not yet queued), the downstream lanes
// render as `pending` so the clinician can see at a glance what
// the bottleneck is. The "approved" lane fills only when the
// encounter reaches `completed` (encounter status) OR the active
// scribe session reaches `finalized`. The "export / billing ready"
// lane fills only when the encounter is `completed` AND no
// blocking quality flags are unresolved (the caller passes that
// derived flag in).
//
// Important non-goals:
//   - does not place orders
//   - does not submit claims
//   - "export / billing ready" means **the chart record is signed
//     and dischargeable to the practice's existing billing / EHR
//     workflow** — not that ChartNav submits anything
//   - does not change encounter or scribe session state
//
// All copy is buyer-safe and provider-controlled.

import { useMemo } from "react";
import type { ScribeSessionStatus } from "./api";

export type EncounterStatusForBar =
  | "scheduled"
  | "in_progress"
  | "draft_ready"
  | "review_needed"
  | "completed";

export type LaneId =
  | "intake"
  | "transcript_queued"
  | "transcript_ready"
  | "physician_review"
  | "note_approved"
  | "export_billing_ready";

export type LaneState = "done" | "active" | "blocked" | "pending";

export interface LaneDescriptor {
  id: LaneId;
  label: string;
  short: string;
}

export const WORKFLOW_LANES: LaneDescriptor[] = [
  {
    id: "intake",
    label: "Intake pending",
    short: "Front desk readiness",
  },
  {
    id: "transcript_queued",
    label: "Transcript queued",
    short: "Source text captured",
  },
  {
    id: "transcript_ready",
    label: "Transcript ready",
    short: "Draft prepared",
  },
  {
    id: "physician_review",
    label: "Physician review in progress",
    short: "Provider editing",
  },
  {
    id: "note_approved",
    label: "Note approved",
    short: "Provider sign-off complete",
  },
  {
    id: "export_billing_ready",
    label: "Export / billing ready",
    short: "Hand-off to EHR + RCM",
  },
];

export interface DeriveLanesInput {
  encounterStatus: EncounterStatusForBar;
  scribeSessionStatus?: ScribeSessionStatus | null;
  /** When true, the export/billing lane is held at `pending` even
   *  if everything else is done — the caller (typically the
   *  encounter detail view) blocks export when unresolved
   *  `block`-severity quality flags exist. */
  hasBlockingQualityFlags?: boolean;
}

/** Pure derivation. Exported separately so tests can pin the
 *  full mapping table without rendering anything. */
export function deriveLaneStates(
  input: DeriveLanesInput,
): Record<LaneId, LaneState> {
  const { encounterStatus, scribeSessionStatus, hasBlockingQualityFlags } =
    input;

  // 1. Intake pending — done as soon as the encounter is no longer
  //    purely `scheduled`. While `scheduled`, the lane is `active`
  //    (the front desk owns it).
  const intake: LaneState =
    encounterStatus === "scheduled" ? "active" : "done";

  // 2. Transcript queued — done once a scribe session exists with
  //    any non-terminal-pre-ready status (`draft` or `processing`),
  //    OR if the encounter has advanced past `scheduled`. If the
  //    encounter is `in_progress` but no scribe session is present,
  //    transcript_queued is `active`.
  let transcriptQueued: LaneState;
  if (encounterStatus === "scheduled") {
    transcriptQueued = "pending";
  } else if (
    scribeSessionStatus === "draft" || scribeSessionStatus === "processing"
  ) {
    transcriptQueued = "done";
  } else if (
    scribeSessionStatus === "ready_for_review"
    || scribeSessionStatus === "reviewed"
    || scribeSessionStatus === "finalized"
  ) {
    transcriptQueued = "done";
  } else if (encounterStatus === "in_progress") {
    transcriptQueued = "active";
  } else {
    // draft_ready / review_needed / completed but no scribe session
    // tracked — that's fine; the encounter advanced via the
    // operational path.
    transcriptQueued = "done";
  }

  // 3. Transcript ready — done once the scribe session is
  //    `ready_for_review` or later, OR the encounter is
  //    `draft_ready` or later. While the scribe session is in
  //    `processing`, this lane is `active`.
  let transcriptReady: LaneState;
  if (encounterStatus === "scheduled") {
    transcriptReady = "pending";
  } else if (scribeSessionStatus === "processing") {
    transcriptReady = "active";
  } else if (
    scribeSessionStatus === "ready_for_review"
    || scribeSessionStatus === "reviewed"
    || scribeSessionStatus === "finalized"
  ) {
    transcriptReady = "done";
  } else if (
    encounterStatus === "draft_ready"
    || encounterStatus === "review_needed"
    || encounterStatus === "completed"
  ) {
    transcriptReady = "done";
  } else {
    // in_progress with no scribe session and no draft_ready
    // encounter status — transcript not yet ready.
    transcriptReady = "pending";
  }

  // 4. Physician review in progress — `active` when the encounter
  //    is `draft_ready` or the scribe session is `ready_for_review`
  //    or `reviewed`. Done once the scribe session is `finalized`
  //    or the encounter is `completed`.
  let physicianReview: LaneState;
  if (
    scribeSessionStatus === "finalized"
    || encounterStatus === "completed"
  ) {
    physicianReview = "done";
  } else if (
    encounterStatus === "draft_ready"
    || encounterStatus === "review_needed"
    || scribeSessionStatus === "ready_for_review"
    || scribeSessionStatus === "reviewed"
  ) {
    physicianReview = "active";
  } else if (transcriptReady === "done") {
    physicianReview = "pending";
  } else {
    physicianReview = "pending";
  }

  // 5. Note approved — done when the encounter is `completed` OR
  //    the active scribe session is `finalized`. Otherwise
  //    `pending`, with one exception: if we are blocked upstream
  //    (transcript not ready), report `pending` rather than
  //    `blocked` so the bar reads as a smooth progression.
  let noteApproved: LaneState;
  if (
    encounterStatus === "completed"
    || scribeSessionStatus === "finalized"
  ) {
    noteApproved = "done";
  } else if (physicianReview === "active") {
    noteApproved = "pending";
  } else {
    noteApproved = "pending";
  }

  // 6. Export / billing ready — done only if note_approved is done
  //    AND no blocking quality flags are unresolved.
  let exportBillingReady: LaneState;
  if (noteApproved !== "done") {
    exportBillingReady = "pending";
  } else if (hasBlockingQualityFlags) {
    exportBillingReady = "blocked";
  } else {
    exportBillingReady = "done";
  }

  return {
    intake,
    transcript_queued: transcriptQueued,
    transcript_ready: transcriptReady,
    physician_review: physicianReview,
    note_approved: noteApproved,
    export_billing_ready: exportBillingReady,
  };
}

interface Props extends DeriveLanesInput {
  /** Optional caption rendered above the bar (e.g., the patient
   *  display name). */
  caption?: string;
}

export function EncounterWorkflowStatusBar({
  caption,
  ...input
}: Props) {
  const states = useMemo(() => deriveLaneStates(input), [input]);
  const overallActiveLane = useMemo(() => {
    // The first non-`done` lane is the operator's current focus.
    for (const lane of WORKFLOW_LANES) {
      if (states[lane.id] !== "done") return lane;
    }
    return null;
  }, [states]);

  return (
    <section
      className="encounter-workflow-bar"
      data-testid="encounter-workflow-bar"
      aria-label="Encounter workflow status"
    >
      {caption && (
        <p
          className="encounter-workflow-bar__caption"
          data-testid="encounter-workflow-bar-caption"
        >
          {caption}
        </p>
      )}
      <ol className="encounter-workflow-bar__lanes">
        {WORKFLOW_LANES.map((lane, idx) => {
          const state = states[lane.id];
          return (
            <li
              key={lane.id}
              className={
                "encounter-workflow-bar__lane "
                + `encounter-workflow-bar__lane--${state}`
              }
              data-testid={`encounter-workflow-lane-${lane.id}`}
              data-state={state}
              aria-current={state === "active" ? "step" : undefined}
            >
              <span
                className="encounter-workflow-bar__num"
                aria-hidden="true"
              >
                {idx + 1}
              </span>
              <span className="encounter-workflow-bar__lane-label">
                {lane.label}
              </span>
              <span className="encounter-workflow-bar__lane-short">
                {lane.short}
              </span>
              <span
                className={
                  "encounter-workflow-bar__pill "
                  + `encounter-workflow-bar__pill--${state}`
                }
                data-testid={`encounter-workflow-pill-${lane.id}`}
              >
                {state}
              </span>
            </li>
          );
        })}
      </ol>
      {overallActiveLane && (
        <p
          className="encounter-workflow-bar__hint subtle-note"
          data-testid="encounter-workflow-bar-hint"
        >
          Next action lives in <strong>{overallActiveLane.label}</strong>.
          Provider review remains explicit; ChartNav does not advance
          state automatically.
        </p>
      )}
    </section>
  );
}
