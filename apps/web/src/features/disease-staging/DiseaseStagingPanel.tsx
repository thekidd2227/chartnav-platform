// Phase 84 — Disease Staging Panel.
//
// Read + record surface for provider-entered disease staging. Color
// coding indicates change (progression_detected boolean only) — NOT
// clinical interpretation. ChartNav does not stage disease, does not
// interpret imaging, does not infer progression, does not recommend
// treatment or surgery. Every value displayed was entered by the
// provider; the panel renders it back metadata-only.

import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getDiseaseStaging,
  postDiseaseStage,
} from "./diseaseStagingApi";
import type {
  DiseaseStagingPanelResponse,
  StagingSystem,
} from "./diseaseStagingTypes";

interface Props {
  patientId: number;
  encounterId: number;
}

type Tone = "green" | "amber" | "neutral";

function toneStyle(tone: Tone): React.CSSProperties {
  if (tone === "green") return { background: "#c6f6d5", color: "#1c4532" };
  if (tone === "amber") return { background: "#fed7aa", color: "#7c2d12" };
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

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function progressionTone(detected: boolean | null): Tone {
  if (detected === null) return "neutral";
  if (detected) return "amber";
  return "green";
}

function progressionLabel(detected: boolean | null): string {
  if (detected === null) return "First stage on record";
  if (detected) return "Stage changed";
  return "Stage unchanged";
}

export function DiseaseStagingPanel({ patientId, encounterId }: Props) {
  const [data, setData] = useState<DiseaseStagingPanelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Form state
  const [system, setSystem] = useState<StagingSystem>("amd_areds");
  const [diagnosis, setDiagnosis] = useState("h35.31");
  const [stage, setStage] = useState("Category 1");

  const fetchPanel = useCallback(() => {
    setLoading(true);
    setError(null);
    getDiseaseStaging(patientId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  useEffect(() => {
    fetchPanel();
  }, [fetchPanel]);

  const stagesForSelected = useMemo(() => {
    const found = data?.supported_systems.find((s) => s.code === system);
    return found?.stages ?? [];
  }, [data, system]);

  // Reset stage when system changes to the first allowed value.
  useEffect(() => {
    if (stagesForSelected.length > 0 && !stagesForSelected.includes(stage)) {
      setStage(stagesForSelected[0]!);
    }
  }, [stagesForSelected, stage]);

  const onSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);
      setSubmitting(true);
      try {
        await postDiseaseStage(encounterId, {
          diagnosis_code: diagnosis.trim(),
          staging_system: system,
          stage_value: stage,
        });
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Stage record failed",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [diagnosis, encounterId, fetchPanel, stage, system],
  );

  const latest = data?.latest_by_diagnosis ?? {};
  const latestEntries = Object.values(latest);

  return (
    <div
      data-testid="disease-staging-panel"
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
          Disease Staging
        </h3>
        <button
          type="button"
          onClick={fetchPanel}
          disabled={loading}
          data-testid="disease-staging-refresh-btn"
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
        data-testid="disease-staging-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-entered disease staging records. ChartNav does not stage
        disease, does not interpret imaging, does not infer progression,
        and does not recommend treatment or surgery.
      </p>

      {error && (
        <p
          data-testid="disease-staging-error"
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
          data-testid="disease-staging-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          <p
            data-testid="disease-staging-patient-meta"
            style={{
              margin: "0 0 12px",
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <strong>{data.patient_name ?? "Unknown patient"}</strong>{" "}
            ({data.patient_identifier ?? "—"}) ·{" "}
            <span data-testid="disease-staging-record-count">
              {data.records.length} record
              {data.records.length === 1 ? "" : "s"}
            </span>
          </p>

          {latestEntries.length === 0 ? (
            <p
              data-testid="disease-staging-empty"
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
              No provider-entered disease-staging records on file. Staging
              is informational and never blocks signing.
            </p>
          ) : (
            <ul
              data-testid="disease-staging-latest-list"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {latestEntries.map((rec) => (
                <li
                  key={rec.diagnosis_code}
                  data-testid={`disease-staging-latest-${rec.diagnosis_code}`}
                  style={{
                    padding: 10,
                    background: "#fff",
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
                    <strong>{rec.diagnosis_code}</strong>
                    {pill(
                      progressionLabel(rec.progression_detected),
                      progressionTone(rec.progression_detected),
                      `disease-staging-progression-${rec.diagnosis_code}`,
                    )}
                  </div>
                  <div>
                    <strong>System:</strong>{" "}
                    <span
                      data-testid={`disease-staging-system-${rec.diagnosis_code}`}
                    >
                      {rec.staging_system_label}
                    </span>
                  </div>
                  <div>
                    <strong>Current stage:</strong>{" "}
                    <span
                      data-testid={`disease-staging-stage-${rec.diagnosis_code}`}
                    >
                      {rec.stage_value}
                    </span>
                  </div>
                  {rec.prior_stage && (
                    <div>
                      <strong>Prior stage:</strong>{" "}
                      <span
                        data-testid={`disease-staging-prior-${rec.diagnosis_code}`}
                      >
                        {rec.prior_stage}
                      </span>
                    </div>
                  )}
                  {rec.elapsed_days_since_prior !== null && (
                    <div>
                      <strong>Days since prior:</strong>{" "}
                      <span
                        data-testid={`disease-staging-elapsed-${rec.diagnosis_code}`}
                      >
                        {rec.elapsed_days_since_prior}
                      </span>
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: "#4a5568" }}>
                    Staged by{" "}
                    <span
                      data-testid={`disease-staging-actor-${rec.diagnosis_code}`}
                    >
                      {rec.staged_by_display_name ?? "Unknown"}
                      {rec.staged_by_role && ` (${rec.staged_by_role})`}
                    </span>{" "}
                    at {fmtDate(rec.staged_at)}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <form
            data-testid="disease-staging-form"
            onSubmit={onSubmit}
            style={{
              marginTop: 12,
              padding: 10,
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              fontSize: 12,
              color: "#2d3748",
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
              Record provider-entered stage
            </p>
            <label style={{ display: "block", marginBottom: 6 }}>
              Staging system{" "}
              <select
                value={system}
                onChange={(e) => setSystem(e.target.value as StagingSystem)}
                data-testid="disease-staging-system-select"
                style={{ marginLeft: 4 }}
              >
                {data.supported_systems.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Stage value{" "}
              <select
                value={stage}
                onChange={(e) => setStage(e.target.value)}
                data-testid="disease-staging-stage-select"
                style={{ marginLeft: 4 }}
              >
                {stagesForSelected.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Diagnosis code{" "}
              <input
                type="text"
                value={diagnosis}
                onChange={(e) => setDiagnosis(e.target.value)}
                data-testid="disease-staging-diagnosis-input"
                maxLength={64}
                style={{ marginLeft: 4 }}
              />
            </label>
            <button
              type="submit"
              disabled={submitting || !diagnosis.trim()}
              data-testid="disease-staging-submit-btn"
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
              {submitting ? "Saving…" : "Record stage"}
            </button>
            {submitError && (
              <p
                data-testid="disease-staging-submit-error"
                style={{
                  marginTop: 6,
                  padding: 6,
                  background: "#fff5f5",
                  border: "1px solid #fed7d7",
                  borderRadius: 4,
                  color: "#822727",
                }}
              >
                {submitError}
              </p>
            )}
          </form>

          <p
            data-testid="disease-staging-disclosure"
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
