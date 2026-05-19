/**
 * Markdown deck parser.
 *
 * The deck markdown shape (locked in the master kit) is:
 *
 *   # <Deck title>
 *
 *   > <one-or-more-line description>
 *
 *   **Audience:** ...
 *   **Purpose:** ...
 *   **CTA / next step:** ...
 *
 *   **Safe-claims contract.** ...
 *
 *   ---
 *
 *   ## Slide N — <slide title>
 *
 *   - **Title:** <title>
 *   - **Purpose:** <purpose>     (sometimes)
 *   - **Content:**
 *     - bullet
 *     - bullet
 *   - **Speaker notes:** <notes>
 *   - **Visual:** <visual cue>
 *
 *   ## Slide N+1 — ...
 *
 * This parser is intentionally tolerant — decks vary slightly
 * (e.g. "Subtitle:" appears in a few decks; the educational deck
 * uses "Slide 4.5"; the buyer-objection-handling deck has no
 * slides at all). When something doesn't match the canonical
 * shape we surface it as a body line on the slide rather than
 * losing it.
 *
 * Output shape:
 *   {
 *     deckId:        string  (filename stem),
 *     deckTitle:     string,
 *     description:   string  (the leading blockquote, joined),
 *     audience:      string  | null,
 *     purpose:       string  | null,
 *     cta:           string  | null,
 *     safeContract:  string  | null,
 *     slides: [{
 *       number:      string,
 *       title:       string,
 *       purpose:     string | null,
 *       contentLines: string[],   // bullet text, * stripped
 *       speakerNotes: string | null,
 *       visual:      string | null,
 *       contact:     string | null,    // "Contact:" line
 *     }, ...]
 *   }
 */

import { readFileSync } from "node:fs";
import path from "node:path";

