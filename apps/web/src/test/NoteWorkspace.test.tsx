import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    listEncounterInputs: vi.fn(),
    createEncounterInput: vi.fn(),
    listEncounterNotes: vi.fn(),
    generateNoteVersion: vi.fn(),
    getNoteVersion: vi.fn(),
    patchNoteVersion: vi.fn(),
    submitNoteForReview: vi.fn(),
    signNoteVersion: vi.fn(),
    exportNoteVersion: vi.fn(),
    // Phase 22 — ingestion lifecycle.
    processEncounterInput: vi.fn(),
    retryEncounterInput: vi.fn(),
    // Phase 25 — artifact download. The component triggers a browser
    // anchor-click to actually download; mocking `downloadNoteArtifact`
    // means the test never touches jsdom's blob/anchor plumbing.
    downloadNoteArtifact: vi.fn(),
    // Phase 26 — signed-note transmission. `getPlatform` gates the
    // Transmit button's visibility; `transmitNoteVersion` +
    // `listNoteTransmissions` drive the action + history pane.
    getPlatform: vi.fn(),
    transmitNoteVersion: vi.fn(),
    listNoteTransmissions: vi.fn(),
    // Phase 27 — clinician quick-comment pad.
    listMyQuickComments: vi.fn(),
    createMyQuickComment: vi.fn(),
    updateMyQuickComment: vi.fn(),
    deleteMyQuickComment: vi.fn(),
    // Phase 28 — favorites + usage audit.
    listMyQuickCommentFavorites: vi.fn(),
    favoriteQuickComment: vi.fn(),
    unfavoriteQuickComment: vi.fn(),
    recordQuickCommentUsage: vi.fn(),
  };
});

import * as api from "../api";
import { NoteWorkspace } from "../NoteWorkspace";

const ADMIN: api.Me = {
  user_id: 1,
  email: "admin@chartnav.local",
  full_name: "Admin",
  role: "admin",
  organization_id: 1,
};
const CLIN: api.Me = { ...ADMIN, user_id: 2, email: "clin@chartnav.local", role: "clinician" };
const REV: api.Me = { ...ADMIN, user_id: 3, email: "rev@chartnav.local", role: "reviewer" };

const FINDINGS: api.ExtractedFindings = {
  id: 10,
  encounter_id: 1,
  input_id: 5,
  chief_complaint: "blurry vision right eye",
  hpi_summary: "3 weeks duration",
  visual_acuity_od: "20/40",
  visual_acuity_os: "20/20",
  iop_od: "15",
  iop_os: "17",
  structured_json: {
    diagnoses: ["posterior capsular opacification"],
    medications: [],
    imaging: [],
    plan: "YAG capsulotomy",
    follow_up_interval: "4 weeks",
  },
  extraction_confidence: "medium",
  created_at: "2026-04-18 20:00:00",
};

