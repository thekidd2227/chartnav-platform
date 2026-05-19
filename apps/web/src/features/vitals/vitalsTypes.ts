export type VitalWorkupStatus =
  | "draft"
  | "entered"
  | "reviewed"
  | "signed"
  | "superseded";

export type VitalWorkupSourceType =
  | "technician_entry"
  | "clinician_entry"
  | "imported"
  | "demo";

export interface VitalWorkupPayload {
  status?: VitalWorkupStatus;
  source_type?: VitalWorkupSourceType;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  bp_position?: "sitting" | "standing" | "supine" | "unknown" | null;
  bp_site?: "left_arm" | "right_arm" | "wrist" | "other" | "unknown" | null;
  temperature_value?: number | null;
  temperature_unit?: "F" | "C";
  temperature_site?: "oral" | "temporal" | "tympanic" | "axillary" | "other" | "unknown" | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  oxygen_saturation?: number | null;
  height_value?: number | null;
  height_unit?: "in" | "cm";
  weight_value?: number | null;
  weight_unit?: "lb" | "kg";
  pain_score?: number | null;
  visual_acuity_od?: string | null;
  visual_acuity_os?: string | null;
  visual_acuity_ou?: string | null;
  iop_od?: number | null;
  iop_os?: number | null;
  iop_method?: "applanation" | "tonopen" | "icare" | "other" | "unknown" | null;
  dilation_status?: "not_dilated" | "dilated" | "declined" | "contraindicated" | "unknown" | null;
  dilation_time?: string | null;
  allergies_reviewed?: boolean;
  medications_reviewed?: boolean;
  technician_notes?: string | null;
}

export interface VitalWorkup extends VitalWorkupPayload {
  id: number;
  organization_id: number;
  encounter_id: number | null;
  patient_id: number;
  status: VitalWorkupStatus;
  source_type: VitalWorkupSourceType;
  temperature_unit: "F" | "C";
  height_unit: "in" | "cm";
  weight_unit: "lb" | "kg";
  bmi: number | null;
  allergies_reviewed: boolean;
  medications_reviewed: boolean;
  warnings_json: string[];
  reviewed_by_user_id: number | null;
  signed_by_user_id: number | null;
  signed_at: string | null;
  created_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}
