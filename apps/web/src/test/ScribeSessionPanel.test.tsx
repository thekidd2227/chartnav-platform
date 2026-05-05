import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    listPatientScribeSessions: vi.fn(),
    getPatientScribeSession: vi.fn(),
    createPatientScribeSession: vi.fn(),
    updatePatientScribeSession: vi.fn(),
    processPatientScribeSession: vi.fn(),
    reviewPatientScribeSession: vi.fn(),
    finalizePatientScribeSession: vi.fn(),
    discardPatientScribeSession: vi.fn(),
  };
});

import {
  ApiError,
  ScribeSession,
  createPatientScribeSession,
  discardPatientScribeSession,
  finalizePatientScribeSession,
  getPatientScribeSession,
  listPatientScribeSessions,
  processPatientScribeSession,
  reviewPatientScribeSession,
  updatePatientScribeSession,
} from "../api";
import { ScribeSessionPanel } from "../ScribeSessionPanel";

const mockedList = vi.mocked(listPatientScribeSessions);
const mockedGet = vi.mocked(getPatientScribeSession);
const mockedCreate = vi.mocked(createPatientScribeSession);
const mockedUpdate = vi.mocked(updatePatientScribeSession);
const mockedProcess = vi.mocked(processPatientScribeSession);
const mockedReview = vi.mocked(reviewPatientScribeSession);
const mockedFinalize = vi.mocked(finalizePatientScribeSession);
const mockedDiscard = vi.mocked(discardPatientScribeSession);

function makeSession(overrides: Partial<ScribeSession> = {}): ScribeSession {
  return {
    id: 11,
    organization_id: 1,
    patient_id: 7,
    encounter_id: null,
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
    created_at: "2026-05-04T23:00:00+00:00",
    updated_at: "2026-05-04T23:00:00+00:00",
    is_terminal: false,
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <ScribeSessionPanel
      identity="clin@chartnav.local"
      patientId={7}
      encounterId={42}
    />
  );
}

