import React, { useEffect, useState } from "react";
import type {
  FundusChart,
  FundusChartListItem,
  FundusChartSourceType,
  FundusChartStatus,
  Laterality,
} from "./fundusTypes";
import {
  listFundusCharts,
  generateFundusChart,
  getFundusChart,
} from "./fundusApi";
import { FundusChartEditor, lateralityLong } from "./FundusChartEditor";

function statusLabel(status: FundusChartStatus): string {
  return status === "signed"
    ? "Signed · Locked"
    : status === "reviewed"
      ? "Reviewed"
      : "Draft";
}

function statusPillStyle(status: FundusChartStatus): React.CSSProperties {
  if (status === "signed") {
    return { background: "#c6f6d5", color: "#276749" };
  }
  if (status === "reviewed") {
    return { background: "#bee3f8", color: "#2a4a7f" };
  }
  return { background: "#fed7d7", color: "#9b2c2c" };
}

function sourceLabel(source: FundusChartSourceType): string {
  if (source === "ai_generated") return "AI-drafted";
  if (source === "manual") return "Manual";
  return "Imported";
}

interface Props {
  encounterId: number;
}

const DEMO_SAMPLES: ReadonlyArray<{ label: string; text: string; laterality: Laterality }> = [
  {
    label: "Horseshoe tear 10:30 OD",
    text: "horseshoe tear at 10:30 OD",
    laterality: "OD",
  },
  {
    label: "Lattice 5 to 7 OS",
    text: "lattice from 5 to 7 OS near ora",
    laterality: "OS",
  },
  {
    label: "Superotemporal detachment OD",
    text: "superotemporal detachment OD",
    laterality: "OD",
  },
  {
    label: "Laser scars temporal OS",
    text: "laser scars temporal OS",
    laterality: "OS",
  },
];

