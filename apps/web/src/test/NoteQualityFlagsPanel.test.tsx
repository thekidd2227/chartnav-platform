// NoteQualityFlagsPanel.test.tsx
//
// Pin the panel's rendering surface: counts header, severity-
// ordered flags, acknowledge action wiring, empty-state, and the
// blocking-flag hint.

import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NoteQualityFlagsPanel } from "../NoteQualityFlagsPanel";

const COMPLETE_DRAFT =
  "Chief complaint: blurry vision OD.\n"
  + "History: 3 days of floaters.\n"
  + "Exam: vitreous syneresis OD, no retinal tear.\n"
  + "Assessment: acute PVD OD.\n"
  + "Plan: return precautions, follow-up in 4 weeks.\n";

describe("NoteQualityFlagsPanel — empty + happy path", () => {
  it("renders the empty-state when the draft is clean (no flags)", () => {
    render(
      <NoteQualityFlagsPanel
        draftText={COMPLETE_DRAFT}
        context={{ specialty: "general", encounterLaterality: "OD" }}
      />,
    );
    expect(screen.getByTestId("note-quality-panel")).toBeInTheDocument();
    expect(screen.getByTestId("note-quality-panel-empty")).toBeInTheDocument();
    expect(
      screen.getByTestId("note-quality-panel-completeness"),
    ).toHaveTextContent("100%");
  });

  it("renders the title + safety-claim subtitle", () => {
    render(<NoteQualityFlagsPanel draftText="" />);
    expect(
      screen.getByTestId("note-quality-panel-title"),
    ).toHaveTextContent(/note quality checks/i);
    // Panel subtitle restates the safe-claims contract.
    expect(screen.getByTestId("note-quality-panel")).toHaveTextContent(
      /Provider review remains the source of truth/i,
    );
  });
});

describe("NoteQualityFlagsPanel — flag rendering + ordering", () => {
  it("renders block-severity flags above warns", () => {
    render(
      <NoteQualityFlagsPanel
        draftText="Patient with OS retinal tear. Autonomous diagnosis suggests it."
        context={{ specialty: "general", encounterLaterality: "OD" }}
      />,
    );
    const list = screen.getByTestId("note-quality-panel-flags");
    const items = within(list).getAllByRole("listitem");
    // First item must be the laterality_conflict block.
    expect(items[0]).toHaveAttribute("data-severity", "block");
    // Banned phrase warn must come after.
    const block = screen.getByTestId(
      "note-quality-panel-flag-laterality_conflict",
    );
    const warn = screen.getByTestId("note-quality-panel-flag-banned_phrase");
    expect(block).toBeInTheDocument();
    expect(warn).toBeInTheDocument();
  });

  it("shows a block-hint when any blocking flag is present", () => {
    render(
      <NoteQualityFlagsPanel
        draftText="Patient with OS findings."
        context={{ specialty: "general", encounterLaterality: "OD" }}
      />,
    );
    expect(
      screen.getByTestId("note-quality-panel-block-hint"),
    ).toBeInTheDocument();
  });

  it("does not show the block-hint when no flags block", () => {
    render(
      <NoteQualityFlagsPanel
        draftText="Chief complaint: blurry vision\n"
        context={{ specialty: "general" }}
      />,
    );
    expect(
      screen.queryByTestId("note-quality-panel-block-hint"),
    ).toBeNull();
  });

  it("updates the severity counts in the header", () => {
    render(
      <NoteQualityFlagsPanel
        draftText="Patient with OS findings. Autonomous diagnosis."
        context={{ specialty: "general", encounterLaterality: "OD" }}
      />,
    );
    expect(
      screen.getByTestId("note-quality-panel-count-block"),
    ).toHaveTextContent("1");
    // banned_phrase + missing_critical_element + completeness_low etc.
    const warn = Number(
      screen.getByTestId("note-quality-panel-count-warn").textContent,
    );
    expect(warn).toBeGreaterThanOrEqual(2);
  });
});

describe("NoteQualityFlagsPanel — acknowledge wiring", () => {
  it("renders an action button when onAcknowledge is provided + the flag is not acked", async () => {
    const user = userEvent.setup();
    const ack = vi.fn();
    render(
      <NoteQualityFlagsPanel
        draftText="Patient with OS findings."
        context={{ specialty: "general", encounterLaterality: "OD" }}
        onAcknowledge={ack}
      />,
    );
    const ackBtn = screen.getByTestId(
      "note-quality-panel-ack-laterality_conflict",
    );
    await user.click(ackBtn);
    expect(ack).toHaveBeenCalledWith("laterality_conflict");
  });

  it("renders an Acknowledged marker for codes in acknowledgedCodes", () => {
    render(
      <NoteQualityFlagsPanel
        draftText="Patient with OS findings."
        context={{ specialty: "general", encounterLaterality: "OD" }}
        onAcknowledge={() => {}}
        acknowledgedCodes={new Set(["laterality_conflict"])}
      />,
    );
    expect(
      screen.getByTestId("note-quality-panel-acked-laterality_conflict"),
    ).toBeInTheDocument();
    // Action button must NOT render when the flag is already acked.
    expect(
      screen.queryByTestId("note-quality-panel-ack-laterality_conflict"),
    ).toBeNull();
  });

  it("omits the action button entirely when onAcknowledge is not supplied", () => {
    render(
      <NoteQualityFlagsPanel
        draftText="Patient with OS findings."
        context={{ specialty: "general", encounterLaterality: "OD" }}
      />,
    );
    expect(
      screen.queryByTestId("note-quality-panel-ack-laterality_conflict"),
    ).toBeNull();
  });
});
