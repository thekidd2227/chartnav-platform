import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RetinalProposalReview } from "../RetinalProposalReview";
import type { RetinalProposal, ProposalMissingFlag } from "../retinalAnnotations";

function proposal(overrides: Partial<RetinalProposal> = {}): RetinalProposal {
  return {
    proposal_id: "p_test_drusen_od",
    kind: "symbol",
    symbol_type: "drusen",
    eye: "OD",
    x: 0.5,
    y: 0.5,
    zone: "macula",
    text: "OD drusen at macula",
    color: "#c1121f",
    confidence: 0.85,
    confidence_band: "high",
    source_phrase: "OD drusen at macula",
    source_start: 0,
    source_end: 19,
    reason: "matched finding=drusen + eye=OD + zone=macula",
    missing_flags: [],
    source: "ai_proposed",
    ...overrides,
  };
}

const SUMMARY = { high: 1, medium: 0, low: 0, needs_review: true };

describe("RetinalProposalReview", () => {
  it("renders proposals, ignored chatter, uncertain phrases, missing flags", () => {
    const missing: ProposalMissingFlag = {
      code: "missing_laterality",
      detail: "Found drusen but no eye",
      source_phrase: "Drusen at macula.",
      source_start: 0,
      source_end: 17,
    };
    render(
      <RetinalProposalReview
        clinicalText="OD drusen at macula"
        ignoredChatter={["Good morning, doctor"]}
        uncertainPhrases={["Patient seemed cheerful"]}
        proposals={[proposal()]}
        missingFlags={[missing]}
        confidenceSummary={SUMMARY}
        onApply={vi.fn()}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByTestId("retinal-proposal-review")).toBeInTheDocument();
    expect(
      screen.getByTestId("proposal-item-p_test_drusen_od")
    ).toBeInTheDocument();
    expect(screen.getByTestId("proposal-summary-high")).toHaveTextContent("1");
    expect(screen.getByTestId("proposal-missing-flags")).toBeInTheDocument();
    expect(screen.getByTestId("proposal-chatter")).toBeInTheDocument();
    expect(screen.getByTestId("proposal-uncertain")).toBeInTheDocument();
  });

  it("Apply calls onApply once and marks the item applied", async () => {
    const onApply = vi.fn();
    render(
      <RetinalProposalReview
        clinicalText=""
        ignoredChatter={[]}
        uncertainPhrases={[]}
        proposals={[proposal()]}
        missingFlags={[]}
        confidenceSummary={SUMMARY}
        onApply={onApply}
        onDismiss={vi.fn()}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByTestId("proposal-apply-p_test_drusen_od"));
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledWith(
      expect.objectContaining({ proposal_id: "p_test_drusen_od" })
    );
    // Re-clicking does NOT re-apply.
    await user.click(screen.getByTestId("proposal-apply-p_test_drusen_od"));
    expect(onApply).toHaveBeenCalledTimes(1);
  });

  it("Reject hides the proposal from the list and never calls onApply", async () => {
    const onApply = vi.fn();
    render(
      <RetinalProposalReview
        clinicalText=""
        ignoredChatter={[]}
        uncertainPhrases={[]}
        proposals={[proposal()]}
        missingFlags={[]}
        confidenceSummary={SUMMARY}
        onApply={onApply}
        onDismiss={vi.fn()}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByTestId("proposal-reject-p_test_drusen_od"));
    expect(
      screen.queryByTestId("proposal-item-p_test_drusen_od")
    ).not.toBeInTheDocument();
    expect(onApply).not.toHaveBeenCalled();
  });

  it("Apply remaining only fires for pending proposals", async () => {
    const a = proposal({ proposal_id: "p_a" });
    const b = proposal({
      proposal_id: "p_b",
      eye: "OS",
      text: "OS flame hemorrhage",
      symbol_type: "flame_hemorrhage",
    });
    const c = proposal({
      proposal_id: "p_c",
      eye: "OS",
      text: "OS microaneurysm",
      symbol_type: "microaneurysm",
    });
    const onApply = vi.fn();
    render(
      <RetinalProposalReview
        clinicalText=""
        ignoredChatter={[]}
        uncertainPhrases={[]}
        proposals={[a, b, c]}
        missingFlags={[]}
        confidenceSummary={SUMMARY}
        onApply={onApply}
        onDismiss={vi.fn()}
      />
    );
    const user = userEvent.setup();

    // Reject one and apply one individually first.
    await user.click(screen.getByTestId("proposal-reject-p_a"));
    await user.click(screen.getByTestId("proposal-apply-p_b"));
    expect(onApply).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("proposal-apply-remaining"));
    // Only p_c was still pending — only one extra apply fires.
    expect(onApply).toHaveBeenCalledTimes(2);
    expect(onApply).toHaveBeenLastCalledWith(
      expect.objectContaining({ proposal_id: "p_c" })
    );
  });

  it("Reject remaining never calls onApply", async () => {
    const onApply = vi.fn();
    render(
      <RetinalProposalReview
        clinicalText=""
        ignoredChatter={[]}
        uncertainPhrases={[]}
        proposals={[proposal({ proposal_id: "p_x" }), proposal({ proposal_id: "p_y" })]}
        missingFlags={[]}
        confidenceSummary={SUMMARY}
        onApply={onApply}
        onDismiss={vi.fn()}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByTestId("proposal-reject-remaining"));
    expect(onApply).not.toHaveBeenCalled();
    expect(screen.queryByTestId("proposal-item-p_x")).not.toBeInTheDocument();
    expect(screen.queryByTestId("proposal-item-p_y")).not.toBeInTheDocument();
  });

  it("disabled=true prevents apply / reject / bulk", async () => {
    const onApply = vi.fn();
    render(
      <RetinalProposalReview
        clinicalText=""
        ignoredChatter={[]}
        uncertainPhrases={[]}
        proposals={[proposal()]}
        missingFlags={[]}
        confidenceSummary={SUMMARY}
        onApply={onApply}
        onDismiss={vi.fn()}
        disabled
      />
    );
    expect(
      (screen.getByTestId(
        "proposal-apply-p_test_drusen_od"
      ) as HTMLButtonElement).disabled
    ).toBe(true);
    expect(
      (screen.getByTestId(
        "proposal-reject-p_test_drusen_od"
      ) as HTMLButtonElement).disabled
    ).toBe(true);
    expect(
      (screen.getByTestId("proposal-apply-remaining") as HTMLButtonElement).disabled
    ).toBe(true);
  });

  it("empty proposal list shows the empty marker", () => {
    render(
      <RetinalProposalReview
        clinicalText=""
        ignoredChatter={[]}
        uncertainPhrases={[]}
        proposals={[]}
        missingFlags={[]}
        confidenceSummary={{ high: 0, medium: 0, low: 0, needs_review: true }}
        onApply={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByTestId("proposal-empty")).toBeInTheDocument();
  });
});
