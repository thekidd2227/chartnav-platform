// Phase 88 — Imaging Metadata Review Linkage panel.
//
// Read + review surface for structured imaging metadata. ChartNav
// does NOT interpret images and does NOT infer findings from
// imaging — this panel surfaces modality, laterality, acquisition
// date, device manufacturer/model, source system, review status,
// and reviewer metadata only.

import React, { useCallback, useEffect, useState } from "react";

import {
  getImagingMetadata,
  patchImagingMetadataReview,
} from "./imagingMetadataApi";
import type {
  ImagingMetadataItem,
  ImagingMetadataResponse,
  ImagingReviewStatus,
} from "./imagingMetadataTypes";

interface Props {
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

function reviewTone(status: ImagingReviewStatus): Tone {
  if (status === "reviewed") return "green";
  if (status === "ready_for_review") return "amber";
  return "neutral";
}

function reviewLabel(status: ImagingReviewStatus): string {
  switch (status) {
    case "reviewed":
      return "Reviewed";
    case "ready_for_review":
      return "Ready for review";
    case "uploaded":
      return "Uploaded";
    case "pending_upload":
      return "Pending upload";
    case "archived":
      return "Archived";
    default:
      return status;
  }
}

export function ImagingMetadataPanel({ encounterId }: Props) {
  const [data, setData] = useState<ImagingMetadataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const fetchPanel = useCallback(() => {
    setLoading(true);
    setError(null);
    getImagingMetadata(encounterId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    fetchPanel();
  }, [fetchPanel]);

  const onMarkReviewed = useCallback(
    async (item: ImagingMetadataItem) => {
      setReviewError(null);
      setReviewing(item.id);
      try {
        await patchImagingMetadataReview(item.id);
        fetchPanel();
      } catch (err) {
        setReviewError(
          err instanceof Error ? err.message : "Mark reviewed failed",
        );
      } finally {
        setReviewing(null);
      }
    },
    [fetchPanel],
  );

  return (
    <div
      data-testid="imaging-metadata-panel"
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
          Imaging Metadata
        </h3>
        <button
          type="button"
          onClick={fetchPanel}
          disabled={loading}
          data-testid="imaging-metadata-refresh-btn"
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
        data-testid="imaging-metadata-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Imaging metadata only. ChartNav does not interpret images, does
        not infer findings, does not autonomously classify modality or
        laterality, and does not recommend treatment or surgery. Provider
        review required.
      </p>

      {error && (
        <p
          data-testid="imaging-metadata-error"
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
          data-testid="imaging-metadata-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          <div
            data-testid="imaging-metadata-counts"
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
              data-testid="imaging-metadata-count-total"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Total:</strong> {data.counts.total}
            </div>
            <div
              data-testid="imaging-metadata-count-reviewed"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Reviewed:</strong> {data.counts.reviewed}
            </div>
            <div
              data-testid="imaging-metadata-count-unreviewed"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Awaiting review:</strong> {data.counts.unreviewed}
            </div>
          </div>

          {data.items.length === 0 ? (
            <p
              data-testid="imaging-metadata-empty"
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
              No imaging metadata on file for this patient. Metadata is
              informational and never blocks signing.
            </p>
          ) : (
            <ul
              data-testid="imaging-metadata-list"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {data.items.map((item) => (
                <li
                  key={item.id}
                  data-testid={`imaging-metadata-row-${item.id}`}
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
                    <strong
                      data-testid={`imaging-metadata-modality-${item.id}`}
                    >
                      {item.modality} · {item.laterality}
                    </strong>
                    {pill(
                      reviewLabel(item.review_status),
                      reviewTone(item.review_status),
                      `imaging-metadata-status-${item.id}`,
                    )}
                  </div>
                  <div>
                    <strong>Modality group:</strong>{" "}
                    <span
                      data-testid={`imaging-metadata-group-${item.id}`}
                    >
                      {item.modality_group}
                    </span>
                  </div>
                  <div>
                    <strong>Acquisition date:</strong>{" "}
                    <span
                      data-testid={`imaging-metadata-date-${item.id}`}
                    >
                      {fmtDate(item.acquisition_date)}
                    </span>
                  </div>
                  {(item.device_manufacturer || item.device_model) && (
                    <div data-testid={`imaging-metadata-device-${item.id}`}>
                      <strong>Device:</strong>{" "}
                      {item.device_manufacturer ?? "—"}
                      {item.device_model ? ` / ${item.device_model}` : ""}
                    </div>
                  )}
                  {item.source_system && (
                    <div
                      data-testid={`imaging-metadata-source-${item.id}`}
                    >
                      <strong>Source system:</strong> {item.source_system}
                    </div>
                  )}
                  {item.reviewed_by_display && (
                    <div
                      data-testid={`imaging-metadata-reviewer-${item.id}`}
                      style={{ fontSize: 11, color: "#4a5568" }}
                    >
                      Reviewed by {item.reviewed_by_display}
                      {item.reviewed_by_role && ` (${item.reviewed_by_role})`}{" "}
                      at {fmtDate(item.reviewed_at)}
                    </div>
                  )}
                  <div
                    data-testid={`imaging-metadata-hash-${item.id}`}
                    style={{
                      fontSize: 10,
                      color: "#4a5568",
                      fontFamily: "monospace",
                      marginTop: 4,
                    }}
                  >
                    metadata_hash: {item.metadata_hash.slice(0, 12)}…
                  </div>
                  {item.review_status !== "reviewed" && (
                    <button
                      type="button"
                      onClick={() => onMarkReviewed(item)}
                      disabled={reviewing === item.id}
                      data-testid={`imaging-metadata-review-btn-${item.id}`}
                      style={{
                        marginTop: 6,
                        fontSize: 11,
                        padding: "3px 8px",
                        borderRadius: 4,
                        border: "1px solid #4a5568",
                        background:
                          reviewing === item.id ? "#cbd5e0" : "#1c4532",
                        color: "#fff",
                        cursor:
                          reviewing === item.id ? "wait" : "pointer",
                      }}
                    >
                      {reviewing === item.id
                        ? "Marking reviewed…"
                        : "Mark reviewed"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {reviewError && (
            <p
              data-testid="imaging-metadata-review-error"
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
              {reviewError}
            </p>
          )}

          <p
            data-testid="imaging-metadata-disclosure"
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
