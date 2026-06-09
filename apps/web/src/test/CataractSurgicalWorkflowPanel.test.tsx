// Phase 80 — Cataract Surgical Workflow Panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/cataract/cataractApi", () => ({
  getCataractWorkflowSummary: vi.fn(),
}));

import { getCataractWorkflowSummary } from "../features/cataract/cataractApi";
import { CataractSurgicalWorkflowPanel } from "../features/cataract/CataractSurgicalWorkflowPanel";
import type {
  CataractEye,
  CataractEyeLane,
  CataractWorkflowSummary,
} from "../features/cataract/cataractTypes";

function emptyLane(eye: CataractEye): CataractEyeLane {
  return {
    eye,
    record_count: 0,
    latest_record: null,
    preop_readiness: {
      has_planned_date: false,
      biometry_reviewed: false,
      topography_reviewed: false,
      consent_signed: false,
      score_numerator: 0,
      score_denominator: 4,
    },
    postop_cadence: {
      postop_day_1_status: "unknown",
      postop_week_1_status: "unknown",
      postop_month_1_status: "unknown",
      score_numerator: 0,
      score_denominator: 3,
    },
    complications_flag: false,
    insufficient_data: true,
  };
}

function richLane(eye: CataractEye): CataractEyeLane {
  return {
    eye,
    record_count: 1,
    latest_record: {
      id: 1,
      encounter_id: 1,
      surgery_eye: eye,
      planned_surgery_date: "2026-07-01",
      biometry_study_id: 5,
      biometry_reviewed: true,
      topography_reviewed: true,
      consent_status: "signed",
      postop_day_1_status: "completed",
      postop_week_1_status: "scheduled",
      postop_month_1_status: "unknown",
      complications_flag: false,
      created_at: "2026-06-09T10:00:00Z",
      updated_at: "2026-06-09T10:00:00Z",
    },
    preop_readiness: {
      has_planned_date: true,
      biometry_reviewed: true,
      topography_reviewed: true,
      consent_signed: true,
      score_numerator: 4,
      score_denominator: 4,
    },
    postop_cadence: {
      postop_day_1_status: "completed",
      postop_week_1_status: "scheduled",
      postop_month_1_status: "unknown",
      score_numerator: 2,
      score_denominator: 3,
    },
    complications_flag: false,
    insufficient_data: false,
  };
}

function emptySummary(): CataractWorkflowSummary {
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    generated_at: "2026-06-09T10:00:00Z",
    demo_mode: true,
    od: emptyLane("OD"),
    os: emptyLane("OS"),
    bilateral_planned: false,
    disclosure:
      "Provider-entered cataract surgical workflow support. ChartNav does not select an IOL power, does not recommend a surgical technique, does not recommend a surgery date, does not infer complications, and does not order tests.",
  };
}

function richSummary(): CataractWorkflowSummary {
  return {
    ...emptySummary(),
    od: richLane("OD"),
    os: richLane("OS"),
    bilateral_planned: true,
  };
}

function complicationsSummary(): CataractWorkflowSummary {
  const base = richSummary();
  base.od = {
    ...base.od,
    complications_flag: true,
    latest_record: { ...base.od.latest_record!, complications_flag: true },
  };
  return base;
}

beforeEach(() => {
  vi.mocked(getCataractWorkflowSummary).mockReset();
});

describe("CataractSurgicalWorkflowPanel — base render", () => {
  it("renders header, banner, refresh button", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(emptySummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-surgical-workflow-panel"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("cataract-banner").textContent).toMatch(
      /Provider-entered surgical workflow support/i,
    );
    expect(screen.getByTestId("cataract-banner").textContent).toMatch(
      /Does not select lens power/i,
    );
    expect(screen.getByTestId("cataract-banner").textContent).toMatch(
      /Does not recommend technique/i,
    );
    expect(screen.getByTestId("cataract-refresh-btn")).toBeInTheDocument();
  });

  it("renders both eye lanes with long-form labels", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("cataract-eye-lane-OD")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("cataract-eye-lane-OD").textContent).toMatch(
      /OD · Right Eye/,
    );
    expect(screen.getByTestId("cataract-eye-lane-OS").textContent).toMatch(
      /OS · Left Eye/,
    );
  });
});

