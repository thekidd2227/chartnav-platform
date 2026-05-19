import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../features/vitals/vitalsApi", () => ({
  listVitalsWorkups: vi.fn(),
  createVitalsWorkup: vi.fn(),
  getVitalsWorkup: vi.fn(),
  updateVitalsWorkup: vi.fn(),
  reviewVitalsWorkup: vi.fn(),
  signVitalsWorkup: vi.fn(),
}));

import {
  listVitalsWorkups,
  createVitalsWorkup,
  getVitalsWorkup,
  updateVitalsWorkup,
  reviewVitalsWorkup,
  signVitalsWorkup,
} from "../features/vitals/vitalsApi";
import { VitalsWorkupPanel } from "../features/vitals/VitalsWorkupPanel";
import type { VitalsWorkup } from "../features/vitals/vitalsTypes";

const baseWorkup = (over: Partial<VitalsWorkup> = {}): VitalsWorkup => ({
  id: 1,
  organization_id: 1,
  encounter_id: 7,
  patient_id: 42,
  status: "draft",
  source_type: "technician_entry",
  bp_systolic: null,
  bp_diastolic: null,
  bp_position: null,
  bp_site: null,
  temperature_value: null,
  temperature_unit: "F",
  temperature_site: null,
  pulse: null,
  respiratory_rate: null,
  oxygen_saturation: null,
  height_value: null,
  height_unit: "in",
  weight_value: null,
  weight_unit: "lb",
  bmi: null,
  pain_score: null,
  visual_acuity_od: null,
  visual_acuity_os: null,
  visual_acuity_ou: null,
  iop_od: null,
  iop_os: null,
  iop_method: null,
  dilation_status: null,
  dilation_time: null,
  allergies_reviewed: false,
  medications_reviewed: false,
  technician_notes: null,
  warnings: [],
  reviewed_by_user_id: null,
  reviewed_at: null,
  signed_by_user_id: null,
  signed_at: null,
  created_by_user_id: 1,
  created_at: "2026-05-19T20:00:00Z",
  updated_at: "2026-05-19T20:00:00Z",
  requires_provider_review: true,
  forbidden_actions: {
    diagnosis: false,
    treatment_recommendation: false,
    orders: false,
    referrals: false,
    patient_message: false,
    billing_or_coding: false,
    device_integration: false,
    remote_patient_monitoring: false,
    auto_sign: false,
  },
  is_terminal: false,
  ...over,
});

beforeEach(() => {
  vi.mocked(listVitalsWorkups).mockReset();
  vi.mocked(createVitalsWorkup).mockReset();
  vi.mocked(getVitalsWorkup).mockReset();
  vi.mocked(updateVitalsWorkup).mockReset();
  vi.mocked(reviewVitalsWorkup).mockReset();
  vi.mocked(signVitalsWorkup).mockReset();
});

describe("VitalsWorkupPanel — empty + safety", () => {
  it("renders the panel with required safety clauses", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-empty")).toBeInTheDocument(),
    );
    const banner = screen.getByTestId("vitals-safety-banner");
    expect(banner.textContent).toMatch(/Structured intake for provider review/i);
    expect(banner.textContent).toMatch(/Does not diagnose/i);
    expect(banner.textContent).toMatch(/Does not recommend treatment/i);
    expect(banner.textContent).toMatch(/Does not place orders/i);
    expect(banner.textContent).toMatch(/Does not send referrals or patient messages/i);
    expect(banner.textContent).toMatch(/Does not bill or code/i);
    expect(banner.textContent).toMatch(/Not for real PHI/i);
    expect(banner.textContent).toMatch(/No device integration/i);
  });

  it("Save draft button disabled while loading list", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-save-draft-btn")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("vitals-save-draft-btn")).not.toBeDisabled();
  });
});

