// Phase 2 item 4 — vitest coverage for MessageStatusLabel + OptOutBadge.
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageStatusLabel } from "../MessageStatusLabel";
import { OptOutBadge } from "../OptOutBadge";

describe("MessageStatusLabel", () => {
  it("renders 'Stub-delivered' when status=delivered + providerKind=stub", () => {
    render(<MessageStatusLabel status="delivered" providerKind="stub" />);
    expect(screen.getByTestId("message-status-label")).toHaveTextContent(
      "Stub-delivered"
    );
  });

  it("renders 'Delivered' for a non-stub provider", () => {
    render(<MessageStatusLabel status="delivered" providerKind="twilio" />);
    expect(screen.getByTestId("message-status-label")).toHaveTextContent(
      "Delivered"
    );
  });

  it("renders 'Opted out (not sent)' for status=opt_out", () => {
    render(<MessageStatusLabel status="opt_out" providerKind="stub" />);
    expect(screen.getByTestId("message-status-label")).toHaveTextContent(
      /opted out/i
    );
  });
});

describe("OptOutBadge", () => {
  it("renders when opted_in is false", () => {
    render(<OptOutBadge optedIn={false} channel="sms_stub" source="inbound-stop" />);
    const badge = screen.getByTestId("opt-out-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("data-channel", "sms_stub");
  });

  it("does NOT render when opted_in is true", () => {
    const { container } = render(<OptOutBadge optedIn={true} channel="sms_stub" />);
    expect(container.querySelector('[data-testid="opt-out-badge"]')).toBeNull();
  });
});
