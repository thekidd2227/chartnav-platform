/**
 * Phase 12 — End-to-end clinical workflow smoke (frontend).
 *
 * Mounts NoteWorkspace with a numeric patientId (so all Phase 5B / 8 /
 * 9 / 10 / 11 panels render) and asserts:
 *   - every panel mounts and shows its safety copy
 *   - the workflow drives the right API calls in the right order
 *   - the panels surface no order / coding / referral / patient-
 *     messaging / autonomous-diagnosis / external-LLM language
 *   - one mocked API error renders a safe banner without raw stack
 *
 * This file does not introduce new product behavior — it verifies
 * existing wiring across phases.
 */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../audioRecorder", async () => {
  const actual = await vi.importActual<typeof import("../audioRecorder")>(
    "../audioRecorder"
  );
  return {
    ...actual,
    detectBrowserCapture: vi.fn(),
    startBrowserRecording: vi.fn(),
  };
});

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    // existing-workspace deps — must mock anything NoteWorkspace touches
    // on mount.
    listEncounterInputs: vi.fn(),
    listEncounterNotes: vi.fn(),
    getNoteVersion: vi.fn(),
    getPlatform: vi.fn(),
    listMyQuickComments: vi.fn(),
    listMyQuickCommentFavorites: vi.fn(),
    listMyClinicalShortcutFavorites: vi.fn(),

    // Phase 5B — eye diagram panel.
    listPatientEyeDiagrams: vi.fn(),
    proposeRetinalFromFindings: vi.fn(),

    // Phase 8 — scribe sessions.
    listPatientScribeSessions: vi.fn(),
    getPatientScribeSession: vi.fn(),
    createPatientScribeSession: vi.fn(),
    processPatientScribeSession: vi.fn(),
    reviewPatientScribeSession: vi.fn(),
    finalizePatientScribeSession: vi.fn(),

    // Phase 9 — patient summaries.
    listPatientSummaries: vi.fn(),
    getPatientSummary: vi.fn(),
    createPatientSummary: vi.fn(),
    reviewPatientSummary: vi.fn(),
    finalizePatientSummary: vi.fn(),

    // Phase 10 — pre-visit briefs.
    getPatientPreVisitBrief: vi.fn(),
    generatePatientPreVisitBrief: vi.fn(),

    // Phase 11 — provider action items.
    listProviderActionItems: vi.fn(),
    generateProviderActionItems: vi.fn(),
    acceptProviderActionItem: vi.fn(),
    dismissProviderActionItem: vi.fn(),
    completeProviderActionItem: vi.fn(),
  };
});

import * as api from "../api";
import * as audioRecorder from "../audioRecorder";
import { NoteWorkspace } from "../NoteWorkspace";

const CLIN: api.Me = {
  user_id: 2,
  email: "clin@chartnav.local",
  full_name: "Casey Clinician",
  role: "clinician",
  organization_id: 1,
};

const PATIENT_ID = 7;
const ENCOUNTER_ID = 42;

function makeScribeSession(
  overrides: Partial<api.ScribeSession> = {}
): api.ScribeSession {
  return {
    id: 50,
    organization_id: 1,
    patient_id: PATIENT_ID,
    encounter_id: ENCOUNTER_ID,
    created_by_user_id: 2,
    status: "draft",
    input_mode: "pasted_text",
    source_text: null,
    transcript_text: null,
    draft_note_text: null,
    structured_note_json: {},
    linked_artifact_id: null,
    review_notes: null,
    finalized_at: null,
    reviewed_at: null,
    reviewed_by_user_id: null,
    discarded_at: null,
    created_at: "2026-05-06T03:00:00+00:00",
    updated_at: "2026-05-06T03:00:00+00:00",
    is_terminal: false,
    ...overrides,
  };
}

function makePatientSummary(
  overrides: Partial<api.PatientSummary> = {}
): api.PatientSummary {
  return {
    id: 21,
    organization_id: 1,
    patient_id: PATIENT_ID,
    encounter_id: ENCOUNTER_ID,
    scribe_session_id: 50,
    created_by_user_id: 2,
    reviewed_by_user_id: null,
    status: "draft",
    plain_language_summary: "Visit summary placeholder.",
    key_findings: [],
    next_steps: [],
    questions: [],
    limitations_notice:
      "This summary is a draft for provider review and may be incomplete.",
    review_notes: null,
    finalized_at: null,
    reviewed_at: null,
    discarded_at: null,
    created_at: "2026-05-06T03:00:00+00:00",
    updated_at: "2026-05-06T03:00:00+00:00",
    is_terminal: false,
    ...overrides,
  };
}

