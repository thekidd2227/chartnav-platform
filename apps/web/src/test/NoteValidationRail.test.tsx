// Phase 82 — Note Validation Rail tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/note-validation/noteValidationApi", () => ({
  getNoteValidation: vi.fn(),
  getNoteValidationAcknowledgements: vi.fn(),
  postNoteValidationAcknowledgement: vi.fn(),
}));

import {
  getNoteValidation,
  getNoteValidationAcknowledgements,
  postNoteValidationAcknowledgement,
} from "../features/note-validation/noteValidationApi";
import { NoteValidationRail } from "../features/note-validation/NoteValidationRail";
import type {
  NoteValidationCheck,
  NoteValidationRailResponse,
} from "../features/note-validation/noteValidationTypes";

function check(over: Partial<NoteValidationCheck> = {}): NoteValidationCheck {
  return {
    check_id: "laterality:rollup",
    category: "laterality",
    label: "Laterality consistency across sources",
    status: "warning",
    laterality: "OU",
    source: "visit_draft",
    detail:
      "Laterality differs across surfaces: vitals=OD, fundus=OS. Confirm the visit draft references the correct eye.",
    requires_provider_acknowledgement: true,
    source_artifact_id: null,
    ...over,
  };
}

function emptyResponse(): NoteValidationRailResponse {
  return {
    encounter_id: 1,
    organization_id: 1,
    patient_id: 1,
    generated_at: "2026-06-09T22:00:00Z",
    demo_mode: true,
    checks: [],
    totals: { pass: 0, warning: 0, missing: 0, blocked: 0 },
    acknowledgements_required: 0,
    disclosure:
      "Validation checks use structured provider-entered workflow data. ChartNav does not diagnose, interpret images, or recommend treatment. Provider attestation remains required.",
  };
}

function richResponse(): NoteValidationRailResponse {
  const checks: NoteValidationCheck[] = [
    check({
      check_id: "laterality:vitals",
      label: "vitals laterality recorded",
      status: "pass",
      laterality: "OD",
      source: "vitals",
      detail: "vitals laterality OD on file.",
      requires_provider_acknowledgement: false,
    }),
    check({
      check_id: "laterality:fundus",
      label: "fundus laterality recorded",
      status: "pass",
      laterality: "OS",
      source: "fundus",
      detail: "fundus laterality OS on file.",
      requires_provider_acknowledgement: false,
    }),
    check(), // disjoint rollup warning with ack required
    check({
      check_id: "follow_up:interval",
      category: "follow_up",
      label: "Follow-up interval recorded",
      status: "pass",
      source: "anti_vegf",
      laterality: "OD",
      detail: "Anti-VEGF interval of 6 week(s) on file for OD.",
      requires_provider_acknowledgement: false,
    }),
    check({
      check_id: "unsigned:fundus:7",
      category: "unsigned_upstream",
      label: "Fundus chart not yet signed",
      status: "warning",
      source: "fundus",
      laterality: "OD",
      detail:
        "Fundus chart #7 (OD) is not signed. Sign upstream or acknowledge to proceed.",
      requires_provider_acknowledgement: true,
      source_artifact_id: 7,
    }),
    check({
      check_id: "review_state:attestation",
      category: "review_state",
      label: "Provider attestation required",
      status: "pass",
      source: "signed_lock",
      laterality: null,
      detail:
        "Provider attestation remains required on the existing sign-and-lock checkbox before any artifact is finalized.",
      requires_provider_acknowledgement: false,
    }),
  ];
  return {
    ...emptyResponse(),
    checks,
    totals: { pass: 3, warning: 2, missing: 0, blocked: 0 },
    acknowledgements_required: 2,
  };
}

beforeEach(() => {
  vi.mocked(getNoteValidation).mockReset();
  vi.mocked(getNoteValidationAcknowledgements).mockReset();
  vi.mocked(getNoteValidationAcknowledgements).mockResolvedValue([]);
  vi.mocked(postNoteValidationAcknowledgement).mockReset();
  vi.mocked(postNoteValidationAcknowledgement).mockResolvedValue({
    id: 1,
    audit_created_at: "2026-06-10T01:00:00Z",
    encounter_id: 1,
    actor_id: 2,
    actor_display_name: "Casey Clinician",
    actor_role: "clinician",
    validation_item_id: "stub",
    validation_category: "stub",
    acknowledgement_type: "acknowledged",
    acknowledgement_timestamp: "2026-06-10T01:00:00Z",
  });
});

