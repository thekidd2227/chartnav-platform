/**
 * Phase 15 — GuidedDemoMode component tests.
 *
 * Asserts the sticky in-workspace orchestrator renders only when
 * demo mode is enabled (URL `?demo=1` or `localStorage.chartnav.demoMode`),
 * the 8-step stepper advances / regresses / resets correctly, the
 * negative-assertion safety bullets always render when enabled,
 * and no autonomous-diagnosis / external-LLM / order / coding /
 * referral / patient-message language appears in the rendered DOM.
 */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEMO_STEPS, GuidedDemoMode } from "../GuidedDemoMode";

function setLocation(search: string) {
  // jsdom location.search is read-only; rebuild a URL to update.
  const url = new URL(window.location.href);
  url.search = search;
  window.history.replaceState({}, "", url.toString());
}

beforeEach(() => {
  // Reset URL and localStorage between tests so each test starts
  // from a clean state.
  setLocation("");
  window.localStorage.removeItem("chartnav.demoMode");
  window.localStorage.removeItem("chartnav.demoStep");
});

afterEach(() => {
  setLocation("");
  window.localStorage.removeItem("chartnav.demoMode");
  window.localStorage.removeItem("chartnav.demoStep");
});

describe("GuidedDemoMode — gating", () => {
  it("renders nothing by default (no ?demo=1, no localStorage flag)", () => {
    render(<GuidedDemoMode patientDisplay="Morgan Lee" />);
    expect(
      screen.queryByTestId("guided-demo-mode")
    ).not.toBeInTheDocument();
  });

  it("renders when URL has ?demo=1", () => {
    setLocation("?demo=1");
    render(<GuidedDemoMode patientDisplay="Morgan Lee" />);
    expect(screen.getByTestId("guided-demo-mode")).toBeInTheDocument();
  });

  it("renders when localStorage chartnav.demoMode === '1'", () => {
    window.localStorage.setItem("chartnav.demoMode", "1");
    render(<GuidedDemoMode />);
    expect(screen.getByTestId("guided-demo-mode")).toBeInTheDocument();
  });

  it("does not render when localStorage chartnav.demoMode is some other value", () => {
    window.localStorage.setItem("chartnav.demoMode", "0");
    render(<GuidedDemoMode />);
    expect(
      screen.queryByTestId("guided-demo-mode")
    ).not.toBeInTheDocument();
  });
});

describe("GuidedDemoMode — stepper structure", () => {
  beforeEach(() => setLocation("?demo=1"));

  it("ships exactly 8 deterministic steps", () => {
    expect(DEMO_STEPS).toHaveLength(8);
    expect(DEMO_STEPS.map((s) => s.id)).toEqual([
      "intake",
      "pre-visit-brief",
      "visit-begins",
      "scribe",
      "retinal-proposal",
      "action-queue",
      "patient-summary",
      "completed",
    ]);
  });

  it("renders the DEMO MODE badge with the fake-data-only label", () => {
    render(<GuidedDemoMode />);
    const badge = screen.getByTestId("guided-demo-mode-badge");
    expect(badge).toHaveTextContent(/DEMO MODE/i);
    expect(badge).toHaveTextContent(/fake data only/i);
  });

  it("renders a step counter and the 8-item progress list", () => {
    render(<GuidedDemoMode />);
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 1 of 8/);
    const progress = screen.getByTestId("guided-demo-mode-progress");
    expect(within(progress).getAllByRole("listitem")).toHaveLength(8);
    for (const s of DEMO_STEPS) {
      expect(
        screen.getByTestId(`guided-demo-mode-step-${s.id}`)
      ).toBeInTheDocument();
    }
  });

  it("renders the current step's title, body, and presenter cue", () => {
    render(<GuidedDemoMode />);
    expect(
      screen.getByTestId("guided-demo-mode-current-title")
    ).toHaveTextContent(/Intake arrives/i);
    expect(
      screen.getByTestId("guided-demo-mode-current-body")
    ).toHaveTextContent(/encounter row is open/i);
    expect(
      screen.getByTestId("guided-demo-mode-current-cue")
    ).toHaveTextContent(/provider-reviewed/i);
  });

  it("inlines the patientDisplay into the lead when provided", () => {
    render(<GuidedDemoMode patientDisplay="Morgan Lee" />);
    expect(
      screen.getByTestId("guided-demo-mode-lead")
    ).toHaveTextContent(/for Morgan Lee/);
  });

  it("renders the three negative-assertion safety bullets", () => {
    render(<GuidedDemoMode />);
    const safety = screen.getByTestId("guided-demo-mode-safety");
    expect(safety).toHaveTextContent(
      /supports documentation and review workflows/i
    );
    expect(safety).toHaveTextContent(/does not diagnose, order, bill/i);
    expect(safety).toHaveTextContent(/explicit provider review/i);
  });
});

