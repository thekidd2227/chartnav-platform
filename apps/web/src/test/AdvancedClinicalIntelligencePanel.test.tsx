// Phase 92 — Advanced Clinical Intelligence Panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock(
  "../features/advanced-clinical-intelligence/advancedClinicalIntelligenceApi",
  () => ({
    getAdvancedClinicalIntelligence: vi.fn(),
  }),
);

import { getAdvancedClinicalIntelligence } from "../features/advanced-clinical-intelligence/advancedClinicalIntelligenceApi";
import { AdvancedClinicalIntelligencePanel } from "../features/advanced-clinical-intelligence/AdvancedClinicalIntelligencePanel";
import type {
  AdvancedClinicalIntelligenceResponse,
} from "../features/advanced-clinical-intelligence/advancedClinicalIntelligenceTypes";

function emptyResponse(): AdvancedClinicalIntelligenceResponse {
  return {
    encounter_id: 1,
    organization_id: 1,
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    encounter_type: "comprehensive",
    visit_mode: "follow_up",
    active_laterality: "OU",
    retina_summary: {
      od: {
        injection_count: 0,
        latest_injection_date: null,
        latest_interval_weeks: null,
        latest_authorization_status: null,
        insufficient_data: true,
      },
      os: {
        injection_count: 0,
        latest_injection_date: null,
        latest_interval_weeks: null,
        latest_authorization_status: null,
        insufficient_data: true,
      },
      stage_history: [],
      stage_history_count: 0,
      fundus_chart_count: 0,
      fundus_chart_latest: null,
      imaging_metadata_summary: {},
      data_limitations: ["No anti-VEGF history on file."],
      insufficient_data: true,
    },
    glaucoma_summary: {
      od: {},
      os: {},
      poag_stage_history: [],
      poag_stage_history_count: 0,
      adherence_signals: {
        active_medication_count: 0,
        refill_gap_count: 0,
        active_safety_event_count: 0,
      },
      data_limitations: ["No glaucoma data on file."],
      insufficient_data: true,
    },
    cataract_summary: {
      od: { record_count: 0, insufficient_data: true },
      os: { record_count: 0, insufficient_data: true },
      conversion_funnel: {
        any_record: false,
        planned_date_present: false,
        biometry_review_complete: false,
        consent_signed: false,
        post_op_day_1_complete: false,
      },
      data_limitations: ["No cataract workflow records on file."],
      insufficient_data: true,
    },
    fhir_export_readiness: {
      packet_renderable: true,
      document_reference_id: "retina-visit-packet-1",
      schema_version: "chartnav.retina_visit_packet/1.0",
      all_signed: false,
      extensions_present: [],
      submission_status: "not_submitted",
      transport: "none",
      boundary:
        "ChartNav does not submit, transmit, or post this packet to any registry, payer, CMS endpoint, IRIS feed, or EHR.",
      insufficient_data: false,
    },
    data_limitations: ["No anti-VEGF history on file."],
    safety_boundaries: [
      {
        key: "no_autonomous_diagnosis",
        asserted: true,
        statement:
          "ChartNav does not diagnose. Every projection on this surface is a metadata-only summary of provider-entered data.",
      },
      {
        key: "no_image_interpretation",
        asserted: true,
        statement:
          "ChartNav does not interpret fundus photographs, OCT scans, or any imaging modality.",
      },
      {
        key: "no_treatment_recommendation",
        asserted: true,
        statement:
          "ChartNav does not recommend anti-VEGF injection, laser, surgery, IOL choice, medication change, or any other treatment.",
      },
      {
        key: "no_submission",
        asserted: true,
        statement:
          "ChartNav does not submit, transmit, or post anything to any registry, payer, CMS endpoint, IRIS feed, or EHR.",
      },
      {
        key: "metadata_only",
        asserted: true,
        statement:
          "Every section on this surface is a metadata projection only.",
      },
    ],
    generated_at: "2026-06-09T12:00:00Z",
    demo_mode: true,
    submission_status: "not_submitted",
    disclosure:
      "Advanced Clinical Intelligence is a longitudinal projection of provider-entered structured data. ChartNav does not diagnose, does not interpret images, does not recommend treatment, and does not submit anything to any registry, payer, CMS endpoint, IRIS feed, or EHR. Every section is a metadata projection.",
  };
}

