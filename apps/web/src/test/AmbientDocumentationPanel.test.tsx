import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/ambient/ambientApi", () => ({
  listScribeSessions: vi.fn(),
  createScribeSession: vi.fn(),
  getScribeSession: vi.fn(),
  draftAmbientSession: vi.fn(),
  reviewScribeSession: vi.fn(),
  finalizeScribeSession: vi.fn(),
}));

import {
  listScribeSessions,
  createScribeSession,
  getScribeSession,
  draftAmbientSession,
  reviewScribeSession,
  finalizeScribeSession,
} from "../features/ambient/ambientApi";
import { AmbientDocumentationPanel } from "../features/ambient/AmbientDocumentationPanel";
import type {
  AmbientDraftPayload,
  ScribeSessionResponse,
  ScribeSessionWithAmbientDraft,
} from "../features/ambient/ambientTypes";

const baseSession = (
  over: Partial<ScribeSessionResponse> = {},
): ScribeSessionResponse => ({
  id: 7,
  organization_id: 1,
  patient_id: 42,
  encounter_id: 9,
  created_by_user_id: 1,
  status: "draft",
  input_mode: "transcript",
  source_text: null,
  transcript_text: "Demo transcript only. VA 20/40 OD.",
  draft_note_text: null,
  structured_note_json: null,
  linked_artifact_id: null,
  review_notes: null,
  finalized_at: null,
  reviewed_at: null,
  reviewed_by_user_id: null,
  discarded_at: null,
  created_at: "2026-05-19T17:00:00Z",
  updated_at: "2026-05-19T17:00:00Z",
  is_terminal: false,
  ...over,
});

const baseDraft = (
  over: Partial<AmbientDraftPayload> = {},
): AmbientDraftPayload => ({
  structured_facts: {
    chief_complaint: "blurry vision in the right eye for two weeks",
    hpi_summary: "Two-week history of right-eye blurry vision.",
    visual_acuity: "20/40 OD, 20/25 OS",
    iop: "18 OD, 16 OS",
    imaging_metadata: "OCT macula metadata available for review",
    assessment_context: "Provider to confirm.",
    plan_as_stated:
      "Follow-up discussed; no treatment order placed in this demo.",
  },
  draft_note: "DRAFT — provider review required. body…",
  safety_flags: [],
  missing_information: [],
  requires_provider_review: true,
  forbidden_actions: {
    diagnosis: false,
    orders: false,
    referrals: false,
    patient_message: false,
    billing_or_coding: false,
    auto_sign: false,
    image_interpretation: false,
  },
  ai_model_name: "ambient_rule_based_v1",
  confidence: {},
  ...over,
});

const baseSessionWithDraft = (
  sessionOver: Partial<ScribeSessionResponse> = {},
  draftOver: Partial<AmbientDraftPayload> = {},
): ScribeSessionWithAmbientDraft => ({
  ...baseSession({ status: "ready_for_review", ...sessionOver }),
  ambient_draft: baseDraft(draftOver),
});

beforeEach(() => {
  vi.mocked(listScribeSessions).mockReset();
  vi.mocked(createScribeSession).mockReset();
  vi.mocked(getScribeSession).mockReset();
  vi.mocked(draftAmbientSession).mockReset();
  vi.mocked(reviewScribeSession).mockReset();
  vi.mocked(finalizeScribeSession).mockReset();
});