describe("VitalsWorkupPanel — demo sample + BMI", () => {
  it("Load fake demo vitals populates the form with synthetic data", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-demo-sample-btn")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-demo-sample-btn"));
    expect(
      (screen.getByTestId("vitals-input-bp_systolic") as HTMLInputElement).value,
    ).toBe("122");
    expect(
      (screen.getByTestId("vitals-input-pulse") as HTMLInputElement).value,
    ).toBe("72");
    expect(
      (screen.getByTestId("vitals-input-visual_acuity_od") as HTMLInputElement)
        .value,
    ).toBe("20/20");
    // No real-PHI shapes in the synthetic sample.
    const notes = (screen.getByTestId(
      "vitals-input-technician_notes",
    ) as HTMLTextAreaElement).value.toLowerCase();
    expect(notes).not.toMatch(/ssn/);
    expect(notes).not.toMatch(/dob[: ]/);
    expect(notes).not.toMatch(/mrn[: ]?\d/);
    expect(notes).toMatch(/fake[- ]data only/);
  });

  it("BMI display updates live from height/weight entries", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-bmi-display")).toBeInTheDocument(),
    );
    // Initially empty.
    expect(screen.getByTestId("vitals-bmi-display").textContent).toContain("—");
    // 70 in + 154 lb → BMI ~22.1.
    await userEvent.type(
      screen.getByTestId("vitals-input-height_value"),
      "70",
    );
    await userEvent.type(
      screen.getByTestId("vitals-input-weight_value"),
      "154",
    );
    expect(screen.getByTestId("vitals-bmi-display").textContent).toMatch(
      /22\.1/,
    );
  });
});

describe("VitalsWorkupPanel — create + warnings flow", () => {
  it("create flow calls createVitalsWorkup and selects the result", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    vi.mocked(createVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({ id: 99, pulse: 72 }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-demo-sample-btn")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-demo-sample-btn"));
    await userEvent.click(screen.getByTestId("vitals-save-draft-btn"));
    await waitFor(() =>
      expect(createVitalsWorkup).toHaveBeenCalled(),
    );
    expect(screen.getByTestId("vitals-list-item-99")).toBeInTheDocument();
  });

  it("warnings panel renders warnings text from the server response", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({
        id: 5,
        status: "draft",
        warnings: [
          "Blood pressure systolic captured but diastolic missing; please add diastolic before signing.",
        ],
        bp_systolic: 120,
      }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({
        id: 5,
        status: "draft",
        warnings: [
          "Blood pressure systolic captured but diastolic missing; please add diastolic before signing.",
        ],
        bp_systolic: 120,
      }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-5"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-warnings")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("vitals-warning-0").textContent).toMatch(
      /diastolic missing/,
    );
  });
});

