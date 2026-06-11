// Phase 90 — Ophthalmic Medication Safety & Adherence Panel.
//
// Provider-reviewed medication safety workflow support. ChartNav does
// NOT prescribe, does NOT recommend a medication change, does NOT
// diagnose, does NOT recommend treatment or surgery, and does NOT
// submit to pharmacies, payers, or EHRs.

import React, { useCallback, useEffect, useState } from "react";

import {
  getMedicationSafety,
  postAcknowledgeEvent,
  postOphthalmicMedication,
} from "./medicationSafetyApi";
import type {
  EventSeverity,
  EventStatus,
  MedicationSafetyEvent,
  MedicationSafetyResponse,
  OphthalmicMedicationRecord,
  PreservativeType,
} from "./medicationSafetyTypes";

interface Props {
  patientId: number;
  encounterId: number;
}

type Tone = "green" | "amber" | "neutral" | "red";

function toneStyle(tone: Tone): React.CSSProperties {
  if (tone === "green") return { background: "#c6f6d5", color: "#1c4532" };
  if (tone === "amber") return { background: "#fed7aa", color: "#7c2d12" };
  if (tone === "red") return { background: "#fed7d7", color: "#822727" };
  return { background: "#edf2f7", color: "#2d3748" };
}

function pill(
  text: string,
  tone: Tone,
  testid?: string,
): React.ReactElement {
  return (
    <span
      data-testid={testid}
      style={{
        ...toneStyle(tone),
        padding: "1px 8px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.3,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </span>
  );
}

function severityTone(severity: EventSeverity, status: EventStatus): Tone {
  if (status === "resolved") return "neutral";
  if (status === "acknowledged") return "green";
  if (severity === "hard_stop") return "red";
  if (severity === "alert") return "red";
  return "amber";
}

function severityLabel(severity: EventSeverity, status: EventStatus): string {
  if (status === "acknowledged") return "Acknowledged";
  if (status === "resolved") return "Resolved";
  if (severity === "hard_stop") return "Hard stop (reserved)";
  if (severity === "alert") return "Alert (reserved)";
  return "Advisory";
}

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function MedicationSafetyPanel({ patientId, encounterId }: Props) {
  const [data, setData] = useState<MedicationSafetyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acking, setAcking] = useState<number | null>(null);
  const [ackError, setAckError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Add-medication form
  const [medName, setMedName] = useState("");
  const [medClass, setMedClass] = useState("pgf2_analog");
  const [medPreservative, setMedPreservative] =
    useState<PreservativeType>("BAK");
  const [medDose, setMedDose] = useState<number>(1);
  const [medLastFill, setMedLastFill] = useState("");
  const [medDaysSupply, setMedDaysSupply] = useState<number>(30);

  const fetchPanel = useCallback(() => {
    setLoading(true);
    setError(null);
    getMedicationSafety(patientId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  useEffect(() => {
    fetchPanel();
  }, [fetchPanel]);

  const onAcknowledge = useCallback(
    async (event: MedicationSafetyEvent) => {
      setAckError(null);
      setAcking(event.id);
      try {
        await postAcknowledgeEvent(event.id);
        fetchPanel();
      } catch (err) {
        setAckError(
          err instanceof Error ? err.message : "Acknowledge failed",
        );
      } finally {
        setAcking(null);
      }
    },
    [fetchPanel],
  );

  const onSubmitMedication = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);
      setSubmitting(true);
      try {
        await postOphthalmicMedication(encounterId, {
          medication_name: medName.trim(),
          medication_class: medClass,
          route: "drops",
          laterality: "OU",
          dose_per_day: medDose,
          preservative_type: medPreservative,
          last_fill_date: medLastFill || null,
          days_supply: medDaysSupply || null,
        });
        setMedName("");
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Record medication failed",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [
      encounterId,
      fetchPanel,
      medClass,
      medDaysSupply,
      medDose,
      medLastFill,
      medName,
      medPreservative,
    ],
  );

  const renderMedication = (med: OphthalmicMedicationRecord) => (
    <li
      key={med.id}
      data-testid={`medication-safety-medication-row-${med.id}`}
      style={{
        padding: 10,
        background: med.active ? "#fff" : "#f7fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        marginBottom: 6,
        fontSize: 12,
        color: "#2d3748",
        lineHeight: 1.5,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 8,
          marginBottom: 4,
        }}
      >
        <strong
          data-testid={`medication-safety-medication-name-${med.id}`}
        >
          {med.medication_name}
        </strong>
        <span
          data-testid={`medication-safety-medication-laterality-${med.id}`}
          style={{ fontSize: 11, color: "#4a5568" }}
        >
          {med.laterality}
        </span>
      </div>
      <div>
        <strong>Class:</strong> {med.medication_class} ·{" "}
        <strong>Preservative:</strong>{" "}
        <span
          data-testid={`medication-safety-medication-preservative-${med.id}`}
        >
          {med.preservative_type}
        </span>
      </div>
      <div>
        <strong>Dose/day:</strong> {med.dose_per_day} ·{" "}
        <strong>Days supply:</strong> {med.days_supply ?? "—"} ·{" "}
        <strong>Last fill:</strong> {med.last_fill_date ?? "—"}
      </div>
      {med.refill_gap_days !== null && med.refill_gap_days > 0 && (
        <div
          data-testid={`medication-safety-refill-gap-${med.id}`}
          style={{ color: "#7c2d12" }}
        >
          <strong>Refill gap:</strong> {med.refill_gap_days} day(s)
        </div>
      )}
      <div style={{ fontSize: 11, color: "#4a5568" }}>
        Reviewed:{" "}
        <span data-testid={`medication-safety-medication-reviewed-${med.id}`}>
          {med.reviewed_at ? fmt(med.reviewed_at) : "not recorded"}
        </span>
      </div>
    </li>
  );

  const renderEvent = (event: MedicationSafetyEvent) => (
    <li
      key={event.id}
      data-testid={`medication-safety-event-row-${event.id}`}
      style={{
        padding: 10,
        background:
          event.status === "active"
            ? "#fffaf0"
            : event.status === "acknowledged"
            ? "#f0fff4"
            : "#f7fafc",
        border: "1px solid #e2e8f0",
        borderRadius: 6,
        marginBottom: 6,
        fontSize: 12,
        color: "#2d3748",
        lineHeight: 1.5,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 8,
          marginBottom: 4,
        }}
      >
        <strong>{event.rule_key}</strong>
        {pill(
          severityLabel(event.severity, event.status),
          severityTone(event.severity, event.status),
          `medication-safety-event-severity-${event.id}`,
        )}
      </div>
      <div data-testid={`medication-safety-event-message-${event.id}`}>
        {event.message}
      </div>
      {event.acknowledged_at && (
        <div
          data-testid={`medication-safety-event-acker-${event.id}`}
          style={{ fontSize: 11, color: "#4a5568" }}
        >
          Acknowledged by {event.acknowledged_by_display_name ?? "Unknown"}
          {event.acknowledged_by_role && ` (${event.acknowledged_by_role})`} at{" "}
          {fmt(event.acknowledged_at)}
        </div>
      )}
      {event.status === "active" && (
        <button
          type="button"
          onClick={() => onAcknowledge(event)}
          disabled={acking === event.id}
          data-testid={`medication-safety-event-ack-btn-${event.id}`}
          style={{
            marginTop: 6,
            fontSize: 11,
            padding: "3px 8px",
            borderRadius: 4,
            border: "1px solid #4a5568",
            background: acking === event.id ? "#cbd5e0" : "#1c4532",
            color: "#fff",
            cursor: acking === event.id ? "wait" : "pointer",
          }}
        >
          {acking === event.id ? "Acknowledging…" : "Mark reviewed"}
        </button>
      )}
    </li>
  );

  return (
    <div
      data-testid="medication-safety-panel"
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
          Ophthalmic Medication Safety &amp; Adherence
        </h3>
        <button
          type="button"
          onClick={fetchPanel}
          disabled={loading}
          data-testid="medication-safety-refresh-btn"
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
        data-testid="medication-safety-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-reviewed medication safety support. ChartNav does not
        prescribe, does not recommend a medication change, and does not
        submit to pharmacies, payers, or EHRs. Signals are generated
        from structured medication data.
      </p>

      {error && (
        <p
          data-testid="medication-safety-error"
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
          data-testid="medication-safety-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          {data.internal_demo_rules_present && (
            <p
              data-testid="medication-safety-demo-caution"
              style={{
                margin: "0 0 12px",
                padding: 10,
                background: "#fffaf0",
                border: "1px solid #f6ad55",
                borderRadius: 6,
                fontSize: 12,
                color: "#7c2d12",
                lineHeight: 1.5,
              }}
            >
              <strong>Internal demo rules present.</strong> The medication
              safety rules driving these advisories are placeholder rules
              and have NOT been verified for clinical use. Verify with a
              qualified operator before any real-program use.
            </p>
          )}

          <div
            data-testid="medication-safety-signals"
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginBottom: 10,
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <div
              data-testid="medication-safety-signal-active-meds"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Active medications:</strong>{" "}
              {data.signals.active_medication_count}
            </div>
            <div
              data-testid="medication-safety-signal-preservative-burden"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Preservative burden:</strong>{" "}
              {data.signals.preservative_burden_count}
            </div>
            <div
              data-testid="medication-safety-signal-refill-gaps"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Refill gaps:</strong> {data.signals.refill_gap_count}
            </div>
            <div
              data-testid="medication-safety-signal-active-events"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Active advisories:</strong>{" "}
              {data.counts.active_events}
            </div>
          </div>

          <h4 style={{ margin: "12px 0 6px", fontSize: 13, color: "#2d3748" }}>
            Safety events
          </h4>
          {data.events.length === 0 ? (
            <p
              data-testid="medication-safety-events-empty"
              style={{
                margin: "0 0 12px",
                padding: 8,
                background: "#fed7d7",
                border: "1px solid #fc8181",
                borderRadius: 6,
                fontSize: 12,
                color: "#822727",
              }}
            >
              No active safety events. Provider review required for all
              medication safety decisions.
            </p>
          ) : (
            <ul
              data-testid="medication-safety-events-list"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {data.events.map(renderEvent)}
            </ul>
          )}

          {ackError && (
            <p
              data-testid="medication-safety-ack-error"
              style={{
                marginTop: 6,
                padding: 6,
                background: "#fff5f5",
                border: "1px solid #fed7d7",
                borderRadius: 4,
                color: "#822727",
                fontSize: 12,
              }}
            >
              {ackError}
            </p>
          )}

          <h4 style={{ margin: "16px 0 6px", fontSize: 13, color: "#2d3748" }}>
            Active medications
          </h4>
          {data.medications.length === 0 ? (
            <p
              data-testid="medication-safety-medications-empty"
              style={{
                margin: "0 0 12px",
                padding: 8,
                background: "#edf2f7",
                border: "1px solid #cbd5e0",
                borderRadius: 6,
                fontSize: 12,
                color: "#4a5568",
              }}
            >
              No medications on file. Add one below.
            </p>
          ) : (
            <ul
              data-testid="medication-safety-medications-list"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {data.medications.map(renderMedication)}
            </ul>
          )}

          <h4 style={{ margin: "16px 0 6px", fontSize: 13, color: "#2d3748" }}>
            Add a medication record
          </h4>
          <form
            data-testid="medication-safety-form"
            onSubmit={onSubmitMedication}
            style={{
              padding: 10,
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <label style={{ display: "block", marginBottom: 6 }}>
              Medication name
              <input
                type="text"
                value={medName}
                onChange={(e) => setMedName(e.target.value)}
                data-testid="medication-safety-form-name"
                maxLength={128}
                style={{ marginLeft: 4 }}
              />
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Class
              <select
                value={medClass}
                onChange={(e) => setMedClass(e.target.value)}
                data-testid="medication-safety-form-class"
                aria-label="Medication class"
                style={{ marginLeft: 4 }}
              >
                <option value="pgf2_analog">PGF2 analog</option>
                <option value="beta_blocker">Beta blocker</option>
                <option value="alpha_agonist">Alpha agonist</option>
                <option value="carbonic_anhydrase_inhibitor">CAI</option>
                <option value="combination_drop">Combination drop</option>
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Preservative
              <select
                value={medPreservative}
                onChange={(e) =>
                  setMedPreservative(e.target.value as PreservativeType)
                }
                data-testid="medication-safety-form-preservative"
                aria-label="Preservative type"
                style={{ marginLeft: 4 }}
              >
                <option value="BAK">BAK</option>
                <option value="preservative_free">Preservative-free</option>
                <option value="other">Other</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Doses per day
              <input
                type="number"
                min={0}
                max={24}
                value={medDose}
                onChange={(e) => setMedDose(Number(e.target.value))}
                data-testid="medication-safety-form-dose"
                style={{ marginLeft: 4, width: 64 }}
              />
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Last fill date
              <input
                type="date"
                value={medLastFill}
                onChange={(e) => setMedLastFill(e.target.value)}
                data-testid="medication-safety-form-last-fill"
                style={{ marginLeft: 4 }}
              />
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Days supply
              <input
                type="number"
                min={1}
                max={365}
                value={medDaysSupply}
                onChange={(e) => setMedDaysSupply(Number(e.target.value))}
                data-testid="medication-safety-form-days-supply"
                style={{ marginLeft: 4, width: 64 }}
              />
            </label>
            <button
              type="submit"
              disabled={submitting || !medName.trim()}
              data-testid="medication-safety-form-submit"
              style={{
                marginTop: 6,
                padding: "4px 12px",
                borderRadius: 4,
                border: "1px solid #4a5568",
                background: submitting ? "#cbd5e0" : "#1c4532",
                color: "#fff",
                fontSize: 12,
                fontWeight: 600,
                cursor: submitting ? "wait" : "pointer",
              }}
            >
              {submitting ? "Saving…" : "Record medication"}
            </button>
            {submitError && (
              <p
                data-testid="medication-safety-form-error"
                style={{
                  marginTop: 6,
                  padding: 6,
                  background: "#fff5f5",
                  border: "1px solid #fed7d7",
                  borderRadius: 4,
                  color: "#822727",
                  fontSize: 12,
                }}
              >
                {submitError}
              </p>
            )}
          </form>

          <p
            data-testid="medication-safety-disclosure"
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
