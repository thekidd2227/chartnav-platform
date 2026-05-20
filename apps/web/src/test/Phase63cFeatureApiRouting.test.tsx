// Phase 63C — feature API clients route through the configured
// API_URL and send X-User-Email for header-mode demo auth.
//
// Pre-Phase-63C, vitalsApi/fundusApi/ambientApi called relative
// paths against the Vite origin (127.0.0.1:5173), which 404'd
// because the dev server doesn't proxy /api/v1 to the backend.
// These tests pin the fix in place: the three feature clients
// must use API_URL + identity.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_URL } from "../api";
import { listVitalsWorkups, createVitalsWorkup } from "../features/vitals/vitalsApi";
import { listFundusCharts, generateFundusChart } from "../features/fundus/fundusApi";
import {
  listScribeSessions,
  draftAmbientSession,
} from "../features/ambient/ambientApi";

const okJson = (body: unknown): Response =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

function lastCall(spy: ReturnType<typeof vi.spyOn>): {
  url: string;
  init: RequestInit;
} {
  const [u, i] = spy.mock.calls[spy.mock.calls.length - 1] as [
    string | URL,
    RequestInit,
  ];
  return { url: String(u), init: i };
}

describe("Phase 63C feature API clients route through API_URL with X-User-Email", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(global, "fetch" as never).mockImplementation(
      ((..._args: unknown[]) => Promise.resolve(okJson({}))) as never,
    );
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("vitalsApi.listVitalsWorkups uses API_URL/api/v1/...", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "clin@chartnav.local");
    await listVitalsWorkups(1);
    const { url, init } = lastCall(fetchSpy);
    expect(url).toBe(`${API_URL}/api/v1/encounters/1/vitals-workups`);
    expect(url).not.toContain("5173");
    const headers = new Headers(init.headers);
    expect(headers.get("X-User-Email")).toBe("clin@chartnav.local");
  });

  it("vitalsApi.createVitalsWorkup sends JSON body + identity", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "tech@chartnav.local");
    await createVitalsWorkup(1, {
      source_type: "technician_entry",
    } as never);
    const { url, init } = lastCall(fetchSpy);
    expect(url).toBe(`${API_URL}/api/v1/encounters/1/vitals-workups`);
    expect(init.method).toBe("POST");
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-User-Email")).toBe("tech@chartnav.local");
  });

  it("vitalsApi accepts an explicit identity arg overriding localStorage", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "clin@chartnav.local");
    await listVitalsWorkups(1, "admin@chartnav.local");
    const { init } = lastCall(fetchSpy);
    expect(new Headers(init.headers).get("X-User-Email")).toBe(
      "admin@chartnav.local",
    );
  });

  it("fundusApi.listFundusCharts uses API_URL/api/v1/...", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "clin@chartnav.local");
    await listFundusCharts(1);
    const { url, init } = lastCall(fetchSpy);
    expect(url).toBe(`${API_URL}/api/v1/encounters/1/fundus-charts`);
    expect(url).not.toContain("5173");
    expect(new Headers(init.headers).get("X-User-Email")).toBe(
      "clin@chartnav.local",
    );
  });

  it("fundusApi.generateFundusChart posts JSON to API_URL", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "clin@chartnav.local");
    await generateFundusChart(1, {
      findings_text: "horseshoe tear at 10:30 OD",
      laterality: "OD",
    } as never);
    const { url, init } = lastCall(fetchSpy);
    expect(url).toBe(
      `${API_URL}/api/v1/encounters/1/fundus-charts/generate`,
    );
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("X-User-Email")).toBe(
      "clin@chartnav.local",
    );
  });

  it("ambientApi.listScribeSessions uses API_URL/patients/...", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "clin@chartnav.local");
    await listScribeSessions(1);
    const { url } = lastCall(fetchSpy);
    expect(url).toBe(`${API_URL}/patients/1/scribe-sessions`);
    expect(url).not.toContain("5173");
  });

  it("ambientApi.draftAmbientSession posts to draft-ambient on API_URL", async () => {
    window.localStorage.setItem("chartnav.devIdentity", "clin@chartnav.local");
    await draftAmbientSession(1, 7);
    const { url, init } = lastCall(fetchSpy);
    expect(url).toBe(
      `${API_URL}/patients/1/scribe-sessions/7/draft-ambient`,
    );
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("X-User-Email")).toBe(
      "clin@chartnav.local",
    );
  });

  it("omits X-User-Email when no explicit arg and no localStorage", async () => {
    window.localStorage.removeItem("chartnav.devIdentity");
    await listVitalsWorkups(1);
    const { init } = lastCall(fetchSpy);
    expect(new Headers(init.headers).has("X-User-Email")).toBe(false);
  });
});
