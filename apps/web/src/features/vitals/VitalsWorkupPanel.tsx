import { useEffect, useMemo, useState } from "react";
import {
  createVitalsWorkup,
  getVitalsWorkup,
  listVitalsWorkups,
  reviewVitalsWorkup,
  signVitalsWorkup,
  updateVitalsWorkup,
} from "./vitalsApi";
import { VitalsWorkupForm } from "./VitalsWorkupForm";
import { VitalsWorkupSummary } from "./VitalsWorkupSummary";
import type { VitalWorkup, VitalWorkupPayload } from "./vitalsTypes";

interface Props {
  encounterId: number;
}

const EMPTY_FORM: VitalWorkupPayload = {
  status: "entered",
  source_type: "technician_entry",
  temperature_unit: "F",
  height_unit: "in",
  weight_unit: "lb",
  allergies_reviewed: false,
  medications_reviewed: false,
};

const DEMO_VALUES: VitalWorkupPayload = {
  status: "entered",
  source_type: "demo",
  bp_systolic: 118,
  bp_diastolic: 74,
  bp_position: "sitting",
  bp_site: "left_arm",
  temperature_value: 98.4,
  temperature_unit: "F",
  pulse: 72,
  respiratory_rate: 14,
  oxygen_saturation: 98,
  height_value: 70,
  height_unit: "in",
  weight_value: 175,
  weight_unit: "lb",
  pain_score: 1,
  visual_acuity_od: "20/30",
  visual_acuity_os: "20/25",
  visual_acuity_ou: "20/25",
  iop_od: 16,
  iop_os: 15,
  iop_method: "tonopen",
  dilation_status: "not_dilated",
  allergies_reviewed: true,
  medications_reviewed: true,
  technician_notes: "Fake demo intake values only.",
};

function bmiFor(values: VitalWorkupPayload): number | null {
  const h = values.height_value;
  const w = values.weight_value;
  if (!h || !w || h <= 0 || w <= 0) return null;
  const heightIn = values.height_unit === "cm" ? h / 2.54 : h;
  const weightLb = values.weight_unit === "kg" ? w * 2.2046226218 : w;
  return (weightLb / (heightIn * heightIn)) * 703;
}

function warningsFor(values: VitalWorkupPayload): string[] {
  const warnings: string[] = [];
  if (values.bp_systolic && !values.bp_diastolic) {
    warnings.push("Blood pressure systolic entered without diastolic; provider review required.");
  }
  if (values.bp_diastolic && !values.bp_systolic) {
    warnings.push("Blood pressure diastolic entered without systolic; provider review required.");
  }
  if ((values.bp_systolic || values.bp_diastolic) && !values.bp_site) {
    warnings.push("Blood pressure value entered without site; review required.");
  }
  if ((values.bp_systolic || values.bp_diastolic) && !values.bp_position) {
    warnings.push("Blood pressure value entered without position; review required.");
  }
  if (values.height_value && !values.weight_value) warnings.push("Height entered without weight; review required.");
  if (values.weight_value && !values.height_value) warnings.push("Weight entered without height; review required.");
  if (values.iop_od && !values.iop_os) warnings.push("IOP OD entered without IOP OS; provider review required.");
  if (values.iop_os && !values.iop_od) warnings.push("IOP OS entered without IOP OD; provider review required.");
  if (values.visual_acuity_od && !values.visual_acuity_os) warnings.push("VA OD entered without VA OS; provider review required.");
  if (values.visual_acuity_os && !values.visual_acuity_od) warnings.push("VA OS entered without VA OD; provider review required.");
  if (values.oxygen_saturation !== null && values.oxygen_saturation !== undefined && values.oxygen_saturation < 92) {
    warnings.push("Oxygen saturation is outside expected review range; provider review required.");
  }
  if (values.temperature_value !== null && values.temperature_value !== undefined) {
    const temp = values.temperature_value;
    const out = values.temperature_unit === "C" ? temp < 35 || temp > 38 : temp < 95 || temp > 100.4;
    if (out) warnings.push("Temperature is outside expected review range; provider review required.");
  }
  return warnings;
}

