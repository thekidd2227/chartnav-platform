// EncounterWorkflowStatusBar.test.tsx
//
// Pin the derivation table from encounter status + scribe-session
// status → 6 explicit lane states. The mapping is the operator-
// facing source of truth; if it changes, downstream UI (e.g., the
// production-readiness panel) needs to be updated in lockstep.

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  deriveLaneStates,
  EncounterWorkflowStatusBar,
  WORKFLOW_LANES,
  type LaneId,
  type LaneState,
} from "../EncounterWorkflowStatusBar";

function expectStates(
  actual: Record<LaneId, LaneState>,
  expected: Partial<Record<LaneId, LaneState>>,
) {
  for (const [k, v] of Object.entries(expected) as [LaneId, LaneState][]) {
    expect(actual[k]).toBe(v);
  }
}

describe("EncounterWorkflowStatusBar — deriveLaneStates", () => {
  it("scheduled encounter, no scribe session → intake active, rest pending", () => {
    const states = deriveLaneStates({ encounterStatus: "scheduled" });
    expectStates(states, {
      intake: "active",
      transcript_queued: "pending",
      transcript_ready: "pending",
      physician_review: "pending",
      note_approved: "pending",
      export_billing_ready: "pending",
    });
  });

  it("in_progress + scribe session draft → intake done, transcript_queued done, transcript_ready pending", () => {
    const states = deriveLaneStates({
      encounterStatus: "in_progress",
      scribeSessionStatus: "draft",
    });
    expectStates(states, {
      intake: "done",
      transcript_queued: "done",
      transcript_ready: "pending",
      physician_review: "pending",
      note_approved: "pending",
      export_billing_ready: "pending",
    });
  });

  it("in_progress + scribe session processing → transcript_ready active", () => {
    const states = deriveLaneStates({
      encounterStatus: "in_progress",
      scribeSessionStatus: "processing",
    });
    expect(states.transcript_ready).toBe("active");
  });

  it("draft_ready encounter → transcript_ready done, physician_review active", () => {
    const states = deriveLaneStates({ encounterStatus: "draft_ready" });
    expectStates(states, {
      intake: "done",
      transcript_queued: "done",
      transcript_ready: "done",
      physician_review: "active",
      note_approved: "pending",
      export_billing_ready: "pending",
    });
  });

  it("review_needed encounter → physician_review active, note_approved pending", () => {
    const states = deriveLaneStates({ encounterStatus: "review_needed" });
    expect(states.physician_review).toBe("active");
    expect(states.note_approved).toBe("pending");
  });

  it("scribe session finalized → physician_review done, note_approved done, export_billing_ready done by default", () => {
    const states = deriveLaneStates({
      encounterStatus: "draft_ready",
      scribeSessionStatus: "finalized",
    });
    expectStates(states, {
      physician_review: "done",
      note_approved: "done",
      export_billing_ready: "done",
    });
  });

  it("completed encounter → all lanes done unless blocking flags hold export back", () => {
    const states = deriveLaneStates({ encounterStatus: "completed" });
    expect(states.physician_review).toBe("done");
    expect(states.note_approved).toBe("done");
    expect(states.export_billing_ready).toBe("done");
  });

  it("export_billing_ready holds at `blocked` when quality flags block", () => {
    const states = deriveLaneStates({
      encounterStatus: "completed",
      hasBlockingQualityFlags: true,
    });
    expect(states.note_approved).toBe("done");
    expect(states.export_billing_ready).toBe("blocked");
  });

  it("export_billing_ready stays pending if note_approved is not done, regardless of flags", () => {
    const states = deriveLaneStates({
      encounterStatus: "draft_ready",
      hasBlockingQualityFlags: true,
    });
    expect(states.note_approved).toBe("pending");
    expect(states.export_billing_ready).toBe("pending");
  });
});

describe("EncounterWorkflowStatusBar — render", () => {
  it("renders all six lanes with stable testids and the right state pills", () => {
    render(
      <EncounterWorkflowStatusBar
        encounterStatus="draft_ready"
        scribeSessionStatus="ready_for_review"
      />,
    );
    for (const lane of WORKFLOW_LANES) {
      const el = screen.getByTestId(`encounter-workflow-lane-${lane.id}`);
      expect(el).toBeInTheDocument();
      expect(el).toHaveAttribute("data-state");
    }
    // Physician review is active in this state.
    expect(
      screen.getByTestId("encounter-workflow-lane-physician_review"),
    ).toHaveAttribute("data-state", "active");
    expect(
      screen.getByTestId("encounter-workflow-pill-physician_review"),
    ).toHaveTextContent("active");
  });

  it("renders the caption when provided", () => {
    render(
      <EncounterWorkflowStatusBar
        encounterStatus="scheduled"
        caption="Morgan Lee — retina follow-up"
      />,
    );
    expect(
      screen.getByTestId("encounter-workflow-bar-caption"),
    ).toHaveTextContent("Morgan Lee");
  });

  it("renders the next-action hint when at least one lane is not done", () => {
    render(<EncounterWorkflowStatusBar encounterStatus="scheduled" />);
    expect(
      screen.getByTestId("encounter-workflow-bar-hint"),
    ).toHaveTextContent(/Intake pending/);
  });

  it("omits the hint when every lane is done", () => {
    render(<EncounterWorkflowStatusBar encounterStatus="completed" />);
    expect(
      screen.queryByTestId("encounter-workflow-bar-hint"),
    ).toBeNull();
  });

  it("renders the export lane as blocked when quality flags block", () => {
    render(
      <EncounterWorkflowStatusBar
        encounterStatus="completed"
        hasBlockingQualityFlags
      />,
    );
    const cell = screen.getByTestId(
      "encounter-workflow-lane-export_billing_ready",
    );
    expect(cell).toHaveAttribute("data-state", "blocked");
  });
});
