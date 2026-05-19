// Phase 21B — ImagingPipelinePanel tests.
//
// Covers:
//   - Empty state when no studies exist (clinician identity).
//   - Populated list + study selection + file/measurement rendering.
//   - RBAC rendering: clinician + technician see + Add controls;
//     technician does NOT see Mark reviewed; reviewer sees no
//     write controls; front_desk is fully blocked.
//   - Mark-reviewed flow for clinician.
//   - Patient-not-bridged renders unavailable state with no API calls.
//   - No device-integration / autonomous-interpretation / billing /
//     order / referral / patient-messaging language anywhere in
//     the interactive surface.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    API_URL: "http://test",
    listPatientImagingStudies: vi.fn(),
    createPatientImagingStudy: vi.fn(),
    getImagingStudy: vi.fn(),
    updateImagingStudy: vi.fn(),
    markImagingStudyReviewed: vi.fn(),
    listImagingStudyFiles: vi.fn(),
    createImagingStudyFile: vi.fn(),
    listImagingStudyMeasurements: vi.fn(),
    createImagingStudyMeasurement: vi.fn(),
  };
});

import * as api from "../api";
import { ImagingPipelinePanel } from "../ImagingPipelinePanel";

const CLINICIAN: api.Me = {
  user_id: 2,
  email: "clin@chartnav.local",
  full_name: "Casey Clinician",
  role: "clinician",
  organization_id: 1,
};

const REVIEWER: api.Me = {
  user_id: 3,
  email: "rev@chartnav.local",
  full_name: "Riley Reviewer",
  role: "reviewer",
  organization_id: 1,
};

const FRONT_DESK: api.Me = {
  user_id: 10,
  email: "front@chartnav.local",
  full_name: "Frankie Front-Desk",
  role: "front_desk",
  organization_id: 1,
};

const TECHNICIAN: api.Me = {
  user_id: 11,
  email: "tech@chartnav.local",
  full_name: "Taylor Technician",
  role: "technician",
  organization_id: 1,
};

const STUDY: api.ImagingStudy = {
  id: 500,
  organization_id: 1,
  patient_id: 1,
  encounter_id: 200,
  modality: "oct_macula",
  eye: "OD",
  status: "ready_for_review",
  captured_at: "2026-04-10T09:00:00",
  reviewed_by_user_id: null,
  reviewed_at: null,
  notes: null,
  created_by_user_id: 2,
  created_at: "2026-05-01T00:00:00",
  updated_at: "2026-05-01T00:00:00",
};

const FILE_ROW: api.ImagingFileMetadata = {
  id: 800,
  organization_id: 1,
  study_id: 500,
  file_kind: "image",
  storage_uri: "s3://practice/scan.dcm",
  file_name: "od_macula_20260410.dcm",
  content_type: "application/dicom",
  size_bytes: 8421376,
  checksum_sha256: null,
  created_by_user_id: 2,
  created_at: "2026-05-01T00:00:00",
};

const MEASUREMENT_ROW: api.ImagingMeasurement = {
  id: 900,
  organization_id: 1,
  study_id: 500,
  measurement_type: "central_macular_thickness",
  eye: "OD",
  value: "240",
  unit: "microns",
  source: "manual",
  created_by_user_id: 2,
  created_at: "2026-05-01T00:00:00",
};

function emptyList<T>() {
  return { items: [] as T[], total: 0 };
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.listPatientImagingStudies as any).mockResolvedValue(emptyList());
  (api.listImagingStudyFiles as any).mockResolvedValue(emptyList());
  (api.listImagingStudyMeasurements as any).mockResolvedValue(emptyList());
});

