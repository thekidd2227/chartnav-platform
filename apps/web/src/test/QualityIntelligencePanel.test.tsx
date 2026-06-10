// Phase 89 — Quality Intelligence Panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/quality-intelligence/qualityIntelligenceApi", () => ({
  getQualityMeasures: vi.fn(),
  postQualityResponse: vi.fn(),
}));

import {
  getQualityMeasures,
  postQualityResponse,
} from "../features/quality-intelligence/qualityIntelligenceApi";
import { QualityIntelligencePanel } from "../features/quality-intelligence/QualityIntelligencePanel";
import type {
  QualityMeasureItem,
  QualityMeasuresResponse,
} from "../features/quality-intelligence/qualityIntelligenceTypes";

const DISCLOSURE =
  "Provider-reviewed quality documentation support. ChartNav does NOT submit to CMS, IRIS, payers, or registries; does NOT autonomously compute MIPS scoring; does NOT autonomously decide whether a measure is met; does NOT interpret images.";

function item(over: Partial<QualityMeasureItem> = {}): QualityMeasureItem {
  return {
    measure_id: "chartnav_demo_ophth_dr_communication",
    measure_name: "DR Communication (DEMO)",
    program_year: 2026,
    applicable: true,
    response_status: "pending",
    response_exception_code: null,
    responded_by_display: null,
    responded_by_role: null,
    responded_at: null,
    missing_structured_fields: ["visit_draft_signed"],
    present_structured_fields: [],
    required_fields: ["visit_draft_signed", "disease_stage_documented"],
    exception_codes: ["patient_refused", "documentation_other"],
    verified_for_submission: false,
    internal_demo_only: true,
    submission_status: "not_submitted",
    ...over,
  };
}

function emptyResponse(): QualityMeasuresResponse {
  return {
    encounter_id: 1,
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    encounter_type: "comprehensive",
    generated_at: "2026-06-10T10:00:00Z",
    demo_mode: true,
    items: [],
    counts: { total: 0, applicable: 0, incomplete: 0, completed: 0 },
    supported_response_types: [
      "met", "exception", "exclusion", "not_applicable", "incomplete",
    ],
    internal_demo_specs_present: false,
    submission_status: "not_submitted",
    disclosure: DISCLOSURE,
  };
}

function populatedResponse(): QualityMeasuresResponse {
  const a = item({
    measure_id: "chartnav_demo_ophth_dr_communication",
    measure_name: "DR Communication (DEMO)",
  });
  const b = item({
    measure_id: "chartnav_demo_ophth_poag_iop_documentation",
    measure_name: "POAG IOP Documentation (DEMO)",
    response_status: "met",
    responded_by_display: "Casey Clinician",
    responded_by_role: "clinician",
    responded_at: "2026-06-10T09:00:00Z",
    missing_structured_fields: [],
    present_structured_fields: ["iop_documented", "visit_draft_signed"],
  });
  return {
    ...emptyResponse(),
    items: [a, b],
    counts: { total: 2, applicable: 2, incomplete: 1, completed: 1 },
    internal_demo_specs_present: true,
  };
}

beforeEach(() => {
  vi.mocked(getQualityMeasures).mockReset();
  vi.mocked(postQualityResponse).mockReset();
});