describe("NoteValidationRail — base render", () => {
  it("renders header, banner, refresh button, and disclosure", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(emptyResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("note-validation-rail")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("note-validation-banner").textContent).toMatch(
      /Validation checks use structured provider-entered workflow data/i,
    );
    expect(screen.getByTestId("note-validation-banner").textContent).toMatch(
      /does not diagnose/i,
    );
    expect(screen.getByTestId("note-validation-banner").textContent).toMatch(
      /Provider attestation remains required/i,
    );
    expect(
      screen.getByTestId("note-validation-refresh-btn"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("note-validation-disclosure").textContent,
    ).toMatch(/does not diagnose/i);
  });

  it("renders totals with the four status counts", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("note-validation-totals")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("note-validation-totals").textContent).toMatch(
      /3 pass · 2 warning · 0 missing · 0 blocked/,
    );
  });
});

describe("NoteValidationRail — check rendering", () => {
  it("renders pass checks with green Pass pill and source badge", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-check-laterality:vitals"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("note-validation-check-laterality:vitals-status")
        .textContent,
    ).toBe("Pass");
    expect(
      screen.getByTestId("note-validation-check-laterality:vitals-source")
        .textContent,
    ).toBe("Vitals");
    expect(
      screen.getByTestId(
        "note-validation-check-laterality:vitals-laterality",
      ).textContent,
    ).toBe("OD");
  });

  it("renders warning rollup with ack-required pill and detail", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-check-laterality:rollup"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("note-validation-check-laterality:rollup-status")
        .textContent,
    ).toBe("Warning");
    expect(
      screen.getByTestId(
        "note-validation-check-laterality:rollup-ack-required",
      ).textContent,
    ).toMatch(/Ack required/i);
    const detail = screen.getByTestId(
      "note-validation-check-laterality:rollup",
    );
    expect(detail.textContent).toMatch(/differs across surfaces/i);
  });

  it("renders unsigned-fundus warning with OD laterality", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-check-unsigned:fundus:7"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("note-validation-check-unsigned:fundus:7-laterality")
        .textContent,
    ).toBe("OD");
    expect(
      screen.getByTestId("note-validation-check-unsigned:fundus:7-source")
        .textContent,
    ).toBe("Fundus");
  });
});

describe("NoteValidationRail — acknowledgements", () => {
  it("shows ack summary outstanding then transitions to all-acknowledged when both ticks fire", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-ack-summary"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("note-validation-ack-summary").textContent,
    ).toMatch(/0 \/ 2 acknowledged/);
    expect(
      screen.getByTestId("note-validation-ack-banner").textContent,
    ).toMatch(/2 acknowledgement\(s\) outstanding/i);

    await userEvent.click(
      screen.getByTestId(
        "note-validation-check-laterality:rollup-ack-checkbox",
      ),
    );
    await userEvent.click(
      screen.getByTestId(
        "note-validation-check-unsigned:fundus:7-ack-checkbox",
      ),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-ack-summary").textContent,
      ).toMatch(/2 \/ 2 acknowledged/),
    );
    expect(
      screen.getByTestId("note-validation-ack-banner").textContent,
    ).toMatch(/All required acknowledgements recorded/i);
    expect(
      screen.getByTestId("note-validation-ack-banner").textContent,
    ).toMatch(/Provider attestation on the sign-and-lock checkbox/i);
  });

  it("does not render ack-banner when no acknowledgements are required", async () => {
    const noAck = richResponse();
    noAck.checks = noAck.checks.map((c) => ({
      ...c,
      requires_provider_acknowledgement: false,
    }));
    noAck.acknowledgements_required = 0;
    noAck.totals = { pass: 6, warning: 0, missing: 0, blocked: 0 };
    vi.mocked(getNoteValidation).mockResolvedValueOnce(noAck);

    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("note-validation-totals")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("note-validation-ack-banner")).toBeNull();
    expect(screen.queryByTestId("note-validation-ack-summary")).toBeNull();
  });
});

describe("NoteValidationRail — interaction + safety", () => {
  it("refresh button refetches and resets acknowledgements", async () => {
    vi.mocked(getNoteValidation)
      .mockResolvedValueOnce(richResponse())
      .mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-ack-summary"),
      ).toBeInTheDocument(),
    );
    await userEvent.click(
      screen.getByTestId(
        "note-validation-check-laterality:rollup-ack-checkbox",
      ),
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-ack-summary").textContent,
      ).toMatch(/1 \/ 2 acknowledged/),
    );
    await userEvent.click(
      screen.getByTestId("note-validation-refresh-btn"),
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-ack-summary").textContent,
      ).toMatch(/0 \/ 2 acknowledged/),
    );
    expect(getNoteValidation).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in the error banner", async () => {
    vi.mocked(getNoteValidation).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("note-validation-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("note-validation-error").textContent).toMatch(
      /HTTP 503/,
    );
  });

  it("does NOT render forbidden clinical-decision phrases", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("note-validation-rail")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "surgery recommended",
      "rapid progression",
      "stage iii",
      "iol power",
      "phaco recommended",
      "order placed",
      "billing code",
      "ai prioritized",
      "ai blocks signing",
      "ai recommends",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});

