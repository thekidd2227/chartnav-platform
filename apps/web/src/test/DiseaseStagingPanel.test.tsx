// Phase 84 — Disease Staging Panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/disease-staging/diseaseStagingApi", () => ({
  getDiseaseStaging: vi.fn(),
  postDiseaseStage: vi.fn(),
}));

import {
  getDiseaseStaging,
  postDiseaseStage,
} from "../features/disease-staging/diseaseStagingApi";
import { DiseaseStagingPanel } from "../features/disease-staging/DiseaseStagingPanel";
import type {
  DiseaseStageRecord,
  DiseaseStagingPanelResponse,
} from "../features/disease-staging/diseaseStagingTypes";

const SUPPORTED_SYSTEMS = [
  {
    code: "amd_areds" as const,
    label: "AMD AREDS",
    stages: ["Category 1", "Category 2", "Category 3", "Category 4"],
  },
  {
    code: "diabetic_etdrs" as const,
    label: "Diabetic Retinopathy ETDRS",
    stages: [
      "Mild NPDR",
      "Moderate NPDR",
      "Severe NPDR",
      "Non-high-risk PDR",
      "High-risk PDR",
      "Advanced",
    ],
  },
  {
    code: "glaucoma_poag" as const,
    label: "Glaucoma POAG",
    stages: ["Mild", "Moderate", "Severe"],
  },
  {
    code: "keratoconus_amsler_krumeich" as const,
    label: "Keratoconus Amsler-Krumeich",
    stages: ["Stage I", "Stage II", "Stage III", "Stage IV"],
  },
  {
    code: "dry_eye_dews" as const,
    label: "Dry Eye DEWS",
    stages: ["Severity 1", "Severity 2", "Severity 3", "Severity 4"],
  },
];

const DISCLOSURE =
  "Provider-entered disease staging records. ChartNav does not stage disease, " +
  "does not interpret imaging, does not infer progression, does not recommend " +
  "treatment, and does not recommend surgery.";

function emptyResponse(): DiseaseStagingPanelResponse {
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    generated_at: "2026-06-09T10:00:00Z",
    demo_mode: true,
    records: [],
    latest_by_diagnosis: {},
    supported_systems: SUPPORTED_SYSTEMS,
    disclosure: DISCLOSURE,
  };
}

function record(over: Partial<DiseaseStageRecord> = {}): DiseaseStageRecord {
  return {
    id: 1,
    organization_id: 1,
    patient_id: 1,
    encounter_id: 1,
    diagnosis_code: "h35.31",
    staging_system: "amd_areds",
    staging_system_label: "AMD AREDS",
    stage_value: "Category 3",
    prior_stage: null,
    staged_at: "2026-06-09T10:00:00Z",
    staged_by_user_id: 5,
    staged_by_display_name: "Dr. Carter",
    staged_by_role: "clinician",
    progression_detected: null,
    elapsed_days_since_prior: null,
    created_at: "2026-06-09T10:00:00Z",
    updated_at: "2026-06-09T10:00:00Z",
    ...over,
  };
}

function richResponse(): DiseaseStagingPanelResponse {
  const amd = record({
    diagnosis_code: "h35.31",
    staging_system: "amd_areds",
    staging_system_label: "AMD AREDS",
    stage_value: "Category 4",
    prior_stage: "Category 2",
    progression_detected: true,
    elapsed_days_since_prior: 90,
  });
  const glaucoma = record({
    id: 2,
    diagnosis_code: "h40.1",
    staging_system: "glaucoma_poag",
    staging_system_label: "Glaucoma POAG",
    stage_value: "Moderate",
    prior_stage: null,
    progression_detected: null,
    elapsed_days_since_prior: null,
  });
  return {
    ...emptyResponse(),
    records: [amd, glaucoma],
    latest_by_diagnosis: { "h35.31": amd, "h40.1": glaucoma },
  };
}

beforeEach(() => {
  vi.mocked(getDiseaseStaging).mockReset();
  vi.mocked(postDiseaseStage).mockReset();
});

describe("DiseaseStagingPanel — base render", () => {
  it("renders header, banner, and refresh button", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(emptyResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("disease-staging-panel")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("disease-staging-banner").textContent).toMatch(
      /Provider-entered disease staging records/i,
    );
    expect(screen.getByTestId("disease-staging-banner").textContent).toMatch(
      /does not stage disease/i,
    );
    expect(screen.getByTestId("disease-staging-banner").textContent).toMatch(
      /does not interpret imaging/i,
    );
    expect(
      screen.getByTestId("disease-staging-refresh-btn"),
    ).toBeInTheDocument();
  });

  it("renders patient meta with record count", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(richResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-patient-meta"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("disease-staging-record-count").textContent,
    ).toMatch(/2 records/);
  });
});

describe("DiseaseStagingPanel — empty state", () => {
  it("renders empty callout when no records are on file", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(emptyResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("disease-staging-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("disease-staging-empty").textContent).toMatch(
      /No provider-entered disease-staging records on file/i,
    );
    expect(screen.getByTestId("disease-staging-empty").textContent).toMatch(
      /never blocks signing/i,
    );
  });
});

