// Phase 76 — Retina Visit Summary panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/retina-summary/retinaSummaryApi", () => ({
  getRetinaVisitSummary: vi.fn(),
}));

import { getRetinaVisitSummary } from "../features/retina-summary/retinaSummaryApi";
import { RetinaVisitSummaryPanel } from "../features/retina-summary/RetinaVisitSummaryPanel";
import type { RetinaVisitSummary } from "../features/retina-summary/retinaSummaryTypes";

const emptySummary = (over: Partial<RetinaVisitSummary> = {}): RetinaVisitSummary => ({
  encounter_id: 1,
  patient_id: 1,
  organization_id: 1,
  patient_identifier: "PT-1001",
  patient_name: "Morgan Lee",
  encounter_status: "in_progress",
  encounter_started_at: "2026-05-19T06:00:00Z",
  demo_mode: true,
  vitals: { count: 0, latest_id: null, latest_status: null },
  visit_draft: { count: 0, latest_id: null, latest_status: null },
  fundus: { count: 0, latest_id: null, latest_status: null },
  blockers: [
    { kind: "missing_vitals", message: "No vitals workup recorded yet." },
    { kind: "missing_visit_draft", message: "No visit draft yet." },
    { kind: "missing_fundus", message: "No fundus chart drafted yet." },
  ],
  role_capabilities: {
    role: "clinician",
    can_review: true,
    can_sign: true,
    can_create_intake: true,
    explainer: "Clinician can review and sign clinical artifacts.",
  },
  evidence_timeline: [],
  audit_disclosure:
    "ChartNav records metadata-only audit events: who created, reviewed, and signed each artifact, and when. The audit trail does not store clinical free text (no transcripts, BP/IOP/VA values, chief complaint, HPI, or findings text).",
  ...over,
});

const fullSummary = (): RetinaVisitSummary => ({
  ...emptySummary(),
  vitals: {
    count: 1,
    latest_id: 5,
    latest_status: "signed",
    latest_signed_at: "2026-05-19T07:00:00Z",
    latest_warning_count: 0,
  },
  visit_draft: {
    count: 1,
    latest_id: 3,
    latest_status: "finalized",
    latest_finalized_at: "2026-05-19T07:05:00Z",
  },
  fundus: {
    count: 1,
    latest_id: 7,
    latest_status: "signed",
    latest_signed_at: "2026-05-19T07:10:00Z",
    latest_warning_count: 1,
    latest_element_count: 3,
    latest_laterality: "OD",
  },
  blockers: [],
  evidence_timeline: [
    {
      artifact_type: "vitals_workup",
      event_type: "created",
      timestamp: "2026-05-19T06:30:00Z",
      ref_id: 5,
      actor_display_name: "Taylor Technician",
      actor_role: "technician",
      warning_count: 0,
    },
    {
      artifact_type: "vitals_workup",
      event_type: "signed",
      timestamp: "2026-05-19T07:00:00Z",
      ref_id: 5,
      actor_display_name: "Casey Clinician",
      actor_role: "clinician",
      warning_count: 0,
    },
    {
      artifact_type: "fundus_chart",
      event_type: "signed",
      timestamp: "2026-05-19T07:10:00Z",
      ref_id: 7,
      actor_display_name: "Casey Clinician",
      actor_role: "clinician",
      laterality: "OD",
      element_count: 3,
      warning_count: 1,
    },
  ],
});

beforeEach(() => {
  vi.mocked(getRetinaVisitSummary).mockReset();
});

