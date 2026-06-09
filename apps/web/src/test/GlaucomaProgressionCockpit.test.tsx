// Phase 79 — Glaucoma Progression Cockpit tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/glaucoma/glaucomaApi", () => ({
  getGlaucomaSummary: vi.fn(),
}));

import { getGlaucomaSummary } from "../features/glaucoma/glaucomaApi";
import { GlaucomaProgressionCockpit } from "../features/glaucoma/GlaucomaProgressionCockpit";
import type {
  GlaucomaEye,
  GlaucomaEyeLane,
  GlaucomaModalitySummary,
  GlaucomaSummary,
} from "../features/glaucoma/glaucomaTypes";

function emptyModality(): GlaucomaModalitySummary {
  return {
    count: 0,
    latest_id: null,
    latest_modality: null,
    latest_status: null,
    latest_captured_at: null,
    latest_reviewed_at: null,
    latest_reviewed_by_user_id: null,
    insufficient_data: true,
  };
}

function reviewedModality(): GlaucomaModalitySummary {
  return {
    count: 2,
    latest_id: 7,
    latest_modality: "visual_field_24_2",
    latest_status: "reviewed",
    latest_captured_at: "2026-05-19T06:30:00Z",
    latest_reviewed_at: "2026-05-19T07:00:00Z",
    latest_reviewed_by_user_id: 3,
    insufficient_data: false,
  };
}

function readyForReviewModality(): GlaucomaModalitySummary {
  return {
    count: 1,
    latest_id: 11,
    latest_modality: "oct_rnfl",
    latest_status: "ready_for_review",
    latest_captured_at: "2026-05-19T06:30:00Z",
    latest_reviewed_at: null,
    latest_reviewed_by_user_id: null,
    insufficient_data: false,
  };
}

function emptyLane(eye: GlaucomaEye): GlaucomaEyeLane {
  return {
    eye,
    iop_history: [],
    latest_iop: null,
    iop_count: 0,
    visual_field: emptyModality(),
    oct_rnfl: emptyModality(),
    oct_macula: emptyModality(),
    data_completeness: {
      has_iop: false,
      has_visual_field: false,
      has_oct_rnfl: false,
      score_numerator: 0,
      score_denominator: 3,
    },
    insufficient_data: true,
  };
}

function richLane(eye: GlaucomaEye): GlaucomaEyeLane {
  return {
    eye,
    iop_history: [
      {
        vitals_workup_id: 3,
        encounter_id: 1,
        eye,
        value: 18,
        method: "applanation",
        status: "signed",
        signed: true,
        reviewed_at: "2026-05-19T06:50:00Z",
        signed_at: "2026-05-19T07:00:00Z",
        recorded_at: "2026-05-19T06:30:00Z",
      },
      {
        vitals_workup_id: 2,
        encounter_id: 1,
        eye,
        value: 22,
        method: "applanation",
        status: "signed",
        signed: true,
        reviewed_at: "2026-04-12T06:50:00Z",
        signed_at: "2026-04-12T07:00:00Z",
        recorded_at: "2026-04-12T06:30:00Z",
      },
    ],
    latest_iop: {
      vitals_workup_id: 3,
      encounter_id: 1,
      eye,
      value: 18,
      method: "applanation",
      status: "signed",
      signed: true,
      reviewed_at: "2026-05-19T06:50:00Z",
      signed_at: "2026-05-19T07:00:00Z",
      recorded_at: "2026-05-19T06:30:00Z",
    },
    iop_count: 2,
    visual_field: reviewedModality(),
    oct_rnfl: readyForReviewModality(),
    oct_macula: emptyModality(),
    data_completeness: {
      has_iop: true,
      has_visual_field: true,
      has_oct_rnfl: true,
      score_numerator: 3,
      score_denominator: 3,
    },
    insufficient_data: false,
  };
}

function emptySummary(): GlaucomaSummary {
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    generated_at: "2026-06-09T10:00:00Z",
    demo_mode: true,
    bilateral_data: false,
    od: emptyLane("OD"),
    os: emptyLane("OS"),
    disclosure:
      "ChartNav surfaces what the provider's measurements show. ChartNav does not interpret IOP trends, visual fields, or OCT scans. It does not classify glaucoma progression. It does not recommend medication, laser, or surgery.",
  };
}

