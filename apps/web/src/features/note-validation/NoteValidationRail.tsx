// Phase 82 — Note Validation Rail.
//
// Read-only deterministic pre-sign rail. Surfaces structured workflow
// checks (laterality consistency, follow-up cadence, unsigned upstream
// artifacts, review state, specialty data presence) the provider can
// review before signing. ChartNav does not diagnose, interpret images,
// or recommend treatment. Sign attestation remains the existing hard
// blocker — this rail does not autonomously block signing beyond it.
//
// For checks that require provider acknowledgement, the rail shows an
// inline acknowledgement checkbox. Acknowledgement state lives in
// local component state and is reset on refetch; it never persists or
// posts to the API in this phase.

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { getNoteValidation } from "./noteValidationApi";
import type {
  NoteValidationCheck,
  NoteValidationRailResponse,
  NoteValidationSource,
  NoteValidationStatus,
} from "./noteValidationTypes";

interface Props {
  encounterId: number;
}

type Tone = "green" | "amber" | "red" | "blue" | "neutral";

function toneStyle(tone: Tone): React.CSSProperties {
  if (tone === "green") return { background: "#c6f6d5", color: "#1c4532" };
  if (tone === "amber") return { background: "#fed7aa", color: "#7c2d12" };
  if (tone === "red") return { background: "#fed7d7", color: "#822727" };
  if (tone === "blue") return { background: "#bee3f8", color: "#1a365d" };
  return { background: "#edf2f7", color: "#2d3748" };
}

const STATUS_META: Record<
  NoteValidationStatus,
  { label: string; tone: Tone }
> = {
  pass: { label: "Pass", tone: "green" },
  warning: { label: "Warning", tone: "amber" },
  missing: { label: "Missing", tone: "amber" },
  blocked: { label: "Blocked", tone: "red" },
};

const SOURCE_LABELS: Record<NoteValidationSource, string> = {
  vitals: "Vitals",
  fundus: "Fundus",
  visit_draft: "Visit draft",
  retina_summary: "Retina summary",
  anti_vegf: "Anti-VEGF",
  glaucoma: "Glaucoma",
  cataract: "Cataract",
  signed_lock: "Signed lock",
};

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

function CheckRow({
  check,
  acknowledged,
  onToggle,
}: {
  check: NoteValidationCheck;
  acknowledged: boolean;
  onToggle: () => void;
}) {
  const meta = STATUS_META[check.status];
  const tid = `note-validation-check-${check.check_id}`;
  return (
    <li
      data-testid={tid}
      style={{
        padding: "8px 10px",
        borderLeft: "3px solid #cbd5e0",
        marginBottom: 6,
        background: "#f7fafc",
        borderRadius: "0 6px 6px 0",
        fontSize: 12,
        color: "#2d3748",
        lineHeight: 1.5,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          flexWrap: "wrap",
          marginBottom: 2,
        }}
      >
        <strong>{check.label}</strong>
        {pill(meta.label, meta.tone, `${tid}-status`)}
        {pill(
          SOURCE_LABELS[check.source] ?? check.source,
          "neutral",
          `${tid}-source`,
        )}
        {check.laterality &&
          pill(check.laterality, "blue", `${tid}-laterality`)}
        {check.requires_provider_acknowledgement &&
          pill("Ack required", "amber", `${tid}-ack-required`)}
      </div>
      <div style={{ color: "#4a5568" }}>{check.detail}</div>
      {check.requires_provider_acknowledgement && (
        <label
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            marginTop: 6,
            fontSize: 12,
            color: "#7c2d12",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            data-testid={`${tid}-ack-checkbox`}
            checked={acknowledged}
            onChange={onToggle}
          />
          Provider acknowledged
        </label>
      )}
    </li>
  );
}

export function NoteValidationRail({ encounterId }: Props) {
  const [data, setData] = useState<NoteValidationRailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acks, setAcks] = useState<Record<string, boolean>>({});

  const fetchRail = useCallback(() => {
    setLoading(true);
    setError(null);
    getNoteValidation(encounterId)
      .then((r) => {
        setData(r);
        setAcks({});
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    fetchRail();
  }, [fetchRail]);

  const ackRequired = useMemo(
    () =>
      (data?.checks ?? []).filter(
        (c) => c.requires_provider_acknowledgement,
      ),
    [data],
  );
  const acknowledgedCount = ackRequired.filter(
    (c) => acks[c.check_id],
  ).length;
  const allAcknowledged =
    ackRequired.length === 0 || acknowledgedCount === ackRequired.length;

  return (
    <div
      data-testid="note-validation-rail"
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
          Note Validation Rail
        </h3>
        <button
          type="button"
          onClick={fetchRail}
          disabled={loading}
          data-testid="note-validation-refresh-btn"
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
        data-testid="note-validation-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Validation checks use structured provider-entered workflow data.
        ChartNav does not diagnose, interpret images, or recommend
        treatment. Provider attestation remains required.
      </p>

      {error && (
        <p
          data-testid="note-validation-error"
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
          data-testid="note-validation-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          <p
            data-testid="note-validation-totals"
            style={{ margin: "0 0 12px", fontSize: 12, color: "#2d3748" }}
          >
            <strong>
              {data.totals.pass} pass · {data.totals.warning} warning ·{" "}
              {data.totals.missing} missing · {data.totals.blocked} blocked
            </strong>
            {ackRequired.length > 0 && (
              <>
                {" "}
                ·{" "}
                <span data-testid="note-validation-ack-summary">
                  {acknowledgedCount} / {ackRequired.length} acknowledged
                </span>
              </>
            )}
          </p>

          {ackRequired.length > 0 && (
            <p
              data-testid="note-validation-ack-banner"
              style={{
                margin: "0 0 8px",
                padding: 8,
                background: allAcknowledged ? "#f0fff4" : "#fffbf0",
                border: allAcknowledged
                  ? "1px solid #9ae6b4"
                  : "1px solid #f6d860",
                borderRadius: 6,
                fontSize: 12,
                color: allAcknowledged ? "#1c4532" : "#744210",
                lineHeight: 1.5,
              }}
            >
              {allAcknowledged
                ? "All required acknowledgements recorded. Provider attestation on the sign-and-lock checkbox is still required."
                : `${ackRequired.length - acknowledgedCount} acknowledgement(s) outstanding. Sign attestation is still the existing hard blocker; this rail does not block sign-off, but provider acknowledgement is requested before proceeding.`}
            </p>
          )}

          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {data.checks.map((check) => (
              <CheckRow
                key={check.check_id}
                check={check}
                acknowledged={!!acks[check.check_id]}
                onToggle={() =>
                  setAcks((prev) => ({
                    ...prev,
                    [check.check_id]: !prev[check.check_id],
                  }))
                }
              />
            ))}
          </ul>

          <p
            data-testid="note-validation-disclosure"
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