describe("AmbientDocumentationPanel — empty state + safety", () => {
  it("renders the safety banner with all required clauses", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    render(<AmbientDocumentationPanel patientId={42} encounterId={9} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list-empty")).toBeInTheDocument(),
    );
    const banner = screen.getByTestId("ambient-safety-banner");
    expect(banner.textContent).toMatch(/Draft from fake\/demo encounter transcript/i);
    expect(banner.textContent).toMatch(/Provider review required/i);
    expect(banner.textContent).toMatch(/Does not diagnose/i);
    expect(banner.textContent).toMatch(/Does not place orders/i);
    expect(banner.textContent).toMatch(/Does not send referrals or patient messages/i);
    expect(banner.textContent).toMatch(/Does not bill or code/i);
    expect(banner.textContent).toMatch(/Not for real PHI/i);
  });

  it("renders empty list + empty preview when there are no sessions", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ambient-draft-empty")).toBeInTheDocument();
    expect(
      screen.getByTestId("ambient-list-empty").textContent,
    ).toMatch(/Paste a fake \/ demo transcript/i);
  });

  it("Generate button is disabled until a transcript is entered", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-generate-btn")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ambient-generate-btn")).toBeDisabled();
    await userEvent.type(
      screen.getByTestId("ambient-transcript-text"),
      "Demo transcript only. VA 20/40 OD.",
    );
    expect(screen.getByTestId("ambient-generate-btn")).not.toBeDisabled();
  });

  it("clicking the demo sample button populates the textarea with fake data", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-sample-btn")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-sample-btn"));
    const ta = screen.getByTestId(
      "ambient-transcript-text",
    ) as HTMLTextAreaElement;
    expect(ta.value).toMatch(/Demo transcript only/);
    expect(ta.value).toMatch(/20\/40 OD/);
    // The sample MUST NOT include any real-PHI shapes.
    expect(ta.value.toLowerCase()).not.toMatch(/ssn/);
    expect(ta.value.toLowerCase()).not.toMatch(/mrn[: ]?\d/);
    expect(ta.value.toLowerCase()).not.toMatch(/dob[: ]/);
  });
});

describe("AmbientDocumentationPanel — generate flow", () => {
  it("creates a session, drafts via the ambient endpoint, and selects the result", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    vi.mocked(createScribeSession).mockResolvedValueOnce(baseSession());
    vi.mocked(draftAmbientSession).mockResolvedValueOnce(
      baseSessionWithDraft(),
    );

    render(<AmbientDocumentationPanel patientId={42} encounterId={9} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-generate-btn")).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByTestId("ambient-sample-btn"));
    await userEvent.click(screen.getByTestId("ambient-generate-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("ambient-draft-editor")).toBeInTheDocument(),
    );
    expect(createScribeSession).toHaveBeenCalledWith(42, {
      input_mode: "transcript",
      transcript_text: expect.stringMatching(/Demo transcript only/),
      encounter_id: 9,
    });
    expect(draftAmbientSession).toHaveBeenCalledWith(42, 7, {
      fake_data_context: true,
    });
  });

  it("generate failure preserves the typed transcript text", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    vi.mocked(createScribeSession).mockRejectedValueOnce(
      new Error("HTTP 500 upstream blew up"),
    );

    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-generate-btn")).toBeInTheDocument(),
    );

    const userText = "Demo transcript only. VA 20/40 OD.";
    await userEvent.type(
      screen.getByTestId("ambient-transcript-text"),
      userText,
    );
    await userEvent.click(screen.getByTestId("ambient-generate-btn"));

    await waitFor(() =>
      expect(screen.getByTestId("ambient-error")).toBeInTheDocument(),
    );
    expect(
      (screen.getByTestId("ambient-transcript-text") as HTMLTextAreaElement).value,
    ).toBe(userText);
  });
});

