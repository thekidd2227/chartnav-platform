// Phase 80 — Cataract Surgical Workflow Panel.
//
// Read-only per-eye workflow surface for cataract pre-op + post-op
// state. Surfaces provider-entered data verbatim under explicit
// "provider-entered" labeling. Computes deterministic readiness +
// cadence scores from existing data.
//
// ChartNav does NOT select an IOL power, does NOT recommend a
// surgical technique, does NOT recommend a surgery date, does NOT
// infer complications, and does NOT order tests.

import React, { useCallback, useEffect, useState } from "react";
import { getCataractWorkflowSummary } from "./cataractApi";
import type {
  CataractConsentStatus,
  CataractEye,
  CataractEyeLane,
  CataractPostopStatus,
  CataractWorkflowSummary,
} from "./cataractTypes";

interface Props {
  patientId: number;
}

type Tone = "green" | "amber" | "red" | "neutral";

function toneStyle(tone: Tone): React.CSSProperties {
  if (tone === "green") return { background: "#c6f6d5", color: "#1c4532" };
  if (tone === "amber") return { background: "#fed7aa", color: "#7c2d12" };
  if (tone === "red") return { background: "#fed7d7", color: "#822727" };
  return { background: "#edf2f7", color: "#2d3748" };
}

function consentLabel(status: CataractConsentStatus): string {
  if (status === "signed") return "Signed";
  if (status === "in_progress") return "In progress";
  if (status === "declined") return "Declined";
  if (status === "not_obtained") return "Not obtained";
  return "Unknown";
}

function consentTone(status: CataractConsentStatus): Tone {
  if (status === "signed") return "green";
  if (status === "in_progress") return "amber";
  if (status === "declined" || status === "not_obtained") return "red";
  return "neutral";
}

function postopLabel(status: CataractPostopStatus): string {
  if (status === "completed") return "Completed";
  if (status === "scheduled") return "Scheduled";
  if (status === "missed") return "Missed";
  if (status === "not_scheduled") return "Not scheduled";
  return "Unknown";
}

function postopTone(status: CataractPostopStatus): Tone {
  if (status === "completed") return "green";
  if (status === "scheduled") return "amber";
  if (status === "missed") return "red";
  if (status === "not_scheduled") return "neutral";
  return "neutral";
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso + "T00:00:00Z").toLocaleDateString();
  } catch {
    return iso;
  }
}

function PreopRow({ lane }: { lane: CataractEyeLane }) {
  const r = lane.preop_readiness;
  const tone: Tone =
    r.score_numerator >= 3
      ? "green"
      : r.score_numerator >= 1
        ? "amber"
        : "red";
  const latest = lane.latest_record;
  return (
    <div
      data-testid={`cataract-${lane.eye}-preop`}
      style={{
        padding: 10,
        background: "#f7fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        marginBottom: 6,
        fontSize: 12,
        color: "#2d3748",
        lineHeight: 1.6,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 4,
        }}
      >
        <strong>Pre-op readiness</strong>
        <span
          data-testid={`cataract-${lane.eye}-preop-score`}
          style={{
            ...toneStyle(tone),
            padding: "1px 6px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.3,
            textTransform: "uppercase",
          }}
        >
          {r.score_numerator} / {r.score_denominator} signals
        </span>
      </div>
      <div>
        <strong>Planned surgery:</strong>{" "}
        <span data-testid={`cataract-${lane.eye}-planned-date`}>
          {latest?.planned_surgery_date
            ? fmtDate(latest.planned_surgery_date)
            : "Not entered"}
        </span>
      </div>
      <div>
        <strong>Biometry reviewed:</strong>{" "}
        <span data-testid={`cataract-${lane.eye}-biometry`}>
          {r.biometry_reviewed ? "Yes" : "No"}
        </span>
      </div>
      <div>
        <strong>Topography reviewed:</strong>{" "}
        <span data-testid={`cataract-${lane.eye}-topography`}>
          {r.topography_reviewed ? "Yes" : "No"}
        </span>
      </div>
      <div>
        <strong>Consent:</strong>{" "}
        <span
          data-testid={`cataract-${lane.eye}-consent`}
          style={{
            ...toneStyle(consentTone(latest?.consent_status ?? "unknown")),
            padding: "1px 6px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.3,
            textTransform: "uppercase",
            marginLeft: 4,
          }}
        >
          {consentLabel(latest?.consent_status ?? "unknown")}
        </span>
      </div>
    </div>
  );
}

