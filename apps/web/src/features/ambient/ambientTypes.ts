export type ScribeStatus =
  | "draft"
  | "processing"
  | "ready_for_review"
  | "reviewed"
  | "finalized"
  | "discarded";

export type ScribeInputMode =
  | "pasted_text"
  | "transcript"
  | "audio_placeholder";

export interface AmbientForbiddenActions {
  diagnosis: boolean;
  orders: boolean;
  referrals: boolean;
  patient_message: boolean;
  billing_or_coding: boolean;
  auto_sign: boolean;
  image_interpretation: boolean;
}

export interface AmbientStructuredFacts {
  chief_complaint: string;
  hpi_summary: string;
  visual_acuity: string;
  iop: string;
  imaging_metadata: string;
  assessment_context: string;
  plan_as_stated: string;
}

export interface AmbientDraftPayload {
  structured_facts: AmbientStructuredFacts;
  draft_note: string;
  safety_flags: string[];
  missing_information: string[];
  requires_provider_review: boolean;
  forbidden_actions: AmbientForbiddenActions;
  ai_model_name: string;
  confidence: Record<string, unknown>;
}

export interface ScribeSessionResponse {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  created_by_user_id: number;
  status: ScribeStatus;
  input_mode: ScribeInputMode;
  source_text: string | null;
  transcript_text: string | null;
  draft_note_text: string | null;
  structured_note_json: Record<string, unknown> | null;
  linked_artifact_id: number | null;
  review_notes: string | null;
  finalized_at: string | null;
  reviewed_at: string | null;
  reviewed_by_user_id: number | null;
  discarded_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  is_terminal: boolean;
}

export interface ScribeSessionWithAmbientDraft extends ScribeSessionResponse {
  ambient_draft?: AmbientDraftPayload;
}

export interface CreateScribeSessionRequest {
  input_mode: ScribeInputMode;
  source_text?: string;
  transcript_text?: string;
  encounter_id?: number;
}

export interface DraftAmbientRequest {
  fake_data_context: boolean;
}

export interface ReviewScribeSessionRequest {
  review_notes?: string;
}
