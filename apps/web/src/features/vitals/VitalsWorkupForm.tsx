import React from "react";
import type {
  BpPosition,
  BpSite,
  DilationStatus,
  HeightUnit,
  IopMethod,
  TemperatureUnit,
  VitalsWorkup,
  VitalsWorkupCreateRequest,
  WeightUnit,
} from "./vitalsTypes";

export type FormState = VitalsWorkupCreateRequest;

interface Props {
  state: FormState;
  onChange: (next: FormState) => void;
  disabled?: boolean;
}

function NumberField({
  label,
  name,
  value,
  onChange,
  disabled,
  min,
  max,
  step,
}: {
  label: string;
  name: string;
  value: number | null | undefined;
  onChange: (v: number | null) => void;
  disabled?: boolean;
  min?: number;
  max?: number;
  step?: number | string;
}) {
  return (
    <label
      style={{ display: "flex", flexDirection: "column", fontSize: 11 }}
      data-testid={`vitals-field-${name}`}
    >
      <span
        style={{
          color: "#718096",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: 0.4,
          marginBottom: 2,
        }}
      >
        {label}
      </span>
      <input
        type="number"
        value={value === null || value === undefined ? "" : value}
        disabled={disabled}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            onChange(null);
          } else {
            const parsed = Number(raw);
            onChange(Number.isNaN(parsed) ? null : parsed);
          }
        }}
        min={min}
        max={max}
        step={step}
        style={{
          fontSize: 13,
          padding: "4px 6px",
          borderRadius: 4,
          border: "1px solid #cbd5e0",
        }}
        data-testid={`vitals-input-${name}`}
      />
    </label>
  );
}

function TextField({
  label,
  name,
  value,
  onChange,
  disabled,
  placeholder,
}: {
  label: string;
  name: string;
  value: string | null | undefined;
  onChange: (v: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <label
      style={{ display: "flex", flexDirection: "column", fontSize: 11 }}
      data-testid={`vitals-field-${name}`}
    >
      <span
        style={{
          color: "#718096",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: 0.4,
          marginBottom: 2,
        }}
      >
        {label}
      </span>
      <input
        type="text"
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value || null)}
        placeholder={placeholder}
        style={{
          fontSize: 13,
          padding: "4px 6px",
          borderRadius: 4,
          border: "1px solid #cbd5e0",
        }}
        data-testid={`vitals-input-${name}`}
      />
    </label>
  );
}

function SelectField<T extends string>({
  label,
  name,
  value,
  onChange,
  options,
  disabled,
}: {
  label: string;
  name: string;
  value: T | null | undefined;
  onChange: (v: T | null) => void;
  options: ReadonlyArray<readonly [T, string]>;
  disabled?: boolean;
}) {
  return (
    <label
      style={{ display: "flex", flexDirection: "column", fontSize: 11 }}
      data-testid={`vitals-field-${name}`}
    >
      <span
        style={{
          color: "#718096",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: 0.4,
          marginBottom: 2,
        }}
      >
        {label}
      </span>
      <select
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange((e.target.value || null) as T | null)}
        style={{
          fontSize: 13,
          padding: "4px 6px",
          borderRadius: 4,
          border: "1px solid #cbd5e0",
        }}
        data-testid={`vitals-input-${name}`}
      >
        <option value="">—</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

const BP_POSITIONS: ReadonlyArray<readonly [BpPosition, string]> = [
  ["sitting", "Sitting"],
  ["standing", "Standing"],
  ["supine", "Supine"],
  ["unknown", "Unknown"],
];
const BP_SITES: ReadonlyArray<readonly [BpSite, string]> = [
  ["left_arm", "Left arm"],
  ["right_arm", "Right arm"],
  ["wrist", "Wrist"],
  ["other", "Other"],
  ["unknown", "Unknown"],
];
const TEMP_UNITS: ReadonlyArray<readonly [TemperatureUnit, string]> = [
  ["F", "°F"],
  ["C", "°C"],
];
const HEIGHT_UNITS: ReadonlyArray<readonly [HeightUnit, string]> = [
  ["in", "in"],
  ["cm", "cm"],
];
const WEIGHT_UNITS: ReadonlyArray<readonly [WeightUnit, string]> = [
  ["lb", "lb"],
  ["kg", "kg"],
];
const IOP_METHODS: ReadonlyArray<readonly [IopMethod, string]> = [
  ["applanation", "Applanation"],
  ["tonopen", "Tono-Pen"],
  ["icare", "iCare"],
  ["other", "Other"],
  ["unknown", "Unknown"],
];
const DILATION_STATUSES: ReadonlyArray<readonly [DilationStatus, string]> = [
  ["not_dilated", "Not dilated"],
  ["dilated", "Dilated"],
  ["declined", "Declined"],
  ["contraindicated", "Contraindicated"],
  ["unknown", "Unknown"],
];

const SECTION: React.CSSProperties = {
  background: "#f7fafc",
  border: "1px solid #e2e8f0",
  borderRadius: 8,
  padding: 12,
  marginBottom: 12,
};
const GRID: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
  gap: 10,
};

