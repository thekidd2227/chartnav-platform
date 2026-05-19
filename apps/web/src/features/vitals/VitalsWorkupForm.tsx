import type React from "react";
import type { VitalWorkupPayload } from "./vitalsTypes";

interface Props {
  value: VitalWorkupPayload;
  locked: boolean;
  bmi: number | null;
  onChange: (next: VitalWorkupPayload) => void;
  onLoadDemo: () => void;
}

function numberValue(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

function toNumber(value: string): number | null {
  return value.trim() === "" ? null : Number(value);
}

function Field({
  label,
  children,
}: {
  label: string;
  children: JSX.Element;
}) {
  return (
    <label style={{ display: "grid", gap: 4, fontSize: 12, color: "#4a5568" }}>
      <span style={{ fontWeight: 700 }}>{label}</span>
      {children}
    </label>
  );
}

function inputStyle(): React.CSSProperties {
  return {
    border: "1px solid #cbd5e0",
    borderRadius: 6,
    padding: "7px 8px",
    fontSize: 13,
    minWidth: 0,
  };
}

export function VitalsWorkupForm({
  value,
  locked,
  bmi,
  onChange,
  onLoadDemo,
}: Props) {
  const patch = (next: VitalWorkupPayload) => onChange({ ...value, ...next });
  const disabled = locked;

  return (
    <div data-testid="vitals-workup-form" style={{ display: "grid", gap: 16 }}>
      <button
        type="button"
        onClick={onLoadDemo}
        disabled={disabled}
        data-testid="vitals-load-demo"
        style={{
          justifySelf: "start",
          border: "1px solid #0b6e79",
          background: "#e6fffb",
          color: "#0b6e79",
          borderRadius: 6,
          padding: "7px 10px",
          fontWeight: 700,
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.5 : 1,
        }}
      >
        Load fake demo vitals
      </button>

      <section>
        <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>General vitals</h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
          <Field label="BP systolic">
            <input data-testid="vitals-bp-systolic" type="number" disabled={disabled} value={numberValue(value.bp_systolic)} onChange={(e) => patch({ bp_systolic: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="BP diastolic">
            <input data-testid="vitals-bp-diastolic" type="number" disabled={disabled} value={numberValue(value.bp_diastolic)} onChange={(e) => patch({ bp_diastolic: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Position">
            <select data-testid="vitals-bp-position" disabled={disabled} value={value.bp_position ?? ""} onChange={(e) => patch({ bp_position: e.target.value as VitalWorkupPayload["bp_position"] })} style={inputStyle()}>
              <option value="">Select</option><option value="sitting">Sitting</option><option value="standing">Standing</option><option value="supine">Supine</option><option value="unknown">Unknown</option>
            </select>
          </Field>
          <Field label="Site">
            <select data-testid="vitals-bp-site" disabled={disabled} value={value.bp_site ?? ""} onChange={(e) => patch({ bp_site: e.target.value as VitalWorkupPayload["bp_site"] })} style={inputStyle()}>
              <option value="">Select</option><option value="left_arm">Left arm</option><option value="right_arm">Right arm</option><option value="wrist">Wrist</option><option value="other">Other</option><option value="unknown">Unknown</option>
            </select>
          </Field>
          <Field label="Temperature">
            <input data-testid="vitals-temperature" type="number" step="0.1" disabled={disabled} value={numberValue(value.temperature_value)} onChange={(e) => patch({ temperature_value: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Temp unit">
            <select data-testid="vitals-temperature-unit" disabled={disabled} value={value.temperature_unit ?? "F"} onChange={(e) => patch({ temperature_unit: e.target.value as "F" | "C" })} style={inputStyle()}><option value="F">F</option><option value="C">C</option></select>
          </Field>
          <Field label="Pulse">
            <input data-testid="vitals-pulse" type="number" disabled={disabled} value={numberValue(value.pulse)} onChange={(e) => patch({ pulse: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Respiratory rate">
            <input data-testid="vitals-respiratory-rate" type="number" disabled={disabled} value={numberValue(value.respiratory_rate)} onChange={(e) => patch({ respiratory_rate: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Oxygen saturation">
            <input data-testid="vitals-oxygen-saturation" type="number" disabled={disabled} value={numberValue(value.oxygen_saturation)} onChange={(e) => patch({ oxygen_saturation: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Height">
            <input data-testid="vitals-height" type="number" step="0.1" disabled={disabled} value={numberValue(value.height_value)} onChange={(e) => patch({ height_value: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Height unit">
            <select data-testid="vitals-height-unit" disabled={disabled} value={value.height_unit ?? "in"} onChange={(e) => patch({ height_unit: e.target.value as "in" | "cm" })} style={inputStyle()}><option value="in">in</option><option value="cm">cm</option></select>
          </Field>
          <Field label="Weight">
            <input data-testid="vitals-weight" type="number" step="0.1" disabled={disabled} value={numberValue(value.weight_value)} onChange={(e) => patch({ weight_value: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
          <Field label="Weight unit">
            <select data-testid="vitals-weight-unit" disabled={disabled} value={value.weight_unit ?? "lb"} onChange={(e) => patch({ weight_unit: e.target.value as "lb" | "kg" })} style={inputStyle()}><option value="lb">lb</option><option value="kg">kg</option></select>
          </Field>
          <div data-testid="vitals-bmi-display" style={{ alignSelf: "end", padding: "8px", border: "1px solid #bee3f8", borderRadius: 6, background: "#ebf8ff", fontSize: 13 }}>
            BMI: <strong>{bmi === null ? "Not calculated" : bmi.toFixed(2)}</strong>
          </div>
          <Field label="Pain score">
            <input data-testid="vitals-pain-score" type="number" min={0} max={10} disabled={disabled} value={numberValue(value.pain_score)} onChange={(e) => patch({ pain_score: toNumber(e.target.value) })} style={inputStyle()} />
          </Field>
        </div>
      </section>

      <section>
        <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Ophthalmology workup</h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
          <Field label="VA OD"><input data-testid="vitals-va-od" disabled={disabled} value={value.visual_acuity_od ?? ""} onChange={(e) => patch({ visual_acuity_od: e.target.value })} style={inputStyle()} /></Field>
          <Field label="VA OS"><input data-testid="vitals-va-os" disabled={disabled} value={value.visual_acuity_os ?? ""} onChange={(e) => patch({ visual_acuity_os: e.target.value })} style={inputStyle()} /></Field>
          <Field label="VA OU"><input data-testid="vitals-va-ou" disabled={disabled} value={value.visual_acuity_ou ?? ""} onChange={(e) => patch({ visual_acuity_ou: e.target.value })} style={inputStyle()} /></Field>
          <Field label="IOP OD"><input data-testid="vitals-iop-od" type="number" step="0.1" disabled={disabled} value={numberValue(value.iop_od)} onChange={(e) => patch({ iop_od: toNumber(e.target.value) })} style={inputStyle()} /></Field>
          <Field label="IOP OS"><input data-testid="vitals-iop-os" type="number" step="0.1" disabled={disabled} value={numberValue(value.iop_os)} onChange={(e) => patch({ iop_os: toNumber(e.target.value) })} style={inputStyle()} /></Field>
          <Field label="IOP method">
            <select data-testid="vitals-iop-method" disabled={disabled} value={value.iop_method ?? ""} onChange={(e) => patch({ iop_method: e.target.value as VitalWorkupPayload["iop_method"] })} style={inputStyle()}>
              <option value="">Select</option><option value="applanation">Applanation</option><option value="tonopen">Tonopen</option><option value="icare">iCare</option><option value="other">Other</option><option value="unknown">Unknown</option>
            </select>
          </Field>
          <Field label="Dilation status">
            <select data-testid="vitals-dilation-status" disabled={disabled} value={value.dilation_status ?? ""} onChange={(e) => patch({ dilation_status: e.target.value as VitalWorkupPayload["dilation_status"] })} style={inputStyle()}>
              <option value="">Select</option><option value="not_dilated">Not dilated</option><option value="dilated">Dilated</option><option value="declined">Declined</option><option value="contraindicated">Contraindicated</option><option value="unknown">Unknown</option>
            </select>
          </Field>
          <Field label="Dilation time">
            <input data-testid="vitals-dilation-time" type="datetime-local" disabled={disabled} value={value.dilation_time ?? ""} onChange={(e) => patch({ dilation_time: e.target.value })} style={inputStyle()} />
          </Field>
        </div>
      </section>

      <section>
        <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Review checks</h4>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <label><input data-testid="vitals-allergies-reviewed" type="checkbox" disabled={disabled} checked={Boolean(value.allergies_reviewed)} onChange={(e) => patch({ allergies_reviewed: e.target.checked })} /> Allergies reviewed</label>
          <label><input data-testid="vitals-medications-reviewed" type="checkbox" disabled={disabled} checked={Boolean(value.medications_reviewed)} onChange={(e) => patch({ medications_reviewed: e.target.checked })} /> Medications reviewed</label>
        </div>
      </section>

      <section>
        <h4 style={{ margin: "0 0 8px", fontSize: 14 }}>Technician notes</h4>
        <textarea
          data-testid="vitals-technician-notes"
          disabled={disabled}
          value={value.technician_notes ?? ""}
          onChange={(e) => patch({ technician_notes: e.target.value })}
          rows={3}
          style={{ ...inputStyle(), width: "100%", boxSizing: "border-box" }}
        />
      </section>
    </div>
  );
}
