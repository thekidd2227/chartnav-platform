// Phase 89 — Quality Intelligence types.

export type QualityResponseType =
  | "met"
  | "exception"
  | "exclusion"
  | "not_applicable"
  | "incomplete";

export type QualityResponseStatus =
  | "pending"
  | "met"
  | "exception"
  | "exclusion"
  | "not_applicable"
  | "incomplete";

export interface QualityMeasureItem {
  measure_id: string;
  measure_name: string;
  program_year: number;
  applicable: boolean;
  response_status: QualityResponseStatus;
  response_exception_code: string | null;
  responded_by_display: string | null;
  responded_by_role: string | null;
  responded_at: string | null;
  missing_structured_fields: string[];
  present_structured_fields: string[];
  required_fields: string[];
  exception_codes: string[];
  verified_for_submission: boolean;
  internal_demo_only: boolean;
  submission_status: "not_submitted";
}

export interface QualityMeasuresResponse {
  encounter_id: number;
  patient_id: number | null;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  encounter_type: string | null;
  generated_at: string;
  demo_mode: boolean;
  items: QualityMeasureItem[];
  counts: {
    total: number;
    applicable: number;
    incomplete: number;
    completed: number;
  };
  supported_response_types: QualityResponseType[];
  internal_demo_specs_present: boolean;
  submission_status: "not_submitted";
  disclosure: string;
}

export interface QualityResponsePayload {
  response_type: QualityResponseType;
  exception_code?: string | null;
}

export interface QualityResponseRecord {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number;
  measure_id: string;
  response_type: QualityResponseType;
  exception_code: string | null;
  responded_by_user_id: number;
  responded_by_display: string | null;
  responded_by_role: string | null;
  responded_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}
