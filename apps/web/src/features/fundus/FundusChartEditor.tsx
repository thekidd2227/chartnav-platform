import React, { useEffect, useState } from "react";
import type { FundusChart, Laterality } from "./fundusTypes";
import {
  renderFundusChart,
  reviewFundusChart,
  signFundusChart,
} from "./fundusApi";
import { FundusChartRenderer } from "./FundusChartRenderer";
import { FundusChartLegend } from "./FundusChartLegend";

interface Props {
  encounterId: number;
  chart: FundusChart;
  onUpdated: (chart: FundusChart) => void;
}

type Step = "draft" | "reviewed" | "signed";

export function lateralityLong(l: Laterality): string {
  return l === "OD"
    ? "OD · Right Eye"
    : l === "OS"
      ? "OS · Left Eye"
      : "OU · Both Eyes";
}

function extractFindingsText(chart: FundusChart): string | null {
  const j = chart.findings_json;
  if (!j) return null;
  const t = (j as { text?: unknown }).text;
  if (typeof t === "string" && t.trim().length > 0) return t.trim();
  return null;
}

function btn(bg: string, disabled = false): React.CSSProperties {
  return {
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: 13,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 600,
    opacity: disabled ? 0.5 : 1,
  };
}

function StatusTimeline({ chart }: { chart: FundusChart }) {
  const isSigned = chart.signed_at !== null;
  const isReviewed = isSigned || chart.status === "reviewed";

  const steps: Array<{ key: Step; label: string; active: boolean }> = [
    { key: "draft", label: "Draft", active: true },
    { key: "reviewed", label: "Reviewed", active: isReviewed },
    { key: "signed", label: "Signed", active: isSigned },
  ];

  return (
    <div
      data-testid="fundus-status-timeline"
      style={{
        display: "flex",
        gap: 4,
        alignItems: "center",
        marginBottom: 4,
      }}
    >
      {steps.map((s, i) => (
        <React.Fragment key={s.key}>
          <span
            data-testid={`fundus-status-step-${s.key}`}
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
                    : "#fed7d7"
                : "#edf2f7",
              color: s.active
                ? s.key === "signed"
                  ? "#276749"
                  : s.key === "reviewed"
                    ? "#2a4a7f"
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
              style={{
                width: 16,
                height: 1,
                background: "#cbd5e0",
              }}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export function FundusChartEditor({
  encounterId: _encounterId,
  chart,
  onUpdated,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>(
    chart.warnings_json ?? [],
  );
  const [attested, setAttested] = useState(false);

  useEffect(() => {
    setWarnings(chart.warnings_json ?? []);
    setAttested(false);
    setError(null);
  }, [chart.id, chart.warnings_json]);

  const isSigned = chart.signed_at !== null;
  const isReviewed = chart.status === "reviewed";
  const isAiDrafted = chart.source_type === "ai_generated";
  const findingsText = extractFindingsText(chart);
  const elementCount = chart.drawing_json?.elements?.length ?? 0;
  const warningCount = warnings.length;

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
      const res = await reviewFundusChart(chart.id);
      onUpdated({
        ...chart,
        status: "reviewed",
        reviewed_at: res.reviewed_at,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSign() {
    if (!attested) return;
    setLoading(true);
    setError(null);
    try {
      const res = await signFundusChart(chart.id);
      onUpdated({
        ...chart,
        status: "signed",
        signed_at: res.signed_at,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif" }} data-testid="fundus-chart-editor">
      <StatusTimeline chart={chart} />

      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          flexWrap: "wrap",
          marginBottom: 12,
          fontSize: 11,
          color: "#718096",
        }}
      >
        <span data-testid="fundus-laterality-badge">
          <strong style={{ color: "#2d3748" }}>
            {lateralityLong(chart.laterality)}
          </strong>{" "}
          · chart #{chart.id}
        </span>
        {isAiDrafted && (
          <span
            data-testid="fundus-ai-drafted-badge"
            style={{
              fontSize: 11,
              color: "#4a5568",
              background: "#edf2f7",
              padding: "1px 6px",
              borderRadius: 4,
            }}
          >
            AI-drafted from clinician findings · provider review required
          </span>
        )}
      </div>

      {!isSigned && (
        <div
          data-testid="fundus-awaiting-review"
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
          <strong>Awaiting provider review.</strong> ChartNav drafted this
          diagram from clinician-entered findings. The provider reviews,
          then signs to lock the chart. Not image interpretation.
        </div>
      )}

      {findingsText && (
        <div
          data-testid="fundus-clinician-findings"
          style={{
            background: "#fffaf0",
            border: "1px solid #feebc8",
            borderRadius: 6,
            padding: 10,
            marginBottom: 12,
          }}
        >
          <p
            style={{
              margin: "0 0 4px",
              fontSize: 11,
              fontWeight: 700,
              color: "#7b341e",
              textTransform: "uppercase",
              letterSpacing: 0.4,
            }}
          >
            Clinician-entered findings (input to this chart)
          </p>
          <p
            style={{
              margin: 0,
              fontSize: 12,
              color: "#7b341e",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
            }}
            data-testid="fundus-clinician-findings-text"
          >
            {findingsText}
          </p>
        </div>
      )}

      <div
        data-testid="fundus-warnings"
        style={{
          background: warnings.length > 0 ? "#fffbf0" : "#f7fafc",
          border:
            warnings.length > 0
              ? "1px solid #f6d860"
              : "1px solid #e2e8f0",
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
          Warnings
        </p>
        {warnings.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {warnings.map((w, i) => (
              <li
                key={i}
                style={{ fontSize: 12, color: "#744210" }}
                data-testid={`fundus-warning-${i}`}
              >
                {w}
              </li>
            ))}
          </ul>
        ) : (
          <p
            style={{
              fontSize: 12,
              color: "#718096",
              margin: 0,
            }}
            data-testid="fundus-warnings-empty"
          >
            No warnings. Provider must still review before signing.
          </p>
        )}
      </div>

      <p
        data-testid="fundus-renderer-caption"
        style={{
          margin: "0 0 6px",
          fontSize: 11,
          color: "#718096",
          lineHeight: 1.5,
        }}
      >
        Drafted from clinician findings · not interpreted from a fundus
        photo. The provider reviews this drawing before signing.
      </p>

      <FundusChartRenderer
        drawing={chart.drawing_json}
        laterality={chart.laterality}
        size={320}
      />

      <p
        data-testid="fundus-element-count"
        style={{
          margin: "6px 0 0",
          fontSize: 11,
          color: "#718096",
        }}
      >
        {elementCount} drafted element{elementCount === 1 ? "" : "s"}
        {warningCount > 0
          ? ` · ${warningCount} warning${warningCount === 1 ? "" : "s"}`
          : ""}
      </p>

      {chart.drawing_json && (
        <FundusChartLegend elements={chart.drawing_json.elements ?? []} />
      )}

      {error && (
        <p
          data-testid="fundus-editor-error"
          style={{
            color: "#c53030",
            fontSize: 12,
            marginTop: 8,
            background: "#fff5f5",
            border: "1px solid #fed7d7",
            borderRadius: 6,
            padding: 8,
          }}
        >
          {error}
        </p>
      )}

      {isSigned ? (
        <div
          data-testid="fundus-signed-lock"
          style={{
            marginTop: 16,
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
            Chart signed · locked
          </p>
          <p
            style={{
              margin: 0,
              fontSize: 12,
              color: "#22543d",
              lineHeight: 1.5,
            }}
            data-testid="fundus-signed-meta"
          >
            Signed{" "}
            {chart.signed_at
              ? new Date(chart.signed_at).toLocaleString()
              : ""}
            {chart.signed_by_user_id !== null && (
              <> by clinician #{chart.signed_by_user_id}</>
            )}
            . Signed charts are immutable.
          </p>
          {chart.reviewed_at && chart.reviewed_by_user_id !== null && (
            <p
              style={{
                margin: "4px 0 0",
                fontSize: 12,
                color: "#22543d",
                lineHeight: 1.5,
              }}
              data-testid="fundus-signed-reviewer"
            >
              Reviewed {new Date(chart.reviewed_at).toLocaleString()} by
              clinician #{chart.reviewed_by_user_id}.
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
            data-testid="fundus-signed-summary"
          >
            Locked snapshot · {elementCount} drafted element
            {elementCount === 1 ? "" : "s"} · {warningCount} warning
            {warningCount === 1 ? "" : "s"} at signing
          </p>
        </div>
      ) : (
        <div style={{ marginTop: 16 }}>
          <div
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              marginBottom: 12,
            }}
          >
            <button
              type="button"
              onClick={handleRender}
              disabled={loading}
              data-testid="fundus-render-btn"
              style={btn("#3182ce", loading)}
              title="Refresh the server-side SVG snapshot. The diagram above is always current; this just persists a new copy on the server."
            >
              {loading ? "…" : "Refresh server snapshot"}
            </button>
            <button
              type="button"
              onClick={handleReview}
              disabled={loading || isReviewed}
              data-testid="fundus-review-btn"
              style={btn("#38a169", loading || isReviewed)}
              title={
                isReviewed
                  ? "Already marked reviewed"
                  : "Mark reviewed (not the final signature)"
              }
            >
              {loading ? "…" : isReviewed ? "Reviewed" : "Mark Reviewed"}
            </button>
          </div>

          <div
            data-testid="fundus-attestation-block"
            style={{
              background: "#faf5ff",
              border: "1px solid #d6bcfa",
              borderRadius: 6,
              padding: 12,
            }}
          >
            <label
              style={{
                display: "flex",
                gap: 8,
                fontSize: 12,
                color: "#44337a",
                cursor: "pointer",
                lineHeight: 1.5,
              }}
            >
              <input
                type="checkbox"
                checked={attested}
                onChange={(e) => setAttested(e.target.checked)}
                data-testid="fundus-attestation-checkbox"
                style={{ marginTop: 3 }}
              />
              <span>
                I attest that I have reviewed this fundus chart and it
                accurately reflects my clinical findings. Signing will lock
                the chart — signed charts are immutable.
              </span>
            </label>
            <button
              type="button"
              onClick={handleSign}
              disabled={loading || !attested}
              data-testid="fundus-sign-btn"
              style={{ ...btn("#805ad5", loading || !attested), marginTop: 10 }}
              title={
                attested
                  ? "Sign and lock this chart"
                  : "Tick the attestation box to enable signing"
              }
            >
              {loading ? "…" : "Sign & Lock Chart"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
