// Phase 78 — Anti-VEGF injection rail types.

export type AntiVegfEye = "OD" | "OS";

export type AntiVegfDrugLabel =
  | "anti_vegf_generic"
  | "anti_vegf_biosimilar"
  | "anti_vegf_branded"
  | "other";

export type AntiVegfAuthStatus =
  | "not_required"
  | "pending"
  | "approved"
  | "denied"
  | "expired"
  | "unknown";

export interface AntiVegfInjection {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  eye: AntiVegfEye;
  drug_label: AntiVegfDrugLabel;
  injection_date: string;
  interval_weeks: number | null;
  next_due_date: string | null;
  authorization_status: AntiVegfAuthStatus;
  authorization_expires_on: string | null;
  lot_number: string | null;
  notes: string | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface AntiVegfHistory {
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  total_count: number;
  od_count: number;
  os_count: number;
  od_history: AntiVegfInjection[];
  os_history: AntiVegfInjection[];
  latest_od: AntiVegfInjection | null;
  latest_os: AntiVegfInjection | null;
  bilateral: boolean;
}

export type AntiVegfBucket =
  | "due_today"
  | "due_this_week"
  | "overdue"
  | "authorization_pending"
  | "authorization_expired";

export interface AntiVegfQueueItem {
  injection_id: number;
  patient_id: number;
  encounter_id: number | null;
  eye: AntiVegfEye;
  drug_label: AntiVegfDrugLabel;
  injection_date: string;
  next_due_date: string | null;
  authorization_status: AntiVegfAuthStatus;
  authorization_expires_on: string | null;
  lot_number: string | null;
  interval_weeks: number | null;
  patient_identifier: string | null;
  patient_name: string | null;
}

export interface AntiVegfBilateralAsymmetric {
  patient_id: number;
  od_bucket: AntiVegfBucket;
  os_bucket: AntiVegfBucket;
}

export interface AntiVegfReadinessQueue {
  generated_at: string;
  today: string;
  organization_id: number;
  demo_mode: boolean;
  buckets: Record<AntiVegfBucket, AntiVegfQueueItem[]>;
  bilateral_asymmetric: AntiVegfBilateralAsymmetric[];
  totals: Record<AntiVegfBucket, number>;
  disclosure: string;
}
