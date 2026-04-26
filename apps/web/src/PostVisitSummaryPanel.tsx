// Phase 2 item 5 — In-app panel: generate a post-visit summary from
// a signed note and surface the read-link to staff.
//
// Spec: docs/chartnav/closure/PHASE_B_Minimum_Patient_Portal_and_Post_Visit_Summary.md
//
// Truthful UI: the read-link copy explicitly says "share this link
// with the patient" — we do NOT imply automatic delivery, because no
// real outbound channel is wired in Phase B (delivery uses the
// messaging StubProvider).
import { useState } from "react";
import {
  ApiError,
  PostVisitSummaryGenerateResponse,
  generatePostVisitSummary,
  postVisitSummaryPdfUrl,
  publicSummaryUrl,
} from "./api";

export interface PostVisitSummaryPanelProps {
  identity: string;
  noteVersionId: number | null;
  signed: boolean;
}

export function PostVisitSummaryPanel({
  identity,
  noteVersionId,
  signed,
}: PostVisitSummaryPanelProps) {
  const [out, setOut] = useState<PostVisitSummaryGenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!noteVersionId) {
    return (
      <div className="post-visit-summary-panel" data-testid="post-visit-summary-panel">
        Sign the note first to generate a post-visit summary.
      </div>
    );
  }

  async function onGenerate() {
    if (!noteVersionId) return;
    setBusy(true);
    setError(null);
    try {
      const r = await generatePostVisitSummary(identity, noteVersionId);
      setOut(r);
    } catch (e: unknown) {
      if (e instanceof ApiError) setError(e.reason);
      else setError("Could not generate the summary.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="post-visit-summary-panel" data-testid="post-visit-summary-panel">
      <h3>Post-visit summary</h3>
      <p className="post-visit-summary-panel__hint">
        Generates a one-page plain-language PDF for the patient. The
        read-link is single-device, expires in 30 days, and is not a
        full patient portal.
      </p>
      <button
        className="btn btn--primary"
        disabled={busy || !signed}
        onClick={onGenerate}
        data-testid="generate-summary-btn"
      >
        {signed ? "Generate summary" : "Sign the note first"}
      </button>
      {out && (
        <div className="post-visit-summary-panel__result">
          <p>
            Summary ready. Download the PDF or copy the read-link to
            share with the patient (out-of-band — ChartNav does not
            send the link automatically in Phase B).
          </p>
          <a
            className="btn"
            href={postVisitSummaryPdfUrl(out.id)}
            target="_blank"
            rel="noreferrer"
          >
            Download PDF
          </a>
          {out.read_link_token && (
            <div>
              <code data-testid="summary-read-link">
                {publicSummaryUrl(out.read_link_token)}
              </code>
              <button
                className="btn"
                data-testid="read-link-copy-btn"
                onClick={() => {
                  if (out.read_link_token) {
                    navigator.clipboard?.writeText(
                      publicSummaryUrl(out.read_link_token)
                    );
                  }
                }}
              >
                Copy link
              </button>
            </div>
          )}
          <p>Expires: {out.expires_at}</p>
        </div>
      )}
      {error && <div role="alert">{error}</div>}
    </div>
  );
}
