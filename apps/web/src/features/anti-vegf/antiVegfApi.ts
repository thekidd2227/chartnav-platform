// Phase 78 — Anti-VEGF API client.

import { API_URL } from "../../api";
import type {
  AntiVegfEye,
  AntiVegfHistory,
  AntiVegfReadinessQueue,
} from "./antiVegfTypes";

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

export function getInjectionHistory(
  patientId: number,
  options: { eye?: AntiVegfEye; email?: string | null } = {},
): Promise<AntiVegfHistory> {
  const { eye, email } = options;
  const qs = eye ? `?eye=${eye}` : "";
  return apiFetch(`/patients/${patientId}/anti-vegf-injections${qs}`, { email });
}

export interface InjectionCreateRequest {
  eye: AntiVegfEye;
  drug_label?: string;
  injection_date: string;
  interval_weeks?: number | null;
  next_due_date?: string | null;
  authorization_status?: string;
  authorization_expires_on?: string | null;
  lot_number?: string | null;
  notes?: string | null;
  encounter_id?: number | null;
}

export function recordInjection(
  patientId: number,
  body: InjectionCreateRequest,
  email?: string | null,
): Promise<unknown> {
  return apiFetch(`/patients/${patientId}/anti-vegf-injections`, {
    method: "POST",
    body: JSON.stringify(body),
    email,
  });
}

export function getReadinessQueue(
  email?: string | null,
): Promise<AntiVegfReadinessQueue> {
  return apiFetch(`/anti-vegf/readiness-queue`, { email });
}
