import type {
  VitalsWorkup,
  VitalsWorkupCreateRequest,
  VitalsWorkupSignRequest,
  VitalsWorkupUpdateRequest,
} from "./vitalsTypes";

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

export function listVitalsWorkups(
  encounterId: number,
): Promise<VitalsWorkup[]> {
  return apiFetch(`/encounters/${encounterId}/vitals-workups`);
}

export function createVitalsWorkup(
  encounterId: number,
  body: VitalsWorkupCreateRequest,
): Promise<VitalsWorkup> {
  return apiFetch(`/encounters/${encounterId}/vitals-workups`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getVitalsWorkup(workupId: number): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}`);
}

export function updateVitalsWorkup(
  workupId: number,
  body: VitalsWorkupUpdateRequest,
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function reviewVitalsWorkup(
  workupId: number,
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}/review`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function signVitalsWorkup(
  workupId: number,
  body: VitalsWorkupSignRequest = { attested: true },
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}/sign`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
