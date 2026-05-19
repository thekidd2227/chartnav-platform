import type { VitalWorkup } from "./vitalsTypes";

interface Props {
  workup: VitalWorkup | null;
  warnings: string[];
}

const STEPS: Array<{ key: VitalWorkup["status"]; label: string }> = [
  { key: "draft", label: "Draft" },
  { key: "entered", label: "Entered" },
  { key: "reviewed", label: "Reviewed" },
  { key: "signed", label: "Signed" },
];

function stepActive(status: VitalWorkup["status"] | undefined, step: VitalWorkup["status"]): boolean {
  const order = ["draft", "entered", "reviewed", "signed"];
  return order.indexOf(status ?? "draft") >= order.indexOf(step);
}

export function VitalsWorkupSummary({ workup, warnings }: Props) {
  const status = workup?.status ?? "draft";
  return (
    <aside data-testid="vitals-workup-summary" style={{ display: "grid", gap: 14 }}>
      {workup?.signed_at && (
        <div
          data-testid="vitals-locked-banner"
          style={{ border: "1px solid #9ae6b4", background: "#f0fff4", borderRadius: 8, padding: 10, color: "#276749", fontSize: 13, fontWeight: 700 }}
        >
          Signed and locked {new Date(workup.signed_at).toLocaleString()}
        </div>
      )}

      <div data-testid="vitals-status-timeline" style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {STEPS.map((step) => {
          const active = stepActive(status, step.key);
          return (
            <span
              key={step.key}
              data-testid={`vitals-status-${step.key}`}
              data-active={active ? "true" : "false"}
              style={{
                borderRadius: 12,
                padding: "3px 9px",
                fontSize: 11,
                fontWeight: 800,
                textTransform: "uppercase",
                background: active ? "#bee3f8" : "#edf2f7",
                color: active ? "#2a4a7f" : "#718096",
              }}
            >
              {step.label}
            </span>
          );
        })}
      </div>

      <div
        data-testid="vitals-warnings-panel"
        style={{
          border: "1px solid #fbd38d",
          background: warnings.length ? "#fffaf0" : "#f7fafc",
          borderRadius: 8,
          padding: 10,
          fontSize: 13,
        }}
      >
        <strong>Warnings</strong>
        {warnings.length ? (
          <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        ) : (
          <p style={{ margin: "6px 0 0", color: "#4a5568" }}>No review warnings.</p>
        )}
      </div>

      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 10px", margin: 0, fontSize: 13 }}>
        <dt style={{ fontWeight: 700 }}>Status</dt><dd style={{ margin: 0 }}>{status}</dd>
        <dt style={{ fontWeight: 700 }}>Source</dt><dd style={{ margin: 0 }}>{workup?.source_type ?? "technician_entry"}</dd>
        <dt style={{ fontWeight: 700 }}>BMI</dt><dd style={{ margin: 0 }}>{workup?.bmi == null ? "Not calculated" : workup.bmi.toFixed(2)}</dd>
        <dt style={{ fontWeight: 700 }}>Signed by</dt><dd style={{ margin: 0 }}>{workup?.signed_by_user_id ?? "Not signed"}</dd>
      </dl>
    </aside>
  );
}