describe("DiseaseStagingPanel — populated", () => {
  it("renders latest-by-diagnosis rows with progression pill tones", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(richResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-latest-list"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("disease-staging-latest-h35.31"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("disease-staging-system-h35.31").textContent,
    ).toBe("AMD AREDS");
    expect(
      screen.getByTestId("disease-staging-stage-h35.31").textContent,
    ).toBe("Category 4");
    expect(
      screen.getByTestId("disease-staging-prior-h35.31").textContent,
    ).toBe("Category 2");
    expect(
      screen.getByTestId("disease-staging-elapsed-h35.31").textContent,
    ).toBe("90");
    expect(
      screen.getByTestId("disease-staging-progression-h35.31").textContent,
    ).toMatch(/Stage changed/i);
    expect(
      screen.getByTestId("disease-staging-progression-h40.1").textContent,
    ).toMatch(/First stage on record/i);
    expect(
      screen.getByTestId("disease-staging-actor-h35.31").textContent,
    ).toMatch(/Dr\. Carter/);
    expect(
      screen.getByTestId("disease-staging-actor-h35.31").textContent,
    ).toMatch(/clinician/);
  });

  it("renders Stage unchanged tone when progression_detected is false", async () => {
    const r = emptyResponse();
    const rec = record({
      stage_value: "Category 2",
      prior_stage: "Category 2",
      progression_detected: false,
      elapsed_days_since_prior: 30,
    });
    r.records = [rec];
    r.latest_by_diagnosis = { "h35.31": rec };
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(r);
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-progression-h35.31"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("disease-staging-progression-h35.31").textContent,
    ).toMatch(/Stage unchanged/i);
  });
});

describe("DiseaseStagingPanel — form interaction", () => {
  it("system-select changes filter the stage-select options", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(emptyResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-system-select"),
      ).toBeInTheDocument(),
    );

    const stageSelect = screen.getByTestId(
      "disease-staging-stage-select",
    ) as HTMLSelectElement;

    // Default is amd_areds with 4 categories.
    expect(stageSelect.options.length).toBe(4);
    expect(stageSelect.options[0]!.value).toBe("Category 1");

    await userEvent.selectOptions(
      screen.getByTestId("disease-staging-system-select"),
      "glaucoma_poag",
    );

    await waitFor(() => expect(stageSelect.options.length).toBe(3));
    expect(stageSelect.options[0]!.value).toBe("Mild");
  });

  it("POSTs the staging payload and refetches on success", async () => {
    vi.mocked(getDiseaseStaging)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(richResponse());
    vi.mocked(postDiseaseStage).mockResolvedValueOnce(record());

    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("disease-staging-empty")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("disease-staging-submit-btn"));

    await waitFor(() =>
      expect(postDiseaseStage).toHaveBeenCalledTimes(1),
    );
    expect(vi.mocked(postDiseaseStage).mock.calls[0]![0]).toBe(1);
    expect(vi.mocked(postDiseaseStage).mock.calls[0]![1]).toEqual({
      diagnosis_code: "h35.31",
      staging_system: "amd_areds",
      stage_value: "Category 1",
    });
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-latest-h35.31"),
      ).toBeInTheDocument(),
    );
    expect(getDiseaseStaging).toHaveBeenCalledTimes(2);
  });

  it("surfaces submit errors in an inline banner", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(emptyResponse());
    vi.mocked(postDiseaseStage).mockRejectedValueOnce(
      new Error("staging_system_invalid"),
    );

    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-submit-btn"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("disease-staging-submit-btn"));

    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-submit-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("disease-staging-submit-error").textContent,
    ).toMatch(/staging_system_invalid/);
  });
});

describe("DiseaseStagingPanel — interaction + safety", () => {
  it("refresh button refetches the panel", async () => {
    vi.mocked(getDiseaseStaging)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(richResponse());

    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("disease-staging-empty")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("disease-staging-refresh-btn"));

    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-latest-h35.31"),
      ).toBeInTheDocument(),
    );
    expect(getDiseaseStaging).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getDiseaseStaging).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("disease-staging-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("disease-staging-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("renders disclosure with explicit boundary language", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(richResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-disclosure"),
      ).toBeInTheDocument(),
    );
    const d = screen.getByTestId("disease-staging-disclosure");
    expect(d.textContent).toMatch(/does not stage disease/i);
    expect(d.textContent).toMatch(/does not interpret imaging/i);
    expect(d.textContent).toMatch(/does not infer progression/i);
    expect(d.textContent).toMatch(/does not recommend treatment/i);
    expect(d.textContent).toMatch(/does not recommend surgery/i);
  });

  it("does NOT render forbidden clinical or autonomous-decision phrases", async () => {
    vi.mocked(getDiseaseStaging).mockResolvedValueOnce(richResponse());
    render(<DiseaseStagingPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("disease-staging-latest-h35.31"),
      ).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "surgery recommended",
      "anti-vegf recommended",
      "injection recommended",
      "iol power recommended",
      "stage automatically detected",
      "stage auto-detected",
      "image interpreted",
      "image interpretation",
      "progression confirmed by chartnav",
      "auto-staged",
      "order placed",
      "billing code",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
