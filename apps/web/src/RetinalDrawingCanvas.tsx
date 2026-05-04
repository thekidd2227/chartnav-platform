// RetinalDrawingCanvas.tsx
//
// SVG-based OD/OS retinal drawing surface. Side-by-side panes for the
// right (OD) and left (OS) eye, each rendered with optic-disc and
// macula reference markers. Provider can place ophthalmology symbols
// from the palette, drop text labels, sketch freehand polylines, and
// select/move/delete annotations. Undo/redo goes through the
// whole-state reducer in retinalAnnotations.ts.
//
// Coordinates are stored normalized (0..1) per eye pane so resizing
// the SVG never breaks position. The component is read-only when
// `readOnly` is true (signed artifact viewing path).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  Annotation,
  AnnotationKind,
  DrawingDocument,
  Eye,
  EMPTY_DRAWING,
  HistoryAction,
  HistoryState,
  Point,
  SYMBOL_DISPLAY_BY_KEY,
  SYMBOL_LIBRARY,
  SymbolType,
  addAnnotation,
  clamp01,
  clearAll,
  clearEye,
  historyReducer,
  initHistory,
  moveAnnotation,
  newAnnotationId,
  withoutAnnotation,
} from "./retinalAnnotations";

// --- public surface ----------------------------------------------------

interface Props {
  value: DrawingDocument;
  onChange: (doc: DrawingDocument) => void;
  readOnly?: boolean;
}

type Tool =
  | { kind: "select" }
  | { kind: "freehand" }
  | { kind: "text" }
  | { kind: "symbol"; symbol_type: SymbolType };

// --- coordinate helpers ------------------------------------------------

const VIEW_W = 200;
const VIEW_H = 200;

function svgPointFor(
  evt: React.PointerEvent<SVGSVGElement>,
  svg: SVGSVGElement
): { x: number; y: number } {
  const rect = svg.getBoundingClientRect();
  // jsdom returns 0/0 sized rects; treat that as already-normalized.
  if (rect.width === 0 || rect.height === 0) {
    return { x: clamp01(0.5), y: clamp01(0.5) };
  }
  const x = (evt.clientX - rect.left) / rect.width;
  const y = (evt.clientY - rect.top) / rect.height;
  return { x: clamp01(x), y: clamp01(y) };
}

// --- presentational helpers --------------------------------------------

function symbolGlyph(t: SymbolType): string {
  const found = SYMBOL_LIBRARY.find((s) => s.key === t);
  return found ? found.short : "?";
}

function pointsToPathD(points: Point[]): string {
  if (points.length === 0) return "";
  const head = points[0];
  let d = `M ${head.x * VIEW_W} ${head.y * VIEW_H}`;
  for (let i = 1; i < points.length; i++) {
    d += ` L ${points[i].x * VIEW_W} ${points[i].y * VIEW_H}`;
  }
  return d;
}

// --- component ---------------------------------------------------------

