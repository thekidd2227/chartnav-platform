// Phase 84 — Disease staging types.

export type StagingSystem =
  | "amd_areds"
  | "diabetic_etdrs"
  | "glaucoma_poag"
  | "keratoconus_amsler_krumeich"
  | "dry_eye_dews";

export interface DiseaseStageRecord {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  diagnosis_code: string;
  staging_system: StagingSystem;
  staging_system_label: string;
  stage_value: string;
  prior_stage: string | null;
  staged_at: string | null;
  staged_by_user_id: number | null;
  staged_by_display_name: string | null;
  staged_by_role: string | null;
  progression_detected: boolean | null;
  elapsed_days_since_prior: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DiseaseStageSupportedSystem {
  code: StagingSystem;
  label: string;
  stages: string[];
}

export interface DiseaseStagingPanelResponse {
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  generated_at: string;
  demo_mode: boolean;
  records: DiseaseStageRecord[];
  latest_by_diagnosis: Record<string, DiseaseStageRecord>;
  supported_systems: DiseaseStageSupportedSystem[];
  disclosure: string;
}

export interface DiseaseStageCreatePayload {
  diagnosis_code: string;
  staging_system: StagingSystem;
  stage_value: string;
  prior_stage?: string | null;
}
