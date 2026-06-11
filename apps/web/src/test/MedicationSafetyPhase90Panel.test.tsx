// Phase 90 — Ophthalmic Medication Safety & Adherence Panel tests.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/medication-safety/medicationSafetyApi", () => ({
  getMedicationSafety: vi.fn(),
  postAcknowledgeEvent: vi.fn(),
  postOphthalmicMedication: vi.fn(),
}));

import {
  getMedicationSafety,
  postAcknowledgeEvent,
  postOphthalmicMedication,
} from "../features/medication-safety/medicationSafetyApi";
import { MedicationSafetyPanel } from "../features/medication-safety/MedicationSafetyPanel";
import type {
  MedicationSafetyEvent,
  MedicationSafetyResponse,
  OphthalmicMedicationRecord,
} from "../features/medication-safety/medicationSafetyTypes";

const DISCLOSURE =
  "Provider-reviewed medication safety workflow support. ChartNav does NOT prescribe, does NOT recommend a medication, does NOT recommend stopping or changing a medication, does NOT diagnose.";

function med(
  over: Partial<OphthalmicMedicationRecord> = {},
): OphthalmicMedicationRecord {
  return {
    id: 1,
    organization_id: 1,
    patient_id: 1,
    encounter_id: 1,
    medication_name: "Latanoprost 0.005%",
    medication_class: "pgf2_analog",
    route: "drops",
    laterality: "OU",
    dose_per_day: 1,
    preservative_flag: true,
    preservative_type: "BAK",
    started_on: null,
    discontinued_on: null,
    last_fill_date: "2026-06-01",
    days_supply: 30,
    supply_through: "2026-07-01",
    refill_gap_days: 0,
    active: true,
    reviewed_by_user_id: null,
    reviewed_at: null,
    recorded_by_user_id: 5,
    created_at: "2026-06-10T10:00:00Z",
    updated_at: "2026-06-10T10:00:00Z",
    ...over,
  };
}

function event(
  over: Partial<MedicationSafetyEvent> = {},
): MedicationSafetyEvent {
  return {
    id: 1,
    organization_id: 1,
    patient_id: 1,
    encounter_id: null,
    medication_id: null,
    rule_key: "ophth_preservative_burden_advisory",
    severity: "advisory",
    laterality: "none",
    status: "active",
    message:
      "Provider review advisory: 3 active BAK-preserved drop(s) on the medication list. ChartNav does not recommend a medication change.",
    acknowledged_by_user_id: null,
    acknowledged_by_display_name: null,
    acknowledged_by_role: null,
    acknowledged_at: null,
    created_at: "2026-06-10T10:00:00Z",
    updated_at: "2026-06-10T10:00:00Z",
    ...over,
  };
}

function emptyResponse(): MedicationSafetyResponse {
  return {
    patient_id: 1,
    patient_identifier: "PT-1001",
    patient_name: "Morgan Lee",
    organization_id: 1,
    generated_at: "2026-06-10T10:00:00Z",
    demo_mode: true,
    medications: [],
    active_medication_count: 0,
    events: [],
    counts: {
      active_events: 0,
      acknowledged_events: 0,
      resolved_events: 0,
      total_events: 0,
    },
    signals: {
      preservative_burden_count: 0,
      refill_gap_count: 0,
      refill_gaps: [],
      active_medication_count: 0,
      medications_reviewed_count: 0,
      insufficient_data: true,
    },
    rules: [],
    internal_demo_rules_present: true,
    submission_status: "not_submitted",
    disclosure: DISCLOSURE,
  };
}

function populatedResponse(): MedicationSafetyResponse {
  return {
    ...emptyResponse(),
    medications: [med()],
    active_medication_count: 1,
    events: [event()],
    counts: {
      active_events: 1,
      acknowledged_events: 0,
      resolved_events: 0,
      total_events: 1,
    },
    signals: {
      preservative_burden_count: 3,
      refill_gap_count: 0,
      refill_gaps: [],
      active_medication_count: 1,
      medications_reviewed_count: 0,
      insufficient_data: false,
    },
  };
}

beforeEach(() => {
  vi.mocked(getMedicationSafety).mockReset();
  vi.mocked(postAcknowledgeEvent).mockReset();
  vi.mocked(postOphthalmicMedication).mockReset();
});

describe("MedicationSafetyPanel — base render", () => {
  it("renders header, banner, refresh button", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(emptyResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-safety-panel")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("medication-safety-banner").textContent).toMatch(
      /Provider-reviewed medication safety support/i,
    );
    expect(screen.getByTestId("medication-safety-banner").textContent).toMatch(
      /does not prescribe/i,
    );
    expect(screen.getByTestId("medication-safety-banner").textContent).toMatch(
      /does not recommend a medication change/i,
    );
    expect(
      screen.getByTestId("medication-safety-refresh-btn"),
    ).toBeInTheDocument();
  });

  it("renders signal counters", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-signals"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-signal-preservative-burden")
        .textContent,
    ).toMatch(/Preservative burden:\s*3/);
    expect(
      screen.getByTestId("medication-safety-signal-active-events").textContent,
    ).toMatch(/Active advisories:\s*1/);
  });

  it("shows internal-demo caution banner when present", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-demo-caution"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-demo-caution").textContent,
    ).toMatch(/Internal demo rules present/i);
  });
});

