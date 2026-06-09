// Phase 79 — Glaucoma Progression Cockpit types.

export type GlaucomaEye = "OD" | "OS";

export interface GlaucomaIopMeasurement {
  vitals_workup_id: number;
  encounter_id: number | null;
  eye: GlaucomaEye;
  value: number;
  method: string | null;
  status: string;
  signed: boolean;
  reviewed_at: string | null;
  signed_at: string | null;
  recorded_at: string | null;
}

export interface GlaucomaModalitySummary {
  count: number;
  latest_id: number | null;
  latest_modality: string | null;
  latest_status: string | null;
  latest_captured_at: string | null;
  latest_reviewed_at: string | null;
  latest_reviewed_by_user_id: number | null;
  insufficient_data: boolean;
}

export interface GlaucomaDataCompleteness {
  has_iop: boolean;
  has_visual_field: boolean;
  has_oct_rnfl: boolean;
  score_numerator: number;
  score_denominator: number;
}

export interface GlaucomaEyeLane {
  eye: GlaucomaEye;
  iop_history: GlaucomaIopMeasurement[];
  latest_iop: GlaucomaIopMeasurement | null;
  iop_count: number;
  visual_field: GlaucomaModalitySummary;
  oct_rnfl: GlaucomaModalitySummary;
  oct_macula: GlaucomaModalitySummary;
  data_completeness: GlaucomaDataCompleteness;
  insufficient_data: boolean;
}

export interface GlaucomaSummary {
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  generated_at: string;
  demo_mode: boolean;
  bilateral_data: boolean;
  od: GlaucomaEyeLane;
  os: GlaucomaEyeLane;
  disclosure: string;
}