describe("RetinaVisitSummaryPanel — baseline", () => {
  it("renders patient identity, encounter id, and status from API response", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(emptySummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-summary-encounter-meta"),
      ).toBeInTheDocument(),
    );
    const meta = screen.getByTestId("retina-summary-encounter-meta");
    expect(meta.textContent).toMatch(/Morgan Lee/);
    expect(meta.textContent).toMatch(/PT-1001/);
    expect(meta.textContent).toMatch(/encounter #1/);
    expect(meta.textContent).toMatch(/in_progress/);
  });

  it("renders three artifact cards with their status pills", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(emptySummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-card-vitals")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("retina-summary-card-vitals")).toBeInTheDocument();
    expect(
      screen.getByTestId("retina-summary-card-visitdraft"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("retina-summary-card-fundus")).toBeInTheDocument();
    // All None yet because every count is 0
    expect(
      screen.getByTestId("retina-summary-card-vitals-status").textContent,
    ).toMatch(/None yet/i);
  });

  it("renders blockers list with the right kinds when artifacts are missing", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(emptySummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-blockers")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("retina-summary-blocker-missing_vitals"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("retina-summary-blocker-missing_visit_draft"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("retina-summary-blocker-missing_fundus"),
    ).toBeInTheDocument();
  });

  it("renders 'all signed' empty-blockers banner when no blockers", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(fullSummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-summary-blockers-empty"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("retina-summary-blockers-empty").textContent,
    ).toMatch(/All clinical artifacts are signed and locked/i);
  });
});

describe("RetinaVisitSummaryPanel — role + audit", () => {
  it("renders the role explainer from the API response", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(emptySummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-role")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("retina-summary-role-explainer").textContent,
    ).toMatch(/Clinician can review and sign/i);
  });

  it("renders the metadata-only audit disclosure verbatim", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(emptySummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-summary-audit-disclosure"),
      ).toBeInTheDocument(),
    );
    const note = screen.getByTestId("retina-summary-audit-disclosure");
    expect(note.textContent).toMatch(/metadata-only audit events/i);
    expect(note.textContent).toMatch(/does not store clinical free text/i);
  });

  it("does NOT render any forbidden clinical free-text fragments", async () => {
    // Even with a full summary, the rendered DOM must not contain
    // transcript/BP/IOP/findings text.
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(fullSummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-timeline")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "transcript_text",
      "draft_note",
      "findings_json",
      "drawing_json",
      "technician_notes",
      "blood pressure value",
      "intraocular pressure value",
      "visual acuity od:",
    ]) {
      expect(body, `forbidden phrase appeared: ${forbidden}`).not.toContain(
        forbidden,
      );
    }
  });
});

describe("RetinaVisitSummaryPanel — timeline + interaction", () => {
  it("renders timeline events with artifact type, ref id, actor, and role", async () => {
    vi.mocked(getRetinaVisitSummary).mockResolvedValueOnce(fullSummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-timeline")).toBeInTheDocument(),
    );
    const e0 = screen.getByTestId("retina-summary-event-0");
    expect(e0.textContent).toMatch(/Vitals/);
    expect(e0.textContent).toMatch(/#5/);
    expect(e0.textContent).toMatch(/Taylor Technician/);
    expect(e0.textContent).toMatch(/technician/);
    const e2 = screen.getByTestId("retina-summary-event-2");
    expect(e2.textContent).toMatch(/Fundus/);
    expect(e2.textContent).toMatch(/OD/);
  });

  it("refresh button refetches the summary", async () => {
    vi.mocked(getRetinaVisitSummary)
      .mockResolvedValueOnce(emptySummary())
      .mockResolvedValueOnce(fullSummary());
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-blockers")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("retina-summary-refresh-btn"));
    await waitFor(() =>
      expect(
        screen.getByTestId("retina-summary-blockers-empty"),
      ).toBeInTheDocument(),
    );
    expect(getRetinaVisitSummary).toHaveBeenCalledTimes(2);
  });

  it("error from API surfaces a retry-safe error banner", async () => {
    vi.mocked(getRetinaVisitSummary).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<RetinaVisitSummaryPanel encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("retina-summary-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("retina-summary-error").textContent).toMatch(
      /HTTP 503/,
    );
    expect(screen.getByTestId("retina-summary-refresh-btn")).toBeInTheDocument();
  });
});
