// Phase A item 5 — Offline banner.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.3.
//
// When the network drops, surface a persistent banner at the top of
// the viewport and explicitly state that state-changing actions
// (sign / export) are disabled until the connection comes back. This
// is a UX honesty surface — ChartNav is not offline-first; the user
// has to know that.
import { useOnlineStatus } from "./queue";

export interface OfflineBannerProps {
  /** Optional override for tests; in production the hook is used. */
  online?: boolean;
}

export function OfflineBanner(props: OfflineBannerProps) {
  const hookOnline = useOnlineStatus();
  const online = props.online !== undefined ? props.online : hookOnline;
  if (online) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="offline-banner"
    >
      You are offline. Charting input is queued locally; signing and
      handoff export are disabled until you reconnect.
    </div>
  );
}

/** Predicate the encounter UI uses to disable sign / export
 *  buttons while offline. */
export function isStateTransitionAllowed(online: boolean): boolean {
  return online === true;
}
