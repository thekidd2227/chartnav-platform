// Phase 91 — Visit Mode Ribbon.
//
// Provider-driven visit mode chooser rendered above the Overview
// grid. The ribbon does NOT auto-classify the visit. Each mode is a
// closed-allowlist value; the resolved emphasis below is a UI hint
// only — no panel is ever hidden.

import React from "react";

import type { VisitMode } from "./workspaceStateTypes";
import { useWorkspaceState } from "./WorkspaceStateProvider";

interface Props {
  canEdit: boolean;
}

function modeStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: 11,
    padding: "4px 10px",
    borderRadius: 4,
    border: "1px solid #4a5568",
    background: active ? "#1c4532" : "#fff",
    color: active ? "#fff" : "#2d3748",
    cursor: active ? "default" : "pointer",
    fontWeight: 600,
  };
}

export function VisitModeRibbon({ canEdit }: Props) {
  const ctx = useWorkspaceState();
  if (!ctx) return null;
  const { state, loading, updating, setVisitMode } = ctx;

  if (loading && !state) {
    return (
      <div
        data-testid="visit-mode-ribbon-loading"
        style={{ fontSize: 11, color: "#4a5568", padding: 4 }}
      >
        Loading visit mode…
      </div>
    );
  }

  if (!state) return null;

  return (
    <div
      data-testid="visit-mode-ribbon"
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 8,
        padding: 8,
        marginBottom: 8,
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        fontSize: 12,
        color: "#2d3748",
      }}
    >
      <strong data-testid="visit-mode-ribbon-label">Visit mode:</strong>
      <span
        data-testid="visit-mode-ribbon-active"
        data-active-mode={state.visit_mode}
        style={{
          padding: "2px 8px",
          borderRadius: 999,
          background: "#edf2f7",
          fontSize: 11,
          fontWeight: 700,
        }}
      >
        {state.visit_mode_label}
      </span>
      {canEdit && (
        <div
          data-testid="visit-mode-ribbon-options"
          style={{ display: "flex", flexWrap: "wrap", gap: 6 }}
        >
          {state.supported_visit_modes.map((m) => (
            <button
              key={m.code}
              type="button"
              onClick={() => setVisitMode(m.code)}
              disabled={updating || state.visit_mode === m.code}
              data-testid={`visit-mode-ribbon-option-${m.code}`}
              style={modeStyle(state.visit_mode === m.code)}
            >
              {m.label}
            </button>
          ))}
        </div>
      )}
      <p
        data-testid="visit-mode-ribbon-disclosure"
        style={{
          width: "100%",
          margin: "4px 0 0",
          fontSize: 10,
          color: "#4a5568",
          lineHeight: 1.4,
        }}
      >
        Visit mode is provider-driven. ChartNav does not auto-classify
        the visit. Emphasis is a UI hint only — no panel is ever
        hidden by visit mode.
      </p>
    </div>
  );
}
