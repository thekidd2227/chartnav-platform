// Phase 88 — Imaging Metadata Review Linkage panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/imaging-metadata/imagingMetadataApi", () => ({
  getImagingMetadata: vi.fn(),
  patchImagingMetadataReview: vi.fn(),
}));

import {
  getImagingMetadata,
  patchImagingMetadataReview,
} from "../features/imaging-metadata/imagingMetadataApi";
import { ImagingMetadataPanel } from "../features/imaging-metadata/ImagingMetadataPanel";
import type {
  ImagingMetadataItem,
  ImagingMetadataResponse,
} from "../features/imaging-metadata/imagingMetadataTypes";

const DISCLOSURE =
  "Imaging metadata only. ChartNav does not interpret images, does not " +
  "infer findings, does not autonomously classify modality or laterality, " +
  "and does not recommend treatment or surgery. Provider review required.";

function item(over: Partial<ImagingMetadataItem> = {}): ImagingMetadataItem {
  return {
    id: 1,
    organization_id: 1,
    patient_id: 1,
    encounter_id: 1,
    modality: "oct_macula",
    modality_group: "oct",
    laterality: "OD",
    acquisition_date: "2026-06-09T14:00:00Z",
    device_manufacturer: "Heidelberg",
    device_model: "Spectralis",
    source_system: "OCT cart 1",
    review_status: "uploaded",
    reviewed_by_user_id: null,
    reviewed_by_display: null,
    reviewed_by_role: null,
    reviewed_at: null,
    created_at: "2026-06-09T14:05:00Z",
    updated_at: "2026-06-09T14:05:00Z",
    metadata_hash:
      "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    ...over,
  };
}

function emptyResponse(): ImagingMetadataResponse {
  return {
    encounter_id: 1,
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    generated_at: "2026-06-10T10:00:00Z",
    demo_mode: true,
    items: [],
    by_modality_group: {} as any,
    counts: { total: 0, reviewed: 0, unreviewed: 0 },
    modality_groups_present: [],
    disclosure: DISCLOSURE,
  };
}

function populatedResponse(): ImagingMetadataResponse {
  const a = item({ id: 1, modality: "oct_macula", modality_group: "oct" });
  const b = item({
    id: 2,
    modality: "visual_field_24_2",
    modality_group: "visual_field",
    laterality: "OS",
    review_status: "reviewed",
    reviewed_by_user_id: 5,
    reviewed_by_display: "Casey Clinician",
    reviewed_by_role: "clinician",
    reviewed_at: "2026-06-10T09:00:00Z",
    metadata_hash:
      "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
  });
  return {
    ...emptyResponse(),
    items: [b, a],
    by_modality_group: {
      oct: [a],
      visual_field: [b],
    } as any,
    counts: { total: 2, reviewed: 1, unreviewed: 1 },
    modality_groups_present: ["oct", "visual_field"],
  };
}

beforeEach(() => {
  vi.mocked(getImagingMetadata).mockReset();
  vi.mocked(patchImagingMetadataReview).mockReset();
});

describe("ImagingMetadataPanel — base render", () => {
  it("renders header, banner, refresh button", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(emptyResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-panel"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("imaging-metadata-banner").textContent).toMatch(
      /Imaging metadata only/i,
    );
    expect(screen.getByTestId("imaging-metadata-banner").textContent).toMatch(
      /does not interpret images/i,
    );
    expect(screen.getByTestId("imaging-metadata-banner").textContent).toMatch(
      /does not autonomously classify/i,
    );
    expect(
      screen.getByTestId("imaging-metadata-refresh-btn"),
    ).toBeInTheDocument();
  });

  it("renders counts", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(populatedResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-counts"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("imaging-metadata-count-total").textContent,
    ).toMatch(/Total:\s*2/);
    expect(
      screen.getByTestId("imaging-metadata-count-reviewed").textContent,
    ).toMatch(/Reviewed:\s*1/);
    expect(
      screen.getByTestId("imaging-metadata-count-unreviewed").textContent,
    ).toMatch(/Awaiting review:\s*1/);
  });
});

describe("ImagingMetadataPanel — empty state", () => {
  it("renders empty callout when no items are present", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(emptyResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("imaging-metadata-empty")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("imaging-metadata-empty").textContent,
    ).toMatch(/never blocks signing/i);
  });
});