function richResponse(): AdvancedClinicalIntelligenceResponse {
  const base = emptyResponse();
  return {
    ...base,
    retina_summary: {
      ...base.retina_summary,
      od: {
        injection_count: 3,
        latest_injection_date: "2026-05-30",
        latest_interval_weeks: 8,
        latest_authorization_status: "approved",
        insufficient_data: false,
      },
      os: {
        injection_count: 2,
        latest_injection_date: "2026-05-15",
        latest_interval_weeks: 6,
        latest_authorization_status: "approved",
        insufficient_data: false,
      },
      stage_history: [
        {
          id: 1,
          diagnosis_code: "h35.31",
          staging_system: "amd_areds",
          stage_value: "Category 3",
          staged_at: "2026-05-01T10:00:00Z",
          progression_detected: null,
        },
      ],
      stage_history_count: 1,
      fundus_chart_count: 1,
      fundus_chart_latest: {
        id: 5,
        laterality: "OD",
        status: "signed",
        created_at: "2026-05-30T10:00:00Z",
        signed_at: "2026-05-30T11:00:00Z",
      },
      data_limitations: [],
      insufficient_data: false,
    },
    glaucoma_summary: {
      ...base.glaucoma_summary,
      poag_stage_history: [
        {
          id: 9,
          stage_value: "Mild",
          staged_at: "2026-04-01T10:00:00Z",
          progression_detected: null,
        },
      ],
      poag_stage_history_count: 1,
      adherence_signals: {
        active_medication_count: 2,
        refill_gap_count: 1,
        active_safety_event_count: 0,
      },
      data_limitations: [],
      insufficient_data: false,
    },
    cataract_summary: {
      ...base.cataract_summary,
      od: {
        record_count: 1,
        planned_surgery_date: "2026-07-15",
        biometry_reviewed: true,
        consent_status: "signed",
        insufficient_data: false,
      },
      os: { record_count: 0, insufficient_data: true },
      conversion_funnel: {
        any_record: true,
        planned_date_present: true,
        biometry_review_complete: true,
        consent_signed: true,
        post_op_day_1_complete: false,
      },
      data_limitations: [],
      insufficient_data: false,
    },
    fhir_export_readiness: {
      ...base.fhir_export_readiness,
      extensions_present: ["disease_staging_summary", "medication_safety_summary"],
      all_signed: true,
    },
  };
}

beforeEach(() => {
  vi.mocked(getAdvancedClinicalIntelligence).mockReset();
});

describe("AdvancedClinicalIntelligencePanel — baseline + safety", () => {
  it("renders the panel header, banner, and refresh button", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      emptyResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("advanced-clinical-intelligence-panel"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("aci-banner").textContent).toMatch(
      /Provider-reviewed longitudinal projection/i,
    );
    expect(screen.getByTestId("aci-refresh-btn")).toBeInTheDocument();
  });

  it("renders Phase 91 context chips for visit_mode + active_laterality", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      emptyResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-context-chips")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("aci-visit-mode-chip").textContent).toMatch(
      /follow up/i,
    );
    expect(screen.getByTestId("aci-laterality-chip").textContent).toMatch(/OU/);
  });

  it("renders all five safety boundaries as asserted statements", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      emptyResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-safety-boundaries")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("aci-boundary-no_autonomous_diagnosis"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("aci-boundary-no_image_interpretation"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("aci-boundary-no_treatment_recommendation"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("aci-boundary-no_submission")).toBeInTheDocument();
    expect(screen.getByTestId("aci-boundary-metadata_only")).toBeInTheDocument();
  });

  it("renders the disclosure with safe-claims language", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      emptyResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-disclosure")).toBeInTheDocument(),
    );
    const text = screen.getByTestId("aci-disclosure").textContent ?? "";
    expect(text).toMatch(/does not diagnose/i);
    expect(text).toMatch(/does not interpret images/i);
    expect(text).toMatch(/does not recommend treatment/i);
    expect(text).toMatch(/does not submit/i);
  });
});