function baseNote(overrides: Partial<api.NoteVersion> = {}): api.NoteVersion {
  return {
    id: 100,
    encounter_id: 1,
    version_number: 1,
    draft_status: "draft",
    note_format: "soap",
    note_text: "SUBJECTIVE\nChief complaint: blurry vision.\n",
    source_input_id: 5,
    extracted_findings_id: 10,
    generated_by: "system",
    provider_review_required: 1,
    missing_data_flags: ["iop_missing", "plan_missing"],
    signed_at: null,
    signed_by_user_id: null,
    exported_at: null,
    created_at: "2026-04-18 20:00:00",
    updated_at: "2026-04-18 20:00:00",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.listEncounterInputs as any).mockResolvedValue([
    {
      id: 5,
      encounter_id: 1,
      input_type: "text_paste",
      processing_status: "completed",
      transcript_text: "OD 20/40, OS 20/20.",
      confidence_summary: null,
      source_metadata: null,
      created_by_user_id: 1,
      created_at: "2026-04-18 20:00:00",
      updated_at: "2026-04-18 20:00:00",
    },
  ]);
  (api.listEncounterNotes as any).mockResolvedValue([baseNote()]);
  (api.getNoteVersion as any).mockResolvedValue({
    note: baseNote(),
    findings: FINDINGS,
  });
  (api.generateNoteVersion as any).mockImplementation(async () => ({
    note: baseNote({ version_number: 2, id: 101 }),
    findings: FINDINGS,
  }));
  (api.patchNoteVersion as any).mockImplementation(async (_e: any, _id: any, body: any) =>
    baseNote({
      ...baseNote(),
      draft_status: body.draft_status ?? "revised",
      generated_by: body.note_text ? "manual" : "system",
      note_text: body.note_text ?? baseNote().note_text,
    })
  );
  (api.submitNoteForReview as any).mockResolvedValue(
    baseNote({ draft_status: "provider_review" })
  );
  (api.signNoteVersion as any).mockResolvedValue(
    baseNote({
      draft_status: "signed",
      signed_at: "2026-04-18 20:10:00",
      signed_by_user_id: 2,
    })
  );
  (api.exportNoteVersion as any).mockResolvedValue(
    baseNote({
      draft_status: "exported",
      signed_at: "2026-04-18 20:10:00",
      exported_at: "2026-04-18 20:11:00",
    })
  );
  // Phase 26 defaults — standalone mode, no transmit. Individual tests
  // override to integrated_writethrough to exercise the Transmit surface.
  (api.getPlatform as any).mockResolvedValue({
    platform_mode: "standalone",
    integration_adapter: "native",
    adapter: {
      key: "native",
      display_name: "ChartNav native",
      description: "",
      supports: {
        patient_read: true,
        patient_write: true,
        encounter_read: true,
        encounter_write: true,
        document_write: true,
        document_transmit: false,
      },
      source_of_truth: {},
    },
  });
  (api.listNoteTransmissions as any).mockResolvedValue([]);
  // Phase 27 — default empty list; tests override as needed.
  (api.listMyQuickComments as any).mockResolvedValue([]);
  (api.createMyQuickComment as any).mockImplementation(
    async (_email: string, body: string) => ({
      id: 9999,
      organization_id: 1,
      user_id: 2,
      body,
      is_active: true,
      created_at: "2026-04-19 09:00:00",
      updated_at: "2026-04-19 09:00:00",
    })
  );
  (api.updateMyQuickComment as any).mockImplementation(
    async (_e: string, id: number, patch: any) => ({
      id,
      organization_id: 1,
      user_id: 2,
      body: patch.body ?? "",
      is_active: patch.is_active ?? true,
      created_at: "2026-04-19 09:00:00",
      updated_at: "2026-04-19 09:00:01",
    })
  );
  (api.deleteMyQuickComment as any).mockResolvedValue({
    id: 9999,
    organization_id: 1,
    user_id: 2,
    body: "x",
    is_active: false,
    created_at: "2026-04-19 09:00:00",
    updated_at: "2026-04-19 09:00:02",
  });
  // Phase 28 defaults — no favorites, usage audit swallowed silently.
  (api.listMyQuickCommentFavorites as any).mockResolvedValue([]);
  (api.favoriteQuickComment as any).mockImplementation(
    async (_e: string, ref: any) => ({
      id: 1,
      organization_id: 1,
      user_id: 2,
      preloaded_ref: ref.preloaded_ref ?? null,
      custom_comment_id: ref.custom_comment_id ?? null,
      created_at: "2026-04-19 10:00:00",
    })
  );
  (api.unfavoriteQuickComment as any).mockResolvedValue({ removed: 1 });
  (api.recordQuickCommentUsage as any).mockResolvedValue({
    recorded: true,
    kind: "preloaded",
  });
  (api.createEncounterInput as any).mockResolvedValue({});
});

function renderWorkspace(me: api.Me = CLIN) {
  return render(
    <NoteWorkspace
      identity={me.email}
      me={me}
      encounterId={1}
      patientDisplay="Morgan Lee"
      providerDisplay="Dr. Carter"
    />
  );
}

// ---------------------------------------------------------------------

