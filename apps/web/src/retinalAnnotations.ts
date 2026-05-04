// retinalAnnotations.ts
//
// Schema, helpers, and reducer for retinal-diagram drawing annotations.
//
// The on-disk shape lives in `chart_artifacts.drawing_json` as a JSON
// object. We version it explicitly so older payloads round-trip cleanly
// when we add fields later. Coordinates are normalized 0..1 against the
// per-eye canvas viewBox so resizing the SVG never breaks positions.
//
// Provenance: every annotation carries `source: "manual"` in this PR.
// The field is reserved so AI-proposed annotations land naturally in a
// later phase without a schema bump.

export type Eye = "OD" | "OS";

export const SYMBOL_TYPES = [
  "drusen",
  "dot_blot_hemorrhage",
  "flame_hemorrhage",
  "microaneurysm",
  "hard_exudates",
  "cotton_wool_spot",
  "neovascularization",
  "retinal_tear",
  "retinal_detachment",
  "laser_scar",
  "disc_pallor",
  "rpe_change",
  "lattice_degeneration",
] as const;

export type SymbolType = (typeof SYMBOL_TYPES)[number];

export interface SymbolLabel {
  key: SymbolType;
  short: string;       // 3-4 char glyph rendered on the canvas
  display: string;     // human-readable label for tooltips/findings
}

export const SYMBOL_LIBRARY: SymbolLabel[] = [
  { key: "drusen",                short: "DRU", display: "drusen" },
  { key: "dot_blot_hemorrhage",   short: "DOT", display: "dot/blot hemorrhage" },
  { key: "flame_hemorrhage",      short: "FLM", display: "flame hemorrhage" },
  { key: "microaneurysm",         short: "MA",  display: "microaneurysm" },
  { key: "hard_exudates",         short: "HE",  display: "hard exudates" },
  { key: "cotton_wool_spot",      short: "CWS", display: "cotton-wool spot" },
  { key: "neovascularization",    short: "NV",  display: "neovascularization" },
  { key: "retinal_tear",          short: "TR",  display: "retinal tear/hole" },
  { key: "retinal_detachment",    short: "RD",  display: "retinal detachment" },
  { key: "laser_scar",            short: "LSR", display: "laser/scar" },
  { key: "disc_pallor",           short: "PAL", display: "disc pallor" },
  { key: "rpe_change",            short: "RPE", display: "RPE change" },
  { key: "lattice_degeneration",  short: "LAT", display: "lattice degeneration" },
];

export const SYMBOL_DISPLAY_BY_KEY: Record<SymbolType, string> =
  Object.fromEntries(SYMBOL_LIBRARY.map((s) => [s.key, s.display])) as Record<
    SymbolType,
    string
  >;

export type AnnotationKind = "symbol" | "freehand" | "text";

export interface Point {
  x: number; // 0..1 normalized within the eye pane
  y: number; // 0..1 normalized within the eye pane
}

export interface BaseAnnotation {
  id: string;
  kind: AnnotationKind;
  eye: Eye;
  x: number;
  y: number;
  color: string;
  source: "manual";
  created_at: string;
}

export interface SymbolAnnotation extends BaseAnnotation {
  kind: "symbol";
  symbol_type: SymbolType;
  label?: string;
}

export interface FreehandAnnotation extends BaseAnnotation {
  kind: "freehand";
  points: Point[];
}

export interface TextAnnotation extends BaseAnnotation {
  kind: "text";
  text: string;
}

export type Annotation = SymbolAnnotation | FreehandAnnotation | TextAnnotation;

export interface DrawingDocument {
  schema_version: 1;
  canvas_type: "retinal_diagram";
  annotations: Annotation[];
}

export const EMPTY_DRAWING: DrawingDocument = {
  schema_version: 1,
  canvas_type: "retinal_diagram",
  annotations: [],
};

