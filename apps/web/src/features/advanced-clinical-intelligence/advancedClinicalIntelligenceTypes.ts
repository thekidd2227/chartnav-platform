// Phase 92 — Advanced Clinical Intelligence Layer types.

export interface RetinaLane {
  injection_count: number;
  latest_injection_date: string | null;
  latest_interval_weeks: number | null;
  latest_authorization_status: string | null;
  interval_history_weeks?: number[];
  insufficient_data: boolean;
}

export interface RetinaSummary {
  od: RetinaLane;
  os: RetinaLane;
  stage_history: Array<{
    id: number;
    diagnosis_code: string | null;
    staging_system: string | null;
    stage_value: string | null;
    staged_at: string | null;
    progression_detected: boolean | null;
  }>;
  stage_history_count: number;
  fundus_chart_count: number;
  fundus_chart_latest: {
    id: number;
    laterality: string | null;
    status: string | null;
    created_at: string | null;
    signed_at: string | null;
  } | null;
  imaging_metadata_summary: Record<string, unknown>;
  data_limitations: string[];
  insufficient_data: boolean;
}

export interface GlaucomaSummary {
  od: Record<string, unknown>;
  os: Record<string, unknown>;
  poag_stage_history: Array<{
    id: number;
    stage_value: string | null;
    staged_at: string | null;
    progression_detected: boolean | null;
  }>;
  poag_stage_history_count: number;
  adherence_signals: {
    active_medication_count: number;
    refill_gap_count: number;
    active_safety_event_count: number;
  };
  data_limitations: string[];
  insufficient_data: boolean;
}

export interface CataractLaneState {
  record_count: number;
  planned_surgery_date?: string | null;
  biometry_reviewed?: boolean | null;
  topography_reviewed?: boolean | null;
  consent_status?: string | null;
  postop_day_1_status?: string | null;
  postop_week_1_status?: string | null;
  postop_month_1_status?: string | null;
  complications_flag?: boolean | null;
  insufficient_data: boolean;
}

export interface CataractSummary {
  od: CataractLaneState;
  os: CataractLaneState;
  conversion_funnel: {
    any_record: boolean;
    planned_date_present: boolean;
    biometry_review_complete: boolean;
    consent_signed: boolean;
    post_op_day_1_complete: boolean;
  };
  data_limitations: string[];
  insufficient_data: boolean;
}

export interface FhirExportReadiness {
  packet_renderable: boolean;
  document_reference_id: string | null;
  schema_version?: string;
  all_signed?: boolean;
  extensions_present: string[];
  submission_status: "not_submitted";
  transport: "none";
  boundary?: string;
  reason?: string;
  insufficient_data: boolean;
}

export interface SafetyBoundary {
  key: string;
  asserted: boolean;
  statement: string;
}

export interface AdvancedClinicalIntelligenceResponse {
  encounter_id: number;
  organization_id: number;
  patient_id: number | null;
  patient_identifier: string | null;
  patient_name: string | null;
  encounter_type: string;
  visit_mode: string;
  active_laterality: string;
  retina_summary: RetinaSummary;
  glaucoma_summary: GlaucomaSummary;
  cataract_summary: CataractSummary;
  fhir_export_readiness: FhirExportReadiness;
  data_limitations: string[];
  safety_boundaries: SafetyBoundary[];
  generated_at: string;
  demo_mode: boolean;
  submission_status: "not_submitted";
  disclosure: string;
}
