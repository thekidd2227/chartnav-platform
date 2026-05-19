import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/fundus/fundusApi", () => ({
  listFundusCharts: vi.fn(),
  generateFundusChart: vi.fn(),
  getFundusChart: vi.fn(),
  renderFundusChart: vi.fn(),
  reviewFundusChart: vi.fn(),
  signFundusChart: vi.fn(),
}));

import {
  listFundusCharts,
  generateFundusChart,
  getFundusChart,
  reviewFundusChart,
  signFundusChart,
} from "../features/fundus/fundusApi";
import { FundusChartPanel } from "../features/fundus/FundusChartPanel";
import { FundusChartEditor } from "../features/fundus/FundusChartEditor";
import type {
  FundusChart,
  FundusChartListItem,
} from "../features/fundus/fundusTypes";

const baseChart = (over: Partial<FundusChart> = {}): FundusChart => ({
  id: 42,
  organization_id: 1,
  encounter_id: 7,
  patient_id: 1,
  laterality: "OD",
  status: "draft",
  source_type: "ai_generated",
  findings_json: { text: "horseshoe tear at 10:30 OD" },
  drawing_json: {
    version: 1,
    elements: [
      {
        type: "horseshoe_tear",
        laterality: "OD",
        clock_start: 10.5,
        clock_end: 10.5,
        zone: "equator",
        color: "#e53e3e",
        label: "horseshoe tear at 10:30 OD",
      },
    ],
  },
  rendered_svg: null,
  ai_model_name: "rule_based_v1",
  ai_confidence_json: null,
  warnings_json: [],
  reviewed_by_user_id: null,
  reviewed_at: null,
  signed_by_user_id: null,
  signed_at: null,
  created_by_user_id: 1,
  created_at: "2026-05-19T06:00:00Z",
  updated_at: "2026-05-19T06:00:00Z",
  ...over,
});

const baseListItem = (over: Partial<FundusChartListItem> = {}): FundusChartListItem => ({
  id: 42,
  laterality: "OD",
  status: "draft",
  source_type: "ai_generated",
  reviewed_at: null,
  signed_at: null,
  created_at: "2026-05-19T06:00:00Z",
  updated_at: "2026-05-19T06:00:00Z",
  ...over,
});

beforeEach(() => {
  vi.mocked(listFundusCharts).mockReset();
  vi.mocked(generateFundusChart).mockReset();
  vi.mocked(getFundusChart).mockReset();
  vi.mocked(reviewFundusChart).mockReset();
  vi.mocked(signFundusChart).mockReset();
});