describe("AdvancedClinicalIntelligencePanel — insufficient data states", () => {
  it("shows OD/OS insufficient-data banners in retina + cataract sections", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      emptyResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-retina-section")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("aci-retina-OD-empty")).toBeInTheDocument();
    expect(screen.getByTestId("aci-retina-OS-empty")).toBeInTheDocument();
    expect(screen.getByTestId("aci-cataract-OD-empty")).toBeInTheDocument();
    expect(screen.getByTestId("aci-cataract-OS-empty")).toBeInTheDocument();
    expect(screen.getByTestId("aci-glaucoma-empty")).toBeInTheDocument();
  });
});

describe("AdvancedClinicalIntelligencePanel — rich data", () => {
  it("reflects anti-VEGF injection count and latest interval per eye", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      richResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-retina-OD-count")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("aci-retina-OD-count").textContent).toMatch(/3/);
    expect(screen.getByTestId("aci-retina-OD-interval").textContent).toMatch(
      /8 wks/,
    );
    expect(screen.getByTestId("aci-retina-OS-interval").textContent).toMatch(
      /6 wks/,
    );
  });

  it("reflects POAG stage history count and adherence signals", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      richResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-glaucoma-stage-count")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("aci-glaucoma-stage-count").textContent,
    ).toMatch(/1 record/);
    expect(
      screen.getByTestId("aci-glaucoma-adherence").textContent,
    ).toMatch(/meds 2/);
  });

  it("renders cataract conversion funnel rows with chips", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      richResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-cataract-funnel")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("aci-cataract-funnel-any-record-chip").textContent,
    ).toMatch(/Yes/i);
    expect(
      screen.getByTestId("aci-cataract-funnel-postop1-chip").textContent,
    ).toMatch(/Pending/i);
  });

  it("renders FHIR readiness chips, extensions, and boundary note", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      richResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-fhir-section")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("aci-fhir-renderable-chip").textContent,
    ).toMatch(/Packet renderable/i);
    expect(
      screen.getByTestId("aci-fhir-submission-chip").textContent,
    ).toMatch(/not submitted/i);
    expect(
      screen.getByTestId("aci-fhir-transport-chip").textContent,
    ).toMatch(/none/i);
    expect(
      screen.getByTestId("aci-fhir-extensions").textContent,
    ).toMatch(/disease_staging_summary/);
    expect(screen.getByTestId("aci-fhir-boundary").textContent).toMatch(
      /does not submit/i,
    );
  });
});

describe("AdvancedClinicalIntelligencePanel — interaction + safety", () => {
  it("refresh button refetches the projection", async () => {
    vi.mocked(getAdvancedClinicalIntelligence)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(richResponse());
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-retina-OD-empty")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("aci-refresh-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("aci-retina-OD-count")).toBeInTheDocument(),
    );
    expect(getAdvancedClinicalIntelligence).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("aci-error").textContent).toMatch(/HTTP 503/);
  });

  it("does NOT render any forbidden autonomy / submission phrases", async () => {
    vi.mocked(getAdvancedClinicalIntelligence).mockResolvedValueOnce(
      richResponse(),
    );
    render(<AdvancedClinicalIntelligencePanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("aci-retina-OD-count")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "disease worsening detected",
      "interval should be shortened",
      "interval should be extended",
      "anti-vegf recommended",
      "progression confirmed",
      "escalate to surgery",
      "medication change recommended",
      "treatment recommended",
      "iol power recommended",
      "lens model recommended",
      "phaco recommended",
      "complications detected",
      "surgical plan recommended",
      "auto-classified",
      "auto-scheduled",
      "submitted to",
      "transmitted to",
      "wrote back to ehr",
      "auto-submitted",
      "bidirectional sync",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