function richSummary(): GlaucomaSummary {
  return {
    ...emptySummary(),
    bilateral_data: true,
    od: richLane("OD"),
    os: richLane("OS"),
  };
}

beforeEach(() => {
  vi.mocked(getGlaucomaSummary).mockReset();
});

describe("GlaucomaProgressionCockpit — baseline", () => {
  it("renders header, banner, refresh button", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(emptySummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-progression-cockpit"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("glaucoma-banner").textContent).toMatch(
      /Provider-reviewed workflow intelligence/i,
    );
    expect(screen.getByTestId("glaucoma-refresh-btn")).toBeInTheDocument();
  });

  it("renders both eye lanes with long-form labels", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("glaucoma-eye-lane-OD")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("glaucoma-eye-lane-OD").textContent).toMatch(
      /OD · Right Eye/,
    );
    expect(screen.getByTestId("glaucoma-eye-lane-OS").textContent).toMatch(
      /OS · Left Eye/,
    );
  });
});

describe("GlaucomaProgressionCockpit — insufficient data", () => {
  it("shows OD/OS insufficient-data callouts when no data", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(emptySummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-insufficient"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("glaucoma-OD-insufficient").textContent).toMatch(
      /Insufficient data for OD/i,
    );
    expect(screen.getByTestId("glaucoma-OS-insufficient").textContent).toMatch(
      /Insufficient data for OS/i,
    );
    expect(screen.getByTestId("glaucoma-OD-iop-empty")).toBeInTheDocument();
    expect(screen.getByTestId("glaucoma-OS-iop-empty")).toBeInTheDocument();
  });

  it("renders 0/3 completeness pill when nothing present", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(emptySummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-completeness"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("glaucoma-OD-completeness").textContent,
    ).toMatch(/0 \/ 3/);
  });
});

describe("GlaucomaProgressionCockpit — rich data", () => {
  it("renders IOP latest value + trend list per eye", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-iop-latest-value"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("glaucoma-OD-iop-latest-value").textContent,
    ).toBe("18 mmHg");
    expect(
      screen.getByTestId("glaucoma-OD-iop-trend-list").textContent,
    ).toMatch(/18 → 22/);
  });

  it("renders visual_field 'Reviewed' green pill when reviewed_at present", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("glaucoma-OD-vf")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("glaucoma-OD-vf-tone").textContent).toMatch(
      /Reviewed/i,
    );
  });

  it("renders OCT RNFL 'Ready for review' amber pill", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-oct-rnfl"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("glaucoma-OD-oct-rnfl-tone").textContent,
    ).toMatch(/Ready for review/i);
  });

  it("renders OCT macula insufficient-data red pill when not present", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-oct-macula"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("glaucoma-OD-oct-macula-tone").textContent,
    ).toMatch(/Insufficient data/i);
  });

  it("renders 3/3 completeness pill on rich data", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-completeness"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("glaucoma-OD-completeness").textContent,
    ).toMatch(/3 \/ 3/);
  });

  it("renders bilateral-data flag and disclosure", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("glaucoma-disclosure")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("glaucoma-bilateral-flag").textContent,
    ).toMatch(/Bilateral data/i);
    const disc = screen.getByTestId("glaucoma-disclosure");
    expect(disc.textContent).toMatch(/does not interpret/i);
    expect(disc.textContent).toMatch(/does not classify glaucoma progression/i);
  });
});

describe("GlaucomaProgressionCockpit — interaction + safety", () => {
  it("refresh button refetches summary", async () => {
    vi.mocked(getGlaucomaSummary)
      .mockResolvedValueOnce(emptySummary())
      .mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-insufficient"),
      ).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("glaucoma-refresh-btn"));
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-iop-latest-value"),
      ).toBeInTheDocument(),
    );
    expect(getGlaucomaSummary).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getGlaucomaSummary).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("glaucoma-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("glaucoma-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("does NOT render forbidden clinical/progression phrases", async () => {
    vi.mocked(getGlaucomaSummary).mockResolvedValueOnce(richSummary());
    render(<GlaucomaProgressionCockpit patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("glaucoma-OD-iop-latest-value"),
      ).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "stage iii",
      "stage iv",
      "rapid progression",
      "surgery recommended",
      "laser recommended",
      "order placed",
      "advanced glaucoma",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
