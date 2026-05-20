// Phase 63C — manual_note payload shaping.
//
// Backend rejects manual_note.event_data when it isn't a JSON
// object (apps/api/app/api/routes.py emits
// `invalid_event_data: manual_note event_data must be a JSON
// object`). The frontend must therefore wrap free-text as
// { note: "..." }, refuse empty input, and pass through valid
// JSON objects unchanged.

import { describe, expect, it } from "vitest";

import { shapeEventData } from "../utils/shapeEventData";

describe("Phase 63C shapeEventData policy", () => {
  describe("manual_note", () => {
    it("refuses empty input with an error", () => {
      expect(shapeEventData("manual_note", "")).toEqual({ error: "empty" });
      expect(shapeEventData("manual_note", "   ")).toEqual({ error: "empty" });
    });

    it("wraps free-text as { note: trimmed }", () => {
      expect(shapeEventData("manual_note", "blurry vision OD")).toEqual({
        ok: { note: "blurry vision OD" },
      });
      expect(shapeEventData("manual_note", "  hello  ")).toEqual({
        ok: { note: "hello" },
      });
    });

    it("wraps a JSON string literal as a note object", () => {
      // The raw input parses as a valid JSON string. Backend would
      // reject it as a non-object — the helper wraps it.
      expect(shapeEventData("manual_note", '"already json string"')).toEqual({
        ok: { note: '"already json string"' },
      });
    });

    it("wraps a JSON array as a note object", () => {
      expect(shapeEventData("manual_note", "[1, 2, 3]")).toEqual({
        ok: { note: "[1, 2, 3]" },
      });
    });

    it("wraps JSON null as a note object", () => {
      expect(shapeEventData("manual_note", "null")).toEqual({
        ok: { note: "null" },
      });
    });

    it("passes through a JSON object unchanged", () => {
      expect(shapeEventData("manual_note", '{"note":"already shaped"}')).toEqual({
        ok: { note: "already shaped" },
      });
    });

    it("passes through a JSON object with extra fields", () => {
      expect(
        shapeEventData(
          "manual_note",
          '{"note":"detail","priority":"low"}',
        ),
      ).toEqual({ ok: { note: "detail", priority: "low" } });
    });
  });

  describe("other event types", () => {
    it("preserves legacy behaviour: parse JSON when possible", () => {
      expect(shapeEventData("status_changed", '{"new_status":"draft_ready"}')).toEqual({
        ok: { new_status: "draft_ready" },
      });
    });

    it("preserves legacy behaviour: raw string fallback for non-JSON", () => {
      expect(shapeEventData("status_changed", "draft_ready")).toEqual({
        ok: "draft_ready",
      });
    });

    it("returns undefined for empty non-manual_note input", () => {
      expect(shapeEventData("status_changed", "")).toEqual({ ok: undefined });
      expect(shapeEventData("status_changed", "  ")).toEqual({ ok: undefined });
    });
  });
});
