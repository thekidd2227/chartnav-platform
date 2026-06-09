// Phase 78 — Anti-VEGF Injection Command Panel.
//
// Read-only workflow surface that summarizes the structured retina-
// injection state for one patient:
//   * bilateral OD / OS history split (newest first per eye)
//   * current interval + next due date per eye
//   * authorization badge with status + expiry
//   * lot number visibility for inventory + recall tracking
//   * readiness chip computed from latest record + today
//
// The panel never recommends a treatment, never proposes a drug
// switch, never autonomously orders, never interprets imaging. Every
// value displayed is what the provider entered.

import React, { useCallback, useEffect, useState } from "react";
import { getInjectionHistory } from "./antiVegfApi";
import type {
  AntiVegfAuthStatus,
  AntiVegfEye,
  AntiVegfHistory,
  AntiVegfInjection,
} from "./antiVegfTypes";

interface Props {
  patientId: number;
}

function authPillStyle(
  status: AntiVegfAuthStatus,
): React.CSSProperties {
  if (status === "approved")
    return { background: "#c6f6d5", color: "#1c4532" };
  if (status === "not_required")
    return { background: "#edf2f7", color: "#2d3748" };
  if (status === "pending")
    return { background: "#fed7aa", color: "#7c2d12" };
  if (status === "expired" || status === "denied")
    return { background: "#fed7d7", color: "#822727" };
  return { background: "#e2e8f0", color: "#1a202c" };
}

function authLabel(status: AntiVegfAuthStatus): string {
  if (status === "not_required") return "Not Required";
  if (status === "approved") return "Approved";
  if (status === "pending") return "Pending";
  if (status === "denied") return "Denied";
  if (status === "expired") return "Expired";
  return "Unknown";
}

function drugLabel(label: string): string {
  if (label === "anti_vegf_generic") return "Generic";
  if (label === "anti_vegf_biosimilar") return "Biosimilar";
  if (label === "anti_vegf_branded") return "Branded";
  return "Other";
}

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  try {
    const target = new Date(iso + "T00:00:00Z").getTime();
    const today = new Date(new Date().toISOString().slice(0, 10) + "T00:00:00Z").getTime();
    return Math.round((target - today) / 86400000);
  } catch {
    return null;
  }
}

function readinessChipFor(latest: AntiVegfInjection | null): {
  text: string;
  style: React.CSSProperties;
  testid: string;
} | null {
  if (latest === null) return null;
  if (latest.authorization_status === "expired") {
    return {
      text: "Auth expired",
      style: { background: "#fed7d7", color: "#822727" },
      testid: "readiness-chip-auth-expired",
    };
  }
  if (latest.authorization_status === "pending") {
    return {
      text: "Auth pending",
      style: { background: "#fed7aa", color: "#7c2d12" },
      testid: "readiness-chip-auth-pending",
    };
  }
  const d = daysUntil(latest.next_due_date);
  if (d === null) {
    return {
      text: "No interval set",
      style: { background: "#edf2f7", color: "#2d3748" },
      testid: "readiness-chip-no-interval",
    };
  }
  if (d < 0) {
    return {
      text: `Overdue ${Math.abs(d)}d`,
      style: { background: "#fed7d7", color: "#822727" },
      testid: "readiness-chip-overdue",
    };
  }
  if (d === 0) {
    return {
      text: "Due today",
      style: { background: "#fed7aa", color: "#7c2d12" },
      testid: "readiness-chip-due-today",
    };
  }
  if (d <= 7) {
    return {
      text: `Due in ${d}d`,
      style: { background: "#fed7aa", color: "#7c2d12" },
      testid: "readiness-chip-due-this-week",
    };
  }
  return {
    text: `In ${d}d`,
    style: { background: "#c6f6d5", color: "#1c4532" },
    testid: "readiness-chip-future",
  };
}