describe("ScribeSessionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the provider-review banner copy", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    const banner = await screen.findByTestId("scribe-session-banner-copy");
    expect(banner).toHaveTextContent(/Draft — provider review required/i);
    expect(banner).toHaveTextContent(/Nothing is finalized until/i);
    // Sanity: no autonomous-diagnosis copy.
    expect(banner.textContent).not.toMatch(/autonomous/i);
    expect(banner.textContent).not.toMatch(/diagnos/i);
  });

  it("lists sessions for the patient", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeSession({ id: 11, status: "draft" }),
        makeSession({ id: 12, status: "ready_for_review" }),
      ],
      total: 2,
    });
    renderPanel();

    await waitFor(() => {
      expect(mockedList).toHaveBeenCalledWith("clin@chartnav.local", 7);
    });
    expect(await screen.findByTestId("scribe-session-load-11")).toHaveTextContent("Draft");
    expect(screen.getByTestId("scribe-session-load-12")).toHaveTextContent("Ready for review");
  });

  it("creates a session with source/transcript text", async () => {
    mockedList.mockResolvedValue({ items: [], total: 0 });
    mockedCreate.mockResolvedValueOnce(makeSession({ id: 50, status: "draft" }));

    renderPanel();
    const user = userEvent.setup();
    const source = await screen.findByTestId<HTMLTextAreaElement>(
      "scribe-session-source-text"
    );
    fireEvent.change(source, {
      target: { value: "Chief complaint: blurry vision OD." },
    });
    const transcript = screen.getByTestId<HTMLTextAreaElement>(
      "scribe-session-transcript-text"
    );
    fireEvent.change(transcript, { target: { value: "audio dictation transcript" } });

    await user.click(screen.getByTestId("scribe-session-create"));

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledTimes(1);
    });
    const [emailArg, patientArg, payload] = mockedCreate.mock.calls[0];
    expect(emailArg).toBe("clin@chartnav.local");
    expect(patientArg).toBe(7);
    expect(payload.source_text).toContain("blurry vision");
    expect(payload.transcript_text).toContain("audio dictation");
    expect(payload.encounter_id).toBe(42);
    expect(payload.input_mode).toBe("pasted_text");
  });

  it("loads an existing session into the editor", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSession({ id: 11 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSession({
        id: 11,
        source_text: "Chief complaint: red eye.",
        review_notes: "looks ok",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("clin@chartnav.local", 7, 11);
    });
    expect(
      screen.getByTestId<HTMLTextAreaElement>("scribe-session-source-text").value
    ).toBe("Chief complaint: red eye.");
    expect(
      screen.getByTestId<HTMLTextAreaElement>("scribe-session-review-notes").value
    ).toBe("looks ok");
    expect(screen.getByTestId("scribe-session-status-badge")).toHaveTextContent(
      "Draft"
    );
  });

  it("updates a draft session", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSession({ id: 11 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(makeSession({ id: 11 }));
    mockedUpdate.mockResolvedValueOnce(
      makeSession({ id: 11, source_text: "edited" })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));

    const source = screen.getByTestId<HTMLTextAreaElement>(
      "scribe-session-source-text"
    );
    fireEvent.change(source, { target: { value: "edited" } });

    await user.click(screen.getByTestId("scribe-session-update"));

    await waitFor(() => {
      expect(mockedUpdate).toHaveBeenCalledTimes(1);
    });
    const [, , sessionIdArg, payload] = mockedUpdate.mock.calls[0];
    expect(sessionIdArg).toBe(11);
    expect(payload.source_text).toBe("edited");
  });

  it("processes a draft and shows the draft note + structured sections", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSession({ id: 11 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSession({
        id: 11,
        source_text: "Chief complaint: red eye.\nPlan: refraction.",
      })
    );
    mockedProcess.mockResolvedValueOnce(
      makeSession({
        id: 11,
        status: "ready_for_review",
        draft_note_text:
          "Draft — provider review required\n\nChief complaint:\nred eye.\n\nPlan:\nrefraction.",
        structured_note_json: {
          chief_complaint: "red eye.",
          plan: "refraction.",
        },
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));
    await user.click(screen.getByTestId("scribe-session-process"));

    await waitFor(() => {
      expect(mockedProcess).toHaveBeenCalledTimes(1);
    });
    const draft = await screen.findByTestId("scribe-session-draft-note");
    expect(draft).toHaveTextContent("Draft — provider review required");
    expect(
      screen.getByTestId("scribe-session-section-chief_complaint")
    ).toHaveTextContent("red eye");
    expect(
      screen.getByTestId("scribe-session-section-plan")
    ).toHaveTextContent("refraction");
    expect(screen.getByTestId("scribe-session-status-badge")).toHaveTextContent(
      "Ready for review"
    );
  });

  it("reviews a ready_for_review session", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSession({ id: 11, status: "ready_for_review" })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSession({ id: 11, status: "ready_for_review" })
    );
    mockedReview.mockResolvedValueOnce(
      makeSession({ id: 11, status: "reviewed", review_notes: "lgtm" })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));

    const notes = screen.getByTestId<HTMLTextAreaElement>(
      "scribe-session-review-notes"
    );
    fireEvent.change(notes, { target: { value: "lgtm" } });

    await user.click(screen.getByTestId("scribe-session-review"));

    await waitFor(() => {
      expect(mockedReview).toHaveBeenCalledTimes(1);
    });
    const reviewCall = mockedReview.mock.calls[0];
    expect(reviewCall[2]).toBe(11);
    expect(reviewCall[3]).toBeDefined();
    expect(reviewCall[3]?.review_notes).toBe("lgtm");
    expect(screen.getByTestId("scribe-session-status-badge")).toHaveTextContent(
      "Reviewed"
    );
  });

  it("finalizes a reviewed session", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSession({ id: 11, status: "reviewed" })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(makeSession({ id: 11, status: "reviewed" }));
    mockedFinalize.mockResolvedValueOnce(
      makeSession({
        id: 11,
        status: "finalized",
        is_terminal: true,
        finalized_at: "2026-05-04T23:30:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));
    await user.click(screen.getByTestId("scribe-session-finalize"));

    await waitFor(() => {
      expect(mockedFinalize).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId("scribe-session-status-badge")).toHaveTextContent(
      "Finalized"
    );
    // Read-only mode reflected.
    expect(
      screen.getByTestId("scribe-session-readonly-warning")
    ).toBeInTheDocument();
    // No write actions visible.
    expect(screen.queryByTestId("scribe-session-update")).not.toBeInTheDocument();
    expect(screen.queryByTestId("scribe-session-finalize")).not.toBeInTheDocument();
    expect(screen.queryByTestId("scribe-session-discard")).not.toBeInTheDocument();
  });

  it("discards a draft session", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSession({ id: 11 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(makeSession({ id: 11 }));
    mockedDiscard.mockResolvedValueOnce(
      makeSession({
        id: 11,
        status: "discarded",
        is_terminal: true,
        discarded_at: "2026-05-04T23:30:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));
    await user.click(screen.getByTestId("scribe-session-discard"));

    await waitFor(() => {
      expect(mockedDiscard).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId("scribe-session-status-badge")).toHaveTextContent(
      "Discarded"
    );
    expect(
      screen.getByTestId("scribe-session-readonly-warning")
    ).toBeInTheDocument();
  });

  it("finalized session is read-only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeSession({
          id: 11,
          status: "finalized",
          is_terminal: true,
          finalized_at: "2026-05-04T23:30:00+00:00",
        }),
      ],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSession({
        id: 11,
        status: "finalized",
        is_terminal: true,
        finalized_at: "2026-05-04T23:30:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));

    expect(
      (screen.getByTestId("scribe-session-source-text") as HTMLTextAreaElement)
        .disabled
    ).toBe(true);
    expect(
      screen.queryByTestId("scribe-session-update")
    ).not.toBeInTheDocument();
  });

  it("discarded session is read-only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeSession({
          id: 11,
          status: "discarded",
          is_terminal: true,
          discarded_at: "2026-05-04T23:30:00+00:00",
        }),
      ],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSession({
        id: 11,
        status: "discarded",
        is_terminal: true,
        discarded_at: "2026-05-04T23:30:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("scribe-session-load-11"));

    expect(
      (screen.getByTestId("scribe-session-source-text") as HTMLTextAreaElement)
        .disabled
    ).toBe(true);
    expect(
      screen.queryByTestId("scribe-session-process")
    ).not.toBeInTheDocument();
  });

  it("API error shows a safe banner message", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    mockedCreate.mockRejectedValueOnce(
      new ApiError(409, "scribe_session_invalid_transition", "cannot finalize from draft")
    );

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("scribe-session-empty");

    const source = screen.getByTestId<HTMLTextAreaElement>(
      "scribe-session-source-text"
    );
    fireEvent.change(source, { target: { value: "x" } });
    await user.click(screen.getByTestId("scribe-session-create"));

    const banner = await screen.findByTestId("scribe-session-banner");
    expect(banner).toHaveTextContent(/Create failed/);
    expect(banner).toHaveTextContent(/scribe_session_invalid_transition/);
    // The banner must not include words that imply autonomous decisioning.
    expect(banner.textContent).not.toMatch(/autonomous/i);
  });

  it("does not contain autonomous-diagnosis or external-LLM language", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    await screen.findByTestId("scribe-session-empty");
    const root = screen.getByTestId("scribe-session-panel");
    expect(root.textContent).not.toMatch(/autonomous/i);
    expect(root.textContent).not.toMatch(/diagnos/i);
    expect(root.textContent).not.toMatch(/openai|anthropic|gpt|llm/i);
  });
});