describe("ImagingPipelinePanel — unavailable state", () => {
  it("renders unavailable when no native patientId", () => {
    render(
      <ImagingPipelinePanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={null}
        encounterId={null}
      />
    );
    expect(
      screen.getByTestId("imaging-pipeline-unavailable")
    ).toBeInTheDocument();
    expect(api.listPatientImagingStudies).not.toHaveBeenCalled();
  });

  it("blocks front_desk regardless of patientId", () => {
    render(
      <ImagingPipelinePanel
        identity="front@chartnav.local"
        me={FRONT_DESK}
        patientId={1}
        encounterId={200}
      />
    );
    expect(
      screen.getByTestId("imaging-pipeline-blocked")
    ).toBeInTheDocument();
    expect(api.listPatientImagingStudies).not.toHaveBeenCalled();
  });
});

describe("ImagingPipelinePanel — empty state", () => {
  it("renders empty placeholder for clinician with no studies", async () => {
    render(
      <ImagingPipelinePanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("imaging-pipeline")).toBeInTheDocument()
    );
    expect(screen.getByTestId("imaging-studies-empty")).toHaveTextContent(
      /No imaging studies yet/i
    );
    expect(screen.getByTestId("imaging-detail-empty")).toBeInTheDocument();
    expect(screen.getByTestId("imaging-add-study")).toBeInTheDocument();
  });
});

describe("ImagingPipelinePanel — populated rendering + RBAC", () => {
  it("clinician sees studies list, files, measurements, and Mark reviewed", async () => {
    (api.listPatientImagingStudies as any).mockResolvedValue({
      items: [STUDY],
      total: 1,
    });
    (api.listImagingStudyFiles as any).mockResolvedValue({
      items: [FILE_ROW],
      total: 1,
    });
    (api.listImagingStudyMeasurements as any).mockResolvedValue({
      items: [MEASUREMENT_ROW],
      total: 1,
    });
    render(
      <ImagingPipelinePanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("imaging-studies")).toBeInTheDocument()
    );
    const row = screen.getByTestId(`imaging-study-row-${STUDY.id}`);
    expect(within(row).getByText(/OCT macula/i)).toBeInTheDocument();
    expect(within(row).getByText("OD")).toBeInTheDocument();
    expect(within(row).getByText(/ready for review/i)).toBeInTheDocument();

    // Wait for the detail panel to pick up files + measurements.
    await waitFor(() =>
      expect(screen.getByTestId("imaging-files-table")).toBeInTheDocument()
    );
    expect(
      screen.getByTestId("imaging-measurements-table")
    ).toBeInTheDocument();

    expect(screen.getByTestId("imaging-add-study")).toBeInTheDocument();
    expect(screen.getByTestId("imaging-add-file")).toBeInTheDocument();
    expect(screen.getByTestId("imaging-add-measurement")).toBeInTheDocument();
    expect(screen.getByTestId("imaging-mark-reviewed")).toBeInTheDocument();
  });

  it("technician sees create controls but NOT Mark reviewed", async () => {
    (api.listPatientImagingStudies as any).mockResolvedValue({
      items: [STUDY],
      total: 1,
    });
    render(
      <ImagingPipelinePanel
        identity="tech@chartnav.local"
        me={TECHNICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("imaging-studies")).toBeInTheDocument()
    );
    expect(screen.getByTestId("imaging-add-study")).toBeInTheDocument();
    expect(screen.getByTestId("imaging-add-file")).toBeInTheDocument();
    expect(screen.getByTestId("imaging-add-measurement")).toBeInTheDocument();
    expect(
      screen.queryByTestId("imaging-mark-reviewed")
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("imaging-review-readonly")
    ).toHaveTextContent(/admin or clinician/i);
  });

  it("reviewer sees no write controls and no Mark reviewed", async () => {
    (api.listPatientImagingStudies as any).mockResolvedValue({
      items: [STUDY],
      total: 1,
    });
    render(
      <ImagingPipelinePanel
        identity="rev@chartnav.local"
        me={REVIEWER}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("imaging-studies")).toBeInTheDocument()
    );
    expect(screen.queryByTestId("imaging-add-study")).not.toBeInTheDocument();
    expect(screen.queryByTestId("imaging-add-file")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("imaging-add-measurement")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("imaging-mark-reviewed")
    ).not.toBeInTheDocument();
    expect(
      screen.getByTestId("imaging-review-readonly")
    ).toBeInTheDocument();
  });
});

