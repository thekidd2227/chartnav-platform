// Phase 88 — Imaging Metadata Review Linkage types.

export type ImagingLaterality = "OD" | "OS" | "OU" | "NA";

export type ImagingModalityGroup =
  | "oct"
  | "fundus"
  | "visual_field"
  | "biometry"
  | "topography"
  | "external_record"
  | "other";

export type ImagingReviewStatus =
  | "pending_upload"
  | "uploaded"
  | "ready_for_review"
  | "reviewed"
  | "archived";

export interface ImagingMetadataItem {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  modality: string;
  modality_group: ImagingModalityGroup;
  laterality: ImagingLaterality;
  acquisition_date: string | null;
  device_manufacturer: string | null;
  device_model: string | null;
  source_system: string | null;
  review_status: ImagingReviewStatus;
  reviewed_by_user_id: number | null;
  reviewed_by_display: string | null;
  reviewed_by_role: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  metadata_hash: string;
}

export interface ImagingMetadataResponse {
  encounter_id: number;
  patient_id: number | null;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  generated_at: string;
  demo_mode: boolean;
  items: ImagingMetadataItem[];
  by_modality_group: Record<ImagingModalityGroup, ImagingMetadataItem[]>;
  counts: {
    total: number;
    reviewed: number;
    unreviewed: number;
  };
  modality_groups_present: ImagingModalityGroup[];
  disclosure: string;
}
