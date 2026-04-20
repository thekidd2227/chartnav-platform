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
    // Phase 29 — clinical shortcuts usage audit.
    recordClinicalShortcutUsage: vi.fn(),
    // Phase 30 — clinical shortcut favorites.
    listMyClinicalShortcutFavorites: vi.fn(),
    favoriteClinicalShortcut: vi.fn(),
    unfavoriteClinicalShortcut: vi.fn(),
    // Phase 33 — audio intake + transcript review.
    uploadEncounterAudio: vi.fn(),
    patchEncounterInputTranscript: vi.fn(),
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
  (api.recordClinicalShortcutUsage as any).mockResolvedValue({
    recorded: true,
    shortcut_id: "rd-01",
  });
  // Phase 30 defaults — no pinned shortcuts, successful toggle ops.
  (api.listMyClinicalShortcutFavorites as any).mockResolvedValue([]);
  (api.favoriteClinicalShortcut as any).mockImplementation(
    async (_e: string, ref: string) => ({
      id: 1,
      organization_id: 1,
      user_id: 2,
      shortcut_ref: ref,
      created_at: "2026-04-19 12:00:00",
    })
  );
  (api.unfavoriteClinicalShortcut as any).mockResolvedValue({ removed: 1 });
  // Phase 33 defaults.
  (api.uploadEncounterAudio as any).mockImplementation(
    async (_email: string, _enc: number, file: File) => ({
      id: 501,
      encounter_id: 1,
      input_type: "audio_upload",
      processing_status: "completed",
      transcript_text: `[stub-transcript] File metadata: ${file.name} (${file.type || "audio/unknown"}, ${file.size} bytes).`,
      confidence_summary: null,
      source_metadata: JSON.stringify({
        original_filename: file.name,
        content_type: file.type || "audio/unknown",
        size_bytes: file.size,
      }),
      created_by_user_id: 2,
      retry_count: 0,
      last_error: null,
      last_error_code: null,
      started_at: "2026-04-20 00:00:00",
      finished_at: "2026-04-20 00:00:01",
      worker_id: "inline",
      claimed_by: null,
      claimed_at: null,
      created_at: "2026-04-20 00:00:00",
      updated_at: "2026-04-20 00:00:01",
    })
  );
  (api.patchEncounterInputTranscript as any).mockImplementation(
    async (_email: string, id: number, text: string) => ({
      id,
      encounter_id: 1,
      input_type: "audio_upload",
      processing_status: "completed",
      transcript_text: text,
      confidence_summary: null,
      source_metadata: null,
      created_by_user_id: 2,
      retry_count: 0,
      last_error: null,
      last_error_code: null,
      started_at: null,
      finished_at: null,
      worker_id: null,
      claimed_by: null,
      claimed_at: null,
      created_at: "x",
      updated_at: "y",
    })
  );
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

  // -------------------------------------------------------------------
  // Phase 29 — Clinical Shortcuts
  // -------------------------------------------------------------------

  it("Clinical Shortcuts panel is hidden for reviewers", async () => {
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
      screen.queryByTestId("clinical-shortcuts-panel")
    ).not.toBeInTheDocument();
    // No shortcut usage-audit POST should have fired for reviewer.
    expect(api.recordClinicalShortcutUsage).not.toHaveBeenCalled();
  });

  it("renders the three specialist groups with verbatim phrasing", async () => {
    renderWorkspace();
    const panel = await screen.findByTestId("clinical-shortcuts-panel");
    // Provenance label is unambiguous.
    expect(panel).toHaveTextContent(/clinician-entered/i);
    expect(panel).toHaveTextContent(
      /doctor-inserted shortcuts, not transcript findings or ai-generated/i
    );
    // All three clinical groups render.
    expect(
      screen.getByTestId("clinical-shortcuts-group-pvd")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcuts-group-retinal-detachment")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcuts-group-wet-dry-amd")
    ).toBeInTheDocument();
    // Spot-check exact clinical phrasing per the brief.
    expect(panel).toHaveTextContent(/Acute PVD noted with vitreous syneresis/);
    expect(panel).toHaveTextContent(/Negative Shafer sign/);
    expect(panel).toHaveTextContent(/Rhegmatogenous retinal detachment/);
    expect(panel).toHaveTextContent(/macula on \/ macula off/);
    expect(panel).toHaveTextContent(/Dry AMD with drusen and RPE mottling/);
  });

  it("abbreviations inside shortcut bodies render with hover-help (<abbr title>)", async () => {
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    // "AMD" appears inside the Dry AMD shortcut; should be wrapped
    // with a title attribute carrying the expansion.
    const abbrs = screen.getAllByTestId("clinical-shortcut-abbr-AMD");
    expect(abbrs.length).toBeGreaterThan(0);
    expect(abbrs[0]).toHaveAttribute(
      "title",
      expect.stringMatching(/Age-related macular degeneration/i)
    );
    // "RPE" is present in "Dry AMD with drusen and RPE mottling".
    const rpe = screen.getAllByTestId("clinical-shortcut-abbr-RPE");
    expect(rpe[0]).toHaveAttribute(
      "title",
      expect.stringMatching(/Retinal pigment epithelium/i)
    );
  });

  it("click-to-insert routes the full clinical phrase into the draft", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.click(screen.getByTestId("clinical-shortcut-pvd-01"));
    await waitFor(() => {
      expect(textarea.value).toContain(
        "Acute PVD noted with vitreous syneresis."
      );
      expect(textarea.value).toContain(
        "No retinal tear or retinal detachment on scleral depressed exam."
      );
    });
  });

  it("click-to-insert fires recordClinicalShortcutUsage with shortcut_id + no body", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.click(screen.getByTestId("clinical-shortcut-rd-02"));
    await waitFor(() =>
      expect(api.recordClinicalShortcutUsage).toHaveBeenCalledWith(
        CLIN.email,
        expect.objectContaining({ shortcut_id: "rd-02" })
      )
    );
    // PHI invariant: the payload must not carry the shortcut body.
    const call = (api.recordClinicalShortcutUsage as any).mock.calls.at(-1);
    expect(call?.[1]).not.toHaveProperty("body");
  });

  it("signed notes disable every Clinical Shortcut button", async () => {
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
    await screen.findByTestId("clinical-shortcuts-panel");
    const btn = screen.getByTestId("clinical-shortcut-amd-01");
    expect(btn).toBeDisabled();
  });

  it("abbreviation-aware search: 'RD' surfaces the retinal-detachment group even without typing 'detachment'", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(screen.getByTestId("clinical-shortcuts-search"), "RD");
    // The Retinal detachment group must still render.
    expect(
      screen.getByTestId("clinical-shortcuts-group-retinal-detachment")
    ).toBeInTheDocument();
    // And the PVD shortcuts that explicitly rule out an RD (tagged
    // with `rd`) should still be visible, too.
    expect(
      screen.queryByTestId("clinical-shortcuts-group-pvd")
    ).toBeInTheDocument();
  });

  it("abbreviation-aware search: 'SRF' surfaces the shortcuts that mention subretinal fluid", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(screen.getByTestId("clinical-shortcuts-search"), "SRF");
    // rd-02 has the phrase "subretinal fluid"; rd-04 has "SRF" literally.
    expect(
      screen.getByTestId("clinical-shortcut-rd-02")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcut-rd-04")
    ).toBeInTheDocument();
  });

  it("abbreviation-aware search: 'AMD' restricts results to the Wet/Dry AMD group", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(screen.getByTestId("clinical-shortcuts-search"), "AMD");
    expect(
      screen.getByTestId("clinical-shortcuts-group-wet-dry-amd")
    ).toBeInTheDocument();
    // No PVD or RD group visible (their bodies never say "age-related
    // macular degeneration" and their tags don't include 'amd').
    expect(
      screen.queryByTestId("clinical-shortcuts-group-pvd")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("clinical-shortcuts-group-retinal-detachment")
    ).not.toBeInTheDocument();
  });

  it("Clinical Shortcuts live in their own panel, separate from Quick Comments", async () => {
    renderWorkspace();
    const shortcuts = await screen.findByTestId("clinical-shortcuts-panel");
    const qc = await screen.findByTestId("quick-comments-panel");
    // Structurally distinct sections (no ancestor sharing beyond the
    // workspace shell).
    expect(shortcuts).not.toBe(qc);
    expect(shortcuts.contains(qc)).toBe(false);
    expect(qc.contains(shortcuts)).toBe(false);
    // Each carries its own clinician-entered trust pill + its own
    // help caption.
    expect(qc).toHaveTextContent(/clinician-entered/i);
    expect(shortcuts).toHaveTextContent(/clinician-entered/i);
    expect(
      screen.getByTestId("clinical-shortcuts-help")
    ).toHaveTextContent(/specialty shorthand/i);
    expect(
      screen.getByTestId("quick-comments-help")
    ).toHaveTextContent(/clinician quick-picks/i);
  });

  it("Clinical Shortcut insertion does NOT fire the Quick-Comment audit", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.click(screen.getByTestId("clinical-shortcut-amd-03"));
    await waitFor(() =>
      expect(api.recordClinicalShortcutUsage).toHaveBeenCalled()
    );
    // The two audit streams must stay separate — a shortcut click
    // must never register as a quick-comment event.
    expect(api.recordQuickCommentUsage).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // Phase 30 — retina expansion, shortcut favorites, caret-to-blank
  // -------------------------------------------------------------------

  it("renders the four new retina-expansion groups", async () => {
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    // Groups from phase 30.
    expect(
      screen.getByTestId("clinical-shortcuts-group-diabetic-retinopathy-dme")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcuts-group-erm-vmt-macular-hole")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcuts-group-brvo-crvo-retinal-vascular")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId(
        "clinical-shortcuts-group-post-injection-post-vitrectomy-post-op"
      )
    ).toBeInTheDocument();
    // Spot-check verbatim shorthand phrases per the brief's clinical
    // tone. Use `toHaveTextContent` because abbreviations inside the
    // bodies are wrapped in `<abbr>` nodes and would otherwise break
    // a raw `getByText` substring query across DOM boundaries.
    expect(screen.getByTestId("clinical-shortcut-dm-02")).toHaveTextContent(
      /center-involving DME on OCT/i
    );
    expect(screen.getByTestId("clinical-shortcut-mac-03")).toHaveTextContent(
      /Full-thickness macular hole/i
    );
    expect(screen.getByTestId("clinical-shortcut-vasc-02")).toHaveTextContent(
      /Non-ischemic CRVO with diffuse intraretinal/i
    );
    expect(screen.getByTestId("clinical-shortcut-post-02")).toHaveTextContent(
      /Post-injection return precautions reviewed in detail/i
    );
  });

  it("abbreviation-aware search for 'DME' surfaces the diabetic group", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(screen.getByTestId("clinical-shortcuts-search"), "DME");
    expect(
      screen.getByTestId("clinical-shortcuts-group-diabetic-retinopathy-dme")
    ).toBeInTheDocument();
    // Non-diabetic groups with no DME mention drop out.
    expect(
      screen.queryByTestId("clinical-shortcuts-group-pvd")
    ).not.toBeInTheDocument();
  });

  it("abbreviation-aware search for 'CRVO' surfaces the retinal-vascular group", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(screen.getByTestId("clinical-shortcuts-search"), "CRVO");
    expect(
      screen.getByTestId("clinical-shortcuts-group-brvo-crvo-retinal-vascular")
    ).toBeInTheDocument();
  });

  it("abbreviation-aware search for 'FTMH' surfaces the macular-hole shortcuts", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(screen.getByTestId("clinical-shortcuts-search"), "FTMH");
    // Should include mac-03 (verbatim FTMH body) and mac-04
    // (tagged ftmh).
    expect(
      screen.getByTestId("clinical-shortcut-mac-03")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcut-mac-04")
    ).toBeInTheDocument();
  });

  it("shortcut star toggle calls favoriteClinicalShortcut and refreshes list", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    expect(
      screen.queryByTestId("clinical-shortcuts-favorites")
    ).not.toBeInTheDocument();
    await user.click(screen.getByTestId("clinical-shortcut-star-dm-01"));
    await waitFor(() =>
      expect(api.favoriteClinicalShortcut).toHaveBeenCalledWith(
        CLIN.email,
        "dm-01"
      )
    );
    expect(api.listMyClinicalShortcutFavorites).toHaveBeenCalled();
  });

  it("Favorites strip renders above the main catalog when a shortcut is pinned", async () => {
    (api.listMyClinicalShortcutFavorites as any).mockResolvedValue([
      {
        id: 10,
        organization_id: 1,
        user_id: 2,
        shortcut_ref: "post-03",
        created_at: "x",
      },
    ]);
    renderWorkspace();
    const strip = await screen.findByTestId(
      "clinical-shortcuts-favorites"
    );
    expect(strip).toHaveTextContent(/s\/p PPV/i);
    expect(
      within(strip).getByTestId("clinical-shortcut-favorite-post-03")
    ).toBeInTheDocument();
    // Star on the main-catalog row renders as pinned.
    expect(
      screen.getByTestId("clinical-shortcut-star-post-03")
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("shortcut favorites and star controls are hidden for reviewers", async () => {
    (api.listMyClinicalShortcutFavorites as any).mockResolvedValue([
      {
        id: 10,
        organization_id: 1,
        user_id: 2,
        shortcut_ref: "dm-01",
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
      screen.queryByTestId("clinical-shortcuts-favorites")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("clinical-shortcut-star-dm-01")
    ).not.toBeInTheDocument();
    expect(api.listMyClinicalShortcutFavorites).not.toHaveBeenCalled();
  });

  it("caret-to-first-blank: clicking rd-01 selects the first `___` in the draft", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    // Clear existing draft and seed a tiny known body so selection
    // offsets are deterministic.
    await user.clear(textarea);
    await user.type(textarea, "START|END");
    textarea.focus();
    textarea.setSelectionRange(5, 5); // caret between `|`

    await screen.findByTestId("clinical-shortcuts-panel");
    await user.click(screen.getByTestId("clinical-shortcut-rd-01"));
    // rAF runs before the assertion resolves; wait for the textarea
    // selection to land on the placeholder.
    await waitFor(() => {
      const value = textarea.value;
      const selected = value.slice(
        textarea.selectionStart,
        textarea.selectionEnd
      );
      expect(selected).toBe("___");
      // And the selection lands on the FIRST `___`, not a later one.
      const firstBlank = value.indexOf("___");
      expect(textarea.selectionStart).toBe(firstBlank);
    });
  });

  it("caret fallback: no blank → caret lands at end of inserted phrase", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "existing");
    textarea.focus();
    textarea.setSelectionRange(8, 8);
    // pvd-03 has no `___` placeholder.
    await user.click(screen.getByTestId("clinical-shortcut-pvd-03"));
    await waitFor(() => {
      // caret should land AT the end of the inserted phrase (not at
      // a phantom `___`). Simplest assertion: the selection is
      // collapsed (start === end) and sits strictly after the seeded
      // "existing" prefix.
      expect(textarea.selectionStart).toBe(textarea.selectionEnd);
      expect(textarea.selectionStart).toBeGreaterThan("existing".length);
    });
  });

  it("`s/p` in shortcut bodies renders with hover help via the case-insensitive matcher", async () => {
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    // dm-03 body: "PDR s/p PRP, stable without new NVD or NVE."
    const row = screen.getByTestId("clinical-shortcut-dm-03");
    // At least one `s/p` inside the body should have been wrapped.
    const abbrs = within(row).getAllByText("s/p");
    expect(abbrs.length).toBeGreaterThan(0);
    expect(abbrs[0].tagName.toLowerCase()).toBe("abbr");
    expect(abbrs[0]).toHaveAttribute(
      "title",
      expect.stringMatching(/Status post/i)
    );
  });

  // -------------------------------------------------------------------
  // Phase 31 — glaucoma + cornea expansion, Tab-to-next-blank
  // -------------------------------------------------------------------

  it("renders the two new subspecialty groups", async () => {
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    expect(
      screen.getByTestId("clinical-shortcuts-group-glaucoma")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcuts-group-cornea-anterior-segment")
    ).toBeInTheDocument();
    // Spot-check conservative specialist phrasing.
    expect(screen.getByTestId("clinical-shortcut-glc-02")).toHaveTextContent(
      /Ocular hypertension without glaucomatous optic neuropathy/i
    );
    expect(screen.getByTestId("clinical-shortcut-glc-04")).toHaveTextContent(
      /Narrow angles on gonioscopy OU without evidence of angle-closure/i
    );
    expect(screen.getByTestId("clinical-shortcut-cor-03")).toHaveTextContent(
      /Keratoconus with inferior steepening on topography/i
    );
    expect(screen.getByTestId("clinical-shortcut-cor-05")).toHaveTextContent(
      /Fuchs endothelial dystrophy/i
    );
  });

  it("abbreviation-aware search: 'POAG' surfaces the glaucoma group", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(
      screen.getByTestId("clinical-shortcuts-search"),
      "POAG"
    );
    expect(
      screen.getByTestId("clinical-shortcuts-group-glaucoma")
    ).toBeInTheDocument();
    // Retina-only groups drop out.
    expect(
      screen.queryByTestId("clinical-shortcuts-group-pvd")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("clinical-shortcuts-group-wet-dry-amd")
    ).not.toBeInTheDocument();
  });

  it("abbreviation-aware search: 'CXL' surfaces cornea with keratoconus", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(
      screen.getByTestId("clinical-shortcuts-search"),
      "CXL"
    );
    expect(
      screen.getByTestId("clinical-shortcuts-group-cornea-anterior-segment")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcut-cor-03")
    ).toBeInTheDocument();
  });

  it("Tab-to-next-blank: pressing Tab inside the draft selects the next `___`", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;

    // Seed a body containing two placeholders with known offsets.
    await user.clear(textarea);
    await user.type(textarea, "A ___ B ___ C");
    // Place caret at the start of the field.
    textarea.focus();
    textarea.setSelectionRange(0, 0);

    // Tab → first `___`.
    await user.keyboard("{Tab}");
    await waitFor(() => {
      const sel = textarea.value.slice(
        textarea.selectionStart,
        textarea.selectionEnd
      );
      expect(sel).toBe("___");
      expect(textarea.selectionStart).toBe("A ".length);
    });

    // Tab again → second `___`.
    await user.keyboard("{Tab}");
    await waitFor(() => {
      const sel = textarea.value.slice(
        textarea.selectionStart,
        textarea.selectionEnd
      );
      expect(sel).toBe("___");
      expect(textarea.selectionStart).toBe("A ___ B ".length);
    });
  });

  it("Tab fallback: with no remaining blanks, default Tab behaviour runs", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "no placeholders here");
    textarea.focus();
    textarea.setSelectionRange(3, 3);

    const before = {
      value: textarea.value,
      start: textarea.selectionStart,
      end: textarea.selectionEnd,
    };

    // Dispatch a Tab keydown and confirm the handler did NOT
    // preventDefault (i.e. the default event remains cancelable=true
    // and the value + selection are unchanged by our handler).
    const ev = new KeyboardEvent("keydown", {
      key: "Tab",
      bubbles: true,
      cancelable: true,
    });
    textarea.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(false);
    expect(textarea.value).toBe(before.value);
    expect(textarea.selectionStart).toBe(before.start);
    expect(textarea.selectionEnd).toBe(before.end);
  });

  it("Tab with Shift modifier now walks BACKWARD to the previous blank (phase 32)", async () => {
    // Phase 32: Shift+Tab walks backward through placeholders.
    // Previously (phase 31) this was a pass-through; the test now
    // asserts the new behaviour.
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "A ___ B ___ C");
    // Caret sits at the very end — Shift+Tab should walk to the
    // SECOND `___` (at "A ___ B ".length = 8).
    textarea.focus();
    const len = textarea.value.length;
    textarea.setSelectionRange(len, len);

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    await waitFor(() => {
      const sel = textarea.value.slice(
        textarea.selectionStart,
        textarea.selectionEnd
      );
      expect(sel).toBe("___");
      expect(textarea.selectionStart).toBe("A ___ B ".length);
    });

    // Shift+Tab again → walks to the FIRST `___` at "A ".length = 2.
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    await waitFor(() => {
      expect(textarea.selectionStart).toBe("A ".length);
      const sel = textarea.value.slice(
        textarea.selectionStart,
        textarea.selectionEnd
      );
      expect(sel).toBe("___");
    });
  });

  it("Shift+Tab fallback: no previous blank → default browser behaviour runs", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "no blanks at all");
    textarea.focus();
    textarea.setSelectionRange(0, 0);

    const ev = new KeyboardEvent("keydown", {
      key: "Tab",
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    textarea.dispatchEvent(ev);
    // Handler left the event alone so the browser default
    // (focus previous element) runs; nothing in the textarea
    // mutated.
    expect(ev.defaultPrevented).toBe(false);
    expect(textarea.selectionStart).toBe(0);
    expect(textarea.selectionEnd).toBe(0);
  });

  it("Shift+Tab sitting ON a blank jumps to the PREVIOUS one, not the same one", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const textarea = (await screen.findByTestId(
      "note-draft-textarea"
    )) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "A ___ B ___ C");
    // Put the selection ON the SECOND `___` (index 8..11).
    const secondStart = "A ___ B ".length;
    textarea.focus();
    textarea.setSelectionRange(
      secondStart,
      secondStart + "___".length
    );

    await user.keyboard("{Shift>}{Tab}{/Shift}");
    await waitFor(() => {
      // Must have HOPPED to the FIRST `___`, not resolved back to
      // the placeholder the caret was already sitting on.
      expect(textarea.selectionStart).toBe("A ".length);
      expect(textarea.selectionEnd).toBe("A ".length + "___".length);
    });
  });

  // -------------------------------------------------------------------
  // Phase 32 — Oculoplastics pack
  // -------------------------------------------------------------------

  it("renders the new Oculoplastics group with verbatim phrasing", async () => {
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    expect(
      screen.getByTestId(
        "clinical-shortcuts-group-oculoplastics-lids-adnexa"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("clinical-shortcut-ocp-01")
    ).toHaveTextContent(/Involutional ectropion OD/i);
    expect(
      screen.getByTestId("clinical-shortcut-ocp-04")
    ).toHaveTextContent(/Aponeurotic ptosis OD with MRD1/i);
    expect(
      screen.getByTestId("clinical-shortcut-ocp-06")
    ).toHaveTextContent(/Lagophthalmos OD/i);
  });

  it("abbreviation-aware search: 'MRD1' surfaces the oculoplastics pack", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(
      screen.getByTestId("clinical-shortcuts-search"),
      "MRD1"
    );
    expect(
      screen.getByTestId(
        "clinical-shortcuts-group-oculoplastics-lids-adnexa"
      )
    ).toBeInTheDocument();
    // Retina-only groups drop out.
    expect(
      screen.queryByTestId("clinical-shortcuts-group-pvd")
    ).not.toBeInTheDocument();
  });

  it("abbreviation-aware search: 'ectropion' surfaces the relevant ocp shortcut", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    await screen.findByTestId("clinical-shortcuts-panel");
    await user.type(
      screen.getByTestId("clinical-shortcuts-search"),
      "ectropion"
    );
    expect(
      screen.getByTestId("clinical-shortcut-ocp-01")
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("clinical-shortcut-glc-01")
    ).not.toBeInTheDocument();
  });

  it("reviewer still cannot see the Oculoplastics surface", async () => {
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
      screen.queryByTestId(
        "clinical-shortcuts-group-oculoplastics-lids-adnexa"
      )
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("clinical-shortcut-ocp-01")
    ).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------
  // Phase 33 — audio intake + transcript review
  // -------------------------------------------------------------------

  it("audio upload form renders for clinicians (phase 33)", async () => {
    renderWorkspace();
    const form = await screen.findByTestId("audio-upload-form");
    expect(form).toBeInTheDocument();
    expect(
      within(form).getByTestId("audio-upload-input")
    ).toBeInTheDocument();
    const submit = within(form).getByTestId("audio-upload-submit");
    // Disabled until a file is chosen.
    expect(submit).toBeDisabled();
  });

  it("audio upload form is hidden for reviewers", async () => {
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
      screen.queryByTestId("audio-upload-form")
    ).not.toBeInTheDocument();
  });

  it("uploading audio dispatches uploadEncounterAudio and refreshes inputs", async () => {
    const user = userEvent.setup();
    renderWorkspace();
    const fileInput = (await screen.findByTestId(
      "audio-upload-input"
    )) as HTMLInputElement;
    const file = new File(["RIFF....WAVE"], "dictation.wav", {
      type: "audio/wav",
    });
    await user.upload(fileInput, file);
    await waitFor(() =>
      expect(
        screen.getByTestId("audio-upload-submit")
      ).not.toBeDisabled()
    );
    await user.click(screen.getByTestId("audio-upload-submit"));
    await waitFor(() =>
      expect(api.uploadEncounterAudio).toHaveBeenCalledWith(
        CLIN.email,
        1,
        file
      )
    );
    // Inputs list is re-fetched after upload.
    expect(api.listEncounterInputs).toHaveBeenCalled();
  });

  it("completed audio input shows the Edit transcript button", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 701,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "completed",
        transcript_text:
          "[stub-transcript] Audio ingested; placeholder transcript.",
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 2,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: "a",
        finished_at: "b",
        worker_id: "inline",
        claimed_by: null,
        claimed_at: null,
        created_at: "a",
        updated_at: "b",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-edit-701");
  });

  it("non-completed audio inputs do NOT show the Edit transcript button", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 702,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "failed",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 2,
        retry_count: 0,
        last_error: "stub forced failure",
        last_error_code: "stub_transcription_failed",
        started_at: "a",
        finished_at: "b",
        worker_id: "inline",
        claimed_by: null,
        claimed_at: null,
        created_at: "a",
        updated_at: "b",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-status-702");
    expect(
      screen.queryByTestId("transcript-edit-702")
    ).not.toBeInTheDocument();
    // Retry is still offered for failed rows.
    expect(screen.getByTestId("transcript-retry-702")).toBeInTheDocument();
  });

  it("Edit transcript modal saves via patchEncounterInputTranscript", async () => {
    const completed = {
      id: 703,
      encounter_id: 1,
      input_type: "audio_upload" as const,
      processing_status: "completed" as const,
      transcript_text: "[stub-transcript] original placeholder body.",
      confidence_summary: null,
      source_metadata: null,
      created_by_user_id: 2,
      retry_count: 0,
      last_error: null,
      last_error_code: null,
      started_at: "a",
      finished_at: "b",
      worker_id: "inline",
      claimed_by: null,
      claimed_at: null,
      created_at: "a",
      updated_at: "b",
    };
    (api.listEncounterInputs as any).mockResolvedValue([completed]);
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(await screen.findByTestId("transcript-edit-703"));
    const modal = await screen.findByTestId("transcript-edit-modal");
    const textarea = within(modal).getByTestId(
      "transcript-edit-textarea"
    ) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(
      textarea,
      "Doctor-corrected transcript. Visual acuity OD 20/40, OS 20/20."
    );
    await user.click(within(modal).getByTestId("transcript-edit-save"));
    await waitFor(() =>
      expect(api.patchEncounterInputTranscript).toHaveBeenCalledWith(
        CLIN.email,
        703,
        "Doctor-corrected transcript. Visual acuity OD 20/40, OS 20/20."
      )
    );
    // Modal closes after save.
    await waitFor(() =>
      expect(
        screen.queryByTestId("transcript-edit-modal")
      ).not.toBeInTheDocument()
    );
  });

  it("Edit transcript Save is disabled under 10 chars (provenance guard)", async () => {
    const completed = {
      id: 704,
      encounter_id: 1,
      input_type: "audio_upload" as const,
      processing_status: "completed" as const,
      transcript_text: "[stub-transcript] original body.",
      confidence_summary: null,
      source_metadata: null,
      created_by_user_id: 2,
      retry_count: 0,
      last_error: null,
      last_error_code: null,
      started_at: "a",
      finished_at: "b",
      worker_id: "inline",
      claimed_by: null,
      claimed_at: null,
      created_at: "a",
      updated_at: "b",
    };
    (api.listEncounterInputs as any).mockResolvedValue([completed]);
    const user = userEvent.setup();
    renderWorkspace();
    await user.click(await screen.findByTestId("transcript-edit-704"));
    const modal = await screen.findByTestId("transcript-edit-modal");
    const textarea = within(modal).getByTestId(
      "transcript-edit-textarea"
    ) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "short");
    expect(
      within(modal).getByTestId("transcript-edit-save")
    ).toBeDisabled();
  });

  it("generation stays blocked until an input completes (audio-aware path)", async () => {
    (api.listEncounterInputs as any).mockResolvedValue([
      {
        id: 705,
        encounter_id: 1,
        input_type: "audio_upload",
        processing_status: "processing",
        transcript_text: null,
        confidence_summary: null,
        source_metadata: null,
        created_by_user_id: 2,
        retry_count: 0,
        last_error: null,
        last_error_code: null,
        started_at: "a",
        finished_at: null,
        worker_id: "inline",
        claimed_by: null,
        claimed_at: null,
        created_at: "a",
        updated_at: "b",
      },
    ]);
    renderWorkspace();
    await screen.findByTestId("transcript-status-705");
    expect(screen.getByTestId("generate-draft")).toBeDisabled();
    // And the blocked-hint surfaces honestly.
    expect(
      screen.getByTestId("generate-blocked-note")
    ).toBeInTheDocument();
  });
});
