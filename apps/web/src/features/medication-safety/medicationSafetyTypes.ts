// Phase 90 — Ophthalmic Medication Safety & Adherence types.

export type PreservativeType = "BAK" | "preservative_free" | "other" | "unknown";
export type EventSeverity = "hard_stop" | "alert" | "advisory";
export type EventStatus = "active" | "acknowledged" | "resolved";
export type EventLaterality = "OD" | "OS" | "OU" | "none";

export interface OphthalmicMedicationRecord {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  medication_name: string;
  medication_class: string;
  route: string;
  laterality: string;
  dose_per_day: number;
  preservative_flag: boolean;
  preservative_type: PreservativeType;
  started_on: string | null;
  discontinued_on: string | null;
  last_fill_date: string | null;
  days_supply: number | null;
  supply_through: string | null;
  refill_gap_days: number | null;
  active: boolean;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  recorded_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface MedicationSafetyEvent {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  medication_id: number | null;
  rule_key: string;
  severity: EventSeverity;
  laterality: EventLaterality;
  status: EventStatus;
  message: string;
  acknowledged_by_user_id: number | null;
  acknowledged_by_display_name: string | null;
  acknowledged_by_role: string | null;
  acknowledged_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MedicationSafetyRule {
  id: number;
  organization_id: number | null;
  rule_key: string;
  rule_name: string;
  medication_class: string | null;
  trigger_context: string;
  severity: EventSeverity;
  message: string;
  requires_acknowledgement: boolean;
  status: "active" | "inactive";
  internal_demo_only: boolean;
  verified_for_clinical_use: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface MedicationSafetySignals {
  preservative_burden_count: number;
  refill_gap_count: number;
  refill_gaps: Array<{
    medication_id: number;
    medication_name: string;
    refill_gap_days: number | null;
    last_fill_date: string | null;
    supply_through: string | null;
  }>;
  active_medication_count: number;
  medications_reviewed_count: number;
  insufficient_data: boolean;
}

export interface MedicationSafetyResponse {
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  generated_at: string;
  demo_mode: boolean;
  medications: OphthalmicMedicationRecord[];
  active_medication_count: number;
  events: MedicationSafetyEvent[];
  counts: {
    active_events: number;
    acknowledged_events: number;
    resolved_events: number;
    total_events: number;
  };
  signals: MedicationSafetySignals;
  rules: MedicationSafetyRule[];
  internal_demo_rules_present: boolean;
  submission_status: "not_submitted";
  disclosure: string;
}

export interface OphthalmicMedicationCreatePayload {
  medication_name: string;
  medication_class: string;
  route: string;
  laterality: string;
  dose_per_day: number;
  preservative_type?: PreservativeType;
  started_on?: string | null;
  discontinued_on?: string | null;
  last_fill_date?: string | null;
  days_supply?: number | null;
}
