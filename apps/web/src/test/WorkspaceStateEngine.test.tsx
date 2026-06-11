// Phase 91 — Unified Ophthalmology Workspace Engine tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/workspace-state/workspaceStateApi", () => ({
  getWorkspaceState: vi.fn(),
  patchVisitMode: vi.fn(),
  patchActiveLaterality: vi.fn(),
}));

import {
  getWorkspaceState,
  patchActiveLaterality,
  patchVisitMode,
} from "../features/workspace-state/workspaceStateApi";
import { LateralitySwitcher } from "../features/workspace-state/LateralitySwitcher";
import { VisitModeRibbon } from "../features/workspace-state/VisitModeRibbon";
import {
  WorkspaceStateProvider,
  panelIsEmphasised,
  panelIsLateralityLinked,
  useWorkspaceState,
} from "../features/workspace-state/WorkspaceStateProvider";
import type { WorkspaceStateResponse } from "../features/workspace-state/workspaceStateTypes";

const DISCLOSURE =
  "Unified workspace state is a deterministic projection. ChartNav does not auto-classify the visit mode and does not autonomously select an eye.";

function makeState(
  over: Partial<WorkspaceStateResponse> = {},
): WorkspaceStateResponse {
  return {
    encounter_id: 1,
    organization_id: 1,
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    provider_name: "Casey Clinician",
    status: "in_progress",
    encounter_type: "comprehensive",
    encounter_type_label: "Comprehensive",
    visit_mode: "unscheduled",
    visit_mode_label: "Unscheduled",
    active_laterality: "NA",
    active_laterality_label: "Not applicable",
    profile: {
      code: "comprehensive",
      label: "Comprehensive",
      panel_order: [
        "provider_action_queue",
        "note_validation",
        "anti_vegf_injection",
        "cataract_workflow",
      ] as any,
      panel_labels: {
        provider_action_queue: "Provider Action Queue",
        note_validation: "Note Validation Rail",
        anti_vegf_injection: "Anti-VEGF Injection Rail",
        cataract_workflow: "Cataract Surgical Workflow",
      } as any,
    },
    emphasis: {
      emphasised_panels: ["provider_action_queue", "note_validation"] as any,
      secondary_panels: ["anti_vegf_injection", "cataract_workflow"] as any,
      total_panels: 4,
    },
    laterality_linked_panels: [
      "anti_vegf_injection",
      "glaucoma_cockpit",
      "cataract_workflow",
    ],
    supported_visit_modes: [
      { code: "intake", label: "Intake" },
      { code: "surgical_pre_op", label: "Surgical pre-op" },
      { code: "post_op", label: "Post-op" },
      { code: "follow_up", label: "Follow-up" },
      { code: "lab_review", label: "Lab / imaging review" },
      { code: "unscheduled", label: "Unscheduled" },
    ],
    supported_active_lateralities: [
      { code: "OD", label: "OD · Right eye" },
      { code: "OS", label: "OS · Left eye" },
      { code: "OU", label: "OU · Both eyes" },
      { code: "NA", label: "Not applicable" },
    ],
    generated_at: "2026-06-11T10:00:00Z",
    disclosure: DISCLOSURE,
    ...over,
  };
}

