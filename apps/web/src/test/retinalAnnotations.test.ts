import { describe, expect, it } from "vitest";

import {
  AUTO_SUMMARY_END,
  AUTO_SUMMARY_HEADING,
  AUTO_SUMMARY_START,
  type Annotation,
  type DrawingDocument,
  EMPTY_DRAWING,
  UNDO_STACK_CAP,
  applyAutoSummary,
  historyReducer,
  initHistory,
  isDrawingDocument,
  migrateUnknownDrawing,
  newAnnotationId,
  summarizeAnnotations,
} from "../retinalAnnotations";

function symbol(id: string, eye: "OD" | "OS", x = 0.5, y = 0.5): Annotation {
  return {
    id,
    kind: "symbol",
    symbol_type: "drusen",
    eye,
    x,
    y,
    color: "#000",
    source: "manual",
    created_at: "2026-05-04T12:00:00+00:00",
  };
}

describe("retinalAnnotations / schema validation", () => {
  it("isDrawingDocument accepts current schema", () => {
    expect(isDrawingDocument(EMPTY_DRAWING)).toBe(true);
  });

  it("isDrawingDocument rejects legacy shapes", () => {
    expect(isDrawingDocument(null)).toBe(false);
    expect(isDrawingDocument({})).toBe(false);
    expect(isDrawingDocument({ strokes: [] })).toBe(false);
    expect(isDrawingDocument({ schema_version: 99, canvas_type: "retinal_diagram", annotations: [] })).toBe(false);
  });

  it("migrateUnknownDrawing returns recognized=true for current schema", () => {
    const doc: DrawingDocument = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [symbol("a1", "OD")],
    };
    const r = migrateUnknownDrawing(doc);
    expect(r.recognized).toBe(true);
    expect(r.doc.annotations).toHaveLength(1);
  });

  it("migrateUnknownDrawing returns empty doc for unknown shapes", () => {
    const r1 = migrateUnknownDrawing({});
    expect(r1.recognized).toBe(false);
    expect(r1.doc).toEqual(EMPTY_DRAWING);

    const r2 = migrateUnknownDrawing({ strokes: [{ path: "M0 0" }] });
    expect(r2.recognized).toBe(false);
    expect(r2.doc.annotations).toEqual([]);
  });

  it("migrateUnknownDrawing strips invalid annotations from a recognized doc", () => {
    const dirty = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [
        symbol("ok", "OD"),
        { foo: "bar" }, // invalid
        { id: "x", kind: "symbol", eye: "XX", x: 0.5, y: 0.5 }, // invalid eye
      ],
    } as unknown as DrawingDocument;
    const r = migrateUnknownDrawing(dirty);
    expect(r.recognized).toBe(true);
    expect(r.doc.annotations.map((a) => a.id)).toEqual(["ok"]);
  });

  it("newAnnotationId returns a unique string each call", () => {
    const a = newAnnotationId();
    const b = newAnnotationId();
    expect(typeof a).toBe("string");
    expect(a).not.toBe(b);
  });
});

describe("retinalAnnotations / history reducer", () => {
  it("commit pushes present onto past and clears future", () => {
    const start: DrawingDocument = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [],
    };
    const next: DrawingDocument = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [symbol("a1", "OD")],
    };
    const after = historyReducer(initHistory(start), { type: "commit", next });
    expect(after.past).toEqual([start]);
    expect(after.present).toEqual(next);
    expect(after.future).toEqual([]);
  });

  it("undo moves present back to the previous past entry", () => {
    const v0 = EMPTY_DRAWING;
    const v1: DrawingDocument = { ...v0, annotations: [symbol("a1", "OD")] };
    let h = historyReducer(initHistory(v0), { type: "commit", next: v1 });
    h = historyReducer(h, { type: "undo" });
    expect(h.present).toEqual(v0);
    expect(h.future).toEqual([v1]);
  });

  it("redo replays after an undo", () => {
    const v0 = EMPTY_DRAWING;
    const v1: DrawingDocument = { ...v0, annotations: [symbol("a1", "OD")] };
    let h = historyReducer(initHistory(v0), { type: "commit", next: v1 });
    h = historyReducer(h, { type: "undo" });
    h = historyReducer(h, { type: "redo" });
    expect(h.present).toEqual(v1);
    expect(h.future).toEqual([]);
  });

  it("undo on empty past is a no-op", () => {
    const h = initHistory(EMPTY_DRAWING);
    expect(historyReducer(h, { type: "undo" })).toBe(h);
  });

  it("history caps past entries at UNDO_STACK_CAP", () => {
    let h = initHistory(EMPTY_DRAWING);
    for (let i = 0; i < UNDO_STACK_CAP + 5; i++) {
      const next: DrawingDocument = {
        ...EMPTY_DRAWING,
        annotations: [symbol(`a${i}`, "OD")],
      };
      h = historyReducer(h, { type: "commit", next });
    }
    expect(h.past.length).toBe(UNDO_STACK_CAP);
  });
});

describe("retinalAnnotations / summarize + auto-summary fence", () => {
  it("summarizeAnnotations renders heading + (none) when empty", () => {
    const out = summarizeAnnotations(EMPTY_DRAWING);
    expect(out).toContain(AUTO_SUMMARY_HEADING);
    expect(out).toContain("(none)");
  });

  it("summarizeAnnotations groups by eye and uses display labels", () => {
    const flame: Annotation = {
      id: "a2",
      kind: "symbol",
      symbol_type: "flame_hemorrhage",
      eye: "OS",
      x: 0.2,
      y: 0.1,
      color: "#000",
      source: "manual",
      created_at: "2026-05-04T12:00:00+00:00",
    };
    const doc: DrawingDocument = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [symbol("a1", "OD", 0.5, 0.5), flame],
    };
    const out = summarizeAnnotations(doc);
    expect(out).toMatch(/OD: drusen/);
    expect(out).toMatch(/OS: flame hemorrhage/);
  });

  it("applyAutoSummary appends a fenced block when no fence exists", () => {
    const out = applyAutoSummary("Provider note one.", EMPTY_DRAWING);
    expect(out).toContain("Provider note one.");
    expect(out).toContain(AUTO_SUMMARY_START);
    expect(out).toContain(AUTO_SUMMARY_END);
  });

  it("applyAutoSummary replaces only the fenced block, leaving outside text intact", () => {
    const initialFindings =
      "Top provider line.\n" +
      `${AUTO_SUMMARY_START}\nold summary content\n${AUTO_SUMMARY_END}\n` +
      "Bottom provider line.";
    const next: DrawingDocument = {
      ...EMPTY_DRAWING,
      annotations: [symbol("a1", "OD")],
    };
    const out = applyAutoSummary(initialFindings, next);

    expect(out).toContain("Top provider line.");
    expect(out).toContain("Bottom provider line.");
    expect(out).not.toContain("old summary content");
    expect(out).toMatch(/OD: drusen/);
  });

  it("applyAutoSummary produces an idempotent block on repeated calls", () => {
    const docA: DrawingDocument = {
      ...EMPTY_DRAWING,
      annotations: [symbol("a1", "OD")],
    };
    const once = applyAutoSummary("Outer text.", docA);
    const twice = applyAutoSummary(once, docA);
    expect(twice).toBe(once);
  });
});
