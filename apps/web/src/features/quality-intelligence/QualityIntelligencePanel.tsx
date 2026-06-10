// Phase 89 — Quality Intelligence Panel.
//
// Provider-reviewed quality documentation support. ChartNav does
// NOT submit to CMS, IRIS, payers, or registries; does NOT
// autonomously compute MIPS scoring; does NOT autonomously decide
// whether a measure is met; does NOT interpret images; does NOT
// diagnose; does NOT recommend treatment.

import React, { useCallback, useEffect, useState } from "react";

import {
  getQualityMeasures,
  postQualityResponse,
} from "./qualityIntelligenceApi";
import type {
  QualityMeasureItem,
  QualityMeasuresResponse,
  QualityResponseStatus,
  QualityResponseType,
} from "./qualityIntelligenceTypes";

interface Props {
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

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusTone(status: QualityResponseStatus): Tone {
  if (status === "met") return "green";
  if (status === "exception" || status === "exclusion") return "green";
  if (status === "not_applicable") return "neutral";
  if (status === "pending" || status === "incomplete") return "amber";
  return "neutral";
}

function statusLabel(status: QualityResponseStatus): string {
  switch (status) {
    case "met":
      return "Met";
    case "exception":
      return "Exception";
    case "exclusion":
      return "Exclusion";
    case "not_applicable":
      return "Not applicable";
    case "incomplete":
      return "Incomplete";
    case "pending":
      return "Pending response";
    default:
      return status;
  }
}

export function QualityIntelligencePanel({ encounterId }: Props) {
  const [data, setData] = useState<QualityMeasuresResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [selectedException, setSelectedException] = useState<
    Record<string, string>
  >({});

  const fetchPanel = useCallback(() => {
    setLoading(true);
    setError(null);
    getQualityMeasures(encounterId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    fetchPanel();
  }, [fetchPanel]);

  const onRecord = useCallback(
    async (
      item: QualityMeasureItem,
      responseType: QualityResponseType,
    ) => {
      setSubmitError(null);
      setSubmittingId(item.measure_id);
      try {
        const payload: {
          response_type: QualityResponseType;
          exception_code?: string;
        } = { response_type: responseType };
        if (responseType === "exception") {
          const code = selectedException[item.measure_id];
          if (code) payload.exception_code = code;
        }
        await postQualityResponse(encounterId, item.measure_id, payload);
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Record response failed",
        );
      } finally {
        setSubmittingId(null);
      }
    },
    [encounterId, fetchPanel, selectedException],
  );

  return (
    <div
      data-testid="quality-intelligence-panel"
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
          Quality Documentation Support
        </h3>
        <button
          type="button"
          onClick={fetchPanel}
          disabled={loading}
          data-testid="quality-intelligence-refresh-btn"
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
        data-testid="quality-intelligence-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-reviewed quality documentation support. ChartNav does
        not submit to CMS, IRIS, payers, or registries; does not
        autonomously compute MIPS scoring; and does not autonomously
        decide whether a measure is met. Not a certified submission
        system.
      </p>

      {error && (
        <p
          data-testid="quality-intelligence-error"
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
          data-testid="quality-intelligence-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          {data.internal_demo_specs_present && (
            <p
              data-testid="quality-intelligence-demo-caution"
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
              <strong>Internal demo specs present.</strong> One or more
              measure specifications below are placeholder demo specs
              and have NOT been verified for current CMS / IRIS /
              payer program use. Verify with a qualified operator
              before any real-program submission.
            </p>
          )}

          <div
            data-testid="quality-intelligence-counts"
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
              data-testid="quality-intelligence-count-applicable"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Applicable:</strong> {data.counts.applicable}
            </div>
            <div
              data-testid="quality-intelligence-count-completed"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Documented:</strong> {data.counts.completed}
            </div>
            <div
              data-testid="quality-intelligence-count-incomplete"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Awaiting response:</strong> {data.counts.incomplete}
            </div>
            <div
              data-testid="quality-intelligence-submission-status"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Submission status:</strong> not submitted
            </div>
          </div>

          {data.items.length === 0 ? (
            <p
              data-testid="quality-intelligence-empty"
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
              No quality measure specs on file for this program year.
              Quality documentation is informational and never blocks
              signing.
            </p>
          ) : (
            <ul
              data-testid="quality-intelligence-list"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {data.items.map((item) => (
                <li
                  key={item.measure_id}
                  data-testid={`quality-intelligence-row-${item.measure_id}`}
                  style={{
                    padding: 10,
                    background: item.applicable ? "#fff" : "#f7fafc",
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
                    <strong>{item.measure_name}</strong>
                    {pill(
                      statusLabel(item.response_status),
                      statusTone(item.response_status),
                      `quality-intelligence-status-${item.measure_id}`,
                    )}
                  </div>
                  <div>
                    <strong>Measure:</strong>{" "}
                    <code
                      data-testid={`quality-intelligence-measure-id-${item.measure_id}`}
                    >
                      {item.measure_id}
                    </code>{" "}
                    · <strong>Program year:</strong> {item.program_year}
                  </div>
                  {item.internal_demo_only && (
                    <div
                      data-testid={`quality-intelligence-demo-flag-${item.measure_id}`}
                      style={{ color: "#7c2d12" }}
                    >
                      <strong>Internal demo spec</strong> — not verified
                      for submission.
                    </div>
                  )}
                  {item.missing_structured_fields.length > 0 && (
                    <div
                      data-testid={`quality-intelligence-missing-${item.measure_id}`}
                    >
                      <strong>Missing structured fields:</strong>{" "}
                      {item.missing_structured_fields.join(", ")}
                    </div>
                  )}
                  {item.responded_by_display && (
                    <div
                      data-testid={`quality-intelligence-responder-${item.measure_id}`}
                      style={{ fontSize: 11, color: "#4a5568" }}
                    >
                      Recorded by {item.responded_by_display}
                      {item.responded_by_role && ` (${item.responded_by_role})`}{" "}
                      at {fmtDate(item.responded_at)}
                    </div>
                  )}
                  {item.applicable && (
                    <div
                      style={{
                        marginTop: 6,
                        display: "flex",
                        gap: 6,
                        flexWrap: "wrap",
                      }}
                    >
                      {(["met", "incomplete", "not_applicable"] as const).map(
                        (resp) => (
                          <button
                            key={resp}
                            type="button"
                            onClick={() => onRecord(item, resp)}
                            disabled={submittingId === item.measure_id}
                            data-testid={`quality-intelligence-${resp}-btn-${item.measure_id}`}
                            style={{
                              fontSize: 11,
                              padding: "3px 8px",
                              borderRadius: 4,
                              border: "1px solid #4a5568",
                              background:
                                submittingId === item.measure_id
                                  ? "#cbd5e0"
                                  : item.response_status === resp
                                  ? "#1c4532"
                                  : "#fff",
                              color:
                                submittingId === item.measure_id ||
                                item.response_status === resp
                                  ? "#fff"
                                  : "#2d3748",
                              cursor:
                                submittingId === item.measure_id
                                  ? "wait"
                                  : "pointer",
                            }}
                          >
                            {statusLabel(resp)}
                          </button>
                        ),
                      )}
                      {item.exception_codes.length > 0 && (
                        <>
                          <select
                            value={
                              selectedException[item.measure_id] ?? ""
                            }
                            onChange={(e) =>
                              setSelectedException((prev) => ({
                                ...prev,
                                [item.measure_id]: e.target.value,
                              }))
                            }
                            data-testid={`quality-intelligence-exception-select-${item.measure_id}`}
                            style={{ fontSize: 11 }}
                          >
                            <option value="">— exception code —</option>
                            {item.exception_codes.map((c) => (
                              <option key={c} value={c}>
                                {c}
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            onClick={() => onRecord(item, "exception")}
                            disabled={
                              submittingId === item.measure_id ||
                              !selectedException[item.measure_id]
                            }
                            data-testid={`quality-intelligence-exception-btn-${item.measure_id}`}
                            style={{
                              fontSize: 11,
                              padding: "3px 8px",
                              borderRadius: 4,
                              border: "1px solid #4a5568",
                              background: "#fff",
                              color: "#2d3748",
                              cursor:
                                submittingId === item.measure_id
                                  ? "wait"
                                  : "pointer",
                            }}
                          >
                            Record exception
                          </button>
                          <button
                            type="button"
                            onClick={() => onRecord(item, "exclusion")}
                            disabled={submittingId === item.measure_id}
                            data-testid={`quality-intelligence-exclusion-btn-${item.measure_id}`}
                            style={{
                              fontSize: 11,
                              padding: "3px 8px",
                              borderRadius: 4,
                              border: "1px solid #4a5568",
                              background: "#fff",
                              color: "#2d3748",
                              cursor:
                                submittingId === item.measure_id
                                  ? "wait"
                                  : "pointer",
                            }}
                          >
                            Exclusion
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}

          {submitError && (
            <p
              data-testid="quality-intelligence-submit-error"
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

          <p
            data-testid="quality-intelligence-disclosure"
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
