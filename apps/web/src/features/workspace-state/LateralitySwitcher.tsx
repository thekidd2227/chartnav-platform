// Phase 91 — Eye-Linked Laterality Switcher.
//
// Provider-driven OD / OS / OU / NA chooser rendered in the
// workspace header. Laterality-linked panels subscribe to this
// signal and re-filter on change; the switcher itself does NOT
// auto-select an eye.

import React from "react";

import type { ActiveLaterality } from "./workspaceStateTypes";
import { useWorkspaceState } from "./WorkspaceStateProvider";

interface Props {
  canEdit: boolean;
}

function lateralityStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: 11,
    padding: "4px 10px",
    borderRadius: 4,
    border: "1px solid #4a5568",
    background: active ? "#2c5282" : "#fff",
    color: active ? "#fff" : "#2d3748",
    cursor: active ? "default" : "pointer",
    fontWeight: 600,
  };
}

export function LateralitySwitcher({ canEdit }: Props) {
  const ctx = useWorkspaceState();
  if (!ctx) return null;
  const { state, updating, setActiveLaterality } = ctx;
  if (!state) return null;

  return (
    <div
      data-testid="laterality-switcher"
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
      <strong data-testid="laterality-switcher-label">Active eye:</strong>
      <span
        data-testid="laterality-switcher-active"
        data-active-laterality={state.active_laterality}
        style={{
          padding: "2px 8px",
          borderRadius: 999,
          background: "#edf2f7",
          fontSize: 11,
          fontWeight: 700,
        }}
      >
        {state.active_laterality_label}
      </span>
      {canEdit && (
        <div
          data-testid="laterality-switcher-options"
          style={{ display: "flex", gap: 6 }}
        >
          {state.supported_active_lateralities.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => setActiveLaterality(l.code)}
              disabled={
                updating || state.active_laterality === l.code
              }
              data-testid={`laterality-switcher-option-${l.code}`}
              style={lateralityStyle(state.active_laterality === l.code)}
            >
              {l.code}
            </button>
          ))}
        </div>
      )}
      <p
        data-testid="laterality-switcher-disclosure"
        style={{
          width: "100%",
          margin: "4px 0 0",
          fontSize: 10,
          color: "#4a5568",
          lineHeight: 1.4,
        }}
      >
        Active laterality is provider-driven. ChartNav does not
        autonomously select an eye. Laterality-linked panels re-filter
        on change; non-linked panels are unaffected.
      </p>
    </div>
  );
}