/**
 * Returns true if `value` looks like a current-schema retinal drawing.
 * Anything else is treated as legacy/unknown and migrated to an empty
 * document while preserving the original payload separately.
 */
export function isDrawingDocument(value: unknown): value is DrawingDocument {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    v.schema_version === 1 &&
    v.canvas_type === "retinal_diagram" &&
    Array.isArray(v.annotations)
  );
}

/**
 * Pull a normalized DrawingDocument out of whatever was stored. Safe to
 * call on legacy persistence-shell payloads (which were `{}` or
 * arbitrary JSON). Returns the empty doc + a flag indicating whether
 * the input was already a known shape.
 */
export function migrateUnknownDrawing(
  value: unknown
): { doc: DrawingDocument; recognized: boolean } {
  if (isDrawingDocument(value)) {
    // Defensive copy of annotations to detach from store state.
    return {
      doc: {
        schema_version: 1,
        canvas_type: "retinal_diagram",
        annotations: value.annotations.filter(isAnnotation),
      },
      recognized: true,
    };
  }
  return { doc: { ...EMPTY_DRAWING, annotations: [] }, recognized: false };
}

function isAnnotation(value: unknown): value is Annotation {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "string" &&
    (v.kind === "symbol" || v.kind === "freehand" || v.kind === "text") &&
    (v.eye === "OD" || v.eye === "OS") &&
    typeof v.x === "number" &&
    typeof v.y === "number"
  );
}

// --- Findings auto-summary ----------------------------------------------
//
// Provider text outside our fenced block is NEVER touched. The block is
// fenced with explicit start/end markers; if the markers are missing
// from `findings_text`, we append a fresh block. If they are present,
// only the content between them is replaced.

export const AUTO_SUMMARY_START = "<!-- retinal-auto-summary:start -->";
export const AUTO_SUMMARY_END = "<!-- retinal-auto-summary:end -->";
export const AUTO_SUMMARY_HEADING = "Retinal diagram auto-summary:";

const FENCE_RE = new RegExp(
  `${escapeRe(AUTO_SUMMARY_START)}[\\s\\S]*?${escapeRe(AUTO_SUMMARY_END)}`,
  "m"
);

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Build the human-readable summary of all annotations in `doc`.
 * Always renders at least the heading so the block has visible content.
 */
export function summarizeAnnotations(doc: DrawingDocument): string {
  const lines: string[] = [AUTO_SUMMARY_HEADING];
  if (doc.annotations.length === 0) {
    lines.push("(none)");
  } else {
    for (const eye of ["OD", "OS"] as const) {
      const items = doc.annotations.filter((a) => a.eye === eye);
      if (items.length === 0) continue;
      const phrases = items.map((a) => describeAnnotation(a));
      const merged = mergeDuplicatePhrases(phrases);
      lines.push(`${eye}: ${merged.join("; ")}.`);
    }
  }
  return lines.join("\n");
}

function describeAnnotation(a: Annotation): string {
  const zone = describeZone(a);
  if (a.kind === "symbol") {
    const base = SYMBOL_DISPLAY_BY_KEY[a.symbol_type] ?? a.symbol_type;
    return zone ? `${base} ${zone}` : base;
  }
  if (a.kind === "text") {
    return a.text.trim() || "(empty label)";
  }
  return zone ? `freehand mark ${zone}` : "freehand mark";
}

function describeZone(a: Annotation): string {
  // Eight-way rough zone label based on normalized coords. Center is
  // anything within 0.18 of (0.5, 0.5).
  const dx = a.x - 0.5;
  const dy = a.y - 0.5;
  if (Math.abs(dx) < 0.18 && Math.abs(dy) < 0.18) return "near macula";
  const v = dy < -0.18 ? "superior" : dy > 0.18 ? "inferior" : "";
  const h = dx < -0.18 ? "nasal" : dx > 0.18 ? "temporal" : "";
  const parts = [v, h].filter(Boolean);
  return parts.length ? parts.join(" ") : "";
}

