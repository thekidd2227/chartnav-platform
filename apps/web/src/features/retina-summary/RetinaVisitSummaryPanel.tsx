// Phase 76 — Retina Visit Summary panel.
//
// Buyer-visible read-only surface that aggregates Vitals, VisitDraft,
// and Fundus state for one encounter, plus a metadata-only evidence
// timeline pulled from the new
// GET /api/v1/encounters/{id}/retina-visit-summary endpoint.
//
// The panel never displays clinical free text — the aggregator only
// emits metadata (artifact_type, event_type, actor name + role,
// timestamp, ref id, optional counts) per the Phase 73 metadata-only
// audit invariant. The audit-disclosure line from the API response is
// rendered verbatim so the buyer hears the same boundary statement
// the backend enforces.

import React, { useCallback, useEffect, useState } from "react";
import { getRetinaVisitSummary } from "./retinaSummaryApi";
import type {
  RetinaArtifactType,
  RetinaSummaryArtifactSection,
  RetinaSummaryBlocker,
  RetinaSummaryEvent,
  RetinaSummaryRoleCapabilities,
  RetinaVisitSummary,
} from "./retinaSummaryTypes";

interface Props {
  encounterId: number;
}

function statusPillStyle(status: string | null): React.CSSProperties {
  if (status === "signed" || status === "finalized") {
    return { background: "#c6f6d5", color: "#276749" };
  }
  if (status === "reviewed") {
    return { background: "#bee3f8", color: "#2a4a7f" };
  }
  if (status === "entered" || status === "ready_for_review") {
    return { background: "#fed7aa", color: "#7c2d12" };
  }
  if (status === null) {
    return { background: "#edf2f7", color: "#a0aec0" };
  }
  return { background: "#fed7d7", color: "#9b2c2c" };
}

function statusLabel(status: string | null): string {
  if (status === null) return "None yet";
  if (status === "signed" || status === "finalized") return "Signed · Locked";
  if (status === "reviewed") return "Reviewed";
  if (status === "entered") return "Entered";
  if (status === "ready_for_review") return "Ready for Review";
  if (status === "draft") return "Draft";
  return status;
}

function artifactLabel(t: RetinaArtifactType): string {
  if (t === "vitals_workup") return "Vitals";
  if (t === "visit_draft") return "VisitDraft";
  return "Fundus";
}

