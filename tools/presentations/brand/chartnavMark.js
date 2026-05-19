/**
 * Reproduces the ChartNav brand mark + wordmark as PptxGenJS
 * shapes so the deck export does not depend on raster assets.
 *
 * The shape mirrors `apps/web/public/brand/chartnav-mark.svg` and
 * `apps/web/public/brand/chartnav-logo.svg` — two teal pulse
 * ticks flanking a tall red vertical bar.
 *
 * All dimensions are in inches (PptxGenJS native).
 */

import { PALETTE, TYPE } from "../theme.js";

/**
 * Draw the compact mark (mark only, no wordmark) at (x, y) with
 * total width `w`. Aspect locked at 1:1.
 */
export function drawMark(slide, x, y, w) {
  const h = w; // 1:1
  // Left teal tick — relative geometry from the 48x48 viewBox.
  // Left x=6, y=21, w=10, h=6, rx=1 → fractions of 48.
  slide.addShape("roundRect", {
    x: x + (6 / 48) * w,
    y: y + (21 / 48) * h,
    w: (10 / 48) * w,
    h: (6 / 48) * h,
    fill: { color: PALETTE.primary },
    line: { type: "none" },
    rectRadius: 0.02 * w,
  });
  // Right teal tick.
  slide.addShape("roundRect", {
    x: x + (32 / 48) * w,
    y: y + (21 / 48) * h,
    w: (10 / 48) * w,
    h: (6 / 48) * h,
    fill: { color: PALETTE.primary },
    line: { type: "none" },
    rectRadius: 0.02 * w,
  });
  // Center red vertical bar.
  slide.addShape("roundRect", {
    x: x + (22 / 48) * w,
    y: y + (6 / 48) * h,
    w: (4 / 48) * w,
    h: (36 / 48) * h,
    fill: { color: PALETTE.pulse },
    line: { type: "none" },
    rectRadius: 0.03 * w,
  });
}

/**
 * Draw the full logo (mark + wordmark) at (x, y) with total width
 * `w`. Aspect locked at the SVG's 520:120 ratio (≈ 4.33:1).
 */
export function drawLogo(slide, x, y, w) {
  const h = w * (120 / 520);
  // Pulse mark — left third of the logo.
  // SVG mark left tick: rect x=10 y=52 w=24 h=14
  // SVG mark right tick: rect x=62 y=52 w=24 h=14
  // SVG mark red bar:    rect x=40 y=20 w=12 h=78
  // Map from 520x120 → x_in/w
  const sx = (px) => x + (px / 520) * w;
  const sy = (py) => y + (py / 120) * h;
  const sw = (pw) => (pw / 520) * w;
  const sh = (ph) => (ph / 120) * h;

  slide.addShape("roundRect", {
    x: sx(10),
    y: sy(52),
    w: sw(24),
    h: sh(14),
    fill: { color: PALETTE.primary },
    line: { type: "none" },
    rectRadius: 0.025,
  });
  slide.addShape("roundRect", {
    x: sx(62),
    y: sy(52),
    w: sw(24),
    h: sh(14),
    fill: { color: PALETTE.primary },
    line: { type: "none" },
    rectRadius: 0.025,
  });
  slide.addShape("roundRect", {
    x: sx(40),
    y: sy(20),
    w: sw(12),
    h: sh(78),
    fill: { color: PALETTE.pulse },
    line: { type: "none" },
    rectRadius: 0.04,
  });

  // Wordmark — "Chart" in fg, "Nav" in primary teal.
  // SVG places "Chart" at x=120 baseline y=82 with font-size 80.
  // PptxGenJS positions text by box top-left, so we approximate
  // with a textbox that visually matches the SVG baseline.
  const fontSize = Math.round((80 / 120) * h * 72); // h in inches → pt
  const wordmarkH = h * 0.85;
  const wordmarkY = y + h * 0.08;
  // "Chart" — fg color.
  slide.addText("Chart", {
    x: sx(120),
    y: wordmarkY,
    w: sw(200),
    h: wordmarkH,
    fontFace: TYPE.family,
    fontSize: fontSize,
    color: PALETTE.fg,
    bold: true,
    valign: "middle",
    align: "left",
    margin: 0,
  });
  // "Nav" — primary teal.
  slide.addText("Nav", {
    x: sx(320),
    y: wordmarkY,
    w: sw(180),
    h: wordmarkH,
    fontFace: TYPE.family,
    fontSize: fontSize,
    color: PALETTE.primary,
    bold: true,
    valign: "middle",
    align: "left",
    margin: 0,
  });
}
