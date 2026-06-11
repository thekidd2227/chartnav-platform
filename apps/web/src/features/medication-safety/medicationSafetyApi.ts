// Phase 90 — Ophthalmic Medication Safety API client.

import { API_URL } from "../../api";
import type {
  MedicationSafetyEvent,
  MedicationSafetyResponse,
  OphthalmicMedicationCreatePayload,
  OphthalmicMedicationRecord,
} from "./medicationSafetyTypes";

const PATH_PREFIX = "/api/v1";

function resolveIdentity(explicit?: string | null): string | null {
  if (explicit && explicit.length > 0) return explicit;
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const stored = window.localStorage.getItem("chartnav.devIdentity");
      if (stored && stored.length > 0) return stored;
    }
  } catch {
    /* localStorage can throw in restricted contexts. */
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

export function getMedicationSafety(
  patientId: number,
  email?: string | null,
): Promise<MedicationSafetyResponse> {
  return apiFetch(`/patients/${patientId}/medication-safety`, { email });
}

export function postOphthalmicMedication(
  encounterId: number,
  payload: OphthalmicMedicationCreatePayload,
  email?: string | null,
): Promise<OphthalmicMedicationRecord> {
  return apiFetch(`/encounters/${encounterId}/ophthalmic-medications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    email,
  });
}

export function postAcknowledgeEvent(
  eventId: number,
  email?: string | null,
): Promise<MedicationSafetyEvent> {
  return apiFetch(`/medication-safety-events/${eventId}/acknowledge`, {
    method: "POST",
    email,
  });
}
