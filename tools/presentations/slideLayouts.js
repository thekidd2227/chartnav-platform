/**
 * Reusable slide-layout helpers for ChartNav presentations.
 *
 * Each function takes the PptxGenJS slide and a structured slide
 * record, then draws a branded layout. The renderer picks a
 * layout per slide using simple heuristics on the slide title +
 * content (see `pickLayout` in renderDeck.js).
 *
 * Layout catalog:
 *   - drawCover           the first slide of a deck (deck title)
 *   - drawSection         section divider with a single big title
 *   - drawTitleBullets    title + bullet body (the workhorse)
 *   - drawFeatureCards    3–6 feature cards in a grid
 *   - drawClinicalSignal  the prime CSF four-classification card
 *   - drawWorkflow        7-stage workflow strip
 *   - drawPricing         pricing-tier table
 *   - drawSafetyDual      "what ChartNav does / does not do"
 *   - drawCta             single-CTA close slide
 *   - drawAppendix        Q&A or table-style content
 *   - drawIndex           the demo-deck index
 *
 * Every layout includes the consistent header strip + footer
 * strip so a presenter can identify the source deck on any slide.
 */

import { PALETTE, TYPE, SPACING, FOOTER_TEXT, SAFETY_LINE } from "./theme.js";
import { drawMark, drawLogo } from "./brand/chartnavMark.js";

// ---------------------------------------------------------------
// Header / footer / chrome
// ---------------------------------------------------------------

function drawHeaderStrip(slide, deckTitle) {
  // Thin teal accent bar at the very top.
  slide.addShape("rect", {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.08,
    fill: { color: PALETTE.primary },
    line: { type: "none" },
  });
  // Tiny mark + abbreviated deck title in the top-left.
  drawMark(slide, 0.35, 0.18, 0.32);
  slide.addText(deckTitle, {
    x: 0.85,
    y: 0.15,
    w: 8,
    h: 0.4,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.eyebrow,
    color: PALETTE.muted,
    bold: false,
    valign: "middle",
    align: "left",
  });
}

function drawFooterStrip(slide, slideIndex, slideTotal) {
  slide.addShape("rect", {
    x: 0,
    y: 7.42,
    w: 13.333,
    h: 0.08,
    fill: { color: PALETTE.line },
    line: { type: "none" },
  });
  slide.addText(FOOTER_TEXT, {
    x: 0.5,
    y: 7.05,
    w: 8,
    h: 0.32,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.footer,
    color: PALETTE.dim,
    align: "left",
    valign: "middle",
  });
  slide.addText(`${slideIndex} / ${slideTotal}`, {
    x: 11.5,
    y: 7.05,
    w: 1.4,
    h: 0.32,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.footer,
    color: PALETTE.dim,
    align: "right",
    valign: "middle",
  });
}

function drawChrome(slide, ctx) {
  drawHeaderStrip(slide, ctx.deckTitle);
  drawFooterStrip(slide, ctx.slideIndex, ctx.slideTotal);
}

// ---------------------------------------------------------------
// Cover
// ---------------------------------------------------------------

export function drawCover(slide, deck, ctx) {
  // Full-bleed white with a teal accent band on the left.
  slide.background = { color: PALETTE.surface };
  slide.addShape("rect", {
    x: 0,
    y: 0,
    w: 0.5,
    h: 7.5,
    fill: { color: PALETTE.primary },
    line: { type: "none" },
  });

  // Logo top-center of right pane.
  drawLogo(slide, 1.2, 1.2, 4.5);

  // Deck title.
  slide.addText(deck.deckTitle, {
    x: 1.2,
    y: 3.1,
    w: 11,
    h: 1.2,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.deckTitle,
    color: PALETTE.fg,
    bold: true,
    align: "left",
    valign: "top",
  });

  // Tagline / first-slide title (often "Cover").
  const cover = deck.slides[0];
  if (cover && cover.title && cover.title.toLowerCase() !== "cover") {
    slide.addText(cover.title, {
      x: 1.2,
      y: 4.4,
      w: 11,
      h: 0.7,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.slideSubtitle,
      color: PALETTE.primary,
      bold: false,
      align: "left",
      valign: "top",
    });
  }

  // Audience + Purpose + CTA strip — small under the title.
  const meta = [];
  if (deck.audience) meta.push(`Audience — ${deck.audience}`);
  if (deck.purpose) meta.push(`Purpose — ${deck.purpose}`);
  if (deck.cta) meta.push(`Next step — ${deck.cta}`);
  slide.addText(meta.join("\n"), {
    x: 1.2,
    y: 5.3,
    w: 11,
    h: 1.5,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.body,
    color: PALETTE.muted,
    align: "left",
    valign: "top",
    paraSpaceAfter: 4,
  });

  // Footer.
  slide.addText(FOOTER_TEXT, {
    x: 1.2,
    y: 7.0,
    w: 10,
    h: 0.4,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.footer,
    color: PALETTE.dim,
    align: "left",
    valign: "middle",
  });

  attachSpeakerNotes(slide, deck.slides[0]);
}

