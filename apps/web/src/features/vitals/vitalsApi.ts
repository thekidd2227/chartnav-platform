import type { VitalWorkup, VitalWorkupPayload } from "./vitalsTypes";

const BASE = "";

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

export function listVitalsWorkups(encounterId: number): Promise<VitalWorkup[]> {
  return apiFetch(`/api/v1/encounters/${encounterId}/vitals-workups`);
}

export function createVitalsWorkup(
  encounterId: number,
  body: VitalWorkupPayload,
): Promise<VitalWorkup> {
  return apiFetch(`/api/v1/encounters/${encounterId}/vitals-workups`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getVitalsWorkup(workupId: number): Promise<VitalWorkup> {
  return apiFetch(`/api/v1/vitals-workups/${workupId}`);
}

export function updateVitalsWorkup(
  workupId: number,
  body: VitalWorkupPayload,
): Promise<VitalWorkup> {
  return apiFetch(`/api/v1/vitals-workups/${workupId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function reviewVitalsWorkup(workupId: number): Promise<VitalWorkup> {
  return apiFetch(`/api/v1/vitals-workups/${workupId}/review`, {
    method: "POST",
    body: JSON.stringify({ reviewed: true }),
  });
}

export function signVitalsWorkup(
  workupId: number,
  attested: boolean,
): Promise<VitalWorkup> {
  return apiFetch(`/api/v1/vitals-workups/${workupId}/sign`, {
    method: "POST",
    body: JSON.stringify({ attested }),
  });
}