describe("ImagingPipelinePanel — mark reviewed flow", () => {
  it("calls markImagingStudyReviewed and refreshes", async () => {
    (api.listPatientImagingStudies as any).mockResolvedValueOnce({
      items: [STUDY],
      total: 1,
    });
    (api.markImagingStudyReviewed as any).mockResolvedValue({
      ...STUDY,
      status: "reviewed",
      reviewed_by_user_id: 2,
      reviewed_at: "2026-05-11T00:00:00",
    });
    // refreshed list returns the reviewed study
    (api.listPatientImagingStudies as any).mockResolvedValueOnce({
      items: [
        {
          ...STUDY,
          status: "reviewed",
          reviewed_by_user_id: 2,
          reviewed_at: "2026-05-11T00:00:00",
        },
      ],
      total: 1,
    });

    render(
      <ImagingPipelinePanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("imaging-mark-reviewed")).toBeInTheDocument()
    );
    await userEvent.click(screen.getByTestId("imaging-mark-reviewed"));
    await waitFor(() =>
      expect(api.markImagingStudyReviewed).toHaveBeenCalledWith(
        "clin@chartnav.local",
        STUDY.id,
        expect.any(Object)
      )
    );
  });
});

describe("ImagingPipelinePanel — forbidden vocabulary scan", () => {
  it("interactive surface has no device-integration / autonomous-interpretation / order / referral / patient-messaging / billing language", async () => {
    (api.listPatientImagingStudies as any).mockResolvedValue({
      items: [STUDY],
      total: 1,
    });
    (api.listImagingStudyFiles as any).mockResolvedValue({
      items: [FILE_ROW],
      total: 1,
    });
    (api.listImagingStudyMeasurements as any).mockResolvedValue({
      items: [MEASUREMENT_ROW],
      total: 1,
    });
    const { container } = render(
      <ImagingPipelinePanel
        identity="clin@chartnav.local"
        me={CLINICIAN}
        patientId={1}
        encounterId={200}
      />
    );
    await waitFor(() =>
      expect(screen.getByTestId("imaging-studies")).toBeInTheDocument()
    );

    // The disclaimer subtitle intentionally states what ChartNav
    // does NOT do. Strip it from the scan so the negative-assertion
    // copy doesn't trip the vocabulary check.
    const subtitle = container.querySelector(
      ".imaging-pipeline__subtitle"
    ) as HTMLElement | null;
    const subtitleText = (subtitle?.textContent ?? "").toLowerCase();
    const fullText = (container.textContent ?? "").toLowerCase();
    const text = fullText.replace(subtitleText, "");

    for (const banned of [
      "cirrus",
      "spectralis",
      "triton",
      "optos",
      "iolmaster",
      "topcon",
      "humphrey",
      "auto-interpret",
      "autonomous",
      "auto-diagnose",
      "auto-grade",
      "place order",
      "send referral",
      "submit referral",
      "send to patient",
      "patient message",
      "billing",
      "claim",
      "insurance",
      "copay",
      "co-pay",
      "deductible",
      "cpt",
      "icd-10",
      "icd10",
      "remit",
      "eob",
      "hipaa compliant",
    ]) {
      expect(text).not.toContain(banned);
    }

    // Defensive: no button offers a forbidden action.
    const buttons = Array.from(container.querySelectorAll("button"));
    const buttonTexts = buttons.map((b) =>
      (b.textContent ?? "").toLowerCase()
    );
    for (const forbidden of [
      "place order",
      "send referral",
      "send to patient",
      "submit claim",
      "billing",
    ]) {
      expect(buttonTexts.some((t) => t.includes(forbidden))).toBe(false);
    }
  });
});
