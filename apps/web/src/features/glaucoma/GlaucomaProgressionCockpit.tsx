// Phase 79 — Glaucoma Progression Cockpit.
//
// Read-only per-eye aggregator surface for IOP + visual-field + OCT
// review state. The cockpit surfaces what the provider's measurements
// show — it does not interpret IOP trends, does not classify glaucoma
// progression, does not recommend medication / laser / surgery, does
// not interpret VF or OCT.
//
// Missing data renders as an explicit "Insufficient data" state with
// no synthesized values.

import React, { useCallback, useEffect, useState } from "react";
import { getGlaucomaSummary } from "./glaucomaApi";
import type {
  GlaucomaEye,
  GlaucomaEyeLane,
  GlaucomaModalitySummary,
  GlaucomaSummary,
} from "./glaucomaTypes";

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

function modalityTone(m: GlaucomaModalitySummary): Tone {
  if (m.insufficient_data) return "red";
  if (m.latest_reviewed_at) return "green";
  if (m.latest_status === "ready_for_review") return "amber";
  return "amber";
}

function modalityLabel(m: GlaucomaModalitySummary): string {
  if (m.insufficient_data) return "Insufficient data";
  if (m.latest_reviewed_at) return "Reviewed";
  if (m.latest_status === "ready_for_review") return "Ready for review";
  if (m.latest_status === "uploaded") return "Uploaded";
  if (m.latest_status === "pending_upload") return "Pending upload";
  if (m.latest_status === "archived") return "Archived";
  return m.latest_status ?? "Unknown";
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

function ModalityRow({
  title,
  summary,
  testid,
}: {
  title: string;
  summary: GlaucomaModalitySummary;
  testid: string;
}) {
  const tone = modalityTone(summary);
  return (
    <div
      data-testid={testid}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "4px 0",
        borderTop: "1px solid #e2e8f0",
        fontSize: 12,
        color: "#2d3748",
      }}
    >
      <span style={{ flex: "0 0 110px", fontWeight: 600 }}>{title}</span>
      <span
        data-testid={`${testid}-tone`}
        style={{
          ...toneStyle(tone),
          padding: "1px 8px",
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: 0.3,
          textTransform: "uppercase",
        }}
      >
        {modalityLabel(summary)}
      </span>
      <span style={{ marginLeft: "auto", fontSize: 11, color: "#4a5568" }}>
        {summary.count} total
        {summary.latest_captured_at && (
          <> · latest {fmtDate(summary.latest_captured_at)}</>
        )}
      </span>
    </div>
  );
}

function IopBlock({ lane }: { lane: GlaucomaEyeLane }) {
  if (lane.iop_count === 0) {
    return (
      <div
        data-testid={`glaucoma-${lane.eye}-iop-empty`}
        style={{
          marginTop: 6,
          padding: 8,
          background: "#fed7d7",
          border: "1px solid #fc8181",
          borderRadius: 6,
          fontSize: 12,
          color: "#822727",
        }}
      >
        Insufficient data — no IOP recorded for {lane.eye} yet.
      </div>
    );
  }
  return (
    <div
      data-testid={`glaucoma-${lane.eye}-iop-block`}
      style={{
        marginTop: 6,
        padding: 8,
        background: "#f7fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        fontSize: 12,
        color: "#2d3748",
        lineHeight: 1.5,
      }}
    >
      <div>
        <strong>Latest IOP ({lane.eye}):</strong>{" "}
        <span data-testid={`glaucoma-${lane.eye}-iop-latest-value`}>
          {lane.latest_iop?.value} mmHg
        </span>{" "}
        <span style={{ fontSize: 11, color: "#4a5568" }}>
          ({fmtDate(lane.latest_iop?.recorded_at ?? null)})
        </span>
      </div>
      <div style={{ marginTop: 4, fontSize: 11, color: "#4a5568" }}>
        Trend ({lane.iop_count}):{" "}
        <span data-testid={`glaucoma-${lane.eye}-iop-trend-list`}>
          {lane.iop_history
            .slice(0, 6)
            .map((m) => `${m.value}`)
            .join(" → ")}{" "}
          mmHg
        </span>
      </div>
    </div>
  );
}

function EyeLane({ lane }: { lane: GlaucomaEyeLane }) {
  const longForm =
    lane.eye === "OD" ? "OD · Right Eye" : "OS · Left Eye";
  const completenessTone: Tone =
    lane.data_completeness.score_numerator >= 2
      ? "green"
      : lane.data_completeness.score_numerator === 1
        ? "amber"
        : "red";
  return (
    <div
      data-testid={`glaucoma-eye-lane-${lane.eye}`}
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
          data-testid={`glaucoma-${lane.eye}-completeness`}
          style={{
            ...toneStyle(completenessTone),
            padding: "1px 8px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.3,
            textTransform: "uppercase",
          }}
        >
          {lane.data_completeness.score_numerator} /{" "}
          {lane.data_completeness.score_denominator} signals
        </span>
      </div>

      {lane.insufficient_data && (
        <p
          data-testid={`glaucoma-${lane.eye}-insufficient`}
          style={{
            margin: "0 0 8px",
            padding: 8,
            background: "#fed7d7",
            border: "1px solid #fc8181",
            borderRadius: 6,
            fontSize: 12,
            color: "#822727",
          }}
        >
          Insufficient data for {lane.eye}. No IOP recorded, no visual-field
          study on file, no OCT RNFL study on file.
        </p>
      )}

      <IopBlock lane={lane} />

      <div style={{ marginTop: 8 }}>
        <ModalityRow
          title="Visual field"
          summary={lane.visual_field}
          testid={`glaucoma-${lane.eye}-vf`}
        />
        <ModalityRow
          title="OCT RNFL"
          summary={lane.oct_rnfl}
          testid={`glaucoma-${lane.eye}-oct-rnfl`}
        />
        <ModalityRow
          title="OCT macula"
          summary={lane.oct_macula}
          testid={`glaucoma-${lane.eye}-oct-macula`}
        />
      </div>
    </div>
  );
}

export function GlaucomaProgressionCockpit({ patientId }: Props) {
  const [summary, setSummary] = useState<GlaucomaSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(() => {
    setLoading(true);
    setError(null);
    getGlaucomaSummary(patientId)
      .then(setSummary)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <div
      data-testid="glaucoma-progression-cockpit"
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
          Glaucoma Progression Cockpit
        </h3>
        <button
          type="button"
          onClick={fetchSummary}
          disabled={loading}
          data-testid="glaucoma-refresh-btn"
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
        data-testid="glaucoma-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-reviewed workflow intelligence. Aggregates IOP history,
        visual-field metadata, and OCT review state per eye from existing
        encounter data. ChartNav does not interpret these measurements
        and does not classify glaucoma progression.
      </p>

      {error && (
        <p
          data-testid="glaucoma-error"
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
          data-testid="glaucoma-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {summary && (
        <>
          <p
            data-testid="glaucoma-patient-meta"
            style={{
              margin: "0 0 12px",
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <strong>{summary.patient_name ?? "Unknown patient"}</strong>{" "}
            ({summary.patient_identifier ?? "—"}) ·{" "}
            <span data-testid="glaucoma-bilateral-flag">
              {summary.bilateral_data ? "Bilateral data" : "Unilateral data"}
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
            data-testid="glaucoma-disclosure"
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