describe("AmbientDocumentationPanel — draft editor", () => {
  it("renders structured facts, safety flags, missing info, and forbidden-actions summary", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft(
        {},
        {
          safety_flags: ["Transcript references orders; not executed."],
          missing_information: ["IOP not stated; provider to confirm."],
        },
      ),
    );

    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-draft-editor")).toBeInTheDocument(),
    );

    // Structured facts.
    expect(
      screen.getByTestId("ambient-fact-chief_complaint").textContent,
    ).toMatch(/blurry vision/i);
    expect(
      screen.getByTestId("ambient-fact-visual_acuity").textContent,
    ).toMatch(/20\/40 OD/);
    expect(
      screen.getByTestId("ambient-fact-iop").textContent,
    ).toMatch(/18 OD/);

    // Safety flag + missing info populated.
    expect(
      screen.getByTestId("ambient-safety-flag-0").textContent,
    ).toMatch(/orders/i);
    expect(
      screen.getByTestId("ambient-missing-item-0").textContent,
    ).toMatch(/IOP/);

    // Forbidden-actions summary lists every key with value false.
    for (const key of [
      "diagnosis",
      "orders",
      "referrals",
      "patient_message",
      "billing_or_coding",
      "auto_sign",
      "image_interpretation",
    ]) {
      const el = screen.getByTestId(`ambient-forbidden-${key}`);
      expect(el.textContent).toMatch(/false/);
    }
  });

  it("status timeline marks Ready for Review for a freshly drafted session", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "ready_for_review" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-status-timeline")).toBeInTheDocument(),
    );
    expect(
      screen
        .getByTestId("ambient-status-step-draft")
        .getAttribute("data-active"),
    ).toBe("true");
    expect(
      screen
        .getByTestId("ambient-status-step-ready_for_review")
        .getAttribute("data-active"),
    ).toBe("true");
    expect(
      screen
        .getByTestId("ambient-status-step-reviewed")
        .getAttribute("data-active"),
    ).toBe("false");
    expect(
      screen
        .getByTestId("ambient-status-step-finalized")
        .getAttribute("data-active"),
    ).toBe("false");
  });

  it("Mark Reviewed flips status to reviewed and exposes the attestation block", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "ready_for_review" }),
    );
    vi.mocked(reviewScribeSession).mockResolvedValueOnce(
      baseSession({
        status: "reviewed",
        reviewed_at: "2026-05-19T17:30:00Z",
        reviewed_by_user_id: 1,
      }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-review-btn")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-review-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-attestation-block")).toBeInTheDocument(),
    );
    expect(reviewScribeSession).toHaveBeenCalledWith(42, 7, {});
  });

  it("Sign & Lock is disabled until the attestation checkbox is ticked", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "reviewed" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-sign-btn")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ambient-sign-btn")).toBeDisabled();
    await userEvent.click(screen.getByTestId("ambient-attestation-checkbox"));
    expect(screen.getByTestId("ambient-sign-btn")).not.toBeDisabled();
  });

  it("attestation block contains the immutability + review language", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "reviewed" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-attestation-block")).toBeInTheDocument(),
    );
    const block = screen.getByTestId("ambient-attestation-block");
    expect(block.textContent).toMatch(/I attest/);
    expect(block.textContent).toMatch(/Signing will lock the draft/);
    expect(block.textContent).toMatch(/immutable/);
  });

  it("clicking sign with attestation invokes finalizeScribeSession", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "reviewed" }),
    );
    vi.mocked(finalizeScribeSession).mockResolvedValueOnce(
      baseSession({
        status: "finalized",
        finalized_at: "2026-05-19T17:45:00Z",
        is_terminal: true,
      }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-sign-btn")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-attestation-checkbox"));
    await userEvent.click(screen.getByTestId("ambient-sign-btn"));
    await waitFor(() =>
      expect(finalizeScribeSession).toHaveBeenCalledWith(42, 7),
    );
  });

  it("signed draft renders the locked banner and hides edit controls", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({
        status: "finalized",
        finalized_at: "2026-05-19T17:45:00Z",
        is_terminal: true,
      }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-signed-lock")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("ambient-review-btn")).toBeNull();
    expect(screen.queryByTestId("ambient-sign-btn")).toBeNull();
    expect(screen.queryByTestId("ambient-attestation-block")).toBeNull();
    expect(
      screen.getByTestId("ambient-signed-lock").textContent,
    ).toMatch(/Signed drafts are immutable/i);
  });
});