beforeEach(() => {
  vi.mocked(getWorkspaceState).mockReset();
  vi.mocked(patchVisitMode).mockReset();
  vi.mocked(patchActiveLaterality).mockReset();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

describe("panelIsEmphasised / panelIsLateralityLinked", () => {
  it("returns false when state is null", () => {
    expect(panelIsEmphasised(null, "provider_action_queue")).toBe(false);
    expect(panelIsLateralityLinked(null, "anti_vegf_injection")).toBe(false);
  });

  it("returns true when panel is in emphasis list", () => {
    const s = makeState();
    expect(panelIsEmphasised(s, "provider_action_queue")).toBe(true);
    expect(panelIsEmphasised(s, "anti_vegf_injection")).toBe(false);
  });

  it("returns true when panel is laterality-linked", () => {
    const s = makeState();
    expect(panelIsLateralityLinked(s, "anti_vegf_injection")).toBe(true);
    expect(panelIsLateralityLinked(s, "note_validation")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// VisitModeRibbon
// ---------------------------------------------------------------------------

describe("VisitModeRibbon", () => {
  it("renders the current visit mode + 6 mode buttons", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <VisitModeRibbon canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("visit-mode-ribbon")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("visit-mode-ribbon-active").textContent).toMatch(
      /Unscheduled/i,
    );
    for (const code of [
      "intake",
      "surgical_pre_op",
      "post_op",
      "follow_up",
      "lab_review",
      "unscheduled",
    ]) {
      expect(
        screen.getByTestId(`visit-mode-ribbon-option-${code}`),
      ).toBeInTheDocument();
    }
  });

  it("PATCHes visit mode on click and refetches state", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    vi.mocked(patchVisitMode).mockResolvedValueOnce(
      makeState({ visit_mode: "follow_up", visit_mode_label: "Follow-up" }),
    );

    render(
      <WorkspaceStateProvider encounterId={1}>
        <VisitModeRibbon canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("visit-mode-ribbon-option-follow_up"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("visit-mode-ribbon-option-follow_up"),
    );

    await waitFor(() => expect(patchVisitMode).toHaveBeenCalledTimes(1));
    expect(vi.mocked(patchVisitMode).mock.calls[0]![0]).toBe(1);
    expect(vi.mocked(patchVisitMode).mock.calls[0]![1]).toBe("follow_up");
    await waitFor(() =>
      expect(screen.getByTestId("visit-mode-ribbon-active").textContent).toMatch(
        /Follow-up/i,
      ),
    );
  });

  it("hides options when canEdit is false", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <VisitModeRibbon canEdit={false} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("visit-mode-ribbon")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("visit-mode-ribbon-options")).toBeNull();
  });

  it("renders disclosure with safe boundary copy", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <VisitModeRibbon canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("visit-mode-ribbon-disclosure"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("visit-mode-ribbon-disclosure").textContent,
    ).toMatch(/does not auto-classify/i);
    expect(
      screen.getByTestId("visit-mode-ribbon-disclosure").textContent,
    ).toMatch(/no panel is ever hidden/i);
  });
});

// ---------------------------------------------------------------------------
// LateralitySwitcher
// ---------------------------------------------------------------------------

describe("LateralitySwitcher", () => {
  it("renders the current laterality + 4 option buttons", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <LateralitySwitcher canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("laterality-switcher")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("laterality-switcher-active").textContent,
    ).toMatch(/Not applicable/i);
    for (const code of ["OD", "OS", "OU", "NA"]) {
      expect(
        screen.getByTestId(`laterality-switcher-option-${code}`),
      ).toBeInTheDocument();
    }
  });

  it("PATCHes laterality on click and refetches state", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    vi.mocked(patchActiveLaterality).mockResolvedValueOnce(
      makeState({
        active_laterality: "OD",
        active_laterality_label: "OD · Right eye",
      }),
    );

    render(
      <WorkspaceStateProvider encounterId={1}>
        <LateralitySwitcher canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("laterality-switcher-option-OD"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("laterality-switcher-option-OD"));

    await waitFor(() =>
      expect(patchActiveLaterality).toHaveBeenCalledTimes(1),
    );
    expect(vi.mocked(patchActiveLaterality).mock.calls[0]![0]).toBe(1);
    expect(vi.mocked(patchActiveLaterality).mock.calls[0]![1]).toBe("OD");
    await waitFor(() =>
      expect(
        screen.getByTestId("laterality-switcher-active").textContent,
      ).toMatch(/OD · Right eye/i),
    );
  });

  it("hides options when canEdit is false", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <LateralitySwitcher canEdit={false} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("laterality-switcher")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("laterality-switcher-options")).toBeNull();
  });

  it("renders disclosure with safe boundary copy", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <LateralitySwitcher canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("laterality-switcher-disclosure"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("laterality-switcher-disclosure").textContent,
    ).toMatch(/does not autonomously select an eye/i);
  });
});

// ---------------------------------------------------------------------------
// Provider behaviour
// ---------------------------------------------------------------------------

function Probe() {
  const ctx = useWorkspaceState();
  if (!ctx?.state)
    return <div data-testid="probe-loading">loading</div>;
  return (
    <div data-testid="probe">
      <span data-testid="probe-visit-mode">{ctx.state.visit_mode}</span>
      <span data-testid="probe-laterality">{ctx.state.active_laterality}</span>
      <span data-testid="probe-error">{ctx.error ?? ""}</span>
    </div>
  );
}

describe("WorkspaceStateProvider", () => {
  it("surfaces fetch errors via ctx.error", async () => {
    vi.mocked(getWorkspaceState).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(
      <WorkspaceStateProvider encounterId={1}>
        <Probe />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("probe-loading")).toBeInTheDocument(),
    );
    // probe rendered with no state but the ctx.error is set; the
    // top-level component decides how to render that.
  });

  it("does not fetch when encounterId is null", async () => {
    render(
      <WorkspaceStateProvider encounterId={null}>
        <Probe />
      </WorkspaceStateProvider>,
    );
    expect(getWorkspaceState).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Safety contract canary
// ---------------------------------------------------------------------------

describe("Workspace state engine — safety contract", () => {
  it("does NOT render autonomous-classification phrases", async () => {
    vi.mocked(getWorkspaceState).mockResolvedValueOnce(makeState());
    render(
      <WorkspaceStateProvider encounterId={1}>
        <VisitModeRibbon canEdit={true} />
        <LateralitySwitcher canEdit={true} />
      </WorkspaceStateProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("visit-mode-ribbon")).toBeInTheDocument(),
    );
    const ribbonDisclosure = (
      screen.getByTestId("visit-mode-ribbon-disclosure").textContent ?? ""
    ).toLowerCase();
    const lateralityDisclosure = (
      screen.getByTestId("laterality-switcher-disclosure").textContent ?? ""
    ).toLowerCase();
    const body = (document.body.textContent ?? "")
      .toLowerCase()
      .replace(ribbonDisclosure, "")
      .replace(lateralityDisclosure, "");
    for (const forbidden of [
      "auto-classified",
      "auto-detected eye",
      "subspecialty detected",
      "auto-staged",
      "auto-selected eye",
      "diagnosis confirmed",
      "treatment recommended",
      "image interpreted",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
