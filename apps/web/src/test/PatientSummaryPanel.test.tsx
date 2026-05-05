import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    listPatientSummaries: vi.fn(),
    getPatientSummary: vi.fn(),
    createPatientSummary: vi.fn(),
    updatePatientSummary: vi.fn(),
    reviewPatientSummary: vi.fn(),
    finalizePatientSummary: vi.fn(),
    discardPatientSummary: vi.fn(),
  };
});

import {
  ApiError,
  PatientSummary,
  createPatientSummary,
  discardPatientSummary,
  finalizePatientSummary,
  getPatientSummary,
  listPatientSummaries,
  reviewPatientSummary,
  updatePatientSummary,
} from "../api";
import { PatientSummaryPanel } from "../PatientSummaryPanel";

const mockedList = vi.mocked(listPatientSummaries);
const mockedGet = vi.mocked(getPatientSummary);
const mockedCreate = vi.mocked(createPatientSummary);
const mockedUpdate = vi.mocked(updatePatientSummary);
const mockedReview = vi.mocked(reviewPatientSummary);
const mockedFinalize = vi.mocked(finalizePatientSummary);
const mockedDiscard = vi.mocked(discardPatientSummary);

function makeSummary(overrides: Partial<PatientSummary> = {}): PatientSummary {
  return {
    id: 21,
    organization_id: 1,
    patient_id: 7,
    encounter_id: 42,
    scribe_session_id: null,
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
    created_at: "2026-05-05T17:00:00+00:00",
    updated_at: "2026-05-05T17:00:00+00:00",
    is_terminal: false,
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <PatientSummaryPanel
      identity="clin@chartnav.local"
      patientId={7}
      encounterId={42}
    />
  );
}

