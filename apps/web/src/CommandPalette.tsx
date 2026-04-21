// Phase 38 — A1 — ⌘K / Ctrl+K command palette.
//
// A lightweight, dependency-free palette that lets the doctor drive
// NoteWorkspace + encounter actions without the mouse. Actions are
// declarative — each is a small record that the palette renders and
// invokes on Enter.
//
// The palette itself owns no domain logic. Consumers pass in an
// `actions` array; the palette handles input, filtering, keyboard
// navigation, and accessible focus.

import { useEffect, useMemo, useRef, useState } from "react";

export interface CommandAction {
  /** Stable id for React keys + data-testid. */
  id: string;
  /** Primary display string (what the doctor searches for). */
  label: string;
  /** Optional grouping for visual organization. */
  section?: string;
  /** Short context string shown right-aligned. */
  context?: string;
  /** Optional keyboard hint shown right-aligned. */
  kbd?: string;
  /** Extra searchable text (aliases / abbreviations / tags). */
  keywords?: string;
  /** Invoked when the user picks this action. */
  run: () => void | Promise<void>;
  /** If false, the action is hidden. */
  when?: boolean;
}

interface Props {
  open: boolean;
  actions: CommandAction[];
  onClose: () => void;
  placeholder?: string;
}

function tokenize(s: string): string[] {
  return s.toLowerCase().split(/\s+/).filter(Boolean);
}

function score(action: CommandAction, query: string): number {
  if (!query) return 1;
  const hay = (
    action.label +
    " " +
    (action.keywords || "") +
    " " +
    (action.section || "") +
    " " +
    (action.context || "")
  ).toLowerCase();
  const toks = tokenize(query);
  let s = 0;
  for (const t of toks) {
    if (!hay.includes(t)) return 0;
    s += hay.startsWith(t) ? 3 : 1;
  }
  return s;
}

export function CommandPalette({ open, actions, onClose, placeholder }: Props) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const visible = useMemo(
    () => actions.filter((a) => a.when !== false),
    [actions]
  );

  const filtered = useMemo(() => {
    const scored = visible
      .map((a) => ({ a, s: score(a, query) }))
      .filter((r) => r.s > 0)
      .sort((x, y) => y.s - x.s)
      .map((r) => r.a);
    return scored;
  }, [visible, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setCursor(0);
      return;
    }
    const t = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(t);
  }, [open]);

  useEffect(() => {
    setCursor((c) => Math.min(Math.max(c, 0), Math.max(filtered.length - 1, 0)));
  }, [filtered]);

  if (!open) return null;

  const run = async (a: CommandAction) => {
    onClose();
    try {
      await a.run();
    } catch {
      // caller is expected to surface its own errors via a banner;
      // the palette intentionally swallows to avoid unhandled rejections.
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const pick = filtered[cursor];
      if (pick) run(pick);
    }
  };

  // Group by section for display.
  const sections: { name: string; rows: CommandAction[] }[] = [];
  for (const a of filtered) {
    const name = a.section || "Actions";
    const bucket = sections.find((s) => s.name === name);
    if (bucket) bucket.rows.push(a);
    else sections.push({ name, rows: [a] });
  }

  return (
    <div
      className="cmdk-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      data-testid="cmdk"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="cmdk" onKeyDown={onKeyDown}>
        <div className="cmdk__input-wrap">
          <input
            ref={inputRef}
            className="cmdk__input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder ?? "Type a command — Enter to run, Esc to close"}
            aria-label="Command input"
            data-testid="cmdk-input"
          />
        </div>
        <div className="cmdk__results" role="listbox" aria-label="Commands">
          {filtered.length === 0 ? (
            <div className="cmdk__empty" data-testid="cmdk-empty">
              No matching actions.
            </div>
          ) : (
            sections.map((section) => (
              <div key={section.name}>
                <div className="cmdk__section">{section.name}</div>
                {section.rows.map((a) => {
                  const idx = filtered.indexOf(a);
                  const active = idx === cursor;
                  return (
                    <button
                      type="button"
                      key={a.id}
                      className="cmdk__item"
                      data-active={active}
                      data-testid={`cmdk-item-${a.id}`}
                      role="option"
                      aria-selected={active}
                      onMouseEnter={() => setCursor(idx)}
                      onClick={() => run(a)}
                    >
                      <span>
                        <span className="cmdk__item__label">{a.label}</span>
                        {a.context && (
                          <>
                            {" "}
                            <span className="cmdk__item__context">
                              {a.context}
                            </span>
                          </>
                        )}
                      </span>
                      {a.kbd && (
                        <span className="cmdk__item__kbd">{a.kbd}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/** Install a global ⌘K/Ctrl+K listener that calls `open()`. */
export function useCommandPaletteShortcut(open: () => void): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mac = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k";
      if (mac) {
        e.preventDefault();
        open();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);
}
