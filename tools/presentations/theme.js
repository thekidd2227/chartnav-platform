/**
 * ChartNav presentation theme.
 *
 * Palette + typography are pulled from the real product CSS at
 * apps/web/src/styles.css so the generated PPTX matches the
 * landing page and product UI. Do not duplicate hex values here —
 * if a value changes in styles.css, sync it here in the same PR.
 *
 * PPTX colors are 6-digit hex without the leading `#` per
 * PptxGenJS convention.
 */

export const PALETTE = {
  // Core ChartNav teal scale (--cn-primary*).
  primary: "0B6E79",
  primaryHover: "095A63",
  primaryActive: "07484F",
  primaryTint: "D6F0F3",
  primarySoft: "EEF8FA",
  // Aqua pulse (logo highlight).
  accent: "14B8A6",
  // Clinical red (logo cross / pulse) — used sparingly for the
  // "what ChartNav is not" boundary slides and for callouts that
  // need attention. Never use red for safe-claims contract text.
  pulse: "DC2626",
  // Surface scale.
  bg: "F4F8FA",
  bgAlt: "EEF2F5",
  surface: "FFFFFF",
  surfaceAlt: "F8FBFC",
  // Lines.
  line: "DCE5EA",
  lineStrong: "C4D2D9",
  // Text scale.
  fg: "0F172A",
  muted: "475569",
  dim: "64748B",
  // State.
  success: "15803D",
  successTint: "DCFCE7",
  warning: "B45309",
};

export const TYPE = {
  // Inter is loaded by apps/web/index.html; PowerPoint will fall
  // back to the OS default if Inter is not installed locally.
  // Calibri is the safe fallback for Mac/Windows clients.
  family: "Inter",
  fallback: "Calibri",
  sizes: {
    deckTitle: 36,
    slideTitle: 28,
    slideSubtitle: 18,
    sectionTitle: 32,
    body: 14,
    bodyLg: 16,
    caption: 11,
    footer: 10,
    eyebrow: 12,
    bigNumber: 48,
  },
};

// Slide dimensions — 16:9 widescreen. PptxGenJS uses inches.
export const SLIDE = {
  layout: "LAYOUT_WIDE",
  widthIn: 13.333,
  heightIn: 7.5,
};

// Common margins / spacings.
export const SPACING = {
  margin: 0.5,
  // Title strip top is the y-position where every non-cover slide
  // starts its title row.
  titleY: 0.5,
  titleH: 0.7,
  // Body region begins below the title rule.
  bodyY: 1.4,
  // Footer strip y-position (starts at).
  footerY: 7.0,
  footerH: 0.4,
};

// Footer / contact strip text.
export const FOOTER_TEXT = "ChartNav · jeanmax@arivergroup.com · chartnavmd.com";

// Safety contract one-liner — the canonical line from the
// approved-claims-language doc. Embedded at the bottom of every
// safety slide.
export const SAFETY_LINE =
  "Provider-reviewed workflow support. ChartNav does not diagnose, " +
  "create orders, send referrals, bill, or message patients automatically.";
