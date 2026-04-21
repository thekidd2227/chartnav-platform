// Phase 38 — trust-calibrated badge primitive.
//
// Consumers map a `kind` to a short UI string. Visual styling lives
// in styles.css under `.trust-badge[data-kind="..."]`.

import { ExtractedFindings, NoteVersion } from "./api";

export type TrustKind =
  | "manual"
  | "ai-high"
  | "ai-medium"
  | "ai-low"
  | "signed"
  | "external"
  | "draft";

const LABELS: Record<TrustKind, string> = {
  manual:    "Manual",
  "ai-high": "AI · high confidence",
  "ai-medium": "AI · medium",
  "ai-low":  "AI · low",
  signed:    "Signed · immutable",
  external:  "External EHR",
  draft:     "Draft",
};

export function TrustBadge({
  kind,
  label,
  title,
  testId,
}: {
  kind: TrustKind;
  label?: string;
  title?: string;
  testId?: string;
}) {
  return (
    <span
      className="trust-badge"
      data-kind={kind}
      data-testid={testId ?? `trust-badge-${kind}`}
      title={title ?? LABELS[kind]}
    >
      {label ?? LABELS[kind]}
    </span>
  );
}

/**
 * Resolve a `NoteVersion` to its most honest trust kind. The rules
 * are:
 *   - signed / exported  → "signed" (immutable)
 *   - generated_by starts with "manual"  → "manual" (provider-edited)
 *   - top-level extraction confidence on the co-findings (if passed)
 *     → ai-high / ai-medium / ai-low
 *   - otherwise → "draft" (no provenance yet)
 */
export function trustKindForNote(
  note: NoteVersion | null | undefined,
  findings?: ExtractedFindings | null
): TrustKind {
  if (!note) return "draft";
  if (note.draft_status === "signed" || note.draft_status === "exported") {
    return "signed";
  }
  const src = (note.generated_by || "").toLowerCase();
  if (src.startsWith("manual") || note.draft_status === "revised") {
    return "manual";
  }
  const conf = findings?.extraction_confidence?.toLowerCase?.() || "";
  if (conf === "high") return "ai-high";
  if (conf === "medium") return "ai-medium";
  if (conf === "low") return "ai-low";
  return "draft";
}