function PostopRow({ lane }: { lane: CataractEyeLane }) {
  const c = lane.postop_cadence;
  const tone: Tone =
    c.score_numerator >= 2 ? "green" : c.score_numerator === 1 ? "amber" : "red";
  return (
    <div
      data-testid={`cataract-${lane.eye}-postop`}
      style={{
        padding: 10,
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        marginBottom: 6,
        fontSize: 12,
        color: "#2d3748",
        lineHeight: 1.6,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 4,
        }}
      >
        <strong>Post-op cadence</strong>
        <span
          data-testid={`cataract-${lane.eye}-postop-score`}
          style={{
            ...toneStyle(tone),
            padding: "1px 6px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.3,
            textTransform: "uppercase",
          }}
        >
          {c.score_numerator} / {c.score_denominator} checkpoints
        </span>
      </div>
      <CheckpointRow
        label="Day 1"
        status={c.postop_day_1_status}
        testid={`cataract-${lane.eye}-postop-day-1`}
      />
      <CheckpointRow
        label="Week 1"
        status={c.postop_week_1_status}
        testid={`cataract-${lane.eye}-postop-week-1`}
      />
      <CheckpointRow
        label="Month 1"
        status={c.postop_month_1_status}
        testid={`cataract-${lane.eye}-postop-month-1`}
      />
    </div>
  );
}

function CheckpointRow({
  label,
  status,
  testid,
}: {
  label: string;
  status: CataractPostopStatus;
  testid: string;
}) {
  return (
    <div
      data-testid={testid}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "2px 0",
        fontSize: 12,
      }}
    >
      <span style={{ flex: "0 0 80px", fontWeight: 600 }}>{label}</span>
      <span
        data-testid={`${testid}-tone`}
        style={{
          ...toneStyle(postopTone(status)),
          padding: "1px 8px",
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: 0.3,
          textTransform: "uppercase",
        }}
      >
        {postopLabel(status)}
      </span>
    </div>
  );
}

function EyeLane({ lane }: { lane: CataractEyeLane }) {
  const longForm = lane.eye === "OD" ? "OD · Right Eye" : "OS · Left Eye";
  return (
    <div
      data-testid={`cataract-eye-lane-${lane.eye}`}
      style={{
        flex: "1 1 320px",
        minWidth: 280,
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
          }}
        >
          {longForm}
        </h4>
        <span
          data-testid={`cataract-${lane.eye}-record-count`}
          style={{ fontSize: 11, color: "#4a5568" }}
        >
          {lane.record_count} record{lane.record_count === 1 ? "" : "s"}
        </span>
      </div>

      {lane.insufficient_data ? (
        <p
          data-testid={`cataract-${lane.eye}-insufficient`}
          style={{
            margin: 0,
            padding: 8,
            background: "#fed7d7",
            border: "1px solid #fc8181",
            borderRadius: 6,
            fontSize: 12,
            color: "#822727",
          }}
        >
          Insufficient data — no cataract workflow record entered for{" "}
          {lane.eye} yet.
        </p>
      ) : (
        <>
          <PreopRow lane={lane} />
          <PostopRow lane={lane} />
          {lane.complications_flag && (
            <div
              data-testid={`cataract-${lane.eye}-complications-flag`}
              style={{
                padding: 8,
                background: "#fffbf0",
                border: "1px solid #f6d860",
                borderRadius: 6,
                fontSize: 12,
                color: "#744210",
              }}
            >
              <strong>Provider-entered complications flag set.</strong>{" "}
              Details on the per-record view (provider-entered note,
              not interpreted by ChartNav).
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function CataractSurgicalWorkflowPanel({ patientId }: Props) {
  const [summary, setSummary] = useState<CataractWorkflowSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(() => {
    setLoading(true);
    setError(null);
    getCataractWorkflowSummary(patientId)
      .then(setSummary)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <div
      data-testid="cataract-surgical-workflow-panel"
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
          Cataract Surgical Workflow
        </h3>
        <button
          type="button"
          onClick={fetchSummary}
          disabled={loading}
          data-testid="cataract-refresh-btn"
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
        data-testid="cataract-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-entered surgical workflow support. Bilateral lane split,
        pre-op readiness signals, post-op cadence checkpoints. Does not
        select lens power. Does not recommend technique. Does not place
        orders.
      </p>

      {error && (
        <p
          data-testid="cataract-error"
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

      {loading && summary === null && (
        <p
          data-testid="cataract-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {summary && (
        <>
          <p
            data-testid="cataract-patient-meta"
            style={{
              margin: "0 0 12px",
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <strong>{summary.patient_name ?? "Unknown patient"}</strong>{" "}
            ({summary.patient_identifier ?? "—"}) ·{" "}
            <span data-testid="cataract-bilateral-flag">
              {summary.bilateral_planned
                ? "Bilateral surgery planned"
                : "No bilateral surgery planned"}
            </span>
          </p>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12,
            }}
          >
            <EyeLane lane={summary.od} />
            <EyeLane lane={summary.os} />
          </div>

          <p
            data-testid="cataract-disclosure"
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
            {summary.disclosure}
          </p>
        </>
      )}
    </div>
  );
}
