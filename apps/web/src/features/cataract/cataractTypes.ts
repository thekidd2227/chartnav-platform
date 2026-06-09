// Phase 80 — Cataract surgical workflow types.

export type CataractEye = "OD" | "OS";

export type CataractConsentStatus =
  | "not_obtained"
  | "in_progress"
  | "signed"
  | "declined"
  | "unknown";

export type CataractPostopStatus =
  | "not_scheduled"
  | "scheduled"
  | "completed"
  | "missed"
  | "unknown";

export interface CataractLatestRecord {
  id: number;
  encounter_id: number | null;
  surgery_eye: CataractEye;
  planned_surgery_date: string | null;
  biometry_study_id: number | null;
  biometry_reviewed: boolean;
  topography_reviewed: boolean;
  consent_status: CataractConsentStatus;
  postop_day_1_status: CataractPostopStatus;
  postop_week_1_status: CataractPostopStatus;
  postop_month_1_status: CataractPostopStatus;
  complications_flag: boolean;
  created_at: string;
  updated_at: string;
}

export interface CataractPreopReadiness {
  has_planned_date: boolean;
  biometry_reviewed: boolean;
  topography_reviewed: boolean;
  consent_signed: boolean;
  score_numerator: number;
  score_denominator: number;
}

export interface CataractPostopCadence {
  postop_day_1_status: CataractPostopStatus;
  postop_week_1_status: CataractPostopStatus;
  postop_month_1_status: CataractPostopStatus;
  score_numerator: number;
  score_denominator: number;
}

export interface CataractEyeLane {
  eye: CataractEye;
  record_count: number;
  latest_record: CataractLatestRecord | null;
  preop_readiness: CataractPreopReadiness;
  postop_cadence: CataractPostopCadence;
  complications_flag: boolean;
  insufficient_data: boolean;
}

export interface CataractWorkflowSummary {
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  generated_at: string;
  demo_mode: boolean;
  od: CataractEyeLane;
  os: CataractEyeLane;
  bilateral_planned: boolean;
  disclosure: string;
}
