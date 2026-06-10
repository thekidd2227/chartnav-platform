// Phase 86 — Subspecialty Adaptive Workspace types.

export type EncounterType = "retina" | "glaucoma" | "cataract" | "comprehensive";

export type PanelCode =
  | "provider_action_queue"
  | "note_validation"
  | "retina_visit_summary"
  | "retina_visit_packet"
  | "anti_vegf_injection"
  | "glaucoma_cockpit"
  | "cataract_workflow"
  | "disease_staging"
  | "medication_safety";

export interface PanelRef {
  code: PanelCode;
  label: string;
}

export interface WorkspaceProfile {
  code: EncounterType;
  label: string;
  prioritized_panels: PanelRef[];
  visible_panels: PanelRef[];
  collapsed_panels: PanelRef[];
  panel_order: PanelCode[];
}

export interface WorkspaceProfileResponse {
  encounter_id: number;
  organization_id: number;
  patient_id: number | null;
  patient_name: string | null;
  patient_identifier: string | null;
  provider_name: string | null;
  status: string;
  encounter_type: EncounterType;
  encounter_type_label: string;
  profile: WorkspaceProfile;
  supported_encounter_types: Array<{ code: EncounterType; label: string }>;
  generated_at: string;
  disclosure: string;
}
