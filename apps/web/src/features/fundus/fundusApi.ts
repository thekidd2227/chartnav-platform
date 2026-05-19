import type {
  FundusChart,
  FundusChartCreateRequest,
  FundusChartGenerateRequest,
  FundusChartGenerateResponse,
  FundusChartListItem,
  FundusChartUpdateRequest,
} from "./fundusTypes";

const BASE = "/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg =
      (body?.detail as { reason?: string } | undefined)?.reason ??
      (typeof body?.detail === "string" ? body.detail : null) ??
      `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export function listFundusCharts(
  encounterId: number,
): Promise<FundusChartListItem[]> {
  return apiFetch(`/encounters/${encounterId}/fundus-charts`);
}

export function generateFundusChart(
  encounterId: number,
  body: FundusChartGenerateRequest,
): Promise<FundusChartGenerateResponse> {
  return apiFetch(`/encounters/${encounterId}/fundus-charts/generate`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function createFundusChart(
  encounterId: number,
  body: FundusChartCreateRequest,
): Promise<{ chart_id: number; status: string }> {
  return apiFetch(`/encounters/${encounterId}/fundus-charts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getFundusChart(chartId: number): Promise<FundusChart> {
  return apiFetch(`/fundus-charts/${chartId}`);
}

export function updateFundusChart(
  chartId: number,
  body: FundusChartUpdateRequest,
): Promise<FundusChart> {
  return apiFetch(`/fundus-charts/${chartId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function renderFundusChart(
  chartId: number,
): Promise<{ chart_id: number; rendered_svg: string }> {
  return apiFetch(`/fundus-charts/${chartId}/render`, { method: "POST" });
}

export function reviewFundusChart(
  chartId: number,
  notes?: string,
): Promise<{ chart_id: number; status: string; reviewed_at: string }> {
  return apiFetch(`/fundus-charts/${chartId}/review`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export function signFundusChart(
  chartId: number,
): Promise<{ chart_id: number; status: string; signed_at: string }> {
  return apiFetch(`/fundus-charts/${chartId}/sign`, {
    method: "POST",
    body: JSON.stringify({ attested: true }),
  });
}