export function RetinalDrawingCanvas({ value, onChange, readOnly = false }: Props) {
  // History wraps `value` so undo/redo work without a parent commit per
  // keystroke. The component is "loosely controlled": parent owns the
  // canonical doc, but undo stack is internal. To avoid resetting the
  // stack when the parent's value-prop echoes our own onChange, we
  // tag locally-originated values via a ref and skip the reset for them.
  const [history, dispatch] = useReducerWithSync(value);
  const localEchoRef = useRef<DrawingDocument | null>(null);
  useEffect(() => {
    if (localEchoRef.current === value) {
      // Caller is mirroring our own commit; no external reset needed.
      localEchoRef.current = null;
      return;
    }
    dispatch({ type: "reset", doc: value });
    // We deliberately depend on `value` only — `dispatch` is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const doc = history.present;

  const commit = useCallback(
    (next: DrawingDocument) => {
      dispatch({ type: "commit", next });
      localEchoRef.current = next;
      onChange(next);
    },
    [dispatch, onChange]
  );

  const undo = useCallback(() => {
    dispatch({ type: "undo" });
  }, [dispatch]);

  const redo = useCallback(() => {
    dispatch({ type: "redo" });
  }, [dispatch]);

  // Whenever undo/redo changes `doc`, push the new doc upstream.
  useEffect(() => {
    if (history.past.length === 0 && history.future.length === 0) return;
    localEchoRef.current = history.present;
    onChange(history.present);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history.present]);

  const [tool, setTool] = useState<Tool>({ kind: "select" });
  const [color, setColor] = useState<string>("#c1121f");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Active freehand drag state, per-eye.
  const draftRef = useRef<{ id: string; points: Point[]; eye: Eye } | null>(null);
  const [draftPoints, setDraftPoints] = useState<Point[]>([]);
  const [draftEye, setDraftEye] = useState<Eye | null>(null);

  // --- annotation actions ---------------------------------------------

  const placeSymbol = useCallback(
    (eye: Eye, symbol_type: SymbolType, x: number, y: number) => {
      if (readOnly) return;
      const annotation: Annotation = {
        id: newAnnotationId(),
        kind: "symbol",
        symbol_type,
        eye,
        x,
        y,
        color,
        source: "manual",
        created_at: new Date().toISOString(),
      };
      const next = addAnnotation(doc, annotation);
      commit(next);
      setSelectedId(annotation.id);
    },
    [color, commit, doc, readOnly]
  );

  const placeText = useCallback(
    (eye: Eye, x: number, y: number) => {
      if (readOnly) return;
      const text = (window.prompt("Label text:") ?? "").trim();
      if (!text) return;
      const annotation: Annotation = {
        id: newAnnotationId(),
        kind: "text",
        text,
        eye,
        x,
        y,
        color,
        source: "manual",
        created_at: new Date().toISOString(),
      };
      commit(addAnnotation(doc, annotation));
      setSelectedId(annotation.id);
    },
    [color, commit, doc, readOnly]
  );

  const finishFreehand = useCallback(() => {
    const draft = draftRef.current;
    draftRef.current = null;
    setDraftPoints([]);
    setDraftEye(null);
    if (!draft || readOnly) return;
    if (draft.points.length < 2) return;
    const head = draft.points[0];
    const annotation: Annotation = {
      id: draft.id,
      kind: "freehand",
      eye: draft.eye,
      x: head.x,
      y: head.y,
      points: draft.points,
      color,
      source: "manual",
      created_at: new Date().toISOString(),
    };
    commit(addAnnotation(doc, annotation));
    setSelectedId(annotation.id);
  }, [color, commit, doc, readOnly]);

  const onDelete = useCallback(() => {
    if (readOnly || !selectedId) return;
    commit(withoutAnnotation(doc, selectedId));
    setSelectedId(null);
  }, [commit, doc, readOnly, selectedId]);

  const onClearEye = useCallback(
    (eye: Eye) => {
      if (readOnly) return;
      commit(clearEye(doc, eye));
      setSelectedId(null);
    },
    [commit, doc, readOnly]
  );

  const onClearAll = useCallback(() => {
    if (readOnly) return;
    commit(clearAll(doc));
    setSelectedId(null);
  }, [commit, doc, readOnly]);

  // --- pointer event handlers per eye pane ----------------------------

  function makePointerHandlers(eye: Eye) {
    return {
      onPointerDown: (evt: React.PointerEvent<SVGSVGElement>) => {
        if (readOnly) return;
        const pt = svgPointFor(evt, evt.currentTarget);
        if (tool.kind === "symbol") {
          placeSymbol(eye, tool.symbol_type, pt.x, pt.y);
        } else if (tool.kind === "text") {
          placeText(eye, pt.x, pt.y);
        } else if (tool.kind === "freehand") {
          draftRef.current = {
            id: newAnnotationId(),
            points: [pt],
            eye,
          };
          setDraftPoints([pt]);
          setDraftEye(eye);
          // jsdom does not implement setPointerCapture on SVG nodes;
          // the call is purely a UX nicety in real browsers.
          if (typeof evt.currentTarget.setPointerCapture === "function") {
            try {
              evt.currentTarget.setPointerCapture(evt.pointerId);
            } catch {
              /* ignore */
            }
          }
        }
      },
      onPointerMove: (evt: React.PointerEvent<SVGSVGElement>) => {
        if (readOnly) return;
        if (tool.kind !== "freehand" || !draftRef.current) return;
        if (draftRef.current.eye !== eye) return;
        const pt = svgPointFor(evt, evt.currentTarget);
        const last = draftRef.current.points[draftRef.current.points.length - 1];
        // Drop sub-pixel jitter to keep payload size sane.
        if (Math.hypot(pt.x - last.x, pt.y - last.y) < 0.005) return;
        draftRef.current.points.push(pt);
        setDraftPoints([...draftRef.current.points]);
      },
      onPointerUp: () => {
        if (tool.kind === "freehand") finishFreehand();
      },
      onPointerCancel: () => {
        if (tool.kind === "freehand") finishFreehand();
      },
    };
  }

  // --- annotation pickup for select/move ------------------------------

  const onAnnotationPointerDown = useCallback(
    (evt: React.PointerEvent<SVGElement>, ann: Annotation) => {
      if (tool.kind !== "select" || readOnly) return;
      evt.stopPropagation();
      setSelectedId(ann.id);
    },
    [readOnly, tool.kind]
  );

  // Move-by-drag for the selected annotation.
  const moveDragRef = useRef<{ id: string; eye: Eye } | null>(null);

  function makeMoveHandlers(eye: Eye) {
    return {
      onPointerDown: (evt: React.PointerEvent<SVGSVGElement>) => {
        if (tool.kind !== "select" || !selectedId || readOnly) return;
        const ann = doc.annotations.find((a) => a.id === selectedId);
        if (!ann || ann.eye !== eye || ann.kind === "freehand") return;
        moveDragRef.current = { id: selectedId, eye };
        if (typeof evt.currentTarget.setPointerCapture === "function") {
          try {
            evt.currentTarget.setPointerCapture(evt.pointerId);
          } catch {
            /* ignore */
          }
        }
      },
      onPointerMove: (evt: React.PointerEvent<SVGSVGElement>) => {
        if (!moveDragRef.current || moveDragRef.current.eye !== eye) return;
        const pt = svgPointFor(evt, evt.currentTarget);
        // Live position only — commit on pointer up.
        const next = moveAnnotation(doc, moveDragRef.current.id, pt.x, pt.y);
        dispatch({ type: "reset", doc: next });
        onChange(next);
      },
      onPointerUp: (evt: React.PointerEvent<SVGSVGElement>) => {
        if (!moveDragRef.current || moveDragRef.current.eye !== eye) return;
        const pt = svgPointFor(evt, evt.currentTarget);
        const next = moveAnnotation(doc, moveDragRef.current.id, pt.x, pt.y);
        moveDragRef.current = null;
        commit(next);
      },
    };
  }

  // --- render ---------------------------------------------------------

  const annotationsByEye = useMemo(() => {
    const od: Annotation[] = [];
    const os: Annotation[] = [];
    for (const a of doc.annotations) {
      (a.eye === "OD" ? od : os).push(a);
    }
    return { OD: od, OS: os };
  }, [doc]);

  const renderEye = (eye: Eye) => {
    const baseHandlers = makePointerHandlers(eye);
    const moveHandlers = makeMoveHandlers(eye);
    return (
      <div className="rdc__eye" data-testid={`rdc-eye-${eye}`}>
        <header>
          <strong>{eye}</strong>
          <span className="muted"> {eye === "OD" ? "right eye" : "left eye"}</span>
          {!readOnly && (
            <button
              type="button"
              data-testid={`rdc-clear-${eye}`}
              onClick={() => onClearEye(eye)}
              disabled={annotationsByEye[eye].length === 0}
            >
              Clear {eye}
            </button>
          )}
        </header>
        <svg
          data-testid={`rdc-svg-${eye}`}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          width="100%"
          height="100%"
          // Combined handlers: pane-scoped pointer events do double duty for
          // freehand drag AND select-then-move drag depending on the active tool.
          onPointerDown={(e) => {
            baseHandlers.onPointerDown(e);
            moveHandlers.onPointerDown(e);
          }}
          onPointerMove={(e) => {
            baseHandlers.onPointerMove(e);
            moveHandlers.onPointerMove(e);
          }}
          onPointerUp={(e) => {
            baseHandlers.onPointerUp();
            moveHandlers.onPointerUp(e);
          }}
          onPointerCancel={baseHandlers.onPointerCancel}
          style={{ touchAction: "none", cursor: readOnly ? "default" : "crosshair" }}
        >
          {/* Reference background — fundus circle, optic disc, macula. */}
          <circle
            cx={VIEW_W / 2}
            cy={VIEW_H / 2}
            r={VIEW_W * 0.48}
            fill="#fff5e6"
            stroke="#b08968"
            strokeWidth={1}
          />
          {/* Optic disc: nasal side (right=OD: nasal is RIGHT half; OS: LEFT half). */}
          <circle
            cx={VIEW_W * (eye === "OD" ? 0.68 : 0.32)}
            cy={VIEW_H * 0.5}
            r={VIEW_W * 0.07}
            fill="#fde7c2"
            stroke="#9c6b3f"
            strokeWidth={1}
            data-testid={`rdc-optic-disc-${eye}`}
          />
          {/* Macula center (slightly temporal to disc, here just at canvas center). */}
          <circle
            cx={VIEW_W * 0.5}
            cy={VIEW_H * 0.5}
            r={VIEW_W * 0.025}
            fill="#7a3c0c"
            data-testid={`rdc-macula-${eye}`}
          />
          {/* Vessel guides — coarse arcs from the disc. Decorative only. */}
          <path
            d={
              eye === "OD"
                ? `M ${VIEW_W * 0.66} ${VIEW_H * 0.5} Q ${VIEW_W * 0.45} ${VIEW_H * 0.2} ${VIEW_W * 0.15} ${VIEW_H * 0.25}`
                : `M ${VIEW_W * 0.34} ${VIEW_H * 0.5} Q ${VIEW_W * 0.55} ${VIEW_H * 0.2} ${VIEW_W * 0.85} ${VIEW_H * 0.25}`
            }
            fill="none"
            stroke="#b22222"
            strokeWidth={0.6}
            opacity={0.5}
          />

          {/* Saved annotations. */}
          {annotationsByEye[eye].map((a) => (
            <AnnotationGlyph
              key={a.id}
              annotation={a}
              selected={a.id === selectedId}
              onPointerDown={(e) => onAnnotationPointerDown(e, a)}
            />
          ))}

          {/* Freehand draft preview. */}
          {draftEye === eye && draftPoints.length >= 2 && (
            <path
              data-testid={`rdc-draft-${eye}`}
              d={pointsToPathD(draftPoints)}
              fill="none"
              stroke={color}
              strokeWidth={1.4}
              opacity={0.7}
            />
          )}
        </svg>
      </div>
    );
  };

  return (
    <div className="rdc" data-testid="rdc-root">
      {!readOnly && (
        <Toolbar
          tool={tool}
          color={color}
          onSelectTool={setTool}
          onColorChange={setColor}
          onUndo={undo}
          onRedo={redo}
          undoEnabled={history.past.length > 0}
          redoEnabled={history.future.length > 0}
          onDelete={onDelete}
          deleteEnabled={!!selectedId}
          onClearAll={onClearAll}
          clearAllEnabled={doc.annotations.length > 0}
        />
      )}
      <div className="rdc__panes">
        {renderEye("OD")}
        {renderEye("OS")}
      </div>
      {readOnly && (
        <p className="muted" data-testid="rdc-readonly-note">
          Signed artifact — editing disabled. Use “Save as new version” to amend.
        </p>
      )}
    </div>
  );
}

// --- toolbar ----------------------------------------------------------

interface ToolbarProps {
  tool: Tool;
  color: string;
  onSelectTool: (t: Tool) => void;
  onColorChange: (c: string) => void;
  onUndo: () => void;
  onRedo: () => void;
  undoEnabled: boolean;
  redoEnabled: boolean;
  onDelete: () => void;
  deleteEnabled: boolean;
  onClearAll: () => void;
  clearAllEnabled: boolean;
}

function Toolbar(props: ToolbarProps) {
  const { tool } = props;
  const isActive = (kind: AnnotationKind | "select", st?: SymbolType) => {
    if (kind === "select") return tool.kind === "select";
    if (kind === "freehand") return tool.kind === "freehand";
    if (kind === "text") return tool.kind === "text";
    return tool.kind === "symbol" && tool.symbol_type === st;
  };
  return (
    <div className="rdc__toolbar" data-testid="rdc-toolbar">
      <div className="rdc__tool-group">
        <button
          type="button"
          aria-pressed={isActive("select")}
          data-testid="rdc-tool-select"
          onClick={() => props.onSelectTool({ kind: "select" })}
        >
          Select
        </button>
        <button
          type="button"
          aria-pressed={isActive("freehand")}
          data-testid="rdc-tool-freehand"
          onClick={() => props.onSelectTool({ kind: "freehand" })}
        >
          Freehand
        </button>
        <button
          type="button"
          aria-pressed={isActive("text")}
          data-testid="rdc-tool-text"
          onClick={() => props.onSelectTool({ kind: "text" })}
        >
          Text label
        </button>
      </div>

      <div className="rdc__tool-group rdc__symbols">
        {SYMBOL_LIBRARY.map((s) => (
          <button
            type="button"
            key={s.key}
            data-testid={`rdc-tool-symbol-${s.key}`}
            aria-pressed={isActive("symbol", s.key)}
            title={s.display}
            onClick={() =>
              props.onSelectTool({ kind: "symbol", symbol_type: s.key })
            }
          >
            {s.short}
          </button>
        ))}
      </div>

      <div className="rdc__tool-group">
        <label className="rdc__color">
          <span className="muted">Color</span>
          <input
            type="color"
            value={props.color}
            data-testid="rdc-color"
            onChange={(e) => props.onColorChange(e.target.value)}
          />
        </label>
      </div>

      <div className="rdc__tool-group">
        <button
          type="button"
          data-testid="rdc-undo"
          onClick={props.onUndo}
          disabled={!props.undoEnabled}
        >
          Undo
        </button>
        <button
          type="button"
          data-testid="rdc-redo"
          onClick={props.onRedo}
          disabled={!props.redoEnabled}
        >
          Redo
        </button>
        <button
          type="button"
          data-testid="rdc-delete"
          onClick={props.onDelete}
          disabled={!props.deleteEnabled}
        >
          Delete
        </button>
        <button
          type="button"
          data-testid="rdc-clear-all"
          onClick={props.onClearAll}
          disabled={!props.clearAllEnabled}
        >
          Clear all
        </button>
      </div>
    </div>
  );
}

// --- annotation glyph render -----------------------------------------

interface GlyphProps {
  annotation: Annotation;
  selected: boolean;
  onPointerDown: (e: React.PointerEvent<SVGElement>) => void;
}

function AnnotationGlyph({ annotation, selected, onPointerDown }: GlyphProps) {
  const cx = annotation.x * VIEW_W;
  const cy = annotation.y * VIEW_H;
  const accent = selected ? "#000" : annotation.color;

  if (annotation.kind === "symbol") {
    return (
      <g
        data-testid={`rdc-annotation-${annotation.id}`}
        data-kind="symbol"
        data-symbol={annotation.symbol_type}
        onPointerDown={onPointerDown}
      >
        <circle
          cx={cx}
          cy={cy}
          r={9}
          fill="#fff"
          stroke={accent}
          strokeWidth={selected ? 2 : 1.2}
        />
        <text
          x={cx}
          y={cy + 3}
          textAnchor="middle"
          fontSize={8}
          fontFamily="monospace"
          fill={accent}
        >
          {symbolGlyph(annotation.symbol_type)}
        </text>
        <title>{SYMBOL_DISPLAY_BY_KEY[annotation.symbol_type]}</title>
      </g>
    );
  }

  if (annotation.kind === "text") {
    return (
      <g
        data-testid={`rdc-annotation-${annotation.id}`}
        data-kind="text"
        onPointerDown={onPointerDown}
      >
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          fontSize={9}
          fill={accent}
          fontWeight={selected ? 700 : 500}
        >
          {annotation.text}
        </text>
      </g>
    );
  }

  // freehand
  return (
    <g
      data-testid={`rdc-annotation-${annotation.id}`}
      data-kind="freehand"
      onPointerDown={onPointerDown}
    >
      <path
        d={pointsToPathD(annotation.points)}
        fill="none"
        stroke={accent}
        strokeWidth={selected ? 2 : 1.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </g>
  );
}

// --- helpers ---------------------------------------------------------

function useReducerWithSync(initial: DrawingDocument): [
  HistoryState,
  React.Dispatch<HistoryAction>
] {
  const [state, setState] = useState<HistoryState>(() =>
    initHistory(initial ?? EMPTY_DRAWING)
  );
  const dispatch = useCallback((action: HistoryAction) => {
    setState((prev) => historyReducer(prev, action));
  }, []);
  return [state, dispatch];
}
