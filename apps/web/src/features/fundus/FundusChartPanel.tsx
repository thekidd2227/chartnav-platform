import React, { useEffect, useState } from "react";
import type { FundusChart, FundusChartListItem, Laterality } from "./fundusTypes";
import {
  listFundusCharts,
  generateFundusChart,
  getFundusChart,
} from "./fundusApi";
import { FundusChartEditor } from "./FundusChartEditor";

interface Props {
  encounterId: number;
}

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

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 700, padding: 16 }}>
      <h3 style={{ margin: "0 0 16px", fontSize: 16, color: "#2d3748" }}>Fundus Charts</h3>

      <div
        style={{
          background: "#f7fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 8,
          padding: 14,
          marginBottom: 16,
        }}
      >
        <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: "#4a5568" }}>
          Generate from findings
        </p>
        <select
          value={laterality}
          onChange={(e) => setLaterality(e.target.value as Laterality)}
          style={{
            fontSize: 13,
            padding: "4px 8px",
            borderRadius: 4,
            border: "1px solid #cbd5e0",
            marginBottom: 8,
          }}
        >
          <option value="OD">OD (Right)</option>
          <option value="OS">OS (Left)</option>
          <option value="OU">OU (Both)</option>
        </select>
        <textarea
          rows={4}
          value={findingsText}
          onChange={(e) => setFindingsText(e.target.value)}
          placeholder="e.g. horseshoe tear at 10:30 OD, lattice from 5 to 7 OS near ora"
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
        <button
          onClick={handleGenerate}
          disabled={loadingGen || !findingsText.trim()}
          style={{
            marginTop: 8,
            background: "#3182ce",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            padding: "6px 16px",
            fontSize: 13,
            cursor: findingsText.trim() ? "pointer" : "not-allowed",
            opacity: findingsText.trim() ? 1 : 0.6,
          }}
        >
          {loadingGen ? "Generating…" : "Generate Chart"}
        </button>
      </div>

      {error && <p style={{ color: "#c53030", fontSize: 12, marginBottom: 12 }}>{error}</p>}

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ width: 200, flexShrink: 0 }}>
          <p style={{ fontWeight: 600, fontSize: 12, color: "#718096", marginBottom: 8 }}>SAVED CHARTS</p>
          {loadingList ? (
            <p style={{ fontSize: 12, color: "#a0aec0" }}>Loading…</p>
          ) : charts.length === 0 ? (
            <p style={{ fontSize: 12, color: "#a0aec0" }}>No charts yet</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {charts.map((c) => (
                <li
                  key={c.id}
                  onClick={() => handleSelectChart(c.id)}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 6,
                    cursor: "pointer",
                    background: selectedChart?.id === c.id ? "#ebf8ff" : "transparent",
                    border:
                      selectedChart?.id === c.id
                        ? "1px solid #bee3f8"
                        : "1px solid transparent",
                    marginBottom: 4,
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#2d3748" }}>
                    {c.laterality} — #{c.id}
                  </div>
                  <div style={{ fontSize: 11, color: "#718096" }}>
                    {c.status} · {new Date(c.created_at).toLocaleDateString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={{ flex: 1 }}>
          {selectedChart ? (
            <FundusChartEditor
              encounterId={encounterId}
              chart={selectedChart}
              onUpdated={handleChartUpdated}
            />
          ) : (
            <div style={{ color: "#a0aec0", fontSize: 13, paddingTop: 16 }}>
              Select or generate a chart to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