function makeBrief(overrides: Partial<api.PreVisitBrief> = {}): api.PreVisitBrief {
  return {
    patient_id: PATIENT_ID,
    brief_status: "generated",
    last_visit_summary:
      "Most recent encounter on 2026-05-04 with Dr. Carter (status: in_progress).",
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
    data_gaps: [],
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
    generated_at: "2026-05-06T03:00:00+00:00",
    notice:
      "Pre-visit brief — provider review required. This brief summarizes available ChartNav records and may be incomplete.",
    ...overrides,
  };
}

function makeAction(
  overrides: Partial<api.ProviderActionItem> = {}
): api.ProviderActionItem {
  return {
    id: 1001,
    organization_id: 1,
    patient_id: PATIENT_ID,
    encounter_id: ENCOUNTER_ID,
    source_type: "scribe_session",
    source_id: 50,
    action_type: "review_scribe_session",
    priority: "medium",
    title: "Review scribe session #50",
    reason: "A scribe session is ready for provider review.",
    status: "suggested",
    created_by_system: true,
    generated_batch_id: "batch-x",
    accepted_by_user_id: null,
    dismissed_by_user_id: null,
    completed_by_user_id: null,
    accepted_at: null,
    dismissed_at: null,
    completed_at: null,
    created_at: "2026-05-06T03:00:00+00:00",
    updated_at: "2026-05-06T03:00:00+00:00",
    is_terminal: false,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();

  // NoteWorkspace mount-time deps. None of these have to be rich for
  // the smoke — the panels under test mount independently of the
  // tier-3 note draft state.
  (api.listEncounterInputs as any).mockResolvedValue([]);
  (api.listEncounterNotes as any).mockResolvedValue([]);
  (api.getNoteVersion as any).mockResolvedValue(null);
  (api.getPlatform as any).mockResolvedValue({
    platform_mode: "standalone",
    integration_adapter: "native",
  });
  (api.listMyQuickComments as any).mockResolvedValue([]);
  (api.listMyQuickCommentFavorites as any).mockResolvedValue([]);
  (api.listMyClinicalShortcutFavorites as any).mockResolvedValue([]);

  // Audio recorder defaults — workspace asks at mount; the smoke
  // doesn't exercise the audio path but the shape must match what
  // the workspace renders.
  (audioRecorder.detectBrowserCapture as any).mockReturnValue({
    supported: true,
    pickedMime: "audio/webm;codecs=opus",
    pickedExt: ".webm",
  });
  (audioRecorder.startBrowserRecording as any).mockReset();

  // Phase-panel default fixtures.
  (api.listPatientEyeDiagrams as any).mockResolvedValue({ items: [], total: 0 });
  (api.listPatientScribeSessions as any).mockResolvedValue({
    items: [],
    total: 0,
  });
  (api.listPatientSummaries as any).mockResolvedValue({
    items: [],
    total: 0,
  });
  (api.getPatientPreVisitBrief as any).mockResolvedValue(makeBrief());
  (api.listProviderActionItems as any).mockResolvedValue({
    items: [],
    total: 0,
  });
});

function renderWorkspace() {
  return render(
    <NoteWorkspace
      identity={CLIN.email}
      me={CLIN}
      encounterId={ENCOUNTER_ID}
      patientId={PATIENT_ID}
      patientDisplay="Morgan Lee"
      providerDisplay="Dr. Carter"
    />
  );
}

