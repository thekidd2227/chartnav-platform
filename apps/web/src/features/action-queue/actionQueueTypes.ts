// Phase 81 — Provider Action Item Queue types.

export type ActionQueueBucket =
  | "same_day"
  | "this_week"
  | "routine"
  | "informational";

export type ActionQueueSource =
  | "anti_vegf"
  | "glaucoma"
  | "cataract"
  | "visit_summary"
  | "signed_lock"
  | "staging"
  | "medication";

export interface ActionQueueItem {
  item_id: string;
  patient_id: number;
  patient_identifier: string | null;
  patient_name: string | null;
  encounter_id: number | null;
  laterality: "OD" | "OS" | "OU" | null;
  specialty_source: ActionQueueSource;
  category: string;
  label: string;
  detail: string;
  status: string;
  priority_bucket: ActionQueueBucket;
  source_artifact_id: number | null;
  created_at: string | null;
  due_at: string | null;
  insufficient_data: boolean;
  requires_provider_review: boolean;
}

export interface ProviderActionQueue {
  generated_at: string;
  organization_id: number;
  demo_mode: boolean;
  buckets: Record<ActionQueueBucket, ActionQueueItem[]>;
  totals: Record<ActionQueueBucket, number>;
  total_items: number;
  sources_present: ActionQueueSource[];
  disclosure: string;
}