describe("NoteValidationRail — Phase 83 persistence", () => {
  it("hydrates persisted acknowledgements from server on mount", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    vi.mocked(getNoteValidationAcknowledgements).mockResolvedValueOnce([
      {
        id: 42,
        audit_created_at: "2026-06-10T01:00:00Z",
        encounter_id: 1,
        actor_id: 2,
        actor_display_name: "Casey Clinician",
        actor_role: "clinician",
        validation_item_id: "laterality:rollup",
        validation_category: "laterality",
        acknowledgement_type: "acknowledged",
        acknowledgement_timestamp: "2026-06-10T01:00:00Z",
      },
    ]);
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "note-validation-check-laterality:rollup-persisted-ack",
        ),
      ).toBeInTheDocument(),
    );
    const note = screen.getByTestId(
      "note-validation-check-laterality:rollup-persisted-ack",
    );
    expect(note.textContent).toMatch(/Acknowledged by Casey Clinician/);
    expect(note.textContent).toMatch(/\(clinician\)/);
    // Seeded checkbox state reflects the persisted ack.
    expect(
      (
        screen.getByTestId(
          "note-validation-check-laterality:rollup-ack-checkbox",
        ) as HTMLInputElement
      ).checked,
    ).toBe(true);
  });

  it("POSTs to /acknowledgements when the operator toggles a checkbox", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "note-validation-check-laterality:rollup-ack-checkbox",
        ),
      ).toBeInTheDocument(),
    );
    await userEvent.click(
      screen.getByTestId(
        "note-validation-check-laterality:rollup-ack-checkbox",
      ),
    );
    await waitFor(() =>
      expect(postNoteValidationAcknowledgement).toHaveBeenCalled(),
    );
    const args = vi
      .mocked(postNoteValidationAcknowledgement)
      .mock.calls[0]!;
    expect(args[0]).toBe(1);
    expect(args[1].validation_item_id).toBe("laterality:rollup");
    expect(args[1].validation_category).toBe("laterality");
    expect(args[1].acknowledgement_type).toBe("acknowledged");
  });

  it("posts an explicit 'rescinded' record when the operator unticks", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    vi.mocked(getNoteValidationAcknowledgements).mockResolvedValueOnce([
      {
        id: 99,
        audit_created_at: "2026-06-10T01:00:00Z",
        encounter_id: 1,
        actor_id: 2,
        actor_display_name: "Casey Clinician",
        actor_role: "clinician",
        validation_item_id: "laterality:rollup",
        validation_category: "laterality",
        acknowledgement_type: "acknowledged",
        acknowledgement_timestamp: "2026-06-10T01:00:00Z",
      },
    ]);
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "note-validation-check-laterality:rollup-persisted-ack",
        ),
      ).toBeInTheDocument(),
    );
    await userEvent.click(
      screen.getByTestId(
        "note-validation-check-laterality:rollup-ack-checkbox",
      ),
    );
    await waitFor(() =>
      expect(postNoteValidationAcknowledgement).toHaveBeenCalled(),
    );
    expect(
      vi.mocked(postNoteValidationAcknowledgement).mock.calls[0]![1]
        .acknowledgement_type,
    ).toBe("rescinded");
  });

  it("reverts the checkbox and surfaces an ack-error banner on POST failure", async () => {
    vi.mocked(getNoteValidation).mockResolvedValueOnce(richResponse());
    vi.mocked(postNoteValidationAcknowledgement).mockRejectedValueOnce(
      new Error("HTTP 503 ack failed"),
    );
    render(<NoteValidationRail encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "note-validation-check-laterality:rollup-ack-checkbox",
        ),
      ).toBeInTheDocument(),
    );
    const cb = screen.getByTestId(
      "note-validation-check-laterality:rollup-ack-checkbox",
    ) as HTMLInputElement;
    await userEvent.click(cb);
    await waitFor(() =>
      expect(
        screen.getByTestId("note-validation-ack-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("note-validation-ack-error").textContent,
    ).toMatch(/HTTP 503/);
    expect(cb.checked).toBe(false);
  });
});
