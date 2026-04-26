// Phase A item 5 — vitest coverage for OfflineBanner.
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OfflineBanner, isStateTransitionAllowed } from "../core/offline/OfflineBanner";

describe("OfflineBanner", () => {
  it("renders nothing when online", () => {
    const { container } = render(<OfflineBanner online={true} />);
    expect(container.querySelector('[data-testid="offline-banner"]')).toBeNull();
  });

  it("renders the banner with the documented testid when offline", () => {
    render(<OfflineBanner online={false} />);
    const banner = screen.getByTestId("offline-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/offline/i);
    expect(banner).toHaveTextContent(/signing.*disabled/i);
  });

  it("isStateTransitionAllowed mirrors the online state", () => {
    expect(isStateTransitionAllowed(true)).toBe(true);
    expect(isStateTransitionAllowed(false)).toBe(false);
  });
});
