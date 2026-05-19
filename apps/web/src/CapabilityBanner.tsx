/**
 * Phase 25A / GH-011 — demo-mode capability banner.
 *
 * Renders an unambiguous strip whenever the backend reports
 * `capability_banner.demo_mode === true`. The text comes straight
 * from the server so the frontend cannot soften / paraphrase / lose
 * the disclaimer. The component renders nothing when the server
 * doesn't ship a banner (backwards compat) or when demo_mode is
 * off.
 */

import type { PlatformInfo } from "./api";

interface CapabilityBannerProps {
  platform: PlatformInfo | null;
}

const REASON_LABELS: Record<string, string> = {
  stt_stub: "STT is the deterministic stub",
  stt_none: "STT is disabled (uploads will fail honestly)",
  standalone_mode: "ChartNav-native mode (no upstream EHR)",
  real_phi_gate_off: "Real-PHI go-live gate has NOT been flipped",
};

export function CapabilityBanner({
  platform,
}: CapabilityBannerProps): JSX.Element | null {
  const banner = platform?.capability_banner;
  if (!banner || !banner.demo_mode) return null;

  return (
    <div
      className="capability-banner capability-banner--demo"
      role="status"
      aria-live="polite"
      data-testid="capability-banner"
      data-demo-mode="true"
    >
      <div className="capability-banner__text">
        <strong data-testid="capability-banner-title">
          {banner.banner_text}
        </strong>
      </div>
      {banner.reasons.length > 0 && (
        <ul
          className="capability-banner__reasons"
          data-testid="capability-banner-reasons"
        >
          {banner.reasons.map((r) => (
            <li
              key={r}
              data-testid={`capability-banner-reason-${r}`}
              data-reason={r}
            >
              {REASON_LABELS[r] ?? r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
