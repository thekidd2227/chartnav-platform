// Phase 38 — A5 — note-version diff + delta digest.
//
// Pure client component that takes a list of NoteVersion rows for
// one encounter and renders a side-by-side text diff of two
// versions, plus a short plain-English digest above it.
//
// The diff algorithm is deliberately simple — a word-level LCS
// produces enough signal for a medical-note review without adding
// a dependency. It is bounded by the max text the note workspace
// already accepts, so running it on the UI thread is fine.

import { useMemo, useState } from "react";
import { NoteVersion } from "./api";

interface Props {
  versions: NoteVersion[];
  defaultSecondId?: number;
}

type Token =
  | { kind: "eq"; text: string }
  | { kind: "ins"; text: string }
  | { kind: "del"; text: string };

function splitWords(s: string | null | undefined): string[] {
  if (!s) return [];
  // Keep whitespace as its own token so re-assembly preserves layout.
  return s.split(/(\s+)/).filter((x) => x.length > 0);
}

/** Word-level LCS → list of eq/ins/del tokens. */
function diffWords(a: string, b: string): Token[] {
  const A = splitWords(a);
  const B = splitWords(b);
  const n = A.length;
  const m = B.length;
  // DP matrix sized (n+1) x (m+1). At ~2k words per side this is ~4M
  // cells — fine on-thread for realistic note sizes. For very large
  // drafts we truncate.
  const MAX = 2000;
  if (n > MAX || m > MAX) {
    return [
      { kind: "del", text: a || "" },
      { kind: "ins", text: b || "" },
    ];
  }
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      if (A[i] === B[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const out: Token[] = [];
  let i = 0;
  let j = 0;
  const push = (kind: Token["kind"], text: string) => {
    const last = out[out.length - 1];
    if (last && last.kind === kind) last.text += text;
    else out.push({ kind, text });
  };
  while (i < n && j < m) {
    if (A[i] === B[j]) {
      push("eq", A[i]);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      push("del", A[i]);
      i++;
    } else {
      push("ins", B[j]);
      j++;
    }
  }
  while (i < n) {
    push("del", A[i++]);
  }
  while (j < m) {
    push("ins", B[j++]);
  }
  return out;
}

function joinSide(tokens: Token[], side: "left" | "right") {
  return tokens.map((t, idx) => {
    if (t.kind === "eq")
      return (
        <span key={idx}>
          {t.text}
        </span>
      );
    if (side === "left" && t.kind === "del")
      return (
        <span key={idx} className="notediff__tok--del">
          {t.text}
        </span>
      );
    if (side === "right" && t.kind === "ins")
      return (
        <span key={idx} className="notediff__tok--ins">
          {t.text}
        </span>
      );
    return null;
  });
}

function summariseDigest(a: NoteVersion, b: NoteVersion, tokens: Token[]): string[] {
  const lines: string[] = [];
  if (a.draft_status !== b.draft_status) {
    lines.push(
      `Status: ${a.draft_status} → ${b.draft_status}`
    );
  }
  if ((a.generated_by || "system") !== (b.generated_by || "system")) {
    lines.push(
      `Generator: ${a.generated_by ?? "—"} → ${b.generated_by ?? "—"}`
    );
  }
  let ins = 0;
  let del = 0;
  for (const t of tokens) {
    if (t.kind === "ins" && /\S/.test(t.text)) ins += 1;
    else if (t.kind === "del" && /\S/.test(t.text)) del += 1;
  }
  if (ins || del) {
    lines.push(`Text: ${ins} addition${ins === 1 ? "" : "s"}, ${del} removal${del === 1 ? "" : "s"}`);
  }
  if (a.version_number !== b.version_number) {
    lines.push(`Version: v${a.version_number} → v${b.version_number}`);
  }
  if (!lines.length) lines.push("No textual changes between these versions.");
  return lines;
}

export function NoteDiff({ versions, defaultSecondId }: Props) {
  const sorted = useMemo(
    () => [...versions].sort((x, y) => x.version_number - y.version_number),
    [versions]
  );

  const latestId = sorted[sorted.length - 1]?.id ?? null;
  const prevId = sorted[sorted.length - 2]?.id ?? null;

  const [rightId, setRightId] = useState<number | null>(
    defaultSecondId ?? latestId
  );
  const [leftId, setLeftId] = useState<number | null>(prevId);

  const right = sorted.find((v) => v.id === rightId) ?? null;
  const left = sorted.find((v) => v.id === leftId) ?? null;

  const tokens = useMemo(
    () => (left && right ? diffWords(left.note_text || "", right.note_text || "") : []),
    [left, right]
  );
  const digest = useMemo(
    () => (left && right ? summariseDigest(left, right, tokens) : []),
    [left, right, tokens]
  );

  if (sorted.length < 2) {
    return (
      <div className="subtle-note" data-testid="notediff-empty">
        Diff requires at least two note versions on this encounter.
      </div>
    );
  }

  return (
    <div className="notediff" data-testid="notediff">
      <div className="notediff__head">
        <strong>Compare</strong>
        <select
          className="notediff__select"
          data-testid="notediff-left"
          value={leftId ?? ""}
          onChange={(e) => setLeftId(e.target.value ? Number(e.target.value) : null)}
          aria-label="From version"
        >
          {sorted.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number} · {v.draft_status}
            </option>
          ))}
        </select>
        <span>→</span>
        <select
          className="notediff__select"
          data-testid="notediff-right"
          value={rightId ?? ""}
          onChange={(e) => setRightId(e.target.value ? Number(e.target.value) : null)}
          aria-label="To version"
        >
          {sorted.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number} · {v.draft_status}
            </option>
          ))}
        </select>
      </div>

      <div className="notediff__digest" data-testid="notediff-digest">
        <strong>What changed</strong>
        <ul>
          {digest.map((line, idx) => (
            <li key={idx}>{line}</li>
          ))}
        </ul>
      </div>

      <div className="notediff__body">
        <div className="notediff__col">
          <h4>Previous</h4>
          <pre className="notediff__pre" data-testid="notediff-left-body">
            {joinSide(tokens, "left")}
          </pre>
        </div>
        <div className="notediff__col">
          <h4>Current</h4>
          <pre className="notediff__pre" data-testid="notediff-right-body">
            {joinSide(tokens, "right")}
          </pre>
        </div>
      </div>
    </div>
  );
}
