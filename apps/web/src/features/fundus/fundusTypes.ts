export type Laterality = "OD" | "OS" | "OU";
export type FundusChartStatus = "draft" | "reviewed" | "signed";
export type FundusChartSourceType = "ai_generated" | "manual" | "imported";

export interface FundusDrawingElement {
  type: string;
  laterality: Laterality;
  clock_start: number | null;
  clock_end: number | null;
  zone: "posterior_pole" | "equator" | "ora_serrata";
  color: string;
  label: string;
}

export interface FundusDrawingJson {
  version: number;
  elements: FundusDrawingElement[];
}

export interface FundusChart {
  id: number;
  organization_id: number;
  encounter_id: number;
  patient_id: number;
  laterality: Laterality;
  status: FundusChartStatus;
  source_type: FundusChartSourceType;
  findings_json: Record<string, unknown> | null;
  drawing_json: FundusDrawingJson | null;
  rendered_svg: string | null;
  ai_model_name: string | null;
  ai_confidence_json: Record<string, unknown> | null;
  warnings_json: string[] | null;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  signed_by_user_id: number | null;
  signed_at: string | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface FundusChartListItem {
  id: number;
  laterality: Laterality;
  status: FundusChartStatus;
  source_type: FundusChartSourceType;
  reviewed_at: string | null;
  signed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FundusChartGenerateRequest {
  findings_text: string;
  laterality?: Laterality;
  note_version_id?: number;
}

export interface FundusChartGenerateResponse {
  chart_id: number;
  laterality: Laterality;
  warnings: string[];
  drawing_json: FundusDrawingJson;
  ai_model_name: string;
  status: FundusChartStatus;
}

export interface FundusChartCreateRequest {
  laterality: Laterality;
  drawing_json?: FundusDrawingJson;
  findings_json?: Record<string, unknown>;
  source_type?: FundusChartSourceType;
  note_version_id?: number;
}

export interface FundusChartUpdateRequest {
  drawing_json?: FundusDrawingJson;
  findings_json?: Record<string, unknown>;
  laterality?: Laterality;
  status?: FundusChartStatus;
}
