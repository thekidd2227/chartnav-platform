// Vitals workup feature client.
//
// Phase 63C — routes through the configured API_URL (the central
// `apps/web/src/api.ts` convention) and sends `X-User-Email` for
// header-mode demo auth. Previously this module used relative
// "/api/v1/..." paths against the Vite origin, which 404'd because
// the dev server doesn't proxy /api/v1 to the backend.
//
// Demo identity discovery order:
//   1. explicit `email` arg passed by the panel
//   2. `localStorage.chartnav.devIdentity` (set by the demo
//      identity selector in App.tsx)
//   3. omitted — backend returns 401 with a clear error
//
// No vendor API key is read. No real PHI processed.

import { API_URL } from "../../api";
import type {
  VitalsWorkup,
  VitalsWorkupCreateRequest,
  VitalsWorkupSignRequest,
  VitalsWorkupUpdateRequest,
} from "./vitalsTypes";

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

export function listVitalsWorkups(
  encounterId: number,
  email?: string | null,
): Promise<VitalsWorkup[]> {
  return apiFetch(`/encounters/${encounterId}/vitals-workups`, { email });
}

export function createVitalsWorkup(
  encounterId: number,
  body: VitalsWorkupCreateRequest,
  email?: string | null,
): Promise<VitalsWorkup> {
  return apiFetch(`/encounters/${encounterId}/vitals-workups`, {
    method: "POST",
    body: JSON.stringify(body),
    email,
  });
}

export function getVitalsWorkup(
  workupId: number,
  email?: string | null,
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}`, { email });
}

export function updateVitalsWorkup(
  workupId: number,
  body: VitalsWorkupUpdateRequest,
  email?: string | null,
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    email,
  });
}

export function reviewVitalsWorkup(
  workupId: number,
  email?: string | null,
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}/review`, {
    method: "POST",
    body: JSON.stringify({}),
    email,
  });
}

export function signVitalsWorkup(
  workupId: number,
  body: VitalsWorkupSignRequest = { attested: true },
  email?: string | null,
): Promise<VitalsWorkup> {
  return apiFetch(`/vitals-workups/${workupId}/sign`, {
    method: "POST",
    body: JSON.stringify(body),
    email,
  });
}