describe("VitalsWorkupPanel — lifecycle UI", () => {
  it("Save & mark entered button appears on a draft and disappears once entered", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({ id: 11, status: "draft", pulse: 72 }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({ id: 11, status: "draft", pulse: 72 }),
    );
    vi.mocked(updateVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({ id: 11, status: "entered", pulse: 72 }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-11")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-11"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-save-advance-btn")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("vitals-save-advance-btn").textContent).toMatch(
      /Save & mark entered/i,
    );
    await userEvent.click(screen.getByTestId("vitals-save-advance-btn"));
    await waitFor(() => expect(updateVitalsWorkup).toHaveBeenCalled());
    // Status flipped → review button now visible.
    await waitFor(() =>
      expect(screen.getByTestId("vitals-review-btn")).toBeInTheDocument(),
    );
  });

  it("Review button is visually distinct from Sign and Sign is hidden pre-review", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({ id: 12, status: "entered" }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({ id: 12, status: "entered" }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-12")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-12"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-review-btn")).toBeInTheDocument(),
    );
    const reviewLabel = screen.getByTestId("vitals-review-btn").textContent ??
      "";
    expect(reviewLabel).toMatch(/Mark Reviewed/i);
    expect(reviewLabel).not.toMatch(/Sign/i);
    expect(screen.queryByTestId("vitals-sign-btn")).toBeNull();
  });

  it("Sign requires the attestation checkbox", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({ id: 13, status: "reviewed" }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({ id: 13, status: "reviewed" }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-13")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-13"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-attestation-block")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("vitals-sign-btn")).toBeDisabled();
    await userEvent.click(screen.getByTestId("vitals-attestation-checkbox"));
    expect(screen.getByTestId("vitals-sign-btn")).not.toBeDisabled();
  });

  it("Attestation block uses the immutability + accuracy copy", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({ id: 14, status: "reviewed" }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({ id: 14, status: "reviewed" }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-14")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-14"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-attestation-block")).toBeInTheDocument(),
    );
    const block = screen.getByTestId("vitals-attestation-block").textContent ?? "";
    expect(block).toMatch(/I attest/i);
    expect(block).toMatch(/vitals values are accurate/i);
    expect(block).toMatch(/Signing will lock the workup/i);
    expect(block).toMatch(/immutable/i);
  });

  it("Signed workup shows the locked banner and removes every edit control", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({
        id: 15,
        status: "signed",
        signed_at: "2026-05-19T20:45:00Z",
        signed_by_user_id: 1,
        is_terminal: true,
        requires_provider_review: false,
      }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({
        id: 15,
        status: "signed",
        signed_at: "2026-05-19T20:45:00Z",
        signed_by_user_id: 1,
        is_terminal: true,
        requires_provider_review: false,
      }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-15")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-15"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-signed-lock")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("vitals-save-advance-btn")).toBeNull();
    expect(screen.queryByTestId("vitals-review-btn")).toBeNull();
    expect(screen.queryByTestId("vitals-sign-btn")).toBeNull();
    expect(screen.queryByTestId("vitals-attestation-block")).toBeNull();
    expect(
      screen.getByTestId("vitals-signed-lock").textContent,
    ).toMatch(/Signed workups are immutable/i);
  });
});

describe("VitalsWorkupPanel — what ChartNav did NOT do", () => {
  it("renders every forbidden action with (false)", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({ id: 21 }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(baseWorkup({ id: 21 }));
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-21")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-21"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-actions-summary")).toBeInTheDocument(),
    );
    const card = screen.getByTestId("vitals-actions-summary").textContent ?? "";
    for (const action of [
      "diagnosis",
      "treatment recommendation",
      "orders",
      "referrals",
      "patient messages",
      "billing or coding",
      "device integration",
      "remote patient monitoring",
      "auto-sign",
    ]) {
      expect(card.toLowerCase()).toContain(action);
    }
    const falseCount = (card.match(/\(false\)/gi) ?? []).length;
    expect(falseCount).toBe(9);
  });
});

describe("VitalsWorkupPanel — claim safety", () => {
  it("does not surface forbidden positive phrasings anywhere in the rendered UI", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      baseWorkup({
        id: 31,
        warnings: [
          "Systolic blood pressure (210) is outside the typical range; provider review required.",
        ],
        bp_systolic: 210,
      }),
    ]);
    vi.mocked(getVitalsWorkup).mockResolvedValueOnce(
      baseWorkup({
        id: 31,
        warnings: [
          "Systolic blood pressure (210) is outside the typical range; provider review required.",
        ],
        bp_systolic: 210,
      }),
    );
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() =>
      expect(screen.getByTestId("vitals-list-item-31")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("vitals-list-item-31"));
    await waitFor(() =>
      expect(screen.getByTestId("vitals-warnings")).toBeInTheDocument(),
    );
    const body = (document.body.textContent ?? "").toLowerCase();
    for (const forbidden of [
      "diagnosis confirmed",
      "treatment recommended",
      "order placed",
      "billing code",
      "automatic coding",
      "patient message sent",
      "hipaa compliant",
      "ehr replacement",
      "device integration enabled",
      "remote patient monitoring enabled",
      "hypertensive crisis",
      "fever",
      "hypoxia",
      "stroke",
    ]) {
      expect(
        body,
        `forbidden phrase appeared: ${forbidden}`,
      ).not.toMatch(new RegExp(forbidden.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    }
  });
});
