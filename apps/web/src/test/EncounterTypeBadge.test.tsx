// Phase 86 — Encounter Type Badge + WorkspaceProfileResolver tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/workspace-profile/workspaceProfileApi", () => ({
  getWorkspaceProfile: vi.fn(),
  patchWorkspaceProfile: vi.fn(),
}));

import {
  getWorkspaceProfile,
  patchWorkspaceProfile,
} from "../features/workspace-profile/workspaceProfileApi";
import { EncounterTypeBadge } from "../features/workspace-profile/EncounterTypeBadge";
import {
  panelDispositionFor,
  panelOrderIndex,
  useWorkspaceProfile,
} from "../features/workspace-profile/WorkspaceProfileResolver";
import type {
  EncounterType,
  WorkspaceProfileResponse,
} from "../features/workspace-profile/workspaceProfileTypes";

function makeProfile(typ: EncounterType): WorkspaceProfileResponse {
  const panels = (codes: string[]) =>
    codes.map((c) => ({ code: c as any, label: c }));
  const matrix = {
    retina: {
      prioritized: [
        "provider_action_queue",
        "note_validation",
        "anti_vegf_injection",
        "retina_visit_summary",
        "retina_visit_packet",
      ],
      visible: ["disease_staging", "medication_safety"],
      collapsed: ["glaucoma_cockpit", "cataract_workflow"],
    },
    glaucoma: {
      prioritized: [
        "provider_action_queue",
        "note_validation",
        "glaucoma_cockpit",
        "medication_safety",
      ],
      visible: ["disease_staging", "retina_visit_summary"],
      collapsed: [
        "anti_vegf_injection",
        "cataract_workflow",
        "retina_visit_packet",
      ],
    },
    cataract: {
      prioritized: [
        "provider_action_queue",
        "note_validation",
        "cataract_workflow",
        "medication_safety",
      ],
      visible: ["disease_staging", "retina_visit_summary"],
      collapsed: [
        "anti_vegf_injection",
        "glaucoma_cockpit",
        "retina_visit_packet",
      ],
    },
    comprehensive: {
      prioritized: [
        "provider_action_queue",
        "note_validation",
        "retina_visit_summary",
        "retina_visit_packet",
        "anti_vegf_injection",
        "glaucoma_cockpit",
        "cataract_workflow",
        "disease_staging",
        "medication_safety",
      ],
      visible: [],
      collapsed: [],
    },
  } as const;
  const m = matrix[typ];
  const order = [...m.prioritized, ...m.visible, ...m.collapsed];
  return {
    encounter_id: 1,
    organization_id: 1,
    patient_id: 1,
    patient_name: "Morgan Lee",
    patient_identifier: "PT-1001",
    provider_name: "Casey Clinician",
    status: "in_progress",
    encounter_type: typ,
    encounter_type_label: typ.charAt(0).toUpperCase() + typ.slice(1),
    profile: {
      code: typ,
      label: typ.charAt(0).toUpperCase() + typ.slice(1),
      prioritized_panels: panels(m.prioritized),
      visible_panels: panels(m.visible),
      collapsed_panels: panels(m.collapsed),
      panel_order: order as any,
    },
    supported_encounter_types: [
      { code: "retina", label: "Retina" },
      { code: "glaucoma", label: "Glaucoma" },
      { code: "cataract", label: "Cataract" },
      { code: "comprehensive", label: "Comprehensive" },
    ],
    generated_at: "2026-06-10T10:00:00Z",
    disclosure:
      "Workspace profile is a deterministic mapping. ChartNav does not autonomously classify the encounter and does not hide data.",
  };
}

beforeEach(() => {
  vi.mocked(getWorkspaceProfile).mockReset();
  vi.mocked(patchWorkspaceProfile).mockReset();
});

// ---------------------------------------------------------------------------
// Pure resolver helpers
// ---------------------------------------------------------------------------

describe("panelDispositionFor", () => {
  it("returns 'visible' when no profile is loaded", () => {
    expect(panelDispositionFor(null, "anti_vegf_injection")).toBe("visible");
  });

  it("classifies retina profile panels correctly", () => {
    const r = makeProfile("retina");
    expect(panelDispositionFor(r, "anti_vegf_injection")).toBe("prioritized");
    expect(panelDispositionFor(r, "disease_staging")).toBe("visible");
    expect(panelDispositionFor(r, "glaucoma_cockpit")).toBe("collapsed");
  });

  it("classifies glaucoma profile panels correctly", () => {
    const g = makeProfile("glaucoma");
    expect(panelDispositionFor(g, "glaucoma_cockpit")).toBe("prioritized");
    expect(panelDispositionFor(g, "anti_vegf_injection")).toBe("collapsed");
  });

  it("classifies cataract profile panels correctly", () => {
    const c = makeProfile("cataract");
    expect(panelDispositionFor(c, "cataract_workflow")).toBe("prioritized");
    expect(panelDispositionFor(c, "glaucoma_cockpit")).toBe("collapsed");
  });

  it("never collapses any panel in the comprehensive profile", () => {
    const c = makeProfile("comprehensive");
    for (const code of [
      "anti_vegf_injection",
      "glaucoma_cockpit",
      "cataract_workflow",
      "disease_staging",
      "medication_safety",
    ] as const) {
      expect(panelDispositionFor(c, code)).toBe("prioritized");
    }
  });
});

