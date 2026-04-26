// Phase 2 item 3 — vitest coverage for IntakePage.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { IntakePage } from "../IntakePage";
import * as api from "../api";

const VIEW: api.IntakePublicView = {
  form_schema: {
    fields: [
      { name: "patient_name", label: "Full name", type: "text", required: true },
      { name: "reason_for_visit", label: "Reason", type: "textarea", required: true },
      { name: "consent", label: "I confirm…", type: "checkbox", required: true },
    ],
  },
  organization_branding: { name: "Demo Eye Clinic" },
  advisory: "After-hours intake",
};

describe("IntakePage", () => {
  beforeEach(() => {
    vi.spyOn(api, "getIntakeForm").mockResolvedValue(VIEW);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the form fields with the documented testids", async () => {
    render(<IntakePage token="abc123" />);
    await waitFor(() => screen.getByTestId("intake-form"));
    expect(screen.getByTestId("intake-consent-checkbox")).toBeInTheDocument();
    expect(screen.getByTestId("intake-submit")).toBeInTheDocument();
  });

  it("shows the thank-you screen after a successful submit", async () => {
    vi.spyOn(api, "submitIntake").mockResolvedValue({ submission_id: 42 });
    render(<IntakePage token="abc123" />);
    await waitFor(() => screen.getByTestId("intake-form"));
    fireEvent.change(screen.getAllByRole("textbox")[0], { target: { value: "Pat Doe" } });
    fireEvent.change(screen.getAllByRole("textbox")[1], { target: { value: "Eye pain" } });
    fireEvent.click(screen.getByTestId("intake-consent-checkbox"));
    await act(async () => {
      fireEvent.submit(screen.getByTestId("intake-form"));
    });
    await waitFor(() => screen.getByTestId("intake-submitted"));
  });

  it("shows the error screen when the token is unknown / expired", async () => {
    (api.getIntakeForm as any).mockRejectedValueOnce(
      new api.ApiError(410, "intake_token_expired", "intake token unavailable")
    );
    render(<IntakePage token="zzz" />);
    await waitFor(() => screen.getByTestId("intake-error"));
    expect(screen.getByTestId("intake-error-code")).toHaveTextContent(
      "intake_token_expired"
    );
  });
});