export function VitalsWorkupForm({ state, onChange, disabled = false }: Props) {
  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    onChange({ ...state, [key]: value });
  }

  // Local BMI preview computed client-side from current state.
  const heightUnit = state.height_unit ?? "in";
  const weightUnit = state.weight_unit ?? "lb";
  const previewBmi = (() => {
    if (state.height_value == null || state.weight_value == null) return null;
    const h = state.height_value;
    const w = state.weight_value;
    if (h <= 0 || w <= 0) return null;
    const heightM = heightUnit === "cm" ? h * 0.01 : h * 0.0254;
    const weightKg = weightUnit === "kg" ? w : w * 0.45359237;
    if (heightM <= 0) return null;
    return Math.round((weightKg / (heightM * heightM)) * 10) / 10;
  })();

  return (
    <div data-testid="vitals-form">
      <div style={SECTION} data-testid="vitals-section-general">
        <p
          style={{
            margin: "0 0 8px",
            fontSize: 11,
            fontWeight: 700,
            color: "#4a5568",
            textTransform: "uppercase",
            letterSpacing: 0.4,
          }}
        >
          General vitals
        </p>
        <div style={GRID}>
          <NumberField
            label="BP systolic"
            name="bp_systolic"
            value={state.bp_systolic}
            onChange={(v) => set("bp_systolic", v)}
            disabled={disabled}
            min={0}
            max={400}
          />
          <NumberField
            label="BP diastolic"
            name="bp_diastolic"
            value={state.bp_diastolic}
            onChange={(v) => set("bp_diastolic", v)}
            disabled={disabled}
            min={0}
            max={300}
          />
          <SelectField<BpPosition>
            label="BP position"
            name="bp_position"
            value={state.bp_position ?? null}
            onChange={(v) => set("bp_position", v)}
            options={BP_POSITIONS}
            disabled={disabled}
          />
          <SelectField<BpSite>
            label="BP site"
            name="bp_site"
            value={state.bp_site ?? null}
            onChange={(v) => set("bp_site", v)}
            options={BP_SITES}
            disabled={disabled}
          />
          <NumberField
            label="Temperature"
            name="temperature_value"
            value={state.temperature_value}
            onChange={(v) => set("temperature_value", v)}
            disabled={disabled}
            step="0.1"
          />
          <SelectField<TemperatureUnit>
            label="Temp unit"
            name="temperature_unit"
            value={state.temperature_unit ?? "F"}
            onChange={(v) => set("temperature_unit", v ?? "F")}
            options={TEMP_UNITS}
            disabled={disabled}
          />
          <NumberField
            label="Pulse"
            name="pulse"
            value={state.pulse}
            onChange={(v) => set("pulse", v)}
            disabled={disabled}
            min={0}
            max={400}
          />
          <NumberField
            label="Resp rate"
            name="respiratory_rate"
            value={state.respiratory_rate}
            onChange={(v) => set("respiratory_rate", v)}
            disabled={disabled}
            min={0}
            max={200}
          />
          <NumberField
            label="O2 sat (%)"
            name="oxygen_saturation"
            value={state.oxygen_saturation}
            onChange={(v) => set("oxygen_saturation", v)}
            disabled={disabled}
            min={0}
            max={100}
          />
          <NumberField
            label="Height"
            name="height_value"
            value={state.height_value}
            onChange={(v) => set("height_value", v)}
            disabled={disabled}
            step="0.1"
          />
          <SelectField<HeightUnit>
            label="Height unit"
            name="height_unit"
            value={state.height_unit ?? "in"}
            onChange={(v) => set("height_unit", v ?? "in")}
            options={HEIGHT_UNITS}
            disabled={disabled}
          />
          <NumberField
            label="Weight"
            name="weight_value"
            value={state.weight_value}
            onChange={(v) => set("weight_value", v)}
            disabled={disabled}
            step="0.1"
          />
          <SelectField<WeightUnit>
            label="Weight unit"
            name="weight_unit"
            value={state.weight_unit ?? "lb"}
            onChange={(v) => set("weight_unit", v ?? "lb")}
            options={WEIGHT_UNITS}
            disabled={disabled}
          />
          <NumberField
            label="Pain (0-10)"
            name="pain_score"
            value={state.pain_score}
            onChange={(v) => set("pain_score", v)}
            disabled={disabled}
            min={0}
            max={10}
          />
          <div
            data-testid="vitals-bmi-display"
            style={{
              display: "flex",
              flexDirection: "column",
              fontSize: 11,
              padding: "4px 6px",
              border: "1px solid #cbd5e0",
              borderRadius: 4,
              background: "#edf2f7",
            }}
          >
            <span
              style={{
                color: "#718096",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: 0.4,
                marginBottom: 2,
              }}
            >
              BMI (calculated)
            </span>
            <span style={{ fontSize: 13, color: "#2d3748", fontWeight: 600 }}>
              {previewBmi === null ? "—" : previewBmi.toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      <div style={SECTION} data-testid="vitals-section-ophthalmology">
        <p
          style={{
            margin: "0 0 8px",
            fontSize: 11,
            fontWeight: 700,
            color: "#4a5568",
            textTransform: "uppercase",
            letterSpacing: 0.4,
          }}
        >
          Ophthalmology workup
        </p>
        <div style={GRID}>
          <TextField
            label="VA OD"
            name="visual_acuity_od"
            value={state.visual_acuity_od}
            onChange={(v) => set("visual_acuity_od", v)}
            disabled={disabled}
            placeholder="20/20"
          />
          <TextField
            label="VA OS"
            name="visual_acuity_os"
            value={state.visual_acuity_os}
            onChange={(v) => set("visual_acuity_os", v)}
            disabled={disabled}
            placeholder="20/20"
          />
          <TextField
            label="VA OU"
            name="visual_acuity_ou"
            value={state.visual_acuity_ou}
            onChange={(v) => set("visual_acuity_ou", v)}
            disabled={disabled}
          />
          <NumberField
            label="IOP OD"
            name="iop_od"
            value={state.iop_od}
            onChange={(v) => set("iop_od", v)}
            disabled={disabled}
            step="0.1"
          />
          <NumberField
            label="IOP OS"
            name="iop_os"
            value={state.iop_os}
            onChange={(v) => set("iop_os", v)}
            disabled={disabled}
            step="0.1"
          />
          <SelectField<IopMethod>
            label="IOP method"
            name="iop_method"
            value={state.iop_method ?? null}
            onChange={(v) => set("iop_method", v)}
            options={IOP_METHODS}
            disabled={disabled}
          />
          <SelectField<DilationStatus>
            label="Dilation status"
            name="dilation_status"
            value={state.dilation_status ?? null}
            onChange={(v) => set("dilation_status", v)}
            options={DILATION_STATUSES}
            disabled={disabled}
          />
        </div>
      </div>

      <div style={SECTION} data-testid="vitals-section-review-checks">
        <p
          style={{
            margin: "0 0 8px",
            fontSize: 11,
            fontWeight: 700,
            color: "#4a5568",
            textTransform: "uppercase",
            letterSpacing: 0.4,
          }}
        >
          Review checks
        </p>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <label
            style={{ display: "flex", gap: 6, fontSize: 13, color: "#2d3748" }}
            data-testid="vitals-field-allergies_reviewed"
          >
            <input
              type="checkbox"
              checked={!!state.allergies_reviewed}
              disabled={disabled}
              onChange={(e) =>
                set("allergies_reviewed", e.target.checked)
              }
              data-testid="vitals-input-allergies_reviewed"
            />
            Allergies reviewed
          </label>
          <label
            style={{ display: "flex", gap: 6, fontSize: 13, color: "#2d3748" }}
            data-testid="vitals-field-medications_reviewed"
          >
            <input
              type="checkbox"
              checked={!!state.medications_reviewed}
              disabled={disabled}
              onChange={(e) =>
                set("medications_reviewed", e.target.checked)
              }
              data-testid="vitals-input-medications_reviewed"
            />
            Medications reviewed
          </label>
        </div>
      </div>

      <div style={SECTION} data-testid="vitals-section-notes">
        <p
          style={{
            margin: "0 0 8px",
            fontSize: 11,
            fontWeight: 700,
            color: "#4a5568",
            textTransform: "uppercase",
            letterSpacing: 0.4,
          }}
        >
          Technician notes
        </p>
        <textarea
          rows={3}
          value={state.technician_notes ?? ""}
          disabled={disabled}
          onChange={(e) => set("technician_notes", e.target.value || null)}
          placeholder="Brief structured notes for provider review. Do not paste real PHI."
          data-testid="vitals-input-technician_notes"
          style={{
            width: "100%",
            fontSize: 13,
            padding: 8,
            borderRadius: 4,
            border: "1px solid #cbd5e0",
            boxSizing: "border-box",
          }}
        />
      </div>
    </div>
  );
}