export function FundusChartPanel({ encounterId }: Props) {
  const [charts, setCharts] = useState<FundusChartListItem[]>([]);
  const [selectedChart, setSelectedChart] = useState<FundusChart | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingGen, setLoadingGen] = useState(false);
  const [findingsText, setFindingsText] = useState("");
  const [laterality, setLaterality] = useState<Laterality>("OD");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingList(true);
    listFundusCharts(encounterId)
      .then(setCharts)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingList(false));
  }, [encounterId]);

  async function handleGenerate() {
    if (!findingsText.trim()) return;
    setLoadingGen(true);
    setError(null);
    try {
      const res = await generateFundusChart(encounterId, {
        findings_text: findingsText,
        laterality,
      });
      const full = await getFundusChart(res.chart_id);
      setCharts((prev) => [
        {
          id: full.id,
          laterality: full.laterality,
          status: full.status,
          source_type: full.source_type,
          reviewed_at: null,
          signed_at: null,
          created_at: full.created_at,
          updated_at: full.updated_at,
        },
        ...prev,
      ]);
      setSelectedChart(full);
      setFindingsText("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoadingGen(false);
    }
  }

  async function handleSelectChart(id: number) {
    try {
      const chart = await getFundusChart(id);
      setSelectedChart(chart);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load chart");
    }
  }

  function handleChartUpdated(updated: FundusChart) {
    setSelectedChart(updated);
    setCharts((prev) =>
      prev.map((c) =>
        c.id === updated.id
          ? {
              ...c,
              status: updated.status,
              signed_at: updated.signed_at,
              reviewed_at: updated.reviewed_at,
            }
          : c,
      ),
    );
  }

  function applySample(sample: typeof DEMO_SAMPLES[number]) {
    setFindingsText(sample.text);
    setLaterality(sample.laterality);
  }

  return (
    <div
      style={{ fontFamily: "sans-serif", padding: 16 }}
      data-testid="fundus-chart-panel"
    >
      <div style={{ marginBottom: 12 }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#2d3748" }}>
          Fundus Charts
        </h3>
        <p
          data-testid="fundus-safety-banner"
          style={{
            margin: 0,
            fontSize: 12,
            color: "#4a5568",
            lineHeight: 1.5,
          }}
        >
          Draft from clinician-entered findings. Provider review required.
          Not image interpretation. Does not diagnose.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          alignItems: "flex-start",
        }}
      >
        <div style={{ flex: "1 1 320px", minWidth: 280 }}>
          <div
            style={{
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              padding: 14,
            }}
          >
            <p
              style={{
                fontWeight: 600,
                fontSize: 13,
                marginBottom: 8,
                color: "#4a5568",
              }}
            >
              Enter clinician findings
            </p>

            <div style={{ marginBottom: 10 }}>
              <label
                htmlFor="fundus-laterality"
                style={{
                  display: "block",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#718096",
                  marginBottom: 4,
                  textTransform: "uppercase",
                  letterSpacing: 0.4,
                }}
              >
                Eye (Laterality)
              </label>
              <div
                role="radiogroup"
                aria-label="Laterality"
                style={{ display: "flex", gap: 6 }}
                data-testid="fundus-laterality-group"
              >
                {(["OD", "OS", "OU"] as const).map((opt) => {
                  const active = laterality === opt;
                  const label =
                    opt === "OD"
                      ? "OD · Right"
                      : opt === "OS"
                        ? "OS · Left"
                        : "OU · Both";
                  return (
                    <button
                      key={opt}
                      type="button"
                      role="radio"
                      aria-checked={active}
                      onClick={() => setLaterality(opt)}
                      data-testid={`fundus-laterality-${opt}`}
                      style={{
                        flex: 1,
                        padding: "6px 8px",
                        fontSize: 12,
                        fontWeight: 600,
                        border: active
                          ? "1px solid #3182ce"
                          : "1px solid #cbd5e0",
                        background: active ? "#ebf8ff" : "#fff",
                        color: active ? "#2a4a7f" : "#4a5568",
                        borderRadius: 6,
                        cursor: "pointer",
                      }}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            <label
              htmlFor="fundus-findings-text"
              style={{
                display: "block",
                fontSize: 11,
                fontWeight: 600,
                color: "#718096",
                marginBottom: 4,
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Findings
            </label>
            <textarea
              id="fundus-findings-text"
              rows={4}
              value={findingsText}
              onChange={(e) => setFindingsText(e.target.value)}
              placeholder="e.g. horseshoe tear at 10:30 OD"
              data-testid="fundus-findings-text"
              style={{
                display: "block",
                width: "100%",
                fontSize: 13,
                padding: 8,
                borderRadius: 4,
                border: "1px solid #cbd5e0",
                boxSizing: "border-box",
              }}
            />

            <div style={{ marginTop: 10 }}>
              <p
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#718096",
                  margin: "0 0 6px",
                  textTransform: "uppercase",
                  letterSpacing: 0.4,
                }}
              >
                Demo samples (fake data)
              </p>
              <div
                style={{ display: "flex", flexWrap: "wrap", gap: 6 }}
                data-testid="fundus-sample-chips"
              >
                {DEMO_SAMPLES.map((s) => (
                  <button
                    key={s.label}
                    type="button"
                    onClick={() => applySample(s)}
                    data-testid={`fundus-sample-${s.laterality}`}
                    style={{
                      fontSize: 11,
                      padding: "4px 8px",
                      borderRadius: 999,
                      border: "1px solid #cbd5e0",
                      background: "#fff",
                      color: "#4a5568",
                      cursor: "pointer",
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={loadingGen || !findingsText.trim()}
              data-testid="fundus-generate-btn"
              style={{
                marginTop: 12,
                background: "#3182ce",
                color: "#fff",
                border: "none",
                borderRadius: 6,
                padding: "8px 16px",
                fontSize: 13,
                fontWeight: 600,
                cursor: findingsText.trim() ? "pointer" : "not-allowed",
                opacity: findingsText.trim() ? 1 : 0.6,
              }}
            >
              {loadingGen ? "Generating…" : "Generate Chart"}
            </button>
          </div>

          <div style={{ marginTop: 16 }}>
            <p
              style={{
                fontWeight: 600,
                fontSize: 11,
                color: "#718096",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Saved charts
            </p>
            {loadingList ? (
              <p
                style={{ fontSize: 12, color: "#a0aec0" }}
                data-testid="fundus-list-loading"
              >
                Loading…
              </p>
            ) : charts.length === 0 ? (
              <p
                style={{ fontSize: 12, color: "#a0aec0" }}
                data-testid="fundus-list-empty"
              >
                No charts yet. Enter findings such as "horseshoe tear at
                10:30 OD" to generate one.
              </p>
            ) : (
              <ul
                style={{ listStyle: "none", padding: 0, margin: 0 }}
                data-testid="fundus-list"
              >
                {charts.map((c) => (
                  <li
                    key={c.id}
                    onClick={() => handleSelectChart(c.id)}
                    data-testid={`fundus-list-item-${c.id}`}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 6,
                      cursor: "pointer",
                      background:
                        selectedChart?.id === c.id
                          ? "#ebf8ff"
                          : "transparent",
                      border:
                        selectedChart?.id === c.id
                          ? "1px solid #bee3f8"
                          : "1px solid transparent",
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "baseline",
                        justifyContent: "space-between",
                        gap: 6,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#2d3748",
                        }}
                      >
                        {lateralityLong(c.laterality)}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          color: "#a0aec0",
                        }}
                      >
                        #{c.id}
                      </span>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        alignItems: "center",
                        gap: 6,
                        marginTop: 4,
                      }}
                    >
                      <span
                        data-testid={`fundus-list-status-${c.id}`}
                        style={{
                          ...statusPillStyle(c.status),
                          padding: "1px 6px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          letterSpacing: 0.3,
                          textTransform: "uppercase",
                        }}
                      >
                        {statusLabel(c.status)}
                      </span>
                      <span
                        data-testid={`fundus-list-source-${c.id}`}
                        style={{
                          fontSize: 10,
                          color: "#4a5568",
                          background: "#edf2f7",
                          padding: "1px 6px",
                          borderRadius: 4,
                          fontWeight: 600,
                          letterSpacing: 0.3,
                          textTransform: "uppercase",
                        }}
                      >
                        {sourceLabel(c.source_type)}
                      </span>
                      <time
                        dateTime={c.created_at}
                        title={new Date(c.created_at).toLocaleString()}
                        style={{ fontSize: 11, color: "#718096" }}
                      >
                        {new Date(c.created_at).toLocaleDateString()}
                      </time>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div
          style={{ flex: "2 1 380px", minWidth: 320 }}
          data-testid="fundus-preview-column"
        >
          {error && (
            <p
              data-testid="fundus-error"
              style={{
                color: "#c53030",
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
          {selectedChart ? (
            <FundusChartEditor
              encounterId={encounterId}
              chart={selectedChart}
              onUpdated={handleChartUpdated}
            />
          ) : (
            <div
              data-testid="fundus-preview-empty"
              style={{
                color: "#718096",
                fontSize: 13,
                padding: 24,
                border: "1px dashed #cbd5e0",
                borderRadius: 8,
                textAlign: "center",
                background: "#fafbfc",
              }}
            >
              <p style={{ margin: "0 0 6px", fontWeight: 600 }}>
                No chart selected
              </p>
              <p style={{ margin: 0, fontSize: 12 }}>
                Enter clinician findings on the left, or pick a saved chart,
                to preview here. ChartNav drafts a structured retinal diagram
                — the provider still reviews and signs before the chart is
                final.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
