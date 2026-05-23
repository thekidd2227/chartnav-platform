import React, { useEffect, useState } from "react";
import type {
  AmbientDraftPayload,
  ScribeSessionResponse,
  ScribeSessionWithAmbientDraft,
  ScribeStatus,
} from "./ambientTypes";
import {
  createScribeSession,
  draftAmbientSession,
  finalizeScribeSession,
  getScribeSession,
  listScribeSessions,
  reviewScribeSession,
} from "./ambientApi";

interface Props {
  patientId: number;
  encounterId?: number;
}

function ambientStatusLabel(status: ScribeStatus): string {
  if (status === "finalized") return "Signed · Locked";
  if (status === "reviewed") return "Reviewed";
  if (status === "ready_for_review") return "Ready for Review";
  if (status === "processing") return "Processing";
  if (status === "discarded") return "Discarded";
  return "Draft";
}

function ambientStatusPillStyle(status: ScribeStatus): React.CSSProperties {
  if (status === "finalized")
    return { background: "#c6f6d5", color: "#276749" };
  if (status === "reviewed")
    return { background: "#bee3f8", color: "#2a4a7f" };
  if (status === "ready_for_review")
    return { background: "#fed7aa", color: "#7c2d12" };
  return { background: "#fed7d7", color: "#9b2c2c" };
}

const DEMO_SAMPLE_TRANSCRIPT =
  "Demo transcript only. Patient reports blurry vision in the right " +
  "eye for two weeks. Visual acuity was stated as 20/40 OD and 20/25 OS. " +
  "IOP was stated as 18 OD and 16 OS. OCT macula metadata is available " +
  "for review. Provider discussed follow-up but no treatment order is " +
  "being placed in this demo.";

function btn(
  bg: string,
  disabled = false,
): React.CSSProperties {
  return {
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "8px 16px",
    fontSize: 13,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 600,
    opacity: disabled ? 0.5 : 1,
  };
}

