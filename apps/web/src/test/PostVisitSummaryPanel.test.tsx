// Phase 2 item 5 — vitest coverage for PostVisitSummaryPanel.
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { PostVisitSummaryPanel } from "../PostVisitSummaryPanel";
import * as api from "../api";

describe("PostVisitSummaryPanel", () => {
  beforeEach(() => {
    vi.spyOn(api, "generatePostVisitSummary").mockResolvedValue({
      id: 7,
      encounter_id: 3,
      note_version_id: 11,
      expires_at: "2026-05-26T12:00:00",
      read_link_token: "test-token-of-sufficient-length-1234",
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("disables the generate button when the note is not signed", () => {
    render(
      <PostVisitSummaryPanel
        identity="x"
        noteVersionId={11}
        signed={false}
      />
    );
    const btn = screen.getByTestId("generate-summary-btn");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent(/sign the note/i);
  });

  it("hint message renders when there is no note version yet", () => {
    render(
      <PostVisitSummaryPanel identity="x" noteVersionId={null} signed={false} />
    );
    expect(screen.getByTestId("post-visit-summary-panel")).toHaveTextContent(
      /sign the note first/i
    );
  });

  it("generates the summary and surfaces the read-link + copy button", async () => {
    render(
      <PostVisitSummaryPanel identity="x" noteVersionId={11} signed={true} />
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("generate-summary-btn"));
    });
    await waitFor(() => screen.getByTestId("summary-read-link"));
    expect(screen.getByTestId("summary-read-link")).toHaveTextContent(
      /\/summary\/test-token/
    );
    expect(screen.getByTestId("read-link-copy-btn")).toBeInTheDocument();
  });
});
