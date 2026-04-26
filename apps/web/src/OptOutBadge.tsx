// Phase 2 item 4 — Opt-out badge.
//
// Spec: docs/chartnav/closure/PHASE_B_Reminders_and_Patient_Communication_Hardening.md §4.
//
// Surfaces an opt-out badge on a reminder's patient tag when the
// patient is opted out on the channel that reminder intends to use.
import React from "react";

export interface OptOutBadgeProps {
  optedIn: boolean;
  channel: string;
  source?: string | null;
  testId?: string;
}

export function OptOutBadge({
  optedIn,
  channel,
  source,
  testId = "opt-out-badge",
}: OptOutBadgeProps) {
  if (optedIn) return null;
  return (
    <span
      className="opt-out-badge"
      data-testid={testId}
      data-channel={channel}
      title={
        source
          ? `Patient opted out on ${channel} (${source})`
          : `Patient opted out on ${channel}`
      }
    >
      Opted out · {channel}
    </span>
  );
}