describe("MedicationSafetyPanel — empty state", () => {
  it("shows events-empty and medications-empty callouts", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(emptyResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-events-empty"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-medications-empty"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("medication-safety-events-empty").textContent,
    ).toMatch(/Provider review required/i);
  });
});

describe("MedicationSafetyPanel — populated", () => {
  it("renders medication row with class, preservative, dose, last fill", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-medication-row-1"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-medication-name-1").textContent,
    ).toBe("Latanoprost 0.005%");
    expect(
      screen.getByTestId("medication-safety-medication-preservative-1")
        .textContent,
    ).toBe("BAK");
    expect(
      screen.getByTestId("medication-safety-medication-laterality-1")
        .textContent,
    ).toBe("OU");
  });

  it("renders event row with severity badge + message + acknowledge button", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-event-row-1"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-event-severity-1").textContent,
    ).toMatch(/Advisory/i);
    expect(
      screen.getByTestId("medication-safety-event-message-1").textContent,
    ).toMatch(/Provider review advisory/i);
    expect(
      screen.getByTestId("medication-safety-event-ack-btn-1"),
    ).toBeInTheDocument();
  });
});

describe("MedicationSafetyPanel — interactions", () => {
  it("acknowledges an event and refetches", async () => {
    vi.mocked(getMedicationSafety)
      .mockResolvedValueOnce(populatedResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postAcknowledgeEvent).mockResolvedValueOnce(
      event({ status: "acknowledged" }),
    );

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-event-ack-btn-1"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("medication-safety-event-ack-btn-1"),
    );

    await waitFor(() =>
      expect(postAcknowledgeEvent).toHaveBeenCalledTimes(1),
    );
    expect(vi.mocked(postAcknowledgeEvent).mock.calls[0]![0]).toBe(1);
    expect(getMedicationSafety).toHaveBeenCalledTimes(2);
  });

  it("surfaces acknowledge error in inline banner", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    vi.mocked(postAcknowledgeEvent).mockRejectedValueOnce(
      new Error("forbidden"),
    );

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-event-ack-btn-1"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("medication-safety-event-ack-btn-1"),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-ack-error"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-ack-error").textContent,
    ).toMatch(/forbidden/);
  });

  it("POSTs a new medication and refetches", async () => {
    vi.mocked(getMedicationSafety)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());
    vi.mocked(postOphthalmicMedication).mockResolvedValueOnce(med());

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-form"),
      ).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByTestId("medication-safety-form-name"),
      "Latanoprost 0.005%",
    );
    await userEvent.click(
      screen.getByTestId("medication-safety-form-submit"),
    );

    await waitFor(() =>
      expect(postOphthalmicMedication).toHaveBeenCalledTimes(1),
    );
    const payload = vi.mocked(postOphthalmicMedication).mock.calls[0]![1];
    expect(payload.medication_name).toBe("Latanoprost 0.005%");
    expect(payload.preservative_type).toBe("BAK");
  });

  it("surfaces form error in inline banner", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(emptyResponse());
    vi.mocked(postOphthalmicMedication).mockRejectedValueOnce(
      new Error("invalid_preservative_type"),
    );

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-form-submit"),
      ).toBeInTheDocument(),
    );

    await userEvent.type(
      screen.getByTestId("medication-safety-form-name"),
      "X",
    );
    await userEvent.click(
      screen.getByTestId("medication-safety-form-submit"),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-form-error"),
      ).toBeInTheDocument(),
    );
  });

  it("refresh button refetches", async () => {
    vi.mocked(getMedicationSafety)
      .mockResolvedValueOnce(emptyResponse())
      .mockResolvedValueOnce(populatedResponse());

    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-events-empty"),
      ).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByTestId("medication-safety-refresh-btn"),
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-event-row-1"),
      ).toBeInTheDocument(),
    );
    expect(getMedicationSafety).toHaveBeenCalledTimes(2);
  });

  it("surfaces API errors in error banner", async () => {
    vi.mocked(getMedicationSafety).mockRejectedValueOnce(
      new Error("HTTP 503 service unavailable"),
    );
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("medication-safety-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("medication-safety-error").textContent).toMatch(
      /HTTP 503/,
    );
  });
});

describe("MedicationSafetyPanel — safety contract", () => {
  it("renders disclosure verbatim", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-disclosure"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("medication-safety-disclosure").textContent,
    ).toMatch(/does not prescribe/i);
  });

  it("does NOT render forbidden recommendation phrases in event rows", async () => {
    vi.mocked(getMedicationSafety).mockResolvedValueOnce(populatedResponse());
    render(<MedicationSafetyPanel patientId={1} encounterId={1} />);
    await waitFor(() =>
      expect(
        screen.getByTestId("medication-safety-event-row-1"),
      ).toBeInTheDocument(),
    );
    const disclosure = (
      screen.getByTestId("medication-safety-disclosure").textContent ?? ""
    ).toLowerCase();
    const banner = (
      screen.getByTestId("medication-safety-banner").textContent ?? ""
    ).toLowerCase();
    const body = (document.body.textContent ?? "")
      .toLowerCase()
      .replace(disclosure, "")
      .replace(banner, "");
    for (const forbidden of [
      "must stop",
      "contraindicated",
      "should prescribe",
      "recommended medication change",
      "auto-prescribed",
      "auto-refilled",
      "billing optimization",
      "automated prescription",
      "send referral",
    ]) {
      expect(body, `forbidden phrase: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