// ---------------------------------------------------------------
// Section divider
// ---------------------------------------------------------------

export function drawSection(slide, slideRec, ctx) {
  slide.background = { color: PALETTE.primarySoft };
  drawChrome(slide, ctx);
  drawMark(slide, 0.5, 2.6, 0.9);
  slide.addText(slideRec.title || "", {
    x: 1.7,
    y: 2.6,
    w: 11,
    h: 1.2,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.sectionTitle,
    color: PALETTE.primary,
    bold: true,
    align: "left",
    valign: "middle",
  });
  if (slideRec.purpose) {
    slide.addText(slideRec.purpose, {
      x: 1.7,
      y: 3.9,
      w: 11,
      h: 0.6,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bodyLg,
      color: PALETTE.muted,
      align: "left",
      valign: "top",
    });
  }
  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Title + bullets (workhorse)
// ---------------------------------------------------------------

export function drawTitleBullets(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  const items = trimContent(slideRec.contentLines);
  const bullets = items.map((line) => ({
    text: stripBoldMarkers(line),
    options: {
      bullet: { type: "bullet" },
      paraSpaceAfter: 6,
    },
  }));
  slide.addText(bullets, {
    x: SPACING.margin,
    y: SPACING.bodyY,
    w: 12.3,
    h: 5.2,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.bodyLg,
    color: PALETTE.fg,
    valign: "top",
    paraSpaceAfter: 6,
  });

  if (slideRec.contact) drawContactStrip(slide, slideRec.contact);
  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Feature cards
// ---------------------------------------------------------------

export function drawFeatureCards(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  const items = trimContent(slideRec.contentLines).slice(0, 8);
  const cols = items.length <= 4 ? Math.min(items.length, 2) : 4;
  const rows = Math.ceil(items.length / cols);
  const gridW = 12.3;
  const gridH = 5.0;
  const gapX = 0.25;
  const gapY = 0.25;
  const cardW = (gridW - gapX * (cols - 1)) / cols;
  const cardH = Math.min(2.0, (gridH - gapY * (rows - 1)) / rows);

  items.forEach((raw, idx) => {
    const r = Math.floor(idx / cols);
    const c = idx % cols;
    const x = SPACING.margin + c * (cardW + gapX);
    const y = SPACING.bodyY + r * (cardH + gapY);
    // Card.
    slide.addShape("roundRect", {
      x,
      y,
      w: cardW,
      h: cardH,
      fill: { color: PALETTE.surfaceAlt },
      line: { color: PALETTE.line, width: 0.75 },
      rectRadius: 0.08,
    });
    // Teal accent strip on the left.
    slide.addShape("rect", {
      x,
      y,
      w: 0.08,
      h: cardH,
      fill: { color: PALETTE.primary },
      line: { type: "none" },
    });
    const { headline, body } = splitFeatureLine(raw);
    slide.addText(headline, {
      x: x + 0.25,
      y: y + 0.15,
      w: cardW - 0.4,
      h: 0.5,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bodyLg,
      color: PALETTE.primary,
      bold: true,
      valign: "top",
    });
    if (body) {
      slide.addText(body, {
        x: x + 0.25,
        y: y + 0.65,
        w: cardW - 0.4,
        h: cardH - 0.75,
        fontFace: TYPE.family,
        fontSize: TYPE.sizes.body,
        color: PALETTE.fg,
        valign: "top",
      });
    }
  });

  if (slideRec.contact) drawContactStrip(slide, slideRec.contact);
  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Clinical Signal Filtering — the prime feature card
// ---------------------------------------------------------------

export function drawClinicalSignal(slide, slideRec, ctx) {
  drawChrome(slide, ctx);

  // Header row — three-line cadence as the slide title.
  slide.addText("Clinical Signal Filtering", {
    x: SPACING.margin,
    y: SPACING.titleY,
    w: 12.3,
    h: 0.4,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.eyebrow,
    color: PALETTE.primary,
    bold: true,
    valign: "top",
  });
  slide.addText("Filters conversation. Captures findings. Builds the diagram.", {
    x: SPACING.margin,
    y: SPACING.titleY + 0.35,
    w: 12.3,
    h: 0.7,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.slideTitle,
    color: PALETTE.fg,
    bold: true,
    valign: "top",
  });

  // Quote band — the doctor's line.
  slide.addShape("roundRect", {
    x: SPACING.margin,
    y: 1.7,
    w: 12.3,
    h: 0.85,
    fill: { color: PALETTE.primarySoft },
    line: { color: PALETTE.primaryTint, width: 0.75 },
    rectRadius: 0.08,
  });
  slide.addText(
    [
      { text: "Doctor says:  ", options: { color: PALETTE.muted, italic: false, bold: false } },
      {
        text: '"Okay hold on… OD drusen in the macula… maybe OS flame hemorrhage inferior."',
        options: { color: PALETTE.fg, italic: true, bold: false },
      },
    ],
    {
      x: SPACING.margin + 0.25,
      y: 1.78,
      w: 12.0,
      h: 0.7,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bodyLg,
      valign: "middle",
    }
  );

  // Four classification cards.
  const cards = [
    {
      label: "Ignored chatter",
      text: '"Okay hold on"',
      color: PALETTE.dim,
      tint: PALETTE.bgAlt,
    },
    {
      label: "Clinical finding",
      text: '"OD drusen in the macula"',
      color: PALETTE.primary,
      tint: PALETTE.primarySoft,
    },
    {
      label: "Uncertain phrase",
      text: '"maybe OS flame hemorrhage inferior"',
      color: PALETTE.warning,
      tint: "FFF7E6",
    },
    {
      label: "Proposed annotation",
      text: "Provider review required",
      color: PALETTE.pulse,
      tint: "FDE8E8",
    },
  ];
  const cardY = 2.85;
  const cardH = 1.7;
  const cardW = (12.3 - 3 * 0.15) / 4;
  cards.forEach((card, idx) => {
    const x = SPACING.margin + idx * (cardW + 0.15);
    slide.addShape("roundRect", {
      x,
      y: cardY,
      w: cardW,
      h: cardH,
      fill: { color: card.tint },
      line: { color: PALETTE.line, width: 0.75 },
      rectRadius: 0.08,
    });
    slide.addShape("rect", {
      x,
      y: cardY,
      w: cardW,
      h: 0.08,
      fill: { color: card.color },
      line: { type: "none" },
    });
    slide.addText(card.label, {
      x: x + 0.2,
      y: cardY + 0.18,
      w: cardW - 0.3,
      h: 0.4,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.eyebrow,
      color: card.color,
      bold: true,
      valign: "top",
    });
    slide.addText(card.text, {
      x: x + 0.2,
      y: cardY + 0.65,
      w: cardW - 0.3,
      h: cardH - 0.75,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: PALETTE.fg,
      bold: false,
      italic: true,
      valign: "top",
    });
  });

  // Provider-control footnote.
  slide.addText(
    "The provider applies, edits, or rejects every proposal before anything is saved or finalized.",
    {
      x: SPACING.margin,
      y: cardY + cardH + 0.35,
      w: 12.3,
      h: 0.55,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: PALETTE.muted,
      bold: false,
      align: "left",
      valign: "middle",
    }
  );

  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Workflow strip
// ---------------------------------------------------------------

export function drawWorkflow(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  // Default 7-stage workflow if no stages provided. We try to
  // pull stages from the slide content first.
  const stages = extractStages(slideRec.contentLines);
  const items = stages.length >= 4 ? stages : [
    "scribe",
    "proposals",
    "diagram",
    "summary",
    "brief",
    "action queue",
    "demo",
  ];

  const top = SPACING.bodyY + 0.5;
  const w = (12.3 - (items.length - 1) * 0.2) / items.length;
  const h = 1.6;
  items.forEach((label, idx) => {
    const x = SPACING.margin + idx * (w + 0.2);
    slide.addShape("roundRect", {
      x,
      y: top,
      w,
      h,
      fill: { color: idx % 2 === 0 ? PALETTE.primarySoft : PALETTE.surface },
      line: { color: PALETTE.primaryTint, width: 0.75 },
      rectRadius: 0.08,
    });
    slide.addText(`${idx + 1}`, {
      x: x + w / 2 - 0.4,
      y: top + 0.15,
      w: 0.8,
      h: 0.5,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bodyLg,
      color: PALETTE.primary,
      bold: true,
      align: "center",
      valign: "middle",
    });
    slide.addText(label, {
      x: x + 0.1,
      y: top + 0.7,
      w: w - 0.2,
      h: h - 0.85,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: PALETTE.fg,
      bold: false,
      align: "center",
      valign: "top",
    });
    if (idx < items.length - 1) {
      slide.addShape("rightTriangle", {
        x: x + w + 0.04,
        y: top + h / 2 - 0.06,
        w: 0.12,
        h: 0.12,
        fill: { color: PALETTE.primary },
        line: { type: "none" },
        rotate: 0,
      });
    }
  });

  // Provider-control reminder.
  slide.addText(
    "Provider drives every transition. Nothing finalizes without a click.",
    {
      x: SPACING.margin,
      y: top + h + 0.6,
      w: 12.3,
      h: 0.5,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: PALETTE.muted,
      align: "center",
      valign: "middle",
    }
  );

  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Pricing
// ---------------------------------------------------------------

export function drawPricing(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  // Three highlight cards: per-provider, per-practice, pilot.
  const tiers = [
    {
      headline: "Per provider",
      price: "$299–$499",
      unit: "/ provider / month",
      sub: "Subscription tier — pick this OR per-practice.",
    },
    {
      headline: "Per practice",
      price: "$5,000",
      unit: "/ practice / month flat",
      sub: "Alternative to per-provider; covers the agreed provider count.",
    },
    {
      headline: "Pilot",
      price: "$10,000",
      unit: "flat · 4–6 weeks",
      sub: "Pilot fees are not discounted unless approved case-by-case.",
    },
  ];
  const top = SPACING.bodyY + 0.2;
  const w = (12.3 - 2 * 0.3) / 3;
  const h = 3.0;
  tiers.forEach((t, idx) => {
    const x = SPACING.margin + idx * (w + 0.3);
    slide.addShape("roundRect", {
      x,
      y: top,
      w,
      h,
      fill: { color: idx === 2 ? PALETTE.primary : PALETTE.surface },
      line: { color: idx === 2 ? PALETTE.primary : PALETTE.line, width: 0.75 },
      rectRadius: 0.1,
    });
    const fg = idx === 2 ? PALETTE.surface : PALETTE.fg;
    const sub = idx === 2 ? PALETTE.primaryTint : PALETTE.muted;
    slide.addText(t.headline, {
      x: x + 0.3,
      y: top + 0.25,
      w: w - 0.6,
      h: 0.4,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.eyebrow,
      color: idx === 2 ? PALETTE.primaryTint : PALETTE.primary,
      bold: true,
      valign: "top",
    });
    slide.addText(t.price, {
      x: x + 0.3,
      y: top + 0.7,
      w: w - 0.6,
      h: 0.9,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bigNumber,
      color: fg,
      bold: true,
      valign: "top",
    });
    slide.addText(t.unit, {
      x: x + 0.3,
      y: top + 1.65,
      w: w - 0.6,
      h: 0.4,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bodyLg,
      color: sub,
      valign: "top",
    });
    slide.addText(t.sub, {
      x: x + 0.3,
      y: top + 2.1,
      w: w - 0.6,
      h: h - 2.2,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: sub,
      valign: "top",
    });
  });

  // Multi-practice discount strip.
  slide.addShape("roundRect", {
    x: SPACING.margin,
    y: top + h + 0.3,
    w: 12.3,
    h: 0.8,
    fill: { color: PALETTE.primarySoft },
    line: { color: PALETTE.primaryTint, width: 0.75 },
    rectRadius: 0.08,
  });
  slide.addText(
    "Multi-practice annual discounts — 2–4 = 10% off · 5–9 = 15% off · 10+ = enterprise pricing.",
    {
      x: SPACING.margin + 0.3,
      y: top + h + 0.3,
      w: 12.0,
      h: 0.8,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.bodyLg,
      color: PALETTE.primary,
      bold: true,
      align: "center",
      valign: "middle",
    }
  );

  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Safety dual column ("what ChartNav does / does not do")
// ---------------------------------------------------------------

export function drawSafetyDual(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  const items = trimContent(slideRec.contentLines);
  const positives = items.filter((l) => !isNegativeBullet(l));
  const negatives = items.filter(isNegativeBullet);

  const top = SPACING.bodyY + 0.2;
  const colW = (12.3 - 0.4) / 2;
  const colH = 4.6;

  // Positive column — "What ChartNav does"
  slide.addShape("roundRect", {
    x: SPACING.margin,
    y: top,
    w: colW,
    h: colH,
    fill: { color: PALETTE.primarySoft },
    line: { color: PALETTE.primaryTint, width: 0.75 },
    rectRadius: 0.1,
  });
  slide.addText("What ChartNav does", {
    x: SPACING.margin + 0.3,
    y: top + 0.2,
    w: colW - 0.5,
    h: 0.5,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.bodyLg,
    color: PALETTE.primary,
    bold: true,
    valign: "top",
  });
  const positiveDefaults = [
    "Provider-reviewed documentation support.",
    "Ophthalmology-specific OD/OS retinal canvas.",
    "Clinical Signal Filtering — chatter / findings / uncertainty / proposals.",
    "Audit-friendly design with metadata-only logging.",
  ];
  const positiveBullets = (positives.length > 0 ? positives : positiveDefaults).map(
    (line) => ({ text: stripBoldMarkers(line), options: { bullet: { type: "bullet" }, paraSpaceAfter: 6 } })
  );
  slide.addText(positiveBullets, {
    x: SPACING.margin + 0.3,
    y: top + 0.8,
    w: colW - 0.6,
    h: colH - 1.0,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.body,
    color: PALETTE.fg,
    valign: "top",
    paraSpaceAfter: 6,
  });

  // Negative column — "What ChartNav does NOT do"
  const negX = SPACING.margin + colW + 0.4;
  slide.addShape("roundRect", {
    x: negX,
    y: top,
    w: colW,
    h: colH,
    fill: { color: "FDE8E8" },
    line: { color: PALETTE.pulse, width: 0.75 },
    rectRadius: 0.1,
  });
  slide.addText("What ChartNav does NOT do", {
    x: negX + 0.3,
    y: top + 0.2,
    w: colW - 0.5,
    h: 0.5,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.bodyLg,
    color: PALETTE.pulse,
    bold: true,
    valign: "top",
  });
  const negativeDefaults = [
    "Not a certified EHR replacement.",
    "Not autonomous diagnosis.",
    "Not automatic orders, coding, referrals, or patient messaging.",
    "Not real-PHI production without legal / security review.",
  ];
  const negativeBullets = (negatives.length > 0 ? negatives : negativeDefaults).map(
    (line) => ({ text: stripBoldMarkers(line), options: { bullet: { type: "bullet" }, paraSpaceAfter: 6 } })
  );
  slide.addText(negativeBullets, {
    x: negX + 0.3,
    y: top + 0.8,
    w: colW - 0.6,
    h: colH - 1.0,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.body,
    color: PALETTE.fg,
    valign: "top",
    paraSpaceAfter: 6,
  });

  // Safety contract footer.
  slide.addText(SAFETY_LINE, {
    x: SPACING.margin,
    y: top + colH + 0.3,
    w: 12.3,
    h: 0.5,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.body,
    color: PALETTE.muted,
    italic: true,
    align: "center",
    valign: "middle",
  });

  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// CTA close
// ---------------------------------------------------------------

export function drawCta(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  const items = trimContent(slideRec.contentLines);
  const bullets = items.map((line) => ({
    text: stripBoldMarkers(line),
    options: { bullet: { type: "bullet" }, paraSpaceAfter: 8 },
  }));

  // Big CTA panel.
  slide.addShape("roundRect", {
    x: SPACING.margin,
    y: SPACING.bodyY + 0.2,
    w: 12.3,
    h: 4.4,
    fill: { color: PALETTE.primary },
    line: { type: "none" },
    rectRadius: 0.12,
  });
  slide.addText(slideRec.title, {
    x: SPACING.margin + 0.5,
    y: SPACING.bodyY + 0.4,
    w: 11.3,
    h: 0.7,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.slideTitle,
    color: PALETTE.surface,
    bold: true,
    valign: "top",
  });
  slide.addText(bullets, {
    x: SPACING.margin + 0.5,
    y: SPACING.bodyY + 1.3,
    w: 11.3,
    h: 3.1,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.bodyLg,
    color: PALETTE.surface,
    valign: "top",
    paraSpaceAfter: 8,
  });

  // Contact strip below the panel.
  slide.addText("jeanmax@arivergroup.com  ·  chartnavmd.com", {
    x: SPACING.margin,
    y: SPACING.bodyY + 4.7,
    w: 12.3,
    h: 0.4,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.bodyLg,
    color: PALETTE.primary,
    bold: true,
    align: "center",
    valign: "middle",
  });

  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Index (used by chartnav-demo-deck.md routing index)
// ---------------------------------------------------------------

export function drawIndex(slide, slideRec, ctx) {
  drawChrome(slide, ctx);
  drawSlideTitle(slide, slideRec);

  const items = trimContent(slideRec.contentLines);
  const top = SPACING.bodyY + 0.2;
  const h = (4.5 - 0.2 * (items.length - 1)) / Math.max(items.length, 1);
  items.forEach((line, idx) => {
    const y = top + idx * (h + 0.2);
    slide.addShape("roundRect", {
      x: SPACING.margin,
      y,
      w: 12.3,
      h,
      fill: { color: PALETTE.surfaceAlt },
      line: { color: PALETTE.line, width: 0.75 },
      rectRadius: 0.08,
    });
    slide.addText(stripBoldMarkers(line), {
      x: SPACING.margin + 0.3,
      y: y + 0.1,
      w: 11.7,
      h: h - 0.2,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: PALETTE.fg,
      valign: "middle",
    });
  });

  attachSpeakerNotes(slide, slideRec);
}

// ---------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------

function drawSlideTitle(slide, slideRec) {
  slide.addText(slideRec.title || "", {
    x: SPACING.margin,
    y: SPACING.titleY,
    w: 12.3,
    h: SPACING.titleH,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.slideTitle,
    color: PALETTE.fg,
    bold: true,
    align: "left",
    valign: "middle",
  });
  // Title rule.
  slide.addShape("rect", {
    x: SPACING.margin,
    y: SPACING.titleY + SPACING.titleH + 0.05,
    w: 12.3,
    h: 0.04,
    fill: { color: PALETTE.primary },
    line: { type: "none" },
  });
  if (slideRec.purpose) {
    slide.addText(slideRec.purpose, {
      x: SPACING.margin,
      y: SPACING.titleY + SPACING.titleH + 0.15,
      w: 12.3,
      h: 0.5,
      fontFace: TYPE.family,
      fontSize: TYPE.sizes.body,
      color: PALETTE.muted,
      italic: true,
      align: "left",
      valign: "top",
    });
  }
}

function drawContactStrip(slide, contactText) {
  slide.addText(contactText, {
    x: SPACING.margin,
    y: 6.5,
    w: 12.3,
    h: 0.4,
    fontFace: TYPE.family,
    fontSize: TYPE.sizes.body,
    color: PALETTE.primary,
    italic: false,
    bold: true,
    align: "center",
    valign: "middle",
  });
}

function attachSpeakerNotes(slide, slideRec) {
  if (slideRec && slideRec.speakerNotes) {
    slide.addNotes(slideRec.speakerNotes);
  }
}

function trimContent(lines) {
  if (!lines) return [];
  return lines.filter((l) => l && l.trim().length > 0).map((l) => l.trim());
}

function stripBoldMarkers(text) {
  // Convert markdown bold/italic syntax to plain text with the
  // visual emphasis carried by the layout instead.
  return text.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\*([^*]+)\*/g, "$1").replace(/`([^`]+)`/g, "$1");
}

function splitFeatureLine(line) {
  // A feature card line typically looks like:
  //   "**Feature name** — supporting copy"
  // or
  //   "Feature name — supporting copy"
  const stripped = stripBoldMarkers(line);
  const sepMatch = stripped.match(/^([^—:]+)[—:]\s*(.+)$/);
  if (sepMatch) {
    return { headline: sepMatch[1].trim(), body: sepMatch[2].trim() };
  }
  return { headline: stripped, body: "" };
}

function extractStages(lines) {
  // Look for an arrow-separated workflow: "scribe → proposals → ..."
  const trimmed = trimContent(lines).map(stripBoldMarkers);
  const arrow = trimmed.find((l) => l.includes("→"));
  if (arrow) return arrow.split("→").map((s) => s.trim()).filter(Boolean);
  return [];
}

function isNegativeBullet(line) {
  const stripped = stripBoldMarkers(line).toLowerCase();
  return (
    /^not\s/.test(stripped) ||
    /^no orders\b/.test(stripped) ||
    /\bdoes not\b/.test(stripped) ||
    /\bnever\b/.test(stripped) ||
    /\bnot a(n)? \b/.test(stripped) ||
    /\bnot real-phi\b/.test(stripped) ||
    /\bnot autonomous\b/.test(stripped) ||
    /\bnot automatic\b/.test(stripped) ||
    /\bnot a certified\b/.test(stripped)
  );
}