describe("panelOrderIndex", () => {
  it("returns 0 when profile is null (stable fallback)", () => {
    expect(panelOrderIndex(null, "anti_vegf_injection")).toBe(0);
  });

  it("ranks prioritized retina panels above collapsed ones", () => {
    const r = makeProfile("retina");
    const anti = panelOrderIndex(r, "anti_vegf_injection");
    const glauc = panelOrderIndex(r, "glaucoma_cockpit");
    expect(anti).toBeLessThan(glauc);
  });

  it("always ranks universal panels first", () => {
    for (const typ of ["retina", "glaucoma", "cataract", "comprehensive"] as const) {
      const p = makeProfile(typ);
      expect(panelOrderIndex(p, "provider_action_queue")).toBe(0);
      expect(panelOrderIndex(p, "note_validation")).toBe(1);
    }
  });
});

// ---------------------------------------------------------------------------
// EncounterTypeBadge
// ---------------------------------------------------------------------------

function TestHarness({
  encounterId = 1,
  canEdit = true,
}: {
  encounterId?: number | null;
  canEdit?: boolean;
}) {
  const state = useWorkspaceProfile(encounterId);
  return <EncounterTypeBadge state={state} canEdit={canEdit} />;
}

describe("EncounterTypeBadge", () => {
  it("renders the resolved chip + summary line", async () => {
    vi.mocked(getWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("retina"),
    );
    render(<TestHarness />);
    await waitFor(() =>
      expect(screen.getByTestId("encounter-type-badge")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("encounter-type-badge-chip").textContent).toMatch(
      /Retina workspace/i,
    );
    expect(
      screen.getByTestId("encounter-type-badge-summary").textContent,
    ).toMatch(/prioritized/i);
  });

  it("exposes the type select when canEdit is true", async () => {
    vi.mocked(getWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("comprehensive"),
    );
    render(<TestHarness canEdit={true} />);
    await waitFor(() =>
      expect(screen.getByTestId("encounter-type-select")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("encounter-type-option-retina"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("encounter-type-option-glaucoma"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("encounter-type-option-cataract"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("encounter-type-option-comprehensive"),
    ).toBeInTheDocument();
  });

  it("hides the type select when canEdit is false", async () => {
    vi.mocked(getWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("retina"),
    );
    render(<TestHarness canEdit={false} />);
    await waitFor(() =>
      expect(screen.getByTestId("encounter-type-badge")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("encounter-type-select")).toBeNull();
  });

  it("PATCHes a new encounter type when the select changes", async () => {
    vi.mocked(getWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("comprehensive"),
    );
    vi.mocked(patchWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("retina"),
    );

    render(<TestHarness />);
    await waitFor(() =>
      expect(screen.getByTestId("encounter-type-select")).toBeInTheDocument(),
    );

    await userEvent.selectOptions(
      screen.getByTestId("encounter-type-select"),
      "retina",
    );

    await waitFor(() =>
      expect(patchWorkspaceProfile).toHaveBeenCalledTimes(1),
    );
    expect(vi.mocked(patchWorkspaceProfile).mock.calls[0]![0]).toBe(1);
    expect(vi.mocked(patchWorkspaceProfile).mock.calls[0]![1]).toBe("retina");

    await waitFor(() =>
      expect(screen.getByTestId("encounter-type-badge-chip").textContent).toMatch(
        /Retina workspace/i,
      ),
    );
  });

  it("shows the error state on fetch failure", async () => {
    vi.mocked(getWorkspaceProfile).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<TestHarness />);
    await waitFor(() =>
      expect(
        screen.getByTestId("encounter-type-badge-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("encounter-type-badge-error").textContent,
    ).toMatch(/HTTP 503/);
  });

  it("renders disclosure with explicit safe-claims boundary language", async () => {
    vi.mocked(getWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("retina"),
    );
    render(<TestHarness />);
    await waitFor(() =>
      expect(
        screen.getByTestId("encounter-type-badge-disclosure"),
      ).toBeInTheDocument(),
    );
    const d = screen.getByTestId("encounter-type-badge-disclosure");
    expect(d.textContent).toMatch(/Provider-driven/i);
    expect(d.textContent).toMatch(/does not autonomously classify/i);
    expect(d.textContent).toMatch(/does not infer subspecialty/i);
    expect(d.textContent).toMatch(/does not hide data/i);
  });

  it("does NOT render forbidden autonomous-classification phrases", async () => {
    vi.mocked(getWorkspaceProfile).mockResolvedValueOnce(
      makeProfile("retina"),
    );
    render(<TestHarness />);
    await waitFor(() =>
      expect(screen.getByTestId("encounter-type-badge")).toBeInTheDocument(),
    );
    const d = screen.getByTestId("encounter-type-badge-disclosure");
    const disclosureText = (d.textContent ?? "").toLowerCase();
    const body = (document.body.textContent ?? "")
      .toLowerCase()
      .replace(disclosureText, "");
    for (const forbidden of [
      "auto-classified",
      "auto-routed",
      "subspecialty detected",
      "specialty inferred",
      "diagnosis confirmed",
      "treatment recommended",
      "image interpreted",
      "subspecialty assigned by chartnav",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
