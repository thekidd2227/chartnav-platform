// Phase 85 — Medication Safety & Adherence Panel.
//
// Read + record surface for provider-entered medication safety.
// Refill-gap pills, preservative-burden counter, polypharmacy
// counter, and allergy-match callouts are deterministic projections
// of provider-entered rows. ChartNav does not prescribe, refill,
// dose, recommend medication changes, contact the pharmacy, or
// perform autonomous drug-interaction checking beyond a literal
// substring match against the provider-entered allergy list.

import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getMedications,
  patchMedicationDiscontinue,
  postAllergy,
  postMedication,
  postRefill,
} from "./medicationsApi";
import type {
  AllergySeverity,
  MedicationClass,
  MedicationLaterality,
  MedicationRecord,
  MedicationRoute,
  MedicationsPanelResponse,
  ReactionType,
  RefillGapStatus,
} from "./medicationsTypes";

interface Props {
  patientId: number;
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
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

function refillGapTone(status: RefillGapStatus): Tone {
  if (status === "on_track") return "green";
  if (status === "gap") return "amber";
  return "neutral";
}

function refillGapLabel(
  status: RefillGapStatus,
  gapDays: number | null,
): string {
  if (status === "on_track") return "On track";
  if (status === "gap")
    return gapDays !== null ? `Refill gap · ${gapDays}d` : "Refill gap";
  if (status === "discontinued") return "Discontinued";
  return "No refill history";
}

export function MedicationSafetyPanel({ patientId, encounterId }: Props) {
  const [data, setData] = useState<MedicationsPanelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Medication form
  const [medName, setMedName] = useState("");
  const [medClass, setMedClass] = useState<MedicationClass>("pgf2_analog");
  const [medRoute, setMedRoute] = useState<MedicationRoute>("drops");
  const [medLat, setMedLat] = useState<MedicationLaterality>("OU");
  const [medDose, setMedDose] = useState(1);
  const [medPreserved, setMedPreserved] = useState(false);

  // Refill form
  const [refillMedId, setRefillMedId] = useState<number | null>(null);
  const [refillDays, setRefillDays] = useState(30);

  // Allergy form
  const [allergySubstance, setAllergySubstance] = useState("");
  const [allergyReaction, setAllergyReaction] = useState<ReactionType>("rash");
  const [allergySeverity, setAllergySeverity] =
    useState<AllergySeverity>("moderate");

  const fetchPanel = useCallback(() => {
    setLoading(true);
    setError(null);
    getMedications(patientId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [patientId]);

  useEffect(() => {
    fetchPanel();
  }, [fetchPanel]);

  const activeMeds = useMemo(
    () => (data?.medications ?? []).filter((m) => m.is_active),
    [data],
  );

  useEffect(() => {
    if (activeMeds.length > 0 && refillMedId === null) {
      setRefillMedId(activeMeds[0]!.id);
    }
  }, [activeMeds, refillMedId]);

  const onSubmitMedication = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);
      setSubmitting(true);
      try {
        await postMedication(encounterId, {
          medication_name: medName.trim(),
          medication_class: medClass,
          route: medRoute,
          laterality: medLat,
          dose_per_day: medDose,
          preservative_flag: medPreserved,
        });
        setMedName("");
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Medication record failed",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [
      encounterId,
      fetchPanel,
      medClass,
      medDose,
      medLat,
      medName,
      medPreserved,
      medRoute,
    ],
  );

  const onSubmitRefill = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (refillMedId === null) return;
      setSubmitError(null);
      setSubmitting(true);
      try {
        await postRefill(refillMedId, {
          expected_days_supply: refillDays,
        });
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Refill record failed",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [fetchPanel, refillDays, refillMedId],
  );

  const onSubmitAllergy = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);
      setSubmitting(true);
      try {
        await postAllergy(patientId, {
          substance: allergySubstance.trim(),
          reaction_type: allergyReaction,
          severity: allergySeverity,
        });
        setAllergySubstance("");
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Allergy record failed",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [allergyReaction, allergySeverity, allergySubstance, fetchPanel, patientId],
  );

