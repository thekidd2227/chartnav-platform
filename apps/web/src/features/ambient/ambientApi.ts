import type {
  CreateScribeSessionRequest,
  DraftAmbientRequest,
  ReviewScribeSessionRequest,
  ScribeSessionResponse,
  ScribeSessionWithAmbientDraft,
} from "./ambientTypes";

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

export function listScribeSessions(
  patientId: number,
): Promise<ScribeSessionResponse[]> {
  return apiFetch(`/patients/${patientId}/scribe-sessions`);
}

export function createScribeSession(
  patientId: number,
  body: CreateScribeSessionRequest,
): Promise<ScribeSessionResponse> {
  return apiFetch(`/patients/${patientId}/scribe-sessions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getScribeSession(
  patientId: number,
  sessionId: number,
): Promise<ScribeSessionResponse> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}`,
  );
}

export function draftAmbientSession(
  patientId: number,
  sessionId: number,
  body: DraftAmbientRequest = { fake_data_context: true },
): Promise<ScribeSessionWithAmbientDraft> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}/draft-ambient`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function reviewScribeSession(
  patientId: number,
  sessionId: number,
  body: ReviewScribeSessionRequest = {},
): Promise<ScribeSessionResponse> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}/review`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function finalizeScribeSession(
  patientId: number,
  sessionId: number,
): Promise<ScribeSessionResponse> {
  return apiFetch(
    `/patients/${patientId}/scribe-sessions/${sessionId}/finalize`,
    { method: "POST" },
  );
}
