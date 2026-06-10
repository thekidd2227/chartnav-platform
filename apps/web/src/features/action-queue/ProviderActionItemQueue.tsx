// Phase 81 — Provider Action Item Queue.
//
// Cross-specialty workflow triage surface. Aggregates deterministic
// signals from the Anti-VEGF rail (Phase 78), the Glaucoma cockpit
// (Phase 79), the Cataract workflow (Phase 80), and the Phase 1
// signed-lock / visit-summary workflow into four grouped sections:
// Same day / This week / Routine / Informational.
//
// Bucket assignment is a documented deterministic rule over
// provider-entered data — not an autonomous urgency decision.
// ChartNav does not diagnose, does not recommend treatment or
// surgery, and does not interpret images.

import React, { useCallback, useEffect, useState } from "react";
import { getProviderActionQueue } from "./actionQueueApi";
import type {
  ActionQueueBucket,
  ActionQueueItem,
  ActionQueueSource,
  ProviderActionQueue,
} from "./actionQueueTypes";

type Tone = "green" | "amber" | "red" | "blue" | "neutral";

function toneStyle(tone: Tone): React.CSSProperties {
  if (tone === "green") return { background: "#c6f6d5", color: "#1c4532" };
  if (tone === "amber") return { background: "#fed7aa", color: "#7c2d12" };
  if (tone === "red") return { background: "#fed7d7", color: "#822727" };
  if (tone === "blue") return { background: "#bee3f8", color: "#1a365d" };
  return { background: "#edf2f7", color: "#2d3748" };
}

const BUCKET_META: Record<
  ActionQueueBucket,
  { title: string; tone: Tone }
> = {
  same_day: { title: "Same day", tone: "red" },
  this_week: { title: "This week", tone: "amber" },
  routine: { title: "Routine", tone: "blue" },
  informational: { title: "Informational", tone: "neutral" },
};

const SOURCE_LABELS: Record<ActionQueueSource, string> = {
  anti_vegf: "Anti-VEGF",
  glaucoma: "Glaucoma",
  cataract: "Cataract",
  visit_summary: "Visit summary",
  signed_lock: "Signed lock",
  staging: "Disease staging",
  medication: "Medication safety",
  quality: "Quality documentation",
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

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(
      iso.length === 10 ? iso + "T00:00:00Z" : iso,
    ).toLocaleDateString();
  } catch {
    return iso;
  }
}

function ItemRow({ item }: { item: ActionQueueItem }) {
  return (
    <li
      data-testid={`action-item-${item.item_id}`}
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
        <strong>{item.label}</strong>
        {item.laterality &&
          pill(
            item.laterality,
            "blue",
            `action-item-${item.item_id}-laterality`,
          )}
        {pill(
          SOURCE_LABELS[item.specialty_source] ?? item.specialty_source,
          "neutral",
          `action-item-${item.item_id}-source`,
        )}
        {pill(item.status, "amber", `action-item-${item.item_id}-status`)}
        {item.insufficient_data &&
          pill(
            "Insufficient data",
            "red",
            `action-item-${item.item_id}-insufficient`,
          )}
        {item.requires_provider_review &&
          pill(
            "Provider review required",
            "green",
            `action-item-${item.item_id}-review`,
          )}
      </div>
      <div style={{ color: "#4a5568" }}>
        <span data-testid={`action-item-${item.item_id}-patient`}>
          {item.patient_name ?? "Unknown patient"} (
          {item.patient_identifier ?? "—"})
        </span>
        {item.due_at && <> · due {fmtDate(item.due_at)}</>}
      </div>
      <div style={{ color: "#4a5568", marginTop: 2 }}>{item.detail}</div>
    </li>
  );
}

function BucketSection({
  bucket,
  items,
}: {
  bucket: ActionQueueBucket;
  items: ActionQueueItem[];
}) {
  const meta = BUCKET_META[bucket];
  return (
    <div
      data-testid={`action-queue-bucket-${bucket}`}
      style={{ marginBottom: 14 }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          marginBottom: 6,
        }}
      >
        <h4
          style={{
            margin: 0,
            fontSize: 13,
            fontWeight: 700,
            color: "#2d3748",
          }}
        >
          {meta.title}
        </h4>
        {pill(
          `${items.length} item${items.length === 1 ? "" : "s"}`,
          meta.tone,
          `action-queue-bucket-${bucket}-count`,
        )}
      </div>
      {items.length === 0 ? (
        <p
          data-testid={`action-queue-bucket-${bucket}-empty`}
          style={{
            margin: 0,
            fontSize: 12,
            color: "#4a5568",
            padding: 6,
            border: "1px dashed #cbd5e0",
            borderRadius: 6,
          }}
        >
          No items in this bucket.
        </p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {items.map((it) => (
            <ItemRow key={it.item_id} item={it} />
          ))}
        </ul>
      )}
    </div>
  );
}

export function ProviderActionItemQueue() {
  const [queue, setQueue] = useState<ProviderActionQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = useCallback(() => {
    setLoading(true);
    setError(null);
    getProviderActionQueue()
      .then(setQueue)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  return (
    <div
      data-testid="provider-action-item-queue"
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
          Provider Action Item Queue
        </h3>
        <button
          type="button"
          onClick={fetchQueue}
          disabled={loading}
          data-testid="action-queue-refresh-btn"
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
        data-testid="action-queue-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Workflow queue from provider-entered data across the Anti-VEGF
        rail, Glaucoma cockpit, Cataract workflow, and signed-lock
        artifacts. Does not diagnose or recommend treatment. Provider
        review required for every item.
      </p>

      {error && (
        <p
          data-testid="action-queue-error"
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

      {loading && queue === null && (
        <p
          data-testid="action-queue-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {queue && (
        <>
          <p
            data-testid="action-queue-meta"
            style={{ margin: "0 0 12px", fontSize: 12, color: "#2d3748" }}
          >
            <strong data-testid="action-queue-total">
              {queue.total_items} open item
              {queue.total_items === 1 ? "" : "s"}
            </strong>{" "}
            {queue.sources_present.length > 0 && (
              <>
                · sources:{" "}
                <span data-testid="action-queue-sources">
                  {queue.sources_present
                    .map((s) => SOURCE_LABELS[s] ?? s)
                    .join(", ")}
                </span>
              </>
            )}
          </p>

          <BucketSection bucket="same_day" items={queue.buckets.same_day} />
          <BucketSection bucket="this_week" items={queue.buckets.this_week} />
          <BucketSection bucket="routine" items={queue.buckets.routine} />
          <BucketSection
            bucket="informational"
            items={queue.buckets.informational}
          />

          <p
            data-testid="action-queue-disclosure"
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
            {queue.disclosure}
          </p>
        </>
      )}
    </div>
  );
}
