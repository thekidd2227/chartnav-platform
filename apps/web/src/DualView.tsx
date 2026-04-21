// Phase 38 — A2 — dual-view transcript ↔ draft with cross-highlight.
//
// The generator does not currently emit span-level provenance, so
// cross-highlight is a heuristic on top of the existing data: when
// the doctor selects a phrase in either pane, the other pane
// highlights a matching substring if one exists. When span-level
// provenance does land in `extracted_findings`, this component can
// switch to anchored highlighting without changing its interface.

import { useMemo, useState } from "react";

interface Props {
  transcript: string;
  draft: string;
  /** Optional hard anchors: [[transcriptStart, transcriptEnd, draftStart, draftEnd], ...].
   *  If present, hovering an anchor highlights both sides exactly.
   *  When empty, the heuristic substring match is used. */
  anchors?: { tFrom: number; tTo: number; dFrom: number; dTo: number }[];
}

function phraseAt(text: string, index: number): { start: number; end: number } | null {
  if (!text) return null;
  const i = Math.max(0, Math.min(index, text.length - 1));
  // Walk outward to sentence / punctuation boundaries.
  const boundaries = /[.!?\n]/;
  let start = i;
  while (start > 0 && !boundaries.test(text[start - 1])) start--;
  let end = i;
  while (end < text.length && !boundaries.test(text[end])) end++;
  return { start, end: end + 1 };
}

function wrapSpan(
  text: string,
  range: { start: number; end: number } | null,
  testId?: string
) {
  if (!text) return null;
  if (!range) return <span>{text}</span>;
  return (
    <>
      <span>{text.slice(0, range.start)}</span>
      <mark
        className="dualview__span--active"
        data-testid={testId ?? "dualview-match"}
      >
        {text.slice(range.start, range.end)}
      </mark>
      <span>{text.slice(range.end)}</span>
    </>
  );
}

export function DualView({ transcript, draft, anchors }: Props) {
  const [selected, setSelected] = useState<{
    side: "transcript" | "draft";
    start: number;
    end: number;
  } | null>(null);

  const mirror = useMemo(() => {
    if (!selected) return null;
    const src = selected.side === "transcript" ? transcript : draft;
    const other = selected.side === "transcript" ? draft : transcript;
    // Hard anchors path (future generator with provenance).
    if (anchors && anchors.length) {
      const hit = anchors.find((a) => {
        if (selected.side === "transcript") {
          return selected.start >= a.tFrom && selected.end <= a.tTo;
        }
        return selected.start >= a.dFrom && selected.end <= a.dTo;
      });
      if (hit) {
        return selected.side === "transcript"
          ? { start: hit.dFrom, end: hit.dTo }
          : { start: hit.tFrom, end: hit.tTo };
      }
    }
    // Heuristic: longest token window from src that also appears in other.
    const picked = src.slice(selected.start, selected.end).trim();
    if (picked.length < 4) return null;
    // Try shrinking from both ends until we find a match.
    let s = 0;
    let e = picked.length;
    let idx = -1;
    while (e - s >= 4) {
      idx = other.toLowerCase().indexOf(picked.slice(s, e).toLowerCase());
      if (idx >= 0) return { start: idx, end: idx + (e - s) };
      if (picked[s] === " ") s++;
      else if (picked[e - 1] === " ") e--;
      else if (e - s > 12) {
        // strip a word from the front, then from the back
        const fwd = picked.indexOf(" ", s + 1);
        if (fwd > 0 && fwd < e) s = fwd + 1;
        else e--;
      } else {
        e--;
      }
    }
    return null;
  }, [selected, transcript, draft, anchors]);

  const selRange = selected ? { start: selected.start, end: selected.end } : null;

  // Use textContent offsets — simple and stable for plaintext panes.
  const onSelectionChange = (side: "transcript" | "draft") => () => {
    const sel = typeof window !== "undefined" ? window.getSelection() : null;
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      setSelected(null);
      return;
    }
    const range = sel.getRangeAt(0);
    const container = range.commonAncestorContainer;
    const pane =
      container.nodeType === 1
        ? (container as Element).closest(`[data-dual-pane="${side}"]`)
        : (container.parentElement ?? null)?.closest(`[data-dual-pane="${side}"]`);
    if (!pane) return;
    const start = rangeOffsetInPane(pane as HTMLElement, range.startContainer, range.startOffset);
    const end = rangeOffsetInPane(pane as HTMLElement, range.endContainer, range.endOffset);
    if (start != null && end != null && end > start) {
      setSelected({ side, start, end });
      return;
    }
    // If heuristic offsets fail, derive from text similarity search.
    const phrase = sel.toString();
    const src = side === "transcript" ? transcript : draft;
    const idx = phrase ? src.indexOf(phrase) : -1;
    if (phrase && idx >= 0) {
      setSelected({ side, start: idx, end: idx + phrase.length });
    } else if (!phrase) {
      setSelected(null);
    }
  };

  const clickFallback = (side: "transcript" | "draft") => (
    ev: React.MouseEvent<HTMLDivElement>
  ) => {
    // If no selection window is open, use a phrase-around-click.
    if (typeof window !== "undefined") {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed) return;
    }
    const node = ev.currentTarget;
    const offset = Math.max(0, Math.min(node.textContent?.length ?? 0, 0));
    // Without full coordinate math we fall back to nothing smart.
    const src = side === "transcript" ? transcript : draft;
    const r = phraseAt(src, offset);
    if (r) setSelected({ side, start: r.start, end: r.end });
  };

  return (
    <div className="dualview" data-testid="dualview">
      <div
        className="dualview__pane"
        data-dual-pane="transcript"
        data-testid="dualview-transcript"
        onMouseUp={onSelectionChange("transcript")}
        onClick={clickFallback("transcript")}
      >
        <h4>Transcript</h4>
        <div style={{ whiteSpace: "pre-wrap", fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12.5 }}>
          {selected?.side === "transcript"
            ? wrapSpan(transcript, selRange, "dualview-transcript-match")
            : wrapSpan(transcript, mirror && selected?.side === "draft" ? mirror : null, "dualview-transcript-mirror")}
        </div>
      </div>
      <div
        className="dualview__pane"
        data-dual-pane="draft"
        data-testid="dualview-draft"
        onMouseUp={onSelectionChange("draft")}
        onClick={clickFallback("draft")}
      >
        <h4>Draft</h4>
        <div style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
          {selected?.side === "draft"
            ? wrapSpan(draft, selRange, "dualview-draft-match")
            : wrapSpan(draft, mirror && selected?.side === "transcript" ? mirror : null, "dualview-draft-mirror")}
        </div>
      </div>
    </div>
  );
}

function rangeOffsetInPane(
  pane: HTMLElement,
  node: Node,
  off: number
): number | null {
  // Walk the text nodes inside `pane` in document order, summing
  // their lengths until we hit `node`.
  let seen = 0;
  const walker = document.createTreeWalker(pane, NodeFilter.SHOW_TEXT);
  let current: Node | null = walker.currentNode;
  while (current) {
    if (current === node) {
      return seen + off;
    }
    seen += (current.textContent?.length ?? 0);
    current = walker.nextNode();
  }
  return null;
}