describe("AmbientDocumentationPanel — claim safety sweep", () => {
  it("does not surface forbidden positive phrasings anywhere in the rendered UI", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({}),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-draft-editor")).toBeInTheDocument(),
    );

    const body = (document.body.textContent ?? "").toLowerCase();

    // Forbidden positive phrasings (the panel must never imply any
    // of these). Negative phrasings ("not diagnosis", "does not diagnose")
    // are required and allowed.
    expect(body).not.toMatch(/hands-free scribing/);
    expect(body).not.toMatch(/automatic charting/);
    expect(body).not.toMatch(/chart fills itself/);
    expect(body).not.toMatch(/note writes itself/);
    expect(body).not.toMatch(/autonomous documentation/);
    expect(body).not.toMatch(/ambient scribe parity/);
    expect(body).not.toMatch(/ai writes the note/);
    expect(body).not.toMatch(/openai-powered clinical documentation/);
    expect(body).not.toMatch(/production llm documentation/);
    expect(body).not.toMatch(/real phi ready/);
    expect(body).not.toMatch(/hipaa compliant/);
    expect(body).not.toMatch(/ehr replacement/);
    expect(body).not.toMatch(/coding recommendation/);
    expect(body).not.toMatch(/billing-aware coding/);
    expect(body).not.toMatch(/automatically signed/);
    expect(body).not.toMatch(/auto-signed/);
  });
});

// ---------------------------------------------------------------
// Phase 59 — explicit safety-copy assertions
// ---------------------------------------------------------------

describe("AmbientDocumentationPanel — Phase 59 safety copy", () => {
  it("renders every required safety-banner clause as an explicit substring", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([]);
    render(<AmbientDocumentationPanel patientId={42} encounterId={9} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-safety-banner")).toBeInTheDocument(),
    );
    const banner = screen.getByTestId("ambient-safety-banner").textContent ?? "";
    // Each clause is asserted individually so a future copy edit that
    // drops one fails an obvious test.
    expect(banner).toMatch(/Provider review required/i);
    expect(banner).toMatch(/Not for real PHI/i);
    expect(banner).toMatch(/Does not diagnose/i);
    expect(banner).toMatch(/Does not place orders/i);
    expect(banner).toMatch(/Does not send referrals or patient messages/i);
    expect(banner).toMatch(/Does not bill or code/i);
  });

  it("'What ChartNav did NOT do' card lists every forbidden action with (false)", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(baseSessionWithDraft());
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-actions-summary")).toBeInTheDocument(),
    );
    const card = screen.getByTestId("ambient-actions-summary").textContent ?? "";
    // The literal "(false)" appears for every key so the demo
    // narrator can read it aloud.
    const required = [
      "diagnosis",
      "orders",
      "referrals",
      "patient messages",
      "billing or coding",
      "auto-sign",
      "image interpretation",
    ];
    for (const action of required) {
      expect(card.toLowerCase()).toContain(action);
    }
    // Each forbidden-actions list item carries "(false)".
    const falseCount = (card.match(/\(false\)/gi) ?? []).length;
    expect(falseCount).toBe(7);
  });

  it("Review button is labelled distinctly from Sign and not the final signature", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "ready_for_review" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-review-btn")).toBeInTheDocument(),
    );
    const reviewLabel = screen.getByTestId("ambient-review-btn").textContent ?? "";
    expect(reviewLabel).toMatch(/Mark Reviewed/i);
    expect(reviewLabel).not.toMatch(/Sign/i);
    // Sign button is not visible until the reviewed state is reached.
    expect(screen.queryByTestId("ambient-sign-btn")).toBeNull();
  });

  it("attestation block text contains 'attest' and references immutability", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "reviewed" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-attestation-block")).toBeInTheDocument(),
    );
    const block = screen.getByTestId("ambient-attestation-block").textContent ?? "";
    expect(block).toMatch(/attest/i);
    expect(block).toMatch(/signing will lock the draft/i);
    expect(block).toMatch(/immutable/i);
    expect(block).toMatch(/fake \/ demo transcript/i);
  });

  it("Phase 59 — forbidden positive phrasings (extended) are absent everywhere in the rendered UI", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([baseSession()]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({
        status: "ready_for_review",
      }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-draft-editor")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    // Phase 59 brief-listed forbidden positive phrasings.
    for (const forbidden of [
      "hands-free scribing",
      "autonomous documentation",
      "ai writes the note",
      "note writes itself",
      "chart fills itself",
      "openai-powered clinical documentation",
      "production llm documentation",
      "real phi ready",
      "ambient scribe parity",
    ]) {
      expect(body, `forbidden phrase appeared: ${forbidden}`).not.toMatch(
        new RegExp(forbidden.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
      );
    }
  });
});

