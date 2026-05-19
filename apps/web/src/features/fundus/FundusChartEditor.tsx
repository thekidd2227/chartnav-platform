import React, { useState } from "react";
import type { FundusChart } from "./fundusTypes";
import { renderFundusChart, reviewFundusChart, signFundusChart } from "./fundusApi";
import { FundusChartRenderer } from "./FundusChartRenderer";
import { FundusChartLegend } from "./FundusChartLegend";

interface Props {
  encounterId: number;
  chart: FundusChart;
  onUpdated: (chart: FundusChart) => void;
}

function statusBadgeStyle(status: string, signed: boolean): React.CSSProperties {
  if (signed) return { background: "#c6f6d5", color: "#276749" };
  if (status === "reviewed") return { background: "#bee3f8", color: "#2a4a7f" };
  return { background: "#fed7d7", color: "#9b2c2c" };
}

function btn(bg: string): React.CSSProperties {
  return {
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 13,
    cursor: "pointer",
    fontWeight: 500,
  };
}

export function FundusChartEditor({ encounterId: _encounterId, chart, onUpdated }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings] = useState<string[]>(chart.warnings_json ?? []);

  const isSigned = chart.signed_at !== null;

  async function handleRender() {
    setLoading(true);
    setError(null);
    try {
      const res = await renderFundusChart(chart.id);
      onUpdated({ ...chart, rendered_svg: res.rendered_svg });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Render failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleReview() {
    setLoading(true);
    setError(null);
    try {
      await reviewFundusChart(chart.id);
      onUpdated({ ...chart, status: "reviewed" });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSign() {
    if (
      !window.confirm(
        "I attest that I have reviewed this fundus chart and it accurately reflects my clinical findings.",
      )
    )
      return;
    setLoading(true);
    setError(null);
    try {
      const res = await signFundusChart(chart.id);
      onUpdated({ ...chart, status: "signed", signed_at: res.signed_at });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
        <span
          style={{
            ...statusBadgeStyle(chart.status, isSigned),
            padding: "2px 8px",
            borderRadius: 12,
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {chart.status.toUpperCase()} — {chart.laterality}
        </span>
        {chart.source_type === "ai_generated" && (
          <span style={{ fontSize: 11, color: "#888" }}>AI-drafted · doctor review required</span>
        )}
      </div>

      {warnings.length > 0 && (
        <div
          style={{
            background: "#fffbf0",
            border: "1px solid #f6d860",
            borderRadius: 6,
            padding: 10,
            marginBottom: 12,
          }}
        >
          <p style={{ fontWeight: 600, fontSize: 12, color: "#744210", marginBottom: 4 }}>Warnings</p>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {warnings.map((w, i) => (
              <li key={i} style={{ fontSize: 12, color: "#744210" }}>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      <FundusChartRenderer drawing={chart.drawing_json} laterality={chart.laterality} size={320} />

      {chart.drawing_json && <FundusChartLegend elements={chart.drawing_json.elements ?? []} />}

      {error && <p style={{ color: "#c53030", fontSize: 12, marginTop: 8 }}>{error}</p>}

      <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
        {!isSigned && (
          <button onClick={handleRender} disabled={loading} style={btn("#3182ce")}>
            {loading ? "…" : "Render SVG"}
          </button>
        )}
        {!isSigned && chart.status !== "reviewed" && (
          <button onClick={handleReview} disabled={loading} style={btn("#38a169")}>
            {loading ? "…" : "Mark Reviewed"}
          </button>
        )}
        {!isSigned && (
          <button onClick={handleSign} disabled={loading} style={btn("#805ad5")}>
            {loading ? "…" : "Sign Chart"}
          </button>
        )}
      </div>

      {isSigned && (
        <p style={{ fontSize: 12, color: "#276749", marginTop: 8 }}>
          Signed {chart.signed_at ? new Date(chart.signed_at).toLocaleString() : ""}
        </p>
      )}
    </div>
  );
}
