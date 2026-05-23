import React, { useEffect, useState } from "react";
import type { VitalsWorkup } from "./vitalsTypes";
import {
  createVitalsWorkup,
  getVitalsWorkup,
  listVitalsWorkups,
  reviewVitalsWorkup,
  signVitalsWorkup,
  updateVitalsWorkup,
} from "./vitalsApi";
import {
  DEMO_FAKE_VITALS,
  type FormState,
  VitalsWorkupForm,
  vitalsFromWorkup,
} from "./VitalsWorkupForm";
import {
  AwaitingReviewCallout,
  ForbiddenActionsCard,
  SignedLockBanner,
  StatusTimeline,
  vitalsStatusLabel,
  vitalsStatusPillStyle,
  WarningsList,
} from "./VitalsWorkupSummary";

interface Props {
  encounterId: number;
}

const EMPTY_FORM: FormState = {
  source_type: "technician_entry",
  temperature_unit: "F",
  height_unit: "in",
  weight_unit: "lb",
  allergies_reviewed: false,
  medications_reviewed: false,
};

function btn(bg: string, disabled = false): React.CSSProperties {
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

export function VitalsWorkupPanel({ encounterId }: Props) {
  const [workups, setWorkups] = useState<VitalsWorkup[]>([]);
  const [selected, setSelected] = useState<VitalsWorkup | null>(null);
  const [formState, setFormState] = useState<FormState>(EMPTY_FORM);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingAction, setLoadingAction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attested, setAttested] = useState(false);

  useEffect(() => {
    setLoadingList(true);
    listVitalsWorkups(encounterId)
      .then((rows) => {
        setWorkups(rows);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingList(false));
  }, [encounterId]);

  useEffect(() => {
    setAttested(false);
    if (selected) {
      setFormState(vitalsFromWorkup(selected));
    } else {
      setFormState(EMPTY_FORM);
    }
  }, [selected?.id]);

  const isSigned = selected?.status === "signed";
  const isReviewed = selected?.status === "reviewed";
  const isEntered = selected?.status === "entered";
  const isDraft = selected?.status === "draft";

  async function handleCreate() {
    setLoadingAction(true);
    setError(null);
    try {
      const created = await createVitalsWorkup(encounterId, formState);
      setWorkups((prev) => [created, ...prev]);
      setSelected(created);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleSaveAndAdvance() {
    if (!selected) return;
    setLoadingAction(true);
    setError(null);
    try {
      const updated = await updateVitalsWorkup(selected.id, {
        ...formState,
        advance_to_entered: isDraft,
      });
      setSelected(updated);
      setWorkups((prev) =>
        prev.map((w) => (w.id === updated.id ? updated : w)),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleReview() {
    if (!selected) return;
    setLoadingAction(true);
    setError(null);
    try {
      const updated = await reviewVitalsWorkup(selected.id);
      setSelected(updated);
      setWorkups((prev) =>
        prev.map((w) => (w.id === updated.id ? updated : w)),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleSign() {
    if (!selected || !attested) return;
    setLoadingAction(true);
    setError(null);
    try {
      const updated = await signVitalsWorkup(selected.id, {
        attested: true,
      });
      setSelected(updated);
      setWorkups((prev) =>
        prev.map((w) => (w.id === updated.id ? updated : w)),
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign failed");
    } finally {
      setLoadingAction(false);
    }
  }

  function loadDemoSample() {
    setSelected(null);
    setFormState({ ...DEMO_FAKE_VITALS });
  }

  return (
    <div
      data-testid="vitals-workup-panel"
      style={{ fontFamily: "sans-serif", padding: 16 }}
    >
      <div style={{ marginBottom: 12 }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#2d3748" }}>
          Technician Workup &amp; Vitals
        </h3>
        <p
          data-testid="vitals-safety-banner"
          style={{
            margin: 0,
            fontSize: 12,
            color: "#4a5568",
            lineHeight: 1.5,
          }}
        >
          Structured intake for provider review. Does not diagnose. Does
          not recommend treatment. Does not place orders. Does not send
          referrals or patient messages. Does not bill or code. Not for
          real PHI. No device integration.
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
        <div style={{ flex: "1 1 240px", minWidth: 220 }}>
          <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                setFormState({ ...EMPTY_FORM });
              }}
              data-testid="vitals-new-btn"
              style={btn("#3182ce")}
            >
              New workup
            </button>
            <button
              type="button"
              onClick={loadDemoSample}
              data-testid="vitals-demo-sample-btn"
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
              Load fake demo vitals
            </button>
          </div>

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
            Saved workups
          </p>
          {loadingList ? (
            <p
              data-testid="vitals-list-loading"
              style={{ fontSize: 12, color: "#a0aec0" }}
            >
              Loading…
            </p>
          ) : workups.length === 0 ? (
            <p
              data-testid="vitals-list-empty"
              style={{ fontSize: 12, color: "#a0aec0" }}
            >
              No workups yet. Click "New workup" or "Load fake demo
              vitals" to start.
            </p>
          ) : (
            <ul
              data-testid="vitals-list"
              style={{ listStyle: "none", padding: 0, margin: 0 }}
            >
              {workups.map((w) => (
                <li
                  key={w.id}
                  onClick={async () => {
                    try {
                      const full = await getVitalsWorkup(w.id);
                      setSelected(full);
                    } catch (e: unknown) {
                      setError(
                        e instanceof Error ? e.message : "Load failed",
                      );
                    }
                  }}
                  data-testid={`vitals-list-item-${w.id}`}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 6,
                    cursor: "pointer",
                    background:
                      selected?.id === w.id ? "#ebf8ff" : "transparent",
                    border:
                      selected?.id === w.id
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
                      Workup #{w.id}
                    </span>
                    <span
                      data-testid={`vitals-list-status-${w.id}`}
                      style={{
                        ...vitalsStatusPillStyle(w.status),
                        padding: "1px 6px",
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 700,
                        letterSpacing: 0.3,
                        textTransform: "uppercase",
                      }}
                    >
                      {vitalsStatusLabel(w.status)}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: "#718096", marginTop: 2 }}>
                    {w.source_type === "technician_entry"
                      ? "Technician entry"
                      : w.source_type === "clinician_entry"
                        ? "Clinician entry"
                        : w.source_type === "demo"
                          ? "Demo"
                          : "Imported"}{" "}
                    ·{" "}
                    <time
                      dateTime={w.created_at}
                      title={
                        w.created_at
                          ? new Date(w.created_at).toLocaleString()
                          : ""
                      }
                    >
                      {w.created_at
                        ? new Date(w.created_at).toLocaleDateString()
                        : ""}
                    </time>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div
          data-testid="vitals-form-column"
          style={{ flex: "2 1 480px", minWidth: 360 }}
        >
          {error && (
            <p
              data-testid="vitals-error"
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

          {selected && <StatusTimeline status={selected.status} />}

          {selected && !isSigned && !isReviewed && (
            <AwaitingReviewCallout status={selected.status} />
          )}

          {selected && <WarningsList warnings={selected.warnings} />}

          <VitalsWorkupForm
            state={formState}
            onChange={setFormState}
            disabled={isSigned}
          />

          {selected && <ForbiddenActionsCard workup={selected} />}

          {isSigned && selected ? (
            <SignedLockBanner workup={selected} />
          ) : (
            <div style={{ marginTop: 8 }}>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  marginBottom: 12,
                }}
              >
                {!selected && (
                  <button
                    type="button"
                    onClick={handleCreate}
                    disabled={loadingAction}
                    data-testid="vitals-save-draft-btn"
                    style={btn("#3182ce", loadingAction)}
                  >
                    {loadingAction ? "…" : "Save draft"}
                  </button>
                )}
                {selected && !isReviewed && (
                  <button
                    type="button"
                    onClick={handleSaveAndAdvance}
                    disabled={loadingAction}
                    data-testid="vitals-save-advance-btn"
                    style={btn("#3182ce", loadingAction)}
                  >
                    {loadingAction
                      ? "…"
                      : isDraft
                        ? "Save & mark entered"
                        : "Save"}
                  </button>
                )}
                {selected && (isEntered || isReviewed) && (
                  <button
                    type="button"
                    onClick={handleReview}
                    disabled={loadingAction || isReviewed}
                    data-testid="vitals-review-btn"
                    style={btn(
                      "#38a169",
                      loadingAction || isReviewed,
                    )}
                  >
                    {loadingAction
                      ? "…"
                      : isReviewed
                        ? "Reviewed"
                        : "Mark Reviewed"}
                  </button>
                )}
              </div>

              {selected && isReviewed && (
                <div
                  data-testid="vitals-attestation-block"
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
                      data-testid="vitals-attestation-checkbox"
                      style={{ marginTop: 3 }}
                    />
                    <span>
                      I attest that I have reviewed this technician workup
                      and the vitals values are accurate. Signing will
                      lock the workup — signed workups are immutable.
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={handleSign}
                    disabled={loadingAction || !attested}
                    data-testid="vitals-sign-btn"
                    style={{
                      ...btn("#805ad5", loadingAction || !attested),
                      marginTop: 10,
                    }}
                  >
                    {loadingAction ? "…" : "Sign & Lock Workup"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
