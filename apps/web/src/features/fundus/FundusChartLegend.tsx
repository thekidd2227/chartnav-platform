import React from "react";
import type { FundusDrawingElement } from "./fundusTypes";

const FINDING_LABELS: Record<string, string> = {
  horseshoe_tear: "Horseshoe Tear",
  tear: "Tear",
  hole: "Hole",
  break: "Retinal Break",
  lattice: "Lattice Degeneration",
  detachment: "Retinal Detachment",
  rpe_change: "RPE Change",
  neovascularization: "Neovascularization",
  exudate: "Exudate",
  hemorrhage: "Hemorrhage",
  drusen: "Drusen",
};

interface Props {
  elements: FundusDrawingElement[];
}

export function FundusChartLegend({ elements }: Props) {
  if (elements.length === 0) return null;

  const unique = Array.from(new Map(elements.map((el) => [el.type, el])).values());

  return (
    <div style={{ marginTop: 12 }} data-testid="fundus-legend">
      <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: "#555" }}>Legend</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {unique.map((el) => (
          <div key={el.type} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                background: el.color,
                flexShrink: 0,
              }}
            />
            <span style={{ color: "#333" }}>{FINDING_LABELS[el.type] ?? el.label}</span>
          </div>
        ))}
      </div>
      <p
        data-testid="fundus-legend-attribution"
        style={{
          margin: "8px 0 0",
          fontSize: 11,
          color: "#718096",
          lineHeight: 1.5,
        }}
      >
        Drafted by ChartNav from clinician findings · provider review
        required · not photo interpretation.
      </p>
    </div>
  );
}