function mergeDuplicatePhrases(phrases: string[]): string[] {
  const counts = new Map<string, number>();
  for (const p of phrases) counts.set(p, (counts.get(p) ?? 0) + 1);
  return Array.from(counts.entries()).map(([phrase, n]) =>
    n > 1 ? `${phrase} ×${n}` : phrase
  );
}

/**
 * Replace (or append) the auto-summary block inside `findingsText`.
 * Any text outside the fenced block is preserved exactly.
 */
export function applyAutoSummary(
  findingsText: string,
  doc: DrawingDocument
): string {
  const summary = summarizeAnnotations(doc);
  const block = `${AUTO_SUMMARY_START}\n${summary}\n${AUTO_SUMMARY_END}`;
  if (FENCE_RE.test(findingsText)) {
    return findingsText.replace(FENCE_RE, block);
  }
  if (!findingsText.trim()) return block;
  return `${findingsText.replace(/\s+$/, "")}\n\n${block}`;
}

// --- Undo / redo reducer ------------------------------------------------
//
// Whole-state snapshot stack. Capped at 50 to bound memory.

export const UNDO_STACK_CAP = 50;

export interface HistoryState {
  past: DrawingDocument[];
  present: DrawingDocument;
  future: DrawingDocument[];
}

export type HistoryAction =
  | { type: "commit"; next: DrawingDocument }
  | { type: "undo" }
  | { type: "redo" }
  | { type: "reset"; doc: DrawingDocument };

export function initHistory(doc: DrawingDocument): HistoryState {
  return { past: [], present: doc, future: [] };
}

export function historyReducer(
  state: HistoryState,
  action: HistoryAction
): HistoryState {
  switch (action.type) {
    case "commit": {
      const past = [...state.past, state.present];
      // Cap from the FRONT so the most recent UNDO_STACK_CAP entries win.
      const capped = past.length > UNDO_STACK_CAP ? past.slice(-UNDO_STACK_CAP) : past;
      return { past: capped, present: action.next, future: [] };
    }
    case "undo": {
      if (state.past.length === 0) return state;
      const previous = state.past[state.past.length - 1];
      const past = state.past.slice(0, -1);
      return { past, present: previous, future: [state.present, ...state.future] };
    }
    case "redo": {
      if (state.future.length === 0) return state;
      const [next, ...rest] = state.future;
      return { past: [...state.past, state.present], present: next, future: rest };
    }
    case "reset":
      return initHistory(action.doc);
  }
}

// --- ID + helpers -------------------------------------------------------

let _counter = 0;
export function newAnnotationId(): string {
  // Deterministic, monotonic, jsdom-safe — no crypto dependency.
  _counter += 1;
  return `a_${Date.now().toString(36)}_${_counter.toString(36)}`;
}

export function clamp01(n: number): number {
  if (Number.isNaN(n)) return 0;
  return n < 0 ? 0 : n > 1 ? 1 : n;
}

export function withoutAnnotation(
  doc: DrawingDocument,
  id: string
): DrawingDocument {
  return {
    ...doc,
    annotations: doc.annotations.filter((a) => a.id !== id),
  };
}

export function addAnnotation(
  doc: DrawingDocument,
  annotation: Annotation
): DrawingDocument {
  return { ...doc, annotations: [...doc.annotations, annotation] };
}

export function moveAnnotation(
  doc: DrawingDocument,
  id: string,
  x: number,
  y: number
): DrawingDocument {
  return {
    ...doc,
    annotations: doc.annotations.map((a) =>
      a.id === id ? { ...a, x: clamp01(x), y: clamp01(y) } : a
    ),
  };
}

export function clearEye(doc: DrawingDocument, eye: Eye): DrawingDocument {
  return { ...doc, annotations: doc.annotations.filter((a) => a.eye !== eye) };
}

export function clearAll(doc: DrawingDocument): DrawingDocument {
  return { ...doc, annotations: [] };
}