describe("NoteWorkspace", () => {
  it("renders three distinct trust tiers (transcript, findings, draft)", async () => {
    renderWorkspace();
    await screen.findByTestId("workspace-tier-transcript");
    await screen.findByTestId("workspace-tier-findings");
    await screen.findByTestId("workspace-tier-draft");
    expect(screen.getByTestId("workspace-tier-transcript")).toHaveTextContent(
      /transcript input/i
    );
    expect(screen.getByTestId("workspace-tier-findings")).toHaveTextContent(
      /extracted findings/i
    );
    expect(screen.getByTestId("workspace-tier-draft")).toHaveTextContent(
      /note draft/i
    );
  });

  it("renders extracted findings + visible confidence", async () => {
    renderWorkspace();
    const fb = await screen.findByTestId("findings-block");
    expect(within(fb).getByTestId("findings-cc")).toHaveTextContent(
      "blurry vision right eye"
    );
    expect(within(fb).getByTestId("findings-va")).toHaveTextContent(
      "20/40 / 20/20"
    );
    expect(within(fb).getByTestId("findings-iop")).toHaveTextContent(
      "15 / 17"
    );
    const confidence = within(fb).getByTestId("findings-confidence");
    expect(confidence).toHaveTextContent("medium");
    expect(confidence).toHaveAttribute("data-confidence", "medium");
  });

  it("shows missing-data flags as a provider-verify checklist", async () => {
    renderWorkspace();
    const banner = await screen.findByTestId("missing-flags-banner");
    expect(banner).toHaveTextContent(/intraocular pressure/i);
    expect(banner).toHaveTextContent(/plan/i);
  });

  it("provider edit flips generated-by to 'provider (edited)'", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = await screen.findByTestId("note-draft-textarea");
    await user.clear(textarea);
    await user.type(textarea, "provider rewrote this line");
    await user.click(screen.getByTestId("note-save-edit"));
    await waitFor(() => {
      expect(api.patchNoteVersion).toHaveBeenCalledWith(
        CLIN.email,
        100,
        expect.objectContaining({ note_text: "provider rewrote this line" })
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("note-generated-by")).toHaveTextContent(
        /provider \(edited\)/i
      );
    });
  });

  it("submits for review and then clinician can sign", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(await screen.findByTestId("note-submit-review"));
    await waitFor(() =>
      expect(api.submitNoteForReview).toHaveBeenCalledWith(CLIN.email, 100)
    );

    await user.click(screen.getByTestId("note-sign"));
    await waitFor(() =>
      expect(api.signNoteVersion).toHaveBeenCalledWith(CLIN.email, 100)
    );
    await waitFor(() =>
      expect(screen.getByTestId("note-draft-status")).toHaveTextContent(
        /signed/i
      )
    );
  });

  it("reviewer sees a disabled-sign note and no sign button", async () => {
    renderWorkspace(REV);
    await screen.findByTestId("note-draft-readonly");
    expect(screen.queryByTestId("note-sign")).not.toBeInTheDocument();
    expect(
      screen.getByTestId("note-sign-disabled-note")
    ).toHaveTextContent(/reviewer role cannot sign/i);
  });

  it("exports a signed note and switches the textarea to read-only", async () => {
    (api.listEncounterNotes as any).mockResolvedValue([
      baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
    ]);
    (api.getNoteVersion as any).mockResolvedValue({
      note: baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
      findings: FINDINGS,
    });
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("note-draft-readonly");
    await user.click(screen.getByTestId("note-export"));
    await waitFor(() =>
      expect(api.exportNoteVersion).toHaveBeenCalledWith(CLIN.email, 100)
    );
  });

  it("ingests a transcript paste and triggers a generate", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("workspace-tier-transcript");
    await user.type(
      screen.getByTestId("transcript-ingest-textarea"),
      "OD 20/40, OS 20/20."
    );
    await user.click(screen.getByTestId("transcript-ingest-submit"));
    await waitFor(() =>
      expect(api.createEncounterInput).toHaveBeenCalledWith(
        CLIN.email,
        1,
        expect.objectContaining({
          input_type: "text_paste",
          transcript_text: "OD 20/40, OS 20/20.",
        })
      )
    );
    await user.click(screen.getByTestId("generate-draft"));
    await waitFor(() =>
      expect(api.generateNoteVersion).toHaveBeenCalled()
    );
  });

  // -------------------------------------------------------------------
  // Phase 22 — ingestion lifecycle UX
  // -------------------------------------------------------------------

  it("shows a failed input with last_error + offers a Retry button", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 7,
        encounter_id: 1,
        input_type: "text_paste",
        processing_status: "failed",
        transcript_text: "tiny",
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: "transcript is 4 characters; need at least 10",
        last_error_code: "transcript_too_short",
        started_at: "2026-04-18 22:00:00",
        finished_at: "2026-04-18 22:00:01",
        worker_id: "inline",
        created_at: "2026-04-18 22:00:00",
        updated_at: "2026-04-18 22:00:01",
      },
    ]);
    (api.retryEncounterInput as any).mockResolvedValue({});
    (api.processEncounterInput as any).mockResolvedValue({
      input: {},
      ingestion_error: null,
    });
    renderWorkspace();
    const err = await screen.findByTestId("transcript-error-7");
    expect(err).toHaveTextContent(/transcript_too_short/);
    expect(err).toHaveTextContent(/need at least 10/);
    const status = screen.getByTestId("transcript-status-7");
    expect(status).toHaveAttribute("data-status", "failed");

    const user = userEvent.setup();
    await user.click(screen.getByTestId("transcript-retry-7"));
    await waitFor(() => {
      expect(api.retryEncounterInput).toHaveBeenCalledWith(CLIN.email, 7);
      expect(api.processEncounterInput).toHaveBeenCalledWith(CLIN.email, 7);
    });
  });

  it("shows retry_count when > 0", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 8,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "failed",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 2,
        last_error: "audio_transcription_not_implemented",
        last_error_code: "audio_transcription_not_implemented",
        started_at: "x",
        finished_at: "x",
        worker_id: "inline",
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-retry-count-8");
    expect(screen.getByTestId("transcript-retry-count-8")).toHaveTextContent(
      "retries 2"
    );
  });

  it("queued input exposes a Process now button and disables Generate", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 9,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "queued",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: null,
        finished_at: null,
        worker_id: null,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    (api.processEncounterInput as any).mockResolvedValue({
      input: {},
      ingestion_error: null,
    });
    renderWorkspace();
    await screen.findByTestId("transcript-process-9");
    // Generate button is disabled because no completed input exists.
    expect(screen.getByTestId("generate-draft")).toBeDisabled();

    const user = userEvent.setup();
    await user.click(screen.getByTestId("transcript-process-9"));
    await waitFor(() =>
      expect(api.processEncounterInput).toHaveBeenCalledWith(CLIN.email, 9)
    );
  });

  it("Generate stays enabled when a completed input exists", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 10,
        encounter_id: 1,
        input_type: "text_paste",
        processing_status: "completed",
        transcript_text: "done",
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: "x",
        finished_at: "x",
        worker_id: "inline",
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-status-10");
    expect(screen.getByTestId("generate-draft")).toBeEnabled();
  });

  // -------------------------------------------------------------------
  // Phase 23 — background-processing UX
  // -------------------------------------------------------------------

  it("renders a processing-continues-in-background banner when any input is queued", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 30,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "queued",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: null,
        finished_at: null,
        worker_id: null,
        claimed_by: null,
        claimed_at: null,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    const banner = await screen.findByTestId("workspace-queue-banner");
    expect(banner).toHaveTextContent(/queued in the background/i);
    expect(banner).toHaveTextContent(/waiting for a worker/i);
    expect(banner).toHaveTextContent(/Process now/i);
  });

  it("renders the banner with 'currently processing' when a row is claimed", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 31,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "processing",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: "2026-04-19 00:00:00",
        finished_at: null,
        worker_id: "worker-a",
        claimed_by: "worker-a",
        claimed_at: "2026-04-19 00:00:00",
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    const banner = await screen.findByTestId("workspace-queue-banner");
    expect(banner).toHaveTextContent(/processing in the background/i);
    expect(banner).toHaveTextContent(/Refresh/i);
  });

  it("hides the banner when all inputs are completed", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 32,
        encounter_id: 1,
        input_type: "text_paste",
        processing_status: "completed",
        transcript_text: "done",
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: "x",
        finished_at: "x",
        worker_id: "inline",
        claimed_by: null,
        claimed_at: null,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-status-32");
    expect(
      screen.queryByTestId("workspace-queue-banner")
    ).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------
  // Phase 24 (frontend hardening) — generate-blocked hints
  // -------------------------------------------------------------------

  it("generate-blocked hint: empty state tells the operator to ingest first", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([]);
    renderWorkspace();
    await screen.findByTestId("workspace-tier-transcript");
    const hint = screen.getByTestId("generate-blocked-note");
    expect(hint).toHaveTextContent(/unlocks once a transcript/i);
    expect(screen.getByTestId("generate-draft")).toBeDisabled();
  });

  it("generate-blocked hint: queued input tells the operator processing is pending", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 40,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "queued",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: null,
        finished_at: null,
        worker_id: null,
        claimed_by: null,
        claimed_at: null,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    const hint = await screen.findByTestId("generate-blocked-note");
    expect(hint).toHaveTextContent(/waiting on transcript processing/i);
    expect(hint).toHaveTextContent(/Background work continues/i);
  });

  it("generate-blocked hint: failed input tells the operator to retry", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 41,
        encounter_id: 1,
        input_type: "text_paste",
        processing_status: "failed",
        transcript_text: "tiny",
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 1,
        last_error: "transcript_too_short",
        last_error_code: "transcript_too_short",
        started_at: "x",
        finished_at: "x",
        worker_id: "inline",
        claimed_by: null,
        claimed_at: null,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    const hint = await screen.findByTestId("generate-blocked-note");
    expect(hint).toHaveTextContent(/failed or needs review/i);
    expect(hint).toHaveTextContent(/Retry it/i);
  });

  it("manual refresh button re-fetches the input list", async () => {
    const listMock = (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 33,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "queued",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 1,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: null,
        finished_at: null,
        worker_id: null,
        claimed_by: null,
        claimed_at: null,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-refresh");
    const callsBefore = listMock.mock.calls.length;
    const user = userEvent.setup();
    await user.click(screen.getByTestId("transcript-refresh"));
    await waitFor(() => {
      expect(listMock.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  // -------------------------------------------------------------------
  // Phase 25 — signed-note artifact export
  // -------------------------------------------------------------------

  it("exposes Download JSON/TEXT/FHIR once the note is signed", async () => {
    (api.listEncounterNotes as any).mockResolvedValue([
      baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
    ]);
    (api.getNoteVersion as any).mockResolvedValue({
      note: baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
      findings: FINDINGS,
    });
    renderWorkspace();
    const actions = await screen.findByTestId("note-artifact-actions");
    expect(within(actions).getByTestId("note-artifact-json")).toHaveTextContent(
      /download json/i
    );
    expect(within(actions).getByTestId("note-artifact-text")).toHaveTextContent(
      /download text/i
    );
    expect(within(actions).getByTestId("note-artifact-fhir")).toHaveTextContent(
      /download fhir/i
    );
  });

  it("unsigned notes do not show the artifact actions", async () => {
    (api.listEncounterNotes as any).mockResolvedValue([
      baseNote({ draft_status: "draft" }),
    ]);
    (api.getNoteVersion as any).mockResolvedValue({
      note: baseNote({ draft_status: "draft" }),
      findings: FINDINGS,
    });
    renderWorkspace();
    await screen.findByTestId("note-draft-textarea");
    expect(
      screen.queryByTestId("note-artifact-actions")
    ).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------
  // Phase 26 — signed-note transmission
  // -------------------------------------------------------------------

  const signedSetup = () => {
    (api.listEncounterNotes as any).mockResolvedValue([
      baseNote({ draft_status: "signed", signed_at: "2026-04-18 20:10:00" }),
    ]);
    (api.getNoteVersion as any).mockResolvedValue({
      note: baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
      findings: FINDINGS,
    });
  };

  it("hides Transmit when the adapter does not support document_transmit", async () => {
    signedSetup();
    // Default getPlatform mock has document_transmit=false.
    renderWorkspace();
    await screen.findByTestId("note-artifact-actions");
    expect(screen.queryByTestId("note-transmit")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("note-transmissions")
    ).not.toBeInTheDocument();
  });

  it("shows Transmit when the adapter supports document_transmit", async () => {
    signedSetup();
    (api.getPlatform as any).mockResolvedValue({
      platform_mode: "integrated_writethrough",
      integration_adapter: "fhir",
      adapter: {
        key: "fhir",
        display_name: "FHIR R4",
        description: "",
        supports: {
          patient_read: true,
          patient_write: false,
          encounter_read: true,
          encounter_write: false,
          document_write: false,
          document_transmit: true,
        },
        source_of_truth: {},
      },
    });
    renderWorkspace();
    const btn = await screen.findByTestId("note-transmit");
    expect(btn).toHaveTextContent(/transmit to ehr/i);
  });

  it("click Transmit dispatches transmitNoteVersion and refreshes history", async () => {
    signedSetup();
    (api.getPlatform as any).mockResolvedValue({
      platform_mode: "integrated_writethrough",
      integration_adapter: "fhir",
      adapter: {
        key: "fhir",
        display_name: "FHIR R4",
        description: "",
        supports: {
          patient_read: true,
          patient_write: false,
          encounter_read: true,
          encounter_write: false,
          document_write: false,
          document_transmit: true,
        },
        source_of_truth: {},
      },
    });
    (api.transmitNoteVersion as any).mockResolvedValue({
      id: 500,
      note_version_id: 100,
      encounter_id: 1,
      organization_id: 1,
      adapter_key: "fhir",
      target_system: "https://fhir.test/r4",
      transport_status: "succeeded",
      request_body_hash: "abc",
      response_code: 201,
      response_snippet: "{}",
      remote_id: "docref-xyz",
      last_error_code: null,
      last_error: null,
      attempt_number: 1,
      attempted_at: "2026-04-19 08:30:00",
      completed_at: "2026-04-19 08:30:01",
      created_by_user_id: 2,
      created_at: "2026-04-19 08:30:00",
      updated_at: "2026-04-19 08:30:01",
    });
    (api.listNoteTransmissions as any)
      .mockResolvedValueOnce([]) // initial mount
      .mockResolvedValue([
        {
          id: 500,
          note_version_id: 100,
          encounter_id: 1,
          organization_id: 1,
          adapter_key: "fhir",
          target_system: "https://fhir.test/r4",
          transport_status: "succeeded",
          request_body_hash: "abc",
          response_code: 201,
          response_snippet: "{}",
          remote_id: "docref-xyz",
          last_error_code: null,
          last_error: null,
          attempt_number: 1,
          attempted_at: null,
          completed_at: null,
          created_by_user_id: 2,
          created_at: "2026-04-19 08:30:00",
          updated_at: "2026-04-19 08:30:01",
        },
      ]);

    const user = userEvent.setup();
    renderWorkspace();
    const btn = await screen.findByTestId("note-transmit");
    await user.click(btn);
    await waitFor(() =>
      expect(api.transmitNoteVersion).toHaveBeenCalledWith(
        CLIN.email,
        100,
        { force: false }
      )
    );
    // History pane renders the new row.
    const history = await screen.findByTestId("note-transmissions");
    expect(within(history).getByTestId("note-transmission-500")).toHaveTextContent(
      /succeeded/
    );
    expect(
      within(history).getByTestId("note-transmission-500")
    ).toHaveTextContent(/docref-xyz/);
  });

  it("click Download FHIR dispatches downloadNoteArtifact with the right format", async () => {
    (api.listEncounterNotes as any).mockResolvedValue([
      baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
    ]);
    (api.getNoteVersion as any).mockResolvedValue({
      note: baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
      findings: FINDINGS,
    });
    (api.downloadNoteArtifact as any).mockResolvedValue({
      filename: "chartnav-note-100.fhir.json",
      variant: "fhir.DocumentReference.v1",
    });
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("note-artifact-actions");
    await user.click(screen.getByTestId("note-artifact-fhir"));
    await waitFor(() =>
      expect(api.downloadNoteArtifact).toHaveBeenCalledWith(
        CLIN.email,
        100,
        "fhir"
      )
    );
  });

  // -------------------------------------------------------------------
  // Phase 27 — clinician quick-comment pad
  // -------------------------------------------------------------------

  it("Quick Comments panel is hidden for reviewers", async () => {
    render(
      <NoteWorkspace
        identity="rev@chartnav.local"
        me={REV}
        encounterId={1}
        patientDisplay="Test"
        providerDisplay="Dr T"
      />
    );
    // Reviewer view should render *something* from the workspace…
    await screen.findByTestId("workspace-tier-transcript");
    // …but never the quick-comments panel.
    expect(
      screen.queryByTestId("quick-comments-panel")
    ).not.toBeInTheDocument();
    // And no API fetch for per-user comments should have fired.
    expect(api.listMyQuickComments).not.toHaveBeenCalled();
  });

  it("renders preloaded quick comments grouped by category for clinicians", async () => {
    renderWorkspace();
    const panel = await screen.findByTestId("quick-comments-panel");
    // Provenance label — these are NOT AI findings.
    expect(panel).toHaveTextContent(/clinician-entered/i);
    expect(panel).toHaveTextContent(
      /not transcript findings or ai-generated/i
    );

    const preloaded = within(panel).getByTestId("quick-comments-preloaded");
    // All five categories render.
    expect(
      within(preloaded).getByTestId("quick-comments-group-symptoms-hpi")
    ).toBeInTheDocument();
    expect(
      within(preloaded).getByTestId(
        "quick-comments-group-visual-function-basic-exam"
      )
    ).toBeInTheDocument();
    expect(
      within(preloaded).getByTestId(
        "quick-comments-group-external-anterior-segment"
      )
    ).toBeInTheDocument();
    expect(
      within(preloaded).getByTestId("quick-comments-group-posterior-segment")
    ).toBeInTheDocument();
    expect(
      within(preloaded).getByTestId(
        "quick-comments-group-assessment-plan-counseling"
      )
    ).toBeInTheDocument();
    // Spot-check some exact brief phrases to confirm verbatim render.
    expect(preloaded).toHaveTextContent("Vision stable since last visit.");
    expect(preloaded).toHaveTextContent("IOP acceptable today.");
    expect(preloaded).toHaveTextContent("Macula flat and dry.");
    expect(preloaded).toHaveTextContent("Follow-up interval reviewed and agreed upon.");
  });

  it("click preloaded quick comment inserts into the editable draft", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("note-draft-textarea");
    const textarea = screen.getByTestId(
      "note-draft-textarea"
    ) as HTMLTextAreaElement;
    const before = textarea.value;
    await user.click(screen.getByTestId("quick-comment-sx-01"));
    await waitFor(() => {
      expect(textarea.value).not.toBe(before);
      expect(textarea.value).toContain("Vision stable since last visit.");
    });
  });

  it("preloaded quick comments are disabled once the note is signed", async () => {
    (api.listEncounterNotes as any).mockResolvedValue([
      baseNote({ draft_status: "signed", signed_at: "2026-04-18 20:10:00" }),
    ]);
    (api.getNoteVersion as any).mockResolvedValue({
      note: baseNote({
        draft_status: "signed",
        signed_at: "2026-04-18 20:10:00",
      }),
      findings: FINDINGS,
    });
    renderWorkspace();
    await screen.findByTestId("quick-comments-panel");
    const btn = screen.getByTestId("quick-comment-post-44");
    expect(btn).toBeDisabled();
  });

  it("search filters the preloaded pack", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("quick-comments-panel");
    await user.type(
      screen.getByTestId("quick-comments-search"),
      "macula"
    );
    const preloaded = screen.getByTestId("quick-comments-preloaded");
    expect(preloaded).toHaveTextContent(/Macula flat and dry/i);
    expect(preloaded).not.toHaveTextContent(/Vision stable since last visit/i);
  });

  it("Add Custom Comment opens modal and saves through the API", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("quick-comments-panel");
    await user.click(screen.getByTestId("quick-comments-add"));
    const modal = await screen.findByTestId("quick-comments-modal");
    const textarea = within(modal).getByTestId(
      "quick-comments-modal-textarea"
    );
    await user.type(textarea, "Refraction deferred per patient request.");
    await user.click(within(modal).getByTestId("quick-comments-modal-save"));
    await waitFor(() =>
      expect(api.createMyQuickComment).toHaveBeenCalledWith(
        CLIN.email,
        "Refraction deferred per patient request."
      )
    );
    // Modal closes + list refreshes.
    await waitFor(() =>
      expect(
        screen.queryByTestId("quick-comments-modal")
      ).not.toBeInTheDocument()
    );
    expect(api.listMyQuickComments).toHaveBeenCalled();
  });

  it("renders per-doctor custom comments and clicking one inserts", async () => {
    (api.listMyQuickComments as any).mockResolvedValue([
      {
        id: 42,
        organization_id: 1,
        user_id: 2,
        body: "Warned patient about glare at night.",
        is_active: true,
        created_at: "2026-04-19 09:00:00",
        updated_at: "2026-04-19 09:00:00",
      },
    ]);
    const user = userEvent.setup();
    renderWorkspace();
    const custom = await screen.findByTestId("quick-comments-custom");
    const row = within(custom).getByTestId("quick-comment-custom-42");
    expect(row).toHaveTextContent(/Warned patient about glare at night/);
    // Insert into draft.
    await screen.findByTestId("note-draft-textarea");
    const textarea = screen.getByTestId(
      "note-draft-textarea"
    ) as HTMLTextAreaElement;
    await user.click(within(row).getByRole("button", { name: /warned patient/i }));
    await waitFor(() =>
      expect(textarea.value).toContain(
        "Warned patient about glare at night."
      )
    );
  });

  it("delete custom comment calls deleteMyQuickComment and refreshes", async () => {
    (api.listMyQuickComments as any)
      .mockResolvedValueOnce([
        {
          id: 42,
          organization_id: 1,
          user_id: 2,
          body: "X",
          is_active: true,
          created_at: "x",
          updated_at: "x",
        },
      ])
      .mockResolvedValue([]);
    const user = userEvent.setup();
    renderWorkspace();
    const row = await screen.findByTestId("quick-comment-custom-42");
    await user.click(
      within(row).getByTestId("quick-comment-custom-delete-42")
    );
    await waitFor(() =>
      expect(api.deleteMyQuickComment).toHaveBeenCalledWith(CLIN.email, 42)
    );
  });

  it("no patient-facing surface: quick comments live only inside the clinician workspace", async () => {
    renderWorkspace();
    const panel = await screen.findByTestId("quick-comments-panel");
    // The panel renders *inside* the workspace, not at the App shell.
    // This is a structural check: the panel is a descendant of the
    // workspace container that's gated by the clinician role.
    const workspace = panel.closest("section");
    expect(workspace).toBeTruthy();
    expect(workspace?.className).toContain("workspace__quick-comments");
    // And the preloaded pack clearly labels itself as clinician-entered.
    expect(
      screen.getByTestId("quick-comments-help")
    ).toHaveTextContent(
      /clinician quick-picks, not transcript findings or ai-generated/i
    );
  });

  // -------------------------------------------------------------------
  // Phase 28 — favorites / pinning
  // -------------------------------------------------------------------

  it("preloaded star toggle calls favorite + refreshes favorites list", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("quick-comments-panel");
    // No favorites at mount → strip absent.
    expect(
      screen.queryByTestId("quick-comments-favorites")
    ).not.toBeInTheDocument();
    // Click the star next to a preloaded comment.
    await user.click(screen.getByTestId("quick-comment-star-sx-04"));
    await waitFor(() =>
      expect(api.favoriteQuickComment).toHaveBeenCalledWith(CLIN.email, {
        preloaded_ref: "sx-04",
      })
    );
    expect(api.listMyQuickCommentFavorites).toHaveBeenCalled();
  });

  it("favorites strip renders above the library when a pin exists", async () => {
    (api.listMyQuickCommentFavorites as any).mockResolvedValue([
      {
        id: 1,
        organization_id: 1,
        user_id: 2,
        preloaded_ref: "post-44",
        custom_comment_id: null,
        created_at: "x",
      },
    ]);
    renderWorkspace();
    const strip = await screen.findByTestId("quick-comments-favorites");
    expect(strip).toHaveTextContent(/Macula flat and dry/);
    const btn = within(strip).getByTestId(
      "quick-comment-favorite-preloaded-post-44"
    );
    expect(btn).toBeInTheDocument();
    // Star on the preloaded row should render as pinned.
    expect(screen.getByTestId("quick-comment-star-post-44")).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("custom favorite strip surfaces a pinned custom comment", async () => {
    (api.listMyQuickComments as any).mockResolvedValue([
      {
        id: 77,
        organization_id: 1,
        user_id: 2,
        body: "Recommended punctal plugs.",
        is_active: true,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    (api.listMyQuickCommentFavorites as any).mockResolvedValue([
      {
        id: 2,
        organization_id: 1,
        user_id: 2,
        preloaded_ref: null,
        custom_comment_id: 77,
        created_at: "x",
      },
    ]);
    renderWorkspace();
    const strip = await screen.findByTestId("quick-comments-favorites");
    expect(
      within(strip).getByTestId("quick-comment-favorite-custom-77")
    ).toHaveTextContent(/Recommended punctal plugs/);
  });

  it("favorites panel is NOT rendered for reviewers", async () => {
    (api.listMyQuickCommentFavorites as any).mockResolvedValue([
      {
        id: 1,
        organization_id: 1,
        user_id: 2,
        preloaded_ref: "post-44",
        custom_comment_id: null,
        created_at: "x",
      },
    ]);
    render(
      <NoteWorkspace
        identity="rev@chartnav.local"
        me={REV}
        encounterId={1}
        patientDisplay="Test"
        providerDisplay="Dr T"
      />
    );
    await screen.findByTestId("workspace-tier-transcript");
    expect(
      screen.queryByTestId("quick-comments-favorites")
    ).not.toBeInTheDocument();
    expect(api.listMyQuickCommentFavorites).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // Phase 28 — cursor-position insertion
  // -------------------------------------------------------------------

  it("inserts at the cursor position, not the end, when there's a selection", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    // Seed a known draft body with a well-known insertion point.
    await user.clear(textarea);
    await user.type(textarea, "BEFORE|AFTER");
    // Place caret at the `|` — index 6.
    textarea.focus();
    textarea.setSelectionRange(6, 6);

    await user.click(screen.getByTestId("quick-comment-sx-01"));

    await waitFor(() => {
      const v = textarea.value;
      expect(v.startsWith("BEFORE")).toBe(true);
      expect(v).toContain("Vision stable since last visit.");
      // The inserted phrase must appear BEFORE the "|AFTER" tail,
      // proving it was spliced at the caret rather than appended.
      const phraseIdx = v.indexOf("Vision stable since last visit.");
      const afterIdx = v.indexOf("|AFTER");
      expect(phraseIdx).toBeGreaterThan(-1);
      expect(afterIdx).toBeGreaterThan(phraseIdx);
    });
  });

  it("appends at end when the textarea has no selection state", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    // Push caret to the end and blur so no active selection exists.
    await user.click(textarea);
    const len = textarea.value.length;
    textarea.setSelectionRange(len, len);
    textarea.blur();

    await user.click(screen.getByTestId("quick-comment-plan-50"));
    await waitFor(() =>
      expect(textarea.value).toContain(
        "Follow-up interval reviewed and agreed upon."
      )
    );
    // Appended at the end of whatever was there.
    expect(textarea.value.trim().endsWith("agreed upon.")).toBe(true);
  });

  // -------------------------------------------------------------------
  // Phase 28 — usage audit
  // -------------------------------------------------------------------

  it("click preloaded fires recordQuickCommentUsage with preloaded_ref", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("quick-comments-panel");
    await user.click(screen.getByTestId("quick-comment-vf-24"));
    await waitFor(() =>
      expect(api.recordQuickCommentUsage).toHaveBeenCalledWith(
        CLIN.email,
        expect.objectContaining({ preloaded_ref: "vf-24" })
      )
    );
    // PHI invariant: the payload must NOT carry the comment body.
    const call = (api.recordQuickCommentUsage as any).mock.calls.at(-1);
    expect(call?.[1]).not.toHaveProperty("body");
  });

  it("click custom fires recordQuickCommentUsage with custom_comment_id", async () => {
    (api.listMyQuickComments as any).mockResolvedValue([
      {
        id: 55,
        organization_id: 1,
        user_id: 2,
        body: "Discussed lens options.",
        is_active: true,
        created_at: "x",
        updated_at: "x",
      },
    ]);
    const user = userEvent.setup();
    renderWorkspace();
    const row = await screen.findByTestId("quick-comment-custom-55");
    await user.click(within(row).getByRole("button", { name: /discussed lens/i }));
    await waitFor(() =>
      expect(api.recordQuickCommentUsage).toHaveBeenCalledWith(
        CLIN.email,
        expect.objectContaining({ custom_comment_id: 55 })
      )
    );
    const call = (api.recordQuickCommentUsage as any).mock.calls.at(-1);
    expect(call?.[1]).not.toHaveProperty("body");
  });
});