export const DEMO_FAKE_VITALS: FormState = {
  source_type: "demo",
  bp_systolic: 122,
  bp_diastolic: 78,
  bp_position: "sitting",
  bp_site: "left_arm",
  temperature_value: 98.6,
  temperature_unit: "F",
  pulse: 72,
  respiratory_rate: 16,
  oxygen_saturation: 98,
  height_value: 70,
  height_unit: "in",
  weight_value: 165,
  weight_unit: "lb",
  pain_score: 0,
  visual_acuity_od: "20/20",
  visual_acuity_os: "20/25",
  iop_od: 14,
  iop_os: 13,
  iop_method: "applanation",
  dilation_status: "not_dilated",
  allergies_reviewed: true,
  medications_reviewed: true,
  technician_notes:
    "Demo fake-data only. No real PHI. Provider review required before signing.",
};

export function vitalsFromWorkup(w: VitalsWorkup): FormState {
  return {
    source_type: w.source_type,
    bp_systolic: w.bp_systolic,
    bp_diastolic: w.bp_diastolic,
    bp_position: w.bp_position,
    bp_site: w.bp_site,
    temperature_value: w.temperature_value,
    temperature_unit: w.temperature_unit,
    temperature_site: w.temperature_site,
    pulse: w.pulse,
    respiratory_rate: w.respiratory_rate,
    oxygen_saturation: w.oxygen_saturation,
    height_value: w.height_value,
    height_unit: w.height_unit,
    weight_value: w.weight_value,
    weight_unit: w.weight_unit,
    pain_score: w.pain_score,
    visual_acuity_od: w.visual_acuity_od,
    visual_acuity_os: w.visual_acuity_os,
    visual_acuity_ou: w.visual_acuity_ou,
    iop_od: w.iop_od,
    iop_os: w.iop_os,
    iop_method: w.iop_method,
    dilation_status: w.dilation_status,
    dilation_time: w.dilation_time,
    allergies_reviewed: w.allergies_reviewed,
    medications_reviewed: w.medications_reviewed,
    technician_notes: w.technician_notes,
  };
}
