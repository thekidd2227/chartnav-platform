import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    getPatientPreVisitBrief: vi.fn(),
    generatePatientPreVisitBrief: vi.fn(),
  };
});

import {
  ApiError,
  PreVisitBrief,
  generatePatientPreVisitBrief,
  getPatientPreVisitBrief,
} from "../api";
import { PreVisitBriefPanel } from "../PreVisitBriefPanel";

const mockedGet = vi.mocked(getPatientPreVisitBrief);
const mockedGenerate = vi.mocked(generatePatientPreVisitBrief);

function makeBrief(overrides: Partial<PreVisitBrief> = {}): PreVisitBrief {
  return {
    patient_id: 7,
    brief_status: "generated",
    last_visit_summary:
      "Most recent encounter on 2026-05-01 with Dr. Carter (status: in_progress).",
    active_issues: [],
    retinal_artifact_summary: {
      total: 0,
      signed_count: 0,
      unsigned_count: 0,
      has_unsigned_drafts: false,
      latest_signed: null,
    },
    recent_scribe_session_summary: { session_id: null, status: "none" },
    patient_summary_context: { summary_id: null, status: "none" },
    pending_items: [],
    suggested_review_items: [],
    data_gaps: [
      "No scribe sessions on file for this patient.",
      "No retinal artifacts on file for this patient.",
      "No patient-friendly summaries on file for this patient.",
    ],
    source_counts: {
      encounters: 1,
      workflow_events: 3,
      scribe_sessions: 0,
      scribe_sessions_finalized: 0,
      retinal_artifacts: 0,
      retinal_artifacts_signed: 0,
      patient_summaries: 0,
      patient_summaries_finalized: 0,
    },
    generated_at: "2026-05-05T18:00:00+00:00",
    notice:
      "Pre-visit brief — provider review required. This brief summarizes available ChartNav records and may be incomplete.",
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <PreVisitBriefPanel
      identity="clin@chartnav.local"
      patientId={7}
      encounterId={42}
    />
  );
}

