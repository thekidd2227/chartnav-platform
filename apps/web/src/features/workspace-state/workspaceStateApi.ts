// Phase 91 — Unified Workspace State API client.

import { API_URL } from "../../api";
import type {
  ActiveLaterality,
  VisitMode,
  WorkspaceStateResponse,
} from "./workspaceStateTypes";

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

export function getWorkspaceState(
  encounterId: number,
  email?: string | null,
): Promise<WorkspaceStateResponse> {
  return apiFetch(`/encounters/${encounterId}/workspace-state`, { email });
}

export function patchVisitMode(
  encounterId: number,
  visitMode: VisitMode,
  email?: string | null,
): Promise<WorkspaceStateResponse> {
  return apiFetch(
    `/encounters/${encounterId}/workspace-state/visit-mode`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visit_mode: visitMode }),
      email,
    },
  );
}

export function patchActiveLaterality(
  encounterId: number,
  activeLaterality: ActiveLaterality,
  email?: string | null,
): Promise<WorkspaceStateResponse> {
  return apiFetch(
    `/encounters/${encounterId}/workspace-state/active-laterality`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_laterality: activeLaterality }),
      email,
    },
  );
}
