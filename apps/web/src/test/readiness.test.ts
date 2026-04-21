// ROI wave 1 — readiness + queue preset unit tests.
//
// Keeps the deterministic classifier honest so UI behavior stays
// predictable as we fold in more state over time.

import { describe, it, expect } from "vitest";
import { Encounter } from "../api";
import { QUEUE_PRESETS, deriveReadiness } from "../readiness";

const NOW = new Date("2026-04-20T15:00:00Z").getTime();

function mk(partial: Partial<Encounter>): Encounter {
  return {
    id: 1,
    organization_id: 1,
    location_id: 1,
    patient_identifier: "PT-1",
    patient_name: "Test",
    provider_name: "Dr Carter",
    status: "scheduled",
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    created_at: null,
    ...partial,
  };
}

describe("deriveReadiness", () => {
  it("classifies completed", () => {
    expect(deriveReadiness(mk({ status: "completed" }), NOW).kind).toBe(
      "completed"
    );
  });

  it("classifies review_needed as warn", () => {
    const r = deriveReadiness(mk({ status: "review_needed" }), NOW);
    expect(r.kind).toBe("review_needed");
    expect(r.severity).toBe("warn");
  });

  it("escalates review_needed > 48h as blocked", () => {
    const old = new Date(NOW - 72 * 60 * 60 * 1000).toISOString();
    const r = deriveReadiness(
      mk({ status: "review_needed", created_at: old }),
      NOW
    );
    expect(r.kind).toBe("blocked");
    expect(r.severity).toBe("error");
  });

  it("flags arriving_soon within 30min window", () => {
    const in20min = new Date(NOW + 20 * 60 * 1000).toISOString();
    const r = deriveReadiness(
      mk({ status: "scheduled", scheduled_at: in20min }),
      NOW
    );
    expect(r.kind).toBe("arriving_soon");
  });

  it("flags past-scheduled non-checked-in as late/ready_for_tech", () => {
    const pastSchedule = new Date(NOW - 90 * 60 * 1000).toISOString();
    const r = deriveReadiness(
      mk({ status: "scheduled", scheduled_at: pastSchedule }),
      NOW
    );
    expect(r.kind).toBe("ready_for_tech");
    expect(r.severity).toBe("warn");
  });
});

describe("QUEUE_PRESETS", () => {
  it("all matches every encounter", () => {
    const all = QUEUE_PRESETS.find((p) => p.key === "all")!;
    expect(all.match(mk({ status: "scheduled" }), NOW)).toBe(true);
    expect(all.match(mk({ status: "completed" }), NOW)).toBe(true);
  });

  it("draft_ready only matches draft_ready status", () => {
    const p = QUEUE_PRESETS.find((q) => q.key === "draft_ready")!;
    expect(p.match(mk({ status: "draft_ready" }), NOW)).toBe(true);
    expect(p.match(mk({ status: "in_progress" }), NOW)).toBe(false);
  });

  it("blocked escalates stale review_needed", () => {
    const old = new Date(NOW - 72 * 60 * 60 * 1000).toISOString();
    const p = QUEUE_PRESETS.find((q) => q.key === "blocked")!;
    expect(
      p.match(mk({ status: "review_needed", created_at: old }), NOW)
    ).toBe(true);
    expect(p.match(mk({ status: "review_needed" }), NOW)).toBe(false);
  });
});