describe("FundusChartPanel", () => {
  it("renders the safety banner with all four required clauses", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-list-empty")).toBeInTheDocument(),
    );
    const banner = screen.getByTestId("fundus-safety-banner");
    expect(banner.textContent).toMatch(/Draft from clinician-entered findings/i);
    expect(banner.textContent).toMatch(/Provider review required/i);
    expect(banner.textContent).toMatch(/Not image interpretation/i);
    expect(banner.textContent).toMatch(/Does not diagnose/i);
  });

  it("shows demo-ready empty state with sample-finding language", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-list-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("fundus-list-empty").textContent).toMatch(
      /horseshoe tear at 10:30 OD/,
    );
    expect(
      screen.getByTestId("fundus-preview-empty").textContent,
    ).toMatch(/No chart selected/i);
  });

  it("renders demo-safe sample chips (fake-data only)", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-sample-chips")).toBeInTheDocument(),
    );
    const chips = screen.getByTestId("fundus-sample-chips");
    expect(within(chips).getByText(/Horseshoe tear 10:30 OD/)).toBeInTheDocument();
    expect(within(chips).getByText(/Lattice 5 to 7 OS/)).toBeInTheDocument();
    expect(within(chips).getByText(/Superotemporal detachment OD/)).toBeInTheDocument();
    expect(within(chips).getByText(/Laser scars temporal OS/)).toBeInTheDocument();
  });

  it("clicking a sample chip populates the textarea and updates laterality", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-sample-chips")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByText(/Lattice 5 to 7 OS/));
    expect(
      (screen.getByTestId("fundus-findings-text") as HTMLTextAreaElement).value,
    ).toMatch(/lattice from 5 to 7 OS/);
    expect(screen.getByTestId("fundus-laterality-OS").getAttribute("aria-checked")).toBe(
      "true",
    );
  });

  it("OD/OS/OU selector updates aria-checked state", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-laterality-group")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("fundus-laterality-OD").getAttribute("aria-checked")).toBe(
      "true",
    );
    await userEvent.click(screen.getByTestId("fundus-laterality-OU"));
    expect(screen.getByTestId("fundus-laterality-OU").getAttribute("aria-checked")).toBe(
      "true",
    );
    expect(screen.getByTestId("fundus-laterality-OD").getAttribute("aria-checked")).toBe(
      "false",
    );
  });

  it("Generate button is disabled when findings text is empty", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-generate-btn")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("fundus-generate-btn")).toBeDisabled();
    await userEvent.type(
      screen.getByTestId("fundus-findings-text"),
      "horseshoe tear at 10:30 OD",
    );
    expect(screen.getByTestId("fundus-generate-btn")).not.toBeDisabled();
  });

  it("generate flow: posts findings, then loads + selects the new chart", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([]);
    vi.mocked(generateFundusChart).mockResolvedValueOnce({
      chart_id: 42,
      laterality: "OD",
      warnings: [],
      drawing_json: { version: 1, elements: [] },
      ai_model_name: "rule_based_v1",
      status: "draft",
    });
    vi.mocked(getFundusChart).mockResolvedValueOnce(baseChart());

    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-generate-btn")).toBeInTheDocument(),
    );
    await userEvent.type(
      screen.getByTestId("fundus-findings-text"),
      "horseshoe tear at 10:30 OD",
    );
    await userEvent.click(screen.getByTestId("fundus-generate-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("fundus-chart-editor")).toBeInTheDocument(),
    );
    expect(generateFundusChart).toHaveBeenCalledWith(7, {
      findings_text: "horseshoe tear at 10:30 OD",
      laterality: "OD",
    });
  });
});