  const onDiscontinue = useCallback(
    async (med: MedicationRecord) => {
      setSubmitError(null);
      try {
        await patchMedicationDiscontinue(med.id);
        fetchPanel();
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Discontinue failed",
        );
      }
    },
    [fetchPanel],
  );

  return (
    <div
      data-testid="medication-safety-panel"
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
          Medication Safety &amp; Adherence
        </h3>
        <button
          type="button"
          onClick={fetchPanel}
          disabled={loading}
          data-testid="medication-refresh-btn"
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
        data-testid="medication-banner"
        style={{
          margin: "0 0 12px",
          fontSize: 12,
          color: "#4a5568",
          lineHeight: 1.5,
        }}
      >
        Provider-entered medication safety surface. ChartNav does not
        prescribe, does not refill, does not dose, does not contact the
        pharmacy, does not recommend medication changes, and does not
        perform autonomous drug-interaction checking. Refill-gap and
        preservative-burden signals are deterministic counts only.
      </p>

      {error && (
        <p
          data-testid="medication-error"
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
          data-testid="medication-loading"
          style={{ fontSize: 12, color: "#4a5568" }}
        >
          Loading…
        </p>
      )}

      {data && (
        <>
          <div
            data-testid="medication-signals"
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginBottom: 12,
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <div
              data-testid="medication-signal-polypharmacy"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Active meds:</strong> {data.signals.polypharmacy_count}
            </div>
            <div
              data-testid="medication-signal-preservative"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Preservative burden:</strong>{" "}
              {data.signals.preservative_burden}
            </div>
            <div
              data-testid="medication-signal-refill-gaps"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Refill gaps:</strong> {data.signals.refill_gaps.length}
            </div>
            <div
              data-testid="medication-signal-allergies"
              style={{
                padding: "6px 10px",
                background: "#edf2f7",
                borderRadius: 6,
              }}
            >
              <strong>Allergies on file:</strong> {data.allergies.length}
            </div>
          </div>

          {data.signals.allergy_matches.length > 0 && (
            <div
              data-testid="medication-allergy-match-callout"
              style={{
                padding: 10,
                background: "#fff5f5",
                border: "1px solid #fed7d7",
                borderRadius: 6,
                fontSize: 12,
                color: "#822727",
                marginBottom: 10,
              }}
            >
              <strong>Allergy substring match</strong> — review the
              provider-entered allergy list against the provider-entered
              medication list. ChartNav does not interpret drug-drug
              interactions; this is a literal name/class match only.
              <ul style={{ margin: "6px 0 0 18px", padding: 0 }}>
                {data.signals.allergy_matches.map((m, idx) => (
                  <li
                    key={`${m.medication_id}-${m.allergy_id}`}
                    data-testid={`medication-allergy-match-${idx}`}
                  >
                    {m.medication_name} ↔ {m.allergy_substance} (
                    {m.allergy_severity})
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.medications.length === 0 ? (
            <p
              data-testid="medication-empty"
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
              No provider-entered medications on file. Medication safety is
              informational and never blocks signing.
            </p>
          ) : (
            <ul
              data-testid="medication-list"
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {data.medications.map((rec) => (
                <li
                  key={rec.id}
                  data-testid={`medication-row-${rec.id}`}
                  style={{
                    padding: 10,
                    background: rec.is_active ? "#fff" : "#f7fafc",
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
                    <strong>{rec.medication_name}</strong>
                    {pill(
                      refillGapLabel(
                        rec.refill_gap.status,
                        rec.refill_gap.gap_days,
                      ),
                      refillGapTone(rec.refill_gap.status),
                      `medication-refill-gap-${rec.id}`,
                    )}
                  </div>
                  <div>
                    <strong>Class:</strong>{" "}
                    <span data-testid={`medication-class-${rec.id}`}>
                      {rec.medication_class_label}
                    </span>{" "}
                    · <strong>Route:</strong> {rec.route} ·{" "}
                    <strong>Laterality:</strong> {rec.laterality}
                  </div>
                  <div>
                    <strong>Dose/day:</strong>{" "}
                    <span data-testid={`medication-dose-${rec.id}`}>
                      {rec.dose_per_day}
                    </span>{" "}
                    · <strong>Preservative:</strong>{" "}
                    <span data-testid={`medication-preservative-${rec.id}`}>
                      {rec.preservative_flag ? "Yes" : "No"}
                    </span>
                  </div>
                  {rec.refill_gap.last_refill_date && (
                    <div data-testid={`medication-last-refill-${rec.id}`}>
                      <strong>Last refill:</strong>{" "}
                      {fmtDate(rec.refill_gap.last_refill_date)}{" "}
                      ({rec.refill_gap.expected_days_supply} day supply)
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: "#4a5568" }}>
                    Recorded by{" "}
                    <span data-testid={`medication-actor-${rec.id}`}>
                      {rec.recorded_by_display_name ?? "Unknown"}
                      {rec.recorded_by_role && ` (${rec.recorded_by_role})`}
                    </span>
                    {rec.is_active ? (
                      <button
                        type="button"
                        onClick={() => onDiscontinue(rec)}
                        data-testid={`medication-discontinue-${rec.id}`}
                        style={{
                          marginLeft: 8,
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 4,
                          border: "1px solid #cbd5e0",
                          background: "#fff",
                          color: "#2d3748",
                          cursor: "pointer",
                        }}
                      >
                        Mark discontinued
                      </button>
                    ) : (
                      <span
                        data-testid={`medication-discontinued-flag-${rec.id}`}
                        style={{ marginLeft: 8, fontStyle: "italic" }}
                      >
                        Discontinued {fmtDate(rec.discontinued_on)}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <form
            data-testid="medication-form"
            onSubmit={onSubmitMedication}
            style={{
              marginTop: 12,
              padding: 10,
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <p
              style={{
                margin: "0 0 6px",
                fontSize: 11,
                fontWeight: 700,
                color: "#4a5568",
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Record provider-entered medication
            </p>
            <label style={{ display: "block", marginBottom: 6 }}>
              Medication name{" "}
              <input
                type="text"
                value={medName}
                onChange={(e) => setMedName(e.target.value)}
                data-testid="medication-name-input"
                maxLength={128}
                style={{ marginLeft: 4 }}
              />
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Class{" "}
              <select
                value={medClass}
                onChange={(e) =>
                  setMedClass(e.target.value as MedicationClass)
                }
                data-testid="medication-class-select"
                style={{ marginLeft: 4 }}
              >
                {data.supported_medication_classes.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Route{" "}
              <select
                value={medRoute}
                onChange={(e) =>
                  setMedRoute(e.target.value as MedicationRoute)
                }
                data-testid="medication-route-select"
                style={{ marginLeft: 4 }}
              >
                {data.supported_routes.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Laterality{" "}
              <select
                value={medLat}
                onChange={(e) =>
                  setMedLat(e.target.value as MedicationLaterality)
                }
                data-testid="medication-laterality-select"
                style={{ marginLeft: 4 }}
              >
                {data.supported_lateralities.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Dose per day{" "}
              <input
                type="number"
                min={0}
                max={24}
                value={medDose}
                onChange={(e) =>
                  setMedDose(Math.max(0, Math.min(24, Number(e.target.value))))
                }
                data-testid="medication-dose-input"
                style={{ marginLeft: 4, width: 64 }}
              />
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              <input
                type="checkbox"
                checked={medPreserved}
                onChange={(e) => setMedPreserved(e.target.checked)}
                data-testid="medication-preservative-checkbox"
                style={{ marginRight: 4 }}
              />
              Preservative present (provider-entered)
            </label>
            <button
              type="submit"
              disabled={submitting || !medName.trim()}
              data-testid="medication-submit-btn"
              style={{
                marginTop: 6,
                padding: "4px 12px",
                borderRadius: 4,
                border: "1px solid #4a5568",
                background: submitting ? "#cbd5e0" : "#1c4532",
                color: "#fff",
                fontSize: 12,
                fontWeight: 600,
                cursor: submitting ? "wait" : "pointer",
              }}
            >
              {submitting ? "Saving…" : "Record medication"}
            </button>
          </form>

          {activeMeds.length > 0 && (
            <form
              data-testid="refill-form"
              onSubmit={onSubmitRefill}
              style={{
                marginTop: 10,
                padding: 10,
                background: "#f7fafc",
                border: "1px solid #e2e8f0",
                borderRadius: 6,
                fontSize: 12,
                color: "#2d3748",
              }}
            >
              <p
                style={{
                  margin: "0 0 6px",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#4a5568",
                  textTransform: "uppercase",
                  letterSpacing: 0.4,
                }}
              >
                Record provider-entered refill
              </p>
              <label style={{ display: "block", marginBottom: 6 }}>
                Medication{" "}
                <select
                  value={refillMedId ?? ""}
                  onChange={(e) => setRefillMedId(Number(e.target.value))}
                  data-testid="refill-medication-select"
                  style={{ marginLeft: 4 }}
                >
                  {activeMeds.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.medication_name}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: "block", marginBottom: 6 }}>
                Expected days supply{" "}
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={refillDays}
                  onChange={(e) =>
                    setRefillDays(
                      Math.max(1, Math.min(365, Number(e.target.value))),
                    )
                  }
                  data-testid="refill-days-input"
                  style={{ marginLeft: 4, width: 64 }}
                />
              </label>
              <button
                type="submit"
                disabled={submitting || refillMedId === null}
                data-testid="refill-submit-btn"
                style={{
                  padding: "4px 12px",
                  borderRadius: 4,
                  border: "1px solid #4a5568",
                  background: submitting ? "#cbd5e0" : "#1c4532",
                  color: "#fff",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: submitting ? "wait" : "pointer",
                }}
              >
                {submitting ? "Saving…" : "Record refill"}
              </button>
            </form>
          )}

          <form
            data-testid="allergy-form"
            onSubmit={onSubmitAllergy}
            style={{
              marginTop: 10,
              padding: 10,
              background: "#f7fafc",
              border: "1px solid #e2e8f0",
              borderRadius: 6,
              fontSize: 12,
              color: "#2d3748",
            }}
          >
            <p
              style={{
                margin: "0 0 6px",
                fontSize: 11,
                fontWeight: 700,
                color: "#4a5568",
                textTransform: "uppercase",
                letterSpacing: 0.4,
              }}
            >
              Record provider-entered allergy
            </p>
            <label style={{ display: "block", marginBottom: 6 }}>
              Substance{" "}
              <input
                type="text"
                value={allergySubstance}
                onChange={(e) => setAllergySubstance(e.target.value)}
                data-testid="allergy-substance-input"
                maxLength={128}
                style={{ marginLeft: 4 }}
              />
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Reaction{" "}
              <select
                value={allergyReaction}
                onChange={(e) =>
                  setAllergyReaction(e.target.value as ReactionType)
                }
                data-testid="allergy-reaction-select"
                style={{ marginLeft: 4 }}
              >
                {data.supported_reaction_types.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "block", marginBottom: 6 }}>
              Severity{" "}
              <select
                value={allergySeverity}
                onChange={(e) =>
                  setAllergySeverity(e.target.value as AllergySeverity)
                }
                data-testid="allergy-severity-select"
                style={{ marginLeft: 4 }}
              >
                {data.supported_severities.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              disabled={submitting || !allergySubstance.trim()}
              data-testid="allergy-submit-btn"
              style={{
                padding: "4px 12px",
                borderRadius: 4,
                border: "1px solid #4a5568",
                background: submitting ? "#cbd5e0" : "#1c4532",
                color: "#fff",
                fontSize: 12,
                fontWeight: 600,
                cursor: submitting ? "wait" : "pointer",
              }}
            >
              {submitting ? "Saving…" : "Record allergy"}
            </button>
          </form>

          {submitError && (
            <p
              data-testid="medication-submit-error"
              style={{
                marginTop: 6,
                padding: 6,
                background: "#fff5f5",
                border: "1px solid #fed7d7",
                borderRadius: 4,
                color: "#822727",
              }}
            >
              {submitError}
            </p>
          )}

          <p
            data-testid="medication-disclosure"
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