describe("ClinicalWorkflowSmoke — Phase 12", () => {
  it("mounts every clinical panel section when patientId is numeric", async () => {
    renderWorkspace();
    // Each panel section is wrapped with its own data-testid in
    // NoteWorkspace; mounting them confirms the integration wiring.
    await screen.findByTestId("eye-diagram-section");
    await screen.findByTestId("scribe-session-section");
    await screen.findByTestId("patient-summary-section");
    await screen.findByTestId("pre-visit-brief-section");
    await screen.findByTestId("provider-action-items-section");
    // And each panel root mounts.
    expect(screen.getByTestId("scribe-session-panel")).toBeInTheDocument();
    expect(screen.getByTestId("patient-summary-panel")).toBeInTheDocument();
    expect(screen.getByTestId("pre-visit-brief-panel")).toBeInTheDocument();
    expect(
      screen.getByTestId("provider-action-items-panel")
    ).toBeInTheDocument();
  });

  it("each panel surfaces its provider-review safety copy", async () => {
    renderWorkspace();
    // Phase 8 — scribe session draft notice.
    expect(
      await screen.findByTestId("scribe-session-banner-copy")
    ).toHaveTextContent(/provider review required/i);
    // Phase 9 — patient summary review notice.
    expect(
      screen.getByTestId("patient-summary-banner-copy")
    ).toHaveTextContent(/Do not send to patient/i);
    // Phase 10 — pre-visit brief notice.
    expect(
      screen.getByTestId("pre-visit-brief-banner-copy")
    ).toHaveTextContent(/may be incomplete/i);
    // Phase 11 — provider action queue notice.
    expect(
      screen.getByTestId("provider-action-items-banner-copy")
    ).toHaveTextContent(/take action automatically/i);
  });

  it("running the full create→process→review→finalize→summary→brief→actions flow drives the right API calls", async () => {
    // Scribe lifecycle.
    (api.createPatientScribeSession as any).mockResolvedValueOnce(
      makeScribeSession({ id: 50, status: "draft" })
    );
    (api.processPatientScribeSession as any).mockResolvedValueOnce(
      makeScribeSession({ id: 50, status: "ready_for_review" })
    );
    (api.reviewPatientScribeSession as any).mockResolvedValueOnce(
      makeScribeSession({ id: 50, status: "reviewed" })
    );
    (api.finalizePatientScribeSession as any).mockResolvedValueOnce(
      makeScribeSession({
        id: 50,
        status: "finalized",
        is_terminal: true,
        finalized_at: "2026-05-06T03:01:00+00:00",
      })
    );

    // Patient summary lifecycle.
    (api.createPatientSummary as any).mockResolvedValueOnce(
      makePatientSummary({ id: 21, status: "draft" })
    );

    // Pre-visit brief generate.
    (api.generatePatientPreVisitBrief as any).mockResolvedValueOnce(
      makeBrief({ generated_at: "2026-05-06T03:02:00+00:00" })
    );

    // Provider actions.
    (api.generateProviderActionItems as any).mockResolvedValueOnce({
      batch_id: "batch-x",
      generated_count: 1,
      created_count: 1,
      reused_count: 0,
      items: [makeAction()],
    });

    renderWorkspace();
    const user = userEvent.setup();
    await screen.findByTestId("scribe-session-panel");

    // 1) Create a scribe session.
    fireEvent.change(
      screen.getByTestId<HTMLTextAreaElement>("scribe-session-source-text"),
      { target: { value: "Chief complaint: blurry vision OD." } }
    );
    await user.click(screen.getByTestId("scribe-session-create"));
    await waitFor(() => {
      expect(api.createPatientScribeSession).toHaveBeenCalledTimes(1);
    });

    // 2) Process it.
    await user.click(screen.getByTestId("scribe-session-process"));
    await waitFor(() => {
      expect(api.processPatientScribeSession).toHaveBeenCalledTimes(1);
    });

    // 3) Review it.
    await user.click(screen.getByTestId("scribe-session-review"));
    await waitFor(() => {
      expect(api.reviewPatientScribeSession).toHaveBeenCalledTimes(1);
    });

    // 4) Finalize it.
    await user.click(screen.getByTestId("scribe-session-finalize"));
    await waitFor(() => {
      expect(api.finalizePatientScribeSession).toHaveBeenCalledTimes(1);
    });

    // 5) Create a patient summary.
    await user.click(screen.getByTestId("patient-summary-create"));
    await waitFor(() => {
      expect(api.createPatientSummary).toHaveBeenCalledTimes(1);
    });

    // 6) Regenerate the pre-visit brief.
    await user.click(screen.getByTestId("pre-visit-brief-generate"));
    await waitFor(() => {
      expect(api.generatePatientPreVisitBrief).toHaveBeenCalledTimes(1);
    });

    // 7) Generate provider action items.
    await user.click(screen.getByTestId("provider-action-items-generate"));
    await waitFor(() => {
      expect(api.generateProviderActionItems).toHaveBeenCalledTimes(1);
    });
  });

  it("never renders order / coding / referral / patient-message buttons across panels", async () => {
    // Make the panels show actual rendered items so any forbidden
    // button would surface.
    (api.listProviderActionItems as any).mockResolvedValue({
      items: [makeAction(), makeAction({ id: 1002, status: "accepted" })],
      total: 2,
    });
    (api.listPatientSummaries as any).mockResolvedValue({
      items: [makePatientSummary({ id: 21, status: "draft" })],
      total: 1,
    });
    (api.listPatientScribeSessions as any).mockResolvedValue({
      items: [makeScribeSession({ id: 50, status: "draft" })],
      total: 1,
    });

    renderWorkspace();
    await screen.findByTestId("provider-action-items-panel");

    const forbiddenLabels: RegExp[] = [
      /place order/i,
      /\border\b(?!.*review)/i,
      /coding/i,
      /icd-?10/i,
      /cpt code/i,
      /send referral/i,
      /submit referral/i,
      /send to patient/i,
      /email patient/i,
      /sms patient/i,
      /portal push/i,
      /prescribe/i,
    ];
    for (const label of forbiddenLabels) {
      expect(
        screen.queryByRole("button", { name: label })
      ).not.toBeInTheDocument();
    }
  });

  it("never surfaces autonomous-diagnosis or external-LLM language in any panel root", async () => {
    renderWorkspace();
    const roots = await Promise.all([
      screen.findByTestId("scribe-session-panel"),
      screen.findByTestId("patient-summary-panel"),
      screen.findByTestId("pre-visit-brief-panel"),
      screen.findByTestId("provider-action-items-panel"),
    ]);
    const forbidden = [
      /autonomous/i,
      /openai/i,
      /anthropic/i,
      /\bgpt\b/i,
      /\bllm\b/i,
      /external llm/i,
    ];
    for (const root of roots) {
      const text = root.textContent || "";
      for (const pattern of forbidden) {
        expect(text).not.toMatch(pattern);
      }
    }
  });

  it("a mocked API error renders a safe banner — no raw stack trace, no autonomous-action language", async () => {
    (api.generateProviderActionItems as any).mockRejectedValueOnce(
      new api.ApiError(
        500,
        "internal_error",
        "ChartNav engine could not generate suggestions."
      )
    );
    renderWorkspace();
    const user = userEvent.setup();
    await screen.findByTestId("provider-action-items-panel");
    await user.click(screen.getByTestId("provider-action-items-generate"));

    const banner = await screen.findByTestId("provider-action-items-banner");
    // Friendly, code-driven message — no exception class names, no
    // autonomous-action language.
    expect(banner).toHaveTextContent(/Generate failed/);
    expect(banner).toHaveTextContent(/internal_error/);
    expect(banner.textContent).not.toMatch(/Traceback/);
    expect(banner.textContent).not.toMatch(/at\s+\w+\s+\([^)]+\)/);
    expect(banner.textContent).not.toMatch(/autonomous/i);
  });

  it("each panel safety banner is a negative assertion — and ChartNav itself never renders a 'send to patient' control", async () => {
    // Specific defensive contract: the banner copy on the patient
    // summary panel says "Do not send to patient until finalized".
    // Make sure that's the only place those tokens appear, and that
    // there is no actionable button matching them.
    renderWorkspace();
    const summaryBanner = await screen.findByTestId(
      "patient-summary-banner-copy"
    );
    expect(summaryBanner.textContent).toMatch(/Do not send to patient/i);
    // Likewise the action queue banner is a negative assertion.
    const actionBanner = await screen.findByTestId(
      "provider-action-items-banner-copy"
    );
    expect(actionBanner.textContent).toMatch(/does not create orders/i);
    expect(actionBanner.textContent).toMatch(/send referrals/i);
    expect(actionBanner.textContent).toMatch(/message patients/i);
    // No button labeled with any "send" variant exists.
    expect(
      screen.queryByRole("button", { name: /send to patient/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /send referral/i })
    ).not.toBeInTheDocument();
  });
});