describe("QualityIntelligencePanel — base render", () => {
  it("renders header, banner, refresh button", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(emptyResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-panel"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("quality-intelligence-banner").textContent,
    ).toMatch(/Provider-reviewed quality documentation support/i);
    expect(
      screen.getByTestId("quality-intelligence-banner").textContent,
    ).toMatch(/does not submit to CMS, IRIS, payers, or registries/i);
    expect(
      screen.getByTestId("quality-intelligence-banner").textContent,
    ).toMatch(/does not autonomously compute MIPS scoring/i);
    expect(
      screen.getByTestId("quality-intelligence-banner").textContent,
    ).toMatch(/Not a certified submission system/i);
    expect(
      screen.getByTestId("quality-intelligence-refresh-btn"),
    ).toBeInTheDocument();
  });

  it("renders counters + submission status", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(populatedResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-counts"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("quality-intelligence-count-applicable").textContent,
    ).toMatch(/Applicable:\s*2/);
    expect(
      screen.getByTestId("quality-intelligence-count-completed").textContent,
    ).toMatch(/Documented:\s*1/);
    expect(
      screen.getByTestId("quality-intelligence-count-incomplete").textContent,
    ).toMatch(/Awaiting response:\s*1/);
    expect(
      screen.getByTestId("quality-intelligence-submission-status").textContent,
    ).toMatch(/Submission status:\s*not submitted/i);
  });
});

describe("QualityIntelligencePanel — empty state", () => {
  it("renders empty callout when no specs are on file", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(emptyResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-empty"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("quality-intelligence-empty").textContent,
    ).toMatch(/never blocks signing/i);
  });
});

describe("QualityIntelligencePanel — populated rendering", () => {
  it("renders rows with status pill + missing fields + demo flag", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(populatedResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "quality-intelligence-row-chartnav_demo_ophth_dr_communication",
        ),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId(
        "quality-intelligence-status-chartnav_demo_ophth_dr_communication",
      ).textContent,
    ).toMatch(/Pending response/i);
    expect(
      screen.getByTestId(
        "quality-intelligence-status-chartnav_demo_ophth_poag_iop_documentation",
      ).textContent,
    ).toMatch(/Met/i);
    expect(
      screen.getByTestId(
        "quality-intelligence-missing-chartnav_demo_ophth_dr_communication",
      ).textContent,
    ).toMatch(/visit_draft_signed/);
    expect(
      screen.getByTestId(
        "quality-intelligence-demo-flag-chartnav_demo_ophth_dr_communication",
      ).textContent,
    ).toMatch(/Internal demo spec/i);
    expect(
      screen.getByTestId(
        "quality-intelligence-responder-chartnav_demo_ophth_poag_iop_documentation",
      ).textContent,
    ).toMatch(/Casey Clinician/);
  });

  it("shows internal-demo caution banner when demo specs present", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(populatedResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-demo-caution"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("quality-intelligence-demo-caution").textContent,
    ).toMatch(/Internal demo specs present/i);
    expect(
      screen.getByTestId("quality-intelligence-demo-caution").textContent,
    ).toMatch(/Verify with a qualified operator/i);
  });
});

