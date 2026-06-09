// Phase 76 — Retina Visit Summary API client.
//
// Follows the same identity-resolution pattern as the other feature
// clients in this monorepo (header-mode X-User-Email, explicit
// localStorage fallback, no relative URLs against the Vite origin).

import { API_URL } from "../../api";
import type { RetinaVisitPacket } from "./retinaPacketTypes";
import type { RetinaVisitSummary } from "./retinaSummaryTypes";

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

export function getRetinaVisitSummary(
  encounterId: number,
  email?: string | null,
): Promise<RetinaVisitSummary> {
  return apiFetch(`/encounters/${encounterId}/retina-visit-summary`, { email });
}

export function getRetinaVisitPacket(
  encounterId: number,
  email?: string | null,
): Promise<RetinaVisitPacket> {
  return apiFetch(`/encounters/${encounterId}/retina-visit-packet`, { email });
}