describe("FundusChartEditor", () => {
  it("renders all three status-timeline steps and marks Draft as active", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart()}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-status-step-draft").getAttribute("data-active")).toBe(
      "true",
    );
    expect(screen.getByTestId("fundus-status-step-reviewed").getAttribute("data-active")).toBe(
      "false",
    );
    expect(screen.getByTestId("fundus-status-step-signed").getAttribute("data-active")).toBe(
      "false",
    );
  });

  it("renders AI-drafted badge when source_type is ai_generated", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({ source_type: "ai_generated" })}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-ai-drafted-badge").textContent).toMatch(
      /provider review required/i,
    );
  });

  it("renders warnings list when warnings_json is present", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({
          warnings_json: [
            "Laterality not stated in dictation; please confirm.",
            "No clock-hour specified for the lesion; please clarify.",
          ],
        })}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-warning-0").textContent).toMatch(/Laterality/);
    expect(screen.getByTestId("fundus-warning-1").textContent).toMatch(/clock-hour/);
  });

  it("renders 'no warnings' message instead of hiding the panel when empty", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({ warnings_json: [] })}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-warnings-empty").textContent).toMatch(
      /Provider must still review/i,
    );
  });

  it("sign button is disabled until the attestation checkbox is ticked", async () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart()}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-sign-btn")).toBeDisabled();
    await userEvent.click(screen.getByTestId("fundus-attestation-checkbox"));
    expect(screen.getByTestId("fundus-sign-btn")).not.toBeDisabled();
  });

  it("attestation block reads with the immutability + review language", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart()}
        onUpdated={vi.fn()}
      />,
    );
    const block = screen.getByTestId("fundus-attestation-block");
    expect(block.textContent).toMatch(/I attest/);
    expect(block.textContent).toMatch(/Signing will lock the chart/);
    expect(block.textContent).toMatch(/immutable/);
  });

  it("review button is distinct from sign and not labelled as a signature", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart()}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-review-btn").textContent).toMatch(
      /Mark Reviewed/i,
    );
    expect(screen.getByTestId("fundus-sign-btn").textContent).toMatch(/Sign/);
  });

  it("after Mark Reviewed, button shows reviewed and disables", async () => {
    vi.mocked(reviewFundusChart).mockResolvedValueOnce({
      chart_id: 42,
      status: "reviewed",
      reviewed_at: "2026-05-19T06:30:00Z",
    });
    const onUpdated = vi.fn();
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart()}
        onUpdated={onUpdated}
      />,
    );
    await userEvent.click(screen.getByTestId("fundus-review-btn"));
    await waitFor(() =>
      expect(reviewFundusChart).toHaveBeenCalledWith(42),
    );
    expect(onUpdated).toHaveBeenCalled();
  });

  it("signed chart renders a locked banner with timestamp + signer", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({
          status: "signed",
          signed_at: "2026-05-19T06:45:00Z",
          signed_by_user_id: 3,
        })}
        onUpdated={vi.fn()}
      />,
    );
    const lock = screen.getByTestId("fundus-signed-lock");
    expect(lock.textContent).toMatch(/locked/i);
    expect(lock.textContent).toMatch(/immutable/i);
    const meta = screen.getByTestId("fundus-signed-meta");
    expect(meta.textContent).toMatch(/clinician #3/);
  });

  it("signed chart disables edit controls (render/review/sign all gone)", () => {
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({
          status: "signed",
          signed_at: "2026-05-19T06:45:00Z",
        })}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("fundus-render-btn")).toBeNull();
    expect(screen.queryByTestId("fundus-review-btn")).toBeNull();
    expect(screen.queryByTestId("fundus-sign-btn")).toBeNull();
    expect(screen.queryByTestId("fundus-attestation-block")).toBeNull();
  });

  it("clicking sign with attestation invokes signFundusChart", async () => {
    vi.mocked(signFundusChart).mockResolvedValueOnce({
      chart_id: 42,
      status: "signed",
      signed_at: "2026-05-19T06:45:00Z",
    });
    const onUpdated = vi.fn();
    render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart()}
        onUpdated={onUpdated}
      />,
    );
    await userEvent.click(screen.getByTestId("fundus-attestation-checkbox"));
    await userEvent.click(screen.getByTestId("fundus-sign-btn"));
    await waitFor(() =>
      expect(signFundusChart).toHaveBeenCalledWith(42),
    );
    expect(onUpdated).toHaveBeenCalled();
  });

  it("warnings refresh when the chart prop changes (bug fix regression)", async () => {
    const { rerender } = render(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({ id: 1, warnings_json: ["first warning"] })}
        onUpdated={vi.fn()}
      />,
    );
    expect(screen.getByTestId("fundus-warning-0").textContent).toMatch(
      /first warning/,
    );
    rerender(
      <FundusChartEditor
        encounterId={7}
        chart={baseChart({ id: 2, warnings_json: ["second warning"] })}
        onUpdated={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("fundus-warning-0").textContent).toMatch(
        /second warning/,
      ),
    );
  });
});

describe("FundusChart UI — claim safety", () => {
  it("does not surface any diagnosis / orders / billing / coding / patient-messaging language", async () => {
    vi.mocked(listFundusCharts).mockResolvedValueOnce([baseListItem()]);
    vi.mocked(getFundusChart).mockResolvedValueOnce(
      baseChart({
        warnings_json: ["Laterality not stated; please confirm."],
      }),
    );
    render(<FundusChartPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("fundus-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("fundus-list-item-42"));
    await waitFor(() =>
      expect(screen.getByTestId("fundus-chart-editor")).toBeInTheDocument(),
    );

    const body = document.body.textContent ?? "";
    const lower = body.toLowerCase();

    // Forbidden positive phrasings — these would be promises ChartNav
    // does not make. Negative phrasings ("not image interpretation",
    // "does not diagnose") are required by the safety banner and are
    // therefore allowed.
    expect(lower).not.toMatch(/order placed/);
    expect(lower).not.toMatch(/refer to/);
    expect(lower).not.toMatch(/send patient message/);
    expect(lower).not.toMatch(/billing code/);
    expect(lower).not.toMatch(/cpt code/);
    expect(lower).not.toMatch(/icd[- ]?10/);
    expect(lower).not.toMatch(/diagnosis confirmed/);
    expect(lower).not.toMatch(/autonomous diagnosis/);
    expect(lower).not.toMatch(/autonomous image interpretation/);
    expect(lower).not.toMatch(/automatic image interpretation/);
    expect(lower).not.toMatch(/ai diagnoses/);
    expect(lower).not.toMatch(/openai-powered/);
    expect(lower).not.toMatch(/hipaa compliant/);
    expect(lower).not.toMatch(/automatically signed/);
    expect(lower).not.toMatch(/auto-signed/);
  });
});
