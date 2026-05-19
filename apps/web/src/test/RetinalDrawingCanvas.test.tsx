import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { RetinalDrawingCanvas } from "../RetinalDrawingCanvas";
import {
  type DrawingDocument,
  EMPTY_DRAWING,
  type SymbolType,
} from "../retinalAnnotations";

function Harness({
  initial = EMPTY_DRAWING,
  readOnly = false,
  onChangeSpy,
}: {
  initial?: DrawingDocument;
  readOnly?: boolean;
  onChangeSpy?: (next: DrawingDocument) => void;
}) {
  const [doc, setDoc] = useState<DrawingDocument>(initial);
  return (
    <RetinalDrawingCanvas
      value={doc}
      onChange={(next) => {
        onChangeSpy?.(next);
        setDoc(next);
      }}
      readOnly={readOnly}
    />
  );
}

describe("RetinalDrawingCanvas", () => {
  it("renders OD and OS panes with reference markers", () => {
    render(<Harness />);
    expect(screen.getByTestId("rdc-eye-OD")).toBeInTheDocument();
    expect(screen.getByTestId("rdc-eye-OS")).toBeInTheDocument();
    expect(screen.getByTestId("rdc-optic-disc-OD")).toBeInTheDocument();
    expect(screen.getByTestId("rdc-optic-disc-OS")).toBeInTheDocument();
    expect(screen.getByTestId("rdc-macula-OD")).toBeInTheDocument();
    expect(screen.getByTestId("rdc-macula-OS")).toBeInTheDocument();
  });

  it("placing a symbol creates a manual annotation with eye/type/x/y", async () => {
    const onChange = vi.fn();
    render(<Harness onChangeSpy={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("rdc-tool-symbol-microaneurysm"));

    fireEvent.pointerDown(screen.getByTestId("rdc-svg-OD"), {
      clientX: 80,
      clientY: 40,
      pointerId: 1,
    });

    expect(onChange).toHaveBeenCalled();
    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(last.annotations).toHaveLength(1);
    expect(last.annotations[0]).toMatchObject({
      kind: "symbol",
      symbol_type: "microaneurysm" as SymbolType,
      eye: "OD",
      source: "manual",
    });
    expect(typeof last.annotations[0].x).toBe("number");
    expect(typeof last.annotations[0].y).toBe("number");
  });

  it("text label tool prompts and creates a text annotation", async () => {
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("Note here");
    const onChange = vi.fn();
    render(<Harness onChangeSpy={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("rdc-tool-text"));

    fireEvent.pointerDown(screen.getByTestId("rdc-svg-OS"), {
      clientX: 100,
      clientY: 100,
      pointerId: 1,
    });

    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(last.annotations[0]).toMatchObject({
      kind: "text",
      eye: "OS",
      text: "Note here",
      source: "manual",
    });
    promptSpy.mockRestore();
  });

  it("undo reverts the last placement; redo replays it", async () => {
    const onChange = vi.fn();
    render(<Harness onChangeSpy={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("rdc-tool-symbol-drusen"));
    fireEvent.pointerDown(screen.getByTestId("rdc-svg-OD"), {
      clientX: 50,
      clientY: 50,
      pointerId: 1,
    });

    const afterPlace = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(afterPlace.annotations).toHaveLength(1);

    await user.click(screen.getByTestId("rdc-undo"));
    const afterUndo = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(afterUndo.annotations).toHaveLength(0);

    await user.click(screen.getByTestId("rdc-redo"));
    const afterRedo = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(afterRedo.annotations).toHaveLength(1);
    const replayed = afterRedo.annotations[0];
    if (replayed.kind === "symbol") {
      expect(replayed.symbol_type).toBe("drusen");
    } else {
      throw new Error(`expected symbol annotation, got ${replayed.kind}`);
    }
  });

  it("delete removes the selected annotation", async () => {
    const onChange = vi.fn();
    const seeded: DrawingDocument = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [
        {
          id: "a1",
          kind: "symbol",
          symbol_type: "drusen",
          eye: "OD",
          x: 0.4,
          y: 0.4,
          color: "#000",
          source: "manual",
          created_at: "2026-05-04T12:00:00+00:00",
        },
      ],
    };
    render(<Harness initial={seeded} onChangeSpy={onChange} />);
    const user = userEvent.setup();

    // Select then delete.
    fireEvent.pointerDown(screen.getByTestId("rdc-annotation-a1"));
    await user.click(screen.getByTestId("rdc-delete"));

    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(last.annotations).toHaveLength(0);
  });

  it("freehand polyline saves points without smoothing", async () => {
    const onChange = vi.fn();
    render(<Harness onChangeSpy={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("rdc-tool-freehand"));

    const svg = screen.getByTestId("rdc-svg-OD");
    // jsdom returns 0/0 sized client rects on SVG nodes; mock so the
    // canvas's normalized-coord math produces distinct points across
    // the move sequence.
    vi.spyOn(svg, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 200,
      bottom: 200,
      width: 200,
      height: 200,
      toJSON: () => ({}),
    } as DOMRect);

    fireEvent.pointerDown(svg, { clientX: 10, clientY: 10, pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 60, clientY: 60, pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 120, clientY: 120, pointerId: 1 });
    fireEvent.pointerUp(svg, { pointerId: 1 });

    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    const fh = last.annotations.find((a) => a.kind === "freehand");
    expect(fh).toBeDefined();
    if (fh && fh.kind === "freehand") {
      expect(fh.points.length).toBeGreaterThanOrEqual(2);
      expect(fh.eye).toBe("OD");
      expect(fh.source).toBe("manual");
    }
  });

  it("readOnly hides the toolbar and shows the read-only note", () => {
    render(<Harness readOnly />);
    expect(screen.queryByTestId("rdc-toolbar")).not.toBeInTheDocument();
    expect(screen.getByTestId("rdc-readonly-note")).toBeInTheDocument();
  });

  it("readOnly ignores pointer placement attempts", () => {
    const onChange = vi.fn();
    render(<Harness readOnly onChangeSpy={onChange} />);
    fireEvent.pointerDown(screen.getByTestId("rdc-svg-OD"), {
      clientX: 50,
      clientY: 50,
      pointerId: 1,
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("clear all wipes annotations from both eyes", async () => {
    const seeded: DrawingDocument = {
      schema_version: 1,
      canvas_type: "retinal_diagram",
      annotations: [
        {
          id: "a1",
          kind: "symbol",
          symbol_type: "drusen",
          eye: "OD",
          x: 0.4,
          y: 0.4,
          color: "#000",
          source: "manual",
          created_at: "2026-05-04T12:00:00+00:00",
        },
        {
          id: "a2",
          kind: "symbol",
          symbol_type: "flame_hemorrhage",
          eye: "OS",
          x: 0.6,
          y: 0.6,
          color: "#000",
          source: "manual",
          created_at: "2026-05-04T12:00:00+00:00",
        },
      ],
    };
    const onChange = vi.fn();
    render(<Harness initial={seeded} onChangeSpy={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByTestId("rdc-clear-all"));

    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0] as DrawingDocument;
    expect(last.annotations).toHaveLength(0);
  });
});
