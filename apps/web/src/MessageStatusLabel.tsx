// Phase 2 item 4 — Message status label.
//
// Spec: docs/chartnav/closure/PHASE_B_Reminders_and_Patient_Communication_Hardening.md §4.
//
// The spec is explicit: any "Delivered" label produced by StubProvider
// MUST render as "Stub-delivered" so no demo / log / screenshot can
// imply real carrier transmission. This component owns that mapping
// in one place.
import React from "react";

export interface MessageStatusLabelProps {
  status: string;
  providerKind?: string;
  testId?: string;
}

const HUMAN: Record<string, string> = {
  queued: "Queued",
  sent: "Sent",
  delivered: "Delivered",
  failed: "Failed",
  opt_out: "Opted out (not sent)",
  read: "Read",
};

export function MessageStatusLabel({
  status,
  providerKind,
  testId = "message-status-label",
}: MessageStatusLabelProps) {
  let label = HUMAN[status] || status;
  // Stub provider mapping: any "Delivered" or "Sent" surfaced from
  // the stub is qualified so the UI cannot mislead.
  if (providerKind === "stub") {
    if (status === "delivered") label = "Stub-delivered";
    else if (status === "sent") label = "Stub-sent";
    else if (status === "opt_out") label = "Opted out (not sent)";
  }
  return (
    <span
      className={`message-status message-status--${status}`}
      data-testid={testId}
      data-provider-kind={providerKind || ""}
      data-status={status}
    >
      {label}
    </span>
  );
}