function eventLabel(t: RetinaSummaryEvent["event_type"]): string {
  if (t === "created") return "Created";
  if (t === "reviewed") return "Reviewed";
  return "Signed";
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ArtifactCard({
  title,
  section,
  signedKey,
}: {
  title: string;
  section: RetinaSummaryArtifactSection;
  signedKey: "latest_signed_at" | "latest_finalized_at";
}) {
  const status = section.latest_status;
  const signedAt = section[signedKey];
  return (
    <div
      data-testid={`retina-summary-card-${title.toLowerCase()}`}
      style={{
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: 12,
        flex: "1 1 200px",
        minWidth: 180,
      }}
    >
      <p
        style={{
          margin: "0 0 6px",
          fontSize: 11,
          fontWeight: 700,
          color: "#4a5568",
          textTransform: "uppercase",
          letterSpacing: 0.4,
        }}
      >
        {title}
      </p>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 6,
        }}
      >
        <span
          data-testid={`retina-summary-card-${title.toLowerCase()}-status`}
          style={{
            ...statusPillStyle(status),
            padding: "2px 8px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 0.3,
            textTransform: "uppercase",
          }}
        >
          {statusLabel(status)}
        </span>
        <span style={{ fontSize: 11, color: "#718096" }}>
          {section.count} total
        </span>
      </div>
      {section.latest_id !== null && (
        <p style={{ margin: "0 0 2px", fontSize: 12, color: "#2d3748" }}>
          Latest: #{section.latest_id}
        </p>
      )}
      {signedAt && (
        <p style={{ margin: 0, fontSize: 11, color: "#22543d" }}>
          Signed {fmtTime(signedAt)}
        </p>
      )}
      {!signedAt && section.latest_reviewed_at && (
        <p style={{ margin: 0, fontSize: 11, color: "#2a4a7f" }}>
          Reviewed {fmtTime(section.latest_reviewed_at)}
        </p>
      )}
      {section.latest_warning_count !== undefined && (
        <p style={{ margin: "2px 0 0", fontSize: 11, color: "#744210" }}>
          {section.latest_warning_count} warning
          {section.latest_warning_count === 1 ? "" : "s"}
        </p>
      )}
      {section.latest_element_count !== undefined && (
        <p style={{ margin: "2px 0 0", fontSize: 11, color: "#4a5568" }}>
          {section.latest_element_count} drafted element
          {section.latest_element_count === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );
}

function Blockers({ blockers }: { blockers: RetinaSummaryBlocker[] }) {
  if (blockers.length === 0) {
    return (
      <div
        data-testid="retina-summary-blockers-empty"
        style={{
          marginTop: 12,
          padding: 10,
          background: "#f0fff4",
          border: "1px solid #9ae6b4",
          borderRadius: 6,
          fontSize: 12,
          color: "#276749",
        }}
      >
        All clinical artifacts are signed and locked for this visit.
      </div>
    );
  }
  return (
    <div
      data-testid="retina-summary-blockers"
      style={{
        marginTop: 12,
        padding: 10,
        background: "#fffbf0",
        border: "1px solid #f6d860",
        borderRadius: 6,
      }}
    >
      <p
        style={{
          margin: "0 0 6px",
          fontSize: 11,
          fontWeight: 700,
          color: "#744210",
          textTransform: "uppercase",
          letterSpacing: 0.4,
        }}
      >
        Pending provider action ({blockers.length})
      </p>
      <ul style={{ margin: 0, paddingLeft: 16 }}>
        {blockers.map((b) => (
          <li
            key={b.kind}
            data-testid={`retina-summary-blocker-${b.kind}`}
            style={{ fontSize: 12, color: "#744210" }}
          >
            {b.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RoleCard({
  caps,
}: {
  caps: RetinaSummaryRoleCapabilities;
}) {
  return (
    <div
      data-testid="retina-summary-role"
      style={{
        marginTop: 12,
        padding: 10,
        background: "#ebf8ff",
        border: "1px solid #bee3f8",
        borderRadius: 6,
      }}
    >
      <p
        style={{
          margin: "0 0 4px",
          fontSize: 11,
          fontWeight: 700,
          color: "#2a4a7f",
          textTransform: "uppercase",
          letterSpacing: 0.4,
        }}
      >
        Signed in as {caps.role}
      </p>
      <p
        style={{
          margin: 0,
          fontSize: 12,
          color: "#2a4a7f",
          lineHeight: 1.5,
        }}
        data-testid="retina-summary-role-explainer"
      >
        {caps.explainer}
      </p>
    </div>
  );
}

function Timeline({ events }: { events: RetinaSummaryEvent[] }) {
  if (events.length === 0) {
    return (
      <p
        data-testid="retina-summary-timeline-empty"
        style={{
          marginTop: 12,
          padding: 10,
          fontSize: 12,
          color: "#718096",
          textAlign: "center",
          background: "#fafbfc",
          border: "1px dashed #cbd5e0",
          borderRadius: 6,
        }}
      >
        No metadata-only audit events recorded for this visit yet.
      </p>
    );
  }
  return (
    <ul
      data-testid="retina-summary-timeline"
      style={{
        listStyle: "none",
        padding: 0,
        margin: "8px 0 0",
      }}
    >
      {events.map((e, i) => (
        <li
          key={`${e.artifact_type}-${e.ref_id}-${e.event_type}-${i}`}
          data-testid={`retina-summary-event-${i}`}
          style={{
            padding: "6px 10px",
            borderLeft: "3px solid #cbd5e0",
            margin: "0 0 4px",
            background: "#f7fafc",
            fontSize: 12,
            color: "#2d3748",
          }}
        >
          <span style={{ fontWeight: 600 }}>
            {artifactLabel(e.artifact_type)}
          </span>{" "}
          · {eventLabel(e.event_type)} · #{e.ref_id}
          {e.actor_display_name && (
            <>
              {" "}
              ·{" "}
              <span data-testid={`retina-summary-event-${i}-actor`}>
                {e.actor_display_name}
                {e.actor_role && ` (${e.actor_role})`}
              </span>
            </>
          )}
          {e.laterality && (
            <>
              {" "}
              · <span>{e.laterality}</span>
            </>
          )}
          <div style={{ fontSize: 11, color: "#718096", marginTop: 2 }}>
            {fmtTime(e.timestamp)}
            {e.warning_count !== undefined &&
              ` · ${e.warning_count} warning${e.warning_count === 1 ? "" : "s"}`}
            {e.element_count !== undefined &&
              ` · ${e.element_count} element${e.element_count === 1 ? "" : "s"}`}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function RetinaVisitSummaryPanel({ encounterId }: Props) {
  const [summary, setSummary] = useState<RetinaVisitSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(() => {
    setLoading(true);
    setError(null);
    getRetinaVisitSummary(encounterId)
      .then(setSummary)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return (
    <div
      data-testid="retina-visit-summary-panel"
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
          Retina Visit Summary
        </h3>
        <button
          type="button"
          onClick={fetchSummary}
          disabled={loading}
          data-testid="retina-summary-refresh-btn"
          style={{
            fontSize: 11,
            padding: "4px 10px",
            borderRadius: 4,
            border: "1px solid #cbd5e0",
            background: "#fff",
            color: "#4a5568",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p
        data-testid="retina-summary-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Cross-artifact view of clinician-entered intake, drafted note,
        and fundus drawing for this visit. Read-only. Provider review
        and signature drive every status pill below.
      </p>

      {error && (
        <p
          data-testid="retina-summary-error"
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

      {loading && !summary && (
        <p
          data-testid="retina-summary-loading"
          style={{ fontSize: 12, color: "#a0aec0" }}
        >
          Loading…
        </p>
      )}

      {summary && (
        <>
          <div
            data-testid="retina-summary-encounter-meta"
            style={{
              marginBottom: 12,
              fontSize: 12,
              color: "#4a5568",
            }}
          >
            <strong style={{ color: "#2d3748" }}>
              {summary.patient_name ?? "Unknown patient"}
            </strong>{" "}
            ({summary.patient_identifier ?? "—"}) · encounter #
            {summary.encounter_id} · status{" "}
            <span
              style={{
                ...statusPillStyle(summary.encounter_status),
                padding: "1px 6px",
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: 0.3,
              }}
            >
              {summary.encounter_status}
            </span>
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            <ArtifactCard
              title="Vitals"
              section={summary.vitals}
              signedKey="latest_signed_at"
            />
            <ArtifactCard
              title="VisitDraft"
              section={summary.visit_draft}
              signedKey="latest_finalized_at"
            />
            <ArtifactCard
              title="Fundus"
              section={summary.fundus}
              signedKey="latest_signed_at"
            />
          </div>

          <Blockers blockers={summary.blockers} />
          <RoleCard caps={summary.role_capabilities} />

          <div style={{ marginTop: 16 }}>
            <p
              style={{
                margin: "0 0 4px",
                fontSize: 11,
                fontWeight: 700,
                color: "#4a5568",
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Evidence timeline (metadata-only)
            </p>
            <Timeline events={summary.evidence_timeline} />
          </div>

          <p
            data-testid="retina-summary-audit-disclosure"
            style={{
              marginTop: 12,
              fontSize: 11,
              color: "#38a169",
              lineHeight: 1.5,
            }}
          >
            {summary.audit_disclosure}
          </p>
        </>
      )}
    </div>
  );
}
