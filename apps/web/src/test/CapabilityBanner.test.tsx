/**
 * Phase 25A / GH-011 — capability banner unit tests.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CapabilityBanner } from "../CapabilityBanner";
import type { PlatformInfo } from "../api";

const BASE_PLATFORM: PlatformInfo = {
  platform_mode: "standalone",
  integration_adapter: "chartnav_native",
  adapter: {
    key: "chartnav_native",
    display_name: "ChartNav native",
    description: "Standalone",
    supports: {
      patient_read: true,
      patient_write: true,
      encounter_read: true,
      encounter_write: true,
      document_write: true,
      document_transmit: false,
    },
    source_of_truth: {},
  },
};

describe("CapabilityBanner", () => {
  it("renders nothing when platform is null (loading state)", () => {
    const { container } = render(<CapabilityBanner platform={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when the server returns no capability_banner field", () => {
    const { container } = render(<CapabilityBanner platform={BASE_PLATFORM} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when demo_mode is false", () => {
    const { container } = render(
      <CapabilityBanner
        platform={{
          ...BASE_PLATFORM,
          capability_banner: {
            demo_mode: false,
            reasons: [],
            stt_provider: "openai_whisper",
            real_phi_approved_env: true,
            banner_text: "Operator approved.",
          },
        }}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the server-provided text verbatim when demo_mode is on", () => {
    render(
      <CapabilityBanner
        platform={{
          ...BASE_PLATFORM,
          capability_banner: {
            demo_mode: true,
            reasons: ["stt_stub", "real_phi_gate_off"],
            stt_provider: "stub",
            real_phi_approved_env: false,
            banner_text:
              "Demo mode — not approved for real patient health information.",
          },
        }}
      />,
    );
    const title = screen.getByTestId("capability-banner-title");
    // Must echo the server text without paraphrasing.
    expect(title).toHaveTextContent(
      /Demo mode .* not approved for real patient health information/,
    );
    expect(
      screen.getByTestId("capability-banner-reason-stt_stub"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("capability-banner-reason-real_phi_gate_off"),
    ).toBeInTheDocument();
  });

  it("falls back to the raw reason key for unknown reasons", () => {
    render(
      <CapabilityBanner
        platform={{
          ...BASE_PLATFORM,
          capability_banner: {
            demo_mode: true,
            reasons: ["surprise_reason"],
            stt_provider: "stub",
            real_phi_approved_env: false,
            banner_text: "Demo mode.",
          },
        }}
      />,
    );
    const li = screen.getByTestId("capability-banner-reason-surprise_reason");
    expect(li).toHaveTextContent("surprise_reason");
  });
});