// ---------------------------------------------------------------
// Phase 73 — Provider review / signed lock / audit trail
// ---------------------------------------------------------------

describe("AmbientDocumentationPanel — Phase 73 audit trail", () => {
  it("saved list shows status pill with correct label", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([
      baseSession({ id: 7, status: "finalized" }),
      baseSession({ id: 8, status: "reviewed" }),
      baseSession({ id: 9, status: "ready_for_review" }),
      baseSession({ id: 10, status: "draft" }),
    ]);
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ambient-list-status-7").textContent).toMatch(
      /Signed · Locked/,
    );
    expect(screen.getByTestId("ambient-list-status-8").textContent).toMatch(
      /Reviewed/,
    );
    expect(screen.getByTestId("ambient-list-status-9").textContent).toMatch(
      /Ready for Review/,
    );
    expect(screen.getByTestId("ambient-list-status-10").textContent).toMatch(
      /Draft/,
    );
  });

  it("shows awaiting-review callout on non-signed session", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([
      baseSession({ status: "ready_for_review" }),
    ]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "ready_for_review" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(
        screen.getByTestId("ambient-awaiting-review"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("ambient-awaiting-review").textContent,
    ).toMatch(/Awaiting provider review/i);
    expect(
      screen.getByTestId("ambient-awaiting-review").textContent,
    ).toMatch(/Not a diagnosis/i);
    expect(
      screen.getByTestId("ambient-awaiting-review").textContent,
    ).toMatch(/Does not produce notes without provider review/i);
  });

  it("hides awaiting-review callout on signed session", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([
      baseSession({ status: "finalized" }),
    ]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({ status: "finalized", finalized_at: "2026-05-19T07:00:00Z" }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-signed-lock")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("ambient-awaiting-review")).toBeNull();
  });

  it("signed-lock banner shows reviewer info when reviewed_at + reviewed_by_user_id present", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([
      baseSession({ status: "finalized" }),
    ]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({
        status: "finalized",
        finalized_at: "2026-05-19T07:00:00Z",
        reviewed_at: "2026-05-19T06:50:00Z",
        reviewed_by_user_id: 9,
      }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-signed-lock")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("ambient-signed-reviewer").textContent,
    ).toMatch(/clinician #9/);
  });

  it("signed-lock banner includes metadata-only audit note", async () => {
    vi.mocked(listScribeSessions).mockResolvedValueOnce([
      baseSession({ status: "finalized" }),
    ]);
    vi.mocked(getScribeSession).mockResolvedValueOnce(
      baseSessionWithDraft({
        status: "finalized",
        finalized_at: "2026-05-19T07:00:00Z",
      }),
    );
    render(<AmbientDocumentationPanel patientId={42} />);
    await waitFor(() =>
      expect(screen.getByTestId("ambient-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("ambient-list-item-7"));
    await waitFor(() =>
      expect(screen.getByTestId("ambient-signed-lock")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ambient-audit-note").textContent).toMatch(
      /metadata-only audit events/i,
    );
    expect(screen.getByTestId("ambient-audit-note").textContent).toMatch(
      /does not store clinical free text/i,
    );
  });
});
