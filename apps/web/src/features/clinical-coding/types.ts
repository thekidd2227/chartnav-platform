// Phase 64 — Clinical Coding Intelligence types.
// Backend contract lives in apps/api/app/api/routes.py (Phase 64 block).

export type SpecialtyTag =
  | "retina"
  | "glaucoma"
  | "cataract"
  | "cornea"
  | "oculoplastics"
  | "general";

export interface ClinicalCodingVersion {
  id: number;
  version_label: string;
  source_authority: string;
  source_url: string;
  release_date: string;
  effective_start_date: string;
  effective_end_date: string | null;
  is_active: 0 | 1;
  parse_status: string;
  checksum_sha256: string;
  downloaded_at: string;
  parsed_at: string | null;
  activated_at: string | null;
}

export interface CodeRow {
  id: number;
  code: string;
  normalized_code: string;
  is_billable: 0 | 1;
  short_description: string;
  long_description: string;
  chapter_code: string | null;
  chapter_title: string | null;
  category_code: string | null;
  parent_code: string | null;
  specificity_flags: string | null;
}

export interface SupportHint {
  id: number;
  specialty_tag: SpecialtyTag;
  workflow_area:
    | "specificity_prompt"
    | "claim_support_hint"
    | "search"
    | "favorites";
  diagnosis_code_pattern: string;
  advisory_hint: string;
  specificity_prompt: string | null;
  source_reference: string | null;
}

export interface CodeDetail extends CodeRow {
  children: Array<Pick<CodeRow, "code" | "short_description" | "is_billable">>;
  support_hints: SupportHint[];
  source_file: string | null;
  source_line_no: number | null;
}

export interface SearchResponse {
  version: Pick<
    ClinicalCodingVersion,
    | "id"
    | "version_label"
    | "source_authority"
    | "source_url"
    | "effective_start_date"
    | "effective_end_date"
  >;
  query: string;
  limit: number;
  result_count: number;
  results: CodeRow[];
}

export interface SpecialtyBundle {
  specialty_tag: SpecialtyTag;
  label: string;
  pattern: string;
  codes?: Array<{
    code: string;
    short_description: string;
    is_billable: 0 | 1;
    specificity_flags: string | null;
  }>;
}

export interface FavoriteRow {
  id: number;
  organization_id: number;
  user_id: number;
  code: string;
  specialty_tag: SpecialtyTag | null;
  usage_count: number;
  is_pinned: 0 | 1;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}
