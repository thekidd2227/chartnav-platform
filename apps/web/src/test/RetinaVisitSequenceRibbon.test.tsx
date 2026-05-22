/**
 * Phase 71 — RetinaVisitSequenceRibbon tests.
 *
 * The ribbon is the buyer-visible 5-step explanation of the
 * retina visit path. It is navigational (clicking a step jumps
 * to the workspace tab where that stage of the visit happens)
 * and role-aware (the Signed Lock step shows an explicit
 * "Requires clinician or admin" affordance for roles that
 * cannot sign).
 */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Me, Role } from "../api";
import {
  RETINA_VISIT_STEPS,
  RetinaVisitSequenceRibbon,
} from "../RetinaVisitSequenceRibbon";

function makeMe(role: Role): Me {
  return {
    user_id: 1,
    email: `${role}@chartnav.local`,
    full_name: `Test ${role}`,
    role,
    organization_id: 1,
  };
}

describe("Phase 71 — RetinaVisitSequenceRibbon", () => {
  it("renders the section landmark with the safety-frame caption", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("clinician")}
        onJumpToTab={vi.fn()}
      />
    );
    const ribbon = screen.getByTestId("retina-visit-ribbon");
    expect(ribbon).toBeInTheDocument();
    expect(screen.getByTestId("retina-visit-ribbon-title")).toHaveTextContent(
      /Retina visit sequence/i
    );
    const caption = screen.getByTestId("retina-visit-ribbon-caption");
    expect(caption).toHaveTextContent(/Fake-data demo/i);
    expect(caption).toHaveTextContent(/Provider-reviewed/i);
    expect(caption).toHaveTextContent(/the clinician signs/i);
    expect(caption).toHaveTextContent(/Not a certified EHR/i);
    expect(caption).toHaveTextContent(/Does not diagnose/i);
  });

  it("renders exactly 5 steps in the documented order", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("clinician")}
        onJumpToTab={vi.fn()}
      />
    );
    const steps = within(
      screen.getByTestId("retina-visit-ribbon-steps")
    ).getAllByRole("listitem");
    expect(steps).toHaveLength(5);
    const ids = steps.map((s) => s.getAttribute("data-testid"));
    expect(ids).toEqual([
      "retina-visit-step-intake",
      "retina-visit-step-fundus-drawing",
      "retina-visit-step-visit-draft",
      "retina-visit-step-provider-review",
      "retina-visit-step-signed-lock",
    ]);
  });

  it("each step button carries an accessible label that names the destination tab", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("clinician")}
        onJumpToTab={vi.fn()}
      />
    );
    for (const step of RETINA_VISIT_STEPS) {
      const btn = screen.getByTestId(`retina-visit-step-btn-${step.id}`);
      const label = btn.getAttribute("aria-label") || "";
      expect(label).toMatch(new RegExp(step.label));
      expect(label).toMatch(new RegExp(`Opens ${step.tab} tab`));
    }
  });

  it("clicking a step button calls onJumpToTab with the step's tab id", async () => {
    const user = userEvent.setup();
    const onJump = vi.fn();
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("clinician")}
        onJumpToTab={onJump}
      />
    );
    await user.click(screen.getByTestId("retina-visit-step-btn-intake"));
    expect(onJump).toHaveBeenLastCalledWith("clinical");
    await user.click(
      screen.getByTestId("retina-visit-step-btn-fundus-drawing")
    );
    expect(onJump).toHaveBeenLastCalledWith("imaging");
    await user.click(screen.getByTestId("retina-visit-step-btn-visit-draft"));
    expect(onJump).toHaveBeenLastCalledWith("documentation");
    await user.click(
      screen.getByTestId("retina-visit-step-btn-provider-review")
    );
    expect(onJump).toHaveBeenLastCalledWith("documentation");
    await user.click(screen.getByTestId("retina-visit-step-btn-signed-lock"));
    expect(onJump).toHaveBeenLastCalledWith("documentation");
  });

  it("clinician role: signed-lock step is NOT marked locked and the footnote names signing", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("clinician")}
        onJumpToTab={vi.fn()}
      />
    );
    const signStep = screen.getByTestId("retina-visit-step-signed-lock");
    expect(signStep.getAttribute("data-locked")).toBe("false");
    expect(
      screen.queryByTestId("retina-visit-step-role-lock-signed-lock")
    ).toBeNull();
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/role that can review and sign/i);
  });

  it("admin role: signed-lock step is NOT marked locked", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("admin")}
        onJumpToTab={vi.fn()}
      />
    );
    expect(
      screen.getByTestId("retina-visit-step-signed-lock").getAttribute(
        "data-locked"
      )
    ).toBe("false");
    expect(
      screen.queryByTestId("retina-visit-step-role-lock-signed-lock")
    ).toBeNull();
  });

  it("technician role: signed-lock step is marked locked and explicit", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("technician")}
        onJumpToTab={vi.fn()}
      />
    );
    const signStep = screen.getByTestId("retina-visit-step-signed-lock");
    expect(signStep.getAttribute("data-locked")).toBe("true");
    expect(
      screen.getByTestId("retina-visit-step-role-lock-signed-lock")
    ).toHaveTextContent(/Requires clinician or admin/i);
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/Technician role/i);
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/cannot sign/i);
  });

  it("reviewer role: signed-lock step is marked locked and read-only explanation appears", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("reviewer")}
        onJumpToTab={vi.fn()}
      />
    );
    expect(
      screen.getByTestId("retina-visit-step-signed-lock").getAttribute(
        "data-locked"
      )
    ).toBe("true");
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/Reviewer role/i);
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/read-only/i);
  });

  it("front_desk role: signed-lock step is marked locked and front-desk scope is explicit", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("front_desk")}
        onJumpToTab={vi.fn()}
      />
    );
    expect(
      screen.getByTestId("retina-visit-step-signed-lock").getAttribute(
        "data-locked"
      )
    ).toBe("true");
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/Front-desk role/i);
    expect(
      screen.getByTestId("retina-visit-ribbon-footnote")
    ).toHaveTextContent(/scheduling/i);
  });

  it("the ribbon never claims diagnosis / autonomous documentation / image interpretation / EHR replacement / billing / coding", () => {
    render(
      <RetinaVisitSequenceRibbon
        me={makeMe("clinician")}
        onJumpToTab={vi.fn()}
      />
    );
    const ribbon = screen.getByTestId("retina-visit-ribbon");
    const text = (ribbon.textContent || "").toLowerCase();
    // Forbidden phrasings — if any appear, they must appear inside
    // a negative-context disclaimer ("does not diagnose"). The
    // ribbon's caption embeds those disclaimers explicitly, so the
    // negative-context check is enough.
    expect(text).not.toMatch(/auto-?sign/);
    expect(text).not.toMatch(/auto-?document/);
    expect(text).not.toMatch(/autonomous documentation/);
    expect(text).not.toMatch(/replaces your ehr/);
    expect(text).not.toMatch(/interprets fundus/);
    expect(text).not.toMatch(/submit claim/);
    expect(text).not.toMatch(/place order(?!s,)/); // "place orders," is allowed inside the negative-context disclaimer
  });
});