describe("QualityIntelligencePanel — record response", () => {
  it("POSTs a 'met' response on click and refetches", async () => {
    vi.mocked(getQualityMeasures)
      .mockResolvedValueOnce(populatedResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postQualityResponse).mockResolvedValueOnce({
      id: 1,
      organization_id: 1,
      patient_id: 1,
      encounter_id: 1,
      measure_id: "chartnav_demo_ophth_dr_communication",
      response_type: "met",
      exception_code: null,
      responded_by_user_id: 5,
      responded_by_display: "Casey Clinician",
      responded_by_role: "clinician",
      responded_at: "2026-06-10T10:00:00Z",
      created_at: "2026-06-10T10:00:00Z",
      updated_at: "2026-06-10T10:00:00Z",
    });

    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "quality-intelligence-met-btn-chartnav_demo_ophth_dr_communication",
        ),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId(
        "quality-intelligence-met-btn-chartnav_demo_ophth_dr_communication",
      ),
    );

    await waitFor(() =>
      expect(postQualityResponse).toHaveBeenCalledTimes(1),
    );
    const args = vi.mocked(postQualityResponse).mock.calls[0]!;
    expect(args[0]).toBe(1);
    expect(args[1]).toBe("chartnav_demo_ophth_dr_communication");
    expect(args[2].response_type).toBe("met");
  });

  it("POSTs an 'exception' response with selected exception code", async () => {
    vi.mocked(getQualityMeasures)
      .mockResolvedValueOnce(populatedResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postQualityResponse).mockResolvedValueOnce({
      id: 2,
      organization_id: 1,
      patient_id: 1,
      encounter_id: 1,
      measure_id: "chartnav_demo_ophth_dr_communication",
      response_type: "exception",
      exception_code: "patient_refused",
      responded_by_user_id: 5,
      responded_by_display: "Casey Clinician",
      responded_by_role: "clinician",
      responded_at: "2026-06-10T10:00:00Z",
      created_at: "2026-06-10T10:00:00Z",
      updated_at: "2026-06-10T10:00:00Z",
    });

    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "quality-intelligence-exception-select-chartnav_demo_ophth_dr_communication",
        ),
      ).toBeInTheDocument(),
    );

    await userEvent.selectOptions(
      screen.getByTestId(
        "quality-intelligence-exception-select-chartnav_demo_ophth_dr_communication",
      ),
      "patient_refused",
    );
    await userEvent.click(
      screen.getByTestId(
        "quality-intelligence-exception-btn-chartnav_demo_ophth_dr_communication",
      ),
    );

    await waitFor(() =>
      expect(postQualityResponse).toHaveBeenCalledTimes(1),
    );
    const args = vi.mocked(postQualityResponse).mock.calls[0]!;
    expect(args[2].response_type).toBe("exception");
    expect(args[2].exception_code).toBe("patient_refused");
  });

  it("surfaces submit errors in inline banner", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(populatedResponse());
    vi.mocked(postQualityResponse).mockRejectedValueOnce(
      new Error("forbidden"),
    );

    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "quality-intelligence-met-btn-chartnav_demo_ophth_dr_communication",
        ),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId(
        "quality-intelligence-met-btn-chartnav_demo_ophth_dr_communication",
      ),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-submit-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("quality-intelligence-submit-error").textContent,
    ).toMatch(/forbidden/);
  });
});

describe("QualityIntelligencePanel — interaction + safety", () => {
  it("refresh button refetches the panel", async () => {
    vi.mocked(getQualityMeasures)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());

    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-empty"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("quality-intelligence-refresh-btn"),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId(
          "quality-intelligence-row-chartnav_demo_ophth_dr_communication",
        ),
      ).toBeInTheDocument(),
    );
    expect(getQualityMeasures).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getQualityMeasures).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("quality-intelligence-error").textContent,
    ).toMatch(/HTTP 503/);
  });

  it("renders disclosure verbatim from server", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(populatedResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("quality-intelligence-disclosure"),
      ).toBeInTheDocument(),
    );
    const d = screen.getByTestId("quality-intelligence-disclosure");
    expect(d.textContent).toMatch(/does not submit to cms/i);
    expect(d.textContent).toMatch(/iris/i);
    expect(d.textContent).toMatch(/does not autonomously compute mips/i);
  });

  it("does NOT render forbidden submission/scoring/billing phrases", async () => {
    vi.mocked(getQualityMeasures).mockResolvedValueOnce(populatedResponse());
    render(<QualityIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "quality-intelligence-row-chartnav_demo_ophth_dr_communication",
        ),
      ).toBeInTheDocument(),
    );
    const disclosure = (
      screen.getByTestId("quality-intelligence-disclosure").textContent ?? ""
    ).toLowerCase();
    const banner = (
      screen.getByTestId("quality-intelligence-banner").textContent ?? ""
    ).toLowerCase();
    const body = (document.body.textContent ?? "")
      .toLowerCase()
      .replace(disclosure, "")
      .replace(banner, "");
    for (const forbidden of [
      "automated mips submission",
      "iris connected",
      "submitted to cms",
      "submitted to iris",
      "submitted to payer",
      "guaranteed compliance",
      "certified quality reporting",
      "billing optimization",
      "auto-submitted",
      "auto-billed",
      "auto-coded",
      "mips score:",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
