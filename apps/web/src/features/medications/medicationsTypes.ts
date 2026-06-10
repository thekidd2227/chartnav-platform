// Phase 85 — Medication safety types.

export type MedicationClass =
  | "pgf2_analog"
  | "beta_blocker"
  | "alpha_agonist"
  | "carbonic_anhydrase_inhibitor"
  | "rho_kinase_inhibitor"
  | "combination_drop"
  | "steroid_drop"
  | "nsaid_drop"
  | "antibiotic_drop"
  | "anti_vegf_intravitreal"
  | "lubricant"
  | "oral_systemic_other";

export type MedicationRoute = "drops" | "oral" | "intravitreal";
export type MedicationLaterality = "OD" | "OS" | "OU" | "NA";
export type ReactionType =
  | "rash"
  | "swelling"
  | "anaphylaxis"
  | "gi_distress"
  | "respiratory"
  | "other";
export type AllergySeverity = "mild" | "moderate" | "severe";

export type RefillGapStatus =
  | "on_track"
  | "gap"
  | "no_history"
  | "discontinued";

export interface MedicationRefillGap {
  has_history: boolean;
  last_refill_date: string | null;
  expected_days_supply: number | null;
  supply_through: string | null;
  gap_days: number | null;
  status: RefillGapStatus;
}

export interface MedicationRecord {
  id: number;
  organization_id: number;
  patient_id: number;
  encounter_id: number | null;
  medication_name: string;
  medication_class: MedicationClass;
  medication_class_label: string;
  route: MedicationRoute;
  laterality: MedicationLaterality;
  dose_per_day: number;
  preservative_flag: boolean;
  started_on: string | null;
  discontinued_on: string | null;
  prescriber_user_id: number | null;
  prescriber_display_name: string | null;
  recorded_by_user_id: number;
  recorded_by_display_name: string | null;
  recorded_by_role: string | null;
  recorded_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  is_active: boolean;
  refill_gap: MedicationRefillGap;
  refill_count: number;
}

export interface RefillRecord {
  id: number;
  organization_id: number;
  patient_id: number;
  medication_id: number;
  encounter_id: number | null;
  refill_date: string | null;
  expected_days_supply: number;
  recorded_by_user_id: number;
  recorded_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AllergyRecord {
  id: number;
  organization_id: number;
  patient_id: number;
  substance: string;
  reaction_type: ReactionType;
  reaction_type_label: string;
  severity: AllergySeverity;
  recorded_by_user_id: number;
  recorded_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MedicationSignals {
  polypharmacy_count: number;
  preservative_burden: number;
  refill_gaps: Array<{
    medication_id: number;
    medication_name: string;
    gap_days: number;
    last_refill_date: string | null;
    supply_through: string | null;
  }>;
  allergy_matches: Array<{
    medication_id: number;
    medication_name: string;
    allergy_id: number;
    allergy_substance: string;
    allergy_severity: AllergySeverity;
  }>;
  insufficient_data: boolean;
}

export interface MedicationsPanelResponse {
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  organization_id: number;
  generated_at: string;
  demo_mode: boolean;
  medications: MedicationRecord[];
  refills: RefillRecord[];
  allergies: AllergyRecord[];
  supported_medication_classes: Array<{ code: MedicationClass; label: string }>;
  supported_routes: MedicationRoute[];
  supported_lateralities: MedicationLaterality[];
  supported_reaction_types: Array<{ code: ReactionType; label: string }>;
  supported_severities: AllergySeverity[];
  signals: MedicationSignals;
  disclosure: string;
}

export interface MedicationCreatePayload {
  medication_name: string;
  medication_class: MedicationClass;
  route: MedicationRoute;
  laterality: MedicationLaterality;
  dose_per_day: number;
  preservative_flag: boolean;
  started_on?: string | null;
  discontinued_on?: string | null;
  prescriber_display_name?: string | null;
}

export interface RefillCreatePayload {
  expected_days_supply: number;
  refill_date?: string | null;
  encounter_id?: number | null;
}

export interface AllergyCreatePayload {
  substance: string;
  reaction_type: ReactionType;
  severity: AllergySeverity;
}
