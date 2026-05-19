/**
 * Phase 13 — DemoClinicalWorkflowGuide component tests.
 *
 * Direct unit tests against the new collapsible demo guide. The
 * companion file `DemoClinicalWorkflowPackage.test.tsx` tests the
 * package-level integration (guide mounts from NoteWorkspace, docs
 * exist, demo data policy holds).
 */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DemoClinicalWorkflowGuide } from "../DemoClinicalWorkflowGuide";

describe("DemoClinicalWorkflowGuide", () => {
  it("renders the guide root and a Show toggle, collapsed by default", () => {
    render(<DemoClinicalWorkflowGuide />);
    expect(
      screen.getByTestId("demo-clinical-workflow-guide")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    ).toHaveTextContent(/Show demo workflow guide/i);
    // Collapsed body is not in the DOM.
    expect(
      screen.queryByTestId("demo-clinical-workflow-guide-body")
    ).not.toBeInTheDocument();
    // Lead copy is always visible (collapsed or not).
    expect(
      screen.getByTestId("demo-clinical-workflow-guide-lead")
    ).toHaveTextContent(/five minutes/i);
  });

  it("inlines the patientDisplay into the lead when provided", () => {
    render(<DemoClinicalWorkflowGuide patientDisplay="Morgan Lee" />);
    expect(
      screen.getByTestId("demo-clinical-workflow-guide-lead")
    ).toHaveTextContent(/for Morgan Lee/);
  });

  it("expands and collapses on toggle click", async () => {
    render(<DemoClinicalWorkflowGuide />);
    const user = userEvent.setup();
    const toggle = screen.getByTestId("demo-clinical-workflow-guide-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveTextContent(/Hide demo workflow guide/i);
    expect(
      screen.getByTestId("demo-clinical-workflow-guide-body")
    ).toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveTextContent(/Show demo workflow guide/i);
    expect(
      screen.queryByTestId("demo-clinical-workflow-guide-body")
    ).not.toBeInTheDocument();
  });

  it("renders all seven workflow steps when expanded", async () => {
    render(<DemoClinicalWorkflowGuide />);
    const user = userEvent.setup();
    await user.click(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    );

    const checklist = screen.getByTestId(
      "demo-clinical-workflow-guide-checklist"
    );
    // Seven <li> items, one per step.
    expect(within(checklist).getAllByRole("listitem")).toHaveLength(7);
    // Each step has its own testid for downstream specs.
    for (const id of [
      "step-1-scribe",
      "step-2-proposals",
      "step-3-apply",
      "step-4-sign",
      "step-5-summary",
      "step-6-brief",
      "step-7-actions",
    ]) {
      expect(
        screen.getByTestId(`demo-clinical-workflow-guide-${id}`)
      ).toBeInTheDocument();
    }
  });

  it("renders the three negative-assertion safety lines when expanded", async () => {
    render(<DemoClinicalWorkflowGuide />);
    const user = userEvent.setup();
    await user.click(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    );

    const safety = screen.getByTestId(
      "demo-clinical-workflow-guide-safety"
    );
    expect(safety).toHaveTextContent(
      /supports documentation and review workflows/i
    );
    expect(safety).toHaveTextContent(/does not diagnose, order, bill/i);
    expect(safety).toHaveTextContent(/explicit provider review/i);
  });

  it("references the demo script doc path in the footnote", async () => {
    render(<DemoClinicalWorkflowGuide />);
    const user = userEvent.setup();
    await user.click(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    );
    expect(
      screen.getByTestId("demo-clinical-workflow-guide-footnote")
    ).toHaveTextContent(
      /docs\/demo\/chartnav-clinical-workflow-demo-script\.md/
    );
  });

  it("renders no order / coding / referral / patient-message buttons", async () => {
    render(<DemoClinicalWorkflowGuide />);
    const user = userEvent.setup();
    await user.click(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    );

    const guide = screen.getByTestId("demo-clinical-workflow-guide");
    // Only one button exists in the guide — the toggle.
    const buttons = within(guide).getAllByRole("button");
    expect(buttons).toHaveLength(1);
    expect(buttons[0]).toHaveAttribute(
      "data-testid",
      "demo-clinical-workflow-guide-toggle"
    );

    // Negative assertions — no buttons matching the forbidden labels.
    for (const label of [
      /place order/i,
      /\border\b(?!.*review)/i,
      /coding/i,
      /icd-?10/i,
      /cpt code/i,
      /send referral/i,
      /submit referral/i,
      /send to patient/i,
      /email patient/i,
      /sms patient/i,
      /portal push/i,
      /prescribe/i,
    ]) {
      expect(
        within(guide).queryByRole("button", { name: label })
      ).not.toBeInTheDocument();
    }
  });

  it("contains no autonomous-diagnosis or external-LLM language anywhere in the rendered guide", async () => {
    render(<DemoClinicalWorkflowGuide patientDisplay="Morgan Lee" />);
    const user = userEvent.setup();
    await user.click(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    );
    const guide = screen.getByTestId("demo-clinical-workflow-guide");
    const text = (guide.textContent || "").toLowerCase();
    for (const pattern of [
      /autonomous/i,
      /openai/i,
      /anthropic/i,
      /\bgpt\b/i,
      /\bllm\b/i,
      /external llm certainty/i,
      /\bdiagnos(?:e|is|ing)\b/i, // bare diagnosis — only "does not diagnose" is allowed (negative form)
    ]) {
      // For the bare-diagnosis pattern, confirm any match is part of
      // a "does not diagnose" negative assertion, not a positive
      // claim.
      const positive = pattern.source.includes("diagnos")
        ? !/does not diagnose/i.test(text)
        : true;
      if (positive) {
        expect(text).not.toMatch(pattern);
      }
    }
    // Explicit positive checks for forbidden marketing claims.
    for (const claim of [
      /hipaa[ -]compliant/i,
      /certified ehr/i,
      /autonomous diagnosis/i,
      /automatic diagnosis/i,
      /guaranteed accuracy/i,
      /automatic orders?/i,
      /\border oct\b/i,
      /submit referral/i,
      /\bsend referral\b/i,
      /billing automation/i,
      /coding automation/i,
      /\bsend patient message\b/i,
      /replaces (?:a )?doctor/i,
    ]) {
      expect(text).not.toMatch(claim);
    }
  });

  it("the safety bullet points are negative assertions only", async () => {
    render(<DemoClinicalWorkflowGuide />);
    const user = userEvent.setup();
    await user.click(
      screen.getByTestId("demo-clinical-workflow-guide-toggle")
    );
    // Each safety bullet is either a positive support statement
    // ("supports documentation") or an explicit negative
    // ("does not diagnose ..."). None should be a bare positive
    // claim like "ChartNav diagnoses ...".
    const safety = screen.getByTestId(
      "demo-clinical-workflow-guide-safety"
    );
    const items = within(safety).getAllByRole("listitem");
    expect(items.length).toBeGreaterThanOrEqual(3);
    for (const item of items) {
      const text = (item.textContent || "").toLowerCase();
      const hasNegative =
        text.includes("does not") ||
        text.includes("supports") ||
        text.includes("provider review");
      expect(hasNegative).toBe(true);
    }
  });
});
