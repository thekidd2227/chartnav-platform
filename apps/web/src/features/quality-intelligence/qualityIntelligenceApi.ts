// Phase 89 — Quality intelligence API client.

import { API_URL } from "../../api";
import type {
  QualityMeasuresResponse,
  QualityResponsePayload,
  QualityResponseRecord,
} from "./qualityIntelligenceTypes";

const PATH_PREFIX = "/api/v1";

function resolveIdentity(explicit?: string | null): string | null {
  if (explicit && explicit.length > 0) return explicit;
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const stored = window.localStorage.getItem("chartnav.devIdentity");
      if (stored && stored.length > 0) return stored;
    }
  } catch {
    /* localStorage can throw in restricted contexts; treat as no identity. */
  }
  return null;
}

async function apiFetch<T>(
  path: string,
  init: (RequestInit & { email?: string | null }) | undefined = undefined,
): Promise<T> {
  const { email, ...fetchInit } = init ?? {};
  const headers = new Headers(fetchInit.headers || {});
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

export function getQualityMeasures(
  encounterId: number,
  options: { program_year?: number; email?: string | null } = {},
): Promise<QualityMeasuresResponse> {
  const { program_year, email } = options;
  const qs = program_year ? `?program_year=${program_year}` : "";
  return apiFetch(`/encounters/${encounterId}/quality-measures${qs}`, {
    email,
  });
}

export function postQualityResponse(
  encounterId: number,
  measureId: string,
  payload: QualityResponsePayload,
  email?: string | null,
): Promise<QualityResponseRecord> {
  return apiFetch(
    `/encounters/${encounterId}/quality-measures/${encodeURIComponent(measureId)}/response`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      email,
    },
  );
}
