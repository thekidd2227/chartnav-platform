// Phase 85 — Medication safety API client.

import { API_URL } from "../../api";
import type {
  AllergyCreatePayload,
  AllergyRecord,
  MedicationCreatePayload,
  MedicationRecord,
  MedicationsPanelResponse,
  RefillCreatePayload,
  RefillRecord,
} from "./medicationsTypes";

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

export function getMedications(
  patientId: number,
  email?: string | null,
): Promise<MedicationsPanelResponse> {
  return apiFetch(`/patients/${patientId}/medications`, { email });
}

export function postMedication(
  encounterId: number,
  payload: MedicationCreatePayload,
  email?: string | null,
): Promise<MedicationRecord> {
  return apiFetch(`/encounters/${encounterId}/medications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    email,
  });
}

export function patchMedicationDiscontinue(
  medicationId: number,
  discontinuedOn?: string | null,
  email?: string | null,
): Promise<MedicationRecord> {
  const body =
    discontinuedOn !== undefined && discontinuedOn !== null
      ? { discontinued_on: discontinuedOn }
      : {};
  return apiFetch(`/medications/${medicationId}/discontinue`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    email,
  });
}

export function postRefill(
  medicationId: number,
  payload: RefillCreatePayload,
  email?: string | null,
): Promise<RefillRecord> {
  return apiFetch(`/medications/${medicationId}/refills`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    email,
  });
}

export function postAllergy(
  patientId: number,
  payload: AllergyCreatePayload,
  email?: string | null,
): Promise<AllergyRecord> {
  return apiFetch(`/patients/${patientId}/medication-allergies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    email,
  });
}
