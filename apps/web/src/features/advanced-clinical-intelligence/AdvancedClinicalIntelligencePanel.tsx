// Phase 92 — Advanced Clinical Intelligence panel.
//
// Read-only longitudinal projection layer that aggregates Phase 78-91
// services into four sections (Retina / Glaucoma / Cataract / FHIR
// readiness). The panel does not interpret images, does not diagnose,
// does not recommend treatment, does not submit anything to any
// external system. Per the Phase 91 unified workspace, it surfaces the
// active visit_mode + active_laterality and shows insufficient_data
// states with no synthesized values.

import React, { useCallback, useEffect, useState } from "react";

import { getAdvancedClinicalIntelligence } from "./advancedClinicalIntelligenceApi";
import type {
  AdvancedClinicalIntelligenceResponse,
  CataractLaneState,
  CataractSummary,
  FhirExportReadiness,
  GlaucomaSummary,
  RetinaLane,
  RetinaSummary,
} from "./advancedClinicalIntelligenceTypes";

interface Props {
  encounterId: number;
}

type Tone = "green" | "amber" | "red" | "neutral";

function toneStyle(tone: Tone): React.CSSProperties {
  if (tone === "green") return { background: "#c6f6d5", color: "#1c4532" };
  if (tone === "amber") return { background: "#fed7aa", color: "#7c2d12" };
  if (tone === "red") return { background: "#fed7d7", color: "#822727" };
  return { background: "#edf2f7", color: "#2d3748" };
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

function Chip({
  testid,
  tone,
  children,
}: {
  testid: string;
  tone: Tone;
  children: React.ReactNode;
}) {
  return (
    <span
      data-testid={testid}
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
      {children}
    </span>
  );
}

function InsufficientBanner({
  testid,
  message,
}: {
  testid: string;
  message: string;
}) {
  return (
    <div
      data-testid={testid}
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
      {message}
    </div>
  );
}

function SectionShell({
  testid,
  title,
  children,
}: {
  testid: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      data-testid={testid}
      style={{
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
      }}
    >
      <h4
        style={{
          margin: 0,
          marginBottom: 8,
          fontSize: 13,
          fontWeight: 700,
          color: "#2d3748",
        }}
      >
        {title}
      </h4>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Retina section
// ---------------------------------------------------------------------------

function RetinaLaneCard({
  laneCode,
  lane,
}: {
  laneCode: "OD" | "OS";
  lane: RetinaLane;
}) {
  const longForm = laneCode === "OD" ? "OD · Right Eye" : "OS · Left Eye";
  const tone: Tone = lane.insufficient_data
    ? "red"
    : lane.injection_count > 0
      ? "green"
      : "amber";
  return (
    <div
      data-testid={`aci-retina-lane-${laneCode}`}
      style={{
        flex: "1 1 240px",
        minWidth: 240,
        background: "#f7fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        padding: 10,
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
        <strong style={{ fontSize: 12, color: "#2d3748" }}>{longForm}</strong>
        <Chip testid={`aci-retina-${laneCode}-chip`} tone={tone}>
          {lane.insufficient_data ? "Insufficient data" : "Data on file"}
        </Chip>
      </div>
      {lane.insufficient_data ? (
        <InsufficientBanner
          testid={`aci-retina-${laneCode}-empty`}
          message={`No anti-VEGF injection history on file for ${laneCode}.`}
        />
      ) : (
        <div style={{ fontSize: 12, color: "#2d3748", lineHeight: 1.5 }}>
          <div data-testid={`aci-retina-${laneCode}-count`}>
            <strong>Injections:</strong> {lane.injection_count}
          </div>
          <div data-testid={`aci-retina-${laneCode}-latest`}>
            <strong>Latest injection:</strong> {fmtDate(lane.latest_injection_date)}
          </div>
          <div data-testid={`aci-retina-${laneCode}-interval`}>
            <strong>Latest interval:</strong>{" "}
            {lane.latest_interval_weeks !== null
              ? `${lane.latest_interval_weeks} wks`
              : "—"}
          </div>
          <div data-testid={`aci-retina-${laneCode}-auth`}>
            <strong>Latest authorization:</strong>{" "}
            {lane.latest_authorization_status ?? "—"}
          </div>
        </div>
      )}
    </div>
  );
}

function RetinaSection({ summary }: { summary: RetinaSummary }) {
  return (
    <SectionShell testid="aci-retina-section" title="Retina progression">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <RetinaLaneCard laneCode="OD" lane={summary.od} />
        <RetinaLaneCard laneCode="OS" lane={summary.os} />
      </div>
      <div
        data-testid="aci-retina-stage-history"
        style={{ marginTop: 10, fontSize: 12, color: "#2d3748" }}
      >
        <strong>Disease stage history:</strong> {summary.stage_history_count}{" "}
        record(s) ·{" "}
        <strong>Fundus charts:</strong> {summary.fundus_chart_count}
      </div>
      {summary.fundus_chart_latest && (
        <div
          data-testid="aci-retina-fundus-latest"
          style={{ marginTop: 4, fontSize: 11, color: "#4a5568" }}
        >
          Latest fundus chart · {summary.fundus_chart_latest.laterality ?? "—"} ·{" "}
          status {summary.fundus_chart_latest.status ?? "—"} ·{" "}
          signed {fmtDate(summary.fundus_chart_latest.signed_at)}
        </div>
      )}
      {summary.data_limitations.length > 0 && (
        <ul
          data-testid="aci-retina-limitations"
          style={{
            marginTop: 8,
            marginBottom: 0,
            paddingLeft: 18,
            fontSize: 11,
            color: "#4a5568",
          }}
        >
          {summary.data_limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
    </SectionShell>
  );
}

// ---------------------------------------------------------------------------
// Glaucoma section
// ---------------------------------------------------------------------------

function GlaucomaSection({ summary }: { summary: GlaucomaSummary }) {
  const tone: Tone = summary.insufficient_data ? "red" : "green";
  return (
    <SectionShell testid="aci-glaucoma-section" title="Glaucoma longitudinal">
      <div style={{ marginBottom: 6 }}>
        <Chip testid="aci-glaucoma-status-chip" tone={tone}>
          {summary.insufficient_data ? "Insufficient data" : "Data on file"}
        </Chip>
      </div>
      {summary.insufficient_data ? (
        <InsufficientBanner
          testid="aci-glaucoma-empty"
          message="No IOP / VF / OCT / POAG-stage data on file for this patient."
        />
      ) : (
        <div
          data-testid="aci-glaucoma-body"
          style={{ fontSize: 12, color: "#2d3748", lineHeight: 1.5 }}
        >
          <div data-testid="aci-glaucoma-stage-count">
            <strong>POAG stage history:</strong>{" "}
            {summary.poag_stage_history_count} record(s)
          </div>
          <div
            data-testid="aci-glaucoma-adherence"
            style={{ marginTop: 4, fontSize: 11, color: "#4a5568" }}
          >
            Adherence signals · meds{" "}
            {summary.adherence_signals.active_medication_count} · refill gaps{" "}
            {summary.adherence_signals.refill_gap_count} · active safety events{" "}
            {summary.adherence_signals.active_safety_event_count}
          </div>
        </div>
      )}
      {summary.data_limitations.length > 0 && (
        <ul
          data-testid="aci-glaucoma-limitations"
          style={{
            marginTop: 8,
            marginBottom: 0,
            paddingLeft: 18,
            fontSize: 11,
            color: "#4a5568",
          }}
        >
          {summary.data_limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
    </SectionShell>
  );
}

// ---------------------------------------------------------------------------
// Cataract section
// ---------------------------------------------------------------------------

function CataractLaneCard({
  laneCode,
  lane,
}: {
  laneCode: "OD" | "OS";
  lane: CataractLaneState;
}) {
  const longForm = laneCode === "OD" ? "OD · Right Eye" : "OS · Left Eye";
  const tone: Tone = lane.insufficient_data
    ? "red"
    : lane.record_count > 0
      ? "green"
      : "amber";
  return (
    <div
      data-testid={`aci-cataract-lane-${laneCode}`}
      style={{
        flex: "1 1 240px",
        minWidth: 240,
        background: "#f7fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        padding: 10,
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
        <strong style={{ fontSize: 12, color: "#2d3748" }}>{longForm}</strong>
        <Chip testid={`aci-cataract-${laneCode}-chip`} tone={tone}>
          {lane.insufficient_data ? "Insufficient data" : "Data on file"}
        </Chip>
      </div>
      {lane.insufficient_data ? (
        <InsufficientBanner
          testid={`aci-cataract-${laneCode}-empty`}
          message={`No cataract workflow records on file for ${laneCode}.`}
        />
      ) : (
        <div style={{ fontSize: 12, color: "#2d3748", lineHeight: 1.5 }}>
          <div data-testid={`aci-cataract-${laneCode}-count`}>
            <strong>Records:</strong> {lane.record_count}
          </div>
          <div data-testid={`aci-cataract-${laneCode}-planned`}>
            <strong>Planned surgery date:</strong>{" "}
            {fmtDate(lane.planned_surgery_date ?? null)}
          </div>
          <div data-testid={`aci-cataract-${laneCode}-consent`}>
            <strong>Consent status:</strong> {lane.consent_status ?? "—"}
          </div>
        </div>
      )}
    </div>
  );
}

function ConversionFunnelRow({
  label,
  value,
  testid,
}: {
  label: string;
  value: boolean;
  testid: string;
}) {
  const tone: Tone = value ? "green" : "amber";
  return (
    <div
      data-testid={testid}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "3px 0",
        borderTop: "1px solid #e2e8f0",
        fontSize: 11,
        color: "#2d3748",
      }}
    >
      <span style={{ flex: 1 }}>{label}</span>
      <Chip testid={`${testid}-chip`} tone={tone}>
        {value ? "Yes" : "Pending"}
      </Chip>
    </div>
  );
}

function CataractSection({ summary }: { summary: CataractSummary }) {
  return (
    <SectionShell testid="aci-cataract-section" title="Cataract conversion">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <CataractLaneCard laneCode="OD" lane={summary.od} />
        <CataractLaneCard laneCode="OS" lane={summary.os} />
      </div>
      <div style={{ marginTop: 10 }} data-testid="aci-cataract-funnel">
        <strong style={{ fontSize: 12, color: "#2d3748" }}>
          Conversion funnel (metadata only)
        </strong>
        <ConversionFunnelRow
          label="Any record"
          value={summary.conversion_funnel.any_record}
          testid="aci-cataract-funnel-any-record"
        />
        <ConversionFunnelRow
          label="Planned date present"
          value={summary.conversion_funnel.planned_date_present}
          testid="aci-cataract-funnel-planned-date"
        />
        <ConversionFunnelRow
          label="Biometry review complete"
          value={summary.conversion_funnel.biometry_review_complete}
          testid="aci-cataract-funnel-biometry"
        />
        <ConversionFunnelRow
          label="Consent signed"
          value={summary.conversion_funnel.consent_signed}
          testid="aci-cataract-funnel-consent"
        />
        <ConversionFunnelRow
          label="Post-op day 1 complete"
          value={summary.conversion_funnel.post_op_day_1_complete}
          testid="aci-cataract-funnel-postop1"
        />
      </div>
      {summary.data_limitations.length > 0 && (
        <ul
          data-testid="aci-cataract-limitations"
          style={{
            marginTop: 8,
            marginBottom: 0,
            paddingLeft: 18,
            fontSize: 11,
            color: "#4a5568",
          }}
        >
          {summary.data_limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
    </SectionShell>
  );
}

// ---------------------------------------------------------------------------
// FHIR section
// ---------------------------------------------------------------------------

function FhirSection({ readiness }: { readiness: FhirExportReadiness }) {
  const tone: Tone = readiness.packet_renderable ? "green" : "amber";
  return (
    <SectionShell
      testid="aci-fhir-section"
      title="FHIR / export readiness"
    >
      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          marginBottom: 8,
        }}
      >
        <Chip testid="aci-fhir-renderable-chip" tone={tone}>
          {readiness.packet_renderable
            ? "Packet renderable"
            : "Packet not renderable"}
        </Chip>
        <Chip testid="aci-fhir-submission-chip" tone="neutral">
          Submission: {readiness.submission_status.replace(/_/g, " ")}
        </Chip>
        <Chip testid="aci-fhir-transport-chip" tone="neutral">
          Transport: {readiness.transport}
        </Chip>
      </div>
      <div
        style={{
          fontSize: 12,
          color: "#2d3748",
          lineHeight: 1.5,
        }}
      >
        <div data-testid="aci-fhir-document-reference">
          <strong>Document reference:</strong>{" "}
          {readiness.document_reference_id ?? "—"}
        </div>
        {readiness.schema_version && (
          <div data-testid="aci-fhir-schema-version">
            <strong>Schema version:</strong> {readiness.schema_version}
          </div>
        )}
        {readiness.all_signed !== undefined && (
          <div data-testid="aci-fhir-all-signed">
            <strong>All signed:</strong>{" "}
            {readiness.all_signed ? "Yes" : "No"}
          </div>
        )}
      </div>
      <div
        data-testid="aci-fhir-extensions"
        style={{ marginTop: 6, fontSize: 11, color: "#4a5568" }}
      >
        <strong>Extensions present:</strong>{" "}
        {readiness.extensions_present.length > 0
          ? readiness.extensions_present.join(", ")
          : "None"}
      </div>
      {readiness.boundary && (
        <p
          data-testid="aci-fhir-boundary"
          style={{
            marginTop: 8,
            marginBottom: 0,
            padding: 8,
            background: "#f0fff4",
            border: "1px solid #9ae6b4",
            borderRadius: 6,
            fontSize: 11,
            color: "#1c4532",
            lineHeight: 1.5,
          }}
        >
          {readiness.boundary}
        </p>
      )}
    </SectionShell>
  );
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

export function AdvancedClinicalIntelligencePanel({ encounterId }: Props) {
  const [data, setData] = useState<AdvancedClinicalIntelligenceResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    getAdvancedClinicalIntelligence(encounterId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div
      data-testid="advanced-clinical-intelligence-panel"
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
          Advanced Clinical Intelligence
        </h3>
        <button
          type="button"
          onClick={fetchData}
          disabled={loading}
          data-testid="aci-refresh-btn"
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
        data-testid="aci-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-reviewed longitudinal projection from existing structured
        encounter data. ChartNav does not diagnose, does not interpret
        images, does not recommend treatment, and does not submit anything
        to any registry, payer, or external system. Every section is
        metadata only.
      </p>

      {error && (
        <p
          data-testid="aci-error"
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

      {loading && data === null && (
        <p
          data-testid="aci-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          <div
            data-testid="aci-context-chips"
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              marginBottom: 12,
            }}
          >
            <Chip testid="aci-encounter-type-chip" tone="neutral">
              Type: {data.encounter_type}
            </Chip>
            <Chip testid="aci-visit-mode-chip" tone="neutral">
              Visit mode: {data.visit_mode.replace(/_/g, " ")}
            </Chip>
            <Chip testid="aci-laterality-chip" tone="neutral">
              Laterality: {data.active_laterality}
            </Chip>
          </div>

          <RetinaSection summary={data.retina_summary} />
          <GlaucomaSection summary={data.glaucoma_summary} />
          <CataractSection summary={data.cataract_summary} />
          <FhirSection readiness={data.fhir_export_readiness} />

          {data.data_limitations.length > 0 && (
            <ul
              data-testid="aci-limitations"
              style={{
                marginTop: 8,
                paddingLeft: 18,
                fontSize: 11,
                color: "#4a5568",
              }}
            >
              {data.data_limitations.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          )}

          <div
            data-testid="aci-safety-boundaries"
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
            <strong>Safety boundaries</strong>
            <ul style={{ marginTop: 6, marginBottom: 0, paddingLeft: 18 }}>
              {data.safety_boundaries.map((b) => (
                <li key={b.key} data-testid={`aci-boundary-${b.key}`}>
                  {b.statement}
                </li>
              ))}
            </ul>
          </div>

          <p
            data-testid="aci-disclosure"
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
            {data.disclosure}
          </p>
        </>
      )}
    </div>
  );
}