describe("PatientSummaryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the provider-review banner copy and never sends to patient", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    const banner = await screen.findByTestId("patient-summary-banner-copy");
    expect(banner).toHaveTextContent(/provider review required/i);
    expect(banner).toHaveTextContent(/Do not send to patient/i);
    // Sanity: never any send-to-patient action.
    expect(
      screen.queryByRole("button", { name: /send to patient/i })
    ).not.toBeInTheDocument();
  });

  it("lists summaries for the patient", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeSummary({ id: 21, status: "draft" }),
        makeSummary({ id: 22, status: "reviewed" }),
        makeSummary({ id: 23, status: "finalized", is_terminal: true }),
      ],
      total: 3,
    });
    renderPanel();

    await waitFor(() => {
      expect(mockedList).toHaveBeenCalledWith("clin@chartnav.local", 7);
    });
    expect(await screen.findByTestId("patient-summary-load-21")).toHaveTextContent(
      "Draft"
    );
    expect(screen.getByTestId("patient-summary-load-22")).toHaveTextContent(
      "Reviewed"
    );
    expect(screen.getByTestId("patient-summary-load-23")).toHaveTextContent(
      "Finalized"
    );
  });

  it("creates a draft with optional scribe session and provider instructions", async () => {
    mockedList.mockResolvedValue({ items: [], total: 0 });
    mockedCreate.mockResolvedValueOnce(
      makeSummary({
        id: 50,
        status: "draft",
        scribe_session_id: 99,
        plain_language_summary: "Generated draft body.",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    const scribe = await screen.findByTestId<HTMLInputElement>(
      "patient-summary-scribe-id"
    );
    fireEvent.change(scribe, { target: { value: "99" } });
    const instr = screen.getByTestId<HTMLTextAreaElement>(
      "patient-summary-provider-instructions"
    );
    fireEvent.change(instr, {
      target: { value: "Mention the dilation slowed her vision." },
    });

    await user.click(screen.getByTestId("patient-summary-create"));

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledTimes(1);
    });
    const [emailArg, patientArg, payload] = mockedCreate.mock.calls[0];
    expect(emailArg).toBe("clin@chartnav.local");
    expect(patientArg).toBe(7);
    expect(payload.encounter_id).toBe(42);
    expect(payload.scribe_session_id).toBe(99);
    expect(payload.provider_instructions).toMatch(/dilation/i);
    // After create, status badge shows Draft.
    expect(
      await screen.findByTestId("patient-summary-status-badge")
    ).toHaveTextContent("Draft");
  });

  it("loads an existing summary into the editor", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSummary({ id: 21 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        plain_language_summary: "Your eye was checked today.",
        key_findings: ["pressure normal", "lenses clear"],
        next_steps: ["follow up in 1 year"],
        questions: ["any new floaters?"],
        review_notes: "looks fine",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("clin@chartnav.local", 7, 21);
    });
    expect(
      screen.getByTestId<HTMLTextAreaElement>(
        "patient-summary-plain-language"
      ).value
    ).toMatch(/checked today/);
    expect(
      screen.getByTestId<HTMLTextAreaElement>(
        "patient-summary-key-findings"
      ).value
    ).toBe("pressure normal\nlenses clear");
    expect(
      screen.getByTestId<HTMLTextAreaElement>("patient-summary-next-steps").value
    ).toBe("follow up in 1 year");
    expect(
      screen.getByTestId<HTMLTextAreaElement>("patient-summary-questions").value
    ).toBe("any new floaters?");
    expect(
      screen.getByTestId<HTMLTextAreaElement>(
        "patient-summary-review-notes"
      ).value
    ).toBe("looks fine");
    expect(screen.getByTestId("patient-summary-status-badge")).toHaveTextContent(
      "Draft"
    );
  });

  it("updates a draft summary", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSummary({ id: 21 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(makeSummary({ id: 21 }));
    mockedUpdate.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        plain_language_summary: "Edited summary.",
        key_findings: ["item one", "item two"],
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));

    const plain = screen.getByTestId<HTMLTextAreaElement>(
      "patient-summary-plain-language"
    );
    fireEvent.change(plain, { target: { value: "Edited summary." } });
    const findings = screen.getByTestId<HTMLTextAreaElement>(
      "patient-summary-key-findings"
    );
    fireEvent.change(findings, { target: { value: "item one\nitem two\n" } });

    await user.click(screen.getByTestId("patient-summary-update"));

    await waitFor(() => {
      expect(mockedUpdate).toHaveBeenCalledTimes(1);
    });
    const updateCall = mockedUpdate.mock.calls[0];
    expect(updateCall[2]).toBe(21);
    const payload = updateCall[3];
    expect(payload.plain_language_summary).toBe("Edited summary.");
    // textToLines trims and drops empty trailing lines.
    expect(payload.key_findings).toEqual(["item one", "item two"]);
  });

  it("reviews a draft summary", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSummary({ id: 21 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(makeSummary({ id: 21 }));
    mockedReview.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        status: "reviewed",
        reviewed_at: "2026-05-05T18:00:00+00:00",
        reviewed_by_user_id: 2,
        review_notes: "ok",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));

    const notes = screen.getByTestId<HTMLTextAreaElement>(
      "patient-summary-review-notes"
    );
    fireEvent.change(notes, { target: { value: "ok" } });

    await user.click(screen.getByTestId("patient-summary-review"));

    await waitFor(() => {
      expect(mockedReview).toHaveBeenCalledTimes(1);
    });
    const reviewCall = mockedReview.mock.calls[0];
    expect(reviewCall[2]).toBe(21);
    expect(reviewCall[3]?.review_notes).toBe("ok");
    expect(screen.getByTestId("patient-summary-status-badge")).toHaveTextContent(
      "Reviewed"
    );
    // Now the Finalize button shows up; the Review button is gone.
    expect(screen.getByTestId("patient-summary-finalize")).toBeInTheDocument();
    expect(
      screen.queryByTestId("patient-summary-review")
    ).not.toBeInTheDocument();
  });

  it("finalizes a reviewed summary and switches to read-only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSummary({ id: 21, status: "reviewed" })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSummary({ id: 21, status: "reviewed" })
    );
    mockedFinalize.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        status: "finalized",
        is_terminal: true,
        finalized_at: "2026-05-05T19:00:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));
    await user.click(screen.getByTestId("patient-summary-finalize"));

    await waitFor(() => {
      expect(mockedFinalize).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId("patient-summary-status-badge")).toHaveTextContent(
      "Finalized"
    );
    expect(
      screen.getByTestId("patient-summary-readonly-warning")
    ).toBeInTheDocument();
    // No write actions visible.
    expect(
      screen.queryByTestId("patient-summary-update")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("patient-summary-review")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("patient-summary-finalize")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("patient-summary-discard")
    ).not.toBeInTheDocument();
  });

  it("discards a draft summary", async () => {
    mockedList.mockResolvedValueOnce({
      items: [makeSummary({ id: 21 })],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(makeSummary({ id: 21 }));
    mockedDiscard.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        status: "discarded",
        is_terminal: true,
        discarded_at: "2026-05-05T19:00:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));
    await user.click(screen.getByTestId("patient-summary-discard"));

    await waitFor(() => {
      expect(mockedDiscard).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId("patient-summary-status-badge")).toHaveTextContent(
      "Discarded"
    );
    expect(
      screen.getByTestId("patient-summary-readonly-warning")
    ).toBeInTheDocument();
  });

  it("finalized summary is read-only (textareas disabled, no actions)", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeSummary({
          id: 21,
          status: "finalized",
          is_terminal: true,
          finalized_at: "2026-05-05T19:00:00+00:00",
        }),
      ],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        status: "finalized",
        is_terminal: true,
        finalized_at: "2026-05-05T19:00:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));

    expect(
      (
        screen.getByTestId(
          "patient-summary-plain-language"
        ) as HTMLTextAreaElement
      ).disabled
    ).toBe(true);
    expect(
      (
        screen.getByTestId(
          "patient-summary-key-findings"
        ) as HTMLTextAreaElement
      ).disabled
    ).toBe(true);
    expect(
      screen.queryByTestId("patient-summary-update")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("patient-summary-finalize")
    ).not.toBeInTheDocument();
  });

  it("discarded summary is read-only", async () => {
    mockedList.mockResolvedValueOnce({
      items: [
        makeSummary({
          id: 21,
          status: "discarded",
          is_terminal: true,
          discarded_at: "2026-05-05T19:00:00+00:00",
        }),
      ],
      total: 1,
    });
    mockedGet.mockResolvedValueOnce(
      makeSummary({
        id: 21,
        status: "discarded",
        is_terminal: true,
        discarded_at: "2026-05-05T19:00:00+00:00",
      })
    );

    renderPanel();
    const user = userEvent.setup();
    await user.click(await screen.findByTestId("patient-summary-load-21"));

    expect(
      (
        screen.getByTestId(
          "patient-summary-plain-language"
        ) as HTMLTextAreaElement
      ).disabled
    ).toBe(true);
    expect(
      screen.queryByTestId("patient-summary-discard")
    ).not.toBeInTheDocument();
  });

  it("API error shows a safe banner message and exposes the error code", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    mockedCreate.mockRejectedValueOnce(
      new ApiError(
        404,
        "scribe_session_not_found",
        "scribe session not found in your organization for this patient"
      )
    );

    renderPanel();
    const user = userEvent.setup();
    await screen.findByTestId("patient-summary-empty");
    const scribe = screen.getByTestId<HTMLInputElement>(
      "patient-summary-scribe-id"
    );
    fireEvent.change(scribe, { target: { value: "999" } });
    await user.click(screen.getByTestId("patient-summary-create"));

    const banner = await screen.findByTestId("patient-summary-banner");
    expect(banner).toHaveTextContent(/Create failed/);
    expect(banner).toHaveTextContent(/scribe_session_not_found/);
    // Banner must not include words that imply autonomous decisioning.
    expect(banner.textContent).not.toMatch(/autonomous/i);
  });

  it("does not contain autonomous-diagnosis language, external-LLM names, or any patient-send action", async () => {
    mockedList.mockResolvedValueOnce({ items: [], total: 0 });
    renderPanel();
    await screen.findByTestId("patient-summary-empty");
    const root = screen.getByTestId("patient-summary-panel");
    expect(root.textContent).not.toMatch(/autonomous/i);
    expect(root.textContent).not.toMatch(/diagnos/i);
    expect(root.textContent).not.toMatch(/openai|anthropic|gpt|llm/i);
    // No send-to-patient action of any flavor.
    expect(
      screen.queryByRole("button", { name: /send/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /email/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /portal/i })
    ).not.toBeInTheDocument();
  });
});
