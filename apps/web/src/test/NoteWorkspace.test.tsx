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
});
