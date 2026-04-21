// ROI wave 1 · items 1 + 4
//
// ExamSummary — the one-glance summary that sits at the TOP of the
// clinical workspace, before the 3-tier transcript/findings/draft
// layout. It reuses the data already fetched for NoteWorkspace:
//
//   - `ExtractedFindings` (chief complaint, laterality hint, VA,
//     IOP, diagnoses, plan, follow-up, extraction_confidence)
//   - `NoteVersion` (missing_data_flags, draft_status)
//
// It does NOT fetch anything new. It presents the
// ophthalmology-shaped structured fields clearly before the
// narrative draft, marks absent fields honestly with "—", and
// flags confidence / missing-data risk visually.
//
// Keeping it intentionally compact — one dense card the doctor's
// eye hits first. Secondary depth lives in the existing tier 2
// (findings) and tier 3 (draft) below.

import { ExtractedFindings, NoteVersion } from "./api";
import { TrustBadge, trustKindForNote } from "./TrustBadge";

interface Props {
  findings: ExtractedFindings | null;
  note: NoteVersion | null;
  patientDisplay: string;
  providerDisplay: string;
}

/** Derive laterality from diagnoses + structured exam keys. Returns
 *  a short string like "OD", "OS", "OU", or "" when unknown. We
 *  deliberately do not guess — absence is surfaced honestly. */
function deriveLaterality(f: ExtractedFindings | null): string {
  if (!f) return "";
  const hits: string[] = [];
  const s = f.structured_json || {};
  const text = [
    f.chief_complaint,
    f.hpi_summary,
    ...(Array.isArray(s.diagnoses) ? (s.diagnoses as string[]) : []),
    typeof s.assessment === "string" ? (s.assessment as string) : "",
    typeof s.plan === "string" ? (s.plan as string) : "",
  ]
    .filter(Boolean)
    .join(" ");
  const lower = text.toLowerCase();
  const hasOD = /\bod\b|right eye/.test(lower);
  const hasOS = /\bos\b|left eye/.test(lower);
  const hasOU = /\bou\b|both eyes|bilateral/.test(lower);
  if (hasOU) hits.push("OU");
  else {
    if (hasOD) hits.push("OD");
    if (hasOS) hits.push("OS");
  }
  return hits.join(" · ");
}

function renderValue(v: string | null | undefined): React.ReactNode {
  if (v == null || v === "") return <span className="exam-summary__absent">—</span>;
  return <span>{v}</span>;
}

function confidenceTone(f: ExtractedFindings | null): "high" | "medium" | "low" | "unknown" {
  const c = f?.extraction_confidence;
  if (c === "high" || c === "medium" || c === "low") return c;
  return "unknown";
}

