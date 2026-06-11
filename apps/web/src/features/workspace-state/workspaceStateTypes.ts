// Phase 91 — Unified Ophthalmology Workspace State types.

import type { EncounterType, PanelCode } from "../workspace-profile/workspaceProfileTypes";

export type VisitMode =
  | "intake"
  | "surgical_pre_op"
  | "post_op"
  | "follow_up"
  | "lab_review"
  | "unscheduled";

export type ActiveLaterality = "OD" | "OS" | "OU" | "NA";

export interface WorkspaceStateEmphasis {
  emphasised_panels: PanelCode[];
  secondary_panels: PanelCode[];
  total_panels: number;
}

export interface WorkspaceStateResponse {
  encounter_id: number;
  organization_id: number;
  patient_id: number | null;
  patient_identifier: string | null;
  patient_name: string | null;
  provider_name: string | null;
  status: string;
  encounter_type: EncounterType;
  encounter_type_label: string;
  visit_mode: VisitMode;
  visit_mode_label: string;
  active_laterality: ActiveLaterality;
  active_laterality_label: string;
  profile: {
    code: EncounterType;
    label: string;
    panel_order: PanelCode[];
    panel_labels: Record<PanelCode, string>;
  };
  emphasis: WorkspaceStateEmphasis;
  laterality_linked_panels: string[];
  supported_visit_modes: Array<{ code: VisitMode; label: string }>;
  supported_active_lateralities: Array<{ code: ActiveLaterality; label: string }>;
  generated_at: string;
  disclosure: string;
}