describe("PreVisitBriefPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the provider-review banner copy", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    renderPanel();
    const banner = await screen.findByTestId("pre-visit-brief-banner-copy");
    expect(banner).toHaveTextContent(/provider review required/i);
    expect(banner).toHaveTextContent(/may be incomplete/i);
  });

  it("auto-loads the brief on mount and shows the timestamp + counts", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    renderPanel();

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("clin@chartnav.local", 7);
    });
    expect(
      await screen.findByTestId("pre-visit-brief-generated-at")
    ).toHaveTextContent("2026-05-05T18:00:00+00:00");
    expect(screen.getByTestId("pre-visit-brief-counts")).toBeInTheDocument();
    // Sorted-key count tiles are rendered with stable testids per key.
    expect(
      screen.getByTestId("pre-visit-brief-count-encounters")
    ).toHaveTextContent("1");
    expect(
      screen.getByTestId("pre-visit-brief-count-scribe_sessions")
    ).toHaveTextContent("0");
  });

  it("clicking Generate calls the POST endpoint and updates display", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    mockedGenerate.mockResolvedValueOnce(
      makeBrief({
        generated_at: "2026-05-05T19:30:00+00:00",
        source_counts: {
          encounters: 2,
          workflow_events: 5,
          scribe_sessions: 1,
          scribe_sessions_finalized: 1,
          retinal_artifacts: 1,
          retinal_artifacts_signed: 1,
          patient_summaries: 1,
          patient_summaries_finalized: 1,
        },
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("pre-visit-brief-generated-at");

    await user.click(screen.getByTestId("pre-visit-brief-generate"));

    await waitFor(() => {
      expect(mockedGenerate).toHaveBeenCalledWith("clin@chartnav.local", 7);
    });
    expect(
      screen.getByTestId("pre-visit-brief-generated-at")
    ).toHaveTextContent("2026-05-05T19:30:00+00:00");
    expect(
      screen.getByTestId("pre-visit-brief-count-scribe_sessions_finalized")
    ).toHaveTextContent("1");
    const banner = screen.getByTestId("pre-visit-brief-banner");
    expect(banner).toHaveTextContent(/regenerated/i);
  });

  it("displays last-visit summary, retinal block, and scribe excerpts", async () => {
    mockedGet.mockResolvedValueOnce(
      makeBrief({
        retinal_artifact_summary: {
          total: 2,
          signed_count: 1,
          unsigned_count: 1,
          has_unsigned_drafts: true,
          latest_signed: {
            id: 100,
            title: "OD/OS macula drawing",
            signed_at: "2026-05-04T12:00:00+00:00",
            version_number: 1,
            encounter_id: 42,
          },
        },
        recent_scribe_session_summary: {
          session_id: 50,
          status: "reviewed",
          chief_complaint_excerpt: "blurry vision OD",
          plan_excerpt: "refraction next visit",
        },
        patient_summary_context: {
          summary_id: 12,
          status: "finalized",
          source_kind: "finalized",
          plain_language_excerpt: "Visit recap text…",
          key_findings_count: 2,
          next_steps_count: 1,
        },
      })
    );
    renderPanel();

    expect(
      await screen.findByTestId("pre-visit-brief-last-visit")
    ).toHaveTextContent(/Dr. Carter/);
    expect(
      screen.getByTestId("pre-visit-brief-retinal-latest-signed")
    ).toHaveTextContent("OD/OS macula drawing");
    const scribe = screen.getByTestId("pre-visit-brief-scribe");
    expect(scribe).toHaveTextContent("blurry vision OD");
    expect(scribe).toHaveTextContent("refraction next visit");
    const summary = screen.getByTestId("pre-visit-brief-summary");
    expect(summary).toHaveTextContent("finalized");
    expect(summary).toHaveTextContent("Visit recap text");
  });

  it("renders pending and suggested-review lists", async () => {
    mockedGet.mockResolvedValueOnce(
      makeBrief({
        pending_items: [
          { kind: "scribe_session", id: 50, status: "ready_for_review" },
          { kind: "patient_summary", id: 12, status: "draft" },
        ],
        suggested_review_items: [
          {
            kind: "scribe_session",
            id: 50,
            reason: "scribe session ready for provider review",
          },
          {
            kind: "patient_summary",
            id: 12,
            reason: "patient summary draft awaiting review",
          },
        ],
      })
    );
    renderPanel();

    const pending = await screen.findByTestId("pre-visit-brief-pending");
    expect(pending).toHaveTextContent("scribe_session #50");
    expect(pending).toHaveTextContent("patient_summary #12");
    const suggested = screen.getByTestId("pre-visit-brief-suggested");
    expect(suggested).toHaveTextContent("ready for provider review");
    expect(suggested).toHaveTextContent("draft awaiting review");
  });

  it("renders explicit data gaps when sources are missing", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    renderPanel();
    const gaps = await screen.findByTestId("pre-visit-brief-gaps");
    expect(gaps).toHaveTextContent(/No scribe sessions on file/);
    expect(gaps).toHaveTextContent(/No retinal artifacts on file/);
    expect(gaps).toHaveTextContent(/No patient-friendly summaries on file/);
  });

  it("handles a patient with completely empty history (still generates)", async () => {
    mockedGet.mockResolvedValueOnce(
      makeBrief({
        last_visit_summary: null,
        source_counts: {
          encounters: 0,
          workflow_events: 0,
          scribe_sessions: 0,
          scribe_sessions_finalized: 0,
          retinal_artifacts: 0,
          retinal_artifacts_signed: 0,
          patient_summaries: 0,
          patient_summaries_finalized: 0,
        },
        data_gaps: [
          "No recent encounters on file for this patient.",
          "No scribe sessions on file for this patient.",
          "No retinal artifacts on file for this patient.",
          "No patient-friendly summaries on file for this patient.",
        ],
      })
    );
    renderPanel();

    expect(
      await screen.findByTestId("pre-visit-brief-last-visit")
    ).toHaveTextContent("—");
    expect(
      screen.getByTestId("pre-visit-brief-active-issues-empty")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("pre-visit-brief-pending-empty")
    ).toBeInTheDocument();
  });

  it("API error shows a safe banner message", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    mockedGenerate.mockRejectedValueOnce(
      new ApiError(403, "role_forbidden", "role 'reviewer' cannot generate")
    );
    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("pre-visit-brief-generated-at");

    await user.click(screen.getByTestId("pre-visit-brief-generate"));

    const banner = await screen.findByTestId("pre-visit-brief-banner");
    expect(banner).toHaveTextContent(/Generate failed/);
    expect(banner).toHaveTextContent(/role_forbidden/);
    // No leakage of autonomous-action language.
    expect(banner.textContent).not.toMatch(/autonomous/i);
  });

  it("does not contain autonomous-diagnosis or external-LLM language", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    renderPanel();
    await screen.findByTestId("pre-visit-brief-generated-at");
    const root = screen.getByTestId("pre-visit-brief-panel");
    expect(root.textContent).not.toMatch(/autonomous/i);
    expect(root.textContent).not.toMatch(/diagnos/i);
    expect(root.textContent).not.toMatch(/openai|anthropic|gpt|llm/i);
  });

  it("does not render any patient-send button or automatic-send action", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    renderPanel();
    await screen.findByTestId("pre-visit-brief-generated-at");
    expect(
      screen.queryByRole("button", { name: /send to patient/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /portal/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /email/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /sms/i })
    ).not.toBeInTheDocument();
  });

  it("does not render any orders or coding action", async () => {
    mockedGet.mockResolvedValueOnce(makeBrief());
    renderPanel();
    await screen.findByTestId("pre-visit-brief-generated-at");
    const root = screen.getByTestId("pre-visit-brief-panel");
    expect(root.textContent).not.toMatch(/place order/i);
    expect(root.textContent).not.toMatch(/coding/i);
    expect(root.textContent).not.toMatch(/icd-?10|cpt code/i);
    expect(
      screen.queryByRole("button", { name: /order/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /code/i })
    ).not.toBeInTheDocument();
  });
});
