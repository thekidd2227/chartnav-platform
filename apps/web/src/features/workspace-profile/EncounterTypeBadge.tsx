// Phase 86 — Encounter Type Badge.
//
// Compact chip rendered above the Overview tab's panel grid. Shows
// the resolved profile and exposes a typed select so admin /
// clinician can change the encounter's subspecialty type. The
// component does not infer subspecialty — every value here is
// provider-driven.

import React from "react";

import type { EncounterType } from "./workspaceProfileTypes";
import type { WorkspaceProfileState } from "./WorkspaceProfileResolver";

interface Props {
  state: WorkspaceProfileState;
  canEdit: boolean;
}

function toneFor(typ: EncounterType): React.CSSProperties {
  switch (typ) {
    case "retina":
      return { background: "#fed7d7", color: "#742a2a" };
    case "glaucoma":
      return { background: "#bee3f8", color: "#2c5282" };
    case "cataract":
      return { background: "#fefcbf", color: "#744210" };
    default:
      return { background: "#edf2f7", color: "#2d3748" };
  }
}

export function EncounterTypeBadge({ state, canEdit }: Props) {
  const { profile, loading, error, updating, setEncounterType } = state;

  if (loading && !profile) {
    return (
      <div
        data-testid="encounter-type-badge-loading"
        style={{ fontSize: 11, color: "#4a5568", padding: 4 }}
      >
        Resolving workspace profile…
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div
        data-testid="encounter-type-badge-error"
        style={{
          fontSize: 11,
          color: "#822727",
          background: "#fff5f5",
          border: "1px solid #fed7d7",
          padding: 6,
          borderRadius: 4,
        }}
      >
        Workspace profile error: {error}
      </div>
    );
  }

  if (!profile) return null;

  const tone = toneFor(profile.encounter_type);

  return (
    <div
      data-testid="encounter-type-badge"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: 8,
        marginBottom: 8,
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        fontSize: 12,
        color: "#2d3748",
        flexWrap: "wrap",
      }}
    >
      <span
        data-testid="encounter-type-badge-chip"
        data-encounter-type={profile.encounter_type}
        style={{
          ...tone,
          padding: "2px 10px",
          borderRadius: 999,
          fontSize: 11,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 0.3,
        }}
      >
        {profile.encounter_type_label} workspace
      </span>
      <span
        data-testid="encounter-type-badge-summary"
        style={{ fontSize: 11, color: "#4a5568" }}
      >
        {profile.profile.prioritized_panels.length} prioritized ·{" "}
        {profile.profile.collapsed_panels.length} collapsed
      </span>
      {canEdit && (
        <label
          style={{
            marginLeft: "auto",
            fontSize: 11,
            color: "#4a5568",
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          Set type
          <select
            value={profile.encounter_type}
            onChange={(e) =>
              setEncounterType(e.target.value as EncounterType)
            }
            disabled={updating}
            data-testid="encounter-type-select"
            style={{ fontSize: 11 }}
          >
            {profile.supported_encounter_types.map((t) => (
              <option
                key={t.code}
                value={t.code}
                data-testid={`encounter-type-option-${t.code}`}
              >
                {t.label}
              </option>
            ))}
          </select>
        </label>
      )}
      <p
        data-testid="encounter-type-badge-disclosure"
        style={{
          width: "100%",
          margin: "4px 0 0",
          fontSize: 10,
          color: "#4a5568",
          lineHeight: 1.4,
        }}
      >
        Provider-driven workspace profile. ChartNav does not autonomously
        classify the encounter, does not infer subspecialty from clinical
        data, and does not hide data — lower-priority panels may be
        collapsed but remain available.
      </p>
    </div>
  );
}