describe("GuidedDemoMode — controls", () => {
  beforeEach(() => setLocation("?demo=1"));

  it("Previous is disabled on step 1 and Next is enabled", () => {
    render(<GuidedDemoMode />);
    expect(
      screen.getByTestId("guided-demo-mode-back")
    ).toBeDisabled();
    expect(
      screen.getByTestId("guided-demo-mode-next")
    ).not.toBeDisabled();
  });

  it("Next advances the step counter and moves the progress 'current' marker", async () => {
    render(<GuidedDemoMode />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 2 of 8/);
    expect(
      screen.getByTestId("guided-demo-mode-step-pre-visit-brief")
    ).toHaveAttribute("data-step-status", "current");
    expect(
      screen.getByTestId("guided-demo-mode-step-intake")
    ).toHaveAttribute("data-step-status", "complete");
  });

  it("clicking Next 7 times disables Next on the last step", async () => {
    render(<GuidedDemoMode />);
    const user = userEvent.setup();
    const next = screen.getByTestId("guided-demo-mode-next");
    for (let i = 0; i < 7; i++) await user.click(next);
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 8 of 8/);
    expect(next).toBeDisabled();
  });

  it("Reset returns to step 1 from any later step", async () => {
    render(<GuidedDemoMode />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 4 of 8/);
    await user.click(screen.getByTestId("guided-demo-mode-reset"));
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 1 of 8/);
    expect(
      screen.getByTestId("guided-demo-mode-step-intake")
    ).toHaveAttribute("data-step-status", "current");
  });

  it("Previous moves backward and re-enables itself only when not on step 1", async () => {
    render(<GuidedDemoMode />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    expect(
      screen.getByTestId("guided-demo-mode-back")
    ).not.toBeDisabled();
    await user.click(screen.getByTestId("guided-demo-mode-back"));
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 1 of 8/);
    expect(
      screen.getByTestId("guided-demo-mode-back")
    ).toBeDisabled();
  });

  it("step pointer persists across remounts via localStorage", async () => {
    const { unmount } = render(<GuidedDemoMode />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    await user.click(screen.getByTestId("guided-demo-mode-next"));
    expect(window.localStorage.getItem("chartnav.demoStep")).toBe("2");
    unmount();
    render(<GuidedDemoMode />);
    expect(
      screen.getByTestId("guided-demo-mode-step-counter")
    ).toHaveTextContent(/Step 3 of 8/);
  });
});

describe("GuidedDemoMode — safety language", () => {
  beforeEach(() => setLocation("?demo=1"));

  it("does not surface autonomous-diagnosis or external-LLM language anywhere", () => {
    render(<GuidedDemoMode patientDisplay="Morgan Lee" />);
    const root = screen.getByTestId("guided-demo-mode");
    const text = (root.textContent || "").toLowerCase();
    for (const pattern of [
      /autonomous/,
      /openai/,
      /anthropic/,
      /\bgpt\b/,
      /\bllm\b/,
      /external llm certainty/,
      /hipaa[ -]compliant/,
      /certified ehr/,
      /automatic diagnosis/,
      /\bguaranteed accuracy\b/,
      /\bautomatic orders?\b/,
      /\border oct\b/,
      /\bsubmit referral\b/,
      /\bsend referral\b/,
      /\bbilling automation\b/,
      /\bcoding automation\b/,
      /\bsend patient message\b/,
      /\breplaces (?:a )?doctor\b/,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it("renders no order / coding / referral / patient-message buttons", () => {
    render(<GuidedDemoMode />);
    const root = screen.getByTestId("guided-demo-mode");
    for (const label of [
      /place order/i,
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
        within(root).queryByRole("button", { name: label })
      ).not.toBeInTheDocument();
    }
  });

  it("the only buttons in the orchestrator are Previous, Next, and Reset", () => {
    render(<GuidedDemoMode />);
    const root = screen.getByTestId("guided-demo-mode");
    const buttons = within(root).getAllByRole("button");
    expect(buttons).toHaveLength(3);
    const names = buttons.map((b) => b.textContent?.trim());
    expect(names).toContain("Previous step");
    expect(names).toContain("Next step");
    expect(names).toContain("Reset demo");
  });
});
