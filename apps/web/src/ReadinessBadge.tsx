// ROI wave 1 · item 6
//
// Compact readiness badge rendered on each encounter card. Severity
// drives color via the existing token set.

import { Readiness } from "./readiness";

const SEVERITY_TO_KIND: Record<Readiness["severity"], string> = {
  ok: "ok",
  info: "info",
  warn: "warn",
  error: "error",
  muted: "muted",
};

export function ReadinessBadge({ r }: { r: Readiness }) {
  const sev = SEVERITY_TO_KIND[r.severity] || "muted";
  return (
    <span
      className="readiness-badge"
      data-severity={sev}
      data-kind={r.kind}
      title={r.tooltip ?? r.label}
      data-testid={`readiness-${r.kind}`}
    >
      {r.label}
    </span>
  );
}
