// Phase 84 — Disease staging API client.

import { API_URL } from "../../api";
import type {
  DiseaseStageCreatePayload,
  DiseaseStageRecord,
  DiseaseStagingPanelResponse,
} from "./diseaseStagingTypes";

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

export function getDiseaseStaging(
  patientId: number,
  options: { diagnosis_code?: string; email?: string | null } = {},
): Promise<DiseaseStagingPanelResponse> {
  const { diagnosis_code, email } = options;
  const qs = diagnosis_code
    ? `?diagnosis_code=${encodeURIComponent(diagnosis_code)}`
    : "";
  return apiFetch(`/patients/${patientId}/disease-staging${qs}`, { email });
}

export function postDiseaseStage(
  encounterId: number,
  payload: DiseaseStageCreatePayload,
  email?: string | null,
): Promise<DiseaseStageRecord> {
  return apiFetch(`/encounters/${encounterId}/disease-staging`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    email,
  });
}