function EyeColumn({
  eye,
  latest,
  history,
}: {
  eye: AntiVegfEye;
  latest: AntiVegfInjection | null;
  history: AntiVegfInjection[];
}) {
  const longForm = eye === "OD" ? "OD · Right Eye" : "OS · Left Eye";
  const chip = readinessChipFor(latest);
  return (
    <div
      data-testid={`anti-vegf-eye-column-${eye}`}
      style={{
        flex: "1 1 280px",
        minWidth: 240,
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 6,
        }}
      >
        <h4
          style={{
            margin: 0,
            fontSize: 13,
            fontWeight: 700,
            color: "#2d3748",
            letterSpacing: 0.2,
          }}
        >
          {longForm}
        </h4>
        {chip && (
          <span
            data-testid={`anti-vegf-${eye}-readiness-chip`}
            style={{
              ...chip.style,
              padding: "2px 8px",
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: 0.3,
              textTransform: "uppercase",
            }}
          >
            {chip.text}
          </span>
        )}
      </div>

      {latest === null ? (
        <p
          data-testid={`anti-vegf-${eye}-empty`}
          style={{
            margin: 0,
            fontSize: 12,
            color: "#4a5568",
            padding: 8,
            border: "1px dashed #cbd5e0",
            borderRadius: 6,
            textAlign: "center",
          }}
        >
          No injection history recorded for {eye}.
        </p>
      ) : (
        <>
          <div
            data-testid={`anti-vegf-${eye}-latest`}
            style={{
              padding: 10,
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              marginBottom: 8,
              fontSize: 12,
              color: "#2d3748",
              lineHeight: 1.6,
            }}
          >
            <div>
              <strong>Last injection:</strong>{" "}
              <span data-testid={`anti-vegf-${eye}-latest-date`}>
                {latest.injection_date}
              </span>
            </div>
            <div>
              <strong>Drug class:</strong>{" "}
              <span data-testid={`anti-vegf-${eye}-drug`}>
                {drugLabel(latest.drug_label)}
              </span>
            </div>
            {latest.interval_weeks !== null && (
              <div>
                <strong>Current interval:</strong>{" "}
                <span data-testid={`anti-vegf-${eye}-interval`}>
                  every {latest.interval_weeks} weeks
                </span>
              </div>
            )}
            {latest.next_due_date && (
              <div>
                <strong>Next due:</strong>{" "}
                <span data-testid={`anti-vegf-${eye}-next-due`}>
                  {latest.next_due_date}
                </span>
              </div>
            )}
            <div style={{ marginTop: 4 }}>
              <strong>Authorization:</strong>{" "}
              <span
                data-testid={`anti-vegf-${eye}-auth-badge`}
                style={{
                  ...authPillStyle(latest.authorization_status),
                  padding: "1px 6px",
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 0.3,
                  textTransform: "uppercase",
                  marginLeft: 4,
                }}
              >
                {authLabel(latest.authorization_status)}
              </span>
              {latest.authorization_expires_on && (
                <>
                  {" "}
                  <span
                    style={{ fontSize: 11, color: "#4a5568" }}
                    data-testid={`anti-vegf-${eye}-auth-expires`}
                  >
                    (expires {latest.authorization_expires_on})
                  </span>
                </>
              )}
            </div>
            {latest.lot_number && (
              <div>
                <strong>Lot #:</strong>{" "}
                <span data-testid={`anti-vegf-${eye}-lot`}>
                  {latest.lot_number}
                </span>
              </div>
            )}
          </div>

          {history.length > 1 && (
            <div data-testid={`anti-vegf-${eye}-history-list`}>
              <p
                style={{
                  margin: "0 0 4px",
                  fontSize: 10,
                  fontWeight: 700,
                  color: "#4a5568",
                  textTransform: "uppercase",
                  letterSpacing: 0.4,
                }}
              >
                Earlier injections ({history.length - 1})
              </p>
              <ul
                style={{
                  listStyle: "none",
                  margin: 0,
                  padding: 0,
                  fontSize: 11,
                  color: "#2d3748",
                }}
              >
                {history.slice(1).map((h) => (
                  <li
                    key={h.id}
                    data-testid={`anti-vegf-${eye}-history-item-${h.id}`}
                    style={{
                      padding: "3px 6px",
                      borderLeft: "2px solid #cbd5e0",
                      marginBottom: 2,
                      background: "#fafbfc",
                    }}
                  >
                    {h.injection_date} · {drugLabel(h.drug_label)}
                    {h.lot_number ? ` · lot ${h.lot_number}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function InjectionCommandPanel({ patientId }: Props) {
  const [history, setHistory] = useState<AntiVegfHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(() => {
    setLoading(true);
    setError(null);
    getInjectionHistory(patientId)
      .then(setHistory)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return (
    <div
      data-testid="anti-vegf-injection-panel"
      style={{ fontFamily: "sans-serif", padding: 16 }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 6,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 16, color: "#2d3748" }}>
          Anti-VEGF Injection Rail
        </h3>
        <button
          type="button"
          onClick={fetchHistory}
          disabled={loading}
          data-testid="anti-vegf-refresh-btn"
          style={{
            fontSize: 11,
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #cbd5e0",
            background: "#fff",
            color: "#2d3748",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p
        data-testid="anti-vegf-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Structured retina injection workflow record. Bilateral split,
        provider-entered cadence, authorization status, lot tracking.
        ChartNav does not recommend a drug, dose, or treatment plan;
        does not interpret imaging; does not submit prior-auth.
      </p>

      {error && (
        <p
          data-testid="anti-vegf-error"
          style={{
            color: "#822727",
            fontSize: 12,
            marginBottom: 8,
            background: "#fff5f5",
            border: "1px solid #fed7d7",
            borderRadius: 6,
            padding: 8,
          }}
        >
          {error}
        </p>
      )}

      {loading && history === null && (
        <p
          data-testid="anti-vegf-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {history && (
        <>
          <p
            data-testid="anti-vegf-patient-meta"
            style={{
              margin: "0 0 12px",
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <strong>{history.patient_name ?? "Unknown patient"}</strong>{" "}
            ({history.patient_identifier ?? "—"}) ·{" "}
            <span data-testid="anti-vegf-bilateral-flag">
              {history.bilateral ? "Bilateral history" : "Unilateral history"}
            </span>{" "}
            · OD {history.od_count} · OS {history.os_count}
          </p>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <EyeColumn
              eye="OD"
              latest={history.latest_od}
              history={history.od_history}
            />
            <EyeColumn
              eye="OS"
              latest={history.latest_os}
              history={history.os_history}
            />
          </div>

          <p
            data-testid="anti-vegf-boundary-note"
            style={{
              marginTop: 12,
              padding: 10,
              background: "#f0fff4",
              border: "1px solid #9ae6b4",
              borderRadius: 6,
              fontSize: 11,
              color: "#1c4532",
              lineHeight: 1.5,
            }}
          >
            ChartNav records what the provider entered. It does not
            interpret OCT, fundus, or visual-field imagery. It does not
            choose a drug, a dose, or a cadence. Authorization status is
            provider-entered, not a ChartNav decision.
          </p>
        </>
      )}
    </div>
  );
}
