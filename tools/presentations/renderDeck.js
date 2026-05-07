/**
 * Renders a parsed deck object into a PptxGenJS presentation.
 *
 * Layout selection is done per-slide via `pickLayout`. The
 * heuristic looks at the slide title and content to decide which
 * branded layout to use.
 */

import PptxGenJS from "pptxgenjs";
import { SLIDE, PALETTE } from "./theme.js";
import {
  drawCover,
  drawSection,
  drawTitleBullets,
  drawFeatureCards,
  drawClinicalSignal,
  drawWorkflow,
  drawPricing,
  drawSafetyDual,
  drawCta,
  drawIndex,
} from "./slideLayouts.js";

export function renderDeck(deck) {
  const pptx = new PptxGenJS();
  pptx.layout = SLIDE.layout;
  pptx.author = "ChartNav · ARCG Systems";
  pptx.company = "Ariel's River Contracting Group, LLC";
  pptx.title = deck.deckTitle;
  pptx.subject = deck.purpose || "ChartNav presentation";

  const slideTotal = deck.slides.length;
  const ctxBase = { deckTitle: deck.deckTitle, slideTotal };

  // Cover slide always uses drawCover for slide 1.
  if (deck.slides.length > 0) {
    const cover = pptx.addSlide();
    drawCover(cover, deck, { ...ctxBase, slideIndex: 1 });
  }

  // Remaining slides.
  deck.slides.slice(1).forEach((slideRec, idx) => {
    const slide = pptx.addSlide();
    const layout = pickLayout(slideRec, deck);
    const ctx = { ...ctxBase, slideIndex: idx + 2 };
    layout(slide, slideRec, ctx);
  });

  return pptx;
}

/**
 * Heuristic layout picker. Order of checks matters — the most
 * specific layouts come first.
 */
function pickLayout(slideRec, deck) {
  const t = (slideRec.title || "").toLowerCase();
  const all = (slideRec.contentLines || []).join(" ").toLowerCase();
  const haystack = `${t} ${all}`;

  // Index slide for the demo-deck router.
  if (deck.deckId === "chartnav-demo-deck" || /^when to use which/i.test(t)) {
    return drawIndex;
  }

  // Clinical Signal Filtering — the prime feature card. Triggers
  // on either a Clinical Signal Filtering title OR a slide whose
  // title contains the canonical three-line cadence.
  if (
    /clinical signal filtering/i.test(t) ||
    /filters conversation\.\s*captures findings\.\s*builds the diagram/i.test(t)
  ) {
    return drawClinicalSignal;
  }

  // Pricing slides.
  if (/pricing|business model|cost|fee|how chartnav charges/i.test(t)) {
    return drawPricing;
  }

  // Safety / non-goals dual column.
  if (
    /what chartnav is not|buyer-safe non-goals|provider-in-control safety|provider-control safeguards|boundaries|safety boundaries/i.test(
      t
    )
  ) {
    return drawSafetyDual;
  }

  // Workflow strip — explicit workflow titles or arrow-separated
  // content.
  if (
    /workflow|seven explicit steps|click path|what you'll see/i.test(t) ||
    (slideRec.contentLines || []).some((l) => l.includes("→"))
  ) {
    return drawWorkflow;
  }

  // CTA / next-step / close.
  if (/next step|close|cta|talk to us|what we'd like|single cta/i.test(t)) {
    return drawCta;
  }

  // Section dividers — a slide with very little content body.
  if ((slideRec.contentLines || []).length === 0 && (slideRec.title || "").length > 0) {
    return drawSection;
  }

  // Feature cards — when a slide has 3–8 bullets that look like
  // headline-and-body pairs (contains "—" on most bullets).
  const bullets = slideRec.contentLines || [];
  if (
    bullets.length >= 3 &&
    bullets.length <= 8 &&
    bullets.filter((l) => l.includes("—") || /^\*\*[^*]+\*\*/.test(l)).length >= Math.ceil(bullets.length * 0.6)
  ) {
    return drawFeatureCards;
  }

  // Default to title + bullets.
  return drawTitleBullets;
}