export function parseDeckMarkdown(filePath) {
  const text = readFileSync(filePath, "utf-8");
  const stem = path.basename(filePath, ".md");
  const lines = text.split(/\r?\n/);

  // 1. Header / metadata.
  let i = 0;
  let deckTitle = "";
  while (i < lines.length && !lines[i].startsWith("# ")) i++;
  if (i < lines.length) {
    deckTitle = lines[i].replace(/^#\s+/, "").trim();
    i++;
  }

  // 2. Leading blockquote ("> ...").
  const descLines = [];
  while (i < lines.length && (lines[i].trim() === "" || lines[i].startsWith(">"))) {
    if (lines[i].startsWith(">")) {
      descLines.push(lines[i].replace(/^>\s?/, "").trim());
    }
    i++;
  }

  // 3. Front-matter (Audience / Purpose / CTA / Safe-claims).
  // Each can wrap across several lines until the next bold header
  // or the `---` rule.
  let audience = null;
  let purpose = null;
  let cta = null;
  let safeContract = null;
  let active = null; // which field we're currently appending to
  const set = (key, val) => {
    if (key === "audience") audience = val;
    else if (key === "purpose") purpose = val;
    else if (key === "cta") cta = val;
    else if (key === "safe") safeContract = val;
  };
  const get = (key) =>
    key === "audience" ? audience
    : key === "purpose" ? purpose
    : key === "cta" ? cta
    : key === "safe" ? safeContract
    : null;
  while (i < lines.length && !/^---\s*$/.test(lines[i])) {
    const raw = lines[i];
    const l = raw.trim();
    const audienceMatch = l.match(/^\*\*Audience:\*\*\s*(.*)$/);
    const purposeMatch = l.match(/^\*\*Purpose:\*\*\s*(.*)$/);
    const ctaMatch = l.match(/^\*\*CTA(?: ?\/ ?next step)?:\*\*\s*(.*)$/);
    const safeMatch = l.match(/^\*\*Safe[- ]claims contract\.\*\*\s*(.*)$/);
    if (audienceMatch) {
      active = "audience";
      set("audience", audienceMatch[1]);
    } else if (purposeMatch) {
      active = "purpose";
      set("purpose", purposeMatch[1]);
    } else if (ctaMatch) {
      active = "cta";
      set("cta", ctaMatch[1]);
    } else if (safeMatch) {
      active = "safe";
      set("safe", safeMatch[1]);
    } else if (l.length === 0) {
      // Blank line ends the active field.
      active = null;
    } else if (active) {
      // Continuation of the current field.
      set(active, (get(active) + " " + l).trim());
    }
    i++;
  }
  // Skip the `---` rule.
  if (i < lines.length && /^---\s*$/.test(lines[i])) i++;

  // 4. Slides.
  const slides = [];
  let cur = null;
  let inContent = false;
  let inSpeakerNotes = false;
  for (; i < lines.length; i++) {
    const raw = lines[i];
    const l = raw.trim();
    const slideHeader = l.match(/^##\s+Slide\s+([\d.]+)\s*[—-]?\s*(.*)$/);
    if (slideHeader) {
      if (cur) slides.push(cur);
      cur = {
        number: slideHeader[1],
        title: slideHeader[2] || "",
        purpose: null,
        contentLines: [],
        speakerNotes: null,
        visual: null,
        contact: null,
      };
      inContent = false;
      inSpeakerNotes = false;
      continue;
    }
    if (!cur) continue;
    if (/^---\s*$/.test(l)) {
      // Some decks have horizontal rules between slides, others
      // not. End any active multi-line region.
      inContent = false;
      inSpeakerNotes = false;
      continue;
    }

    // Match the per-slide canonical fields.
    const titleM = l.match(/^[-*]\s*\*\*Title:\*\*\s*(.+)$/);
    const subtitleM = l.match(/^[-*]\s*\*\*Subtitle:\*\*\s*(.+)$/);
    const purposeM = l.match(/^[-*]\s*\*\*Purpose:\*\*\s*(.+)$/);
    const contentM = l.match(/^[-*]\s*\*\*Content(?:[^:]*)?:\*\*\s*(.*)$/);
    const speakerM = l.match(/^[-*]\s*\*\*Speaker notes:\*\*\s*(.+)$/);
    const visualM = l.match(/^[-*]\s*\*\*Visual:\*\*\s*(.+)$/);
    const contactM = l.match(/^[-*]\s*\*\*Contact:\*\*\s*(.+)$/);

    if (titleM) {
      // Override the slide title with the explicit "Title:" value
      // (keeps the slide-header numbering separate from the
      // displayed title).
      cur.title = titleM[1].trim();
      inContent = false;
      inSpeakerNotes = false;
      continue;
    }
    if (subtitleM) {
      cur.purpose = subtitleM[1].trim();
      inContent = false;
      inSpeakerNotes = false;
      continue;
    }
    if (purposeM) {
      cur.purpose = purposeM[1].trim();
      inContent = false;
      inSpeakerNotes = false;
      continue;
    }
    if (contentM) {
      inContent = true;
      inSpeakerNotes = false;
      const inline = contentM[1].trim();
      if (inline.length > 0) cur.contentLines.push(inline);
      continue;
    }
    if (speakerM) {
      inContent = false;
      inSpeakerNotes = true;
      cur.speakerNotes = speakerM[1].trim();
      continue;
    }
    if (visualM) {
      inContent = false;
      inSpeakerNotes = false;
      cur.visual = visualM[1].trim();
      continue;
    }
    if (contactM) {
      inContent = false;
      inSpeakerNotes = false;
      cur.contact = contactM[1].trim();
      continue;
    }

    // Continuation under the active region.
    if (inContent) {
      if (l.length === 0) continue;
      // Strip the leading "- " or "  - " bullet markers we are in
      // a content list under.
      const stripped = raw.replace(/^\s{2,}[-*]\s*/, "").replace(/^[-*]\s*/, "");
      cur.contentLines.push(stripped.trim());
      continue;
    }
    if (inSpeakerNotes) {
      if (l.length === 0) {
        inSpeakerNotes = false;
        continue;
      }
      cur.speakerNotes += " " + l;
      continue;
    }
  }
  if (cur) slides.push(cur);

  // 5. Fallback for decks that use `## Section` headers instead
  //    of the canonical `## Slide N — title` shape (e.g. the
  //    one-page sales deck and the demo-deck index).
  if (slides.length === 0) {
    const fallback = parseSectionStyleDeck(text);
    return {
      deckId: stem,
      deckTitle,
      description: descLines.join(" ").trim(),
      audience,
      purpose,
      cta,
      safeContract,
      slides: fallback,
    };
  }

  return {
    deckId: stem,
    deckTitle,
    description: descLines.join(" ").trim(),
    audience,
    purpose,
    cta,
    safeContract,
    slides,
  };
}

/**
 * Parse a section-style deck (`## Section` / `### Subsection`)
 * into slide records. Each top-level `## ` becomes a slide; the
 * body is captured as content lines.
 */
function parseSectionStyleDeck(text) {
  const lines = text.split(/\r?\n/);
  const slides = [];
  let cur = null;
  let buffer = [];
  const flush = () => {
    if (cur) {
      cur.contentLines = buffer
        .filter((l) => l.trim().length > 0)
        // Strip leading `### ` or `**` decorations so the
        // content reads as flat bullets.
        .map((l) => l.replace(/^#+\s+/, "").trim());
      slides.push(cur);
    }
    cur = null;
    buffer = [];
  };
  // First pass — count how many `## ` headers exist. If there's
  // only one (e.g. the one-pager has a single `## ChartNav ...`
  // banner and the real sections live at `### `), demote `### ` to
  // the slide-header level.
  const h2Count = lines.filter((l) => /^##\s+/.test(l.trim())).length;
  const useH3 = h2Count <= 1;
  const headerRe = useH3 ? /^###?\s+(.+)$/ : /^##\s+(.+)$/;

  for (const raw of lines) {
    const l = raw.trim();
    if (/^---\s*$/.test(l)) continue;
    // Skip the deck's own `# H1` so it never becomes a slide.
    if (/^#\s+/.test(l) && !/^##\s+/.test(l)) continue;
    // Skip the leading `## ChartNav ...` banner on the one-pager
    // when we are using H3 mode (it's the deck banner, not a
    // section).
    if (useH3 && /^##\s+/.test(l) && !/^###/.test(l)) continue;
    const sectionMatch = l.match(headerRe);
    if (sectionMatch) {
      flush();
      // Skip a leading "Slide N — " prefix if present (defensive).
      const title = sectionMatch[1].replace(/^Slide\s+[\d.]+\s*[—-]?\s*/i, "");
      cur = {
        number: String(slides.length + 1),
        title,
        purpose: null,
        contentLines: [],
        speakerNotes: null,
        visual: null,
        contact: null,
      };
      buffer = [];
      continue;
    }
    if (cur) {
      // Collect raw body lines; bullet-strip happens at flush.
      const stripped = raw
        .replace(/^\s*[-*]\s*/, "")
        .replace(/^####\s+/, "");
      buffer.push(stripped);
    }
  }
  flush();
  return slides;
}
