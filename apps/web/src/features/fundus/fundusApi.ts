// Fundus drawing assist feature client.
//
// Phase 63C — routes through the configured API_URL and sends
// `X-User-Email` for header-mode demo auth. Previously this module
// used relative "/api/v1/..." paths against the Vite origin, which
// 404'd because the dev server doesn't proxy /api/v1 to the backend.
//
// Demo identity discovery order:
//   1. explicit `email` arg passed by the panel
//   2. `localStorage.chartnav.devIdentity`
//   3. omitted — backend returns 401 with a clear error
//
// No vendor API key is read. No real PHI processed.

import { API_URL } from "../../api";
import type {
  FundusChart,
  FundusChartCreateRequest,
  FundusChartGenerateRequest,
  FundusChartGenerateResponse,
  FundusChartListItem,
  FundusChartUpdateRequest,
} from "./fundusTypes";

const PATH_PREFIX = "/api/v1";

function resolveIdentity(explicit?: string | null): string | null {
  if (explicit && explicit.length > 0) return explicit;
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const stored = window.localStorage.getItem("chartnav.devIdentity");
      if (stored && stored.length > 0) return stored;
    }
  } catch {
    // localStorage can throw in restricted contexts; treat as no identity.
  }
  return null;
}

async function apiFetch<T>(
  path: string,
  init: (RequestInit & { email?: string | null }) | undefined = undefined,
): Promise<T> {
  const { email, ...fetchInit } = init ?? {};
  const headers = new Headers(fetchInit.headers || {});
  if (!headers.has("Content-Type") && fetchInit.body) {
    headers.set("Content-Type", "application/json");
  }
  const identity = resolveIdentity(email);
  if (identity && !headers.has("X-User-Email")) {
    headers.set("X-User-Email", identity);
  }
  const res = await fetch(`${API_URL}${PATH_PREFIX}${path}`, {
    ...fetchInit,
    headers,
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
  email?: string | null,
): Promise<FundusChartListItem[]> {
  return apiFetch(`/encounters/${encounterId}/fundus-charts`, { email });
}

export function generateFundusChart(
  encounterId: number,
  body: FundusChartGenerateRequest,
  email?: string | null,
): Promise<FundusChartGenerateResponse> {
  return apiFetch(`/encounters/${encounterId}/fundus-charts/generate`, {
    method: "POST",
    body: JSON.stringify(body),
    email,
  });
}

export function createFundusChart(
  encounterId: number,
  body: FundusChartCreateRequest,
  email?: string | null,
): Promise<{ chart_id: number; status: string }> {
  return apiFetch(`/encounters/${encounterId}/fundus-charts`, {
    method: "POST",
    body: JSON.stringify(body),
    email,
  });
}

export function getFundusChart(
  chartId: number,
  email?: string | null,
): Promise<FundusChart> {
  return apiFetch(`/fundus-charts/${chartId}`, { email });
}

export function updateFundusChart(
  chartId: number,
  body: FundusChartUpdateRequest,
  email?: string | null,
): Promise<FundusChart> {
  return apiFetch(`/fundus-charts/${chartId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    email,
  });
}

export function renderFundusChart(
  chartId: number,
  email?: string | null,
): Promise<{ chart_id: number; rendered_svg: string }> {
  return apiFetch(`/fundus-charts/${chartId}/render`, {
    method: "POST",
    email,
  });
}

export function reviewFundusChart(
  chartId: number,
  notes?: string,
  email?: string | null,
): Promise<{ chart_id: number; status: string; reviewed_at: string }> {
  return apiFetch(`/fundus-charts/${chartId}/review`, {
    method: "POST",
    body: JSON.stringify({ notes }),
    email,
  });
}

export function signFundusChart(
  chartId: number,
  email?: string | null,
): Promise<{ chart_id: number; status: string; signed_at: string }> {
  return apiFetch(`/fundus-charts/${chartId}/sign`, {
    method: "POST",
    body: JSON.stringify({ attested: true }),
    email,
  });
}