function StatusTimeline({
  status,
}: {
  status: ScribeSessionResponse["status"];
}) {
  const steps: Array<{
    key: ScribeSessionResponse["status"];
    label: string;
    active: boolean;
  }> = [
    { key: "draft", label: "Draft", active: true },
    {
      key: "ready_for_review",
      label: "Ready for Review",
      active: status !== "draft" && status !== "processing",
    },
    {
      key: "reviewed",
      label: "Reviewed",
      active: status === "reviewed" || status === "finalized",
    },
    { key: "finalized", label: "Signed", active: status === "finalized" },
  ];

  return (
    <div
      data-testid="ambient-status-timeline"
      style={{
        display: "flex",
        gap: 4,
        alignItems: "center",
        flexWrap: "wrap",
        marginBottom: 12,
      }}
    >
      {steps.map((s, i) => (
        <React.Fragment key={s.key}>
          <span
            data-testid={`ambient-status-step-${s.key}`}
            data-active={s.active ? "true" : "false"}
            style={{
              padding: "2px 10px",
              borderRadius: 12,
              fontSize: 11,
              fontWeight: 700,
              background: s.active
                ? s.key === "finalized"
                  ? "#c6f6d5"
                  : s.key === "reviewed"
                    ? "#bee3f8"
                    : s.key === "ready_for_review"
                      ? "#fed7aa"
                      : "#fed7d7"
                : "#edf2f7",
              color: s.active
                ? s.key === "finalized"
                  ? "#276749"
                  : s.key === "reviewed"
                    ? "#2a4a7f"
                    : s.key === "ready_for_review"
                      ? "#7c2d12"
                      : "#9b2c2c"
                : "#a0aec0",
              letterSpacing: 0.3,
              textTransform: "uppercase",
            }}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <span
              aria-hidden
              style={{ width: 12, height: 1, background: "#cbd5e0" }}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

function ForbiddenActionsList({
  forbidden,
}: {
  forbidden: AmbientDraftPayload["forbidden_actions"];
}) {
  const labels: Record<keyof AmbientDraftPayload["forbidden_actions"], string> = {
    diagnosis: "diagnosis",
    orders: "orders",
    referrals: "referrals",
    patient_message: "patient messages",
    billing_or_coding: "billing or coding",
    auto_sign: "auto-sign",
    image_interpretation: "image interpretation",
  };
  return (
    <ul
      data-testid="ambient-forbidden-actions"
      style={{
        margin: "4px 0 0 0",
        paddingLeft: 16,
        fontSize: 11,
        color: "#4a5568",
      }}
    >
      {(Object.entries(forbidden) as Array<
        [keyof AmbientDraftPayload["forbidden_actions"], boolean]
      >).map(([key, value]) => (
        <li key={key} data-testid={`ambient-forbidden-${key}`}>
          ChartNav did not perform {labels[key]} ({String(value)}).
        </li>
      ))}
    </ul>
  );
}

export function AmbientDocumentationPanel({
  patientId,
  encounterId,
}: Props) {
  const [sessions, setSessions] = useState<ScribeSessionResponse[]>([]);
  const [selectedSession, setSelectedSession] =
    useState<ScribeSessionWithAmbientDraft | null>(null);
  const [transcriptText, setTranscriptText] = useState("");
  const [loadingList, setLoadingList] = useState(true);
  const [loadingGen, setLoadingGen] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attested, setAttested] = useState(false);

  useEffect(() => {
    setLoadingList(true);
    listScribeSessions(patientId)
      .then(setSessions)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingList(false));
  }, [patientId]);

  useEffect(() => {
    setAttested(false);
  }, [selectedSession?.id]);

  async function handleGenerate() {
    if (!transcriptText.trim()) return;
    setLoadingGen(true);
    setError(null);
    try {
      const session = await createScribeSession(patientId, {
        input_mode: "transcript",
        transcript_text: transcriptText,
        encounter_id: encounterId,
      });
      const drafted = await draftAmbientSession(patientId, session.id, {
        fake_data_context: true,
      });
      setSessions((prev) => [drafted, ...prev]);
      setSelectedSession(drafted);
      setTranscriptText("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoadingGen(false);
    }
  }

  async function handleSelect(id: number) {
    try {
      const sess = await getScribeSession(patientId, id);
      setSelectedSession(sess);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load session");
    }
  }

  async function handleReview() {
    if (!selectedSession) return;
    setLoadingAction(true);
    setError(null);
    try {
      const updated = await reviewScribeSession(
        patientId,
        selectedSession.id,
        {},
      );
      const merged: ScribeSessionWithAmbientDraft = {
        ...updated,
        ambient_draft: selectedSession.ambient_draft,
      };
      setSelectedSession(merged);
      setSessions((prev) =>
        prev.map((s) => (s.id === updated.id ? merged : s)),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleSign() {
    if (!selectedSession || !attested) return;
    setLoadingAction(true);
    setError(null);
    try {
      const updated = await finalizeScribeSession(
        patientId,
        selectedSession.id,
      );
      const merged: ScribeSessionWithAmbientDraft = {
        ...updated,
        ambient_draft: selectedSession.ambient_draft,
      };
      setSelectedSession(merged);
      setSessions((prev) =>
        prev.map((s) => (s.id === updated.id ? merged : s)),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign failed");
    } finally {
      setLoadingAction(false);
    }
  }

  function loadSample() {
    setTranscriptText(DEMO_SAMPLE_TRANSCRIPT);
  }

  const draft = selectedSession?.ambient_draft;
  const status = selectedSession?.status;
  const isSigned = status === "finalized";
  const isReviewed = status === "reviewed" || isSigned;
  const isReadyForReview = status === "ready_for_review" || isReviewed;

  return (
    <div
      data-testid="ambient-documentation-panel"
      style={{ fontFamily: "sans-serif", padding: 16 }}
    >
      <div style={{ marginBottom: 12 }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#2d3748" }}>
          Provider-Reviewed Ambient Documentation Assist
        </h3>
        <p
          data-testid="ambient-safety-banner"
          style={{
            margin: 0,
            fontSize: 12,
            color: "#4a5568",
            lineHeight: 1.5,
          }}
        >
          Draft from fake/demo encounter transcript. Provider review
          required. Does not diagnose. Does not place orders. Does not
          send referrals or patient messages. Does not bill or code.
          Not for real PHI.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          alignItems: "flex-start",
        }}
      >
        <div style={{ flex: "1 1 320px", minWidth: 280 }}>
          <div
            style={{
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              padding: 14,
            }}
          >
            <p
              style={{
                fontWeight: 600,
                fontSize: 13,
                marginBottom: 8,
                color: "#4a5568",
              }}
            >
              Paste a fake / demo encounter transcript
            </p>

            <textarea
              id="ambient-transcript-text"
              rows={6}
              value={transcriptText}
              onChange={(e) => setTranscriptText(e.target.value)}
              placeholder="Paste a fake / demo transcript. Do not paste real PHI."
              data-testid="ambient-transcript-text"
              style={{
                display: "block",
                width: "100%",
                fontSize: 13,
                padding: 8,
                borderRadius: 4,
                border: "1px solid #cbd5e0",
                boxSizing: "border-box",
              }}
            />

            <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
              <button
                type="button"
                onClick={loadSample}
                data-testid="ambient-sample-btn"
                style={{
                  fontSize: 11,
                  padding: "4px 10px",
                  borderRadius: 999,
                  border: "1px solid #cbd5e0",
                  background: "#fff",
                  color: "#4a5568",
                  cursor: "pointer",
                }}
              >
                Load demo sample (fake data)
              </button>
            </div>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={loadingGen || !transcriptText.trim()}
              data-testid="ambient-generate-btn"
              style={{
                ...btn("#3182ce", loadingGen || !transcriptText.trim()),
                marginTop: 12,
              }}
            >
              {loadingGen
                ? "Generating…"
                : "Generate provider-review draft"}
            </button>
          </div>

          <div style={{ marginTop: 16 }}>
            <p
              style={{
                fontWeight: 600,
                fontSize: 11,
                color: "#718096",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Saved sessions
            </p>
            {loadingList ? (
              <p
                data-testid="ambient-list-loading"
                style={{ fontSize: 12, color: "#a0aec0" }}
              >
                Loading…
              </p>
            ) : sessions.length === 0 ? (
              <p
                data-testid="ambient-list-empty"
                style={{ fontSize: 12, color: "#a0aec0" }}
              >
                No sessions yet. Paste a fake / demo transcript above to
                generate a provider-review draft.
              </p>
            ) : (
              <ul
                data-testid="ambient-list"
                style={{ listStyle: "none", padding: 0, margin: 0 }}
              >
                {sessions.map((s) => (
                  <li
                    key={s.id}
                    onClick={() => handleSelect(s.id)}
                    data-testid={`ambient-list-item-${s.id}`}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 6,
                      cursor: "pointer",
                      background:
                        selectedSession?.id === s.id
                          ? "#ebf8ff"
                          : "transparent",
                      border:
                        selectedSession?.id === s.id
                          ? "1px solid #bee3f8"
                          : "1px solid transparent",
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "baseline",
                        justifyContent: "space-between",
                        gap: 6,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#2d3748",
                        }}
                      >
                        Session #{s.id}
                      </span>
                      <span
                        data-testid={`ambient-list-status-${s.id}`}
                        style={{
                          ...ambientStatusPillStyle(s.status),
                          padding: "1px 6px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          letterSpacing: 0.3,
                          textTransform: "uppercase",
                        }}
                      >
                        {ambientStatusLabel(s.status)}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: "#718096", marginTop: 2 }}>
                      <time
                        dateTime={s.created_at ?? ""}
                        title={
                          s.created_at
                            ? new Date(s.created_at).toLocaleString()
                            : ""
                        }
                      >
                        {s.created_at
                          ? new Date(s.created_at).toLocaleDateString()
                          : ""}
                      </time>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div
          data-testid="ambient-draft-column"
          style={{ flex: "2 1 380px", minWidth: 320 }}
        >
          {error && (
            <p
              data-testid="ambient-error"
              style={{
                color: "#c53030",
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
          {selectedSession ? (
            <div data-testid="ambient-draft-editor">
              <StatusTimeline status={selectedSession.status} />

              {!isSigned && (
                <div
                  data-testid="ambient-awaiting-review"
                  style={{
                    background: "#ebf8ff",
                    border: "1px solid #bee3f8",
                    borderRadius: 6,
                    padding: 10,
                    marginBottom: 12,
                    fontSize: 12,
                    color: "#2a4a7f",
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Awaiting provider review.</strong> ChartNav
                  drafted this note from a demo transcript. The provider
                  reviews, then signs to lock the draft. Not a diagnosis.
                  Does not produce notes without provider review.
                </div>
              )}

              {draft && (
                <>
                  <div
                    data-testid="ambient-structured-facts"
                    style={{
                      background: "#f7fafc",
                      border: "1px solid #e2e8f0",
                      borderRadius: 6,
                      padding: 12,
                      marginBottom: 12,
                    }}
                  >
                    <p
                      style={{
                        margin: "0 0 8px",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#4a5568",
                        textTransform: "uppercase",
                        letterSpacing: 0.4,
                      }}
                    >
                      Structured facts
                    </p>
                    <dl style={{ margin: 0, fontSize: 12 }}>
                      {(
                        [
                          ["chief_complaint", "Chief complaint"],
                          ["hpi_summary", "HPI summary"],
                          ["visual_acuity", "Visual acuity"],
                          ["iop", "Intraocular pressure"],
                          ["imaging_metadata", "Imaging metadata"],
                          ["assessment_context", "Assessment context"],
                          ["plan_as_stated", "Plan as stated"],
                        ] as const
                      ).map(([key, label]) => (
                        <div
                          key={key}
                          style={{ marginBottom: 4 }}
                          data-testid={`ambient-fact-${key}`}
                        >
                          <dt
                            style={{
                              fontWeight: 600,
                              color: "#2d3748",
                              display: "inline",
                            }}
                          >
                            {label}:
                          </dt>{" "}
                          <dd
                            style={{
                              margin: 0,
                              display: "inline",
                              color: "#4a5568",
                            }}
                          >
                            {draft.structured_facts[key]}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>

                  <div
                    data-testid="ambient-safety-flags"
                    style={{
                      background:
                        draft.safety_flags.length > 0 ? "#fffbf0" : "#f7fafc",
                      border:
                        draft.safety_flags.length > 0
                          ? "1px solid #f6d860"
                          : "1px solid #e2e8f0",
                      borderRadius: 6,
                      padding: 10,
                      marginBottom: 12,
                    }}
                  >
                    <p
                      style={{
                        fontWeight: 600,
                        fontSize: 12,
                        color:
                          draft.safety_flags.length > 0 ? "#744210" : "#4a5568",
                        margin: "0 0 4px",
                      }}
                    >
                      Safety flags
                    </p>
                    {draft.safety_flags.length > 0 ? (
                      <ul style={{ margin: 0, paddingLeft: 16 }}>
                        {draft.safety_flags.map((f, i) => (
                          <li
                            key={i}
                            data-testid={`ambient-safety-flag-${i}`}
                            style={{ fontSize: 12, color: "#744210" }}
                          >
                            {f}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p
                        data-testid="ambient-safety-flags-empty"
                        style={{ fontSize: 12, color: "#718096", margin: 0 }}
                      >
                        No safety flags. Provider must still review before signing.
                      </p>
                    )}
                  </div>

                  <div
                    data-testid="ambient-missing-info"
                    style={{
                      background:
                        draft.missing_information.length > 0
                          ? "#fff5f5"
                          : "#f7fafc",
                      border:
                        draft.missing_information.length > 0
                          ? "1px solid #fed7d7"
                          : "1px solid #e2e8f0",
                      borderRadius: 6,
                      padding: 10,
                      marginBottom: 12,
                    }}
                  >
                    <p
                      style={{
                        fontWeight: 600,
                        fontSize: 12,
                        color:
                          draft.missing_information.length > 0
                            ? "#9b2c2c"
                            : "#4a5568",
                        margin: "0 0 4px",
                      }}
                    >
                      Missing information
                    </p>
                    {draft.missing_information.length > 0 ? (
                      <ul style={{ margin: 0, paddingLeft: 16 }}>
                        {draft.missing_information.map((f, i) => (
                          <li
                            key={i}
                            data-testid={`ambient-missing-item-${i}`}
                            style={{ fontSize: 12, color: "#9b2c2c" }}
                          >
                            {f}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p
                        data-testid="ambient-missing-info-empty"
                        style={{ fontSize: 12, color: "#718096", margin: 0 }}
                      >
                        No missing-information flags from the parser.
                      </p>
                    )}
                  </div>

                  <details
                    data-testid="ambient-draft-text"
                    style={{
                      background: "#fff",
                      border: "1px solid #e2e8f0",
                      borderRadius: 6,
                      padding: 10,
                      marginBottom: 12,
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
                      Draft note text (provider editable)
                    </summary>
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        wordWrap: "break-word",
                        fontSize: 12,
                        color: "#2d3748",
                        margin: "8px 0 0",
                      }}
                    >
                      {draft.draft_note}
                    </pre>
                  </details>

                  <div
                    data-testid="ambient-actions-summary"
                    style={{
                      background: "#edf2f7",
                      border: "1px solid #cbd5e0",
                      borderRadius: 6,
                      padding: 10,
                      marginBottom: 12,
                    }}
                  >
                    <p
                      style={{
                        fontWeight: 600,
                        fontSize: 12,
                        color: "#4a5568",
                        margin: "0 0 4px",
                      }}
                    >
                      What ChartNav did NOT do
                    </p>
                    <ForbiddenActionsList forbidden={draft.forbidden_actions} />
                  </div>
                </>
              )}

              {isSigned ? (
                <div
                  data-testid="ambient-signed-lock"
                  style={{
                    marginTop: 12,
                    padding: 12,
                    background: "#f0fff4",
                    border: "1px solid #9ae6b4",
                    borderRadius: 6,
                  }}
                >
                  <p
                    style={{
                      margin: "0 0 4px",
                      fontSize: 13,
                      fontWeight: 600,
                      color: "#276749",
                    }}
                  >
                    Draft signed · locked
                  </p>
                  <p
                    style={{
                      margin: 0,
                      fontSize: 12,
                      color: "#22543d",
                      lineHeight: 1.5,
                    }}
                    data-testid="ambient-signed-meta"
                  >
                    Signed{" "}
                    {selectedSession.finalized_at
                      ? new Date(selectedSession.finalized_at).toLocaleString()
                      : ""}
                    . Signed drafts are immutable.
                  </p>
                  {selectedSession.reviewed_at &&
                    selectedSession.reviewed_by_user_id !== null && (
                      <p
                        style={{
                          margin: "4px 0 0",
                          fontSize: 12,
                          color: "#22543d",
                          lineHeight: 1.5,
                        }}
                        data-testid="ambient-signed-reviewer"
                      >
                        Reviewed{" "}
                        {new Date(
                          selectedSession.reviewed_at,
                        ).toLocaleString()}{" "}
                        by clinician #{selectedSession.reviewed_by_user_id}.
                      </p>
                    )}
                  <p
                    style={{
                      margin: "8px 0 0",
                      fontSize: 11,
                      color: "#38a169",
                      lineHeight: 1.5,
                    }}
                    data-testid="ambient-audit-note"
                  >
                    ChartNav records metadata-only audit events: who
                    created, reviewed, and signed, and when. The audit
                    trail does not store clinical free text.
                  </p>
                </div>
              ) : (
                <div style={{ marginTop: 12 }}>
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap",
                      marginBottom: 12,
                    }}
                  >
                    <button
                      type="button"
                      onClick={handleReview}
                      disabled={
                        loadingAction || !isReadyForReview || isReviewed
                      }
                      data-testid="ambient-review-btn"
                      style={btn(
                        "#38a169",
                        loadingAction || !isReadyForReview || isReviewed,
                      )}
                    >
                      {loadingAction
                        ? "…"
                        : isReviewed
                          ? "Reviewed"
                          : "Mark Reviewed"}
                    </button>
                  </div>

                  {isReviewed && (
                    <div
                      data-testid="ambient-attestation-block"
                      style={{
                        background: "#faf5ff",
                        border: "1px solid #d6bcfa",
                        borderRadius: 6,
                        padding: 12,
                      }}
                    >
                      <label
                        style={{
                          display: "flex",
                          gap: 8,
                          fontSize: 12,
                          color: "#44337a",
                          cursor: "pointer",
                          lineHeight: 1.5,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={attested}
                          onChange={(e) => setAttested(e.target.checked)}
                          data-testid="ambient-attestation-checkbox"
                          style={{ marginTop: 3 }}
                        />
                        <span>
                          I attest that I have reviewed this draft note
                          and it accurately reflects my clinical findings
                          from the fake / demo transcript. Signing will
                          lock the draft — signed drafts are immutable.
                        </span>
                      </label>
                      <button
                        type="button"
                        onClick={handleSign}
                        disabled={loadingAction || !attested}
                        data-testid="ambient-sign-btn"
                        style={{
                          ...btn("#805ad5", loadingAction || !attested),
                          marginTop: 10,
                        }}
                      >
                        {loadingAction ? "…" : "Sign & Lock Draft"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div
              data-testid="ambient-draft-empty"
              style={{
                color: "#718096",
                fontSize: 13,
                padding: 24,
                border: "1px dashed #cbd5e0",
                borderRadius: 8,
                textAlign: "center",
                background: "#fafbfc",
              }}
            >
              <p style={{ margin: "0 0 6px", fontWeight: 600 }}>
                No draft selected
              </p>
              <p style={{ margin: 0, fontSize: 12 }}>
                Paste a fake / demo transcript on the left or pick a saved
                session to view a provider-review draft here. ChartNav drafts
                from clinician-entered text — the provider reviews and signs.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
