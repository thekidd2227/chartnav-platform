// Phase 76 — Retina Visit Summary aggregator response shape.

export interface RetinaSummaryArtifactSection {
  count: number;
  latest_id: number | null;
  latest_status: string | null;
  latest_created_at?: string | null;
  latest_reviewed_at?: string | null;
  latest_signed_at?: string | null;
  latest_finalized_at?: string | null;
  latest_warning_count?: number;
  latest_element_count?: number;
  latest_laterality?: string;
}

export interface RetinaSummaryBlocker {
  kind: string;
  message: string;
}

export interface RetinaSummaryRoleCapabilities {
  role: string;
  can_review: boolean;
  can_sign: boolean;
  can_create_intake: boolean;
  explainer: string;
}

export type RetinaArtifactType = "vitals_workup" | "visit_draft" | "fundus_chart";
export type RetinaEventType = "created" | "reviewed" | "signed";

export interface RetinaSummaryEvent {
  artifact_type: RetinaArtifactType;
  event_type: RetinaEventType;
  timestamp: string;
  ref_id: number;
  actor_display_name: string | null;
  actor_role: string | null;
  warning_count?: number;
  element_count?: number;
  laterality?: string;
  source_type?: string;
}

export interface RetinaVisitSummary {
  encounter_id: number;
  patient_id: number | null;
  organization_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  encounter_status: string;
  encounter_started_at: string | null;
  demo_mode: boolean;
  vitals: RetinaSummaryArtifactSection;
  visit_draft: RetinaSummaryArtifactSection;
  fundus: RetinaSummaryArtifactSection;
  blockers: RetinaSummaryBlocker[];
  role_capabilities: RetinaSummaryRoleCapabilities;
  evidence_timeline: RetinaSummaryEvent[];
  audit_disclosure: string;
}
