export type VitalsStatus =
  | "draft"
  | "entered"
  | "reviewed"
  | "signed"
  | "superseded";

export type VitalsSourceType =
  | "technician_entry"
  | "clinician_entry"
  | "imported"
  | "demo";

export type BpPosition = "sitting" | "standing" | "supine" | "unknown";
export type BpSite = "left_arm" | "right_arm" | "wrist" | "other" | "unknown";
export type TemperatureUnit = "F" | "C";
export type TemperatureSite =
  | "oral"
  | "temporal"
  | "tympanic"
  | "axillary"
  | "rectal"
  | "other"
  | "unknown";
export type HeightUnit = "in" | "cm";
export type WeightUnit = "lb" | "kg";
export type IopMethod =
  | "applanation"
  | "tonopen"
  | "icare"
  | "other"
  | "unknown";
export type DilationStatus =
  | "not_dilated"
  | "dilated"
  | "declined"
  | "contraindicated"
  | "unknown";

export interface VitalsForbiddenActions {
  diagnosis: boolean;
  treatment_recommendation: boolean;
  orders: boolean;
  referrals: boolean;
  patient_message: boolean;
  billing_or_coding: boolean;
  device_integration: boolean;
  remote_patient_monitoring: boolean;
  auto_sign: boolean;
}

export interface VitalsWorkup {
  id: number;
  organization_id: number;
  encounter_id: number;
  patient_id: number | null;
  status: VitalsStatus;
  source_type: VitalsSourceType;
  bp_systolic: number | null;
  bp_diastolic: number | null;
  bp_position: BpPosition | null;
  bp_site: BpSite | null;
  temperature_value: number | null;
  temperature_unit: TemperatureUnit;
  temperature_site: TemperatureSite | null;
  pulse: number | null;
  respiratory_rate: number | null;
  oxygen_saturation: number | null;
  height_value: number | null;
  height_unit: HeightUnit;
  weight_value: number | null;
  weight_unit: WeightUnit;
  bmi: number | null;
  pain_score: number | null;
  visual_acuity_od: string | null;
  visual_acuity_os: string | null;
  visual_acuity_ou: string | null;
  iop_od: number | null;
  iop_os: number | null;
  iop_method: IopMethod | null;
  dilation_status: DilationStatus | null;
  dilation_time: string | null;
  allergies_reviewed: boolean;
  medications_reviewed: boolean;
  technician_notes: string | null;
  warnings: string[];
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  signed_by_user_id: number | null;
  signed_at: string | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
  requires_provider_review: boolean;
  forbidden_actions: VitalsForbiddenActions;
  is_terminal: boolean;
}

export interface VitalsWorkupCreateRequest {
  source_type?: VitalsSourceType;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  bp_position?: BpPosition | null;
  bp_site?: BpSite | null;
  temperature_value?: number | null;
  temperature_unit?: TemperatureUnit;
  temperature_site?: TemperatureSite | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  oxygen_saturation?: number | null;
  height_value?: number | null;
  height_unit?: HeightUnit;
  weight_value?: number | null;
  weight_unit?: WeightUnit;
  pain_score?: number | null;
  visual_acuity_od?: string | null;
  visual_acuity_os?: string | null;
  visual_acuity_ou?: string | null;
  iop_od?: number | null;
  iop_os?: number | null;
  iop_method?: IopMethod | null;
  dilation_status?: DilationStatus | null;
  dilation_time?: string | null;
  allergies_reviewed?: boolean;
  medications_reviewed?: boolean;
  technician_notes?: string | null;
}

export interface VitalsWorkupUpdateRequest extends VitalsWorkupCreateRequest {
  advance_to_entered?: boolean;
}

export interface VitalsWorkupSignRequest {
  attested: boolean;
}