export function VitalsWorkupPanel({ encounterId }: Props) {
  const [workups, setWorkups] = useState<VitalWorkup[]>([]);
  const [selected, setSelected] = useState<VitalWorkup | null>(null);
  const [form, setForm] = useState<VitalWorkupPayload>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [attested, setAttested] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listVitalsWorkups(encounterId)
      .then((items) => {
        setWorkups(items);
        if (items[0]) {
          setSelected(items[0]);
          setForm({ ...items[0] });
        }
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [encounterId]);

  useEffect(() => {
    setAttested(false);
  }, [selected?.id]);

  const bmi = useMemo(() => bmiFor(form), [form]);
  const warnings = selected?.warnings_json?.length ? selected.warnings_json : warningsFor(form);
  const locked = selected?.status === "signed" || Boolean(selected?.signed_at);

  async function selectWorkup(id: number) {
    try {
      const full = await getVitalsWorkup(id);
      setSelected(full);
      setForm({ ...full });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load workup");
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const payload = { ...form, bmi: undefined };
      const saved = selected
        ? await updateVitalsWorkup(selected.id, payload)
        : await createVitalsWorkup(encounterId, payload);
      setSelected(saved);
      setForm({ ...saved });
      setWorkups((prev) => {
        const exists = prev.some((w) => w.id === saved.id);
        return exists ? prev.map((w) => (w.id === saved.id ? saved : w)) : [saved, ...prev];
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save workup");
    } finally {
      setSaving(false);
    }
  }

  async function review() {
    if (!selected) return;
    setSaving(true);
    try {
      const reviewed = await reviewVitalsWorkup(selected.id);
      setSelected(reviewed);
      setForm({ ...reviewed });
      setWorkups((prev) => prev.map((w) => (w.id === reviewed.id ? reviewed : w)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setSaving(false);
    }
  }

  async function sign() {
    if (!selected || !attested) return;
    setSaving(true);
    try {
      const signed = await signVitalsWorkup(selected.id, attested);
      setSelected(signed);
      setForm({ ...signed });
      setWorkups((prev) => prev.map((w) => (w.id === signed.id ? signed : w)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign failed");
    } finally {
      setSaving(false);
    }
  }

  function startNew() {
    setSelected(null);
    setForm(EMPTY_FORM);
    setError(null);
  }

  return (
    <div data-testid="vitals-workup-panel" style={{ fontFamily: "sans-serif", padding: 16 }}>
      <header style={{ marginBottom: 12 }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#2d3748" }}>
          Technician Workup &amp; Vitals
        </h3>
        <p data-testid="vitals-safety-copy" style={{ margin: 0, fontSize: 12, color: "#4a5568", lineHeight: 1.5 }}>
          Structured intake for provider review. Does not diagnose. Does
          not recommend treatment. Does not place orders.
        </p>
      </header>

      {error && <div data-testid="vitals-error" style={{ color: "#c53030", marginBottom: 10 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        <main style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button type="button" data-testid="vitals-new" onClick={startNew} disabled={saving} style={{ border: "1px solid #cbd5e0", borderRadius: 6, padding: "7px 10px", background: "#fff" }}>New workup</button>
            {workups.map((w) => (
              <button key={w.id} type="button" data-testid={`vitals-select-${w.id}`} onClick={() => selectWorkup(w.id)} style={{ border: selected?.id === w.id ? "1px solid #3182ce" : "1px solid #cbd5e0", borderRadius: 6, padding: "7px 10px", background: selected?.id === w.id ? "#ebf8ff" : "#fff" }}>
                #{w.id} {w.status}
              </button>
            ))}
            {loading && <span data-testid="vitals-loading">Loading…</span>}
          </div>

          {locked ? (
            <div data-testid="vitals-signed-readonly" style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 12, background: "#f7fafc" }}>
              Signed workup is locked.
            </div>
          ) : (
            <VitalsWorkupForm
              value={form}
              locked={locked}
              bmi={bmi}
              onChange={setForm}
              onLoadDemo={() => setForm(DEMO_VALUES)}
            />
          )}

          {!locked && (
            <div data-testid="vitals-action-row" style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <button type="button" data-testid="vitals-save" onClick={save} disabled={saving} style={{ border: "none", borderRadius: 6, padding: "8px 14px", background: "#0b6e79", color: "#fff", fontWeight: 700 }}>
                {selected ? "Save workup" : "Create workup"}
              </button>
              <button type="button" data-testid="vitals-review" onClick={review} disabled={saving || !selected} style={{ border: "1px solid #3182ce", borderRadius: 6, padding: "8px 14px", background: "#ebf8ff", color: "#2a4a7f", fontWeight: 700 }}>
                Review
              </button>
              <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13 }}>
                <input data-testid="vitals-sign-attestation" type="checkbox" checked={attested} disabled={saving || !selected} onChange={(e) => setAttested(e.target.checked)} />
                Attest for signature
              </label>
              <button type="button" data-testid="vitals-sign" onClick={sign} disabled={saving || !selected || !attested} style={{ border: "1px solid #276749", borderRadius: 6, padding: "8px 14px", background: "#f0fff4", color: "#276749", fontWeight: 700 }}>
                Sign
              </button>
            </div>
          )}
        </main>

        <VitalsWorkupSummary workup={selected} warnings={warnings} />
      </div>
    </div>
  );
}
