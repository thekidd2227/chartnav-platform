// Phase 82 — Note Validation Rail types.

export type NoteValidationStatus = "pass" | "warning" | "missing" | "blocked";

export type NoteValidationSource =
  | "vitals"
  | "fundus"
  | "visit_draft"
  | "retina_summary"
  | "anti_vegf"
  | "glaucoma"
  | "cataract"
  | "signed_lock";

export interface NoteValidationCheck {
  check_id: string;
  category: string;
  label: string;
  status: NoteValidationStatus;
  laterality: "OD" | "OS" | "OU" | null;
  source: NoteValidationSource;
  detail: string;
  requires_provider_acknowledgement: boolean;
  source_artifact_id: number | null;
}

export interface NoteValidationRailResponse {
  encounter_id: number;
  organization_id: number;
  patient_id: number | null;
  generated_at: string;
  demo_mode: boolean;
  checks: NoteValidationCheck[];
  totals: Record<NoteValidationStatus, number>;
  acknowledgements_required: number;
  disclosure: string;
}

export type AcknowledgementType = "acknowledged" | "rescinded";

export interface NoteValidationAcknowledgement {
  id: number;
  audit_created_at: string | null;
  encounter_id: number;
  actor_id: number | null;
  actor_display_name: string | null;
  actor_role: string | null;
  validation_item_id: string;
  validation_category: string;
  acknowledgement_type: AcknowledgementType;
  acknowledgement_timestamp: string;
}