describe("ImagingMetadataPanel — populated rendering", () => {
  it("renders rows with status pill, device, source, and reviewer", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(populatedResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-row-1"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("imaging-metadata-modality-1").textContent,
    ).toMatch(/oct_macula · OD/);
    expect(
      screen.getByTestId("imaging-metadata-status-1").textContent,
    ).toMatch(/Uploaded/i);
    expect(
      screen.getByTestId("imaging-metadata-status-2").textContent,
    ).toMatch(/Reviewed/i);
    expect(
      screen.getByTestId("imaging-metadata-device-1").textContent,
    ).toMatch(/Heidelberg/);
    expect(
      screen.getByTestId("imaging-metadata-source-1").textContent,
    ).toMatch(/OCT cart 1/);
    expect(
      screen.getByTestId("imaging-metadata-reviewer-2").textContent,
    ).toMatch(/Casey Clinician/);
    expect(
      screen.getByTestId("imaging-metadata-hash-1").textContent,
    ).toMatch(/metadata_hash:/);
  });

  it("only shows Mark reviewed for unreviewed rows", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(populatedResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-row-1"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("imaging-metadata-review-btn-1"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("imaging-metadata-review-btn-2")).toBeNull();
  });
});

describe("ImagingMetadataPanel — interactions", () => {
  it("PATCHes review on click and refetches", async () => {
    vi.mocked(getImagingMetadata)
      .mockResolvedValueOnce(populatedResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(patchImagingMetadataReview).mockResolvedValueOnce(
      item({ id: 1, review_status: "reviewed" }),
    );

    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-review-btn-1"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("imaging-metadata-review-btn-1"),
    );

    await waitFor(() =>
      expect(patchImagingMetadataReview).toHaveBeenCalledTimes(1),
    );
    expect(vi.mocked(patchImagingMetadataReview).mock.calls[0]![0]).toBe(1);
    await waitFor(() =>
      expect(getImagingMetadata).toHaveBeenCalledTimes(2),
    );
  });

  it("surfaces review errors in an inline banner", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(populatedResponse());
    vi.mocked(patchImagingMetadataReview).mockRejectedValueOnce(
      new Error("forbidden"),
    );

    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-review-btn-1"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("imaging-metadata-review-btn-1"),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-review-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("imaging-metadata-review-error").textContent,
    ).toMatch(/forbidden/);
  });

  it("refresh button refetches", async () => {
    vi.mocked(getImagingMetadata)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());

    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("imaging-metadata-empty")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("imaging-metadata-refresh-btn"));

    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-row-1"),
      ).toBeInTheDocument(),
    );
    expect(getImagingMetadata).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getImagingMetadata).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("imaging-metadata-error").textContent,
    ).toMatch(/HTTP 503/);
  });
});

describe("ImagingMetadataPanel — safety contract", () => {
  it("renders disclosure with explicit boundary language", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(populatedResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-disclosure"),
      ).toBeInTheDocument(),
    );
    const d = screen.getByTestId("imaging-metadata-disclosure");
    expect(d.textContent).toMatch(/does not interpret images/i);
    expect(d.textContent).toMatch(/does not infer findings/i);
    expect(d.textContent).toMatch(/does not autonomously classify/i);
    expect(d.textContent).toMatch(/Provider review required/i);
  });

  it("does NOT render forbidden image-interpretation phrases", async () => {
    vi.mocked(getImagingMetadata).mockResolvedValueOnce(populatedResponse());
    render(<ImagingMetadataPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("imaging-metadata-row-1"),
      ).toBeInTheDocument(),
    );
    const disclosure = (
      screen.getByTestId("imaging-metadata-disclosure").textContent ?? ""
    ).toLowerCase();
    const banner = (
      screen.getByTestId("imaging-metadata-banner").textContent ?? ""
    ).toLowerCase();
    const body = (document.body.textContent ?? "")
      .toLowerCase()
      .replace(disclosure, "")
      .replace(banner, "");
    for (const forbidden of [
      "image interpreted",
      "ai interpretation",
      "auto-classified",
      "drusen detected",
      "rnfl thinning detected",
      "vf defect detected",
      "macular edema detected",
      "diagnosis confirmed",
      "treatment recommended",
      "anti-vegf recommended",
      "findings:",
      "impression:",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
