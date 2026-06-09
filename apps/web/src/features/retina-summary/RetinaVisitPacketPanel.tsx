// Phase 77 — Retina Visit Packet panel.
//
// Buyer-visible packet builder: fetches the
// /api/v1/encounters/{id}/retina-visit-packet aggregator, lets the
// operator preview the JSON, copy it to the clipboard, and download
// it as a .json file.
//
// The packet itself is built by the backend (see
// app/services/retina_visit_packet.py). This panel is a pure
// presentational + IO surface — no business logic, no clinical text.

import React, { useCallback, useState } from "react";
import { getRetinaVisitPacket } from "./retinaSummaryApi";
import type {
  RetinaPacketSafetyBoundary,
  RetinaVisitPacket,
} from "./retinaPacketTypes";

interface Props {
  encounterId: number;
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function SafetyBoundaries({
  boundaries,
}: {
  boundaries: RetinaPacketSafetyBoundary[];
}) {
  return (
    <ul
      data-testid="retina-packet-safety-boundaries"
      style={{
        margin: "6px 0 0",
        paddingLeft: 16,
        fontSize: 11,
        color: "#1c4532",
        lineHeight: 1.5,
      }}
    >
      {boundaries.map((b) => (
        <li
          key={b.key}
          data-testid={`retina-packet-boundary-${b.key}`}
        >
          {b.statement}
        </li>
      ))}
    </ul>
  );
}

export function RetinaVisitPacketPanel({ encounterId }: Props) {
  const [packet, setPacket] = useState<RetinaVisitPacket | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "ok" | "fail">("idle");

  const fetchPacket = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = await getRetinaVisitPacket(encounterId);
      setPacket(p);
      setPreviewOpen(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Packet build failed");
    } finally {
      setLoading(false);
    }
  }, [encounterId]);

  const copyToClipboard = useCallback(async () => {
    if (!packet) return;
    const text = JSON.stringify(packet, null, 2);
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        setCopyState("ok");
        return;
      }
      throw new Error("clipboard unavailable");
    } catch {
      setCopyState("fail");
    } finally {
      window.setTimeout(() => setCopyState("idle"), 2000);
    }
  }, [packet]);

  const download = useCallback(() => {
    if (!packet) return;
    const text = JSON.stringify(packet, null, 2);
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `retina-visit-packet-encounter-${encounterId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [packet, encounterId]);

  const sealed = packet?.review_sign_lock.all_signed;

  return (
    <div
      data-testid="retina-visit-packet-panel"
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
          Retina Visit Packet
        </h3>
        <span
          data-testid="retina-packet-schema-version"
          style={{ fontSize: 11, color: "#4a5568" }}
        >
          {packet ? packet.schema_version : "chartnav.retina_visit_packet/1.0"}
        </span>
      </div>
      <p
        data-testid="retina-packet-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Self-describing JSON snapshot of this visit's artifact metadata.
        Preview, copy, or download for internal distribution after a
        buyer demo. Metadata only — no clinical free text. Provider
        review required for every clinical artifact referenced.
      </p>

      <div
        style={{
          display: "flex",
          gap: 6,
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <button
          type="button"
          onClick={fetchPacket}
          disabled={loading}
          data-testid="retina-packet-build-btn"
          style={{
            background: "#2c5282",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            padding: "6px 14px",
            fontSize: 13,
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Building…" : packet ? "Rebuild packet" : "Build packet"}
        </button>
        <button
          type="button"
          onClick={copyToClipboard}
          disabled={!packet}
          data-testid="retina-packet-copy-btn"
          style={{
            background: packet ? "#fff" : "#edf2f7",
            color: "#2d3748",
            border: "1px solid #cbd5e0",
            borderRadius: 6,
            padding: "6px 14px",
            fontSize: 13,
            fontWeight: 600,
            cursor: packet ? "pointer" : "not-allowed",
          }}
        >
          {copyState === "ok"
            ? "Copied"
            : copyState === "fail"
              ? "Copy failed"
              : "Copy JSON"}
        </button>
        <button
          type="button"
          onClick={download}
          disabled={!packet}
          data-testid="retina-packet-download-btn"
          style={{
            background: packet ? "#fff" : "#edf2f7",
            color: "#2d3748",
            border: "1px solid #cbd5e0",
            borderRadius: 6,
            padding: "6px 14px",
            fontSize: 13,
            fontWeight: 600,
            cursor: packet ? "pointer" : "not-allowed",
          }}
        >
          Download .json
        </button>
      </div>

      {error && (
        <p
          data-testid="retina-packet-error"
          style={{
            color: "#9b2c2c",
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

      {packet && (
        <>
          <div
            data-testid="retina-packet-meta"
            style={{
              padding: 10,
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              marginBottom: 10,
              fontSize: 12,
              color: "#2d3748",
              lineHeight: 1.6,
            }}
          >
            <div>
              <strong>Encounter:</strong> #{packet.encounter.id} ·{" "}
              {packet.encounter.patient_name ?? "—"} (
              {packet.encounter.patient_identifier ?? "—"})
            </div>
            <div>
              <strong>Generated:</strong>{" "}
              <span data-testid="retina-packet-generated-at">
                {fmtTime(packet.generated_at)}
              </span>
            </div>
            <div>
              <strong>Status:</strong>{" "}
              <span
                data-testid="retina-packet-sealed-state"
                style={{
                  padding: "1px 6px",
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 0.3,
                  textTransform: "uppercase",
                  background: sealed ? "#c6f6d5" : "#fed7aa",
                  color: sealed ? "#1c4532" : "#7c2d12",
                }}
              >
                {sealed ? "All Signed · Sealed" : "Pending Signatures"}
              </span>
            </div>
            <div>
              <strong>Artifact counts:</strong> intake{" "}
              <span data-testid="retina-packet-count-intake">
                {packet.intake.count}
              </span>{" "}
              · visit draft{" "}
              <span data-testid="retina-packet-count-visit-draft">
                {packet.visit_draft.count}
              </span>{" "}
              · fundus{" "}
              <span data-testid="retina-packet-count-fundus">
                {packet.fundus.count}
              </span>
            </div>
            <div>
              <strong>Evidence events:</strong>{" "}
              <span data-testid="retina-packet-evidence-count">
                {packet.evidence_timeline.length}
              </span>
            </div>
          </div>

          <div
            data-testid="retina-packet-hashes"
            style={{
              padding: 10,
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              marginBottom: 10,
              fontSize: 11,
              color: "#2d3748",
              fontFamily:
                "ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          >
            <strong style={{ fontFamily: "sans-serif" }}>
              Artifact integrity hashes (sha256):
            </strong>
            <ul style={{ margin: "4px 0 0", paddingLeft: 16 }}>
              {packet.artifact_hashes.map((h) => (
                <li
                  key={h.section}
                  data-testid={`retina-packet-hash-${h.section}`}
                >
                  {h.section}: {h.hash_short}…
                </li>
              ))}
            </ul>
          </div>

          <div
            style={{
              padding: 10,
              background: "#f0fff4",
              border: "1px solid #9ae6b4",
              borderRadius: 6,
              marginBottom: 10,
            }}
          >
            <p
              style={{
                margin: "0 0 4px",
                fontSize: 11,
                fontWeight: 700,
                color: "#1c4532",
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Safety boundaries asserted in this packet
            </p>
            <SafetyBoundaries boundaries={packet.safety_boundaries} />
          </div>

          {previewOpen && (
            <details
              data-testid="retina-packet-preview-details"
              open
              style={{
                background: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: 6,
                padding: 10,
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 12,
                  color: "#4a5568",
                }}
              >
                Preview packet JSON
              </summary>
              <pre
                data-testid="retina-packet-preview"
                style={{
                  whiteSpace: "pre-wrap",
                  wordWrap: "break-word",
                  fontSize: 11,
                  color: "#2d3748",
                  margin: "8px 0 0",
                  maxHeight: 320,
                  overflow: "auto",
                  background: "#f7fafc",
                  padding: 8,
                  borderRadius: 4,
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, monospace",
                }}
              >
                {JSON.stringify(packet, null, 2)}
              </pre>
            </details>
          )}
        </>
      )}
    </div>
  );
}
