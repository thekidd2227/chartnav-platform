// Ambient documentation / VisitDraft Assist feature client.
//
// Phase 63C — routes through the configured API_URL and sends
// `X-User-Email` for header-mode demo auth. Previously this module
// used the empty BASE and relative "/patients/..." paths, which
// resolved against the Vite origin (127.0.0.1:5173) and returned
// 404. The narration label is "Provider-Reviewed VisitDraft Assist";
// the on-screen card title is still "Provider-Reviewed Ambient
// Documentation Assist" — Phase 62A pinned that.
//
// Demo identity discovery order:
//   1. explicit `email` arg passed by the panel
//   2. `localStorage.chartnav.devIdentity`
//   3. omitted — backend returns 401 with a clear error
//
// No vendor API key is read. No real PHI processed.

import { API_URL } from "../../api";
import type {
  CreateScribeSessionRequest,
  DraftAmbientRequest,
  ReviewScribeSessionRequest,
  ScribeSessionResponse,
  ScribeSessionWithAmbientDraft,
} from "./ambientTypes";

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
  const res = await fetch(`${API_URL}${path}`, { ...fetchInit, headers });
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

export function listScribeSessions(
  patientId: number,
  email?: string | null,
): Promise<ScribeSessionResponse[]> {
  return apiFetch(`/patients/${patientId}/scribe-sessions`, { email });
}

export function createScribeSession(
  patientId: number,
  body: CreateScribeSessionRequest,
  email?: string | null,
): Promise<ScribeSessionResponse> {
  return apiFetch(`/patients/${patientId}/scribe-sessions`, {
    method: "POST",
    body: JSON.stringify(body),
    email,
  });
}

export function getScribeSession(
  patientId: number,
  sessionId: number,
  email?: string | null,
): Promise<ScribeSessionResponse> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}`,
    { email },
  );
}

export function draftAmbientSession(
  patientId: number,
  sessionId: number,
  body: DraftAmbientRequest = { fake_data_context: true },
  email?: string | null,
): Promise<ScribeSessionWithAmbientDraft> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}/draft-ambient`,
    {
      method: "POST",
      body: JSON.stringify(body),
      email,
    },
  );
}

export function reviewScribeSession(
  patientId: number,
  sessionId: number,
  body: ReviewScribeSessionRequest = {},
  email?: string | null,
): Promise<ScribeSessionResponse> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}/review`,
    {
      method: "POST",
      body: JSON.stringify(body),
      email,
    },
  );
}

export function finalizeScribeSession(
  patientId: number,
  sessionId: number,
  email?: string | null,
): Promise<ScribeSessionResponse> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}/finalize`,
    { method: "POST", email },
  );
}
