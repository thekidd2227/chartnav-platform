import React from "react";
import type { VitalsWorkup, VitalsStatus } from "./vitalsTypes";

interface Props {
  workup: VitalsWorkup;
}

export function vitalsStatusLabel(status: VitalsStatus): string {
  if (status === "signed") return "Signed · Locked";
  if (status === "reviewed") return "Reviewed";
  if (status === "entered") return "Entered";
  if (status === "superseded") return "Superseded";
  return "Draft";
}

export function vitalsStatusPillStyle(
  status: VitalsStatus,
): React.CSSProperties {
  if (status === "signed")
    return { background: "#c6f6d5", color: "#276749" };
  if (status === "reviewed")
    return { background: "#bee3f8", color: "#2a4a7f" };
  if (status === "entered")
    return { background: "#fed7aa", color: "#7c2d12" };
  return { background: "#fed7d7", color: "#9b2c2c" };
}

export function StatusTimeline({ status }: { status: VitalsWorkup["status"] }) {
  const steps: ReadonlyArray<{
    key: VitalsWorkup["status"];
    label: string;
    active: boolean;
  }> = [
    { key: "draft", label: "Draft", active: true },
    {
      key: "entered",
      label: "Entered",
      active:
        status === "entered" || status === "reviewed" || status === "signed",
    },
    {
      key: "reviewed",
      label: "Reviewed",
      active: status === "reviewed" || status === "signed",
    },
    { key: "signed", label: "Signed", active: status === "signed" },
  ];
  return (
    <div
      data-testid="vitals-status-timeline"
      style={{
        display: "flex",
        gap: 4,
        alignItems: "center",
        flexWrap: "wrap",
        marginBottom: 8,
      }}
    >
      {steps.map((s, i) => (
        <React.Fragment key={s.key}>
          <span
            data-testid={`vitals-status-step-${s.key}`}
            data-active={s.active ? "true" : "false"}
            style={{
              padding: "2px 10px",
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 700,
              background: s.active
                ? s.key === "signed"
                  ? "#c6f6d5"
                  : s.key === "reviewed"
                    ? "#bee3f8"
                    : s.key === "entered"
                      ? "#fed7aa"
                      : "#fed7d7"
                : "#edf2f7",
              color: s.active
                ? s.key === "signed"
                  ? "#276749"
                  : s.key === "reviewed"
                    ? "#2a4a7f"
                    : s.key === "entered"
                      ? "#7c2d12"
                      : "#9b2c2c"
                : "#a0aec0",
              letterSpacing: 0.3,
              textTransform: "uppercase",
            }}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <span
              aria-hidden
              style={{ width: 12, height: 1, background: "#cbd5e0" }}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export function WarningsList({ warnings }: { warnings: string[] }) {
  return (
    <div
      data-testid="vitals-warnings"
      style={{
        background: warnings.length > 0 ? "#fffbf0" : "#f7fafc",
        border:
          warnings.length > 0 ? "1px solid #f6d860" : "1px solid #e2e8f0",
        borderRadius: 6,
        padding: 10,
        marginBottom: 12,
      }}
    >
      <p
        style={{
          fontWeight: 600,
          fontSize: 12,
          color: warnings.length > 0 ? "#744210" : "#4a5568",
          margin: "0 0 4px",
        }}
      >
        Warnings (review required)
      </p>
      {warnings.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          {warnings.map((w, i) => (
            <li
              key={i}
              data-testid={`vitals-warning-${i}`}
              style={{ fontSize: 12, color: "#744210" }}
            >
              {w}
            </li>
          ))}
        </ul>
      ) : (
        <p
          data-testid="vitals-warnings-empty"
          style={{ fontSize: 12, color: "#718096", margin: 0 }}
        >
          No warnings. Provider review still required before signing.
        </p>
      )}
    </div>
  );
}

export function ForbiddenActionsCard({ workup }: Props) {
  const f = workup.forbidden_actions;
  const labels: ReadonlyArray<readonly [keyof typeof f, string]> = [
    ["diagnosis", "diagnosis"],
    ["treatment_recommendation", "treatment recommendation"],
    ["orders", "orders"],
    ["referrals", "referrals"],
    ["patient_message", "patient messages"],
    ["billing_or_coding", "billing or coding"],
    ["device_integration", "device integration"],
    ["remote_patient_monitoring", "remote patient monitoring"],
    ["auto_sign", "auto-sign"],
  ];
  return (
    <div
      data-testid="vitals-actions-summary"
      style={{
        background: "#edf2f7",
        border: "1px solid #cbd5e0",
        borderRadius: 6,
        padding: 10,
        marginBottom: 12,
      }}
    >
      <p
        style={{
          fontWeight: 600,
          fontSize: 12,
          color: "#4a5568",
          margin: "0 0 4px",
        }}
      >
        What ChartNav did NOT do
      </p>
      <ul
        style={{
          margin: "4px 0 0 0",
          paddingLeft: 16,
          fontSize: 11,
          color: "#4a5568",
        }}
      >
        {labels.map(([key, label]) => (
          <li key={key} data-testid={`vitals-forbidden-${key}`}>
            ChartNav did not perform {label} ({String(f[key])}).
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SignedLockBanner({ workup }: Props) {
  if (workup.status !== "signed") return null;
  const warningCount = workup.warnings.length;
  return (
    <div
      data-testid="vitals-signed-lock"
      style={{
        marginTop: 12,
        padding: 12,
        background: "#f0fff4",
        border: "1px solid #9ae6b4",
        borderRadius: 6,
      }}
    >
      <p
        style={{
          margin: "0 0 4px",
          fontSize: 13,
          fontWeight: 600,
          color: "#276749",
        }}
      >
        Workup signed · locked
      </p>
      <p
        style={{
          margin: 0,
          fontSize: 12,
          color: "#22543d",
          lineHeight: 1.5,
        }}
        data-testid="vitals-signed-meta"
      >
        Signed{" "}
        {workup.signed_at
          ? new Date(workup.signed_at).toLocaleString()
          : ""}
        {workup.signed_by_user_id !== null && (
          <> by clinician #{workup.signed_by_user_id}</>
        )}
        . Signed workups are immutable.
      </p>
      {workup.reviewed_at && workup.reviewed_by_user_id !== null && (
        <p
          style={{
            margin: "4px 0 0",
            fontSize: 12,
            color: "#22543d",
            lineHeight: 1.5,
          }}
          data-testid="vitals-signed-reviewer"
        >
          Reviewed {new Date(workup.reviewed_at).toLocaleString()} by
          clinician #{workup.reviewed_by_user_id}.
        </p>
      )}
      <p
        style={{
          margin: "6px 0 0",
          fontSize: 11,
          fontWeight: 600,
          color: "#276749",
          textTransform: "uppercase",
          letterSpacing: 0.4,
        }}
        data-testid="vitals-signed-summary"
      >
        Locked snapshot · {warningCount} warning
        {warningCount === 1 ? "" : "s"} at signing
      </p>
      <p
        style={{
          margin: "8px 0 0",
          fontSize: 11,
          color: "#38a169",
          lineHeight: 1.5,
        }}
        data-testid="vitals-audit-note"
      >
        ChartNav records metadata-only audit events: who created,
        reviewed, and signed, and when. The audit trail does not store
        clinical free text.
      </p>
    </div>
  );
}

export function AwaitingReviewCallout({
  status,
}: {
  status: VitalsStatus;
}) {
  if (status === "signed" || status === "reviewed") return null;
  return (
    <div
      data-testid="vitals-awaiting-review"
      style={{
        background: "#ebf8ff",
        border: "1px solid #bee3f8",
        borderRadius: 6,
        padding: 10,
        marginBottom: 12,
        fontSize: 12,
        color: "#2a4a7f",
        lineHeight: 1.5,
      }}
    >
      <strong>Awaiting provider review.</strong> Technician has entered
      intake data. A provider must review and sign before this workup is
      finalized. Not a diagnosis. Not a treatment recommendation.
    </div>
  );
}
