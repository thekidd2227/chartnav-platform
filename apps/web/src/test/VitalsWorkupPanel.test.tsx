import { render, screen, waitFor } from "@testing-library/react";
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
  createVitalsWorkup,
  listVitalsWorkups,
  reviewVitalsWorkup,
} from "../features/vitals/vitalsApi";
import { VitalsWorkupPanel } from "../features/vitals/VitalsWorkupPanel";
import type { VitalWorkup } from "../features/vitals/vitalsTypes";

const workup = (over: Partial<VitalWorkup> = {}): VitalWorkup => ({
  id: 11,
  organization_id: 1,
  encounter_id: 7,
  patient_id: 42,
  status: "entered",
  source_type: "technician_entry",
  bp_systolic: 118,
  bp_diastolic: 74,
  bp_position: "sitting",
  bp_site: "left_arm",
  temperature_value: 98.4,
  temperature_unit: "F",
  temperature_site: null,
  pulse: 72,
  respiratory_rate: 14,
  oxygen_saturation: 98,
  height_value: 70,
  height_unit: "in",
  weight_value: 175,
  weight_unit: "lb",
  bmi: 25.11,
  pain_score: 1,
  visual_acuity_od: "20/30",
  visual_acuity_os: "20/25",
  visual_acuity_ou: "20/25",
  iop_od: 16,
  iop_os: 15,
  iop_method: "tonopen",
  dilation_status: "not_dilated",
  dilation_time: null,
  allergies_reviewed: true,
  medications_reviewed: true,
  technician_notes: "Fake demo intake values only.",
  warnings_json: [],
  reviewed_by_user_id: null,
  signed_by_user_id: null,
  signed_at: null,
  created_by_user_id: 2,
  created_at: "2026-05-19T20:00:00Z",
  updated_at: "2026-05-19T20:00:00Z",
  ...over,
});

beforeEach(() => {
  vi.mocked(listVitalsWorkups).mockReset();
  vi.mocked(createVitalsWorkup).mockReset();
  vi.mocked(reviewVitalsWorkup).mockReset();
});

describe("VitalsWorkupPanel", () => {
  it("renders the panel and safety copy", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await waitFor(() => expect(screen.getByTestId("vitals-workup-panel")).toBeInTheDocument());
    const copy = screen.getByTestId("vitals-safety-copy");
    expect(copy).toHaveTextContent(/does not diagnose/i);
    expect(copy).toHaveTextContent(/does not recommend treatment/i);
    expect(copy).toHaveTextContent(/does not place orders/i);
  });

  it("fake demo vitals button loads synthetic values", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await userEvent.click(await screen.findByTestId("vitals-load-demo"));
    expect(screen.getByTestId("vitals-bp-systolic")).toHaveValue(118);
    expect(screen.getByTestId("vitals-va-od")).toHaveValue("20/30");
    expect(screen.getByTestId("vitals-technician-notes")).toHaveValue("Fake demo intake values only.");
  });

  it("BMI display updates from height and weight", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await userEvent.type(await screen.findByTestId("vitals-height"), "70");
    await userEvent.type(screen.getByTestId("vitals-weight"), "175");
    expect(screen.getByTestId("vitals-bmi-display")).toHaveTextContent("25.11");
  });

  it("warning panel appears for partial blood pressure", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await userEvent.type(await screen.findByTestId("vitals-bp-systolic"), "122");
    const warnings = screen.getByTestId("vitals-warnings-panel");
    expect(warnings).toHaveTextContent(/systolic entered without diastolic/i);
    expect(warnings).toHaveTextContent(/without site/i);
    expect(warnings).toHaveTextContent(/without position/i);
  });

  it("save/create flow works with mocked API", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    vi.mocked(createVitalsWorkup).mockResolvedValueOnce(workup());
    render(<VitalsWorkupPanel encounterId={7} />);
    await userEvent.click(await screen.findByTestId("vitals-load-demo"));
    await userEvent.click(screen.getByTestId("vitals-save"));
    await waitFor(() => expect(createVitalsWorkup).toHaveBeenCalled());
    expect(createVitalsWorkup).toHaveBeenCalledWith(7, expect.objectContaining({ source_type: "demo" }));
  });

  it("review button is visible and distinct from sign", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([workup()]);
    vi.mocked(reviewVitalsWorkup).mockResolvedValueOnce(workup({ status: "reviewed", reviewed_by_user_id: 2 }));
    render(<VitalsWorkupPanel encounterId={7} />);
    expect(await screen.findByTestId("vitals-review")).toHaveTextContent("Review");
    expect(screen.getByTestId("vitals-sign")).toHaveTextContent("Sign");
    await userEvent.click(screen.getByTestId("vitals-review"));
    await waitFor(() => expect(reviewVitalsWorkup).toHaveBeenCalledWith(11));
  });

  it("sign requires attestation", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([workup({ status: "reviewed" })]);
    render(<VitalsWorkupPanel encounterId={7} />);
    expect(await screen.findByTestId("vitals-sign")).toBeDisabled();
    await userEvent.click(screen.getByTestId("vitals-sign-attestation"));
    expect(screen.getByTestId("vitals-sign")).not.toBeDisabled();
  });

  it("signed state hides edit controls", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([
      workup({ status: "signed", signed_at: "2026-05-19T20:30:00Z", signed_by_user_id: 2 }),
    ]);
    render(<VitalsWorkupPanel encounterId={7} />);
    expect(await screen.findByTestId("vitals-locked-banner")).toBeInTheDocument();
    expect(screen.getByTestId("vitals-signed-readonly")).toBeInTheDocument();
    expect(screen.queryByTestId("vitals-save")).not.toBeInTheDocument();
    expect(screen.queryByTestId("vitals-load-demo")).not.toBeInTheDocument();
  });

  it("does not render forbidden action or compliance phrases", async () => {
    vi.mocked(listVitalsWorkups).mockResolvedValueOnce([]);
    render(<VitalsWorkupPanel encounterId={7} />);
    await screen.findByTestId("vitals-workup-panel");
    const text = document.body.textContent?.toLowerCase() ?? "";
    for (const phrase of [
      "diagnosis confirmed",
      "treatment recommended",
      "order placed",
      "billing code",
      "automatic coding",
      "patient message sent",
      "hipaa compliant",
      "ehr replacement",
    ]) {
      expect(text).not.toContain(phrase);
    }
  });
});