export function ExamSummary({ findings, note, patientDisplay, providerDisplay }: Props) {
  const s = (findings?.structured_json || {}) as Record<string, unknown>;
  const diagnoses = Array.isArray(s.diagnoses) ? (s.diagnoses as string[]) : [];
  const plan = typeof s.plan === "string" ? (s.plan as string) : "";
  const followUp =
    typeof s.follow_up_interval === "string"
      ? (s.follow_up_interval as string)
      : "";
  const laterality = deriveLaterality(findings);
  const conf = confidenceTone(findings);
  const missing = note?.missing_data_flags ?? [];

  // Ophthalmology-shaped segments. Surface any structured_json keys
  // the generator emits for anterior / posterior / other subspecialty
  // blocks. Render "—" honestly when absent.
  const segKeys: { key: string; label: string }[] = [
    { key: "anterior_segment", label: "Anterior segment" },
    { key: "posterior_segment", label: "Posterior segment" },
    { key: "lens", label: "Lens" },
    { key: "dfe", label: "DFE" },
    { key: "oct", label: "OCT" },
    { key: "refraction", label: "Refraction" },
    { key: "pupils", label: "Pupils" },
    { key: "motility", label: "Motility / EOM" },
    { key: "external", label: "External / lids" },
  ];
  const segments = segKeys
    .map((s_) => {
      const raw = s[s_.key];
      if (raw == null) return null;
      const text =
        typeof raw === "string"
          ? raw
          : Array.isArray(raw)
          ? (raw as unknown[]).filter(Boolean).join("; ")
          : typeof raw === "object"
          ? JSON.stringify(raw)
          : String(raw);
      return { ...s_, value: text };
    })
    .filter(Boolean) as { key: string; label: string; value: string }[];

  return (
    <section
      className="exam-summary"
      data-testid="exam-summary"
      aria-label="One-glance exam summary"
    >
      <header className="exam-summary__head">
        <div>
          <h3 data-testid="exam-summary-patient">{patientDisplay}</h3>
          <div className="exam-summary__sub">
            {providerDisplay}
            {laterality && (
              <>
                {" · "}
                <span className="exam-summary__lat" data-testid="exam-summary-lat">
                  {laterality}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="exam-summary__badges">
          <span
            className="trust-badge"
            data-kind={
              conf === "high"
                ? "ai-high"
                : conf === "low"
                ? "ai-low"
                : conf === "medium"
                ? "ai-medium"
                : "draft"
            }
            data-testid="exam-summary-confidence"
            title={`Extraction confidence: ${conf}`}
          >
            Confidence · {conf}
          </span>
          {missing.length > 0 && (
            <span
              className="trust-badge"
              data-kind="ai-low"
              data-testid="exam-summary-missing"
              title={`Missing data: ${missing.join(", ")}`}
            >
              Missing · {missing.length}
            </span>
          )}
          {note && (
            <TrustBadge
              kind={trustKindForNote(note, findings)}
              label={`Draft · v${note.version_number}`}
              testId="exam-summary-draft-kind"
            />
          )}
        </div>
      </header>

      {!findings && (
        <div className="exam-summary__absent-note" data-testid="exam-summary-empty">
          No findings extracted yet — ingest and process a transcript to
          populate this summary.
        </div>
      )}

      {findings && (
        <>
          <dl className="exam-summary__grid">
            <div>
              <dt>Chief complaint</dt>
              <dd data-testid="exam-summary-cc">
                {renderValue(findings.chief_complaint)}
              </dd>
            </div>
            <div>
              <dt>HPI</dt>
              <dd data-testid="exam-summary-hpi">
                {renderValue(findings.hpi_summary)}
              </dd>
            </div>
            <div>
              <dt>VA OD / OS</dt>
              <dd data-testid="exam-summary-va">
                {renderValue(findings.visual_acuity_od)}
                {" / "}
                {renderValue(findings.visual_acuity_os)}
              </dd>
            </div>
            <div>
              <dt>IOP OD / OS</dt>
              <dd data-testid="exam-summary-iop">
                {renderValue(findings.iop_od)}
                {" / "}
                {renderValue(findings.iop_os)}
              </dd>
            </div>
            <div className="exam-summary__grid-wide">
              <dt>Diagnoses</dt>
              <dd data-testid="exam-summary-dx">
                {diagnoses.length
                  ? diagnoses.join("; ")
                  : renderValue(null)}
              </dd>
            </div>
            <div className="exam-summary__grid-wide">
              <dt>Plan</dt>
              <dd data-testid="exam-summary-plan">
                {renderValue(plan)}
              </dd>
            </div>
            <div>
              <dt>Follow-up</dt>
              <dd data-testid="exam-summary-followup">
                {renderValue(followUp)}
              </dd>
            </div>
          </dl>

          {segments.length > 0 && (
            <div
              className="exam-summary__segments"
              data-testid="exam-summary-segments"
              aria-label="Ophthalmology structured exam"
            >
              <h4>Structured exam</h4>
              <dl>
                {segments.map((s_) => (
                  <div key={s_.key} data-testid={`exam-summary-seg-${s_.key}`}>
                    <dt>{s_.label}</dt>
                    <dd>{renderValue(s_.value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </>
      )}
    </section>
  );
}