describe("CataractSurgicalWorkflowPanel — insufficient data", () => {
  it("shows insufficient-data callouts per eye when no records", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(emptySummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-OD-insufficient"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("cataract-OD-insufficient").textContent).toMatch(
      /Insufficient data/i,
    );
    expect(screen.getByTestId("cataract-OS-insufficient")).toBeInTheDocument();
  });

  it("shows 'No bilateral surgery planned' flag when empty", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(emptySummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-bilateral-flag"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("cataract-bilateral-flag").textContent,
    ).toMatch(/No bilateral surgery planned/i);
  });
});

describe("CataractSurgicalWorkflowPanel — rich data", () => {
  it("renders pre-op readiness 4/4 with planned date + signed consent", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("cataract-OD-preop")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("cataract-OD-preop-score").textContent,
    ).toMatch(/4 \/ 4/);
    expect(
      screen.getByTestId("cataract-OD-biometry").textContent,
    ).toBe("Yes");
    expect(
      screen.getByTestId("cataract-OD-topography").textContent,
    ).toBe("Yes");
    expect(screen.getByTestId("cataract-OD-consent").textContent).toMatch(
      /Signed/,
    );
  });

  it("renders post-op cadence checkpoints with correct labels and tones", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-OD-postop"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("cataract-OD-postop-day-1-tone").textContent,
    ).toMatch(/Completed/i);
    expect(
      screen.getByTestId("cataract-OD-postop-week-1-tone").textContent,
    ).toMatch(/Scheduled/i);
    expect(
      screen.getByTestId("cataract-OD-postop-month-1-tone").textContent,
    ).toMatch(/Unknown/i);
    expect(
      screen.getByTestId("cataract-OD-postop-score").textContent,
    ).toMatch(/2 \/ 3/);
  });

  it("shows bilateral-planned flag when both eyes have a planned date", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-bilateral-flag"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("cataract-bilateral-flag").textContent,
    ).toMatch(/Bilateral surgery planned/i);
  });

  it("renders complications flag callout when set", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(
      complicationsSummary(),
    );
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-OD-complications-flag"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("cataract-OD-complications-flag").textContent,
    ).toMatch(/Provider-entered complications flag/i);
    expect(
      screen.getByTestId("cataract-OD-complications-flag").textContent,
    ).toMatch(/not interpreted by ChartNav/i);
  });
});

describe("CataractSurgicalWorkflowPanel — interaction + safety", () => {
  it("refresh button refetches summary", async () => {
    vi.mocked(getCataractWorkflowSummary)
      .mockResolvedValueOnce(emptySummary())
      .mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("cataract-OD-insufficient"),
      ).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("cataract-refresh-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("cataract-OD-preop")).toBeInTheDocument(),
    );
    expect(getCataractWorkflowSummary).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getCataractWorkflowSummary).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("cataract-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("cataract-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("renders disclosure with explicit boundary language", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("cataract-disclosure")).toBeInTheDocument(),
    );
    const d = screen.getByTestId("cataract-disclosure");
    expect(d.textContent).toMatch(/does not select an IOL power/i);
    expect(d.textContent).toMatch(/does not recommend a surgical technique/i);
    expect(d.textContent).toMatch(/does not recommend a surgery date/i);
    expect(d.textContent).toMatch(/does not order tests/i);
  });

  it("does NOT render forbidden clinical or surgical-decision phrases", async () => {
    vi.mocked(getCataractWorkflowSummary).mockResolvedValueOnce(richSummary());
    render(<CataractSurgicalWorkflowPanel patientId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("cataract-OD-preop")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "iol power recommended",
      "iol power 22",
      "phaco recommended",
      "flacs recommended",
      "surgery scheduled by chartnav",
      "auto-scheduled",
      "billing code",
      "order placed",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
